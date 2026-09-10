#!/usr/bin/env python3
"""Executa coleta e pré-processamento em uma única chamada."""

import argparse

from coletar_lance import FONTES_SITEMAP, coletar, salvar
from preprocessar import processar


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limite", type=int, default=30)
    parser.add_argument("--acumular", action="store_true")
    parser.add_argument(
        "--fonte", choices=sorted(FONTES_SITEMAP), default="recentes",
        help="'hoje' = notícias do dia; 'recentes' = artigos de vários dias (padrão)",
    )
    args = parser.parse_args()
    sitemap = FONTES_SITEMAP[args.fonte]
    noticias, erros, total = coletar(limite=args.limite, sitemap=sitemap)
    caminho = salvar(noticias, erros, total, args.acumular, sitemap=sitemap)
    _, estatisticas = processar(caminho)
    print(f"Pipeline concluído: {len(noticias)} coletadas, {len(erros)} erros, {estatisticas['total_documentos']} documentos na base.")


if __name__ == "__main__":
    main()
