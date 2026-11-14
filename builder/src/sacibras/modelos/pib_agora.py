"""PIB agora: uma estimativa do PIB do trimestre que ainda não saiu, pelo IBC-Br.

Equação-ponte, a mais simples que funciona: o crescimento do PIB contra o mesmo trimestre do
ano anterior explicado pelo crescimento do IBC-Br médio do trimestre na mesma comparação.
O IBC-Br sai todo mês, com uns 45 dias de atraso; o PIB, uma vez por trimestre.

O erro típico vem de um teste fora da amostra: para cada um dos últimos trimestres, a reta é
estimada só com o passado e prevê aquele trimestre. Dois limites declarados: o teste usa o
IBC-Br do trimestre inteiro (com um ou dois meses a estimativa é pior do que o erro sugere), e
os dados são os revisados de hoje, não os da época.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sacibras.tipos import Ponto


@dataclass(frozen=True)
class PibAgora:
    trimestre: date
    previsao: float
    erro_tipico: float
    """Raiz do erro quadrático médio fora da amostra, em pontos percentuais."""
    meses_disponiveis: int
    ibc_no_trimestre: float
    """Crescimento do IBC-Br (a/a) nos meses disponíveis do trimestre."""
    inclinacao: float
    intercepto: float
    trimestres_na_amostra: int
    trimestres_no_teste: int


def _trimestre(d: date) -> date:
    return date(d.year, 3 * ((d.month - 1) // 3) + 1, 1)


def _seguinte(t: date) -> date:
    return date(t.year + (t.month == 10), (t.month + 3 - 1) % 12 + 1, 1)


def _reta(x: list[float], y: list[float]) -> tuple[float, float]:
    """(intercepto, inclinação) dos mínimos quadrados de y em x."""
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    b = sum((a - mx) * (c - my) for a, c in zip(x, y, strict=True)) / sxx
    return my - b * mx, b


def ibc_trimestral(ibc: list[Ponto]) -> dict[date, tuple[float, int]]:
    """{trimestre: (crescimento a/a em %, meses usados)}.

    Trimestre incompleto usa só os meses que existem, contra os mesmos meses um ano antes.
    """
    nivel = dict(ibc)
    por_trimestre: dict[date, list[date]] = {}
    for mes in nivel:
        por_trimestre.setdefault(_trimestre(mes), []).append(mes)
    saida: dict[date, tuple[float, int]] = {}
    for trimestre, meses in por_trimestre.items():
        antes = [date(m.year - 1, m.month, 1) for m in meses]
        if not all(a in nivel for a in antes):
            continue
        atual = sum(nivel[m] for m in meses)
        base = sum(nivel[a] for a in antes)
        saida[trimestre] = ((atual / base - 1) * 100, len(meses))
    return saida


def estimar(pib_aa: list[Ponto], ibc: list[Ponto], teste: int = 20) -> PibAgora | None:
    """`pib_aa`: crescimento do PIB contra o mesmo trimestre do ano anterior (SIDRA 5932,
    variável 6561). `ibc`: nível mensal do IBC-Br sem ajuste sazonal (SGS 24363)."""
    if not pib_aa:
        return None
    x_tri = ibc_trimestral(ibc)
    pares = [(t, x_tri[t][0], v) for t, v in pib_aa if t in x_tri and x_tri[t][1] == 3]
    if len(pares) < 30:
        return None
    alvo = _seguinte(pib_aa[-1][0])
    if alvo not in x_tri:
        return None  # ainda não saiu nenhum mês do IBC-Br do trimestre
    x_agora, meses = x_tri[alvo]

    xs, ys = [p[1] for p in pares], [p[2] for p in pares]
    a, b = _reta(xs, ys)
    erros: list[float] = []
    for i in range(max(20, len(pares) - teste), len(pares)):
        a_i, b_i = _reta(xs[:i], ys[:i])
        erros.append(a_i + b_i * xs[i] - ys[i])
    rmse = (sum(e * e for e in erros) / len(erros)) ** 0.5
    return PibAgora(
        trimestre=alvo,
        previsao=a + b * x_agora,
        erro_tipico=rmse,
        meses_disponiveis=meses,
        ibc_no_trimestre=x_agora,
        inclinacao=b,
        intercepto=a,
        trimestres_na_amostra=len(pares),
        trimestres_no_teste=len(erros),
    )
