"""Atividade: PIB trimestral, IBC-Br, indústria, varejo, serviços e confiança."""

from __future__ import annotations

from datetime import date

from sacibras import contas
from sacibras.fontes import ibge_sidra
from sacibras.schema import LinhaTabela, Secao, Tabela
from sacibras.secoes.base import Contexto, br, cartao, grafico, periodo, serie

# SIDRA 5932, classificação 11255 (setores e subsetores). Conferido em 14/11/2026.
COMPONENTES = {
    "90707": "PIB",
    "93404": "Consumo das famílias",
    "93405": "Consumo do governo",
    "93406": "Investimento (FBCF)",
    "93407": "Exportações",
    "93408": "Importações",
    "90687": "Agropecuária",
    "90691": "Indústria",
    "90696": "Serviços",
}
FONTE_PIB = "IBGE, Contas Nacionais Trimestrais (SIDRA 5932)"


def montar(ctx: Contexto) -> Secao:
    cats = ",".join(COMPONENTES)
    pib_tt = ibge_sidra.series(
        5932, 6564, classificacao=f"c11255/{cats}", por="Setores", trimestral=True
    )
    pib_aa = ibge_sidra.series(
        5932, 6561, classificacao=f"c11255/{cats}", por="Setores", trimestral=True
    )
    pib_4t = ibge_sidra.series(5932, 6562, classificacao="c11255/90707", trimestral=True)[""]
    tt, aa = pib_tt["90707"], pib_aa["90707"]
    ctx.memo["pib_aa"] = aa
    ctx.memo["pib_4t"] = pib_4t

    ibc = ctx.sgs("IBCBR_DESSAZ")
    ibc_bruto = ctx.sgs("IBCBR")
    ibc_12m = contas.variacao(
        contas.soma_movel(ibc_bruto, 12), 12
    )  # média de 12 meses contra os 12 anteriores
    ibc_mm = contas.variacao(ibc, 1)

    pim = ibge_sidra.serie(8888, 12607, classificacao="c544/129314")
    pmc = ibge_sidra.serie(8880, 7170, classificacao="c11046/56734")
    pmc_ampliado = ibge_sidra.serie(8881, 7170, classificacao="c11046/56736")
    pms = ibge_sidra.serie(5906, 7168, classificacao="c11046/56726")
    confianca = ctx.sgs("CONFIANCA_CONSUMIDOR")
    uci = ctx.sgs("UCI_INDUSTRIA")

    trimestre = periodo(tt[-1][0], "T")
    cartoes = [
        cartao(
            "pib-tt",
            "PIB no trimestre",
            tt,
            unidade="%",
            periodicidade="T",
            casas=1,
            detalhe=f"contra o trimestre anterior; {br(aa[-1][1])} % em um ano",
            fonte=FONTE_PIB,
            secao="atividade",
            mini=20,
        ),
        cartao(
            "pib-4t",
            "PIB em quatro trimestres",
            pib_4t,
            unidade="%",
            periodicidade="T",
            casas=1,
            fonte=FONTE_PIB,
            secao="atividade",
            mini=24,
        ),
        cartao(
            "ibcbr",
            "IBC-Br, 12 meses",
            ibc_12m,
            unidade="%",
            periodicidade="M",
            casas=1,
            detalhe=f"no mês, com ajuste: {br(ibc_mm[-1][1])} %",
            fonte=ctx.fonte_sgs("IBCBR", "IBCBR_DESSAZ"),
            procedencia="calculado",
            secao="atividade",
            mini=60,
        ),
        cartao(
            "industria",
            "Indústria (PIM), no mês",
            contas.variacao(pim, 1),
            unidade="%",
            periodicidade="M",
            casas=1,
            detalhe=f"em um ano: {br(contas.variacao(pim, 12)[-1][1])} %",
            fonte="IBGE, PIM-PF (SIDRA 8888)",
            secao="atividade",
            mini=24,
        ),
        cartao(
            "varejo",
            "Varejo (PMC), no mês",
            contas.variacao(pmc, 1),
            unidade="%",
            periodicidade="M",
            casas=1,
            detalhe=f"em um ano: {br(contas.variacao(pmc, 12)[-1][1])} %",
            fonte="IBGE, PMC (SIDRA 8880)",
            secao="atividade",
            mini=24,
        ),
        cartao(
            "servicos",
            "Serviços (PMS), no mês",
            contas.variacao(pms, 1),
            unidade="%",
            periodicidade="M",
            casas=1,
            detalhe=f"em um ano: {br(contas.variacao(pms, 12)[-1][1])} %",
            fonte="IBGE, PMS (SIDRA 5906)",
            secao="atividade",
            mini=24,
        ),
    ]

    inicio = date(ctx.hoje.year - 12, 1, 1)
    base = date(ctx.hoje.year - 5, 1, 1)
    graficos = [
        grafico(
            "pib-trimestral",
            "PIB: crescimento a cada trimestre",
            [
                serie("tt", "Contra o trimestre anterior (com ajuste sazonal)", tt, desde=inicio),
                serie("aa", "Contra o mesmo trimestre do ano anterior", aa, desde=inicio),
            ],
            tipo="barras",
            unidade="%",
            casas=1,
            periodicidade="T",
            janela_anos=5,
            fonte=FONTE_PIB,
        ),
        grafico(
            "pib-demanda",
            "PIB pela demanda: consumo, investimento e comércio exterior",
            [
                serie("familias", "Consumo das famílias", pib_aa["93404"], desde=inicio),
                serie("fbcf", "Investimento (FBCF)", pib_aa["93406"], desde=inicio),
                serie("governo", "Consumo do governo", pib_aa["93405"], desde=inicio),
                serie("exportacoes", "Exportações", pib_aa["93407"], desde=inicio),
            ],
            unidade="% em um ano",
            casas=1,
            periodicidade="T",
            janela_anos=5,
            fonte=FONTE_PIB,
        ),
        grafico(
            "ibcbr",
            "IBC-Br: a prévia mensal do PIB",
            [serie("ibc", "IBC-Br com ajuste sazonal", ibc, desde=inicio)],
            unidade="índice",
            casas=1,
            periodicidade="M",
            janela_anos=5,
            fonte=ctx.fonte_sgs("IBCBR_DESSAZ"),
        ),
        grafico(
            "setores-mensais",
            "Indústria, varejo e serviços",
            [
                serie("pim", "Indústria (PIM-PF)", contas.base_100(pim, base), desde=base),
                serie("pmc", "Varejo restrito (PMC)", contas.base_100(pmc, base), desde=base),
                serie(
                    "pmca",
                    "Varejo ampliado (PMC)",
                    contas.base_100(pmc_ampliado, base),
                    desde=base,
                ),
                serie("pms", "Serviços (PMS)", contas.base_100(pms, base), desde=base),
            ],
            unidade=f"índice, {periodo(base, 'M')} = 100",
            casas=1,
            periodicidade="M",
            fonte="IBGE, SIDRA 8888, 8880, 8881 e 5906 (volume, com ajuste sazonal)",
            nota="Os quatro índices foram postos na mesma base para se compararem.",
        ),
        grafico(
            "confianca",
            "Confiança do consumidor",
            [serie("icc", "Índice de Confiança do Consumidor", confianca, desde=inicio)],
            unidade="índice",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs("CONFIANCA_CONSUMIDOR"),
        ),
        grafico(
            "uci",
            "Uso da capacidade instalada na indústria",
            [serie("uci", "Indústria de transformação", uci, desde=inicio)],
            unidade="%",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=f"{ctx.fonte_sgs('UCI_INDUSTRIA')} (FGV)",
        ),
    ]

    tabela = Tabela(
        id="pib-componentes",
        titulo=f"PIB do {trimestre}, por componente",
        colunas=["Contra o trimestre anterior (%)", "Em um ano (%)"],
        linhas=[
            LinhaTabela(
                rotulo=nome,
                valores=[
                    pib_tt[codigo][-1][1] if codigo in pib_tt else None,
                    pib_aa[codigo][-1][1] if codigo in pib_aa else None,
                ],
                unidade="",
                casas=1,
            )
            for codigo, nome in COMPONENTES.items()
        ],
        fonte=f"{FONTE_PIB}, variáveis 6564 e 6561",
    )
    resumo = (
        f"O PIB cresceu {br(tt[-1][1])} % no {trimestre} contra o trimestre anterior e "
        f"{br(aa[-1][1])} % contra um ano antes; em quatro trimestres acumula "
        f"{br(pib_4t[-1][1])} %."
    )
    return Secao(
        id="atividade",
        titulo="Atividade",
        resumo=resumo,
        cartoes=cartoes,
        graficos=graficos,
        tabelas=[tabela],
        gerado_em=ctx.agora(),
    )
