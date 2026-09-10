#!/usr/bin/env python3
"""Coleta moderada de notícias de futebol brasileiro publicadas pelo Lance!."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

SITEMAP = "https://www.lance.com.br/sitemap/news/today.xml"
# Sitemap de artigos recentes: ~1200 URLs, muito maior que o de "hoje".
SITEMAP_RECENTES = "https://www.lance.com.br/sitemap/articles-current.xml"
FONTES_SITEMAP = {"hoje": SITEMAP, "recentes": SITEMAP_RECENTES}
SAIDA = Path("outputs/noticias_lance.json")
SECOES_FUTEBOL_BRASILEIRO = {
    "brasileirao", "copa-do-brasil", "futebol-nacional", "america-mineiro",
    "athletico-paranaense", "atletico-mineiro", "bahia", "botafogo", "ceara",
    "chapecoense", "corinthians", "coritiba", "cruzeiro", "flamengo",
    "fluminense", "fortaleza", "goias", "gremio", "guarani", "internacional",
    "juventude", "mirassol", "palmeiras", "ponte-preta", "red-bull-bragantino",
    "remo", "santos", "sao-paulo", "sport", "vasco", "vitoria",
}
RUIDOS = (
    re.compile(r"^relacionadas$", re.I),
    re.compile(r"^continua apos a publicidade$", re.I),
    re.compile(r"^[➡🔥]", re.I),
    re.compile(r"ganhe r\$.*(?:credito|jogue)", re.I),
    re.compile(r"aposta nao e investimento", re.I),
    re.compile(r"^para acompanhar as noticias .+ acompanhe o lance!", re.I),
)


def normalizar_espacos(valor: Any) -> str:
    return re.sub(r"\s+", " ", str(valor or "").replace("\xa0", " ")).strip()


def sem_acentos(texto: str) -> str:
    return "".join(
        caractere for caractere in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caractere) != "Mn"
    )


def iso_utc(valor: str | None) -> str | None:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        return None


def obter_texto(url: str, tentativas: int = 3) -> str:
    requisicao = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Projeto-PLN-Noticias/2.0 (uso academico; coleta moderada)",
            "Accept-Language": "pt-BR,pt;q=0.9",
        },
    )
    ultimo_erro: Exception | None = None
    for tentativa in range(tentativas):
        try:
            with urllib.request.urlopen(requisicao, timeout=30) as resposta:
                return resposta.read().decode(resposta.headers.get_content_charset() or "utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError) as erro:
            ultimo_erro = erro
            if tentativa + 1 < tentativas:
                time.sleep(1.5 * (tentativa + 1))
    raise RuntimeError(f"falha ao acessar {url}: {ultimo_erro}")


def nome_local(elemento: ET.Element) -> str:
    return elemento.tag.rsplit("}", 1)[-1]


def primeiro_texto(elemento: ET.Element, nome: str) -> str:
    for filho in elemento.iter():
        if nome_local(filho) == nome and filho.text:
            return normalizar_espacos(filho.text)
    return ""


def ler_sitemap(xml: str) -> list[dict[str, Any]]:
    raiz = ET.fromstring(xml)
    itens: list[dict[str, Any]] = []
    for no_url in (elemento for elemento in raiz if nome_local(elemento) == "url"):
        url = ""
        imagem = None
        titulo = ""
        publicado = None
        for filho in no_url:
            local = nome_local(filho)
            if local == "loc":
                url = normalizar_espacos(filho.text)
            elif local == "news":
                titulo = primeiro_texto(filho, "title")
                publicado = iso_utc(primeiro_texto(filho, "publication_date"))
            elif local == "image":
                imagem = primeiro_texto(filho, "loc") or None
            elif local == "lastmod" and not publicado:
                publicado = iso_utc(normalizar_espacos(filho.text))
        # O sitemap de "hoje" traz título; o de artigos recentes traz apenas a
        # URL e a data — nesse caso o título é obtido depois, na própria página.
        if url:
            itens.append({"url": url, "titulo": titulo, "publicado_em": publicado, "imagem": imagem})
    return sorted(itens, key=lambda item: item.get("publicado_em") or "", reverse=True)


def eh_futebol_brasileiro(item: dict[str, Any]) -> bool:
    partes = [parte for parte in urlparse(item["url"]).path.split("/") if parte]
    secao = partes[0] if partes else ""
    if secao in SECOES_FUTEBOL_BRASILEIRO:
        return True
    if secao != "fora-de-campo":
        return False
    titulo = sem_acentos(item["titulo"].lower())
    return any(secao_time.replace("-", " ") in titulo for secao_time in SECOES_FUTEBOL_BRASILEIRO)


def percorrer_jsonld(valor: Any):
    if isinstance(valor, list):
        for item in valor:
            yield from percorrer_jsonld(item)
    elif isinstance(valor, dict):
        yield valor
        yield from percorrer_jsonld(valor.get("@graph", []))


def jsonld_noticia(sopa: BeautifulSoup) -> dict[str, Any]:
    for script in sopa.select('script[type="application/ld+json"]'):
        try:
            for objeto in percorrer_jsonld(json.loads(script.get_text())):
                tipos = objeto.get("@type", [])
                tipos = tipos if isinstance(tipos, list) else [tipos]
                if "NewsArticle" in tipos:
                    return objeto
        except (json.JSONDecodeError, TypeError):
            continue
    return {}


def autor_texto(valor: Any) -> str | None:
    autores = valor if isinstance(valor, list) else [valor]
    nomes = []
    for autor in autores:
        nome = autor if isinstance(autor, str) else autor.get("name") if isinstance(autor, dict) else None
        if normalizar_espacos(nome):
            nomes.append(normalizar_espacos(nome))
    return ", ".join(nomes) or None


def eh_ruido(texto: str) -> bool:
    comparavel = sem_acentos(texto).lower()
    return any(padrao.search(comparavel) for padrao in RUIDOS)


def extrair_artigo(html: str, item: dict[str, Any]) -> dict[str, Any]:
    sopa = BeautifulSoup(html, "html.parser")
    dados = jsonld_noticia(sopa)
    corpo = sopa.select_one(".paywall-content")
    if corpo is None:
        raise ValueError("corpo da matéria não encontrado")

    blocos = corpo.select("h2, p.paragraph-html") or corpo.find_all(["h2", "p"])
    paragrafos: list[str] = []
    for bloco in blocos:
        texto = normalizar_espacos(bloco.get_text(" ", strip=True))
        if texto and not eh_ruido(texto) and (not paragrafos or paragrafos[-1] != texto):
            paragrafos.append(texto)
    texto = "\n\n".join(paragrafos)
    if len(texto.split()) < 50:
        raise ValueError("matéria sem texto suficiente para PLN")

    url = normalizar_espacos(
        (dados.get("mainEntityOfPage") or {}).get("@id")
        if isinstance(dados.get("mainEntityOfPage"), dict) else dados.get("url")
    ) or item["url"]
    imagens = dados.get("image", [])
    imagens = imagens if isinstance(imagens, list) else [imagens]
    imagens = [imagem if isinstance(imagem, str) else imagem.get("url") for imagem in imagens if imagem]
    titulo = normalizar_espacos(dados.get("headline") or item["titulo"])
    return {
        "id": hashlib.sha256(url.encode()).hexdigest()[:16],
        "titulo": titulo,
        "subtitulo": normalizar_espacos(dados.get("alternativeHeadline") or dados.get("description")) or None,
        "texto": texto,
        "paragrafos": paragrafos,
        "quantidade_palavras": len(texto.split()),
        "autor": autor_texto(dados.get("author")),
        "publicado_em": iso_utc(dados.get("datePublished") or item.get("publicado_em")),
        "modificado_em": iso_utc(dados.get("dateModified")),
        "secao": normalizar_espacos(dados.get("articleSection")) or None,
        "imagem": next((imagem for imagem in imagens if imagem), item.get("imagem")),
        "url": url,
        "fonte": "Lance!",
    }


def coletar(limite: int = 30, todos_esportes: bool = False, concorrencia: int = 3, sitemap: str = SITEMAP) -> tuple[list[dict[str, Any]], list[dict[str, str]], int]:
    itens = ler_sitemap(obter_texto(sitemap))
    candidatos = [item for item in itens if todos_esportes or eh_futebol_brasileiro(item)][:limite]

    def trabalho(item: dict[str, Any]):
        try:
            return extrair_artigo(obter_texto(item["url"]), item), None
        except Exception as erro:  # registra uma URL defeituosa sem perder as demais
            return None, {"titulo": item["titulo"], "url": item["url"], "motivo": str(erro)}

    with ThreadPoolExecutor(max_workers=max(1, min(concorrencia, 5))) as executor:
        resultados = list(executor.map(trabalho, candidatos))
    noticias = [noticia for noticia, _ in resultados if noticia]
    erros = [erro for _, erro in resultados if erro]
    return noticias, erros, len(itens)


def salvar(noticias: list[dict[str, Any]], erros: list[dict[str, str]], total_sitemap: int, acumular: bool, saida: Path = SAIDA, sitemap: str = SITEMAP) -> Path:
    if acumular and saida.exists():
        anteriores = json.loads(saida.read_text(encoding="utf-8")).get("noticias", [])
        por_id = {noticia["id"]: noticia for noticia in anteriores}
        por_id.update({noticia["id"]: noticia for noticia in noticias})
        noticias = sorted(por_id.values(), key=lambda item: item.get("publicado_em") or "", reverse=True)
    saida.parent.mkdir(parents=True, exist_ok=True)
    documento = {
        "fonte": sitemap,
        "extraido_em": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "filtro": "futebol_brasileiro",
        "total_itens_no_sitemap": total_sitemap,
        "total_noticias_extraidas": len(noticias),
        "total_erros": len(erros),
        "erros": erros,
        "noticias": noticias,
    }
    saida.write_text(json.dumps(documento, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    saida.with_suffix(".jsonl").write_text(
        "".join(json.dumps(noticia, ensure_ascii=False) + "\n" for noticia in noticias), encoding="utf-8"
    )
    return saida


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limite", type=int, default=30, help="quantidade de notícias (padrão: 30)")
    parser.add_argument("--todos", action="store_true", help="inclui todos os esportes")
    parser.add_argument("--acumular", action="store_true", help="preserva notícias de execuções anteriores")
    parser.add_argument("--concorrencia", type=int, default=3, choices=range(1, 6))
    parser.add_argument(
        "--fonte", choices=sorted(FONTES_SITEMAP), default="recentes",
        help="'hoje' = notícias do dia; 'recentes' = artigos de vários dias (padrão)",
    )
    args = parser.parse_args()
    if args.limite < 1:
        parser.error("--limite deve ser maior que zero")
    sitemap = FONTES_SITEMAP[args.fonte]
    noticias, erros, total = coletar(args.limite, args.todos, args.concorrencia, sitemap)
    caminho = salvar(noticias, erros, total, args.acumular, sitemap=sitemap)
    print(f"{len(noticias)} notícias coletadas; {len(erros)} erros.")
    print(f"Base bruta: {caminho.resolve()}")


if __name__ == "__main__":
    main()
