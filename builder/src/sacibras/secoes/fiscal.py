"""Contas públicas e dívida: resultado primário, juros, nominal, DBGG e DLSP.

As séries de NFSP do Banco Central são NECESSIDADE de financiamento (positivo = déficit).
Aqui tudo vira RESULTADO: superávit positivo, déficit negativo.
"""

from __future__ import annotations

from datetime import date

from sacibras import contas
from sacibras.fontes import bcb_focus
from sacibras.schema import Secao
from sacibras.secoes.base import Contexto, br, cartao, grafico, periodo, serie
from sacibras.tipos import Ponto


def _resultado(nfsp: list[Ponto]) -> list[Ponto]:
    return contas.escalar(nfsp, -1)


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
