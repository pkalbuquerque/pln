#!/usr/bin/env python3
"""Executa coleta e pré-processamento em uma única chamada."""

import argparse

from coletar_lance import coletar, salvar
from preprocessar import processar


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limite", type=int, default=30)
    parser.add_argument("--acumular", action="store_true")
    args = parser.parse_args()
    noticias, erros, total = coletar(limite=args.limite)
    caminho = salvar(noticias, erros, total, args.acumular)
    _, estatisticas = processar(caminho)
    print(f"Pipeline concluído: {len(noticias)} coletadas, {len(erros)} erros, {estatisticas['total_documentos']} documentos na base.")


if __name__ == "__main__":
    main()
