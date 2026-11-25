"""`sacibras build` gera os JSONs do site; `sacibras anterior` traz os do site no ar (para o
build manter o que a fonte não refez); `sacibras fontes-smoke` testa cada fonte;
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
    anterior = comandos.add_parser(
        "anterior", help="traz os JSONs do site no ar para a pasta (a rodada anterior)"
    )
    anterior.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    anterior.add_argument("--site", help="endereço da pasta data/ do site no ar")
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
    tramitacao = comandos.add_parser(
        "tramitacao", help="se os projetos de lei mostrados no painel andaram no Congresso"
    )
    tramitacao.add_argument(
        "--saida", type=Path, help="grava aqui a tabela do que mudou (vazio se nada mudou)"
    )
    smoke = comandos.add_parser("fontes-smoke", help="uma chamada mínima a cada fonte")
    smoke.add_argument("--markdown", action="store_true", help="imprime a tabela em Markdown")
    args = parser.parse_args(argv)

    if args.comando == "build":
        from sacibras import busca, glossario, links
        from sacibras.construir import construir

        print(f"Gerando em {args.saida}")
        painel = construir(args.saida, args.secao)
        try:  # o índice da busca lê os JSONs gravados; sem ele, o site só fica sem busca
            print(f"  busca: {busca.gravar(args.saida)} itens")
        except Exception as erro:
            print(f"  aviso: índice da busca não gravado ({erro})")
        print(f"  glossário: {glossario.gravar(args.saida)} termos")
        print(f"  endereços das fontes: {links.gravar(args.saida)} regras")
        sem, gerais = links.auditar(args.saida)
        for texto in sem:
            print(f"  aviso: fonte sem endereço: {texto[:150]}")
        for texto in gerais:
            print(f"  aviso: fonte só com a página geral: {texto[:150]}")
        for x in leituras_.pendentes(date.today()):
            situacao = leituras_.situacao(x, date.today())
            print(f"  aviso: releitura {situacao} ({x.reler_ate:%d/%m/%Y}): {x.o_que}")
        com_erro = [s for s in painel.secoes if s.erro]
        if args.falhas:
            args.falhas.write_text(_falhas_md(painel.secoes), encoding="utf-8")
        if com_erro:
            print(f"Seções com falha: {', '.join(s.id for s in com_erro)}")
            return 0 if args.tolerante else 1
        return 0

    if args.comando == "anterior":
        from sacibras import anterior as anterior_

        try:
            gravados = anterior_.trazer(args.saida, args.site or anterior_.SITE)
        except Exception as erro:  # sem a rodada anterior, o build só não tem o que manter
            print(f"aviso: rodada anterior não veio do site ({erro})")
            return 0
        print(f"Rodada anterior: {len(gravados)} arquivos em {args.saida}")
        return 0

    if args.comando == "leituras":
        hoje = date.today()
        print(leituras_.tabela(hoje, todas=args.todas))
        if args.saida:
            pendente = bool(leituras_.pendentes(hoje))
            args.saida.write_text(leituras_.tabela(hoje) + "\n" if pendente else "", "utf-8")
        vencidas = [x for x in leituras_.LEITURAS if leituras_.situacao(x, hoje) == "vencida"]
        return 1 if args.estrito and vencidas else 0

    if args.comando == "tramitacao":
        from sacibras import tramitacao as tramitacao_

        tabela = tramitacao_.olhar()
        print(tabela or "Nenhum projeto andou desde a última leitura.")
        if args.saida:
            args.saida.write_text(tabela + "\n" if tabela else "", "utf-8")
        return 0

    from sacibras.fontes.smoke import rodar

    return rodar(markdown=args.markdown)


def _falhas_md(secoes: list[ItemSecao]) -> str:
    """O que falhou, em Markdown, para a issue do workflow (vazio se nada).

    Uma linha de tabela por seção que falhou inteira; depois, em lista, as seções que saíram
    com parte dos números da rodada anterior."""
    com_erro = [s for s in secoes if s.erro]
    com_mantidos = [s for s in secoes if s.mantidos and not s.erro]
    linhas: list[str] = []
    if com_erro:
        linhas += ["| Seção | Ficou no site? | Erro |", "| --- | --- | --- |"]
        for s in com_erro:
            erro = " ".join(s.erro.split()).replace("|", "\\|")
            ficou = "sim, a versão anterior" if s.ok else "não"
            linhas.append(f"| {s.titulo} (`{s.id}`) | {ficou} | {erro} |")
    if com_mantidos:
        if linhas:
            linhas.append("")
        linhas.append("Com parte dos números da rodada anterior (uma fonte da seção falhou):")
        linhas.append("")
        linhas += [f"- {s.titulo} (`{s.id}`): {', '.join(s.mantidos)}" for s in com_mantidos]
    return "\n".join(linhas) + "\n" if linhas else ""


if __name__ == "__main__":
    sys.exit(main())
