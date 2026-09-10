#!/usr/bin/env python3
"""Pré-processa a base do Lance! para tarefas de PLN em português."""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import simplemma
from nltk.stem.snowball import SnowballStemmer

ENTRADA = Path("outputs/noticias_lance.json")
SAIDA = Path("outputs/noticias_lance_processadas.json")
STOPWORDS = frozenset("""
a à às agora ainda algo algum alguma algumas alguns ampla amplas amplo amplos ante antes ao aos após aquela aquelas aquele aqueles aquilo as até através cada coisa com como contra contudo da daquele daqueles das de dela delas dele deles depois dessa dessas desse desses desta destas deste destes deve devem devendo dever deverá deverão deveria deveriam devia deviam disse disso disto do dos e é ela elas ele eles em enquanto entre era eram essa essas esse esses esta está estamos estão estas estava estavam este estes eu fazendo fazer feita feitas feito feitos foi fomos for foram fosse fossem grande grandes há isso isto já la lá lhe lhes lo mas me mesma mesmas mesmo mesmos meu meus minha minhas muita muitas muito muitos na não nas nem nenhum nessa nessas neste nestes no nos nós nossa nossas nosso nossos num numa nunca o os ou outra outras outro outros para pela pelas pelo pelos pequena pequenas pequeno pequenos per perante pode pude podendo poder poderia poderiam podia podiam pois por porém porque posso pouca poucas pouco poucos primeiro primeiros própria próprias próprio próprios quais qual quando quanto quantos que quem são se seja sejam sem sempre sendo ser será serão seu seus si sido só sob sobre sua suas talvez também tampouco te tem tendo tenha ter teu teus toda todas todavia todo todos tu tua tuas tudo um uma umas uns vendo ver vez vindo vir vos você vocês
""".split())
TOKEN = re.compile(r"[^\W\d_]+", re.UNICODE)
URL = re.compile(r"https?://\S+|www\.\S+", re.I)
EMAIL = re.compile(r"\b\S+@\S+\.\S+\b")


def normalizar_texto(texto: str) -> str:
    texto = unicodedata.normalize("NFC", texto).lower()
    texto = URL.sub(" ", texto)
    texto = EMAIL.sub(" ", texto)
    texto = re.sub(r"[\U00010000-\U0010ffff]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def tokenizar(texto: str) -> list[str]:
    return TOKEN.findall(texto)


def preprocessar_noticia(noticia: dict[str, Any], stemmer: SnowballStemmer) -> dict[str, Any]:
    normalizado = normalizar_texto(noticia["texto"])
    tokens = tokenizar(normalizado)
    tokens_limpos = [token for token in tokens if token not in STOPWORDS and len(token) > 1]
    return {
        "id": noticia["id"],
        "titulo": noticia["titulo"],
        "secao": noticia.get("secao"),
        "publicado_em": noticia.get("publicado_em"),
        "url": noticia["url"],
        "texto_original": noticia["texto"],
        "texto_normalizado": normalizado,
        "tokens": tokens,
        "tokens_sem_stopwords": tokens_limpos,
        "stems": [stemmer.stem(token) for token in tokens_limpos],
        "lemas": [simplemma.lemmatize(token, lang="pt") for token in tokens_limpos],
        "quantidade_tokens": len(tokens),
        "quantidade_tokens_limpos": len(tokens_limpos),
    }


def processar(entrada: Path = ENTRADA, saida: Path = SAIDA) -> tuple[dict[str, Any], dict[str, Any]]:
    bruto = json.loads(entrada.read_text(encoding="utf-8"))
    stemmer = SnowballStemmer("portuguese")
    noticias = [preprocessar_noticia(noticia, stemmer) for noticia in bruto["noticias"]]
    vocabulario = Counter(token for noticia in noticias for token in noticia["tokens_sem_stopwords"])
    secoes = Counter(noticia.get("secao") or "Sem seção" for noticia in noticias)
    estatisticas = {
        "total_documentos": len(noticias),
        "total_tokens": sum(item["quantidade_tokens"] for item in noticias),
        "total_tokens_sem_stopwords": sum(item["quantidade_tokens_limpos"] for item in noticias),
        "tamanho_vocabulario": len(vocabulario),
        "documentos_por_secao": dict(secoes.most_common()),
        "termos_mais_frequentes": dict(vocabulario.most_common(30)),
    }
    documento = {
        "fonte": str(entrada),
        "processado_em": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "etapas": [
            "normalização Unicode NFC e conversão para minúsculas",
            "remoção de URLs, e-mails, emojis, números e pontuação",
            "tokenização por palavras",
            "remoção de stopwords em português",
            "stemming Snowball para português",
            "lematização com simplemma para português",
        ],
        "estatisticas": estatisticas,
        "noticias": noticias,
    }
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(documento, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    saida.with_suffix(".jsonl").write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in noticias), encoding="utf-8"
    )
    with saida.with_suffix(".csv").open("w", newline="", encoding="utf-8") as arquivo:
        campos = ["id", "titulo", "secao", "publicado_em", "url", "texto_normalizado", "tokens_sem_stopwords", "stems", "lemas", "quantidade_tokens", "quantidade_tokens_limpos"]
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        for item in noticias:
            linha = {campo: item.get(campo) for campo in campos}
            for campo in ("tokens_sem_stopwords", "stems", "lemas"):
                linha[campo] = " ".join(linha[campo])
            escritor.writerow(linha)
    saida.with_name("estatisticas.json").write_text(
        json.dumps(estatisticas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return documento, estatisticas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=ENTRADA)
    parser.add_argument("--saida", type=Path, default=SAIDA)
    args = parser.parse_args()
    _, estatisticas = processar(args.entrada, args.saida)
    print(f"{estatisticas['total_documentos']} documentos processados.")
    print(f"Vocabulário: {estatisticas['tamanho_vocabulario']} termos.")
    print(f"Base processada: {args.saida.resolve()}")


if __name__ == "__main__":
    main()
