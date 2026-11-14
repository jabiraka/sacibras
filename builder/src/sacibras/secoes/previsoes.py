"""Previsões: o consenso do mercado (Focus), o FMI, e as contas próprias ao lado deles.

A regra da casa: previsão nunca sozinha. O "PIB agora" aparece com o Focus do mesmo
trimestre e com o erro que o método teve fora da amostra; o Focus aparece com o quanto
costuma errar nesta época do ano; o simulador da dívida parte das hipóteses do Focus.
"""

from __future__ import annotations

from datetime import date, timedelta

from sacibras.fontes import bcb_focus, fmi
from sacibras.modelos import acerto_focus, divida, pib_agora
from sacibras.schema import (
    Cartao,
    Grafico,
    Intervalo,
    LinhaTabela,
    Secao,
    SimuladorDivida,
    Tabela,
)
from sacibras.secoes.base import Contexto, br, cartao, grafico, periodo, serie
from sacibras.tipos import Ponto

MOSTRAR_SIMULADOR = True
"""Saiu da tela em 14/11/2026 e voltou no mesmo dia, a pedido do Caio ("deixe o simulador da
dívida, acho legal")."""

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


def _simulador(
    ctx: Contexto, medianas: dict[str, dict[int, float]], edicao: date
) -> SimuladorDivida | None:
    """A linha de base da dívida bruta para os próximos oito anos, com as hipóteses do Focus."""
    ano = ctx.hoje.year
    focus_divida = medianas.get("Dívida bruta do governo geral", {})
    necessarios = ("PIB Total", "IPCA", "Resultado primário")
    if ano not in focus_divida or any(not medianas.get(n) for n in necessarios):
        return None
    dbgg = ctx.sgs("DBGG", anos=20)
    juros_12m = ctx.sgs("NFSP_JUROS_12M", anos=20)
    # O juro que a dívida paga hoje: os juros de 12 meses divididos pelo estoque.
    implicito = juros_12m[-1][1] / dbgg[-1][1] * 100
    anos = list(range(ano + 1, ano + 9))
    # A parte da dívida atrelada à Selic acompanha a Selic que o Focus espera (a média do
    # ano, pelo começo e pelo fim); o resto mantém o custo de hoje.
    atrelada = ctx.sgs("DIVIDA_IDX_SELIC", anos=2)[-1][1] / 100
    selic_fim = medianas.get("Selic", {})
    selic_hoje = ctx.sgs("SELIC_META", anos=20)[-1][1]
    juro: list[float] = []
    anterior = selic_fim.get(ano, selic_hoje)
    for a in anos:
        fim = selic_fim.get(a, anterior)
        juro.append(round(implicito + atrelada * ((anterior + fim) / 2 - selic_hoje), 2))
        anterior = fim
    return SimuladorDivida(
        ano_inicial=ano,
        divida_inicial=round(focus_divida[ano], 2),
        anos=anos,
        juro=juro,
        crescimento=[round(v, 2) for v in divida.estender(medianas["PIB Total"], anos)],
        inflacao=[round(v, 2) for v in divida.estender(medianas["IPCA"], anos)],
        primario=[round(v, 2) for v in divida.estender(medianas["Resultado primário"], anos)],
        focus_divida=[focus_divida.get(a) for a in anos],
        realizado=[(date(d.year, 1, 1), round(v, 2)) for d, v in dbgg if d.month == 12][-10:],
        fonte=(
            f"Focus de {periodo(edicao, 'D')} (PIB, IPCA, Selic, resultado primário e dívida); "
            f"{ctx.fonte_sgs('DBGG', 'NFSP_JUROS_12M', 'DIVIDA_IDX_SELIC')}; cálculo próprio"
        ),
        nota=(
            "Conta: dívida do ano seguinte = dívida × (1 + juro) ÷ ((1 + crescimento) × "
            "(1 + inflação)) − resultado primário. Parte da dívida que o Focus espera para o "
            f"fim de {ano}. Juro: o que a dívida paga hoje (juros de 12 meses do setor público "
            f"÷ dívida bruta = {br(implicito)} % ao ano); a parte atrelada à Selic "
            f"({br(atrelada * 100, 0)} % dos títulos) acompanha a Selic esperada pelo Focus. "
            "Crescimento, inflação e primário: medianas do Focus, com a última repetida nos "
            "anos que o Focus não cobre. É conta de ordem de grandeza: não separa a dívida "
            "atrelada ao câmbio nem o que entra na dívida sem passar pelo primário."
        ),
    )


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
            "Consenso não é previsão nossa: é a mediana das projeções que as instituições "
            "participantes informam ao Banco Central."
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

    # O histórico de acerto: quanto a mediana errou, nesta época do ano, desde 2010.
    acertos: dict[tuple[str, int], acerto_focus.Acerto] = {}
    realizados = {
        "IPCA": {d.year: v for d, v in ipca_ano},
        "PIB Total": {d.year: v for d, v in pib_real},
    }
    for indicador, real in realizados.items():
        for horizonte in (0, 1):
            try:
                medido = acerto_focus.medir(indicador, real, ctx.hoje, horizonte)
            except Exception as erro:
                print(f"    acerto do Focus ({indicador}) ficou de fora: {str(erro)[:100]}")
                medido = None
            if medido:
                acertos[(indicador, horizonte)] = medido

    def lado_a_lado(
        id: str, titulo: str, realizado: list[Ponto], focus: dict[int, float], codigo: str
    ) -> Grafico:
        ultimo = realizado[-1]
        do_fmi = weo.valores.get(("BRA", codigo), {})
        indicador = "IPCA" if codigo == "PCPIEPCH" else "PIB Total"
        # O erro típico vira barra de erro em cada ano do Focus: o intervalo onde a mediana,
        # nesta época do ano, costumou acertar desde 2010.
        barras = []
        for horizonte in (0, 1):
            medido = acertos.get((indicador, horizonte))
            alvo = ano + horizonte
            if medido and alvo in focus and alvo > ultimo[0].year:
                barras.append(
                    (
                        date(alvo, 1, 1),
                        round(focus[alvo] - medido.erro_tipico, 2),
                        round(focus[alvo] + medido.erro_tipico, 2),
                    )
                )
        extra: dict[str, object] = {}
        if barras:
            extra["intervalos"] = [
                Intervalo(
                    nome="erro típico do Focus nesta época do ano", serie="focus", pontos=barras
                )
            ]
            extra["nota"] = (
                "Barras: a mediana do Focus mais ou menos o erro médio que ela teve, desde 2010, "
                "quando medida nesta mesma época do ano. Quanto mais longe o ano, maior a barra."
            )
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
            fonte=(
                f"IBGE e Banco Central (realizado); Focus de {periodo(edicao, 'D')}; "
                f"FMI, {edicao_fmi}"
            ),
            **extra,
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
    agora = None
    try:
        agora = pib_agora.estimar(realizado_aa, ctx.sgs("IBCBR", anos=24))
    except Exception as erro:
        print(f"    PIB agora ficou de fora: {str(erro)[:120]}")
    cartoes: list[Cartao] = []
    focus_tri = dict(pib_tri)
    if agora and realizado_aa:
        ultimo = realizado_aa[-1]
        do_focus = focus_tri.get(agora.trimestre)
        cartoes.append(
            cartao(
                "pib-agora",
                f"PIB agora: {periodo(agora.trimestre, 'T')}",
                [(agora.trimestre, agora.previsao)],
                unidade="%",
                periodicidade="T",
                casas=1,
                detalhe=(
                    f"em um ano; erro típico de {br(agora.erro_tipico)} pp"
                    + (f"; Focus: {br(do_focus, 2)} %" if do_focus is not None else "")
                ),
                fonte="Cálculo sobre IBGE (SIDRA 5932) e Banco Central (SGS 24363)",
                procedencia="calculado",
                secao="previsoes",
            )
        )
        series_tri = [
            serie("realizado", "PIB realizado", realizado_aa[-12:]),
            serie(
                "agora",
                "PIB agora (estimativa própria)",
                [ultimo, (agora.trimestre, agora.previsao)],
                papel="previsao",
            ),
        ]
        if pib_tri:
            series_tri.insert(
                1,
                serie(
                    "focus",
                    "Focus (mediana)",
                    [ultimo, *[p for p in pib_tri if p[0] > ultimo[0]]],
                    papel="consenso",
                ),
            )
        graficos.insert(
            0,
            grafico(
                "pib-agora",
                "PIB agora: o trimestre que ainda não saiu",
                series_tri,
                tipo="barras",
                unidade="% contra o mesmo trimestre do ano anterior",
                casas=2,
                periodicidade="T",
                intervalos=[
                    Intervalo(
                        nome=f"erro típico do método (±{br(agora.erro_tipico)} pp)",
                        serie="agora",
                        pontos=[
                            (
                                agora.trimestre,
                                round(agora.previsao - agora.erro_tipico, 2),
                                round(agora.previsao + agora.erro_tipico, 2),
                            )
                        ],
                    )
                ],
                fonte=(
                    "IBGE (SIDRA 5932); Banco Central (IBC-Br, SGS 24363; Focus, "
                    "ExpectativasMercadoTrimestrais); cálculo próprio"
                ),
                nota=(
                    "Método: reta que liga o crescimento do PIB ao do IBC-Br médio do trimestre "
                    f"(os dois contra um ano antes), estimada em {agora.trimestres_na_amostra} "
                    f"trimestres. Do {periodo(agora.trimestre, 'T')} já saíram "
                    f"{agora.meses_disponiveis} de 3 meses do IBC-Br ("
                    f"{br(agora.ibc_no_trimestre)} % em um ano). Erro típico: raiz do erro "
                    f"quadrático médio fora da amostra nos últimos {agora.trimestres_no_teste} "
                    "trimestres, com o IBC-Br do trimestre inteiro e os dados revisados de hoje "
                    "— com menos meses, o erro real é maior."
                ),
            ),
        )
    elif pib_tri and realizado_aa:
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

    # Quanto o Focus costuma errar, em tabela.
    tabelas = [tabela]
    linhas_acerto = []
    for (indicador, horizonte), medido in sorted(acertos.items()):
        alvo = ano + horizonte
        aposta = medianas.get(indicador, {}).get(alvo)
        if aposta is None:
            continue
        nome = "IPCA" if indicador == "IPCA" else "PIB"
        linhas_acerto.append(
            LinhaTabela(
                rotulo=f"{nome} de {alvo}",
                valores=[
                    aposta,
                    medido.erro_tipico,
                    aposta - medido.erro_tipico,
                    aposta + medido.erro_tipico,
                    medido.vies,
                ],
                unidade="%",
                casas=2,
            )
        )
    if linhas_acerto:
        tabelas.append(
            Tabela(
                id="acerto-focus",
                titulo="Quanto o Focus costuma errar",
                subtitulo="A aposta de hoje e o erro que a mediana teve nesta época, desde 2010",
                colunas=[
                    "Aposta de hoje",
                    "Erro típico (pp)",
                    "Faixa: de",
                    "Faixa: até",
                    "Viés (pp)",
                ],
                linhas=linhas_acerto,
                fonte=(
                    "Cálculo sobre o Focus (edições antigas), o IPCA e o PIB (Banco Central e IBGE)"
                ),
                nota=(
                    "Erro típico: média do erro absoluto entre a mediana do Focus em "
                    f"{periodo(ctx.hoje, 'D')[:5]} de cada ano e o que aconteceu. Viés positivo: o "
                    "mercado apostou acima do realizado, em média. O realizado é o dado revisado "
                    "de hoje, não o da época."
                ),
            )
        )

    # O simulador da dívida: linha de base com as hipóteses do Focus.
    simulador = None
    if MOSTRAR_SIMULADOR:
        try:
            simulador = _simulador(ctx, medianas, edicao)
        except Exception as erro:
            print(f"    simulador da dívida ficou de fora: {str(erro)[:120]}")

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
    if agora:
        resumo += (
            f" A estimativa própria para o PIB do {periodo(agora.trimestre, 'T')} é de "
            f"{br(agora.previsao)} % em um ano, com erro típico de {br(agora.erro_tipico)} ponto."
        )
    resumo += " Toda previsão aqui vem com o consenso ao lado, a faixa de erro e o método."
    return Secao(
        id="previsoes",
        titulo="Previsões",
        resumo=resumo,
        cartoes=cartoes,
        graficos=graficos,
        tabelas=tabelas,
        simulador=simulador,
        gerado_em=ctx.agora(),
    )
