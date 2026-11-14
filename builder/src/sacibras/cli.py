"""`sacibras build` gera os JSONs do site; `sacibras fontes-smoke` testa cada fonte;
`sacibras leituras` diz o que foi lido à mão e precisa ser lido de novo."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from sacibras import leituras as leituras_

if TYPE_CHECKING:
    from sacibras.schema import ItemSecao

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
    build.add_argument(
        "--falhas",
        type=Path,
        help="grava aqui, em Markdown, as seções que falharam (vazio se nenhuma)",
    )
    leituras = comandos.add_parser("leituras", help="prazos para reler leis e relatórios")
    leituras.add_argument("--todas", action="store_true", help="lista também as em dia")
    leituras.add_argument(
        "--estrito", action="store_true", help="sai com 1 se alguma estiver vencida"
    )
    leituras.add_argument(
        "--saida",
        type=Path,
        help="grava aqui a tabela das pendentes em Markdown (vazio se nenhuma)",
    )
    smoke = comandos.add_parser("fontes-smoke", help="uma chamada mínima a cada fonte")
    smoke.add_argument("--markdown", action="store_true", help="imprime a tabela em Markdown")
    args = parser.parse_args(argv)

    if args.comando == "build":
        from sacibras import busca, glossario
        from sacibras.construir import construir

        print(f"Gerando em {args.saida}")
        painel = construir(args.saida, args.secao)
        try:  # o índice da busca lê os JSONs gravados; sem ele, o site só fica sem busca
            print(f"  busca: {busca.gravar(args.saida)} itens")
        except Exception as erro:
            print(f"  aviso: índice da busca não gravado ({erro})")
        print(f"  glossário: {glossario.gravar(args.saida)} termos")
        for x in leituras_.pendentes(date.today()):
            situacao = leituras_.situacao(x, date.today())
            print(f"  aviso: releitura {situacao} ({x.reler_ate:%d/%m/%Y}): {x.o_que}")
        com_erro = [s for s in painel.secoes if s.erro]
        if args.falhas:
            args.falhas.write_text(_falhas_md(com_erro), encoding="utf-8")
        if com_erro:
            print(f"Seções com falha: {', '.join(s.id for s in com_erro)}")
            return 0 if args.tolerante else 1
        return 0

    if args.comando == "leituras":
        hoje = date.today()
        print(leituras_.tabela(hoje, todas=args.todas))
        if args.saida:
            pendente = bool(leituras_.pendentes(hoje))
            args.saida.write_text(leituras_.tabela(hoje) + "\n" if pendente else "", "utf-8")
        vencidas = [x for x in leituras_.LEITURAS if leituras_.situacao(x, hoje) == "vencida"]
        return 1 if args.estrito and vencidas else 0

    from sacibras.fontes.smoke import rodar

    return rodar(markdown=args.markdown)


def _falhas_md(com_erro: list[ItemSecao]) -> str:
    """As seções que falharam, em Markdown, para a issue do workflow (vazio se nenhuma)."""
    if not com_erro:
        return ""
    linhas = [
        "| Seção | Ficou no site? | Erro |",
        "| --- | --- | --- |",
    ]
    for s in com_erro:
        erro = " ".join(s.erro.split()).replace("|", "\\|")
        ficou = "sim, a versão anterior" if s.ok else "não"
        linhas.append(f"| {s.titulo} (`{s.id}`) | {ficou} | {erro} |")
    return "\n".join(linhas) + "\n"


if __name__ == "__main__":
    sys.exit(main())
