"""Mercados: só os preços que contam a história macro — bolsa, dólar, juros futuros."""

from __future__ import annotations

from datetime import date

from sacibras import contas
from sacibras.fontes import b3_indices
from sacibras.schema import LinhaTabela, Secao, Tabela
from sacibras.secoes.base import Contexto, br, cartao, grafico, periodo, serie
from sacibras.tipos import Ponto


def _retornos(pontos: list[Ponto]) -> list[float | None]:
    """[no dia, em 30 dias, no ano, em 12 meses], em %."""
    dia = (pontos[-1][1] / pontos[-2][1] - 1) * 100 if len(pontos) > 1 else None
    return [dia, contas.em_dias(pontos, 30), contas.no_ano(pontos), contas.em_dias(pontos, 365)]


def montar(ctx: Contexto) -> Secao:
    ano = ctx.hoje.year
    ibov = b3_indices.fechamentos("IBOV", ano - 5, ctx.hoje)
    dolar = ctx.sgs("DOLAR", anos=6)
    euro = ctx.sgs("EURO", anos=6)

    indices: dict[str, list[Ponto]] = {"IBOV": [p for p in ibov if p[0].year >= ano - 2]}
    for codigo in b3_indices.INDICES:
        if codigo == "IBOV":
            continue
        try:
            indices[codigo] = b3_indices.fechamentos(codigo, ano - 2, ctx.hoje)
        except Exception as erro:
            print(f"    índice {codigo} ficou de fora: {str(erro)[:100]}")
    quando = ibov[-1][0]
    tabela = Tabela(
        id="indices-b3",
        titulo="Índices da B3",
        subtitulo=f"Fechamento de {periodo(quando, 'D')} e variação",
        colunas=["Pontos", "No dia (%)", "Em 30 dias (%)", "No ano (%)", "Em 12 meses (%)"],
        linhas=[
            LinhaTabela(
                rotulo=b3_indices.INDICES[codigo],
                valores=[pontos[-1][1], *_retornos(pontos)],
                unidade="",
                casas=1,
            )
            for codigo, pontos in indices.items()
            if len(pontos) > 2
        ],
        fonte="B3, estatísticas históricas dos índices",
        nota=(
            "Os setoriais mostram onde o juro e o câmbio pesam: financeiro, consumo e "
            "imobiliário sentem a Selic; materiais básicos, o dólar e as commodities."
        ),
    )

    ibov_ano = contas.no_ano(ibov)
    dolar_ano = contas.no_ano(dolar)
    # Ibovespa em dólares: o índice dividido pela cotação do dia.
    mapa_dolar = dict(dolar)
    ibov_usd = [(d, v / mapa_dolar[d]) for d, v in ibov if d in mapa_dolar]
    cartoes = [
        cartao(
            "ibovespa",
            "Ibovespa",
            ibov,
            unidade="pontos",
            periodicidade="D",
            casas=0,
            detalhe=f"no ano: {br(ibov_ano or 0)} %",
            fonte="B3",
            procedencia="mercado",
            secao="mercados",
            mini=250,
        ),
        cartao(
            "dolar",
            "Dólar",
            dolar,
            unidade="R$",
            periodicidade="D",
            casas=4,
            detalhe=f"no ano: {br(dolar_ano or 0)} %",
            fonte=ctx.fonte_sgs("DOLAR"),
            procedencia="mercado",
            secao="mercados",
            mini=250,
        ),
        cartao(
            "euro",
            "Euro",
            euro,
            unidade="R$",
            periodicidade="D",
            casas=4,
            detalhe=f"no ano: {br(contas.no_ano(euro) or 0)} %",
            fonte=ctx.fonte_sgs("EURO"),
            procedencia="mercado",
            secao="mercados",
            mini=250,
        ),
        cartao(
            "ibovespa-dolar",
            "Ibovespa em dólares",
            ibov_usd,
            unidade="pontos",
            periodicidade="D",
            casas=0,
            detalhe=f"no ano: {br(contas.no_ano(ibov_usd) or 0)} %",
            fonte=f"B3; {ctx.fonte_sgs('DOLAR')}",
            procedencia="calculado",
            secao="mercados",
            mini=250,
        ),
    ]
    base = date(ano - 1, 1, 1)
    comparados = [
        serie(c.lower(), b3_indices.INDICES[c], contas.base_100(indices[c], base), desde=base)
        for c in ("IBOV", "SMLL", "IFIX", "IDIV")
        if c in indices
    ]
    graficos = [
        grafico(
            "ibovespa",
            "Ibovespa",
            [serie("ibov", "Ibovespa", ibov, casas=0)],
            unidade="pontos",
            casas=0,
            periodicidade="D",
            janela_anos=1,
            fonte="B3, estatísticas históricas do Ibovespa",
        ),
        grafico(
            "dolar",
            "Dólar e euro",
            [serie("dolar", "Dólar", dolar, casas=4), serie("euro", "Euro", euro, casas=4)],
            unidade="R$",
            casas=2,
            periodicidade="D",
            janela_anos=1,
            fonte=ctx.fonte_sgs("DOLAR", "EURO"),
        ),
        grafico(
            "indices-comparados",
            "Bolsa por dentro: grandes, pequenas, fundos imobiliários e dividendos",
            comparados,
            unidade=f"índice, {periodo(comparados[0].pontos[0][0], 'D')} = 100",
            casas=1,
            periodicidade="D",
            fonte="B3, estatísticas históricas dos índices",
        ),
        grafico(
            "ibovespa-dolar",
            "Ibovespa em dólares",
            [serie("ibov-usd", "Ibovespa em dólares", ibov_usd, casas=0)],
            unidade="pontos ÷ R$/US$",
            casas=0,
            periodicidade="D",
            janela_anos=5,
            fonte=f"B3; {ctx.fonte_sgs('DOLAR')}",
            nota="Como o estrangeiro enxerga a bolsa brasileira: o índice dividido pelo dólar do dia.",
        ),
    ]
    resumo = (
        f"O Ibovespa fechou {periodo(quando, 'D')} em {br(ibov[-1][1], 0)} pontos "
        f"({br(ibov_ano or 0)} % no ano) e o dólar a R$ {br(dolar[-1][1], 2)} "
        f"({br(dolar_ano or 0)} % no ano)."
    )
    return Secao(
        id="mercados",
        titulo="Mercados",
        resumo=resumo,
        cartoes=cartoes,
        graficos=graficos,
        tabelas=[tabela],
        gerado_em=ctx.agora(),
    )
