"""As contas da aba de riscos: sustentabilidade da dívida, leque de trajetórias, posição de um
indicador na própria história, volatilidade e queda desde o pico.

Tudo aqui é conta sobre série oficial; nenhuma função fala com fonte. O que cada conta supõe
está dito na docstring e repetido na nota do gráfico que a usa.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from sacibras.modelos import divida
from sacibras.tipos import Ponto

PiorQuando = Literal["alto", "baixo"]
Choque = tuple[float, float, float, float]
"""Desvios, em pontos percentuais, de (juro, crescimento, inflação, primário)."""


def primario_que_estabiliza(divida_pib: float, juro: float, crescimento_nominal: float) -> float:
    """O resultado primário (% do PIB) que mantém a dívida parada em % do PIB.

    Da conta d₊₁ = d · (1 + i) / (1 + γ) − p, com d₊₁ = d: p = d · (i − γ) / (1 + γ).
    `juro` (i) e `crescimento_nominal` (γ) em % ao ano; `divida_pib` (d) em % do PIB.
    """
    return divida_pib * (juro - crescimento_nominal) / (100 + crescimento_nominal)


def serie_do_primario_que_estabiliza(
    divida_pib: list[Ponto], juro: list[Ponto], crescimento_nominal: list[Ponto]
) -> list[Ponto]:
    """A mesma conta, mês a mês, onde as três séries têm valor."""
    j, g = dict(juro), dict(crescimento_nominal)
    return [(d, primario_que_estabiliza(v, j[d], g[d])) for d, v in divida_pib if d in j and d in g]


# ------------------------------------------------------------------ leque da dívida


@dataclass(frozen=True)
class Leque:
    """Para cada ano à frente, onde ficou a dívida nos sorteios (percentis, % do PIB)."""

    p10: list[float]
    p25: list[float]
    mediana: list[float]
    p75: list[float]
    p90: list[float]
    chance_de_subir: float
    """Em quantos % dos sorteios a dívida do último ano ficou acima da inicial."""


def _percentil(ordenados: list[float], p: float) -> float:
    """Percentil por interpolação linear numa lista já ordenada (p de 0 a 100)."""
    if not ordenados:
        raise ValueError("lista vazia")
    posicao = (len(ordenados) - 1) * p / 100
    baixo = math.floor(posicao)
    alto = min(baixo + 1, len(ordenados) - 1)
    return ordenados[baixo] + (ordenados[alto] - ordenados[baixo]) * (posicao - baixo)


def choques_da_historia(anos: dict[int, Choque]) -> list[Choque]:
    """O desvio de cada ano em relação à média de todos, em ordem de ano.

    `anos` traz o nível de (juro, crescimento, inflação, primário) em cada ano da história.
    """
    if not anos:
        return []
    ordem = sorted(anos)
    medias = [sum(anos[a][k] for a in ordem) / len(ordem) for k in range(4)]
    return [
        (
            anos[a][0] - medias[0],
            anos[a][1] - medias[1],
            anos[a][2] - medias[2],
            anos[a][3] - medias[3],
        )
        for a in ordem
    ]


def leque(
    inicial: float,
    juro: list[float],
    crescimento: list[float],
    inflacao: list[float],
    primario: list[float],
    choques: list[Choque],
    *,
    sorteios: int = 4000,
    bloco: int = 2,
    semente: int = 20261114,
) -> Leque:
    """Trajetórias da dívida com a linha de base somada a choques sorteados da história.

    Cada sorteio percorre os anos à frente tirando, com reposição, blocos de `bloco` anos
    seguidos de `choques` (ano ruim costuma vir depois de ano ruim; os quatro desvios de um
    mesmo ano andam juntos, como andaram). A semente é fixa: a mesma entrada dá a mesma saída.
    """
    if not choques:
        raise ValueError("sem choques históricos")
    sorteio = random.Random(semente)
    n = len(juro)
    por_ano: list[list[float]] = [[] for _ in range(n)]
    acima = 0
    for _ in range(sorteios):
        desvios: list[Choque] = []
        while len(desvios) < n:
            comeco = sorteio.randrange(len(choques))
            desvios.extend(choques[(comeco + k) % len(choques)] for k in range(bloco))
        caminho = divida.trajetoria(
            inicial,
            [juro[i] + desvios[i][0] for i in range(n)],
            [crescimento[i] + desvios[i][1] for i in range(n)],
            [inflacao[i] + desvios[i][2] for i in range(n)],
            [primario[i] + desvios[i][3] for i in range(n)],
        )
        for i, valor in enumerate(caminho):
            por_ano[i].append(valor)
        acima += caminho[-1] > inicial
    for valores in por_ano:
        valores.sort()
    return Leque(
        p10=[_percentil(v, 10) for v in por_ano],
        p25=[_percentil(v, 25) for v in por_ano],
        mediana=[_percentil(v, 50) for v in por_ano],
        p75=[_percentil(v, 75) for v in por_ano],
        p90=[_percentil(v, 90) for v in por_ano],
        chance_de_subir=acima / sorteios * 100,
    )


# ------------------------------------------------------------------ posição na história


@dataclass(frozen=True)
class Posicao:
    """Onde o valor de hoje está na história do próprio indicador."""

    pior_que: float
    """% das observações da história em que o indicador esteve em situação melhor que hoje."""
    minimo: float
    maximo: float
    mediana: float
    desde: date


def posicao_na_historia(pontos: list[Ponto], pior_quando: PiorQuando) -> Posicao:
    """A posição do último ponto entre todos os pontos (ele incluído no denominador)."""
    if len(pontos) < 2:
        raise ValueError("história curta demais")
    atual = pontos[-1][1]
    valores = sorted(v for _, v in pontos)
    if pior_quando == "alto":
        melhores = sum(1 for v in valores if v < atual)
    else:
        melhores = sum(1 for v in valores if v > atual)
    return Posicao(
        pior_que=melhores / len(valores) * 100,
        minimo=valores[0],
        maximo=valores[-1],
        mediana=_percentil(valores, 50),
        desde=pontos[0][0],
    )


def ha_um_ano(pontos: list[Ponto]) -> Ponto | None:
    """O ponto de um ano antes do último (o último com data até 365 dias antes), se houver."""
    alvo = pontos[-1][0] - timedelta(days=365)
    antes = [p for p in pontos if p[0] <= alvo]
    # Série com buraco grande (mais de 45 dias antes do alvo) não serve de comparação.
    if not antes or (alvo - antes[-1][0]).days > 45:
        return None
    return antes[-1]


def pior_que(valor: float, pontos: list[Ponto], pior_quando: PiorQuando) -> float:
    """% dos pontos de `pontos` em situação melhor que `valor` (a régua de toda a história)."""
    valores = [v for _, v in pontos]
    if pior_quando == "alto":
        melhores = sum(1 for v in valores if v < valor)
    else:
        melhores = sum(1 for v in valores if v > valor)
    return melhores / len(valores) * 100


# ------------------------------------------------------------------ preços


def volatilidade(pontos: list[Ponto], janela: int = 21, por_ano: int = 252) -> list[Ponto]:
    """Desvio-padrão dos retornos diários (log) nos últimos `janela` pregões, levado ao ano, %."""
    retornos = [
        (pontos[i][0], math.log(pontos[i][1] / pontos[i - 1][1]))
        for i in range(1, len(pontos))
        if pontos[i][1] > 0 and pontos[i - 1][1] > 0
    ]
    saida: list[Ponto] = []
    for i in range(janela - 1, len(retornos)):
        trecho = [r for _, r in retornos[i - janela + 1 : i + 1]]
        media = sum(trecho) / janela
        variancia = sum((r - media) ** 2 for r in trecho) / (janela - 1)
        saida.append((retornos[i][0], math.sqrt(variancia * por_ano) * 100))
    return saida


def queda_desde_o_pico(pontos: list[Ponto]) -> list[Ponto]:
    """Em cada data, quanto o nível está abaixo do maior já visto até ali (% ≤ 0)."""
    pico = -math.inf
    saida: list[Ponto] = []
    for d, v in pontos:
        pico = max(pico, v)
        saida.append((d, (v / pico - 1) * 100 if pico > 0 else 0.0))
    return saida


def maior_alta(pontos: list[Ponto], inicio: date, fim: date) -> float | None:
    """A maior subida (%) de um ponto a outro posterior, dentro da janela."""
    minimo, melhor = math.inf, None
    for d, v in pontos:
        if d < inicio or d > fim or v <= 0:
            continue
        minimo = min(minimo, v)
        alta = (v / minimo - 1) * 100
        melhor = alta if melhor is None else max(melhor, alta)
    return melhor


def maior_queda(pontos: list[Ponto], inicio: date, fim: date) -> float | None:
    """A maior descida (%, negativa) de um ponto a outro posterior, dentro da janela."""
    maximo, pior = -math.inf, None
    for d, v in pontos:
        if d < inicio or d > fim or v <= 0:
            continue
        maximo = max(maximo, v)
        queda = (v / maximo - 1) * 100
        pior = queda if pior is None else min(pior, queda)
    return pior


def maior_mudanca(pontos: list[Ponto], inicio: date, fim: date) -> float | None:
    """A maior distância (com sinal) entre o valor do começo da janela e outro dentro dela."""
    dentro = [v for d, v in pontos if inicio <= d <= fim]
    if not dentro:
        return None
    partida = dentro[0]
    return max((v - partida for v in dentro), key=abs)


# ------------------------------------------------------------------ estresse


def repetir_episodio(
    inicial: float,
    juro: list[float],
    crescimento: list[float],
    inflacao: list[float],
    primario: list[float],
    choques: list[Choque],
) -> list[float]:
    """A dívida ano a ano com os `choques` do episódio somados aos primeiros anos da linha de
    base; depois deles, a base volta (a dívida que subiu continua lá)."""
    n = len(juro)
    zero: Choque = (0.0, 0.0, 0.0, 0.0)
    c = [choques[i] if i < len(choques) else zero for i in range(n)]
    return divida.trajetoria(
        inicial,
        [juro[i] + c[i][0] for i in range(n)],
        [crescimento[i] + c[i][1] for i in range(n)],
        [inflacao[i] + c[i][2] for i in range(n)],
        [primario[i] + c[i][3] for i in range(n)],
    )


def choques_do_episodio(anos: dict[int, Choque], do_episodio: list[int]) -> list[Choque] | None:
    """O desvio de cada ano do episódio em relação à média dos dois anos anteriores a ele.

    Devolve None se a história não cobre o episódio e os dois anos de antes.
    """
    if not do_episodio:
        return None
    antes = [do_episodio[0] - 2, do_episodio[0] - 1]
    if any(a not in anos for a in [*antes, *do_episodio]):
        return None
    base = [sum(anos[a][k] for a in antes) / 2 for k in range(4)]
    return [
        (
            anos[a][0] - base[0],
            anos[a][1] - base[1],
            anos[a][2] - base[2],
            anos[a][3] - base[3],
        )
        for a in do_episodio
    ]
