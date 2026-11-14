"""Curvas zero-cupom do Tesouro: o juro nominal e o real para cada prazo, e o que sai delas —
a inflação implícita e as taxas a termo de cada ano.

Adaptado (copiado, não importado) de `domain/curves.py` e `domain/fixed_income/curva_esperada.py`
do finance_agent, que fazem a mesma conta para o Jabs:

- **Nominal:** o Tesouro Prefixado (LTN, zero-cupom); depois do último, o Prefixado com Juros
  Semestrais (NTN-F) por *bootstrap*.
- **Real:** o Tesouro IPCA+ (NTN-B Principal, zero-cupom); depois do último, o IPCA+ com Juros
  Semestrais (NTN-B) por *bootstrap*.
- **Entre vértices:** interpolação log-linear no fator de desconto (taxa a termo constante no
  trecho, a convenção da ANBIMA). Antes do primeiro vértice, a taxa dele; depois do último,
  nada — a conta nunca extrapola uma perna em silêncio.
- **Inflação implícita** no prazo: (1 + nominal) / (1 + real) − 1.

O *bootstrap*: um papel com cupom é uma soma de zero-cupons, `preço = Σ fluxo × DF(du)`. Os
fluxos até o último vértice são descontados pela curva que já existe; o fator do vencimento é o
único desconhecido, e a taxa dele é a que reproduz o preço (bisseção). O preço sai da própria
taxa do papel, `Σ fluxo / (1+y)^(du/252)`, a identidade que o Tesouro usa para o PU.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sacibras.calendario import dias_uteis
from sacibras.tipos import Ponto

ANO = 252
CUPOM_NTNF = 1.10**0.5 - 1  # 10 % ao ano, pago a cada semestre
CUPOM_NTNB = 1.06**0.5 - 1  # 6 % ao ano, pago a cada semestre


@dataclass(frozen=True)
class Curva:
    """Vértices `(du, taxa ao ano em fração)`, em `du` crescente."""

    base: date
    vertices: tuple[tuple[int, float], ...]

    @property
    def fim(self) -> int:
        return self.vertices[-1][0]

    def fator_de_desconto(self, du: int) -> float:
        if du <= 0:
            return 1.0
        (d0, t0) = self.vertices[0]
        if du <= d0:
            return float((1 + t0) ** (-du / ANO))
        if du > self.fim:
            raise ValueError(f"du={du} depois do último vértice ({self.fim})")
        for (a, ta), (b, tb) in zip(self.vertices, self.vertices[1:], strict=False):
            if a <= du <= b:
                la = math.log((1 + ta) ** (-a / ANO))
                lb = math.log((1 + tb) ** (-b / ANO))
                return math.exp(la + (du - a) / (b - a) * (lb - la))
        raise ValueError(f"du={du} fora da curva")

    def taxa(self, du: int) -> float:
        return float(self.fator_de_desconto(du) ** (-ANO / du) - 1)

    def du_de(self, d: date) -> int:
        return dias_uteis(self.base, d)


def _somar_meses(d: date, meses: int) -> date:
    total = d.month - 1 + meses
    return date(d.year + total // 12, total % 12 + 1, d.day)


def fluxos(base: date, vencimento: date, cupom: float) -> list[tuple[int, float]]:
    """Os fluxos (du, valor por unidade de face) de um papel com cupom semestral: os cupons
    nas datas a cada seis meses contadas para trás a partir do vencimento, e a face no fim."""
    datas: list[date] = []
    d = vencimento
    while d > base:
        datas.append(d)
        d = _somar_meses(d, -6)
    datas.reverse()
    saida = [(dias_uteis(base, x), cupom) for x in datas]
    du_fim, _ = saida[-1]
    saida[-1] = (du_fim, cupom + 1)
    return [f for f in saida if f[0] > 0]


def _bootstrap(
    vertices: list[tuple[int, float]], base: date, fl: Sequence[tuple[int, float]], taxa: float
) -> tuple[int, float]:
    """O vértice zero-cupom no vencimento de um papel com cupom (ver o docstring do módulo)."""
    preco = sum(v / (1 + taxa) ** (du / ANO) for du, v in fl)
    du_n = fl[-1][0]

    def preco_a(t: float) -> float:
        curva = Curva(base, (*vertices, (du_n, t)))
        return sum(v * curva.fator_de_desconto(du) for du, v in fl)

    baixo, alto = -0.5, 2.0
    for _ in range(80):
        meio = (baixo + alto) / 2
        if preco_a(meio) > preco:
            baixo = meio  # taxa baixa demais: preço alto
        else:
            alto = meio
    return du_n, (baixo + alto) / 2


def montar(
    base: date,
    zero: Sequence[Ponto],
    com_cupom: Sequence[Ponto],
    cupom: float,
) -> Curva:
    """A curva com os zero-cupons (`zero`: [(vencimento, taxa % a.a.)]) e, depois do último,
    os papéis com cupom por bootstrap."""
    vertices = sorted((dias_uteis(base, d), t / 100) for d, t in zero if dias_uteis(base, d) > 0)
    if not vertices:
        raise ValueError("sem papel zero-cupom com prazo")
    for vencimento, taxa in sorted(com_cupom):
        fl = fluxos(base, vencimento, cupom)
        if not fl or fl[-1][0] <= vertices[-1][0]:
            continue
        vertices.append(_bootstrap(vertices, base, fl, taxa / 100))
    return Curva(base, tuple(vertices))


@dataclass(frozen=True)
class PontoDaCurva:
    vencimento: date
    nominal: float
    real: float
    implicita: float


def inflacao_implicita(nominal: Curva, real: Curva, datas: Sequence[date]) -> list[PontoDaCurva]:
    """A inflação implícita em cada data onde as duas pernas têm preço (% ao ano)."""
    saida: list[PontoDaCurva] = []
    limite = min(nominal.fim, real.fim)
    for d in sorted(set(datas)):
        du = nominal.du_de(d)
        if du <= 0 or du > limite:
            continue
        n, r = nominal.taxa(du), real.taxa(du)
        saida.append(PontoDaCurva(d, n * 100, r * 100, ((1 + n) / (1 + r) - 1) * 100))
    return saida


def a_termo_por_ano(curva: Curva, anos: Sequence[int]) -> dict[int, float]:
    """A taxa a termo de cada ano civil (de 1º de janeiro a 1º de janeiro), % ao ano, nos anos
    que a curva cobre inteiros. O ano corrente vai de hoje ao fim dele."""
    saida: dict[int, float] = {}
    for ano in anos:
        inicio = max(curva.base, date(ano, 1, 1))
        a, b = curva.du_de(inicio), curva.du_de(date(ano + 1, 1, 1))
        if b <= a or b > curva.fim:
            continue
        fator = curva.fator_de_desconto(a) / curva.fator_de_desconto(b)
        saida[ano] = (fator ** (ANO / (b - a)) - 1) * 100
    return saida


def inflacao_por_ano(nominal: Curva, real: Curva, anos: Sequence[int]) -> dict[int, float]:
    """A inflação implícita de cada ano civil: o termo nominal do ano sobre o termo real."""
    n = a_termo_por_ano(nominal, anos)
    r = a_termo_por_ano(real, anos)
    return {a: ((1 + n[a] / 100) / (1 + r[a] / 100) - 1) * 100 for a in n if a in r}


def media_do_caminho(degraus: Sequence[Ponto], base: date, ate: date) -> float:
    """A taxa média (% ao ano, base 252) de `base` até `ate` de um caminho em degraus:
    `degraus` = [(a partir de, taxa % a.a.)], cada um valendo até o seguinte. Serve para pôr
    o Focus (a Selic de cada reunião, o IPCA de cada ano) na mesma régua da curva."""
    passos = sorted(degraus)
    if not passos:
        raise ValueError("caminho vazio")
    log_fator, total = 0.0, 0
    for i, (inicio, taxa) in enumerate(passos):
        fim = passos[i + 1][0] if i + 1 < len(passos) else ate
        de, a = max(inicio, base), min(fim, ate)
        if i == 0:
            de = base
        du = dias_uteis(de, a) if a > de else 0
        log_fator += du / ANO * math.log1p(taxa / 100)
        total += du
    if total == 0:
        raise ValueError("prazo sem dia útil")
    return (math.exp(log_fator * ANO / total) - 1) * 100
