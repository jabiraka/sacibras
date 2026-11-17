"""Contas de estatística sem biblioteca de fora (o builder só depende de httpx, openpyxl e
pydantic): mínimos quadrados com erro-padrão robusto, o filtro HP e o filtro de Hamilton.

São contas pequenas (dezenas a centenas de pontos), e a clareza vale mais que a velocidade.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

Matriz = list[list[float]]


def _resolver(a: Matriz, b: list[float]) -> list[float]:
    """Resolve a·x = b por eliminação de Gauss com pivô parcial (a é quadrada)."""
    n = len(a)
    m = [[*linha, b[i]] for i, linha in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-12:
            raise ValueError("matriz singular: as variáveis repetem informação")
        m[col], m[piv] = m[piv], m[col]
        for r in range(col + 1, n):
            f = m[r][col] / m[col][col]
            if f:
                for c in range(col, n + 1):
                    m[r][c] -= f * m[col][c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (m[r][n] - sum(m[r][c] * x[c] for c in range(r + 1, n))) / m[r][r]
    return x


def _inversa(a: Matriz) -> Matriz:
    n = len(a)
    colunas = [_resolver(a, [1.0 if i == j else 0.0 for i in range(n)]) for j in range(n)]
    return [[colunas[j][i] for j in range(n)] for i in range(n)]


@dataclass(frozen=True)
class Regressao:
    coef: list[float]
    """Na ordem das colunas de X; a primeira é a constante."""
    erro: list[float]
    """Erro-padrão de Newey-West (robusto a autocorrelação e a variância que muda)."""
    n: int
    r2: float
    residuos: list[float]

    def intervalo(self, i: int, z: float = 1.645) -> tuple[float, float]:
        """O intervalo de 90 % do coeficiente `i` (z = 1,645), pela aproximação normal."""
        return self.coef[i] - z * self.erro[i], self.coef[i] + z * self.erro[i]


def mqo(
    y: Sequence[float], x: Sequence[Sequence[float]], defasagens: int | None = None
) -> Regressao:
    """Mínimos quadrados de y em [1, x...]. `x` vem por observação ([[x1, x2], ...]).

    `defasagens`: as do Newey-West; sem ela, a regra de bolso ⌊4·(n/100)^(2/9)⌋."""
    n = len(y)
    linhas = [[1.0, *map(float, obs)] for obs in x]
    k = len(linhas[0])
    if n <= k:
        raise ValueError(f"poucas observações ({n}) para {k} coeficientes")
    xtx = [[sum(linhas[t][i] * linhas[t][j] for t in range(n)) for j in range(k)] for i in range(k)]
    xty = [sum(linhas[t][i] * y[t] for t in range(n)) for i in range(k)]
    coef = _resolver(xtx, xty)
    res = [y[t] - sum(coef[i] * linhas[t][i] for i in range(k)) for t in range(n)]
    media = sum(y) / n
    tot = sum((v - media) ** 2 for v in y)
    r2 = 1 - sum(e * e for e in res) / tot if tot else 0.0
    lag = defasagens if defasagens is not None else int(4 * (n / 100) ** (2 / 9))
    s: Matriz = [[0.0] * k for _ in range(k)]
    for t in range(n):
        for i in range(k):
            for j in range(k):
                s[i][j] += res[t] ** 2 * linhas[t][i] * linhas[t][j]
    for h in range(1, lag + 1):
        peso = 1 - h / (lag + 1)
        for t in range(h, n):
            for i in range(k):
                for j in range(k):
                    termo = res[t] * res[t - h] * linhas[t][i] * linhas[t - h][j]
                    termo += res[t - h] * res[t] * linhas[t - h][i] * linhas[t][j]
                    s[i][j] += peso * termo
    inv = _inversa(xtx)
    meio = [[sum(inv[i][a] * s[a][b] for a in range(k)) for b in range(k)] for i in range(k)]
    cov = [[sum(meio[i][b] * inv[b][j] for b in range(k)) for j in range(k)] for i in range(k)]
    ajuste = n / (n - k)
    erro = [math.sqrt(max(cov[i][i] * ajuste, 0.0)) for i in range(k)]
    return Regressao(coef=coef, erro=erro, n=n, r2=r2, residuos=res)


def hp(y: Sequence[float], lam: float = 1600.0) -> list[float]:
    """A tendência do filtro de Hodrick-Prescott: resolve (I + λ·D'D)·t = y, com D a segunda
    diferença. λ = 1600 é o de costume para dado trimestral."""
    n = len(y)
    if n < 4:
        return list(y)
    a: Matriz = [[0.0] * n for _ in range(n)]
    for i in range(n):
        a[i][i] = 1.0
    for t in range(n - 2):
        d = {t: 1.0, t + 1: -2.0, t + 2: 1.0}
        for i, vi in d.items():
            for j, vj in d.items():
                a[i][j] += lam * vi * vj
    return _resolver(a, list(map(float, y)))


def hamilton(y: Sequence[float], h: int = 8, p: int = 4) -> list[float | None]:
    """O ciclo pelo filtro de Hamilton (2018): o erro de prever y[t] com y[t-h]...y[t-h-p+1]
    por mínimos quadrados. Os primeiros h+p-1 pontos ficam sem ciclo (None)."""
    inicio = h + p - 1
    if len(y) <= inicio + p + 2:
        return [None] * len(y)
    alvo = [float(y[t]) for t in range(inicio, len(y))]
    x = [[float(y[t - h - j]) for j in range(p)] for t in range(inicio, len(y))]
    r = mqo(alvo, x, defasagens=0)
    return [None] * inicio + r.residuos
