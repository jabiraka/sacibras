"""Três contas do Laboratório sobre pressão e ajuste, sem rede (Caio, 19/11/2026: *"essas
métricas vão nos ajudar a ver o desenrolar e de onde está vindo se tiver uma crise, bem como
oq poderíamos ter feito pra prevenir, o foco principal hj está no ajuste fiscal"*):

- o dólar repartido entre o que veio de fora (o dólar contra os outros emergentes) e o que é
  só do Brasil;
- a dívida que haveria se o primário tivesse sido outro (contabilidade, com o juro e o
  crescimento que aconteceram);
- o primário que se esperava para um ano, anos antes, contra o que veio.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from itertools import pairwise

from sacibras.modelos import estatistica
from sacibras.tipos import Ponto

# ------------------------------------------------------------------ o dólar: mundo ou Brasil


def variacoes(serie: Mapping[date, float], dias: Sequence[date]) -> list[float]:
    """A variação em log × 100 (quase %) entre cada dia de `dias` e o anterior."""
    return [100 * math.log(serie[b] / serie[a]) for a, b in pairwise(dias)]


def composta(log_vezes_100: float) -> float:
    """De soma de logs × 100 para variação em %."""
    return (math.exp(log_vezes_100 / 100) - 1) * 100


@dataclass(frozen=True)
class Reparticao:
    dia: date
    total: float
    """A variação do dólar no Brasil na janela, em log × 100."""
    de_fora: float
    """β × a variação do dólar contra os emergentes na mesma janela."""
    beta: float

    @property
    def do_brasil(self) -> float:
        return self.total - self.de_fora


def _betas_moveis(y: Sequence[float], x: Sequence[float], janela: int) -> list[float | None]:
    """O β de y em x (com constante) nas `janela` observações até cada ponto, por somas
    acumuladas; None enquanto não há janela cheia."""
    n = len(y)
    sx, sy, sxx, sxy = [0.0], [0.0], [0.0], [0.0]
    for a, b in zip(x, y, strict=True):
        sx.append(sx[-1] + a)
        sy.append(sy[-1] + b)
        sxx.append(sxx[-1] + a * a)
        sxy.append(sxy[-1] + a * b)
    saida: list[float | None] = []
    for t in range(n):
        i = t + 1 - janela
        if i < 0:
            saida.append(None)
            continue
        mx, my = (sx[t + 1] - sx[i]) / janela, (sy[t + 1] - sy[i]) / janela
        var = (sxx[t + 1] - sxx[i]) / janela - mx * mx
        cov = (sxy[t + 1] - sxy[i]) / janela - mx * my
        saida.append(cov / var if var > 1e-12 else None)
    return saida


def repartir_dolar(
    dias: Sequence[date],
    brasil: Sequence[float],
    emergentes: Sequence[float],
    *,
    janela: int = 252,
    janela_beta: int = 1260,
) -> list[Reparticao]:
    """Para cada dia, a variação do dólar no Brasil nos `janela` dias úteis até ele, repartida
    em duas: β × a variação do dólar contra os emergentes (o que veio de fora) e o resto (o
    que é do Brasil). β: quanto o dólar no Brasil costuma andar para cada 1 % do dólar contra
    os emergentes, medido nos `janela_beta` dias até aquele dia.

    `dias` são os dias das variações (um a menos que os das cotações)."""
    betas = _betas_moveis(brasil, emergentes, janela_beta)
    ay, ax = [0.0], [0.0]
    for a, b in zip(emergentes, brasil, strict=True):
        ax.append(ax[-1] + a)
        ay.append(ay[-1] + b)
    saida: list[Reparticao] = []
    for t, dia in enumerate(dias):
        beta = betas[t]
        if beta is None or t + 1 < janela:
            continue
        total = ay[t + 1] - ay[t + 1 - janela]
        fora = beta * (ax[t + 1] - ax[t + 1 - janela])
        saida.append(Reparticao(dia=dia, total=total, de_fora=fora, beta=beta))
    return saida


def beta_com_intervalo(
    brasil: Sequence[float], emergentes: Sequence[float], janela_beta: int = 1260
) -> tuple[float, float, float]:
    """(β, de, até) nos últimos `janela_beta` dias: o mesmo β do último ponto de
    `repartir_dolar`, com o intervalo de 90 % (erro de Newey-West)."""
    y, x = list(brasil[-janela_beta:]), list(emergentes[-janela_beta:])
    r = estatistica.mqo(y, [[v] for v in x])
    lo, hi = r.intervalo(1)
    return r.coef[1], lo, hi


def faixa_do_brasil(
    brasil: Sequence[float],
    emergentes: Sequence[float],
    *,
    janela: int = 252,
    janelas_beta: Sequence[int] = (504, 1260, 2520),
) -> tuple[float, float]:
    """(menor, maior) parte do Brasil na última `janela`, em log × 100, com o β medido em
    cada uma das `janelas_beta` (2, 5 e 10 anos) e as pontas do intervalo de 90 % de cada um:
    a parte do Brasil muda com o β que se escolhe, e a faixa mostra o quanto."""
    total, fora = sum(brasil[-janela:]), sum(emergentes[-janela:])
    valores: list[float] = []
    for j in janelas_beta:
        if len(brasil) >= j:
            valores += [total - b * fora for b in beta_com_intervalo(brasil, emergentes, j)]
    return min(valores), max(valores)


def maiores_altas(
    reparticoes: Sequence[Reparticao], quantas: int = 5, afastamento: int = 252
) -> list[Reparticao]:
    """As `quantas` maiores altas (uma por episódio: pelo menos `afastamento` observações
    entre uma e outra), da mais nova para a mais antiga."""
    ordem = sorted(range(len(reparticoes)), key=lambda i: -reparticoes[i].total)
    escolhidos: list[int] = []
    for i in ordem:
        if len(escolhidos) == quantas:
            break
        if all(abs(i - j) >= afastamento for j in escolhidos):
            escolhidos.append(i)
    return [reparticoes[i] for i in sorted(escolhidos, reverse=True)]


# ------------------------------------------------------------------ a dívida com outro primário


def divida_com_outro_primario(
    divida: Mapping[int, float],
    juro: Mapping[int, float],
    crescimento: Mapping[int, float],
    primario: Mapping[int, float],
    outro: Mapping[int, float],
    desde: int,
) -> dict[int, float]:
    """A dívida (% do PIB) de cada ano a partir de `desde` se o primário tivesse sido `outro`
    (onde `outro` não diz nada, vale o que aconteceu), com o juro (% a.a.), o crescimento
    nominal do PIB (%) e tudo o mais de cada ano como foram.

    A dívida anda por dₜ = dₜ₋₁·(1+i)/(1+g) − pₜ + oₜ, e oₜ (câmbio, reconhecimento de dívida,
    compra de ativos) é o que falta para a conta fechar com o número oficial; trocar o
    primário muda só a diferença para o realizado, que rende o juro de cada ano:
    Δₜ = Δₜ₋₁·(1+i)/(1+g) + (pₜ − outroₜ). Com `outro` igual ao realizado, devolve a dívida
    oficial."""
    saida: dict[int, float] = {}
    delta = 0.0
    ano = desde
    while ano in divida and ano in juro and ano in crescimento and ano in primario:
        fator = (1 + juro[ano] / 100) / (1 + crescimento[ano] / 100)
        delta = delta * fator + (primario[ano] - outro.get(ano, primario[ano]))
        saida[ano] = divida[ano] + delta
        ano += 1
    return saida


# ------------------------------------------------------------------ o prometido e o que veio


@dataclass(frozen=True)
class ErroDoHorizonte:
    horizonte: int
    """Quantos anos antes a previsão foi feita."""
    media: float
    """Média de (previsto − realizado): positiva = esperava-se mais do que veio."""
    de: float
    ate: float
    """O intervalo de 90 % da média (erro de Newey-West: os erros de anos vizinhos andam
    juntos)."""
    otimistas: int
    """Em quantos anos o previsto ficou acima do realizado."""
    anos: list[int]


def previsto_antes(safras: Mapping[int, Mapping[int, float]], horizonte: int) -> dict[int, float]:
    """{ano-alvo: o que a safra de `horizonte` anos antes esperava para ele}."""
    return {
        feita + horizonte: valores[feita + horizonte]
        for feita, valores in safras.items()
        if feita + horizonte in valores
    }


def erro_por_horizonte(
    safras: Mapping[int, Mapping[int, float]],
    realizado: Mapping[int, float],
    horizonte: int,
    *,
    sem: Sequence[int] = (),
) -> ErroDoHorizonte | None:
    """O erro da previsão feita `horizonte` anos antes (`safras`: {ano em que foi feita:
    {ano-alvo: valor}}), nos anos-alvo com realizado, fora os de `sem`."""
    previsto = previsto_antes(safras, horizonte)
    anos = sorted(a for a in previsto if a in realizado and a not in sem)
    if len(anos) < 5:
        return None
    erros = [previsto[a] - realizado[a] for a in anos]
    r = estatistica.mqo(erros, [[] for _ in erros])
    de, ate = r.intervalo(0)
    return ErroDoHorizonte(
        horizonte=horizonte,
        media=r.coef[0],
        de=de,
        ate=ate,
        otimistas=sum(e > 0 for e in erros),
        anos=anos,
    )


def corridas(valores: Mapping[int, float], minimo: float = 1.0) -> list[tuple[int, int]]:
    """[(ano de partida, ano de chegada)] de cada sequência de anos seguidos em que o valor
    andou sempre para o mesmo lado e somou pelo menos `minimo` (para cima ou para baixo)."""
    anos = sorted(valores)
    saida: list[tuple[int, int]] = []
    inicio = 0
    for i in range(1, len(anos) + 1):
        acabou = i == len(anos) or anos[i] != anos[i - 1] + 1
        if not acabou and i - 1 > inicio:
            antes = valores[anos[i - 1]] - valores[anos[i - 2]]
            agora = valores[anos[i]] - valores[anos[i - 1]]
            acabou = (antes > 0) != (agora > 0)
        if acabou:
            if abs(valores[anos[i - 1]] - valores[anos[inicio]]) >= minimo:
                saida.append((anos[inicio], anos[i - 1]))
            inicio = i - 1 if i < len(anos) and anos[i] == anos[i - 1] + 1 else i
    return saida


def ultimo_de_cada_ano(pontos: Sequence[Ponto], mes: int = 12) -> dict[int, float]:
    return {d.year: v for d, v in pontos if d.month == mes}
