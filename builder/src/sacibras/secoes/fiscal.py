"""Contas públicas e dívida: resultado primário, juros, nominal, DBGG e DLSP.

As séries de NFSP do Banco Central são NECESSIDADE de financiamento (positivo = déficit).
Aqui tudo vira RESULTADO: superávit positivo, déficit negativo.
"""

from __future__ import annotations

from datetime import date

from sacibras import contas
from sacibras.fontes import bcb_focus, tesouro_rtn
from sacibras.schema import Secao
from sacibras.secoes.base import Contexto, br, cartao, grafico, periodo, serie
from sacibras.tipos import Ponto


def _resultado(nfsp: list[Ponto]) -> list[Ponto]:
    return contas.escalar(nfsp, -1)


def _em_pct_do_pib(mensal: list[Ponto], pib_12m: list[Ponto]) -> list[Ponto]:
    """Soma de 12 meses de um fluxo mensal (R$ milhões) em % do PIB de 12 meses, por mês.

    Só vale a janela com os 12 meses seguidos (mês vazio na fonte não vira soma curta) e
    só nos meses em que há PIB.
    """
    por_mes = dict(mensal)
    pib = dict(pib_12m)
    saida: list[Ponto] = []
    for d, denominador in sorted(pib.items()):
        meses = [date(d.year - (d.month <= k), (d.month - k - 1) % 12 + 1, 1) for k in range(12)]
        if d in por_mes and denominador and all(m in por_mes for m in meses):
            saida.append((d, sum(por_mes[m] for m in meses) / denominador * 100))
    return saida


def montar(ctx: Contexto) -> Secao:
    anos = 20
    primario = _resultado(ctx.sgs("NFSP_PRIMARIO_12M", anos))
    primario_gc = _resultado(ctx.sgs("NFSP_PRIMARIO_GC_12M", anos))
    nominal = _resultado(ctx.sgs("NFSP_NOMINAL_12M", anos))
    juros = ctx.sgs("NFSP_JUROS_12M", anos)
    dbgg = ctx.sgs("DBGG", anos)
    dlsp = ctx.sgs("DLSP", anos)
    primario_mes = contas.escalar(_resultado(ctx.sgs("NFSP_PRIMARIO_MES")), 1 / 1000)

    focus_divida = bcb_focus.mediana_anual_hoje("Dívida bruta do governo geral")
    focus_primario = bcb_focus.mediana_anual_hoje("Resultado primário")
    focus_nominal = bcb_focus.mediana_anual_hoje("Resultado nominal")
    edicao = bcb_focus.data_da_ultima_edicao()
    ctx.memo["focus_divida"] = focus_divida
    ctx.memo["focus_primario"] = focus_primario
    ctx.memo["focus_nominal"] = focus_nominal

    def fim_de_ano(mapa: dict[int, float]) -> list[Ponto]:
        # Só até quatro anos à frente: depois disso poucas casas respondem.
        return [
            (date(ano, 12, 1), valor)
            for ano, valor in sorted(mapa.items())
            if ano <= ctx.hoje.year + 4
        ]

    ano = ctx.hoje.year
    cartoes = [
        cartao(
            "dbgg",
            "Dívida bruta do governo",
            dbgg,
            unidade="% do PIB",
            periodicidade="M",
            casas=1,
            detalhe=(
                f"Focus para o fim de {ano}: {br(focus_divida[ano])} %"
                if ano in focus_divida
                else ""
            ),
            fonte=ctx.fonte_sgs("DBGG"),
            secao="fiscal",
            mini=120,
        ),
        cartao(
            "primario",
            "Resultado primário, 12 meses",
            primario,
            unidade="% do PIB",
            periodicidade="M",
            casas=2,
            detalhe="setor público consolidado; negativo é déficit",
            fonte=ctx.fonte_sgs("NFSP_PRIMARIO_12M"),
            secao="fiscal",
            mini=120,
        ),
        cartao(
            "juros-divida",
            "Juros da dívida, 12 meses",
            juros,
            unidade="% do PIB",
            periodicidade="M",
            casas=2,
            fonte=ctx.fonte_sgs("NFSP_JUROS_12M"),
            secao="fiscal",
            mini=120,
        ),
        cartao(
            "nominal",
            "Resultado nominal, 12 meses",
            nominal,
            unidade="% do PIB",
            periodicidade="M",
            casas=2,
            detalhe="primário menos juros",
            fonte=ctx.fonte_sgs("NFSP_NOMINAL_12M"),
            secao="fiscal",
            mini=120,
        ),
        cartao(
            "dlsp",
            "Dívida líquida do setor público",
            dlsp,
            unidade="% do PIB",
            periodicidade="M",
            casas=1,
            fonte=ctx.fonte_sgs("DLSP"),
            secao="fiscal",
            mini=120,
        ),
    ]
    inicio = date(ctx.hoje.year - anos, 1, 1)
    graficos = [
        grafico(
            "divida",
            "Dívida pública e o que o mercado projeta",
            [
                serie("dbgg", "Dívida bruta do governo geral", dbgg, desde=inicio),
                serie("dlsp", "Dívida líquida do setor público", dlsp, desde=inicio),
                serie(
                    "focus",
                    "Focus: dívida bruta no fim do ano (mediana)",
                    [dbgg[-1], *[p for p in fim_de_ano(focus_divida) if p[0] > dbgg[-1][0]]],
                    papel="consenso",
                ),
            ],
            unidade="% do PIB",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=f"{ctx.fonte_sgs('DBGG', 'DLSP')}; Focus de {periodo(edicao, 'D')}",
            largura="inteira",
        ),
        grafico(
            "primario",
            "Resultado primário em 12 meses",
            [
                serie("consolidado", "Setor público consolidado", primario, desde=inicio),
                serie("gc", "Governo Federal e Banco Central", primario_gc, desde=inicio),
                serie(
                    "focus",
                    "Focus: setor público no fim do ano (mediana)",
                    [
                        primario[-1],
                        *[p for p in fim_de_ano(focus_primario) if p[0] > primario[-1][0]],
                    ],
                    papel="consenso",
                ),
            ],
            unidade="% do PIB (superávit +, déficit −)",
            casas=2,
            periodicidade="M",
            janela_anos=10,
            fonte=f"{ctx.fonte_sgs('NFSP_PRIMARIO_12M', 'NFSP_PRIMARIO_GC_12M')}; Focus",
            nota=(
                "O Banco Central publica a necessidade de financiamento; aqui o sinal está "
                "trocado para ler como resultado."
            ),
        ),
        grafico(
            "nominal",
            "Do primário ao nominal: a conta de juros",
            [
                serie("primario", "Resultado primário", primario, desde=inicio),
                serie("juros", "Juros nominais (despesa)", contas.escalar(juros, -1), desde=inicio),
                serie("nominal", "Resultado nominal", nominal, desde=inicio),
            ],
            unidade="% do PIB, em 12 meses",
            casas=2,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs("NFSP_PRIMARIO_12M", "NFSP_JUROS_12M", "NFSP_NOMINAL_12M"),
            nota="Resultado nominal = primário − juros. Setor público consolidado.",
        ),
        grafico(
            "primario-mensal",
            "Resultado primário mês a mês",
            [serie("mes", "Setor público consolidado", primario_mes, casas=1)],
            tipo="barras",
            unidade="R$ bilhões",
            casas=1,
            periodicidade="M",
            janela_anos=5,
            fonte=ctx.fonte_sgs("NFSP_PRIMARIO_MES"),
        ),
    ]

    # --- Receitas e despesas do Governo Central (RTN, em R$ milhões correntes) ---
    # O site do Tesouro cai de vez em quando: sem o RTN, a seção sai com o resto.
    try:
        rtn = tesouro_rtn.serie_historica()
        pib = ctx.sgs("PIB_12M", anos)
        receita_pib = _em_pct_do_pib(rtn["receita_liquida"], pib)
        despesa_pib = _em_pct_do_pib(rtn["despesa_total"], pib)
        rgps_pib = _em_pct_do_pib(rtn["rgps"], pib)
        pessoal_pib = _em_pct_do_pib(rtn["pessoal"], pib)
        demais_pib = contas.subtrair(contas.subtrair(despesa_pib, rgps_pib), pessoal_pib)
        fonte_rtn = (
            "Tesouro Nacional, Resultado do Tesouro Nacional (série histórica, tabela 1.1); "
            f"PIB: {ctx.fonte_sgs('PIB_12M')}"
        )
        cartoes += [
            cartao(
                "despesa-gc",
                "Despesa do Governo Central, 12 meses",
                despesa_pib,
                unidade="% do PIB",
                periodicidade="M",
                casas=1,
                detalhe="soma de 12 meses sobre o PIB",
                fonte=fonte_rtn,
                procedencia="calculado",
                secao="fiscal",
                mini=120,
            ),
            cartao(
                "previdencia-rgps",
                "Previdência (RGPS), 12 meses",
                rgps_pib,
                unidade="% do PIB",
                periodicidade="M",
                casas=1,
                detalhe="benefícios previdenciários do Regime Geral",
                fonte=fonte_rtn,
                procedencia="calculado",
                secao="fiscal",
                mini=120,
            ),
        ]
        graficos += [
            grafico(
                "receita-despesa",
                "Receita e despesa do Governo Central",
                [
                    serie("receita", "Receita líquida", receita_pib, desde=inicio),
                    serie("despesa", "Despesa total", despesa_pib, desde=inicio),
                ],
                unidade="% do PIB, em 12 meses",
                casas=1,
                periodicidade="M",
                janela_anos=10,
                fonte=fonte_rtn,
                nota=(
                    "Receita líquida de transferências a estados e municípios; soma dos últimos "
                    "12 meses sobre o PIB de 12 meses."
                ),
            ),
            grafico(
                "despesa-composicao",
                "Para onde vai a despesa",
                [
                    serie("rgps", "Benefícios previdenciários", rgps_pib, desde=inicio),
                    serie("pessoal", "Pessoal e encargos sociais", pessoal_pib, desde=inicio),
                    serie("demais", "Demais despesas", demais_pib, desde=inicio),
                ],
                unidade="% do PIB, em 12 meses",
                casas=1,
                periodicidade="M",
                janela_anos=10,
                fonte=fonte_rtn,
                nota="Demais despesas = despesa total menos benefícios previdenciários e pessoal.",
            ),
        ]
    except Exception as erro:
        print(f"    RTN ficou de fora: {str(erro)[:120]}")

    # --- Dívida por indexador (SGS 4173 a 4180: dívida mobiliária federal, posição em carteira) ---
    chaves_divida = [
        "DIVIDA_IDX_SELIC",
        "DIVIDA_IDX_PREFIXADO",
        "DIVIDA_IDX_CAMBIO",
        "DIVIDA_IDX_TR",
        "DIVIDA_IDX_TJLP",
        "DIVIDA_IDX_OUTROS",
        "DIVIDA_IDX_IGPM",
        "DIVIDA_IDX_IGPDI",
    ]
    idx = {c: dict(ctx.sgs(c, anos)) for c in chaves_divida}
    meses_div = sorted(set.intersection(*(set(m) for m in idx.values())))
    selic_div = [(d, idx["DIVIDA_IDX_SELIC"][d]) for d in meses_div]
    pre_div = [(d, idx["DIVIDA_IDX_PREFIXADO"][d]) for d in meses_div]
    cambio_div = [(d, idx["DIVIDA_IDX_CAMBIO"][d]) for d in meses_div]
    resto_div = [
        (d, sum(idx[c][d] for c in ("DIVIDA_IDX_TR", "DIVIDA_IDX_TJLP", "DIVIDA_IDX_OUTROS")))
        for d in meses_div
    ]
    # O BCB não publica o IPCA nessa família (4173 a 4180 não o trazem; o IPCA são as NTN-B).
    # Índices de preços = o que falta para 100 %: IPCA + IGP-M + IGP-DI.
    precos_div = [
        (
            d,
            100
            - sum(
                idx[c][d] for c in chaves_divida if c not in ("DIVIDA_IDX_IGPM", "DIVIDA_IDX_IGPDI")
            ),
        )
        for d in meses_div
    ]
    cartoes.append(
        cartao(
            "divida-selic",
            "Dívida atrelada à Selic",
            selic_div,
            unidade="%",
            periodicidade="M",
            casas=1,
            detalhe="dívida mobiliária federal, posição em carteira",
            fonte=ctx.fonte_sgs("DIVIDA_IDX_SELIC"),
            secao="fiscal",
            mini=120,
        )
    )
    graficos.append(
        grafico(
            "divida-indexador",
            "De que é feita a dívida: participação por indexador",
            [
                serie("selic", "Selic (Over)", selic_div, desde=inicio),
                serie("prefixado", "Prefixado", pre_div, desde=inicio),
                serie("precos", "Índices de preços (IPCA e IGP)", precos_div, desde=inicio),
                serie("cambio", "Câmbio", cambio_div, desde=inicio),
                serie("resto", "TR, TJLP e outros", resto_div, desde=inicio),
            ],
            tipo="empilhado",
            unidade="% da dívida mobiliária federal",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs(*chaves_divida),
            nota=(
                "Dívida mobiliária federal, posição em carteira (títulos do Tesouro Nacional). "
                "As séries de participação por indexador não trazem o IPCA: "
                '"Índices de preços" é o que falta para 100 % depois dos demais indexadores '
                "(IPCA, em sua maior parte, mais IGP-M e IGP-DI)."
            ),
        )
    )

    sinal = "déficit" if primario[-1][1] < 0 else "superávit"
    resumo = (
        f"A dívida bruta está em {br(dbgg[-1][1])} % do PIB ({periodo(dbgg[-1][0], 'M')}). "
        f"O setor público tem {sinal} primário de {br(abs(primario[-1][1]), 2)} % do PIB em "
        "12 meses e paga "
        f"{br(juros[-1][1], 2)} % do PIB em juros: o resultado nominal é de "
        f"{br(nominal[-1][1], 2)} % do PIB."
    )
    return Secao(
        id="fiscal",
        titulo="Contas públicas e dívida",
        resumo=resumo,
        cartoes=cartoes,
        graficos=graficos,
        gerado_em=ctx.agora(),
    )
