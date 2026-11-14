"""`sacibras build` gera os JSONs do site; `sacibras fontes-smoke` testa cada fonte."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SAIDA_PADRAO = Path(__file__).resolve().parents[3] / "web" / "public" / "data"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sacibras", description=__doc__)
    comandos = parser.add_subparsers(dest="comando", required=True)
    build = comandos.add_parser("build", help="chama as fontes e grava os JSONs do site")
    build.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    build.add_argument("--secao", action="append", help="só esta seção (pode repetir)")
    build.add_argument(
        "--tolerante",
        action="store_true",
        help="sai com 0 mesmo se alguma seção falhar (o site publica o resto)",
    )
    smoke = comandos.add_parser("fontes-smoke", help="uma chamada mínima a cada fonte")
    smoke.add_argument("--markdown", action="store_true", help="imprime a tabela em Markdown")
    args = parser.parse_args(argv)

    if args.comando == "build":
        from sacibras import busca
        from sacibras.construir import construir

        print(f"Gerando em {args.saida}")
        painel = construir(args.saida, args.secao)
        try:  # o índice da busca lê os JSONs gravados; sem ele, o site só fica sem busca
            print(f"  busca: {busca.gravar(args.saida)} itens")
        except Exception as erro:
            print(f"  aviso: índice da busca não gravado ({erro})")
        falhas = [s.id for s in painel.secoes if s.erro]
        if falhas:
            print(f"Seções com falha: {', '.join(falhas)}")
            return 0 if args.tolerante else 1
        return 0

    from sacibras.fontes.smoke import rodar

    return rodar(markdown=args.markdown)


if __name__ == "__main__":
    sys.exit(main())
