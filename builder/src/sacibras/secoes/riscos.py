"""Riscos: o que pode dar errado, medido com dado oficial.

Sete blocos, cada um num `try` próprio (um que falha não derruba os outros):

1. a dívida se sustenta? (juro da dívida contra crescimento, primário que a estabiliza, leque);
2. o que o mercado cobra (volatilidade do dólar);
3. câmbio e contas externas; 4. crédito e bancos; 5. inflação — estes três só no painel;
6. testes de estresse: os choques de cada crise aplicados ao ponto de hoje;
7. longo prazo: Previdência e envelhecimento; e energia (reservatórios).

O painel de alerta põe cada indicador na régua da própria história. Não há nota única de
risco (decisão de 14/11/2026): o painel diz quantos indicadores estão no quinto pior.
A palavra na tela é "sustentabilidade da dívida", não "calote" (Caio, 14/11/2026): a dívida é
quase toda em reais; o risco é de rolagem cara e inflação, mais que de não pagar.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from sacibras import alertas, contas, curvas, leis, relatorios
from sacibras.alertas import NO_PAINEL
from sacibras.contas import meta_media, ultimo_de_cada_mes
from sacibras.fontes import (
    banco_mundial,
    bcb_fiscal,
    bcb_focus,
    bis,
    fmi,
    fred,
    ibge_projecao,
    ons,
    tesouro_direto,
    tesouro_rtn,
)
from sacibras.modelos import divida, risco
from sacibras.schema import (
    Alerta,
    Cartao,
    Grafico,
    Intervalo,
    LinhaRef,
    LinhaTabela,
    Procedencia,
    Secao,
    Serie,
    SimuladorDivida,
    Tabela,
    VarianteGrafico,
)
from sacibras.secoes import estabiliza, estados, inflacao, mundo, previsoes
from sacibras.secoes.base import Contexto, br, cartao, grafico, periodo, serie
from sacibras.secoes.estabiliza import juro_que_a_divida_paga
from sacibras.tipos import Periodicidade, Ponto

HIST = 25
"""Anos de história pedidos ao SGS: o painel compara hoje com tudo desde jan/2001 (ou desde
que a série existe)."""
ACESO = 80.0
"""Pior que esta parte da própria história = "aceso" (o quinto pior). O site usa o mesmo corte."""
ANOS_DO_LEQUE = 5
ANOS_DO_ESTRESSE = 4
MESES_DO_ESTRESSE = 24

FISCAL = "Contas públicas"
EXTERNO = "Câmbio e contas externas"
INFLACAO = "Inflação"
CREDITO = "Crédito e bancos"
MERCADO = "Mercado"
LONGO = "Longo prazo e energia"

Anos = dict[int, risco.Choque]
"""{ano: (juro da dívida, crescimento real, inflação, primário)}."""


@dataclass
class Bloco:
    cartoes: list[Cartao] = field(default_factory=list)
    graficos: list[Grafico] = field(default_factory=list)
    tabelas: list[Tabela] = field(default_factory=list)
    alertas: list[Alerta] = field(default_factory=list)


@dataclass(frozen=True)
class Episodio:
    id: str
    nome: str
    inicio: date
    fim: date
    """A janela em que se medem dólar e Selic."""
    anos: tuple[int, ...]
    """Os anos cujo desvio (PIB, primário, juro, inflação) entra na conta da dívida."""


# As janelas e os anos são escolha nossa, dita na nota da tabela.
EPISODIOS = [
    Episodio("2002", "Eleição de 2002", date(2002, 4, 1), date(2002, 12, 31), (2002, 2003)),
    Episodio("2008", "Crise global de 2008", date(2008, 8, 1), date(2009, 3, 31), (2009,)),
    Episodio("2015", "Recessão de 2015–16", date(2014, 9, 1), date(2016, 2, 29), (2015, 2016)),
    Episodio("2020", "Pandemia de 2020", date(2020, 1, 1), date(2020, 6, 30), (2020,)),
    Episodio("2024", "Fim de 2024", date(2024, 9, 1), date(2025, 1, 31), ()),
]


def alerta(
    id: str,
    grupo: str,
    nome: str,
    pontos: list[Ponto],
    *,
    pior_quando: risco.PiorQuando,
    unidade: str,
    periodicidade: Periodicidade,
    fonte: str,
    casas: int = 1,
    limite: LinhaRef | None = None,
    procedencia: Procedencia = "oficial",
) -> Alerta:
    """O último ponto de `pontos` na régua de todos eles."""
    posicao = risco.posicao_na_historia(pontos, pior_quando)
    quando, valor = pontos[-1]
    texto = alertas.EXPLICACOES.get(id)
    antes = risco.ha_um_ano(pontos)
    return Alerta(
        id=id,
        grupo=grupo,
        nome=nome,
        valor=round(valor, casas + 2),
        unidade=unidade,
        casas=casas,
        referencia=quando,
        periodicidade=periodicidade,
        pior_quando=pior_quando,
        pior_que=round(posicao.pior_que, 1),
        minimo=round(posicao.minimo, casas + 2),
        maximo=round(posicao.maximo, casas + 2),
        mediana=round(posicao.mediana, casas + 2),
        desde=posicao.desde,
        limite=limite,
        fonte=fonte,
        procedencia=procedencia,
        significa=texto.significa if texto else "",
        por_que=texto.por_que if texto else "",
        pode_levar=texto.pode_levar if texto else "",
        ha_um_ano=round(antes[1], casas + 2) if antes else None,
        ha_um_ano_em=antes[0] if antes else None,
        pior_que_ha_um_ano=(
            round(risco.pior_que(antes[1], pontos, pior_quando), 1) if antes else None
        ),
    )


def _mais_grave(acesos: list[Alerta]) -> str:
    """O aceso mais longe do normal, em poucas palavras (o cartão diz só o essencial)."""
    if not acesos:
        return "nenhum aceso"
    pior = max(acesos, key=lambda a: a.pior_que)
    return f"o pior: {pior.nome.lower()}" if len(pior.nome) <= 48 else "abra o painel"


def saldo(valor: float) -> str:
    """'superávit primário de 1,20 %' ou 'déficit primário de 0,52 %'."""
    nome = "superávit" if valor >= 0 else "déficit"
    return f"{nome} primário de {br(abs(valor), 2)} %"


def semanal(pontos: list[Ponto]) -> list[Ponto]:
    """O último ponto de cada semana: gráfico longo de série diária sem pesar o JSON."""
    saida: list[Ponto] = []
    semana: tuple[int, int] | None = None
    for d, v in pontos:
        chave = (d.isocalendar()[0], d.isocalendar()[1])
        if chave == semana:
            saida[-1] = (d, v)
        else:
            saida.append((d, v))
            semana = chave
    return saida


def em_dezembro(pontos: list[Ponto]) -> dict[int, float]:
    return {d.year: v for d, v in pontos if d.month == 12}


def historia_anual(ctx: Contexto, juro_divida: list[Ponto], primario: list[Ponto]) -> Anos:
    """{ano: (juro da dívida, crescimento real, inflação, primário)} dos anos fechados."""
    juro = em_dezembro(juro_divida)
    prim = em_dezembro(primario)
    ipca = em_dezembro(ctx.sgs("IPCA_12M", 30))
    pib = {d.year: v for d, v in ctx.sgs("PIB_VAR_ANUAL", 30)}
    anos: Anos = {}
    for ano in sorted(set(juro) & set(prim) & set(ipca) & set(pib)):
        anos[ano] = (juro[ano], pib[ano], ipca[ano], prim[ano])
    return anos


# ------------------------------------------------------------------ 1. a dívida


QUEDAS_DO_JURO = (0.0, 1.0, 2.0, 3.0, 4.0)
"""Quanto o juro da dívida cai em cada linha da tabela, em pontos percentuais."""
PASSO_DO_CRESCIMENTO = 2.0
"""A tabela mostra o crescimento em reais de hoje e dois pontos para menos e para mais."""


def _media_de_dez_anos(necessario: list[Ponto]) -> float | None:
    ultimos = [v for _, v in necessario[-120:]]
    return sum(ultimos) / len(ultimos) if len(ultimos) == 120 else None


def primario_conforme_o_juro(
    divida_pib: float,
    juro: float,
    crescimento: float,
    quando: str,
    fonte: str,
    atrelada_a_selic: float | None,
    *,
    dez_anos: float | None = None,
) -> Tabela:
    """O primário que estabiliza a dívida com outros juros e outros crescimentos (Caio,
    16/11/2026: *"com alguma sinalização maior de ajuste fiscal, os juros podem cair e o
    primário que estabiliza a dívida diminuir [...] é um jogo dinâmico, e com inflação maior
    talvez tbm precisaria de menos"*). A mesma conta do cartão, repetida: não é previsão."""
    crescimentos = [
        crescimento - PASSO_DO_CRESCIMENTO,
        crescimento,
        crescimento + PASSO_DO_CRESCIMENTO,
    ]
    linhas = [
        LinhaTabela(
            rotulo=(
                f"Juro de hoje ({br(juro)} % a.a.)"
                if queda == 0
                else f"Juro {br(queda, 0)} pp menor ({br(juro - queda)} %)"
            ),
            valores=[
                round(risco.primario_que_estabiliza(divida_pib, juro - queda, g), 2)
                for g in crescimentos
            ],
            unidade="% do PIB",
            casas=1,
        )
        for queda in QUEDAS_DO_JURO
    ]
    nota = (
        "A conta do primário que estabiliza a dívida é uma foto: usa o juro e o crescimento "
        "do momento. Se o juro cair, por exemplo porque um ajuste das contas convenceu quem "
        "empresta, o esforço necessário cai junto: são as linhas de baixo. Inflação mais alta "
        "aumenta o crescimento em reais (as colunas da direita) e também diminui o primário, "
        "mas só enquanto o juro não sobe com ela"
    )
    if atrelada_a_selic is not None:
        nota += (
            f": {br(atrelada_a_selic, 0)} % da dívida em títulos segue a Selic, e essa parte "
            "encarece logo"
        )
    nota += "."
    if dez_anos is not None:
        nota += (
            f" Na média dos últimos dez anos, o primário que estabilizava a dívida foi de "
            f"{br(dez_anos)} % do PIB."
        )
    return Tabela(
        id="primario-conforme-o-juro",
        titulo="O primário que estabiliza a dívida, com outros juros e outros crescimentos",
        subtitulo=f"% do PIB; dívida bruta de {br(divida_pib)} % do PIB ({quando})",
        colunas=[
            f"PIB em reais a {br(crescimentos[0])} %",
            f"a {br(crescimentos[1])} % (hoje)",
            f"a {br(crescimentos[2])} %",
        ],
        linhas=linhas,
        fonte=fonte,
        nota=nota,
    )


def _divida(ctx: Contexto, base: SimuladorDivida | None) -> tuple[Bloco, str, Anos]:
    dbgg = ctx.sgs("DBGG", HIST)
    juros = ctx.sgs("NFSP_JUROS_12M", HIST)
    primario = contas.escalar(ctx.sgs("NFSP_PRIMARIO_12M", HIST), -1)
    nominal = contas.escalar(ctx.sgs("NFSP_NOMINAL_12M", HIST), -1)
    pib = ctx.sgs("PIB_12M", HIST)
    atrelada = ctx.sgs("DIVIDA_IDX_SELIC", HIST)

    # O juro que a dívida paga: a taxa implícita da dívida bruta em 12 meses, que o Banco
    # Central publica (decisão de 15/11/2026: substitui a conta nossa, juros de 12 meses do
    # setor público ÷ dívida bruta, que punha os juros LÍQUIDOS de todo o setor público, as
    # estatais e o que o BC ganha nas reservas inclusive, sobre a dívida BRUTA do governo
    # geral, e saía de 1 a 4 pp abaixo; 10,8 % contra 13,0 % em set/2026). A dívida bruta
    # cresce pelo juro que ela mesma rende: é essa taxa que entra na conta da estabilização.
    # Se a planilha do BC falhar, volta a conta nossa, dita no cartão.
    juro_divida, oficial = juro_que_a_divida_paga(ctx, dbgg, juros)
    crescimento = contas.variacao(pib, 12)
    folga = contas.subtrair(juro_divida, crescimento)
    necessario = risco.serie_do_primario_que_estabiliza(dbgg, juro_divida, crescimento)
    falta = contas.subtrair(necessario, primario)
    juros_reais = contas.escalar(ctx.sgs("NFSP_JUROS_12M_RS", HIST), 1 / 1000)
    prazo = ctx.sgs("DIVIDA_PRAZO_MEDIO", HIST)

    fonte_juro = bcb_fiscal.FONTE_TAXA if oficial else f"{ctx.fonte_sgs('DBGG', 'NFSP_JUROS_12M')}"
    fonte_conta = (
        f"{fonte_juro}; {ctx.fonte_sgs('DBGG', 'NFSP_PRIMARIO_12M', 'PIB_12M')}; cálculo próprio"
    )
    explica_juro = (
        "a taxa implícita da dívida bruta em 12 meses, que o Banco Central publica (os juros "
        "que a dívida rendeu ÷ o saldo)"
        if oficial
        else "juros do setor público em 12 meses ÷ dívida bruta (a planilha do Banco Central "
        "com a taxa oficial não respondeu)"
    )
    inicio = date(ctx.hoje.year - 20, 1, 1)
    quando = periodo(necessario[-1][0], "M")
    sobra = -falta[-1][1]
    distancia = f"hoje: {saldo(primario[-1][1])}; " + (
        f"faltam {br(-sobra, 1)} pp" if sobra < 0 else f"sobram {br(sobra, 1)} pp"
    )
    bloco = Bloco()
    bloco.cartoes += [
        cartao(
            "primario-estabiliza",
            "Primário que estabiliza a dívida, com o juro e o PIB de hoje",
            necessario,
            unidade="% do PIB",
            periodicidade="M",
            casas=2,
            detalhe=distancia,
            fonte=fonte_conta,
            procedencia="calculado",
            secao="riscos",
            mini=120,
        ),
        cartao(
            "juro-menos-crescimento",
            "Juro da dívida menos crescimento do PIB",
            folga,
            unidade="pp",
            periodicidade="M",
            casas=1,
            detalhe=(
                f"juro {br(juro_divida[-1][1])} % a.a.; PIB em reais "
                f"{br(crescimento[-1][1])} % em 12 meses"
            ),
            fonte=fonte_conta,
            procedencia="calculado",
            secao="riscos",
            mini=120,
        ),
        cartao(
            "juro-da-divida",
            "Juro que a dívida paga",
            juro_divida,
            unidade="% a.a.",
            periodicidade="M",
            casas=1,
            detalhe=(
                "taxa implícita da dívida bruta, 12 meses"
                if oficial
                else "juros de 12 meses ÷ dívida bruta"
            ),
            fonte=fonte_juro,
            procedencia="oficial" if oficial else "calculado",
            secao="riscos",
            mini=120,
        ),
        cartao(
            "juros-em-reais",
            "Juros pagos em 12 meses",
            juros_reais,
            unidade="R$ bilhões",
            periodicidade="M",
            casas=0,
            detalhe=f"{br(juros[-1][1], 1)} % do PIB",
            fonte=ctx.fonte_sgs("NFSP_JUROS_12M_RS", "NFSP_JUROS_12M"),
            secao="riscos",
            mini=120,
        ),
        cartao(
            "prazo-da-divida",
            "Prazo médio da dívida em títulos",
            contas.escalar(prazo, 1 / 12),
            unidade="anos",
            periodicidade="M",
            casas=1,
            detalhe=f"{br(prazo[-1][1])} meses; mais curto, mais dívida vence por ano",
            fonte=ctx.fonte_sgs("DIVIDA_PRAZO_MEDIO"),
            secao="riscos",
            mini=120,
        ),
    ]
    bloco.graficos += [
        grafico(
            "primario-necessario",
            "O primário que estabiliza a dívida e o que se faz",
            [
                serie("necessario", "Primário que estabiliza a dívida", necessario, desde=inicio),
                serie("realizado", "Primário realizado, 12 meses", primario, desde=inicio),
            ],
            unidade="% do PIB (superávit +, déficit −)",
            casas=2,
            periodicidade="M",
            janela_anos=10,
            fonte=fonte_conta,
            nota=(
                "Conta: dívida × (juro − crescimento) ÷ (1 + crescimento). Juro: "
                f"{explica_juro}. Crescimento: o do "
                "PIB em reais em 12 meses, com a inflação dentro. Quando a linha do realizado "
                "está abaixo, a dívida sobe em % do PIB; acima, cai. É foto do juro e do "
                "crescimento de cada mês, não projeção."
            ),
        ),
        grafico(
            "juro-crescimento",
            "O juro da dívida contra o crescimento do PIB",
            [
                serie("juro", "Juro que a dívida paga", juro_divida, desde=inicio),
                serie("pib", "Crescimento do PIB em reais, 12 meses", crescimento, desde=inicio),
            ],
            unidade="% ao ano",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=fonte_conta,
            nota=(
                "Com o juro acima do crescimento, a dívida cresce sozinha em % do PIB, e só "
                "superávit primário a segura. Com o crescimento acima, ela cai mesmo com "
                f"pequeno déficit. Juro: {explica_juro}."
            ),
        ),
    ]
    with contextlib.suppress(Exception):  # sem o Focus ou a planilha do BC, fica sem a ponte
        bloco.tabelas.append(estabiliza.ponte(ctx))
    bloco.tabelas.append(
        primario_conforme_o_juro(
            # Os três do mesmo mês do cartão (as séries não acabam todas no mesmo mês).
            dict(dbgg)[necessario[-1][0]],
            dict(juro_divida)[necessario[-1][0]],
            dict(crescimento)[necessario[-1][0]],
            quando,
            fonte_conta,
            atrelada[-1][1] if atrelada else None,
            dez_anos=_media_de_dez_anos(necessario),
        )
    )
    bloco.alertas += [
        alerta(
            "dbgg",
            FISCAL,
            "Dívida bruta do governo geral",
            dbgg,
            pior_quando="alto",
            unidade="% do PIB",
            periodicidade="M",
            fonte=ctx.fonte_sgs("DBGG"),
        ),
        alerta(
            "primario",
            FISCAL,
            "Resultado primário, 12 meses",
            primario,
            pior_quando="baixo",
            unidade="% do PIB",
            periodicidade="M",
            casas=2,
            fonte=ctx.fonte_sgs("NFSP_PRIMARIO_12M"),
        ),
        alerta(
            "juros",
            FISCAL,
            "Juros da dívida, 12 meses",
            juros,
            pior_quando="alto",
            unidade="% do PIB",
            periodicidade="M",
            casas=2,
            fonte=ctx.fonte_sgs("NFSP_JUROS_12M"),
        ),
        alerta(
            "nominal",
            FISCAL,
            "Resultado nominal, 12 meses",
            nominal,
            pior_quando="baixo",
            unidade="% do PIB",
            periodicidade="M",
            casas=2,
            fonte=ctx.fonte_sgs("NFSP_NOMINAL_12M"),
        ),
        alerta(
            "juro-menos-crescimento",
            FISCAL,
            "Juro da dívida menos crescimento do PIB",
            folga,
            pior_quando="alto",
            unidade="pp",
            periodicidade="M",
            fonte=fonte_conta,
            procedencia="calculado",
        ),
        alerta(
            "primario-que-falta",
            FISCAL,
            "Primário que falta para estabilizar a dívida",
            falta,
            pior_quando="alto",
            unidade="pp do PIB",
            periodicidade="M",
            casas=2,
            fonte=fonte_conta,
            procedencia="calculado",
        ),
        alerta(
            "divida-selic",
            FISCAL,
            "Dívida atrelada à Selic",
            atrelada,
            pior_quando="alto",
            unidade="% dos títulos",
            periodicidade="M",
            fonte=ctx.fonte_sgs("DIVIDA_IDX_SELIC"),
        ),
        alerta(
            "prazo-da-divida",
            FISCAL,
            "Prazo médio da dívida em títulos",
            prazo,
            pior_quando="baixo",
            unidade="meses",
            periodicidade="M",
            fonte=ctx.fonte_sgs("DIVIDA_PRAZO_MEDIO"),
        ),
    ]

    anos = historia_anual(ctx, juro_divida, primario)
    if base is not None and len(anos) >= 8:
        _leque(ctx, bloco, base, dbgg, anos)

    if necessario[-1][1] > 0:
        pede = f"só deixa de subir com {saldo(necessario[-1][1])} do PIB"
    else:
        pede = f"não sobe mesmo com {saldo(necessario[-1][1])} do PIB"
    frase = (
        f"A dívida bruta está em {br(dbgg[-1][1])} % do PIB ({quando}) e {pede}, pelo juro "
        f"e pelo crescimento de hoje; o resultado em 12 meses é {saldo(primario[-1][1])}."
    )
    return bloco, frase, anos


@dataclass(frozen=True)
class LinhaDoFmi:
    serie: Serie
    nota: str
    fonte: str


def fmi_da_divida(desde: int, ate: int, bc_dezembro: dict[int, float]) -> LinhaDoFmi | None:
    """A dívida bruta do governo geral pelo FMI (WEO), realizada e projetada, para o leque.

    Não é o mesmo número do BC (conferido em 15/11/2026): o FMI conta todos os títulos do
    Tesouro na carteira do Banco Central, e o BC, desde 2008, só as compromissadas. Em 2025,
    93,3 % (WEO de out/2026) contra 78,6 % (SGS 13762, dez/2025). A linha só entra com a
    diferença dita na nota; sem um ano em comum para medi-la, fica de fora."""
    weo = fmi.weo(["BRA"], ["GGXWDG_NGDP"], desde, ate)
    par = ("BRA", "GGXWDG_NGDP")
    valores = weo.valores.get(par, {})
    ultimo_real = weo.ultimo_realizado.get(par, weo.publicado_em.year - 1)
    gap = divida.diferenca_de_conceito(valores, bc_dezembro, ultimo_real)
    if gap is None:
        return None
    ano, diferenca = gap
    projetados = sorted(a for a in valores if a > ultimo_real)
    edicao = weo.publicado_em.strftime("%m/%Y")
    subida = ""
    if projetados:
        fim = projetados[-1]
        subida = (
            f" Compare a inclinação, não o nível: de {ultimo_real} a {fim}, o FMI vê a dívida "
            f"{'subir' if valores[fim] >= valores[ultimo_real] else 'cair'} "
            f"{br(abs(valores[fim] - valores[ultimo_real]))} pontos do PIB."
        )
    return LinhaDoFmi(
        serie=serie(
            "fmi",
            "FMI, outro conceito (com os títulos no BC)",
            [(date(a, 1, 1), v) for a, v in sorted(valores.items())],
            casas=1,
            tracejado_desde=date(ultimo_real + 1, 1, 1) if projetados else None,
        ),
        nota=(
            f"A linha do FMI (WEO de {edicao}, tracejada onde é projeção) mede outra dívida "
            "bruta: soma todos os títulos do Tesouro que estão na carteira do Banco Central, e "
            "o Banco Central conta só as operações compromissadas. Por isso fica acima: em "
            f"{ano}, {br(valores[ano])} % do PIB no FMI contra {br(bc_dezembro[ano])} % no "
            f"Banco Central, {br(diferenca)} pontos a mais.{subida}"
        ),
        fonte=f"FMI, World Economic Outlook de {edicao} (GGXWDG_NGDP)",
    )


def _leque(
    ctx: Contexto,
    bloco: Bloco,
    base: SimuladorDivida,
    dbgg: list[Ponto],
    anos: dict[int, risco.Choque],
) -> None:
    n = min(ANOS_DO_LEQUE, len(base.anos))
    futuros = base.anos[:n]
    choques = risco.choques_da_historia(anos)
    leque = risco.leque(
        base.divida_inicial,
        base.juro[:n],
        base.crescimento[:n],
        base.inflacao[:n],
        base.primario[:n],
        choques,
    )
    partida = (date(base.ano_inicial, 1, 1), base.divida_inicial)
    realizado = [(date(a, 1, 1), v) for a, v in sorted(em_dezembro(dbgg).items())][-12:]
    focus = [(date(a, 1, 1), v) for a, v in zip(futuros, base.focus_divida, strict=False) if v]
    primeiro, ultimo = min(anos), max(anos)
    series_fmi, nota_fmi, fonte_fmi = [], "", ""
    try:  # o FMI fora do ar não derruba o leque: só a linha dele fica de fora
        do_fmi = fmi_da_divida(realizado[0][0].year, futuros[-1], em_dezembro(dbgg))
        if do_fmi:
            series_fmi = [do_fmi.serie]
            nota_fmi = "\n\n" + do_fmi.nota
            fonte_fmi = f"; {do_fmi.fonte}"
    except Exception as erro:
        print(f"    riscos: leque sem o FMI ({str(erro)[:100]})")
    bloco.graficos.insert(
        0,
        grafico(
            "divida-leque",
            "Para onde a dívida pode ir: o leque de trajetórias",
            [
                serie("realizado", "Dívida bruta no fim do ano", realizado, casas=1),
                serie(
                    "mediana",
                    "Caminho do meio dos sorteios",
                    [
                        partida,
                        *[(date(a, 1, 1), v) for a, v in zip(futuros, leque.mediana, strict=True)],
                    ],
                    papel="previsao",
                    casas=1,
                ),
                serie("focus", "Focus (mediana do mercado)", [partida, *focus], papel="consenso"),
                *series_fmi,
            ],
            unidade="% do PIB",
            casas=1,
            periodicidade="A",
            intervalos=[
                Intervalo(
                    nome="8 em cada 10 sorteios ficam entre as pontas",
                    serie="mediana",
                    pontos=[
                        (date(a, 1, 1), round(leque.p10[i], 1), round(leque.p90[i], 1))
                        for i, a in enumerate(futuros)
                    ],
                    meio=[
                        (date(a, 1, 1), round(leque.p25[i], 1), round(leque.p75[i], 1))
                        for i, a in enumerate(futuros)
                    ],
                    nome_meio="metade fica na parte grossa",
                )
            ],
            fonte=f"{base.fonte}; {ctx.fonte_sgs('IPCA_12M', 'PIB_VAR_ANUAL')}{fonte_fmi}",
            nota=(
                "Como ler: ninguém sabe o futuro, então o computador montou 4.000 futuros "
                "possíveis para a dívida. Cada um parte do cenário do Focus e repete, ano a "
                f"ano, tropeços e sortes que a economia já teve entre {primeiro} e {ultimo} (um "
                "ano de juro alto, outro de crescimento fraco), tirados ao acaso como num "
                "sorteio. A linha tracejada é o caminho do meio: metade dos futuros fica acima "
                "dela, metade abaixo. A barra mostra onde cai a maior parte: 8 em cada 10 "
                "ficam entre as pontas, e metade fica na parte grossa. Quanto mais longe o ano, "
                "maior a barra, porque há mais tempo para as coisas mudarem.\n\n"
                "Método: a linha de base do simulador da dívida (hipóteses do Focus) somada a "
                f"choques da história. De {primeiro} a {ultimo}, mede-se quanto juro da dívida, "
                "crescimento, inflação e primário de cada ano se afastaram da média do período; "
                "cada sorteio tira, para os anos à frente, blocos de dois anos seguidos dessa "
                "história (os quatro desvios juntos, como aconteceram). As pontas da barra são "
                "o 10º e o 90º percentil; a parte grossa, o 25º e o 75º. É conta de ordem de "
                "grandeza: supõe que o futuro pode errar como o passado errou, e não separa a "
                "dívida cambial." + nota_fmi
            ),
            largura="inteira",
        ),
    )
    bloco.cartoes.insert(
        1,
        Cartao(
            id="divida-sobe-em-5-anos",
            rotulo=f"Dos futuros sorteados, em quantos a dívida sobe até {futuros[-1]}",
            valor=round(leque.chance_de_subir, 1),
            unidade="%",
            casas=0,
            referencia=dbgg[-1][0],
            periodicidade="M",
            detalhe=f"caminho do meio: {br(leque.mediana[-1])} % do PIB em {futuros[-1]}",
            fonte=f"{base.fonte}; choques históricos de {primeiro} a {ultimo}",
            procedencia="calculado",
            secao="riscos",
        ),
    )


# ------------------------------------------------------------------ 2. o mercado


def _mercado(ctx: Contexto) -> tuple[Bloco, list[Ponto]]:
    dolar = ctx.sgs("DOLAR", HIST + 2)
    vol_dolar = risco.volatilidade(dolar)
    nota_vol = (
        "Desvio-padrão das variações diárias nos últimos 21 dias úteis, levado ao ano "
        "(× raiz de 252). Mede o quanto o preço balança, não para que lado vai."
    )
    bloco = Bloco()
    bloco.cartoes += [
        cartao(
            "vol-dolar",
            "Volatilidade do dólar, 21 dias",
            vol_dolar,
            unidade="% a.a.",
            periodicidade="D",
            casas=1,
            detalhe="o balanço do dólar no último mês, ao ano",
            fonte=f"{ctx.fonte_sgs('DOLAR')}; cálculo próprio",
            procedencia="calculado",
            secao="riscos",
            mini=500,
        ),
    ]
    bloco.graficos += [
        grafico(
            "vol-dolar",
            "Quanto o dólar balança",
            [serie("dolar", "Volatilidade do dólar, 21 dias úteis", semanal(vol_dolar), casas=1)],
            unidade="% ao ano",
            casas=1,
            periodicidade="D",
            janela_anos=10,
            fonte=f"{ctx.fonte_sgs('DOLAR')}; cálculo próprio",
            nota=nota_vol + " Um ponto por semana.",
        ),
    ]
    bloco.alertas += [
        alerta(
            "vol-dolar",
            MERCADO,
            "Volatilidade do dólar, 21 dias",
            vol_dolar,
            pior_quando="alto",
            unidade="% a.a.",
            periodicidade="D",
            fonte=f"{ctx.fonte_sgs('DOLAR')}; cálculo próprio",
            procedencia="calculado",
        ),
    ]
    return bloco, dolar


# ------------------------------------------------------------------ 3 a 5. só no painel


def fim_do_trimestre(d: date) -> date:
    """O SGS data a série trimestral no 1º mês do trimestre; a posição é a do 3º."""
    return date(d.year, d.month + 2, 1)


def cobertura_das_reservas(reservas: list[Ponto], curto_prazo: list[Ponto]) -> list[Ponto]:
    """Reservas ÷ dívida externa de curto prazo, em %, na data de cada trimestre."""
    no_mes = dict(reservas)
    return [
        (d, no_mes[fim_do_trimestre(d)] / v * 100)
        for d, v in curto_prazo
        if v and fim_do_trimestre(d) in no_mes
    ]


def meses_de_importacao(reservas: list[Ponto], importacoes: list[Ponto]) -> list[Ponto]:
    """Quantos meses de importação (pela média dos últimos 12) as reservas pagam."""
    media = dict(contas.media_movel(importacoes, 12))
    return [(d, v / media[d]) for d, v in reservas if media.get(d)]


def _externo(ctx: Contexto) -> Bloco:
    conta_corrente = ctx.sgs("TC_12M_PIB", HIST)
    saldo = dict(conta_corrente)
    idp = ctx.sgs("IDP_12M_PIB", HIST)
    cobertura_idp = [(d, v + saldo[d]) for d, v in idp if d in saldo]
    cambial = ctx.sgs("DIVIDA_IDX_CAMBIO", HIST)
    real_efetivo = ctx.sgs("CAMBIO_REAL_EFETIVO", HIST)
    media = sum(v for _, v in real_efetivo) / len(real_efetivo)
    reservas = ctx.sgs("RESERVAS", HIST + 2)
    # Antes de 2000 a dívida externa tem um ponto por ano: a conta começa em 2000.
    curto_prazo = [p for p in ctx.sgs("DIVIDA_EXTERNA_CURTO_PRAZO", HIST + 2) if p[0].year >= 2000]
    cobertura = cobertura_das_reservas(reservas, curto_prazo)
    meses = meses_de_importacao(reservas, ctx.sgs("IMPORTACOES", HIST + 2))
    externa_liquida = ctx.sgs("DLSP_EXTERNA", HIST)
    swaps = contas.escalar(ctx.sgs("SWAP_CAMBIAL", HIST), 1 / 1000)
    fonte_cobertura = f"{ctx.fonte_sgs('RESERVAS', 'DIVIDA_EXTERNA_CURTO_PRAZO')}; cálculo próprio"
    bloco = Bloco()
    bloco.cartoes += [
        cartao(
            "reservas-cobertura",
            "Reservas sobre a dívida externa de curto prazo",
            cobertura,
            unidade="%",
            periodicidade="T",
            casas=0,
            detalhe=(
                f"reservas: US$ {br(reservas[-1][1] / 1000, 0)} bi; acima de 100 %, "
                "cobrem a dívida curta"
            ),
            fonte=fonte_cobertura,
            procedencia="calculado",
            secao="riscos",
            mini=100,
        ),
        cartao(
            "divida-externa-liquida",
            "Dívida externa líquida do setor público",
            externa_liquida,
            unidade="% do PIB",
            periodicidade="M",
            casas=1,
            detalhe=(
                "negativa: o dólar mais alto reduz a dívida líquida"
                if externa_liquida[-1][1] < 0
                else "positiva: o dólar mais alto aumenta a dívida líquida"
            ),
            fonte=ctx.fonte_sgs("DLSP_EXTERNA"),
            secao="riscos",
            mini=120,
        ),
        cartao(
            "swaps-cambiais",
            "Swaps cambiais do Banco Central",
            swaps,
            unidade="US$ bilhões",
            periodicidade="D",
            casas=1,
            detalhe="proteção contra a alta do dólar vendida pelo BC",
            fonte=ctx.fonte_sgs("SWAP_CAMBIAL"),
            secao="riscos",
            mini=750,
        ),
    ]
    bloco.graficos += [
        grafico(
            "reservas-cobertura",
            "As reservas pagam a dívida externa que vence logo?",
            [serie("cobertura", "Reservas ÷ dívida externa de curto prazo", cobertura, casas=0)],
            unidade="%",
            casas=0,
            periodicidade="T",
            linhas=[LinhaRef(valor=100.0, rotulo="reservas = dívida de curto prazo")],
            fonte=fonte_cobertura,
            nota=(
                "Reservas internacionais no fim do trimestre sobre a dívida externa bruta de "
                "curto prazo (pública e privada), como o Banco Central a publica; a série não "
                "diz se o prazo é o contratado ou o que falta para vencer."
            ),
        ),
        grafico(
            "cambio-real",
            "O real está caro ou barato? Câmbio real efetivo",
            [serie("cambio", "Taxa de câmbio real efetiva (IPCA)", real_efetivo, casas=1)],
            unidade="índice (jun/1994 = 100)",
            casas=1,
            periodicidade="M",
            janela_anos=15,
            linhas=[
                LinhaRef(valor=round(media, 1), rotulo=f"média desde {real_efetivo[0][0].year}")
            ],
            fonte=ctx.fonte_sgs("CAMBIO_REAL_EFETIVO"),
            nota=(
                "O real contra a cesta de moedas dos parceiros comerciais, descontada a "
                "inflação daqui e de lá. Para cima, o real vale menos (exportar fica mais "
                "fácil, importar mais caro); muito abaixo da média, o real está caro e uma "
                "correção brusca fica mais provável."
            ),
        ),
    ]
    bloco.alertas += [
        alerta(
            "reservas-cobertura",
            EXTERNO,
            "Reservas sobre a dívida externa de curto prazo",
            cobertura,
            pior_quando="baixo",
            unidade="%",
            periodicidade="T",
            casas=0,
            fonte=fonte_cobertura,
            procedencia="calculado",
        ),
        alerta(
            "reservas-importacoes",
            EXTERNO,
            "Reservas em meses de importação",
            meses,
            pior_quando="baixo",
            unidade="meses",
            periodicidade="M",
            fonte=f"{ctx.fonte_sgs('RESERVAS', 'IMPORTACOES')}; cálculo próprio",
            procedencia="calculado",
        ),
        alerta(
            "conta-corrente",
            EXTERNO,
            "Saldo em transações correntes, 12 meses",
            conta_corrente,
            pior_quando="baixo",
            unidade="% do PIB",
            periodicidade="M",
            casas=2,
            fonte=ctx.fonte_sgs("TC_12M_PIB"),
        ),
        alerta(
            "cobertura-idp",
            EXTERNO,
            "Investimento direto menos déficit externo",
            cobertura_idp,
            pior_quando="baixo",
            unidade="% do PIB",
            periodicidade="M",
            casas=2,
            fonte=f"{ctx.fonte_sgs('IDP_12M_PIB', 'TC_12M_PIB')}; cálculo próprio",
            procedencia="calculado",
        ),
        alerta(
            "divida-externa-liquida",
            EXTERNO,
            "Dívida externa líquida do setor público",
            externa_liquida,
            pior_quando="alto",
            unidade="% do PIB",
            periodicidade="M",
            fonte=ctx.fonte_sgs("DLSP_EXTERNA"),
        ),
        alerta(
            "divida-cambial",
            EXTERNO,
            "Dívida em títulos atrelada ao câmbio",
            cambial,
            pior_quando="alto",
            unidade="% dos títulos",
            periodicidade="M",
            casas=2,
            fonte=ctx.fonte_sgs("DIVIDA_IDX_CAMBIO"),
        ),
        alerta(
            "swaps-cambiais",
            EXTERNO,
            "Swaps cambiais do Banco Central",
            swaps,
            pior_quando="alto",
            unidade="US$ bilhões",
            periodicidade="D",
            fonte=ctx.fonte_sgs("SWAP_CAMBIAL"),
        ),
    ]
    return bloco


def _credito(ctx: Contexto) -> Bloco:
    total = ctx.sgs("CREDITO_INADIMPLENCIA", HIST)
    pf = ctx.sgs("CREDITO_INADIMPLENCIA_PF", HIST)
    pj = ctx.sgs("CREDITO_INADIMPLENCIA_PJ", HIST)
    atrasos = ctx.sgs("CREDITO_ATRASO_15_90", HIST)
    basileia = ctx.sgs("BASILEIA", HIST)
    principal = ctx.sgs("CAPITAL_PRINCIPAL", HIST)
    bloco = Bloco()
    bloco.cartoes += [
        cartao(
            "credito-atrasos",
            "Crédito com atraso de 15 a 90 dias",
            atrasos,
            unidade="%",
            periodicidade="M",
            casas=2,
            detalhe=f"pode virar inadimplência; acima de 90 dias: {br(total[-1][1], 1)} %",
            fonte=ctx.fonte_sgs("CREDITO_ATRASO_15_90", "CREDITO_INADIMPLENCIA"),
            secao="riscos",
            mini=120,
        ),
        cartao(
            "basileia",
            "Capital dos bancos (índice de Basileia)",
            basileia,
            unidade="%",
            periodicidade="M",
            casas=1,
            detalhe=f"sistema todo; capital principal: {br(principal[-1][1])} %",
            fonte=ctx.fonte_sgs("BASILEIA", "CAPITAL_PRINCIPAL"),
            secao="riscos",
            mini=120,
        ),
    ]
    bloco.graficos += [
        grafico(
            "credito-atrasos",
            "Crédito: o que atrasou e o que já é inadimplência",
            [
                serie("atrasos", "Atraso de 15 a 90 dias, total", atrasos),
                serie("pf", "Inadimplência, pessoas físicas", pf),
                serie("pj", "Inadimplência, empresas", pj),
            ],
            unidade="% da carteira",
            casas=2,
            periodicidade="M",
            fonte=ctx.fonte_sgs(
                "CREDITO_ATRASO_15_90", "CREDITO_INADIMPLENCIA_PF", "CREDITO_INADIMPLENCIA_PJ"
            ),
            nota=(
                "Inadimplência é o saldo com parcela vencida há mais de 90 dias. O atraso de "
                "15 a 90 dias costuma andar na frente dela."
            ),
        ),
        grafico(
            "basileia",
            "O colchão dos bancos: capital sobre ativos de risco",
            [
                serie("basileia", "Índice de Basileia", basileia),
                serie("principal", "Capital principal", principal),
            ],
            unidade="% dos ativos ponderados pelo risco",
            casas=1,
            periodicidade="M",
            fonte=ctx.fonte_sgs("BASILEIA", "CAPITAL_PRINCIPAL"),
            nota=(
                "Todo o Sistema Financeiro Nacional. O Banco Central publica com alguns meses "
                "de atraso. Capital principal é a parte de melhor qualidade (ações e lucros "
                "retidos); antes de out/2013 o conceito não existia e a série repete o Nível 1."
            ),
        ),
    ]
    linhas: list[tuple[str, str, list[Ponto], str, str, int]] = [
        (
            "inadimplencia",
            "Inadimplência do crédito (mais de 90 dias)",
            total,
            "CREDITO_INADIMPLENCIA",
            "%",
            2,
        ),
        (
            "inadimplencia-pf",
            "Inadimplência das pessoas físicas",
            pf,
            "CREDITO_INADIMPLENCIA_PF",
            "%",
            2,
        ),
        ("inadimplencia-pj", "Inadimplência das empresas", pj, "CREDITO_INADIMPLENCIA_PJ", "%", 2),
        ("atrasos", "Crédito com atraso de 15 a 90 dias", atrasos, "CREDITO_ATRASO_15_90", "%", 2),
        (
            "spread",
            "Spread médio do crédito",
            ctx.sgs("CREDITO_SPREAD", HIST),
            "CREDITO_SPREAD",
            "pp",
            1,
        ),
        (
            "comprometimento",
            "Renda das famílias comprometida com dívidas",
            ctx.sgs("FAMILIAS_COMPROMETIMENTO", HIST),
            "FAMILIAS_COMPROMETIMENTO",
            "%",
            1,
        ),
        (
            "endividamento",
            "Endividamento das famílias",
            ctx.sgs("FAMILIAS_ENDIVIDAMENTO", HIST),
            "FAMILIAS_ENDIVIDAMENTO",
            "% da renda de 12 meses",
            1,
        ),
    ]
    for id, nome, pontos, chave, unidade, casas in linhas:
        bloco.alertas.append(
            alerta(
                id,
                CREDITO,
                nome,
                pontos,
                pior_quando="alto",
                unidade=unidade,
                periodicidade="M",
                casas=casas,
                fonte=ctx.fonte_sgs(chave),
            )
        )
    bloco.alertas.append(
        alerta(
            "basileia",
            CREDITO,
            "Capital dos bancos (índice de Basileia)",
            basileia,
            pior_quando="baixo",
            unidade="%",
            periodicidade="M",
            limite=LinhaRef(
                valor=relatorios.BASILEIA_MINIMO, rotulo=relatorios.BASILEIA_MINIMO_FONTE
            ),
            fonte=ctx.fonte_sgs("BASILEIA"),
        )
    )
    return bloco


def _inflacao(ctx: Contexto) -> Bloco:
    meta = leis.META_CONTINUA
    teto = LinhaRef(valor=meta.centro + meta.intervalo, rotulo=f"Teto da meta ({meta.referencia})")
    bloco = Bloco()
    bloco.alertas += [
        alerta(
            "ipca",
            INFLACAO,
            "IPCA em 12 meses",
            ctx.sgs("IPCA_12M", HIST),
            pior_quando="alto",
            unidade="%",
            periodicidade="M",
            casas=2,
            limite=teto,
            fonte=ctx.fonte_sgs("IPCA_12M"),
        ),
        alerta(
            "nucleos",
            INFLACAO,
            "Média dos núcleos, 12 meses",
            inflacao.media_dos_nucleos_12m(ctx),
            pior_quando="alto",
            unidade="%",
            periodicidade="M",
            casas=2,
            limite=teto,
            fonte=f"{ctx.fonte_sgs(*inflacao.NUCLEOS)}; cálculo próprio",
            procedencia="calculado",
        ),
        alerta(
            "difusao",
            INFLACAO,
            "Difusão: itens do IPCA que subiram no mês",
            ctx.sgs("IPCA_DIFUSAO", HIST),
            pior_quando="alto",
            unidade="%",
            periodicidade="M",
            fonte=ctx.fonte_sgs("IPCA_DIFUSAO"),
        ),
    ]
    return bloco


def acima_da_meta(pontos: list[Ponto], metas: dict[int, float], meses: int) -> list[Ponto]:
    """Cada ponto menos a meta média do prazo que ele cobre, em pontos percentuais."""
    return [(d, v - meta_media(metas, d, meses)) for d, v in pontos]


def _anos_depois(d: date, anos: int) -> date:
    try:
        return d.replace(year=d.year + anos)
    except ValueError:  # 29 de fevereiro
        return d.replace(year=d.year + anos, day=28)


def real_no_prazo(real: curvas.Curva, anos: int) -> float | None:
    """O juro real (% a.a.) da curva zero `anos` à frente da data dela, se a curva cobre."""
    du = real.du_de(_anos_depois(real.base, anos))
    return real.taxa(du) * 100 if curvas.tem_real(real, du) else None


def implicita_no_prazo(nominal: curvas.Curva, real: curvas.Curva, anos: int) -> float | None:
    """A inflação implícita (% a.a.) de hoje até `anos` à frente, se as duas pernas cobrem."""
    r = real_no_prazo(real, anos)
    du = nominal.du_de(_anos_depois(nominal.base, anos))
    if r is None or du > nominal.fim:
        return None
    return ((1 + nominal.taxa(du)) / (1 + r / 100) - 1) * 100


def diferenca_por_mes(a: list[Ponto], b: list[Ponto]) -> list[Ponto]:
    """`a` − `b` nos meses em que os dois têm ponto, na data do ponto de `a`."""
    de_b = {(d.year, d.month): v for d, v in b}
    return [(d, v - de_b[(d.year, d.month)]) for d, v in a if (d.year, d.month) in de_b]


PRAZO_JURO_REAL = 10
PRAZO_IMPLICITA = 8
"""Anos. O prefixado de 10 anos falta em metade dos meses (a NTN-F mais longa do Tesouro
Direto às vezes vence antes); 8 anos é o prazo mais longo que as duas pernas cobrem quase
todo mês desde 2007 (conferido em 15/11/2026: 223 meses)."""
FONTE_CURVA = (
    "Tesouro Direto (taxa média entre compra e venda; curva zero com os títulos com cupom por "
    "bootstrap)"
)


def _curvas_de_fim_de_mes() -> tuple[list[Ponto], list[Ponto]]:
    """(juro real de 10 anos, inflação implícita de 8 anos) no último dia de cada mês com
    taxa no Tesouro Direto, desde 2004."""
    td = tesouro_direto.curvas(date(2004, 1, 1))
    datas = [d for d, _ in ultimo_de_cada_mes([(d, 0.0) for d in td[tesouro_direto.IPCA]])]
    juro_real: list[Ponto] = []
    implicita: list[Ponto] = []
    for dia in datas:
        do_dia = {tipo: td.get(tipo, {}).get(dia, []) for tipo in td}
        try:
            real = curvas.montar(
                dia,
                do_dia[tesouro_direto.IPCA],
                do_dia.get(tesouro_direto.IPCA_JUROS, []),
                curvas.CUPOM_NTNB,
            )
        except ValueError:
            continue
        if (r := real_no_prazo(real, PRAZO_JURO_REAL)) is not None:
            juro_real.append((dia, r))
        try:
            nominal = curvas.montar(
                dia,
                do_dia.get(tesouro_direto.PREFIXADO, []),
                do_dia.get(tesouro_direto.PREFIXADO_JUROS, []),
                curvas.CUPOM_NTNF,
            )
        except ValueError:
            continue
        if (i := implicita_no_prazo(nominal, real, PRAZO_IMPLICITA)) is not None:
            implicita.append((dia, i))
    return juro_real, implicita


def _metas(ctx: Contexto) -> dict[int, float]:
    return {d.year: v for d, v in ctx.sgs("META_INFLACAO", 30)}


def _juro_real_e_implicita(ctx: Contexto) -> Bloco:
    """O juro real de 10 anos contra o dos EUA (cartão e gráfico) e a inflação implícita
    longa contra a meta (painel)."""
    brasil, implicita = _curvas_de_fim_de_mes()
    bloco = Bloco()
    if implicita:
        bloco.alertas.append(
            alerta(
                "implicita-longa",
                INFLACAO,
                f"Inflação implícita de {PRAZO_IMPLICITA} anos acima da meta",
                acima_da_meta(implicita, _metas(ctx), PRAZO_IMPLICITA * 12),
                pior_quando="alto",
                unidade="pp",
                periodicidade="M",
                casas=2,
                fonte=(
                    "Tesouro Direto (curva zero, o método de Juros); "
                    f"{ctx.fonte_sgs('META_INFLACAO')}; cálculo próprio"
                ),
                procedencia="calculado",
            )
        )
    try:  # o FRED às vezes demora (docs/FONTES.md): sem ele, fica só o painel
        eua = ultimo_de_cada_mes(fred.serie(fred.TIPS_10_ANOS, date(2004, 1, 1)))
    except Exception as erro:
        print(f"    riscos: sem o juro real dos EUA ({str(erro)[:100]})")
        return bloco
    diferenca = diferenca_por_mes(brasil, eua)
    if not diferenca:
        return bloco
    fonte = f"{FONTE_CURVA}; {fred.FONTE_TIPS}; cálculo próprio"
    bloco.cartoes.append(
        cartao(
            "juro-real-brasil-eua",
            "Juro real de 10 anos: Brasil menos EUA",
            diferenca,
            unidade="pp",
            periodicidade="M",
            casas=1,
            detalhe=f"Brasil {br(brasil[-1][1])} % a.a.; EUA {br(eua[-1][1])} % a.a.",
            fonte=fonte,
            procedencia="calculado",
            secao="riscos",
            mini=120,
        )
    )
    bloco.graficos.append(
        grafico(
            "juro-real-brasil-eua",
            "Juro real de 10 anos: Brasil e EUA",
            [
                serie("brasil", "Brasil, Tesouro IPCA+", brasil),
                serie("eua", "EUA, título do Tesouro indexado à inflação (TIPS)", eua),
                serie("diferenca", "Diferença (Brasil menos EUA)", diferenca),
            ],
            unidade="% a.a.",
            casas=2,
            periodicidade="M",
            fonte=fonte,
            nota=(
                "Um ponto por mês, no último dia com taxa. Brasil: a curva zero do Tesouro "
                "IPCA+ lida 10 anos à frente da data (o mesmo método de Juros). EUA: o "
                "rendimento do título de 10 anos indexado à inflação, prazo constante, do "
                "Federal Reserve. A diferença é quanto o Brasil paga a mais, acima da "
                "inflação de cada país, para tomar dinheiro por 10 anos."
            ),
        )
    )
    return bloco


def _expectativa(ctx: Contexto) -> Bloco:
    """A expectativa de inflação dos 12 meses seguintes (Focus) contra a meta."""
    meta = leis.META_CONTINUA
    focus = ultimo_de_cada_mes(bcb_focus.inflacao_12_meses(date(2001, 1, 1)))
    bloco = Bloco()
    bloco.alertas.append(
        alerta(
            "expectativa-12m",
            INFLACAO,
            "Inflação esperada para 12 meses acima da meta",
            acima_da_meta(focus, _metas(ctx), 12),
            pior_quando="alto",
            unidade="pp",
            periodicidade="M",
            casas=2,
            limite=LinhaRef(
                valor=meta.intervalo,
                rotulo=f"Teto da meta, em pontos acima do centro ({meta.referencia})",
            ),
            fonte=(
                "Banco Central, Focus (mediana do IPCA dos 12 meses seguintes, suavizada); "
                f"{ctx.fonte_sgs('META_INFLACAO')}; cálculo próprio"
            ),
            procedencia="calculado",
        )
    )
    return bloco


def _liquidez_e_hiato(ctx: Contexto) -> Bloco:
    """A liquidez dos bancos (Banco Central) e o hiato de crédito do Brasil (BIS)."""
    bloco = Bloco()
    hiato = bis.hiato_de_credito(["BR"], date(1990, 1, 1)).get("BR", [])
    if hiato:
        bloco.alertas.append(
            alerta(
                "hiato-credito",
                CREDITO,
                "Hiato de crédito (crédito sobre o PIB contra a tendência)",
                hiato,
                pior_quando="alto",
                unidade="pp do PIB",
                periodicidade="T",
                fonte="BIS, hiato de crédito sobre o PIB (WS_CREDIT_GAP)",
            )
        )
    bloco.alertas += [
        alerta(
            "liquidez",
            CREDITO,
            "Liquidez dos bancos (Índice de Liquidez)",
            ctx.sgs("LIQUIDEZ_IL", HIST),
            pior_quando="baixo",
            unidade="",  # o índice não tem unidade: 2,38 quer dizer 2,38 vezes
            periodicidade="T",
            casas=2,
            fonte=ctx.fonte_sgs("LIQUIDEZ_IL"),
        ),
        alerta(
            "liquidez-lcr",
            CREDITO,
            "Liquidez de curto prazo dos bancos (LCR)",
            ctx.sgs("LIQUIDEZ_LCR", HIST),
            pior_quando="baixo",
            unidade="%",
            periodicidade="T",
            casas=0,
            fonte=ctx.fonte_sgs("LIQUIDEZ_LCR"),
        ),
    ]
    return bloco


# ------------------------------------------------------------------ 6. estresse


def _estresse(
    ctx: Contexto,
    base: SimuladorDivida | None,
    anos: dict[int, risco.Choque],
    dolar: list[Ponto],
) -> Bloco:
    selic = ctx.sgs("SELIC_META", HIST + 2)
    pib = {d.year: v for d, v in ctx.sgs("PIB_VAR_ANUAL", 30)}
    n = min(ANOS_DO_ESTRESSE, len(base.anos)) if base else 0
    hipoteses = (
        (
            base.divida_inicial,
            base.juro[:n],
            base.crescimento[:n],
            base.inflacao[:n],
            base.primario[:n],
        )
        if base
        else None
    )
    linha_de_base = divida.trajetoria(*hipoteses) if hipoteses else []

    altas: list[float | None] = []
    juros: list[float | None] = []
    piores_pibs: list[float | None] = []
    dolar_hoje: list[float | None] = []
    divida_a_mais: list[float | None] = []
    caminhos: list[tuple[Episodio, list[float]]] = []
    for ep in EPISODIOS:
        alta = risco.maior_alta(dolar, ep.inicio, ep.fim)
        altas.append(alta)
        juros.append(risco.maior_mudanca(selic, ep.inicio, ep.fim))
        do_episodio = [pib[a] for a in ep.anos if a in pib]
        piores_pibs.append(min(do_episodio) if do_episodio else None)
        dolar_hoje.append(dolar[-1][1] * (1 + alta / 100) if alta is not None else None)
        choques = risco.choques_do_episodio(anos, list(ep.anos))
        if hipoteses and choques and n >= 3:
            caminho = risco.repetir_episodio(*hipoteses, choques)
            caminhos.append((ep, caminho))
            divida_a_mais.append(caminho[2] - linha_de_base[2])
        else:
            divida_a_mais.append(None)

    bloco = Bloco()
    colunas = [ep.nome for ep in EPISODIOS]
    linhas = [
        LinhaTabela(rotulo="Dólar: maior alta na janela", valores=altas, unidade="%", casas=0),
        LinhaTabela(rotulo="Selic: maior mudança na janela", valores=juros, unidade="pp", casas=2),
        LinhaTabela(
            rotulo="PIB no pior ano do episódio", valores=piores_pibs, unidade="%", casas=1
        ),
        LinhaTabela(
            rotulo=f"O dólar de hoje ({br(dolar[-1][1], 2)}) com a mesma alta",
            valores=dolar_hoje,
            unidade="R$",
            casas=2,
        ),
    ]
    if base and any(v is not None for v in divida_a_mais):
        linhas.append(
            LinhaTabela(
                rotulo=f"Dívida bruta em {base.anos[2]}, acima da linha de base",
                valores=divida_a_mais,
                unidade="pp do PIB",
                casas=1,
            )
        )
    janelas = "; ".join(
        f"{ep.nome}: {periodo(ep.inicio, 'M')} a {periodo(ep.fim, 'M')}" for ep in EPISODIOS
    )
    bloco.tabelas.append(
        Tabela(
            id="estresse-episodios",
            titulo="Se acontecesse de novo: cinco episódios",
            subtitulo=(
                "O que cada crise fez com dólar, juro e PIB, e o mesmo tranco aplicado a hoje"
            ),
            colunas=colunas,
            linhas=linhas,
            fonte=f"{ctx.fonte_sgs('DOLAR', 'SELIC_META', 'PIB_VAR_ANUAL')}; cálculo próprio",
            nota=(
                "Não é previsão: é o tamanho de trancos que já aconteceram, posto na escala de "
                f"hoje. As janelas são escolha nossa ({janelas}). Alta e queda são do pior "
                "trecho dentro da janela (do ponto mais baixo ao mais alto que veio depois, e "
                "o contrário). A linha da dívida só existe onde as séries cobrem o episódio "
                "(a dívida bruta na metodologia atual começa em dez/2006). "
                + relatorios.ESTRESSE_DOS_BANCOS
            ),
        )
    )
    variantes: list[VarianteGrafico] = []
    if base and caminhos:
        partida = (date(base.ano_inicial, 1, 1), base.divida_inicial)
        futuros = base.anos[:n]
        nome_base = "Linha de base (hipóteses do Focus)"

        def caminho_serie(valores: list[float]) -> list[Ponto]:
            return [partida, *[(date(a, 1, 1), v) for a, v in zip(futuros, valores, strict=True)]]

        variantes.append(
            VarianteGrafico(
                id="divida",
                rotulo="Dívida bruta",
                titulo="A dívida se cada crise se repetisse agora",
                unidade="% do PIB",
                periodicidade="A",
                series=[
                    serie("base", nome_base, caminho_serie(linha_de_base), papel="consenso"),
                    *[
                        serie(f"ep-{ep.id}", ep.nome, caminho_serie(c), papel="previsao")
                        for ep, c in caminhos
                    ],
                ],
                nota=(
                    "Método: para cada episódio, mede-se quanto crescimento, primário, juro da "
                    "dívida e inflação dos anos da crise se afastaram da média dos dois anos "
                    "anteriores; esses desvios são somados aos primeiros anos da linha de base "
                    "do simulador da dívida, e depois a base volta. A dívida que subiu "
                    "continua lá, rendendo juro. Ordem de grandeza: não separa a dívida cambial "
                    "nem o que entra na dívida sem passar pelo primário."
                ),
            )
        )
        # As hipóteses da linha de base com o desvio de cada crise: as mesmas contas que
        # movem a dívida, mostradas uma a uma. Choque = (juro, crescimento, inflação, primário).
        com_choques = [
            (ep, risco.choques_do_episodio(anos, list(ep.anos)) or []) for ep, _ in caminhos
        ]
        for id_, rotulo, titulo, k, hipotese, nota in (
            (
                "pib",
                "PIB (crescimento)",
                "O crescimento do PIB se cada crise se repetisse agora",
                1,
                base.crescimento[:n],
                "Crescimento real no ano.",
            ),
            (
                "inflacao",
                "Inflação",
                "A inflação se cada crise se repetisse agora",
                2,
                base.inflacao[:n],
                "A inflação da linha de base do simulador da dívida.",
            ),
            (
                "primario",
                "Resultado primário",
                "O primário se cada crise se repetisse agora",
                3,
                base.primario[:n],
                "Positivo é superávit, negativo é déficit.",
            ),
        ):
            variantes.append(
                VarianteGrafico(
                    id=id_,
                    rotulo=rotulo,
                    titulo=titulo,
                    unidade="% do PIB" if id_ == "primario" else "%",
                    periodicidade="A",
                    series=[
                        serie(
                            "base",
                            nome_base,
                            [(date(a, 1, 1), v) for a, v in zip(futuros, hipotese, strict=True)],
                            papel="consenso",
                        ),
                        *[
                            serie(
                                f"ep-{ep.id}",
                                ep.nome,
                                [
                                    (date(a, 1, 1), v + (ch[i][k] if i < len(ch) else 0.0))
                                    for i, (a, v) in enumerate(zip(futuros, hipotese, strict=True))
                                ],
                                papel="previsao",
                            )
                            for ep, ch in com_choques
                        ],
                    ],
                    nota=(
                        f"{nota} A linha de base é a do Focus; em cada episódio, soma-se aos "
                        "primeiros anos o quanto aquele número se afastou, nos anos da crise, "
                        "da média dos dois anos anteriores. Depois, a base volta."
                    ),
                )
            )

    # O mercado mês a mês: o caminho de cada crise desde o começo da janela, posto no nível
    # de hoje (o dólar na mesma proporção; a Selic com a mesma mudança em pp).
    hoje_mes = dolar[-1][0].replace(day=1)

    def meses_a_frente(k: int) -> date:
        a, m = divmod(hoje_mes.month - 1 + k, 12)
        return date(hoje_mes.year + a, m + 1, 1)

    nota_mercado = (
        f"O caminho de cada crise nos {MESES_DO_ESTRESSE} meses desde o começo da janela, "
        "aplicado ao nível de hoje{como}. Não é previsão: é o tamanho de trancos que já "
        "aconteceram. A linha horizontal é o nível de hoje."
    )
    for id_, rotulo, titulo, pontos, unidade, casas, escala, soma in (
        ("dolar", "Dólar", "O dólar se cada crise se repetisse agora", dolar, "R$", 2, 1.0, False),
        ("selic", "Selic", "A Selic se cada crise se repetisse agora", selic, "%", 2, 1.0, True),
    ):
        hoje = pontos[-1][1] / escala
        series_mercado = []
        for ep in EPISODIOS:
            c = risco.caminho_mensal(pontos, ep.inicio, MESES_DO_ESTRESSE)
            if c is None:
                continue
            valores = (
                [max(0.0, hoje + v - c[0]) for v in c] if soma else [hoje * v / c[0] for v in c]
            )
            series_mercado.append(
                serie(
                    f"ep-{ep.id}",
                    ep.nome,
                    [(meses_a_frente(k), v) for k, v in enumerate(valores)],
                    papel="previsao",
                    casas=casas + 1,
                )
            )
        if series_mercado:
            variantes.append(
                VarianteGrafico(
                    id=id_,
                    rotulo=rotulo,
                    titulo=titulo,
                    unidade=unidade,
                    casas=casas,
                    periodicidade="M",
                    series=series_mercado,
                    linhas=[LinhaRef(valor=round(hoje, casas + 1), rotulo="Hoje")],
                    nota=nota_mercado.format(
                        como=(
                            " (a mesma mudança, em pontos percentuais; nunca abaixo de zero)"
                            if soma
                            else " (a mesma alta ou queda, em %)"
                        )
                    ),
                )
            )

    if variantes:
        v0 = variantes[0]
        bloco.graficos.append(
            grafico(
                "estresse-divida",
                v0.titulo,
                v0.series,
                unidade=v0.unidade,
                casas=v0.casas,
                periodicidade=v0.periodicidade,
                linhas=v0.linhas,
                fonte=(f"{base.fonte}; " if base else "")
                + f"{ctx.fonte_sgs('IPCA_12M', 'PIB_VAR_ANUAL', 'DOLAR', 'SELIC_META')}; "
                "cálculo próprio",
                nota=v0.nota,
                largura="inteira",
                variantes=variantes,
                escolher_series=True,
            )
        )
    return bloco


# ------------------------------------------------------------------ 7. longo prazo e energia


def _previdencia(ctx: Contexto) -> Bloco:
    rtn = tesouro_rtn.serie_historica()
    pib_12m = ctx.sgs("PIB_12M", 30)
    beneficios = contas.em_pct_do_pib(rtn["rgps"], pib_12m)
    arrecadacao = contas.em_pct_do_pib(rtn["arrecadacao_rgps"], pib_12m)
    deficit = contas.subtrair(beneficios, arrecadacao)
    fonte = (
        "Tesouro Nacional, Resultado do Tesouro Nacional (tabela 1.1); "
        f"PIB: {ctx.fonte_sgs('PIB_12M')}"
    )
    bloco = Bloco()
    bloco.alertas += [
        alerta(
            "deficit-inss",
            LONGO,
            "Déficit do INSS, 12 meses",
            deficit,
            pior_quando="alto",
            unidade="% do PIB",
            periodicidade="M",
            casas=2,
            fonte=fonte,
            procedencia="calculado",
        ),
        alerta(
            "beneficios-inss",
            LONGO,
            "Benefícios do INSS, 12 meses",
            beneficios,
            pior_quando="alto",
            unidade="% do PIB",
            periodicidade="M",
            casas=2,
            fonte=fonte,
            procedencia="calculado",
        ),
    ]
    return bloco


def _envelhecimento(ctx: Contexto) -> Bloco:
    idosos = ibge_projecao.indicadores()["BR"]["RDI65"]
    agora = ctx.hoje.year
    marcos = [a for a in (agora + 25, max(idosos)) if a in idosos]
    if agora not in idosos or not marcos:
        return Bloco()
    depois = "; ".join(f"{br(idosos[a])} em {a}" for a in marcos)
    bloco = Bloco()
    bloco.cartoes.append(
        Cartao(
            id="idosos-por-100",
            rotulo="Idosos para cada 100 pessoas de 15 a 64 anos",
            valor=round(idosos[agora], 2),
            unidade="",
            casas=1,
            referencia=date(agora, 1, 1),
            periodicidade="A",
            detalhe=f"projeção do IBGE: {depois}",
            fonte=f"{ibge_projecao.FONTE} (tabela 4, RDI65)",
            procedencia="oficial",
            secao="riscos",
            mini=[(date(a, 1, 1), round(v, 2)) for a, v in sorted(idosos.items()) if a >= 2000],
        )
    )
    return bloco


def _energia(ctx: Contexto) -> Bloco:
    diario = ons.reservatorios(ctx.hoje)
    mensal = ons.media_mensal(diario)
    # Reservatório tem estação: o mês de hoje se compara com o mesmo mês dos outros anos.
    mes = diario[-1][0].month
    mesmo_mes = [(d, v) for d, v in mensal if d.month == mes]
    meses = [
        "janeiro",
        "fevereiro",
        "março",
        "abril",
        "maio",
        "junho",
        "julho",
        "agosto",
        "setembro",
        "outubro",
        "novembro",
        "dezembro",
    ]
    bloco = Bloco()
    bloco.cartoes.append(
        cartao(
            "reservatorios",
            "Reservatórios das hidrelétricas",
            diario,
            unidade="% da capacidade",
            periodicidade="D",
            casas=1,
            detalhe=(
                f"média de {meses[mes - 1]} desde {mesmo_mes[0][0].year}: "
                f"{br(sum(v for _, v in mesmo_mes[:-1]) / max(1, len(mesmo_mes) - 1))} %"
            ),
            fonte=f"{ons.FONTE}; soma dos quatro subsistemas",
            procedencia="calculado",
            secao="riscos",
            mini=730,
        )
    )
    bloco.graficos.append(
        grafico(
            "reservatorios",
            "Energia guardada nos reservatórios",
            [serie("sin", "Sistema Interligado Nacional", semanal(diario), casas=1)],
            unidade="% da capacidade",
            casas=1,
            periodicidade="D",
            janela_anos=10,
            fonte=f"{ons.FONTE}; cálculo próprio",
            nota=(
                "Energia armazenada nos reservatórios das hidrelétricas, somados os quatro "
                "subsistemas (Sudeste/Centro-Oeste, Sul, Nordeste e Norte), sobre a capacidade "
                "máxima. Reservatório baixo liga térmicas, encarece a conta de luz e pesa na "
                "inflação; em 2001 houve racionamento e em 2021 houve bandeira de escassez "
                "hídrica. O nível sobe no verão e cai no inverno. Um ponto por semana."
            ),
        )
    )
    bloco.alertas.append(
        alerta(
            "reservatorios",
            LONGO,
            f"Reservatórios das hidrelétricas, contra os meses de {meses[mes - 1]}",
            mesmo_mes,
            pior_quando="baixo",
            unidade="% da capacidade",
            periodicidade="M",
            fonte=f"{ons.FONTE}; média do mês",
            procedencia="calculado",
        )
    )
    return bloco


# ------------------------------------------------------------------ lidos em relatório


def degraus(agencia: str, hoje: date) -> list[Ponto]:
    """A nota da agência em degraus (0 = menor grau de investimento), até hoje."""
    pontos = [(d, float(relatorios.DEGRAU[nota])) for d, nota in relatorios.NOTAS[agencia]]
    return [*pontos, (hoje, pontos[-1][1])]


# O eixo do gráfico com o nome da nota (S&P e Fitch / Moody's) no lugar do degrau.
NOMES_DOS_DEGRAUS = {
    1: "BBB/Baa2",
    0: "BBB−/Baa3",
    -1: "BB+/Ba1",
    -2: "BB/Ba2",
    -3: "BB−/Ba3",
    -4: "B+/B1",
    -5: "B/B2",
}


def _nota(ctx: Contexto) -> Bloco:
    vigentes = {agencia: historia[-1] for agencia, historia in relatorios.NOTAS.items()}
    abaixo = {a: -relatorios.DEGRAU[nota] for a, (_, nota) in vigentes.items()}
    notas = {a: nota.replace("-", "−") for a, (_, nota) in vigentes.items()}
    # A nota mais comum vai grande; quem diverge vai no detalhe.
    principal = max(notas.values(), key=list(notas.values()).count)
    outras = [f"{a} {n}" for a, n in notas.items() if n != principal]
    pior = max(abaixo.values())
    bloco = Bloco()
    bloco.cartoes.append(
        Cartao(
            id="nota-de-credito",
            rotulo="Nota de crédito do Brasil",
            valor=float(pior),
            texto=principal,
            unidade="degraus" if pior != 1 else "degrau",
            casas=0,
            referencia=relatorios.ULTIMO_ATO_LIDO,
            periodicidade="D",
            detalhe=(
                f"{pior} {'degrau' if pior == 1 else 'degraus'} abaixo do grau de investimento"
                + (f"; {', '.join(outras)}" if outras else "")
            ),
            fonte=relatorios.FONTE_NOTAS,
            secao="riscos",
        )
    )
    bloco.graficos.append(
        grafico(
            "nota-de-credito",
            "A nota de crédito do Brasil nas três agências",
            [
                serie("sp", "S&P", degraus("S&P", ctx.hoje), casas=0),
                serie("fitch", "Fitch", degraus("Fitch", ctx.hoje), casas=0),
                serie("moodys", "Moody's", degraus("Moody's", ctx.hoje), casas=0),
            ],
            subtitulo="De BBB− para cima, grau de investimento",
            tipo="degrau",
            unidade="",
            casas=0,
            periodicidade="D",
            linhas=[LinhaRef(valor=0.0, rotulo="grau de investimento (BBB−/Baa3)")],
            marcas_y=[LinhaRef(valor=float(v), rotulo=n) for v, n in NOMES_DOS_DEGRAUS.items()],
            fonte=relatorios.FONTE_NOTAS,
            nota=(
                "Dívida de longo prazo em moeda estrangeira; só as mudanças de nota, sem a "
                "perspectiva (hoje estável nas três). Lido à mão no Tesouro em 14/11/2026; "
                f"depois de {periodo(relatorios.ULTIMO_ATO_LIDO, 'D')} não achamos ato novo."
            ),
        )
    )
    return bloco


def _elasticidades() -> Bloco:
    bloco = Bloco()
    bloco.tabelas.append(
        Tabela(
            id="elasticidades-da-divida",
            titulo="Quanto a dívida sente o dólar, a Selic e a inflação",
            subtitulo=(
                "A conta do Banco Central, em pontos do PIB, com os dados de "
                f"{periodo(relatorios.ELASTICIDADES_EM, 'M')}"
            ),
            colunas=["Dívida líquida do setor público", "Dívida bruta do governo geral"],
            linhas=[
                LinhaTabela(
                    rotulo=e.choque, valores=[e.liquida, e.bruta], unidade="pp do PIB", casas=2
                )
                for e in relatorios.ELASTICIDADES
            ],
            fonte=relatorios.FONTE_ELASTICIDADES,
            nota=(
                "O Banco Central publica o efeito de uma queda de 1 pp na Selic e nos índices "
                "de preços e diz que o da alta é simétrico: aqui vai o da alta. O dólar mais "
                "caro reduz a dívida líquida (as reservas, em dólar, valem mais em reais) e "
                "aumenta a bruta. Lido à mão: o quadro é uma imagem na nota mensal."
            ),
        )
    )
    return bloco


# ------------------------------------------------------------------ custo e rolagem da dívida


def _juros_sobre_receita(ctx: Contexto) -> Bloco:
    """Juros do Governo Central sobre a receita do Governo Central, em 12 meses.

    Escolha de 15/11/2026: as duas pontas do mesmo governo, e as duas conferíveis mês a mês.
    Juros: os nominais do Governo Federal e do Banco Central que o BC apura (SGS 4606, por
    competência, sem o efeito do câmbio; líquidos do que se recebe de juros). Receita: a
    líquida do Governo Central no RTN (a total menos as transferências a estados e
    municípios). Os juros do setor público inteiro contra a carga tributária misturariam
    governos (e a carga só sai uma vez por ano)."""
    juros = ctx.sgs("NFSP_JUROS_GC_MES", HIST)
    rtn = tesouro_rtn.serie_historica()
    razao = divida.juros_sobre_receita(juros, rtn["receita_liquida"])
    if not razao:
        return Bloco()
    fonte = (
        f"{ctx.fonte_sgs('NFSP_JUROS_GC_MES')}; Tesouro Nacional, Resultado do Tesouro "
        "Nacional (tabela 1.1, receita líquida); cálculo próprio"
    )
    inicio = date(ctx.hoje.year - 20, 1, 1)
    bloco = Bloco()
    bloco.cartoes.append(
        cartao(
            "juros-sobre-receita",
            "Juros sobre a receita da União",
            razao,
            unidade="%",
            periodicidade="M",
            casas=0,
            detalhe="juros ÷ receita líquida, 12 meses",
            fonte=fonte,
            procedencia="calculado",
            secao="riscos",
            mini=120,
        )
    )
    bloco.graficos.append(
        grafico(
            "juros-sobre-receita",
            "Quanto da receita da União vai para os juros",
            [serie("razao", "Juros ÷ receita líquida, 12 meses", razao, desde=inicio)],
            unidade="% da receita líquida",
            casas=0,
            periodicidade="M",
            janela_anos=20,
            fonte=fonte,
            nota=(
                "Juros: os do Governo Federal e do Banco Central em 12 meses, como o Banco "
                "Central apura (os que se pagam menos os que se recebem, nas reservas e nos "
                "empréstimos; o resultado do swap cambial entra). Receita: a líquida do "
                "Governo Central em 12 meses, do Tesouro (o que arrecada menos o que a lei "
                "manda repassar a estados e municípios). As duas pontas são do mesmo governo, "
                "que tem quase toda a dívida. Agências de risco olham a mesma razão: quanto "
                "maior, menos sobra para o resto e mais o orçamento depende da Selic."
            ),
        )
    )
    bloco.alertas.append(
        alerta(
            "juros-sobre-receita",
            FISCAL,
            "Juros sobre a receita da União",
            razao,
            pior_quando="alto",
            unidade="% da receita líquida",
            periodicidade="M",
            casas=0,
            fonte=fonte,
            procedencia="calculado",
        )
    )
    return bloco


def _vencimento(ctx: Contexto) -> Bloco:
    """Quanto da dívida bruta vence em até 12 meses: o que o governo precisa rolar no ano."""
    total, faixas = bcb_fiscal.cronograma_dbgg()
    curta = divida.parcela(faixas["até 1 ano"], total)
    if not curta:
        return Bloco()
    pib = dict(ctx.sgs("PIB_12M", HIST))
    quando, saldo = faixas["até 1 ano"][-1]
    no_pib = f"; {br(saldo / pib[quando] * 100)} % do PIB" if pib.get(quando) else ""
    bloco = Bloco()
    bloco.cartoes.append(
        cartao(
            "vence-em-12-meses",
            "Dívida bruta que vence em até 12 meses",
            curta,
            unidade="%",
            periodicidade="M",
            casas=1,
            detalhe=f"R$ {br(saldo / 1e6, 2)} tri{no_pib}",
            fonte=f"{bcb_fiscal.FONTE_CRONOGRAMA}; cálculo próprio",
            procedencia="calculado",
            secao="riscos",
            mini=120,
        )
    )
    bloco.graficos.append(
        grafico(
            "vence-em-12-meses",
            "Quanto da dívida vence em até um ano",
            [serie("curta", "Vence em até 12 meses", curta, desde=date(2006, 12, 1))],
            unidade="% da dívida bruta",
            casas=1,
            periodicidade="M",
            janela_anos=20,
            fonte=f"{bcb_fiscal.FONTE_CRONOGRAMA}; cálculo próprio",
            nota=(
                "Saldo da dívida bruta do governo geral com vencimento em até 12 meses, sobre "
                "o saldo total, pelo cronograma que o Banco Central publica. Inclui as "
                "operações compromissadas do Banco Central, quase todas de prazo curto. Quanto "
                "maior a parte que vence logo, mais dívida o governo precisa trocar por nova no "
                "ano, ao juro do momento."
            ),
        )
    )
    bloco.alertas.append(
        alerta(
            "vence-em-12-meses",
            FISCAL,
            "Dívida bruta que vence em até 12 meses",
            curta,
            pior_quando="alto",
            unidade="% da dívida bruta",
            periodicidade="M",
            fonte=f"{bcb_fiscal.FONTE_CRONOGRAMA}; cálculo próprio",
            procedencia="calculado",
        )
    )
    return bloco


# ------------------------------------------------------------------ riscos fiscais e jurídicos


def pib_anual_em_bilhoes(ctx: Contexto) -> dict[int, float]:
    """O PIB de cada ano fechado (o de 12 meses em dezembro), em R$ bilhões."""
    return {a: v / 1000 for a, v in em_dezembro(ctx.sgs("PIB_12M", 30)).items()}


def _justica(ctx: Contexto) -> Bloco:
    """As ações na Justiça contra a União e o que ela paga por sentença, pelo Anexo de Riscos
    Fiscais do PLDO; e a tabela-resumo dos riscos fiscais específicos."""
    pib = pib_anual_em_bilhoes(ctx)
    acoes = relatorios.ACOES_JUDICIAIS
    ano = max(acoes)
    possivel, provavel = acoes[ano]
    fonte = relatorios.FONTE_RISCOS_FISCAIS
    fonte_pib = f"{fonte}; PIB: {ctx.fonte_sgs('PIB_12M')}"
    pagas = relatorios.SENTENCAS_PAGAS
    ultimo_pago = max(a for a in pagas if a < relatorios.SENTENCAS_PREVISTAS_DESDE)
    pago, despesa = pagas[ultimo_pago]
    previsto = [a for a in pagas if a >= relatorios.SENTENCAS_PREVISTAS_DESDE]

    def no_pib(valores: dict[int, float]) -> list[Ponto]:
        return [(date(a, 1, 1), v / pib[a] * 100) for a, v in sorted(valores.items()) if a in pib]

    provavel_pib = no_pib({a: v[1] for a, v in acoes.items()})
    possivel_pib = no_pib({a: v[0] for a, v in acoes.items()})
    if not provavel_pib or provavel_pib[-1][0].year != ano:
        raise ValueError(f"sem o PIB de {ano} para pôr as ações em % do PIB")

    bloco = Bloco()
    bloco.cartoes += [
        Cartao(
            id="acoes-perda-provavel",
            rotulo="Ações contra a União com perda provável",
            valor=provavel,
            unidade="R$ bilhões",
            casas=0,
            referencia=date(ano, 1, 1),
            periodicidade="A",
            detalhe=(
                f"{br(provavel_pib[-1][1])} % do PIB; perda possível: R$ {br(possivel / 1000, 2)} "
                "tri"
            ),
            fonte=fonte,
            secao="riscos",
            mini=[(date(a, 1, 1), v[1]) for a, v in sorted(acoes.items())],
        ),
        Cartao(
            id="sentencas-pagas",
            rotulo="Sentenças judiciais pagas pela União",
            valor=pago,
            unidade="R$ bilhões",
            casas=0,
            referencia=date(ultimo_pago, 1, 1),
            periodicidade="A",
            detalhe=f"{br(pago / despesa * 100)} % da despesa primária"
            + (
                f"; {previsto[0]}: R$ {br(pagas[previsto[0]][0], 0)} bi no orçamento"
                if previsto
                else ""
            ),
            fonte=fonte,
            secao="riscos",
            mini=[(date(a, 1, 1), v[0]) for a, v in sorted(pagas.items()) if a <= ultimo_pago],
        ),
    ]
    bloco.graficos += [
        grafico(
            "acoes-judiciais",
            "Ações na Justiça que a União pode perder",
            [
                serie("provavel", "Perda provável", provavel_pib, casas=1),
                serie("possivel", "Perda possível", possivel_pib, casas=1),
            ],
            unidade="% do PIB",
            casas=1,
            periodicidade="A",
            fonte=fonte_pib,
            nota=(
                "O valor das ações contra a União, as autarquias, as estatais dependentes e o "
                "Banco Central, como a AGU classifica: perda provável quando o STF, o STJ ou o "
                "TST já decidiu contra o governo; possível quando o caso está para ser julgado "
                "nesses tribunais. Entram as ações acima de R$ 1 bilhão (ou as iguais somadas). "
                "Não é conta a pagar: muda com cada julgamento e com a reclassificação (a "
                "queda de 2024 e 2025 veio de ações da Previdência que passaram a risco "
                "remoto). Em reais, dividido pelo PIB do ano."
            ),
        ),
        grafico(
            "sentencas-judiciais",
            "O que a União paga por decisão da Justiça",
            [
                serie(
                    "pagas",
                    "Precatórios e outras sentenças",
                    [(date(a, 1, 1), p / d * 100) for a, (p, d) in sorted(pagas.items())],
                    casas=1,
                ),
            ],
            tipo="barras",
            unidade="% da despesa primária",
            casas=1,
            periodicidade="A",
            fonte=fonte,
            nota=(
                "Tudo o que a União pagou em cumprimento de sentença judicial (precatórios e "
                "requisições de pequeno valor), sobre a despesa primária do ano. "
                + (
                    f"{', '.join(str(a) for a in previsto)}: o que está no orçamento, não o "
                    "que foi pago. "
                    if previsto
                    else ""
                )
                + "O salto de 2023 é o pagamento dos precatórios adiados, depois que o STF "
                "derrubou o limite (ADI 7064)."
            ),
        ),
    ]
    anterior = ano - 1
    bloco.tabelas.append(
        Tabela(
            id="riscos-fiscais-uniao",
            titulo="Os riscos fiscais da União, pelo Tesouro",
            subtitulo=f"Estoque em R$ bilhões, no fim de {anterior} e de {ano}",
            colunas=[str(anterior), str(ano), f"{ano}, % do PIB"],
            linhas=[
                LinhaTabela(
                    rotulo=f"{r.item} ({r.efeito})",
                    valores=[
                        r.anterior,
                        r.ultimo,
                        round(r.ultimo / pib[ano] * 100, 1) if ano in pib else None,
                    ],
                    unidade="",
                    casas=1,
                )
                for r in relatorios.RISCOS_FISCAIS
            ],
            fonte=fonte_pib,
            nota=(
                "Os itens maiores do quadro-resumo do Anexo de Riscos Fiscais da LDO. "
                '"Mais despesa": o que a União pode ter de pagar (sentenças, garantias '
                'honradas). "Menos receita": o que tem a receber e pode não receber (dívidas '
                "dos estados, empréstimos dos fundos e do Fies). São riscos, não perdas: só "
                "uma parte vira gasto, e o anexo não soma tudo como conta a pagar. A dívida "
                "ativa está em Impostos."
            ),
        )
    )
    return bloco


# Países parecidos, os da América Latina primeiro (CLAUDE.md: "os parecidos (emergentes,
# América Latina) primeiro e o mesmo número e fonte para todos").
PARES_DE_GOVERNANCA = ["MEX", "COL", "CHL", "PER", "ARG", "ZAF", "IND", "IDN", "TUR"]


def tabela_de_governanca(
    dados: dict[tuple[str, str], dict[int, float]], nomes: dict[str, str]
) -> Tabela | None:
    """A nota de 0 a 100 do Banco Mundial nas quatro dimensões, o Brasil (agora e dez anos
    antes) e os pares. Sem o Brasil no ano mais novo, nada."""
    codigos = list(banco_mundial.GOVERNANCA)
    anos_br = [a for a in dados.get(("BRA", codigos[0]), {})]
    if not anos_br:
        return None
    ano = max(anos_br)
    antes = ano - 10

    def linha(iso: str, rotulo: str, quando: int) -> LinhaTabela | None:
        valores = [dados.get((iso, c), {}).get(quando) for c in codigos]
        if all(v is None for v in valores):
            return None
        return LinhaTabela(
            rotulo=rotulo,
            valores=[round(v, 0) if v is not None else None for v in valores],
            unidade="",
            casas=0,
        )

    candidatas = [
        linha("BRA", f"Brasil, {ano}", ano),
        linha("BRA", f"Brasil, {antes}", antes),
        *[linha(iso, nomes[iso], ano) for iso in PARES_DE_GOVERNANCA],
    ]
    linhas = [x for x in candidatas if x is not None]

    def faixa(codigo: str) -> str:
        baixo = dados.get(("BRA", f"{codigo}_LB"), {}).get(ano)
        alto = dados.get(("BRA", f"{codigo}_UB"), {}).get(ano)
        return f"de {br(baixo, 0)} a {br(alto, 0)}" if baixo and alto else ""

    faixa_ge, faixa_rl = faixa("GOV_WGI_GE.SC"), faixa("GOV_WGI_RL.SC")
    erro = (
        f" A margem de erro é grande: com 90 % de confiança, a nota do Brasil fica {faixa_ge} "
        f"em eficácia do governo e {faixa_rl} em estado de direito. Diferença de poucos "
        "pontos entre países não quer dizer muito."
        if faixa_ge and faixa_rl
        else ""
    )
    return Tabela(
        id="governanca",
        titulo="Governança: o Brasil e países parecidos",
        subtitulo=f"Nota de 0 a 100 do Banco Mundial em {ano}; mais é melhor",
        colunas=list(banco_mundial.GOVERNANCA.values()),
        linhas=linhas,
        fonte=f"{banco_mundial.FONTE_GOVERNANCA} ({', '.join(codigos)})",
        nota=(
            "O Banco Mundial junta dezenas de pesquisas e avaliações (de empresas, ONGs, "
            "organismos e da população) numa nota por país, todo ano, com o mesmo método para "
            "todos. Eficácia do governo: a qualidade dos serviços públicos e das políticas. "
            "Estado de direito: se contratos e leis valem e a Justiça funciona. Qualidade da "
            "regulação: se as regras ajudam o setor privado. Controle da corrupção: o quanto "
            "o poder público é usado para ganho privado." + erro
        ),
    )


def _governanca(ctx: Contexto) -> Bloco:
    codigos = list(banco_mundial.GOVERNANCA)
    faixas = [f"{c}_{p}" for c in codigos[:2] for p in ("LB", "UB")]
    dados = banco_mundial.varios(
        ["BRA", *PARES_DE_GOVERNANCA], [*codigos, *faixas], ctx.hoje.year - 12, ctx.hoje.year
    )
    nomes = {iso: mundo.nome_do_pais(iso) for iso in PARES_DE_GOVERNANCA}
    tabela = tabela_de_governanca(dados, nomes)
    bloco = Bloco()
    if tabela:
        bloco.tabelas.append(tabela)
    return bloco


def _inss_ate_2100(ctx: Contexto) -> Bloco:
    """A projeção atuarial do INSS do PLDO, com o realizado do RTN na frente."""
    projecao = relatorios.RGPS_PROJECAO
    primeiro = min(projecao)
    rtn = tesouro_rtn.serie_historica()
    pib_12m = ctx.sgs("PIB_12M", 30)
    beneficios = em_dezembro(contas.em_pct_do_pib(rtn["rgps"], pib_12m))
    arrecadacao = em_dezembro(contas.em_pct_do_pib(rtn["arrecadacao_rgps"], pib_12m))

    def junta(realizado: dict[int, float], indice: int) -> list[Ponto]:
        antes = [(date(a, 1, 1), v) for a, v in sorted(realizado.items()) if 2010 <= a < primeiro]
        return antes + [(date(a, 1, 1), v[indice]) for a, v in sorted(projecao.items())]

    corte = date(primeiro, 1, 1)
    meio = 2060
    necessidade = {a: v[2] for a, v in projecao.items()}
    fonte = f"{relatorios.FONTE_RGPS_PROJECAO}; realizado: Tesouro Nacional, RTN (tabela 1.1)"
    bloco = Bloco()
    bloco.cartoes.append(
        Cartao(
            id="inss-deficit-2060",
            rotulo=f"Déficit do INSS em {meio}, na projeção do governo",
            valor=necessidade[meio],
            unidade="% do PIB",
            casas=1,
            referencia=date(primeiro, 1, 1),
            periodicidade="A",
            detalhe=(
                f"{br(necessidade[primeiro])} % em {primeiro}; "
                f"{br(necessidade[max(projecao)])} % em {max(projecao)}"
            ),
            fonte=relatorios.FONTE_RGPS_PROJECAO,
            procedencia="oficial",
            secao="riscos",
            mini=[(date(a, 1, 1), v) for a, v in sorted(necessidade.items())],
        )
    )
    bloco.graficos.append(
        grafico(
            "inss-ate-2100",
            "O INSS até 2100: a projeção do governo",
            [
                serie("despesa", "Benefícios", junta(beneficios, 1), tracejado_desde=corte),
                serie("receita", "Contribuições", junta(arrecadacao, 0), tracejado_desde=corte),
            ],
            unidade="% do PIB",
            casas=1,
            periodicidade="A",
            fonte=fonte,
            nota=(
                "Até 2025, o realizado (Tesouro); depois, tracejado, a projeção atuarial que "
                "o Ministério da Previdência manda com o projeto da LDO todo ano, pela Lei de "
                "Responsabilidade Fiscal. A distância entre as linhas é o déficit. Método: até "
                "2030, a grade de parâmetros do Ministério da Fazenda; depois, a população "
                "projetada pela ONU e as regras de hoje (a reforma de 2019 inclusive), com o "
                "salário mínimo subindo com o PIB. Não há faixa de erro publicada nem "
                "projeção de mercado para comparar; a do governo muda a cada ano, com a grade "
                "e com a população."
            ),
            largura="inteira",
        )
    )
    return bloco


def _estados(ctx: Contexto) -> Bloco:
    """Os estados acima de algum limite de alerta (pessoal ou dívida) ou com CAPAG C ou D: a
    mesma conta de Estados › Perto dos limites (`estados.perto_dos_limites`)."""
    achado = estados.perto_dos_limites(estados.metricas_dos_limites(ctx))
    if achado is None:
        raise RuntimeError("sem o RGF dos estados")
    cartao, tabela = achado
    return Bloco(cartoes=[cartao], tabelas=[tabela])


# ------------------------------------------------------------------ a seção


def montar(ctx: Contexto) -> Secao:
    try:
        base = previsoes.linha_de_base_da_divida(ctx)
    except Exception as erro:
        print(f"    riscos: sem a linha de base do Focus ({str(erro)[:100]})")
        base = None

    # A dívida é o coração da aba: se ela falha, a seção falha (e fica a da rodada anterior).
    principal, frase, anos = _divida(ctx, base)
    blocos: list[Bloco] = [principal]
    dolar: list[Ponto] = []
    try:
        mercado, dolar = _mercado(ctx)
        blocos.append(mercado)
    except Exception as erro:
        print(f"    riscos: mercado ficou de fora ({str(erro)[:100]})")
    demais: list[tuple[str, Callable[[], Bloco]]] = [
        ("contas externas", lambda: _externo(ctx)),
        ("crédito", lambda: _credito(ctx)),
        ("inflação", lambda: _inflacao(ctx)),
        ("expectativa de inflação", lambda: _expectativa(ctx)),
        ("juro real e inflação implícita", lambda: _juro_real_e_implicita(ctx)),
        ("liquidez e hiato de crédito", lambda: _liquidez_e_hiato(ctx)),
        (
            "estresse",
            lambda: _estresse(ctx, base, anos, dolar) if dolar else Bloco(),
        ),
        ("previdência", lambda: _previdencia(ctx)),
        ("envelhecimento", lambda: _envelhecimento(ctx)),
        ("energia", lambda: _energia(ctx)),
        ("nota de crédito", lambda: _nota(ctx)),
        ("elasticidades", _elasticidades),
        ("juros sobre a receita", lambda: _juros_sobre_receita(ctx)),
        ("vencimento da dívida", lambda: _vencimento(ctx)),
        ("ações na Justiça", lambda: _justica(ctx)),
        ("governança", lambda: _governanca(ctx)),
        ("INSS até 2100", lambda: _inss_ate_2100(ctx)),
        ("estados perto dos limites", lambda: _estados(ctx)),
    ]
    for nome, montar_bloco in demais:
        try:
            blocos.append(montar_bloco())
        except Exception as erro:
            print(f"    riscos: {nome} ficou de fora ({str(erro)[:100]})")

    cartoes = [c for b in blocos for c in b.cartoes]
    graficos = [g for b in blocos for g in b.graficos]
    tabelas = [t for b in blocos for t in b.tabelas]
    alertas = [a for b in blocos for a in b.alertas if a.id in NO_PAINEL]
    # O painel na ordem dos grupos, não na dos blocos.
    ordem = [FISCAL, EXTERNO, INFLACAO, CREDITO, MERCADO, LONGO]
    alertas.sort(key=lambda a: ordem.index(a.grupo))
    acesos = [a for a in alertas if a.pior_que >= ACESO]
    # Entre os quatro números à vista: quantos alertas estão acesos.
    cartoes.insert(
        min(2, len(cartoes)),
        Cartao(
            id="alertas-acesos",
            rotulo="Indicadores no quinto pior da própria história",
            valor=float(len(acesos)),
            unidade=f"de {len(alertas)}",
            casas=0,
            referencia=ctx.hoje,
            periodicidade="D",
            detalhe=_mais_grave(acesos),
            fonte="Painel de alerta desta página (cada linha com a sua fonte); cálculo próprio",
            procedencia="calculado",
            secao="riscos",
        ),
    )
    edicao = ""
    with contextlib.suppress(Exception):
        edicao = f" Focus de {periodo(bcb_focus.data_da_ultima_edicao(), 'D')}."
    resumo = (
        f"{frase} No painel de alerta, {len(acesos)} de {len(alertas)} indicadores estão no "
        "quinto pior da própria história. Nada aqui é previsão de crise: são medidas de "
        f"quanto a economia aguenta, com a fonte ao lado.{edicao}"
    )
    return Secao(
        id="riscos",
        titulo="Riscos",
        resumo=resumo,
        cartoes=cartoes,
        graficos=graficos,
        tabelas=tabelas,
        alertas=alertas,
        gerado_em=ctx.agora(),
    )
