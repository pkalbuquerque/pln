#!/usr/bin/env python3
"""Testes automatizados das etapas de coleta e pré-processamento.

Executar a partir da raiz do projeto:

    python -m unittest discover -s test -p "test_*.py" -v

Os testes não acessam a rede: usam amostras de HTML/XML embutidas, de modo
que sejam rápidos e reprodutíveis em qualquer máquina.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Permite importar os módulos da raiz mesmo rodando de dentro de test/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import coletar_lance as coleta
import preprocessar as prep


SITEMAP_EXEMPLO = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
  <url>
    <loc>https://www.lance.com.br/flamengo/noticia-a.html</loc>
    <news:news>
      <news:title>Flamengo vence e lidera o Brasileirão</news:title>
      <news:publication_date>2026-09-10T12:00:00Z</news:publication_date>
    </news:news>
    <image:image><image:loc>https://img.lance.com.br/a.jpg</image:loc></image:image>
  </url>
  <url>
    <loc>https://www.lance.com.br/nba/noticia-b.html</loc>
    <news:news>
      <news:title>Lakers vencem na NBA</news:title>
      <news:publication_date>2026-09-10T10:00:00Z</news:publication_date>
    </news:news>
  </url>
  <url>
    <loc>https://www.lance.com.br/fora-de-campo/palmeiras-anuncia-reforco.html</loc>
    <news:news>
      <news:title>Palmeiras anuncia reforço para a temporada</news:title>
      <news:publication_date>2026-09-10T09:00:00Z</news:publication_date>
    </news:news>
  </url>
</urlset>
"""

HTML_EXEMPLO = """
<html><head>
<script type="application/ld+json">
{"@type": "NewsArticle", "headline": "Título do teste",
 "articleSection": "Flamengo", "datePublished": "2026-09-10T12:00:00Z",
 "author": {"name": "Repórter Um"},
 "mainEntityOfPage": {"@id": "https://www.lance.com.br/flamengo/teste.html"}}
</script>
</head><body>
<div class="paywall-content">
  <p class="paragraph-html">O Flamengo confirmou a escalação titular para a
     partida decisiva desta quinta-feira contra o adversário direto na
     tabela de classificação do campeonato nacional deste ano.</p>
  <p class="paragraph-html">CONTINUA APÓS A PUBLICIDADE</p>
  <p class="paragraph-html">O técnico prometeu manter o esquema tático que
     rendeu boas atuações nas últimas rodadas, apostando na velocidade dos
     jogadores mais experientes do elenco profissional durante o confronto.</p>
  <p class="paragraph-html">GANHE R$ 200 em créditos para jogue agora</p>
</div>
</body></html>
"""


class TestSitemap(unittest.TestCase):
    def test_leitura_extrai_campos(self):
        itens = coleta.ler_sitemap(SITEMAP_EXEMPLO)
        self.assertEqual(len(itens), 3)
        primeiro = itens[0]
        self.assertIn("url", primeiro)
        self.assertIn("titulo", primeiro)
        self.assertTrue(primeiro["publicado_em"].endswith("Z"))

    def test_ordenacao_por_data_desc(self):
        itens = coleta.ler_sitemap(SITEMAP_EXEMPLO)
        datas = [item["publicado_em"] for item in itens]
        self.assertEqual(datas, sorted(datas, reverse=True))


class TestFiltroTematico(unittest.TestCase):
    def test_mantem_clube_brasileiro(self):
        item = {"url": "https://www.lance.com.br/flamengo/x.html", "titulo": "Flamengo"}
        self.assertTrue(coleta.eh_futebol_brasileiro(item))

    def test_descarta_nba(self):
        item = {"url": "https://www.lance.com.br/nba/x.html", "titulo": "Lakers"}
        self.assertFalse(coleta.eh_futebol_brasileiro(item))

    def test_fora_de_campo_com_clube_no_titulo(self):
        item = {
            "url": "https://www.lance.com.br/fora-de-campo/x.html",
            "titulo": "Palmeiras anuncia reforço",
        }
        self.assertTrue(coleta.eh_futebol_brasileiro(item))


class TestRuidoEExtracao(unittest.TestCase):
    def test_extrair_artigo_remove_ruido(self):
        artigo = coleta.extrair_artigo(HTML_EXEMPLO, {"url": "x", "titulo": "t"})
        corpo = artigo["texto"].lower()
        self.assertNotIn("publicidade", corpo)
        self.assertNotIn("créditos", corpo)
        self.assertIn("flamengo", corpo)
        self.assertGreaterEqual(artigo["quantidade_palavras"], 50)

    def test_artigo_curto_e_rejeitado(self):
        html = '<div class="paywall-content"><p>Muito curto.</p></div>'
        with self.assertRaises(ValueError):
            coleta.extrair_artigo(html, {"url": "x", "titulo": "t"})

    def test_eh_ruido_reconhece_padroes(self):
        self.assertTrue(coleta.eh_ruido("Continua após a publicidade"))
        self.assertFalse(coleta.eh_ruido("O time venceu a partida."))


class TestPreprocessamento(unittest.TestCase):
    def test_normalizacao_remove_url_email_e_minusculas(self):
        texto = "Veja em https://lance.com.br e email TESTE@lance.com AGORA"
        normalizado = prep.normalizar_texto(texto)
        self.assertEqual(normalizado, normalizado.lower())
        self.assertNotIn("http", normalizado)
        self.assertNotIn("@", normalizado)

    def test_tokenizacao_ignora_numeros_e_pontuacao(self):
        # tokenizar() opera sobre o texto normalizado (já em minúsculas).
        tokens = prep.tokenizar(prep.normalizar_texto("Flamengo 3, Vasco 1! Jogo decisivo."))
        self.assertEqual(tokens, ["flamengo", "vasco", "jogo", "decisivo"])
        for token in tokens:
            self.assertTrue(token.isalpha())

    def test_pipeline_de_uma_noticia(self):
        stemmer = prep.SnowballStemmer("portuguese")
        noticia = {
            "id": "abc123",
            "titulo": "Teste",
            "secao": "Flamengo",
            "publicado_em": "2026-09-10T12:00:00Z",
            "url": "https://www.lance.com.br/flamengo/teste.html",
            "texto": "O Flamengo venceu a partida decisiva contra o adversário "
                     "nesta quinta-feira pelo campeonato brasileiro deste ano.",
        }
        resultado = prep.preprocessar_noticia(noticia, stemmer)
        self.assertGreater(len(resultado["tokens"]), 0)
        self.assertLessEqual(
            len(resultado["tokens_sem_stopwords"]), len(resultado["tokens"])
        )
        self.assertEqual(
            len(resultado["stems"]), len(resultado["tokens_sem_stopwords"])
        )
        self.assertEqual(
            len(resultado["lemas"]), len(resultado["tokens_sem_stopwords"])
        )
        # Stopwords como "o", "a", "contra" não devem sobrar.
        self.assertNotIn("o", resultado["tokens_sem_stopwords"])
        self.assertNotIn("contra", resultado["tokens_sem_stopwords"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
