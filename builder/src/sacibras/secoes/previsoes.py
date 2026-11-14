"""Previsões: o consenso do mercado (Focus), como ele mudou, e o FMI ao lado.

Nesta fase a página mostra só previsões de terceiros, cada uma com a fonte. Os modelos
próprios (PIB agora, IPCA, dívida) entram na Fase 5, sempre ao lado destas.
"""

from __future__ import annotations

from datetime import date, timedelta

from sacibras.fontes import bcb_focus, fmi
from sacibras.schema import Grafico, LinhaTabela, Secao, Tabela
from sacibras.secoes.base import Contexto, br, cartao, grafico, periodo, serie
from sacibras.tipos import Ponto

# (indicador do Focus, detalhe, rótulo, unidade, casas)
LINHAS: list[tuple[str, str | None, str, str, int]] = [
    ("IPCA", None, "IPCA", "% no ano", 2),
    ("PIB Total", None, "PIB", "% no ano", 2),
    ("Selic", None, "Selic no fim do ano", "% a.a.", 2),
    ("Câmbio", None, "Dólar no fim do ano", "R$", 2),
    ("Dívida bruta do governo geral", None, "Dívida bruta", "% do PIB", 1),
    ("Resultado primário", None, "Resultado primário", "% do PIB", 2),
    ("Resultado nominal", None, "Resultado nominal", "% do PIB", 2),
    ("Conta corrente", None, "Conta corrente", "US$ bilhões", 1),
    ("Balança comercial", "Saldo", "Saldo comercial", "US$ bilhões", 1),
    ("Investimento direto no país", None, "Investimento direto no país", "US$ bilhões", 1),
    ("Taxa de desocupação", None, "Desocupação", "%", 2),
]


def _anual(pontos: list[Ponto]) -> list[Ponto]:
    return [(date(d.year, 1, 1), v) for d, v in pontos]


def montar(ctx: Contexto) -> Secao:
    ano = ctx.hoje.year
    anos = [ano, ano + 1, ano + 2, ano + 3]
    edicao = bcb_focus.data_da_ultima_edicao()
    medianas: dict[str, dict[int, float]] = {}
    linhas: list[LinhaTabela] = []
    for indicador, detalhe, rotulo, unidade, casas in LINHAS:
        try:
            mapa = bcb_focus.mediana_anual_hoje(indicador, detalhe=detalhe)
        except Exception:
            mapa = {}
        if not mapa:
            continue
        medianas[indicador] = mapa
        linhas.append(
            LinhaTabela(
                rotulo=rotulo,
                valores=[mapa.get(a) for a in anos],
                unidade=unidade,
                casas=casas,
            )
        )
    tabela = Tabela(
        id="focus",
        titulo="O que o mercado espera: Focus",
        subtitulo=f"Mediana das projeções coletadas até {periodo(edicao, 'D')}",
        colunas=[str(a) for a in anos],
        linhas=linhas,
        fonte="Banco Central, Relatório Focus (ExpectativasMercadoAnuais)",
        nota=(
            "Consenso não é previsão nossa: é a mediana do que cerca de uma centena de "
            "instituições informou ao Banco Central."
        ),
    )

    desde = ctx.hoje - timedelta(days=730)
    graficos: list[Grafico] = []
    for indicador, titulo, unidade in [
        ("IPCA", "Como mudou a aposta para o IPCA", "% no ano"),
        ("PIB Total", "Como mudou a aposta para o PIB", "% no ano"),
        ("Selic", "Como mudou a aposta para a Selic no fim do ano", "% a.a."),
        ("Câmbio", "Como mudou a aposta para o dólar no fim do ano", "R$/US$"),
    ]:
        series = []
        for alvo in (ano, ano + 1):
            historia = bcb_focus.historia_anual(indicador, alvo, desde=desde)
            if historia:
                series.append(serie(str(alvo), f"Para {alvo}", historia, papel="consenso"))
        if series:
            for s in series:
                s.papel = "realizado"  # é a história do consenso, não uma projeção desenhada
            graficos.append(
                grafico(
                    f"focus-{indicador.split()[0].lower()}",
                    titulo,
                    series,
                    unidade=unidade,
                    casas=2,
                    periodicidade="D",
                    fonte="Banco Central, Focus (mediana semanal)",
                )
            )

    # Focus × FMI para o Brasil, ao lado do realizado.
    weo = fmi.weo(["BRA"], ["NGDP_RPCH", "PCPIEPCH"], ano - 12, ano + 4)
    edicao_fmi = f"WEO de {weo.publicado_em.strftime('%m/%Y')}"
    pib_real = _anual(ctx.sgs("PIB_VAR_ANUAL", anos=14))
    ipca12 = ctx.sgs("IPCA_12M", anos=14)
    ipca_ano = [(date(d.year, 1, 1), v) for d, v in ipca12 if d.month == 12]

    def lado_a_lado(
        id: str, titulo: str, realizado: list[Ponto], focus: dict[int, float], codigo: str
    ) -> Grafico:
        ultimo = realizado[-1]
        do_fmi = weo.valores.get(("BRA", codigo), {})
        return grafico(
            id,
            titulo,
            [
                serie("realizado", "Realizado", realizado),
                serie(
                    "focus",
                    "Focus (mediana)",
                    [ultimo, *[(date(a, 1, 1), v) for a, v in sorted(focus.items()) if a in anos]],
                    papel="consenso",
                ),
                serie(
                    "fmi",
                    f"FMI ({edicao_fmi})",
                    [
                        ultimo,
                        *[
                            (date(a, 1, 1), v)
                            for a, v in sorted(do_fmi.items())
                            if a > ultimo[0].year and a <= ano + 4
                        ],
                    ],
                    papel="previsao",
                ),
            ],
            unidade="% no ano",
            casas=2,
            periodicidade="A",
            fonte=f"IBGE e Banco Central (realizado); Focus de {periodo(edicao, 'D')}; FMI, {edicao_fmi}",
        )

    if "PIB Total" in medianas:
        graficos.insert(
            0,
            lado_a_lado(
                "pib-focus-fmi",
                "PIB: o realizado, o Focus e o FMI",
                pib_real,
                medianas["PIB Total"],
                "NGDP_RPCH",
            ),
        )
    if "IPCA" in medianas:
        graficos.insert(
            1,
            lado_a_lado(
                "ipca-focus-fmi",
                "IPCA no fim do ano: o realizado, o Focus e o FMI",
                ipca_ano,
                medianas["IPCA"],
                "PCPIEPCH",
            ),
        )

    _, pib_tri = bcb_focus.trimestrais_hoje("PIB Total")
    realizado_aa: list[Ponto] = ctx.memo.get("pib_aa", [])
    if pib_tri and realizado_aa:
        graficos.append(
            grafico(
                "pib-trimestral-focus",
                "PIB trimestral: o que já saiu e o que o Focus espera",
                [
                    serie("realizado", "Realizado", realizado_aa[-12:]),
                    serie(
                        "focus",
                        "Focus (mediana)",
                        [realizado_aa[-1], *[p for p in pib_tri if p[0] > realizado_aa[-1][0]]],
                        papel="consenso",
                    ),
                ],
                tipo="barras",
                unidade="% contra o mesmo trimestre do ano anterior",
                casas=2,
                periodicidade="T",
                fonte="IBGE (SIDRA 5932); Banco Central, Focus (ExpectativasMercadoTrimestrais)",
            )
        )

    cartoes = []
    for indicador, rotulo, unidade, casas in [
        ("PIB Total", f"Focus: PIB de {ano}", "%", 2),
        ("IPCA", f"Focus: IPCA de {ano}", "%", 2),
        ("Câmbio", f"Focus: dólar no fim de {ano}", "R$", 2),
        ("Selic", f"Focus: Selic no fim de {ano + 1}", "% a.a.", 2),
    ]:
        mapa = medianas.get(indicador, {})
        alvo = ano + 1 if indicador == "Selic" else ano
        if alvo not in mapa:
            continue
        seguinte = mapa.get(alvo + 1)
        cartoes.append(
            cartao(
                f"focus-{indicador.split()[0].lower()}-{alvo}",
                rotulo,
                [(edicao, mapa[alvo])],
                unidade=unidade,
                periodicidade="D",
                casas=casas,
                detalhe=f"{alvo + 1}: {br(seguinte, casas)}" if seguinte is not None else "",
                fonte="Banco Central, Focus (mediana)",
                procedencia="mercado",
                secao="previsoes",
            )
        )
    pib_f = medianas.get("PIB Total", {}).get(ano)
    ipca_f = medianas.get("IPCA", {}).get(ano)
    resumo = f"O Focus de {periodo(edicao, 'D')} espera"
    if pib_f is not None and ipca_f is not None:
        resumo += f" PIB de {br(pib_f, 2)} % e IPCA de {br(ipca_f, 2)} % em {ano}."
    resumo += (
        " Toda projeção aqui é de terceiros e leva a fonte: o consenso do mercado (Focus) e o "
        "FMI. Os modelos próprios do sacibras ainda não estão no ar."
    )
    return Secao(
        id="previsoes",
        titulo="Previsões",
        resumo=resumo,
        cartoes=cartoes,
        graficos=graficos,
        tabelas=[tabela],
        gerado_em=ctx.agora(),
    )
