"""Riscos: o que pode dar errado, medido com dado oficial.

Sete blocos, cada um num `try` próprio (um que falha não derruba os outros):

1. a dívida se sustenta? (juro da dívida contra crescimento, primário que a estabiliza, leque);
2. o que o mercado cobra (volatilidade do dólar, queda da bolsa);
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

from sacibras import alertas, contas, leis, relatorios
from sacibras.fontes import bcb_focus, ibge_projecao, ipeadata, ons, tesouro_rtn
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
    SimuladorDivida,
    Tabela,
)
from sacibras.secoes import estados, inflacao, previsoes
from sacibras.secoes.base import Contexto, br, cartao, grafico, periodo, serie
from sacibras.tipos import Periodicidade, Ponto

HIST = 25
"""Anos de história pedidos ao SGS: o painel compara hoje com tudo desde jan/2001 (ou desde
que a série existe)."""
ACESO = 80.0
"""Pior que esta parte da própria história = "aceso" (o quinto pior). O site usa o mesmo corte."""
ANOS_DO_LEQUE = 5
ANOS_DO_ESTRESSE = 4

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
    """A janela em que se medem dólar, bolsa e Selic."""
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


def _divida(ctx: Contexto, base: SimuladorDivida | None) -> tuple[Bloco, str, Anos]:
    dbgg = ctx.sgs("DBGG", HIST)
    juros = ctx.sgs("NFSP_JUROS_12M", HIST)
    primario = contas.escalar(ctx.sgs("NFSP_PRIMARIO_12M", HIST), -1)
    nominal = contas.escalar(ctx.sgs("NFSP_NOMINAL_12M", HIST), -1)
    pib = ctx.sgs("PIB_12M", HIST)
    atrelada = ctx.sgs("DIVIDA_IDX_SELIC", HIST)

    estoque = dict(dbgg)
    # O juro que a dívida paga: os juros de 12 meses divididos pelo estoque (a mesma conta
    # do simulador). Juros do setor público consolidado sobre a dívida bruta do governo geral.
    juro_divida = [(d, j / estoque[d] * 100) for d, j in juros if estoque.get(d)]
    crescimento = contas.variacao(pib, 12)
    folga = contas.subtrair(juro_divida, crescimento)
    necessario = risco.serie_do_primario_que_estabiliza(dbgg, juro_divida, crescimento)
    falta = contas.subtrair(necessario, primario)
    juros_reais = contas.escalar(ctx.sgs("NFSP_JUROS_12M_RS", HIST), 1 / 1000)
    prazo = ctx.sgs("DIVIDA_PRAZO_MEDIO", HIST)

    fonte_conta = (
        f"{ctx.fonte_sgs('DBGG', 'NFSP_JUROS_12M', 'NFSP_PRIMARIO_12M', 'PIB_12M')}; "
        "cálculo próprio"
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
            "Primário que estabiliza a dívida",
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
            detalhe="juros de 12 meses ÷ dívida bruta",
            fonte=fonte_conta,
            procedencia="calculado",
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
                "Conta: dívida × (juro − crescimento) ÷ (1 + crescimento). Juro: o que a dívida "
                "pagou em 12 meses (juros do setor público ÷ dívida bruta). Crescimento: o do "
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
                "pequeno déficit."
            ),
        ),
    ]
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
            fonte=f"{base.fonte}; {ctx.fonte_sgs('IPCA_12M', 'PIB_VAR_ANUAL')}",
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
                "dívida cambial."
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


def _mercado(ctx: Contexto) -> tuple[Bloco, list[Ponto], list[Ponto]]:
    dolar = ctx.sgs("DOLAR", HIST + 2)
    ibov = ipeadata.serie(ipeadata.IBOVESPA, date(1999, 1, 1))
    fonte_ibov = "IPEADATA (série GM366_IBVSP366, fechamento do Ibovespa)"
    vol_dolar = risco.volatilidade(dolar)
    vol_ibov = risco.volatilidade(ibov)
    queda = risco.queda_desde_o_pico(ibov)
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
        cartao(
            "queda-ibovespa",
            "Ibovespa: distância do pico",
            queda,
            unidade="%",
            periodicidade="D",
            casas=1,
            detalhe="abaixo do maior fechamento desde 1999",
            fonte=f"{fonte_ibov}; cálculo próprio",
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
        grafico(
            "queda-ibovespa",
            "Ibovespa: quanto abaixo do pico",
            [serie("queda", "Distância do maior fechamento até a data", semanal(queda), casas=1)],
            tipo="area",
            unidade="%",
            casas=1,
            periodicidade="D",
            janela_anos=10,
            fonte=f"{fonte_ibov}; cálculo próprio",
            nota=(
                "Em pontos do índice, sem descontar a inflação. Zero é recorde. Um ponto por "
                "semana."
            ),
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
        alerta(
            "vol-ibovespa",
            MERCADO,
            "Volatilidade do Ibovespa, 21 dias",
            vol_ibov,
            pior_quando="alto",
            unidade="% a.a.",
            periodicidade="D",
            fonte=f"{fonte_ibov}; cálculo próprio",
            procedencia="calculado",
        ),
        alerta(
            "queda-ibovespa",
            MERCADO,
            "Ibovespa: distância do pico",
            queda,
            pior_quando="baixo",
            unidade="%",
            periodicidade="D",
            fonte=f"{fonte_ibov}; cálculo próprio",
            procedencia="calculado",
        ),
    ]
    return bloco, dolar, ibov


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


# ------------------------------------------------------------------ 6. estresse


def _estresse(
    ctx: Contexto,
    base: SimuladorDivida | None,
    anos: dict[int, risco.Choque],
    dolar: list[Ponto],
    ibov: list[Ponto],
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
    quedas: list[float | None] = []
    juros: list[float | None] = []
    piores_pibs: list[float | None] = []
    dolar_hoje: list[float | None] = []
    ibov_hoje: list[float | None] = []
    divida_a_mais: list[float | None] = []
    caminhos: list[tuple[Episodio, list[float]]] = []
    for ep in EPISODIOS:
        alta = risco.maior_alta(dolar, ep.inicio, ep.fim)
        queda = risco.maior_queda(ibov, ep.inicio, ep.fim)
        altas.append(alta)
        quedas.append(queda)
        juros.append(risco.maior_mudanca(selic, ep.inicio, ep.fim))
        do_episodio = [pib[a] for a in ep.anos if a in pib]
        piores_pibs.append(min(do_episodio) if do_episodio else None)
        dolar_hoje.append(dolar[-1][1] * (1 + alta / 100) if alta is not None else None)
        ibov_hoje.append(ibov[-1][1] * (1 + queda / 100) if queda is not None else None)
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
        LinhaTabela(rotulo="Ibovespa: maior queda na janela", valores=quedas, unidade="%", casas=0),
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
        LinhaTabela(
            rotulo=f"O Ibovespa de hoje ({br(ibov[-1][1] / 1000, 0)} mil) com a mesma queda",
            valores=[v / 1000 if v is not None else None for v in ibov_hoje],
            unidade="mil pontos",
            casas=0,
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
                "O que cada crise fez com dólar, bolsa, juro e PIB, e o mesmo tranco aplicado "
                "a hoje"
            ),
            colunas=colunas,
            linhas=linhas,
            fonte=(
                f"{ctx.fonte_sgs('DOLAR', 'SELIC_META', 'PIB_VAR_ANUAL')}; IPEADATA (Ibovespa); "
                "cálculo próprio"
            ),
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
    if base and caminhos:
        partida = (date(base.ano_inicial, 1, 1), base.divida_inicial)
        futuros = base.anos[:n]

        def caminho_serie(valores: list[float]) -> list[Ponto]:
            return [partida, *[(date(a, 1, 1), v) for a, v in zip(futuros, valores, strict=True)]]

        bloco.graficos.append(
            grafico(
                "estresse-divida",
                "A dívida se cada crise se repetisse agora",
                [
                    serie(
                        "base",
                        "Linha de base (hipóteses do Focus)",
                        caminho_serie(linha_de_base),
                        papel="consenso",
                        casas=1,
                    ),
                    *[
                        serie(
                            f"ep-{ep.id}",
                            ep.nome,
                            caminho_serie(caminho),
                            papel="previsao",
                            casas=1,
                        )
                        for ep, caminho in caminhos
                    ],
                ],
                unidade="% do PIB",
                casas=1,
                periodicidade="A",
                fonte=f"{base.fonte}; {ctx.fonte_sgs('IPCA_12M', 'PIB_VAR_ANUAL')}",
                nota=(
                    "Método: para cada episódio, mede-se quanto crescimento, primário, juro da "
                    "dívida e inflação dos anos da crise se afastaram da média dos dois anos "
                    "anteriores; esses desvios são somados aos primeiros anos da linha de base "
                    "do simulador da dívida, e depois a base volta. A dívida que subiu "
                    "continua lá, rendendo juro. Ordem de grandeza: não separa a dívida cambial "
                    "nem o que entra na dívida sem passar pelo primário."
                ),
                largura="inteira",
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
    ibov: list[Ponto] = []
    try:
        mercado, dolar, ibov = _mercado(ctx)
        blocos.append(mercado)
    except Exception as erro:
        print(f"    riscos: mercado ficou de fora ({str(erro)[:100]})")
    demais: list[tuple[str, Callable[[], Bloco]]] = [
        ("contas externas", lambda: _externo(ctx)),
        ("crédito", lambda: _credito(ctx)),
        ("inflação", lambda: _inflacao(ctx)),
        (
            "estresse",
            lambda: _estresse(ctx, base, anos, dolar, ibov) if dolar and ibov else Bloco(),
        ),
        ("previdência", lambda: _previdencia(ctx)),
        ("envelhecimento", lambda: _envelhecimento(ctx)),
        ("energia", lambda: _energia(ctx)),
        ("nota de crédito", lambda: _nota(ctx)),
        ("elasticidades", _elasticidades),
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
    alertas = [a for b in blocos for a in b.alertas]
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
