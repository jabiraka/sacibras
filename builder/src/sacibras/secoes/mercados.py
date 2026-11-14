"""Mercados: só os preços que contam a história macro — bolsa, dólar, juros futuros."""

from __future__ import annotations

from datetime import date

from sacibras import contas
from sacibras.config import usar_b3
from sacibras.fontes import b3_derivativos, b3_indices, ipeadata
from sacibras.schema import LinhaTabela, Secao, Tabela
from sacibras.secoes.base import Contexto, br, cartao, grafico, periodo, serie
from sacibras.tipos import Ponto


def _retornos(pontos: list[Ponto]) -> list[float | None]:
    """[no dia, em 30 dias, no ano, em 12 meses], em %."""
    dia = (pontos[-1][1] / pontos[-2][1] - 1) * 100 if len(pontos) > 1 else None
    return [dia, contas.em_dias(pontos, 30), contas.no_ano(pontos), contas.em_dias(pontos, 365)]


# (código na B3, nome, unidade, divisor do preço, casas, quantos vencimentos)
FUTUROS: list[tuple[str, str, str, float, int, int]] = [
    ("DOL", "Dólar futuro", "R$", 1000, 4, 1),
    ("IND", "Ibovespa futuro", "pontos", 1, 0, 1),
    ("BGI", "Boi gordo", "R$ por arroba", 1, 2, 1),
    ("CCM", "Milho", "R$ por saca", 1, 2, 1),
    ("SJC", "Soja", "US$ por saca", 1, 2, 1),
    ("ICF", "Café arábica", "US$ por saca", 1, 2, 1),
]


def _tabela_futuros(ctx: Contexto) -> Tabela | None:
    """O vencimento mais negociado de cada futuro, e os juros futuros de janeiro."""
    linhas: list[LinhaTabela] = []
    for venc, taxa in ctx.memo.get("curva_di", []):
        if venc.month == 1 and venc.year <= ctx.hoje.year + 5:
            linhas.append(
                LinhaTabela(
                    rotulo=f"Juro futuro (DI) para {periodo(venc, 'M')}",
                    valores=[taxa, None],
                    unidade="% a.a.",
                    casas=2,
                )
            )
    for codigo, nome, unidade, divisor, casas, _ in FUTUROS:
        try:
            contratos = [c for c in b3_derivativos.futuros(codigo) if c.preco]
        except Exception as erro:
            print(f"    futuro {codigo} ficou de fora: {str(erro)[:100]}")
            continue
        if not contratos:
            continue
        # O vencimento com mais contratos em aberto é o que forma preço.
        c = max(contratos[:4], key=lambda x: x.em_aberto)
        preco = float(c.preco or 0) / divisor
        variacao = (
            (c.ultimo / c.ajuste_anterior - 1) * 100 if c.ultimo and c.ajuste_anterior else None
        )
        linhas.append(
            LinhaTabela(
                rotulo=f"{nome}, vence em {periodo(c.vencimento, 'D')}",
                valores=[preco, variacao],
                unidade=unidade,
                casas=casas,
            )
        )
    if not linhas:
        return None
    return Tabela(
        id="futuros",
        titulo="Futuros: o preço de amanhã negociado hoje",
        subtitulo="Último negócio do vencimento com mais contratos em aberto",
        colunas=["Último", "Contra o ajuste anterior (%)"],
        linhas=linhas,
        fonte="B3, cotações de derivativos (atraso de 15 minutos no pregão)",
        nota=(
            "Juro futuro é a taxa prefixada até a data; dólar e Ibovespa futuros embutem o "
            "juro até o vencimento; boi, milho, soja e café antecipam preços de alimentos."
        ),
    )


def montar(ctx: Contexto) -> Secao:
    ano = ctx.hoje.year
    b3 = usar_b3()
    dolar = ctx.sgs("DOLAR", anos=6)
    euro = ctx.sgs("EURO", anos=6)
    if b3:
        ibov = b3_indices.fechamentos("IBOV", ano - 5, ctx.hoje)
        fonte_ibov = "B3, estatísticas históricas do Ibovespa"
    else:
        ibov = ipeadata.serie(ipeadata.IBOVESPA, date(ano - 5, 1, 1))
        fonte_ibov = "IPEADATA (série GM366_IBVSP366, fechamento do Ibovespa)"

    indices: dict[str, list[Ponto]] = {"IBOV": [p for p in ibov if p[0].year >= ano - 2]}
    tabelas: list[Tabela] = []
    quando = ibov[-1][0]
    if b3:
        for codigo in b3_indices.INDICES:
            if codigo == "IBOV":
                continue
            try:
                indices[codigo] = b3_indices.fechamentos(codigo, ano - 2, ctx.hoje)
            except Exception as erro:
                print(f"    índice {codigo} ficou de fora: {str(erro)[:100]}")
        futuros = _tabela_futuros(ctx)
        if futuros:
            tabelas.append(futuros)
        tabelas.append(
            Tabela(
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
            fonte=fonte_ibov,
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
            casas=2,
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
            casas=2,
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
            fonte=f"{fonte_ibov}; {ctx.fonte_sgs('DOLAR')}",
            procedencia="calculado",
            secao="mercados",
            mini=250,
        ),
    ]
    variacoes = Tabela(
        id="variacoes",
        titulo="Bolsa e câmbio em diferentes prazos",
        subtitulo=f"Variação até {periodo(quando, 'D')}",
        colunas=["Último", "No dia (%)", "Em 30 dias (%)", "No ano (%)", "Em 12 meses (%)"],
        linhas=[
            LinhaTabela(rotulo=nome, valores=[p[-1][1], *_retornos(p)], unidade=u, casas=2)
            for nome, p, u in [
                ("Ibovespa", ibov, "pontos"),
                ("Ibovespa em dólares", ibov_usd, "pontos"),
                ("Dólar", dolar, "R$"),
                ("Euro", euro, "R$"),
            ]
        ],
        fonte=f"{fonte_ibov}; {ctx.fonte_sgs('DOLAR', 'EURO')}",
    )
    tabelas.insert(0, variacoes)
    graficos = [
        grafico(
            "ibovespa",
            "Ibovespa",
            [serie("ibov", "Ibovespa", ibov, casas=0)],
            unidade="pontos",
            casas=0,
            periodicidade="D",
            janela_anos=1,
            fonte=fonte_ibov,
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
            "ibovespa-dolar",
            "Ibovespa em dólares",
            [serie("ibov-usd", "Ibovespa em dólares", ibov_usd, casas=0)],
            unidade="pontos ÷ R$/US$",
            casas=0,
            periodicidade="D",
            janela_anos=5,
            fonte=f"{fonte_ibov}; {ctx.fonte_sgs('DOLAR')}",
            nota=(
                "Como o estrangeiro enxerga a bolsa brasileira: o índice dividido pelo dólar "
                "do dia."
            ),
        ),
    ]
    if b3 and len(indices) > 1:
        base = date(ano - 1, 1, 1)
        comparados = [
            serie(c.lower(), b3_indices.INDICES[c], contas.base_100(indices[c], base), desde=base)
            for c in ("IBOV", "SMLL", "IFIX", "IDIV")
            if c in indices
        ]
        graficos.insert(
            2,
            grafico(
                "indices-comparados",
                "Bolsa por dentro: grandes, pequenas, fundos imobiliários e dividendos",
                comparados,
                unidade=f"índice, {periodo(comparados[0].pontos[0][0], 'D')} = 100",
                casas=1,
                periodicidade="D",
                fonte="B3, estatísticas históricas dos índices",
            ),
        )
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
        tabelas=tabelas,
        gerado_em=ctx.agora(),
    )
