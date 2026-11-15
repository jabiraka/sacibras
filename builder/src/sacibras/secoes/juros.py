"""Juros e Copom: a Selic realizada, a esperada pelo Focus e o juro real."""

from __future__ import annotations

from contextlib import suppress
from datetime import date, timedelta
from itertools import pairwise

from sacibras import curvas, leis, relatorios
from sacibras.calendario import ultimo_dia_util
from sacibras.catalogo import SGS
from sacibras.config import usar_b3
from sacibras.fontes import b3_derivativos, bcb_copom, bcb_focus, bcb_sgs, tesouro_direto
from sacibras.juros_futuros import a_termo
from sacibras.modelos import acerto_focus
from sacibras.modelos import selic as modelo_selic
from sacibras.schema import (
    Cartao,
    Grafico,
    LinhaRef,
    LinhaTabela,
    Meta,
    Secao,
    SimuladorSelic,
    Tabela,
)
from sacibras.secoes.base import Contexto, br, cartao, grafico, periodo, serie
from sacibras.tipos import Ponto

# Os vencimentos de janeiro, abril, julho e outubro concentram os contratos de DI.
MESES_LIQUIDOS = (1, 4, 7, 10)


def _mensal(diaria: list[Ponto]) -> list[Ponto]:
    """O último valor de cada mês, na data do 1º dia do mês."""
    por_mes: dict[date, float] = {}
    for d, v in diaria:
        por_mes[d.replace(day=1)] = v
    return sorted(por_mes.items())


def _mudancas(diaria: list[Ponto]) -> list[Ponto]:
    """Só os dias em que o valor muda, mais o último: o degrau sem peso."""
    saida: list[Ponto] = []
    for ponto in diaria:
        if not saida or saida[-1][1] != ponto[1]:
            saida.append(ponto)
    if diaria and saida[-1][0] != diaria[-1][0]:
        saida.append(diaria[-1])
    return saida


def _mais_perto(curva: list[Ponto], alvo: date) -> Ponto:
    return min(curva, key=lambda p: abs((p[0] - alvo).days))


def _interpolar(curva: list[Ponto], quando: date) -> float:
    """A taxa da curva em `quando`, por interpolação linear no tempo (chata fora das pontas)."""
    if quando <= curva[0][0]:
        return curva[0][1]
    for (d0, v0), (d1, v1) in pairwise(curva):
        if d0 <= quando <= d1:
            return v0 + (v1 - v0) * (quando - d0).days / (d1 - d0).days
    return curva[-1][1]


def _tesouro(ctx: Contexto) -> tuple[list[Cartao], list[Grafico], list[Ponto]]:
    """As curvas dos títulos públicos (Tesouro Direto): prefixada, real e a inflação entre
    elas. Devolve também a Selic embutida na curva prefixada."""
    curvas = tesouro_direto.curvas(ctx.hoje - timedelta(days=800))
    pre, real = curvas[tesouro_direto.PREFIXADO], curvas[tesouro_direto.IPCA]
    dia, pre_hoje = tesouro_direto.no_dia(pre, ctx.hoje)
    _, real_hoje = tesouro_direto.no_dia(real, ctx.hoje)
    ctx.memo["curva_prefixada"] = pre_hoje
    fonte = "Tesouro Nacional, Tesouro Direto (taxa média entre compra e venda, títulos sem cupom)"

    def tres_datas(por_data: dict[date, list[Ponto]], id: str) -> list:  # type: ignore[type-arg]
        series = []
        for rotulo, atras, papel in [
            ("", 0, "realizado"),
            ("Um mês antes", 30, "referencia"),
            ("Um ano antes", 365, "referencia"),
        ]:
            try:
                quando, pontos = tesouro_direto.no_dia(por_data, ctx.hoje - timedelta(days=atras))
            except ValueError:
                continue
            # Curvas antigas trazem títulos que já venceram ou estão para vencer: só os
            # prazos que ainda existem hoje se comparam.
            pontos = [p for p in pontos if (p[0] - ctx.hoje).days > 30]
            nome = rotulo or f"Em {periodo(quando, 'D')}"
            series.append(serie(f"{id}-{atras}", nome, pontos, casas=2, papel=papel))
        return series

    # Inflação implícita: o que iguala o prefixado ao IPCA+ de mesmo prazo, dia a dia.
    vertices = [v for v, _ in real_hoje if v <= pre_hoje[-1][0] + timedelta(days=400)][:2]
    implicitas: dict[date, list[Ponto]] = {v: [] for v in vertices}
    for base in sorted(set(pre) & set(real)):
        if base < ctx.hoje - timedelta(days=730):
            continue
        mapa_real = dict(real[base])
        for v in vertices:
            if v in mapa_real and pre[base]:
                nominal = _interpolar(pre[base], v)
                implicitas[v].append(
                    (base, ((1 + nominal / 100) / (1 + mapa_real[v] / 100) - 1) * 100)
                )

    curto = next((p for p in pre_hoje if (p[0] - ctx.hoje).days > 300), pre_hoje[0])
    longo = pre_hoje[-1]
    cartoes = [
        cartao(
            "prefixado",
            f"Juro prefixado até {periodo(curto[0], 'M')}",
            [(dia, curto[1])],
            unidade="% a.a.",
            periodicidade="D",
            casas=2,
            detalhe=f"até {periodo(longo[0], 'M')}: {br(longo[1], 2)} %",
            fonte=fonte,
            procedencia="mercado",
            secao="juros",
        ),
        cartao(
            "inclinacao",
            "Inclinação da curva de juros",
            [(dia, longo[1] - curto[1])],
            unidade="pp",
            periodicidade="D",
            casas=2,
            detalhe=(
                f"prefixado {periodo(longo[0], 'M')} menos prefixado {periodo(curto[0], 'M')}"
            ),
            fonte=fonte,
            procedencia="calculado",
            secao="juros",
        ),
        cartao(
            "juro-real-longo",
            f"Juro real até {periodo(real_hoje[0][0], 'M')}",
            [(dia, real_hoje[0][1])],
            unidade="% a.a.",
            periodicidade="D",
            casas=2,
            detalhe="Tesouro IPCA+: acima da inflação",
            fonte=fonte,
            procedencia="mercado",
            secao="juros",
        ),
    ]
    graficos = [
        grafico(
            "curva-prefixada",
            "Curva prefixada: o juro travado para cada prazo",
            tres_datas(pre, "pre"),
            tipo="curva",
            unidade="% a.a., por vencimento",
            casas=2,
            periodicidade="M",
            fonte=fonte,
            nota="Cada ponto é a taxa de um Tesouro Prefixado até o vencimento dele.",
        ),
        grafico(
            "curva-real",
            "Curva de juro real: quanto o Tesouro paga acima da inflação",
            tres_datas(real, "real"),
            tipo="curva",
            unidade="% a.a. acima do IPCA, por vencimento",
            casas=2,
            periodicidade="M",
            fonte=fonte.replace("títulos sem cupom", "Tesouro IPCA+ sem cupom"),
        ),
    ]
    com_dados = [v for v in vertices if implicitas[v]]
    if com_dados:
        primeiro = implicitas[com_dados[0]]
        ctx.memo["inflacao_implicita"] = (com_dados[0], primeiro[-1][1])
        cartoes.append(
            cartao(
                "inflacao-implicita",
                f"Inflação implícita até {periodo(com_dados[0], 'M')}",
                primeiro,
                unidade="% a.a.",
                periodicidade="D",
                casas=2,
                detalhe="a que iguala o prefixado ao IPCA+",
                fonte=fonte,
                procedencia="calculado",
                secao="juros",
                mini=250,
            )
        )
        graficos.append(
            grafico(
                "inflacao-implicita",
                "Inflação implícita nos títulos públicos",
                [
                    serie(f"ate-{v.year}", f"Até {periodo(v, 'M')}", implicitas[v])
                    for v in com_dados
                ],
                unidade="% a.a.",
                casas=2,
                periodicidade="D",
                fonte=fonte.replace("títulos sem cupom", "Prefixado e IPCA+ sem cupom"),
                nota=(
                    "(1 + taxa prefixada) / (1 + taxa do IPCA+) − 1, com a prefixada "
                    "interpolada para o vencimento do IPCA+. Inclui prêmio de risco: não é "
                    "previsão pura de inflação."
                ),
            )
        )
    # A Selic embutida na curva prefixada: taxa a termo entre os vencimentos anuais.
    cdi = ctx.sgs("CDI_ANUAL", anos=1)[-1][1]
    distancia = ctx.sgs("SELIC_META", anos=20)[-1][1] - cdi
    referencia = ultimo_dia_util(dia)
    termo = [(d, v + distancia) for d, v in a_termo(pre_hoje, referencia)]
    if termo:
        termo[0] = (ctx.hoje, termo[0][1])
        termo.append((pre_hoje[-1][0], termo[-1][1]))
        termo = [p for p in termo if p[0] <= date(ctx.hoje.year + 3, 1, 5)]
    return cartoes, graficos, termo


def _mercado_x_focus(
    ctx: Contexto, esperada: list[Ponto], distancia: float
) -> tuple[list[Cartao], list[Grafico], str]:
    """A curva do Tesouro contra o Focus no mesmo prazo: o juro prefixado contra o CDI que a
    Selic do Focus renderia, e a inflação implícita contra o IPCA do Focus acumulado."""
    td = tesouro_direto.curvas(ctx.hoje - timedelta(days=15))
    dia, pre = tesouro_direto.no_dia(td[tesouro_direto.PREFIXADO], ctx.hoje)
    _, ntnf = tesouro_direto.no_dia(td[tesouro_direto.PREFIXADO_JUROS], ctx.hoje)
    _, ipca_mais = tesouro_direto.no_dia(td[tesouro_direto.IPCA], ctx.hoje)
    _, ntnb = tesouro_direto.no_dia(td[tesouro_direto.IPCA_JUROS], ctx.hoje)
    nominal = curvas.montar(dia, pre, ntnf, curvas.CUPOM_NTNF)
    real = curvas.montar(dia, ipca_mais, ntnb, curvas.CUPOM_NTNB)

    # O Focus em degraus. Selic: a de cada reunião; depois da última, a média entre o fim de
    # um ano e o do seguinte; o CDI fica à mesma distância da meta de hoje.
    selic_anual = bcb_focus.mediana_anual_hoje("Selic")
    degraus_selic = [(d, v - distancia) for d, v in esperada]
    ultimo_ano = max(selic_anual)
    for ano in range(esperada[-1][0].year + 1, ultimo_ano + 1):
        if ano in selic_anual and ano - 1 in selic_anual:
            media = (selic_anual[ano - 1] + selic_anual[ano]) / 2
            degraus_selic.append((date(ano, 1, 1), media - distancia))
    # IPCA: o de cada mês que falta no ano (anualizado), depois o de cada ano.
    _, ipca_mes = bcb_focus.mensais_hoje("IPCA")
    ipca_anual = bcb_focus.mediana_anual_hoje("IPCA")
    degraus_ipca = [
        (d, ((1 + v / 100) ** 12 - 1) * 100)
        for d, v in ipca_mes
        if d.year == ctx.hoje.year and d >= ctx.hoje.replace(day=1)
    ]
    degraus_ipca += [(date(a, 1, 1), v) for a, v in sorted(ipca_anual.items()) if a > ctx.hoje.year]
    horizonte = date(min(ultimo_ano, max(ipca_anual)) + 1, 1, 1)
    # Só onde o Focus tem previsão: esticar o último ano dele inflaria a diferença.
    alem = horizonte

    def prazos(curva: curvas.Curva, desde: int) -> list[date]:
        vencimentos = [
            d
            for d in (ctx.hoje + timedelta(days=x) for x in range(0, 4000, 1))
            if d.day == 1 and d.month in (1, 7)
        ]
        return [d for d in vencimentos if desde <= curva.du_de(d) <= curva.fim and d <= alem]

    juro_titulos, juro_focus = [], []
    for d in prazos(nominal, 20):
        juro_titulos.append((d, nominal.taxa(nominal.du_de(d)) * 100))
        juro_focus.append((d, curvas.media_do_caminho(degraus_selic, dia, d)))
    inflacao = curvas.inflacao_implicita(
        nominal, real, [v for v, _ in ipca_mais if v <= alem] + prazos(real, real.vertices[0][0])
    )
    infl_titulos = [(p.vencimento, p.implicita) for p in inflacao]
    infl_focus = [
        (p.vencimento, curvas.media_do_caminho(degraus_ipca, dia, p.vencimento)) for p in inflacao
    ]

    fonte = (
        "Tesouro Direto (taxa média, curva zero com os títulos com cupom por bootstrap); "
        f"Focus de {periodo(dia, 'D')}"
    )
    nota_alem = (
        f" Vai até {periodo(horizonte, 'M')}, o fim do que o Focus projeta. A diferença junta "
        "duas coisas que o preço não separa: o mercado esperar uma Selic (ou uma inflação) "
        "diferente da dos economistas e o prêmio por prender o dinheiro por mais tempo."
    )
    alvo = date(ctx.hoje.year + 2, 1, 1)
    titulo_alvo = dict(juro_titulos).get(alvo)
    focus_alvo = dict(juro_focus).get(alvo)
    cartoes: list[Cartao] = []
    frase = ""
    if titulo_alvo is not None and focus_alvo is not None:
        premio = titulo_alvo - focus_alvo
        cartoes.append(
            cartao(
                "premio-curva",
                f"Prefixado acima do Focus até {periodo(alvo, 'M')}",
                [(dia, premio)],
                unidade="pp",
                periodicidade="D",
                casas=2,
                detalhe=(
                    f"títulos {br(titulo_alvo, 2)} % a.a.; o CDI da Selic do Focus, "
                    f"{br(focus_alvo, 2)} %"
                ),
                fonte=fonte,
                procedencia="calculado",
                secao="juros",
            )
        )
        palavra = "ponto" if round(premio, 1) == 1 else "pontos"
        frase = (
            f" Os títulos prefixados até {periodo(alvo, 'M')} pagam {br(titulo_alvo, 1)} % ao "
            f"ano, {br(premio, 1)} {palavra} acima do que renderia a Selic que o Focus espera no "
            "mesmo prazo: além da Selic esperada, o preço carrega o prêmio pelo risco de "
            "emprestar ao governo por mais tempo."
        )
    if inflacao:
        p = inflacao[0]
        focus_p = infl_focus[0][1]
        cartoes.append(
            cartao(
                "inflacao-implicita-focus",
                f"Inflação implícita até {periodo(p.vencimento, 'M')} × Focus",
                [(dia, p.implicita - focus_p)],
                unidade="pp",
                periodicidade="D",
                casas=2,
                detalhe=(
                    f"títulos {br(p.implicita, 2)} % a.a.; IPCA do Focus no prazo, "
                    f"{br(focus_p, 2)} %"
                ),
                fonte=fonte,
                procedencia="calculado",
                secao="juros",
            )
        )
    graficos = [
        grafico(
            "juro-titulos-focus",
            "Juro dos títulos × Selic do Focus, prazo a prazo",
            [
                serie("titulos", "Títulos prefixados (curva zero)", juro_titulos, casas=2),
                serie(
                    "focus",
                    "CDI pela Selic do Focus",
                    juro_focus,
                    casas=2,
                    papel="consenso",
                ),
            ],
            tipo="curva",
            unidade="% a.a., de hoje até o vencimento",
            casas=2,
            periodicidade="M",
            fonte=fonte,
            nota=(
                "Para cada vencimento, a taxa da curva zero do Tesouro e a taxa média que o CDI "
                "teria de hoje até lá se a Selic seguisse o Focus (a de cada reunião, depois a "
                "de cada ano), em dias úteis. A distância é o prêmio de prazo e de risco."
                + nota_alem
            ),
        ),
    ]
    if inflacao:
        graficos.append(
            grafico(
                "inflacao-titulos-focus",
                "Inflação implícita × IPCA do Focus, prazo a prazo",
                [
                    serie("titulos", "Implícita nos títulos", infl_titulos, casas=2),
                    serie(
                        "focus",
                        "IPCA do Focus no mesmo prazo",
                        infl_focus,
                        casas=2,
                        papel="consenso",
                    ),
                ],
                tipo="curva",
                unidade="% a.a., de hoje até o vencimento",
                casas=2,
                periodicidade="M",
                linhas=[LinhaRef(valor=leis.META_CONTINUA.centro, rotulo="meta")],
                fonte=fonte,
                nota=(
                    "Implícita: (1 + juro nominal) / (1 + juro real) − 1, as duas da curva zero "
                    "no mesmo vencimento (o método da curva de inflação do Jabs). Focus: o IPCA "
                    "de cada ano acumulado de hoje até o vencimento. A implícita inclui o "
                    "prêmio pelo risco de inflação." + nota_alem
                ),
            )
        )
    return cartoes, graficos, frase


def _anos_depois(d: date, anos: int) -> date:
    try:
        return d.replace(year=d.year + anos)
    except ValueError:  # 29 de fevereiro
        return d.replace(year=d.year + anos, day=28)


def _curvas_no_dia(
    td: dict[str, dict[date, list[Ponto]]], alvo: date
) -> tuple[date, curvas.Curva, curvas.Curva]:
    dia, pre = tesouro_direto.no_dia(td[tesouro_direto.PREFIXADO], alvo)
    pontos = {
        tipo: dict(td.get(tipo, {})).get(dia, [])
        for tipo in (tesouro_direto.PREFIXADO_JUROS, tesouro_direto.IPCA, tesouro_direto.IPCA_JUROS)
    }
    nominal = curvas.montar(dia, pre, pontos[tesouro_direto.PREFIXADO_JUROS], curvas.CUPOM_NTNF)
    real = curvas.montar(
        dia, pontos[tesouro_direto.IPCA], pontos[tesouro_direto.IPCA_JUROS], curvas.CUPOM_NTNB
    )
    return dia, nominal, real


def _no_prazo(
    dia: date, nominal: curvas.Curva, real: curvas.Curva, anos: int
) -> tuple[float | None, float | None, float | None]:
    """(prefixado, IPCA+, inflação implícita) para `anos` à frente, em % a.a."""
    du = nominal.du_de(_anos_depois(dia, anos))
    n = nominal.taxa(du) * 100 if du <= nominal.fim else None
    r = real.taxa(du) * 100 if curvas.tem_real(real, du) else None
    i = ((1 + n / 100) / (1 + r / 100) - 1) * 100 if n is not None and r is not None else None
    return n, r, i


def _a_termo(
    dia: date, nominal: curvas.Curva, real: curvas.Curva, de: int, ate: int
) -> tuple[float, float, float] | None:
    """(prefixado, IPCA+, implícita) a termo entre `de` e `ate` anos à frente."""
    a = nominal.du_de(_anos_depois(dia, de))
    b = nominal.du_de(_anos_depois(dia, ate))
    if b > nominal.fim or not (curvas.tem_real(real, a) and curvas.tem_real(real, b)):
        return None
    n, r = curvas.termo(nominal, a, b), curvas.termo(real, a, b)
    return n, r, ((1 + n / 100) / (1 + r / 100) - 1) * 100


def _titulos_por_prazo(ctx: Contexto) -> tuple[list[Cartao], list[Grafico], list[Tabela]]:
    """O que o econvitals mostra para os EUA (2, 5 e 10 anos, o juro real, a inflação
    implícita e a de 5 anos daqui a 5), na curva zero do Tesouro."""
    td = tesouro_direto.curvas(ctx.hoje - timedelta(days=800))
    dia, nominal, real = _curvas_no_dia(td, ctx.hoje)
    nominal_ano: curvas.Curva | None = None
    real_ano: curvas.Curva | None = None
    with suppress(ValueError):
        _, nominal_ano, real_ano = _curvas_no_dia(td, _anos_depois(ctx.hoje, -1))
    fonte = (
        "Tesouro Direto (taxa média entre compra e venda; curva zero com os títulos com cupom "
        "por bootstrap, o método do Jabs)"
    )
    # O maior prazo, até 10 anos, que as duas pernas cobrem hoje.
    longo = max(k for k in range(3, 11) if None not in _no_prazo(dia, nominal, real, k))
    linhas: list[LinhaTabela] = []
    for k in sorted({1, 2, 3, 5, longo}):
        n, r, i = _no_prazo(dia, nominal, real, k)
        antes = (
            _no_prazo(dia, nominal_ano, real_ano, k)[2]
            if nominal_ano is not None and real_ano is not None
            else None
        )
        linhas.append(
            LinhaTabela(
                rotulo=f"{k} ano{'s' if k > 1 else ''}",
                valores=[n, r, i, antes],
                unidade="% a.a.",
                casas=2,
            )
        )
    meio = longo // 2
    termo_hoje = _a_termo(dia, nominal, real, meio, longo)
    if termo_hoje is not None:
        termo_antes = (
            _a_termo(dia, nominal_ano, real_ano, meio, longo)
            if nominal_ano is not None and real_ano is not None
            else None
        )
        linhas.append(
            LinhaTabela(
                rotulo=f"De {meio} a {longo} anos (a termo)",
                valores=[*termo_hoje, termo_antes[2] if termo_antes else None],
                unidade="% a.a.",
                casas=2,
            )
        )
    tabela = Tabela(
        id="titulos-por-prazo",
        titulo="Juro e inflação implícita por prazo",
        subtitulo=f"Curva zero dos títulos do Tesouro em {periodo(dia, 'D')}",
        colunas=["Prefixado", "IPCA+ (juro real)", "Inflação implícita", "Implícita há 1 ano"],
        linhas=linhas,
        fonte=fonte,
        nota=(
            "Cada prazo é contado de hoje. A implícita é (1 + prefixado) / (1 + IPCA+) − 1 no "
            "mesmo prazo e carrega o prêmio pelo risco de inflação. A linha a termo é o que a "
            f"curva cobra de {meio} a {longo} anos daqui, sem os anos até lá: a inflação "
            "esperada para o longo prazo, a medida que os bancos centrais acompanham. Sem IPCA+ "
            "curto no Tesouro Direto, o juro real dos prazos curtos fica em branco."
        ),
    )

    # A história, um ponto por semana: o prefixado longo em juro real + inflação implícita,
    # e a implícita a termo. O prazo do gráfico é o maior que as curvas cobrem em todas as
    # semanas (o prefixado de 10 anos não existia em todo o ano passado).
    semanas: list[tuple[date, curvas.Curva, curvas.Curva]] = []
    alvo = ctx.hoje - timedelta(days=735)
    while alvo <= ctx.hoje:
        with suppress(ValueError):
            semanas.append(_curvas_no_dia(td, alvo))
        alvo += timedelta(days=7)

    def cobre(k: int) -> bool:
        return all(None not in _no_prazo(*semana, k) for semana in semanas)

    prazo_grafico = next((k for k in range(longo, 2, -1) if cobre(k)), None)
    decomposto: dict[str, list[Ponto]] = {"n": [], "r": [], "i": [], "t": []}
    for base, n_c, r_c in semanas:
        if prazo_grafico is not None:
            n, r, i = _no_prazo(base, n_c, r_c, prazo_grafico)
            if n is not None and r is not None and i is not None:
                decomposto["n"].append((base, n))
                decomposto["r"].append((base, r))
                decomposto["i"].append((base, i))
        t = _a_termo(base, n_c, r_c, meio, longo)
        if t is not None:
            decomposto["t"].append((base, t[2]))
    graficos: list[Grafico] = []
    cartoes: list[Cartao] = []
    if len(decomposto["n"]) > 10:
        graficos.append(
            grafico(
                "prefixado-decomposto",
                f"Prefixado de {prazo_grafico} anos: juro real + inflação implícita",
                [
                    serie("nominal", f"Prefixado de {prazo_grafico} anos", decomposto["n"]),
                    serie("real", "Juro real (IPCA+)", decomposto["r"]),
                    serie("implicita", "Inflação implícita", decomposto["i"]),
                ],
                unidade="% a.a.",
                casas=2,
                periodicidade="D",
                linhas=[LinhaRef(valor=leis.META_CONTINUA.centro, rotulo="meta")],
                fonte=fonte,
                nota=(
                    f"Um ponto por semana, sempre {prazo_grafico} anos à frente da data. O "
                    "prefixado sobe quando sobe o juro real (o custo do dinheiro acima da "
                    "inflação) ou a "
                    "inflação implícita (a inflação que o preço embute, com prêmio de risco)."
                ),
            )
        )
    if decomposto["t"]:
        cartoes.append(
            cartao(
                "implicita-a-termo",
                f"Inflação implícita de {meio} a {longo} anos à frente",
                decomposto["t"],
                unidade="% a.a.",
                periodicidade="D",
                casas=2,
                detalhe=(
                    f"a dos títulos para depois de {meio} anos; meta "
                    f"{br(leis.META_CONTINUA.centro, 0)} %"
                ),
                fonte=fonte,
                procedencia="calculado",
                secao="juros",
                mini=110,
            )
        )
    return cartoes, graficos, [tabela]


def _curva_di(ctx: Contexto, selic: float) -> tuple[list[Cartao], list[Grafico], list[Ponto]]:
    """Os juros futuros (DI1 da B3): a curva, a inclinação e a Selic embutida nela."""
    contratos = [c for c in b3_derivativos.futuros("DI1") if c.preco and c.em_aberto >= 10_000]
    referencia = ultimo_dia_util(ctx.hoje)
    limite = date(ctx.hoje.year + 10, 12, 31)
    curva = [(c.vencimento, float(c.preco or 0)) for c in contratos if c.vencimento <= limite]
    anterior = [
        (c.vencimento, c.ajuste_anterior)
        for c in contratos
        if c.ajuste_anterior and c.vencimento <= limite
    ]
    ctx.memo["curva_di"] = curva

    # A Selic embutida: taxa a termo entre os vencimentos líquidos, mais a distância de hoje
    # entre a Selic meta e o CDI.
    liquidos = [p for i, p in enumerate(curva) if i == 0 or p[0].month in MESES_LIQUIDOS]
    cdi = ctx.sgs("CDI_ANUAL", anos=1)[-1][1]
    distancia = selic - cdi
    horizonte = date(ctx.hoje.year + 2, 12, 31)
    termo = [(d, v + distancia) for d, v in a_termo(liquidos, referencia) if d <= horizonte]
    if termo:
        fim = next((p[0] for p in liquidos if p[0] > termo[-1][0]), termo[-1][0])
        termo.append((fim, termo[-1][1]))
        termo[0] = (ctx.hoje, termo[0][1])

    um_ano = _mais_perto(curva, date(ctx.hoje.year + 1, ctx.hoje.month, 1))
    dois = _mais_perto(curva, date(ctx.hoje.year + 2, 1, 1))
    dez = _mais_perto(curva, date(ctx.hoje.year + 10, 1, 1))
    fonte = "B3, futuro de DI de um dia (DI1), último negócio"
    cartoes = [
        cartao(
            "di-1-ano",
            f"Juro futuro para {periodo(um_ano[0], 'M')}",
            [(referencia, um_ano[1])],
            unidade="% a.a.",
            periodicidade="D",
            casas=2,
            detalhe="taxa prefixada de hoje até lá (DI futuro)",
            fonte=fonte,
            procedencia="mercado",
            secao="juros",
        ),
        cartao(
            "inclinacao-di",
            "Inclinação da curva de DI",
            [(referencia, dez[1] - dois[1])],
            unidade="pp",
            periodicidade="D",
            casas=2,
            detalhe=(
                f"DI {periodo(dez[0], 'M')} ({br(dez[1], 2)} %) menos "
                f"DI {periodo(dois[0], 'M')} ({br(dois[1], 2)} %)"
            ),
            fonte=fonte,
            procedencia="calculado",
            secao="juros",
        ),
    ]
    graficos = [
        grafico(
            "curva-di",
            "Curva de juros: a taxa prefixada para cada prazo",
            [
                serie("hoje", f"Em {periodo(referencia, 'D')}", curva, casas=3),
                serie(
                    "anterior", "Ajuste do pregão anterior", anterior, casas=3, papel="referencia"
                ),
            ],
            tipo="curva",
            unidade="% a.a., por vencimento",
            casas=2,
            periodicidade="M",
            fonte=fonte + "; vencimentos com mais de 10 mil contratos em aberto",
            nota=(
                "Cada ponto é o juro que o mercado trava hoje até aquela data. Curva subindo: "
                "o mercado cobra mais para prazos longos."
            ),
        )
    ]
    return cartoes, graficos, termo


PRIMEIRO_ANO_DOS_CICLOS = 2003


def _br(valor: float, casas: int = 1) -> str:
    """`br` com o sinal de menos tipográfico, como a tela escreve os números."""
    return br(valor, casas).replace("-", "−")


def _arredondar(valores: list[float | None], casas: int) -> list[float | None]:
    return [None if v is None else round(v, casas) for v in valores]


CICLOS_NO_GRAFICO = 6
"""Os últimos ciclos de corte no gráfico alinhado: um por cor da paleta."""


def _ciclos_alinhados(ctx: Contexto) -> list[Grafico]:
    """A Selic e o IPCA de cada ciclo de corte, com o mês do primeiro corte no zero."""
    meta = ctx.sgs("SELIC_META", anos=24)
    ipca12 = ctx.sgs("IPCA_12M", anos=24)
    cortes = [
        c
        for c in modelo_selic.ciclos(meta)
        if c.sentido == "corte" and c.inicio.year >= PRIMEIRO_ANO_DOS_CICLOS
    ][-CICLOS_NO_GRAFICO:]
    if not cortes:
        return []
    selic_mensal = modelo_selic.fim_do_mes(meta)
    antes, depois = 6, 36
    fonte = f"{ctx.fonte_sgs('SELIC_META', 'IPCA_12M')}; cálculo próprio"
    como_ler = (
        "Cada linha é um ciclo de corte, com o mês do primeiro corte no zero: à esquerda, os "
        "seis meses antes; à direita, até três anos depois. É o que aconteceu, não o que a "
        "Selic causou (o Copom corta quando espera inflação em queda)."
    )
    nomes = {c.inicio: f"{c.rotulo} (de {_br(c.selic_antes, 2)} %)" for c in cortes}
    return [
        grafico(
            "selic-ciclos-alinhados",
            "Selic em cada ciclo de corte, do primeiro corte em diante",
            [
                serie(
                    f"c{c.inicio.year}",
                    nomes[c.inicio],
                    modelo_selic.alinhado(selic_mensal, c.inicio, antes, depois),
                )
                for c in cortes
            ],
            tipo="degrau",
            eixo="meses",
            marco="mês do primeiro corte",
            subtitulo="no eixo, meses desde o primeiro corte",
            unidade="% a.a., no fim do mês",
            casas=2,
            periodicidade="M",
            fonte=fonte,
            nota=como_ler,
        ),
        grafico(
            "ipca-ciclos-alinhados",
            "IPCA em 12 meses em cada ciclo de corte da Selic",
            [
                serie(
                    f"c{c.inicio.year}",
                    nomes[c.inicio],
                    modelo_selic.alinhado(ipca12, c.inicio, antes, depois),
                )
                for c in cortes
            ],
            eixo="meses",
            marco="mês do primeiro corte",
            subtitulo="no eixo, meses desde o primeiro corte",
            unidade="% em 12 meses",
            casas=1,
            periodicidade="M",
            fonte=fonte,
            nota=como_ler,
        ),
    ]


def _ciclos_da_selic(ctx: Contexto) -> list[Tabela]:
    """O que veio depois de cada ciclo de corte e de alta, desde 2003: o fato, não o efeito."""
    # De 2003 em diante, como a amostra dos modelos do BC (o boxe deixa de fora o começo do
    # regime de metas, "caracterizado por elevada volatilidade"). Lê-se desde 2002 para saber
    # de onde a Selic vinha.
    meta = ctx.sgs("SELIC_META", anos=24)
    ipca12 = ctx.sgs("IPCA_12M", anos=24)
    dolar = ctx.sgs("DOLAR", anos=24)
    divida = ctx.sgs("DBGG", anos=20)
    todos = [c for c in modelo_selic.ciclos(meta) if c.inicio.year >= PRIMEIRO_ANO_DOS_CICLOS]
    tabelas: list[Tabela] = []
    for sentido, titulo, verbo in [
        ("corte", "Depois de cada ciclo de corte da Selic", "cortar"),
        ("alta", "Depois de cada ciclo de alta da Selic", "subir"),
    ]:
        deste = [c for c in todos if c.sentido == sentido]
        if not deste:
            continue
        depois = [modelo_selic.depois_do_ciclo(c, ipca12, dolar, divida) for c in deste]
        linhas = [
            LinhaTabela(
                rotulo="Selic antes do ciclo",
                valores=[c.selic_antes for c in deste],
                unidade="% a.a.",
                casas=2,
            ),
            LinhaTabela(
                rotulo="Selic no fim do ciclo",
                valores=[c.selic_depois for c in deste],
                unidade="% a.a.",
                casas=2,
            ),
            LinhaTabela(
                rotulo="IPCA no começo",
                valores=[d.ipca_no_comeco for d in depois],
                unidade="% em 12 meses",
                casas=1,
            ),
            LinhaTabela(
                rotulo="IPCA um ano depois",
                valores=[d.ipca_um_ano for d in depois],
                unidade="% em 12 meses",
                casas=1,
            ),
            LinhaTabela(
                rotulo="IPCA dois anos depois",
                valores=[d.ipca_dois_anos for d in depois],
                unidade="% em 12 meses",
                casas=1,
            ),
            LinhaTabela(
                rotulo="Dólar: variação em um ano",
                valores=_arredondar([d.dolar_um_ano for d in depois], 1),
                unidade="%",
                casas=0,
            ),
            LinhaTabela(
                rotulo="Dívida bruta: mudança em dois anos",
                valores=_arredondar([d.divida_dois_anos for d in depois], 2),
                unidade="pp do PIB",
                casas=1,
            ),
        ]
        quando = "; ".join(
            f"{c.rotulo}: {periodo(c.inicio, 'M')} a {periodo(c.fim, 'M')}" for c in deste
        )
        tabelas.append(
            Tabela(
                id=f"selic-ciclos-{sentido}",
                titulo=titulo,
                subtitulo=(
                    f"O que a inflação, o dólar e a dívida fizeram quando o Copom começou a {verbo}"
                ),
                colunas=[c.rotulo for c in deste],
                linhas=linhas,
                fonte=(
                    f"{ctx.fonte_sgs('SELIC_META', 'IPCA_12M', 'DOLAR', 'DBGG')}; cálculo próprio"
                ),
                nota=(
                    "Como ler: é o que aconteceu, não o que a Selic causou. O Copom corta quando "
                    "espera inflação em queda e sobe quando espera alta, e no mesmo período "
                    "vieram safra, preço do petróleo, crise de fora e contas públicas. Para o "
                    "efeito da Selic sozinha, vale a estimativa do Banco Central, no simulador "
                    "desta tela.\n\n"
                    "Ciclo: mudanças seguidas no mesmo sentido; uma pausa não encerra o ciclo, "
                    f"mas um ano parado sim ({quando}). O último pode não ter acabado. Um ano e "
                    "dois anos contam do mês da primeira mudança da Selic; o IPCA é o acumulado "
                    'em 12 meses; "–" é o que '
                    "ainda não aconteceu ou o que a série não cobre (a dívida bruta na "
                    "metodologia atual começa em dez/2006)."
                ),
            )
        )
    return tabelas


def _efeito_da_selic(ctx: Contexto) -> tuple[list[Cartao], list[Tabela], SimuladorSelic]:
    """O que o Banco Central estima que a Selic faz com a inflação, o dólar e a dívida.

    Nenhum número é nosso: saem do boxe dos modelos do BC e da nota de estatísticas fiscais,
    lidos à mão (`relatorios.py`). Nossa é só a soma das três parcelas da dívida."""
    r = relatorios
    pico = min(range(len(r.IPCA_MODELO_AGREGADO)), key=lambda i: r.IPCA_MODELO_AGREGADO[i])
    ipca, ipca_outro = r.IPCA_MODELO_AGREGADO[pico], r.IPCA_MODELO_DESAGREGADO[pico]
    piso_dolar, teto_dolar = r.DOLAR_POR_PP_DE_SELIC_FAIXA
    bruta, liquida = r.ELASTICIDADE_SELIC.bruta, r.ELASTICIDADE_SELIC.liquida
    pib = None
    with suppress(Exception):
        pib = ctx.sgs("PIB_12M", anos=2)[-1][1] / 1000  # R$ bilhões
    em_reais = f"cerca de R$ {br(bruta / 100 * pib, 0)} bi, " if pib else ""
    fonte_divida = r.FONTE_ELASTICIDADES
    # A faixa de 90 % do IPCA é a da versão de 2021 do modelo: a de 2024 saiu sem faixa.
    menos, mais = r.IPCA_FAIXA_90_MENOR[pico], r.IPCA_FAIXA_90_MAIOR[pico]
    versao_da_faixa = periodo(r.FAIXA_DO_IPCA_EM, "M")

    cartoes = [
        cartao(
            "selic-efeito-ipca",
            "Selic 1 pp mais alta: efeito no IPCA",
            [(r.EFEITO_SELIC_EM, ipca)],
            unidade="pp",
            periodicidade="M",
            casas=2,
            detalhe=f"um ano depois; faixa de 90 % do BC: {_br(mais, 2)} a {_br(menos, 2)}",
            fonte=f"{r.FONTE_EFEITO_SELIC}; {r.FONTE_FAIXA_DO_IPCA}",
            secao="juros",
        ),
        cartao(
            "selic-efeito-dolar",
            "Selic 1 pp mais alta: efeito no dólar",
            [(r.EFEITO_SELIC_EM, r.DOLAR_POR_PP_DE_SELIC)],
            unidade="%",
            periodicidade="M",
            casas=1,
            detalhe=f"faixa de 90 % do BC: {_br(piso_dolar, 1)} % a {_br(teto_dolar, 1)} %",
            fonte=r.FONTE_EFEITO_SELIC,
            secao="juros",
        ),
        cartao(
            "selic-efeito-divida",
            "Selic 1 pp mais alta: efeito na dívida bruta",
            [(r.ELASTICIDADES_EM, bruta)],
            unidade="pp do PIB",
            periodicidade="M",
            casas=2,
            detalhe=f"{em_reais}em 12 meses; sem faixa publicada",
            fonte=fonte_divida,
            secao="juros",
        ),
    ]

    ordinal = "º trimestre"
    pico_2021 = min(range(len(r.IPCA_MODELO_2021)), key=lambda i: r.IPCA_MODELO_2021[i])

    def linha(
        rotulo: str,
        valor: float,
        unidade: str,
        faixa: tuple[float, float] | None = None,
        casas: int = 2,
    ) -> LinhaTabela:
        """Estimativa, ponta de menos efeito e ponta de mais efeito ("–" onde o BC não deu)."""
        pontas: list[float | None] = [None, None]
        if faixa:
            pontas = [*sorted(faixa, key=abs)]
        return LinhaTabela(rotulo=rotulo, valores=[valor, *pontas], unidade=unidade, casas=casas)

    linhas = [
        linha(f"IPCA, modelo agregado de 2024 (o máximo, no {pico}{ordinal})", ipca, "pp"),
        linha(f"IPCA, modelo desagregado de 2024 (o máximo, no {pico}{ordinal})", ipca_outro, "pp"),
        linha(
            f"IPCA, versão de {versao_da_faixa} do modelo, no {pico}{ordinal}",
            r.IPCA_MODELO_2021[pico],
            "pp",
            (menos, mais),
        ),
        linha(
            f"IPCA, versão de {versao_da_faixa} (o máximo, no {pico_2021}{ordinal})",
            r.IPCA_MODELO_2021[pico_2021],
            "pp",
            (r.IPCA_FAIXA_90_MENOR[pico_2021], r.IPCA_FAIXA_90_MAIOR[pico_2021]),
        ),
        *[
            linha(f"IPCA, versão de {versao} (o máximo)", valor, "pp")
            for versao, valor in r.IPCA_NAS_VERSOES
            if not versao.startswith(versao_da_faixa)
        ],
        *[
            linha(f"{g.grupo}, 2024 (o máximo, no {g.trimestre}{ordinal})", g.maximo, "pp")
            for g in r.IPCA_POR_GRUPO
        ],
        linha(
            "Dólar, no trimestre da mudança",
            r.DOLAR_POR_PP_DE_SELIC,
            "%",
            r.DOLAR_POR_PP_DE_SELIC_FAIXA,
        ),
        linha("Dívida bruta do governo geral, em 12 meses", bruta, "pp do PIB"),
        linha("Dívida líquida do setor público, em 12 meses", liquida, "pp do PIB"),
        linha(
            "Para comparar: dólar 10 % mais caro, no IPCA dos 12 meses seguintes",
            r.IPCA_POR_10_DE_DOLAR_12M,
            "pp",
            casas=1,
        ),
        linha(
            "Para comparar: dólar 10 % mais caro, no IPCA dos 24 meses seguintes",
            r.IPCA_POR_10_DE_DOLAR_24M,
            "pp",
            casas=1,
        ),
    ]
    tabela = Tabela(
        id="selic-contas-bc",
        titulo="Selic 1 pp mais alta por um ano: as contas do Banco Central",
        subtitulo="A estimativa e a faixa de erro que o BC publica, conta a conta",
        colunas=["Estimativa", "Faixa de 90 %: de", "a"],
        linhas=linhas,
        fonte=(
            f"{r.FONTE_EFEITO_SELIC}; {r.FONTE_FAIXA_DO_IPCA}; Relatórios de Inflação de "
            f"set/2020 e mar/2021; {r.FONTE_REPASSE_CAMBIAL}; {fonte_divida}"
        ),
        nota=(
            "Como ler: cada linha é quanto o número fica diferente do que seria com a Selic 1 "
            "ponto mais alta durante um ano e o resto igual; com a Selic 1 ponto mais baixa, o "
            "sinal troca. A estimativa é o meio; a faixa de 90 % diz que, pela conta do BC, em "
            "9 de cada 10 casos o efeito fica entre as duas pontas. No IPCA, a ponta de mais "
            "efeito é o triplo da de menos: sabe-se o sentido, não o tamanho.\n\n"
            "A faixa do IPCA é a que o BC publicou na versão de "
            f"{versao_da_faixa} do modelo; a de {periodo(r.EFEITO_SELIC_EM, 'M')}, a vigente, "
            "saiu sem faixa, e as estimativas das quatro versões cabem todas nela. O traço é "
            "onde o BC não publicou faixa (a dívida é conta de estoque: quanto dela segue a "
            "Selic). Modelos estimados com dados desde 2003; depois de um ano, a Selic volta "
            "aos poucos, como o BC costuma reagir. O efeito no IPCA já inclui o que passa pelo "
            f"dólar. Dívida: com os dados de {periodo(r.ELASTICIDADES_EM, 'M')}. Números lidos "
            "à mão nos relatórios em 14/11/2026."
        ),
    )

    ano = ctx.hoje.year + 1

    def focus(indicador: str) -> float | None:
        with suppress(Exception):
            valor = bcb_focus.mediana_anual_hoje(indicador).get(ano)
            return None if valor is None else round(valor, 2)
        return None

    # Quanto o próprio ponto de partida erra: o Focus desta época do ano contra o que deu no
    # ano seguinte, desde 2010 (a dívida, desde que o Focus a pergunta).
    def erro_do_focus(
        indicador: str, realizado: dict[int, float], relativo: bool = False
    ) -> acerto_focus.Acerto | None:
        with suppress(Exception):
            return acerto_focus.medir(indicador, realizado, ctx.hoje, 1, relativo=relativo)
        return None

    def de_dezembro(chave: str) -> dict[int, float]:
        with suppress(Exception):
            return {d.year: v for d, v in ctx.sgs(chave, anos=24) if d.month == 12}
        return {}

    erro_ipca = erro_do_focus("IPCA", de_dezembro("IPCA_12M"))
    erro_dolar = erro_do_focus("Câmbio", de_dezembro("DOLAR"), relativo=True)
    erro_divida = erro_do_focus("Dívida bruta do governo geral", de_dezembro("DBGG"))
    medidos = [e for e in (erro_ipca, erro_dolar, erro_divida) if e]
    desde = min(min(e.anos) for e in medidos) if medidos else None
    desde_do_erro = ""
    if erro_ipca:
        desde_do_erro = f" (IPCA desde {min(erro_ipca.anos)}"
        if erro_divida:
            desde_do_erro += (
                f"; dívida desde {min(erro_divida.anos)}, e nela parte do erro é o PIB "
                "revisado depois"
            )
        desde_do_erro += ")"

    focus_selic = focus("Selic")

    meta = leis.META_CONTINUA
    zero = date(ctx.hoje.year, 10, 1)
    trimestres = [zero]
    for _ in range(len(r.SELIC_CAMINHO) - 1):
        anterior = trimestres[-1]
        mes = anterior.month + 3
        trimestres.append(date(anterior.year + (mes > 12), (mes - 1) % 12 + 1, 1))
    simulador = SimuladorSelic(
        ano=ano,
        focus_selic=focus_selic,
        focus_ipca=focus("IPCA"),
        focus_dolar=focus("Câmbio"),
        focus_divida=focus("Dívida bruta do governo geral"),
        meta=Meta(
            centro=meta.centro,
            inferior=meta.centro - meta.intervalo,
            superior=meta.centro + meta.intervalo,
            norma=meta.referencia,
        ),
        trimestres=trimestres,
        selic_caminho=r.SELIC_CAMINHO,
        ipca_agregado=r.IPCA_MODELO_AGREGADO,
        ipca_desagregado=r.IPCA_MODELO_DESAGREGADO,
        ipca_faixa_menor=r.IPCA_FAIXA_90_MENOR,
        ipca_faixa_maior=r.IPCA_FAIXA_90_MAIOR,
        faixa_do_ipca=f"faixa de 90 % do BC, da versão de {versao_da_faixa} do modelo",
        dolar_por_pp=r.DOLAR_POR_PP_DE_SELIC,
        dolar_por_pp_faixa=r.DOLAR_POR_PP_DE_SELIC_FAIXA,
        divida_por_pp_de_selic=bruta,
        divida_por_1_de_dolar=r.ELASTICIDADE_DOLAR.bruta,
        divida_por_pp_de_precos=r.ELASTICIDADE_PRECOS.bruta,
        pib_em_reais=round(pib, 1) if pib else None,
        erro_focus_ipca=round(erro_ipca.erro_tipico, 2) if erro_ipca else None,
        erro_focus_dolar=round(erro_dolar.erro_tipico, 1) if erro_dolar else None,
        erro_focus_divida=round(erro_divida.erro_tipico, 1) if erro_divida else None,
        erro_focus_desde=desde,
        fonte=(
            f"{r.FONTE_EFEITO_SELIC}; {r.FONTE_FAIXA_DO_IPCA}; {fonte_divida}; Focus de "
            f"{periodo(bcb_focus.data_da_ultima_edicao(), 'D')}; soma das parcelas da dívida: "
            "cálculo próprio"
        ),
        como_ler=(
            "Como ler: não é previsão do que vai acontecer. É quanto cada número se afasta do "
            f"que o Focus espera para {ano} se a Selic ficar diferente durante o ano inteiro e "
            "todo o resto ficar igual. O número grande é a estimativa do meio; logo abaixo vem "
            "a faixa de 90 % do Banco Central: pela conta dele, em 9 de cada 10 casos o efeito "
            "fica entre as pontas, e na inflação a ponta de cima é o triplo da de baixo. Na "
            "régua, o traço de cima é o Focus com o quanto ele costuma errar nesta época do "
            "ano, e o de baixo é onde o número iria parar com a mudança. Sabe-se melhor o "
            "sentido do efeito do que o tamanho."
        ),
        nota=(
            "Conta: cada número é uma estimativa publicada pelo Banco Central para 1 ponto de "
            "Selic, multiplicada pela mudança escolhida (os modelos dele são lineares: o dobro "
            "da mudança dá o dobro do efeito, e corte e alta têm o mesmo tamanho com o sinal "
            "trocado). Inflação: a resposta do IPCA de quatro trimestres a uma Selic diferente "
            "por um ano; já inclui o que passa pelo dólar e pela inflação esperada. Dólar: o "
            f"coeficiente da equação de câmbio do mesmo modelo ({br(-r.DOLAR_POR_PP_DE_SELIC, 2)} "
            "% por ponto), com o juro dos Estados Unidos e o risco do país parados. Dívida: as "
            f"elasticidades da nota de estatísticas fiscais do BC ({br(bruta, 2)} pp do PIB por "
            f"ponto de Selic em 12 meses, {br(r.ELASTICIDADE_DOLAR.bruta, 2)} por 1 % de dólar e "
            f"{br(r.ELASTICIDADE_PRECOS.bruta, 2)} por ponto de inflação); somar as três é conta "
            "nossa. Depois do ano, a Selic volta aos poucos, como o BC costuma reagir.\n\n"
            "Faixas: a da inflação é a de 90 % que o BC publicou na versão de "
            f"{versao_da_faixa} do modelo (a vigente, de {periodo(r.EFEITO_SELIC_EM, 'M')}, "
            "saiu sem faixa; as estimativas das quatro versões, de 0,24 a 0,33 por ponto, cabem "
            "nela). A do dólar é a de 90 % do coeficiente. Na dívida, a parcela dos juros é "
            "conta de estoque, sem faixa; a faixa soma as pontas do dólar e da inflação, o que "
            "a deixa larga de propósito. O erro do Focus é a média de quanto a mediana desta "
            "época do ano errou o ano seguinte" + desde_do_erro + ".\n\n"
            "O que nenhuma faixa cobre: se um corte for lido como descuido com a inflação, o "
            "risco do país e a inflação esperada sobem mais do que o modelo supõe, e o dólar e "
            "os preços respondem mais. Mudança grande sai da região em que o modelo foi "
            "estimado. E a dívida de prazo mais longo sente menos em um ano do que sentirá "
            "depois."
        ),
    )
    return cartoes, [tabela], simulador


def montar(ctx: Contexto) -> Secao:
    meta = ctx.sgs("SELIC_META", anos=20)
    efetiva = ctx.sgs("SELIC_ANUAL", anos=3)
    ipca12 = ctx.sgs("IPCA_12M", anos=20)
    ipca = ctx.sgs("IPCA")

    # A série 432 vem preenchida até o dia da próxima decisão do Copom.
    futuro = bcb_sgs.ler(SGS["SELIC_META"], ctx.hoje, ctx.hoje + timedelta(days=120))
    proxima = futuro[-1][0] if futuro and futuro[-1][0] > ctx.hoje else None

    todas = bcb_copom.reunioes()
    ultima = todas[-1]
    edicao, por_reuniao = bcb_focus.selic_por_reuniao()
    esperada: list[Ponto] = [(ctx.hoje.replace(day=1), meta[-1][1])]
    for rotulo, mediana in por_reuniao:
        ordem, ano = rotulo.removeprefix("R").split("/")
        quando = bcb_copom.mes_da_reuniao(todas, int(ordem), int(ano), proxima)
        if quando > esperada[-1][0]:
            esperada.append((quando, mediana))
    ctx.memo["focus_selic_reuniao"] = esperada

    # Juro real ex-post: Selic meta descontada do IPCA dos 12 meses anteriores.
    meta_mensal = _mensal(meta)
    mapa_ipca = dict(ipca12)
    real_ex_post = [
        (d, ((1 + v / 100) / (1 + mapa_ipca[d] / 100) - 1) * 100)
        for d, v in meta_mensal
        if d in mapa_ipca
    ]
    # Ex-ante: Selic meta descontada do IPCA que o Focus espera para os próximos 12 meses.
    _, focus_mensal = bcb_focus.mensais_hoje("IPCA")
    a_frente = [v for d, v in focus_mensal if d > ipca[-1][0]][:12]
    fator = 1.0
    for v in a_frente:
        fator *= 1 + v / 100
    ipca_esperado = (fator - 1) * 100
    real_ex_ante = ((1 + meta[-1][1] / 100) / fator - 1) * 100
    ctx.memo["ipca_esperado_12m"] = ipca_esperado

    desde_quando = _mudancas(meta)[-2][0] if len(_mudancas(meta)) > 1 else meta[0][0]
    fim_do_ano = next((v for r, v in reversed(por_reuniao) if r.endswith(str(ctx.hoje.year))), None)
    cartoes = [
        cartao(
            "selic-meta",
            "Selic meta",
            meta,
            unidade="% a.a.",
            periodicidade="D",
            casas=2,
            detalhe=(
                f"neste nível desde {periodo(desde_quando, 'D')}"
                + (f"; próxima decisão em {periodo(proxima, 'D')}" if proxima else "")
            ),
            fonte=ctx.fonte_sgs("SELIC_META"),
            secao="juros",
            mini=1500,
            referencia=ultima.data,
        ),
        cartao(
            "juro-real-ex-ante",
            "Juro real esperado (ex-ante)",
            [(edicao, real_ex_ante)],
            unidade="% a.a.",
            periodicidade="D",
            casas=2,
            detalhe=f"Selic menos IPCA esperado em 12 meses ({br(ipca_esperado, 2)} %)",
            fonte=f"{ctx.fonte_sgs('SELIC_META')}; Focus (medianas mensais do IPCA)",
            procedencia="calculado",
            secao="juros",
        ),
        cartao(
            "juro-real-ex-post",
            "Juro real (ex-post)",
            real_ex_post,
            unidade="% a.a.",
            periodicidade="M",
            casas=2,
            detalhe="Selic menos IPCA dos últimos 12 meses",
            fonte=ctx.fonte_sgs("SELIC_META", "IPCA_12M"),
            procedencia="calculado",
            secao="juros",
            mini=120,
        ),
        cartao(
            "selic-efetiva",
            "Selic efetiva",
            efetiva,
            unidade="% a.a.",
            periodicidade="D",
            casas=2,
            detalhe="taxa praticada no dia, base 252",
            fonte=ctx.fonte_sgs("SELIC_ANUAL"),
            secao="juros",
            mini=250,
        ),
    ]
    if fim_do_ano is not None and por_reuniao:
        final, ultimo_valor = por_reuniao[-1]
        cartoes.append(
            cartao(
                "focus-selic",
                f"Focus: Selic no fim de {ctx.hoje.year}",
                [(edicao, fim_do_ano)],
                unidade="% a.a.",
                periodicidade="D",
                casas=2,
                detalhe=f"reunião {final.removeprefix('R')}: {br(ultimo_valor, 2)} %",
                fonte="Banco Central, Focus (mediana por reunião do Copom)",
                procedencia="mercado",
                secao="juros",
            )
        )

    # A curva de juros: sempre a dos títulos do Tesouro (dado aberto); com SB_B3=1, também
    # a dos futuros de DI. Se uma faltar, a seção sai sem ela.
    graficos_di: list[Grafico] = []
    embutida: list[Ponto] = []
    origem = ""
    try:
        cartoes_td, graficos_di, embutida = _tesouro(ctx)
        cartoes[2:2] = cartoes_td
        origem = "nos títulos prefixados do Tesouro"
    except Exception as erro:
        print(f"    curva do Tesouro ficou de fora: {str(erro)[:120]}")
    frase_premio = ""
    try:
        cdi = ctx.sgs("CDI_ANUAL", anos=1)[-1][1]
        cartoes_mf, graficos_mf, frase_premio = _mercado_x_focus(ctx, esperada, meta[-1][1] - cdi)
        cartoes.extend(cartoes_mf)
        graficos_di.extend(graficos_mf)
    except Exception as erro:
        print(f"    curva contra o Focus ficou de fora: {str(erro)[:120]}")
    tabelas: list[Tabela] = []
    try:
        cartoes_pp, graficos_pp, tabelas = _titulos_por_prazo(ctx)
        cartoes.extend(cartoes_pp)
        graficos_di.extend(graficos_pp)
    except Exception as erro:
        print(f"    juros por prazo ficaram de fora: {str(erro)[:120]}")
    simulador_selic: SimuladorSelic | None = None
    try:
        cartoes_ef, tabelas_ef, simulador_selic = _efeito_da_selic(ctx)
        cartoes.extend(cartoes_ef)
        tabelas.extend(tabelas_ef)
    except Exception as erro:
        print(f"    efeito da Selic ficou de fora: {str(erro)[:120]}")
    try:
        tabelas.extend(_ciclos_da_selic(ctx))
    except Exception as erro:
        print(f"    ciclos da Selic ficaram de fora: {str(erro)[:120]}")
    ciclos_alinhados: list[Grafico] = []
    try:
        ciclos_alinhados = _ciclos_alinhados(ctx)
    except Exception as erro:
        print(f"    ciclos alinhados ficaram de fora: {str(erro)[:120]}")
    if usar_b3():
        try:
            cartoes_di, graficos_b3, embutida = _curva_di(ctx, meta[-1][1])
            cartoes.extend(cartoes_di)
            graficos_di = [*graficos_b3, *graficos_di]
            origem = "nos juros futuros (DI)"
        except Exception as erro:
            print(f"    juros futuros ficaram de fora: {str(erro)[:120]}")

    inicio = date(ctx.hoje.year - 20, 1, 1)
    trajetoria = [
        serie("meta", "Selic meta", _mudancas(meta), desde=inicio),
        serie("focus", "Focus, por reunião (mediana)", esperada, papel="consenso"),
    ]
    nota_selic = (
        "O Focus pergunta a Selic de cada reunião do Copom. As reuniões futuras estão "
        "no mês em que caiu a reunião de mesma ordem no último calendário conhecido."
    )
    if embutida:
        trajetoria.append(serie("curva", f"Embutida {origem}", embutida, papel="previsao"))
        nota_selic += (
            f" Embutida {origem}: taxa a termo entre vencimentos consecutivos (dias úteis, "
            "base 252), somada a distância de hoje entre a Selic meta e o CDI; carrega prêmio "
            "de risco, e por isso costuma ficar acima do que os economistas projetam."
        )
    graficos = [
        grafico(
            "selic-trajetoria",
            "Selic: a decidida e a que o mercado espera",
            trajetoria,
            tipo="degrau",
            unidade="% a.a.",
            casas=2,
            periodicidade="D",
            janela_anos=5,
            fonte=(
                f"{ctx.fonte_sgs('SELIC_META')}; Focus de {periodo(edicao, 'D')} "
                "(ExpectativasMercadoSelic)"
                + ("; B3, DI1" if "DI" in origem else "; Tesouro Direto" if origem else "")
            ),
            nota=nota_selic,
            largura="inteira",
        ),
        *graficos_di,
        *ciclos_alinhados,
        grafico(
            "juro-real",
            "Juro real: Selic descontada da inflação",
            [serie("ex-post", "Juro real ex-post", real_ex_post, desde=inicio)],
            tipo="area",
            unidade="% a.a.",
            casas=2,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs("SELIC_META", "IPCA_12M"),
            nota=(
                "Ex-post: (1 + Selic meta) / (1 + IPCA dos 12 meses anteriores) − 1. Olha para "
                "trás; o ex-ante do cartão usa a inflação esperada pelo Focus."
            ),
        ),
        grafico(
            "selic-ipca",
            "Selic e IPCA em 12 meses",
            [
                serie("selic", "Selic meta", meta_mensal, desde=inicio),
                serie("ipca", "IPCA em 12 meses", ipca12, desde=inicio),
            ],
            unidade="%",
            casas=2,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs("SELIC_META", "IPCA_12M"),
        ),
    ]
    # "desde 17/09 (reunião de 04/11)" parecia contradição: a última reunião manteve a taxa,
    # ou a mudou (e então vale do dia seguinte a ela).
    acao = "mudou" if desde_quando > ultima.data else "manteve"
    resumo = (
        f"A Selic está em {br(meta[-1][1], 2)} % ao ano desde {periodo(desde_quando, 'D')}, e o "
        f"Copom a {acao} na reunião de {periodo(ultima.data, 'D')}. Descontada a "
        f"inflação esperada para os próximos 12 meses, o juro real é de {br(real_ex_ante, 1)} % "
        "ao ano." + frase_premio
    )
    return Secao(
        id="juros",
        titulo="Juros e Copom",
        resumo=resumo,
        cartoes=cartoes,
        graficos=graficos,
        tabelas=tabelas,
        simulador_selic=simulador_selic,
        gerado_em=ctx.agora(),
    )
