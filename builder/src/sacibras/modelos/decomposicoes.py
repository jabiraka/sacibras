"""Decomposições: um número oficial repartido nas partes que o formam, por conta nossa.

Nenhuma é previsão: todas usam só dado já publicado e fecham, na soma, com o número oficial.

- `ipca_por_grupo`: quantos pontos do IPCA acumulado vieram de cada grupo. O IBGE publica o
  impacto de cada grupo no mês (peso × variação); aqui os impactos dos meses são encadeados
  pelo índice geral, para a soma dar o acumulado.
- `pib_por_componente`: quantos pontos do crescimento do PIB (contra o mesmo trimestre do ano
  anterior) vieram de cada componente: a fatia dele no PIB um ano antes, a preços correntes,
  vezes o quanto cresceu em volume. O que sobra (os estoques e o encadeamento) vai à parte.
- `divida_por_fator`: por que a dívida em % do PIB mudou em 12 meses, com a mesma identidade
  do simulador da dívida olhada para trás: juros, crescimento do PIB em reais, primário e o
  resto.
- `desocupacao_por_fator`: quanto da mudança da taxa de desocupação veio de mais gente
  ocupada e quanto de mais gente na força de trabalho.
- `carrego`: o crescimento do PIB no ano se ele ficar parado no nível do último trimestre.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from math import log

from sacibras.tipos import Ponto


def _menos_meses(d: date, n: int) -> date:
    total = d.year * 12 + d.month - 1 - n
    return date(total // 12, total % 12 + 1, 1)


def _repartir(partes: dict[str, float], sobra: float, pesos: Mapping[str, float]) -> None:
    """Põe a `sobra` (arredondamento) nas partes, na proporção dos pesos."""
    total = sum(abs(pesos[k]) for k in partes)
    if total:
        for k in partes:
            partes[k] += sobra * abs(pesos[k]) / total


# ------------------------------------------------------------------ IPCA por grupo


def ipca_por_grupo(
    geral: Sequence[Ponto],
    variacao: Mapping[str, Sequence[Ponto]],
    peso: Mapping[str, Sequence[Ponto]],
    n: int = 12,
) -> dict[str, list[Ponto]]:
    """{grupo: pontos percentuais do IPCA acumulado em `n` meses que vieram dele}.

    `geral` e `variacao[g]` são variações no mês, em %; `peso[g]` é o peso do grupo no mês,
    em %. O impacto do grupo no mês (peso × variação ÷ 100) é levado ao acumulado pelo índice
    geral dos meses anteriores da janela. A soma dos grupos dá o IPCA acumulado; o que os
    arredondamentos do IBGE deixam sobrar (centésimos) se reparte pelo peso.
    """
    do_mes = dict(geral)
    var = {g: dict(v) for g, v in variacao.items()}
    pes = {g: dict(v) for g, v in peso.items()}
    saida: dict[str, list[Ponto]] = {g: [] for g in var}
    for fim in sorted(do_mes):
        meses = [_menos_meses(fim, k) for k in range(n - 1, -1, -1)]
        if any(
            m not in do_mes or any(m not in var[g] or m not in pes[g] for g in var) for m in meses
        ):
            continue
        partes = dict.fromkeys(var, 0.0)
        fator = 1.0
        for m in meses:
            for g in var:
                partes[g] += pes[g][m] * var[g][m] / 100 * fator
            fator *= 1 + do_mes[m] / 100
        _repartir(partes, (fator - 1) * 100 - sum(partes.values()), {g: pes[g][fim] for g in var})
        for g in var:
            saida[g].append((fim, partes[g]))
    return saida


# ------------------------------------------------------------------ PIB por componente

RESTO = "resto"


def pib_por_componente(
    volume: Mapping[str, Sequence[Ponto]],
    valor: Mapping[str, Sequence[Ponto]],
    total: str,
    partes: Mapping[str, int],
    resto_a_parte: bool,
) -> dict[str, list[Ponto]]:
    """{componente: pontos do crescimento do PIB contra o mesmo trimestre do ano anterior}.

    `volume[c]` é o índice de volume trimestral e `valor[c]` o valor a preços correntes;
    `partes` dá o sinal de cada componente (as importações entram com −1). Com
    `resto_a_parte`, o que falta para o crescimento do `total` sai na chave `RESTO` (pela
    demanda: a variação de estoques e a diferença do encadeamento); sem, é repartido pela
    fatia (pela oferta, onde o resto é só encadeamento).
    """
    vol = {c: dict(v) for c, v in volume.items()}
    val = {c: dict(v) for c, v in valor.items()}
    saida: dict[str, list[Ponto]] = {c: [] for c in partes}
    if resto_a_parte:
        saida[RESTO] = []
    for t in sorted(vol[total]):
        antes = date(t.year - 1, t.month, 1)
        if any(
            antes not in vol[c] or t not in vol[c] or antes not in val[c] for c in [total, *partes]
        ):
            continue
        fatia = {c: sinal * val[c][antes] / val[total][antes] for c, sinal in partes.items()}
        contrib = {c: fatia[c] * (vol[c][t] / vol[c][antes] - 1) * 100 for c in partes}
        sobra = (vol[total][t] / vol[total][antes] - 1) * 100 - sum(contrib.values())
        if resto_a_parte:
            saida[RESTO].append((t, sobra))
        else:
            _repartir(contrib, sobra, fatia)
        for c in partes:
            saida[c].append((t, contrib[c]))
    return saida


# ------------------------------------------------------------------ dívida por fator


@dataclass(frozen=True)
class FatoresDaDivida:
    """Por que a dívida (% do PIB) mudou em 12 meses; os quatro somam `variacao`."""

    quando: date
    variacao: float
    juros: float
    """Os juros que a dívida rendeu: a taxa implícita vezes a dívida média do período."""
    pib: float
    """O PIB em reais cresceu (com a inflação) e a mesma dívida ficou menor diante dele."""
    primario: float
    """O déficit primário (positivo) ou o superávit (negativo) do setor público."""
    resto: float
    """O que os três não explicam: reservas, caixa do Tesouro, câmbio, ajustes."""


def divida_por_fator(
    divida: Sequence[Ponto],
    pib_12m: Sequence[Ponto],
    taxa_implicita: Sequence[Ponto],
    deficit_primario: Sequence[Ponto],
) -> list[FatoresDaDivida]:
    """A variação da dívida em % do PIB em 12 meses, mês a mês, em quatro partes.

    `divida` e `deficit_primario` (12 meses, positivo é déficit) em % do PIB; `pib_12m` em
    reais; `taxa_implicita` em % em 12 meses. Com D a dívida em reais e Y o PIB de 12 meses:

        d_t − d_0 = (D_t − D_0) / Y_t − d_0 · g / (1 + g),   g = Y_t / Y_0 − 1

    e D_t − D_0 = juros + déficit primário + resto.
    """
    d, y = dict(divida), dict(pib_12m)
    taxa, prim = dict(taxa_implicita), dict(deficit_primario)
    saida = []
    for t in sorted(d):
        antes = _menos_meses(t, 12)
        janela = [_menos_meses(t, k) for k in range(12, 0, -1)]
        if (
            t not in y
            or t not in taxa
            or t not in prim
            or any(m not in d or m not in y for m in janela)
        ):
            continue
        g = y[t] / y[antes] - 1
        media_em_reais = sum(d[m] / 100 * y[m] for m in janela) / 12
        juros = taxa[t] / 100 * media_em_reais / y[t] * 100
        efeito_pib = -d[antes] * g / (1 + g)
        variacao = d[t] - d[antes]
        saida.append(
            FatoresDaDivida(
                quando=t,
                variacao=variacao,
                juros=juros,
                pib=efeito_pib,
                primario=prim[t],
                resto=variacao - juros - efeito_pib - prim[t],
            )
        )
    return saida


# ------------------------------------------------------------------ desocupação por fator


def desocupacao_por_fator(
    ocupados: Sequence[Ponto],
    desocupados: Sequence[Ponto],
    populacao: Sequence[Ponto],
    defasagem: int = 12,
) -> tuple[list[Ponto], list[Ponto], list[Ponto]]:
    """(mudança da taxa de desocupação em `defasagem` meses, a parte da ocupação, a parte da
    participação), em pontos percentuais; as duas partes somam a mudança.

    Com E ocupados, F a força de trabalho (E + desocupados) e P a população de 14 anos ou
    mais: 1 − u = (E/P) ÷ (F/P). Em logaritmo, a variação de (1 − u) é a do nível de ocupação
    menos a da participação; a média logarítmica leva de volta a pontos da taxa, sem sobra.
    Mais gente ocupada derruba a taxa (parte negativa); mais gente na força de trabalho a
    levanta (parte positiva).
    """
    e, des, p = dict(ocupados), dict(desocupados), dict(populacao)
    mudanca: list[Ponto] = []
    ocupacao: list[Ponto] = []
    participacao: list[Ponto] = []
    for t in sorted(e):
        antes = _menos_meses(t, defasagem)
        if any(m not in e or m not in des or m not in p for m in (t, antes)):
            continue
        emprego = [e[m] / (e[m] + des[m]) for m in (antes, t)]  # 1 − u
        nivel = log((e[t] / p[t]) / (e[antes] / p[antes]))
        parte = log(((e[t] + des[t]) / p[t]) / ((e[antes] + des[antes]) / p[antes]))
        delta = emprego[1] - emprego[0]
        media = delta / log(emprego[1] / emprego[0]) if abs(delta) > 1e-12 else emprego[0]
        mudanca.append((t, -delta * 100))
        ocupacao.append((t, -media * nivel * 100))
        participacao.append((t, media * parte * 100))
    return mudanca, ocupacao, participacao


# ------------------------------------------------------------------ massa de rendimento


def massa_por_fator(
    massa: Sequence[Ponto],
    ocupados: Sequence[Ponto],
    defasagem: int = 12,
) -> tuple[list[Ponto], list[Ponto], list[Ponto]]:
    """(variação da massa de rendimento em `defasagem` meses, a parte de mais gente ocupada, a
    parte do rendimento de cada um), em %; as duas partes somam a variação.

    A massa é gente ocupada × rendimento médio: em logaritmo, a variação da massa é a da
    ocupação mais a do rendimento por ocupado (a massa dividida pelos ocupados, para a conta
    fechar sem sobra). A média logarítmica leva de volta à variação em %.
    """
    m, e = dict(massa), dict(ocupados)
    total: list[Ponto] = []
    gente: list[Ponto] = []
    rendimento: list[Ponto] = []
    for t in sorted(m):
        antes = _menos_meses(t, defasagem)
        if any(x not in m or x not in e or m[x] <= 0 or e[x] <= 0 for x in (t, antes)):
            continue
        variacao = (m[t] / m[antes] - 1) * 100
        log_massa = log(m[t] / m[antes])
        escala = variacao / log_massa if abs(log_massa) > 1e-12 else 100.0
        parte_gente = escala * log(e[t] / e[antes])
        total.append((t, variacao))
        gente.append((t, parte_gente))
        rendimento.append((t, variacao - parte_gente))
    return total, gente, rendimento


# ------------------------------------------------------------------ carrego do PIB


@dataclass(frozen=True)
class Carrego:
    ano: int
    valor: float
    """Crescimento do ano, em %, se o PIB ficar no nível do último trimestre até dezembro."""
    trimestres: int
    """Quantos trimestres de `ano` já saíram (0: o carrego é o que o ano anterior deixou)."""
    ultimo: date


def carrego(indice_dessazonalizado: Sequence[Ponto]) -> Carrego | None:
    """O carrego estatístico: a média do ano, com os trimestres que faltam iguais ao último
    publicado, sobre a média do ano anterior. Depois do 4º trimestre, vale para o ano
    seguinte (o que o ano deixa de herança)."""
    nivel = dict(indice_dessazonalizado)
    if not nivel:
        return None
    ultimo = max(nivel)
    ano = ultimo.year + 1 if ultimo.month == 10 else ultimo.year
    do_ano = [nivel[t] for t in sorted(nivel) if t.year == ano]
    anterior = [nivel[t] for t in sorted(nivel) if t.year == ano - 1]
    if len(anterior) != 4:
        return None
    cheio = do_ano + [nivel[ultimo]] * (4 - len(do_ano))
    return Carrego(ano, (sum(cheio) / sum(anterior) - 1) * 100, len(do_ano), ultimo)
