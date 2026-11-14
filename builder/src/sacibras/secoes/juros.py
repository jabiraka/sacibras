"""Juros e Copom: a Selic realizada, a esperada pelo Focus e o juro real."""

from __future__ import annotations

from datetime import date, timedelta
from itertools import pairwise

from sacibras import curvas, leis
from sacibras.calendario import ultimo_dia_util
from sacibras.catalogo import SGS
from sacibras.config import usar_b3
from sacibras.fontes import b3_derivativos, bcb_copom, bcb_focus, bcb_sgs, tesouro_direto
from sacibras.juros_futuros import a_termo
from sacibras.schema import Cartao, Grafico, LinhaRef, Secao
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
    alem = date(horizonte.year + 5, 1, 1)

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
        nominal, real, [v for v, _ in ipca_mais] + prazos(real, real.vertices[0][0])
    )
    infl_titulos = [(p.vencimento, p.implicita) for p in inflacao]
    infl_focus = [
        (p.vencimento, curvas.media_do_caminho(degraus_ipca, dia, p.vencimento)) for p in inflacao
    ]

    fonte = (
        "Tesouro Direto (taxa média, curva zero com os títulos com cupom por bootstrap); "
        f"Focus de {periodo(dia, 'D')}"
    )
    nota_alem = f" Depois de {horizonte.year - 1}, o último ano do Focus fica parado (tracejado)."
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
                    tracejado_desde=horizonte,
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
                        tracejado_desde=horizonte,
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
    resumo = (
        f"A Selic está em {br(meta[-1][1], 2)} % ao ano desde {periodo(desde_quando, 'D')} "
        f"(reunião nº {ultima.numero} do Copom, em {periodo(ultima.data, 'D')}). Descontada a "
        f"inflação esperada para os próximos 12 meses, o juro real é de {br(real_ex_ante, 1)} % "
        "ao ano." + frase_premio
    )
    return Secao(
        id="juros",
        titulo="Juros e Copom",
        resumo=resumo,
        cartoes=cartoes,
        graficos=graficos,
        gerado_em=ctx.agora(),
    )
