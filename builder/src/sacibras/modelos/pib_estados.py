"""PIB trimestral por estado: estimativa nossa, que o IBGE não publica.

O IBGE dá o PIB dos estados uma vez por ano, com dois anos de atraso (Contas Regionais), e o
PIB do Brasil a cada trimestre (Contas Nacionais Trimestrais). A conta junta os dois com um
indicador trimestral de cada estado, o IBC-R do Banco Central (o do próprio estado ou, para
os 14 que não têm, o da região), em dois ajustes repetidos até fecharem:

1. **No tempo** (Denton proporcional, o método do manual de Contas Nacionais Trimestrais do
   FMI, 2017, cap. 6): o índice trimestral do estado é o indicador vezes uma razão que muda o
   mais devagar possível, escolhida para a média dos quatro trimestres bater com o PIB oficial
   de cada ano. Depois do último ano oficial a razão fica parada: o estado anda como o
   indicador.
2. **Entre os estados** (rateio proporcional): em cada trimestre, a soma dos 27, a preços do
   ano anterior, tem de dar o PIB trimestral do Brasil; a diferença é repartida por igual
   (o mesmo fator para todos). Nos trimestres depois do último ano oficial, os preços são os
   desse último ano, porque não há PIB corrente por estado mais novo.

O que a conta não sabe: o desenho dos trimestres dentro do ano é o do IBC-R, que não é o PIB;
e nos 14 estados sem índice o desenho é o da região. O erro se mede refazendo a conta como
se o IBGE só tivesse publicado até um ano Y e comparando com a conta de hoje nos trimestres
de Y+1 e Y+2 (`revisoes`): é o quanto o número do trimestre muda quando sai o oficial do ano.
Limite declarado: o teste usa o IBC-R e o PIB revisados de hoje, não os da época.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from sacibras.tipos import Ponto

PorAno = Mapping[int, float]

VOLTAS = 3
"""Voltas dos dois ajustes. Na primeira o rateio mexe até 2 %; na segunda, menos de 0,01 %."""


def trimestral(pontos: Sequence[Ponto]) -> dict[date, float]:
    """Média dos três meses de cada trimestre de uma série mensal; trimestre incompleto fica
    de fora."""
    por: dict[date, list[float]] = {}
    for d, v in pontos:
        por.setdefault(date(d.year, 3 * ((d.month - 1) // 3) + 1, 1), []).append(v)
    return {t: sum(v) / 3 for t, v in sorted(por.items()) if len(v) == 3}


def _resolver(a: list[list[float]], b: list[float]) -> list[float]:
    """Sistema linear pequeno por eliminação de Gauss com pivô parcial."""
    n = len(b)
    m = [[*linha, b[i]] for i, linha in enumerate(a)]
    for i in range(n):
        p = max(range(i, n), key=lambda k: abs(m[k][i]))
        if abs(m[p][i]) < 1e-12:
            raise ValueError("sistema sem solução única")
        m[i], m[p] = m[p], m[i]
        for k in range(i + 1, n):
            f = m[k][i] / m[i][i]
            if f:
                for j in range(i, n + 1):
                    m[k][j] -= f * m[i][j]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (m[i][n] - sum(m[i][j] * x[j] for j in range(i + 1, n))) / m[i][i]
    return x


def denton(x: Sequence[float], anos: Sequence[int], anual: PorAno) -> list[float]:
    """Denton proporcional (primeira diferença): devolve b = r·x, com r o mais liso possível
    (mínimo de Σ(r_t − r_{t−1})²) e a média dos trimestres de cada ano de `anual` igual ao
    número do ano. `anos[t]` é o ano do trimestre t. Ano sem os quatro trimestres não amarra;
    depois do último ano amarrado, r fica constante.

    Escrito em r_t = r_1 + d_2 + … + d_t, o problema vira o de menor norma em d, e sobra um
    sistema do tamanho do número de anos (não do de trimestres).
    """
    n = len(x)
    amarrados = [a for a in sorted(anual) if sum(1 for y in anos if y == a) == 4]
    if not amarrados:
        raise ValueError("nenhum ano com os quatro trimestres")
    m = len(amarrados)
    # c[i][t]: peso do trimestre t na média do ano i; g[i][j]: efeito de d_j nessa média.
    c = [[x[t] / 4 if anos[t] == a else 0.0 for t in range(n)] for a in amarrados]
    g = []
    for linha in c:
        acum, cauda = 0.0, [0.0] * n
        for t in range(n - 1, 0, -1):
            acum += linha[t]
            cauda[t] = acum
        g.append(cauda[1:])
    sistema = [
        [sum(p * q for p, q in zip(g[i], g[k], strict=True)) for k in range(m)] + [sum(c[i])]
        for i in range(m)
    ]
    sistema.append([sum(linha) for linha in c] + [0.0])
    solucao = _resolver(sistema, [anual[a] for a in amarrados] + [0.0])
    lam, r = solucao[:m], solucao[m]
    saida = [r * x[0]]
    for t in range(1, n):
        r += sum(lam[i] * g[i][t - 1] for i in range(m))
        saida.append(r * x[t])
    return saida


def _media_do_ano(b: Sequence[float], anos: Sequence[int], ano: int) -> float:
    vals = [v for v, a in zip(b, anos, strict=True) if a == ano]
    return sum(vals) / len(vals)


@dataclass(frozen=True)
class Estimativa:
    trimestres: list[date]
    indice: dict[str, list[float]]
    """{UF: índice de volume do PIB em cada trimestre (2010 = 100, como as Contas Regionais)}."""
    ultimo_oficial: int
    """O último ano amarrado ao PIB oficial do estado; os trimestres seguintes andam pelo
    indicador e fecham só com o PIB trimestral do Brasil."""
    pesos: dict[str, list[float]]
    """{UF: fatia no PIB do Brasil em cada trimestre, a preços do ano-base do trimestre}."""


def _base(ano: int, primeiro: int, ultimo: int) -> int:
    """O ano cujos preços valem num trimestre de `ano`: o anterior, limitado ao que existe."""
    return max(min(ano - 1, ultimo), primeiro)


def estimar(
    trimestres: Sequence[date],
    indicador: Mapping[str, Sequence[float]],
    volume: Mapping[str, PorAno],
    corrente: Mapping[str, PorAno],
    pib_brasil: Sequence[float],
    corrente_brasil: PorAno,
    ultimo: int | None = None,
    voltas: int = VOLTAS,
) -> Estimativa:
    """O índice trimestral do PIB de cada estado.

    `trimestres` começa no 1º trimestre de um ano e não tem buraco; `indicador[uf]` e
    `pib_brasil` (índice de volume do PIB trimestral do país) têm um valor por trimestre.
    `volume[uf]` é o índice anual das Contas Regionais e `corrente[uf]` o PIB a preços
    correntes; `ultimo` corta os dois (para o teste: "como se o IBGE só tivesse publicado até
    aqui").
    """
    anos = [t.year for t in trimestres]
    primeiro = anos[0]
    ufs = sorted(indicador)
    cheios = {a for a in set(anos) if anos.count(a) == 4}
    ultimo = min(ultimo or max(cheios), max(a for a in cheios if all(a in volume[s] for s in ufs)))
    oficiais = {s: {a: v for a, v in volume[s].items() if primeiro <= a <= ultimo} for s in ufs}
    b = {s: denton(indicador[s], anos, oficiais[s]) for s in ufs}
    bases = [_base(a, primeiro, ultimo) for a in anos]
    media_br = {a: _media_do_ano(pib_brasil, anos, a) for a in set(bases)}
    alvo = [corrente_brasil[k] * pib_brasil[t] / media_br[k] for t, k in enumerate(bases)]
    pesos: dict[str, list[float]] = {}
    for volta in range(voltas + 1):
        media = {s: {a: _media_do_ano(b[s], anos, a) for a in set(bases)} for s in ufs}
        valor = {
            s: [corrente[s][k] * b[s][t] / media[s][k] for t, k in enumerate(bases)] for s in ufs
        }
        soma = [sum(valor[s][t] for s in ufs) for t in range(len(anos))]
        pesos = {s: [valor[s][t] / soma[t] for t in range(len(anos))] for s in ufs}
        if volta == voltas:
            break
        fator = [alvo[t] / soma[t] for t in range(len(anos))]
        b = {
            s: denton([v * f for v, f in zip(b[s], fator, strict=True)], anos, oficiais[s])
            for s in ufs
        }
    return Estimativa(list(trimestres), b, ultimo, pesos)


def crescimento(indice: Sequence[float]) -> list[float | None]:
    """Em cada trimestre, o crescimento contra o mesmo trimestre do ano anterior, em %."""
    return [None if t < 4 else (indice[t] / indice[t - 4] - 1) * 100 for t in range(len(indice))]


def contribuicoes(e: Estimativa, pib_brasil: Sequence[float]) -> dict[str, list[float | None]]:
    """{UF: quantos pontos do crescimento do PIB do Brasil (contra o mesmo trimestre do ano
    anterior) vieram do estado}. É a fatia do estado um ano antes vezes o crescimento dele; o
    que sobra do encadeamento de preços (centésimos de ponto) se reparte pela fatia, para a
    soma dar exatamente o número do IBGE."""
    brasil = crescimento(pib_brasil)
    saida: dict[str, list[float | None]] = {s: [None] * len(pib_brasil) for s in e.indice}
    for t in range(4, len(pib_brasil)):
        # A fatia de um ano antes, medida aos preços que valem para o trimestre de agora.
        w = {s: e.pesos[s][t] * e.indice[s][t - 4] / e.indice[s][t] for s in e.indice}
        total = sum(w.values())
        bruto = {s: w[s] / total * (e.indice[s][t] / e.indice[s][t - 4] - 1) * 100 for s in w}
        sobra = (brasil[t] or 0.0) - sum(bruto.values())
        for s in w:
            saida[s][t] = bruto[s] + sobra * w[s] / total
    return saida


def revisoes(
    trimestres: Sequence[date],
    indicador: Mapping[str, Sequence[float]],
    volume: Mapping[str, PorAno],
    corrente: Mapping[str, PorAno],
    pib_brasil: Sequence[float],
    corrente_brasil: PorAno,
    final: Estimativa,
    voltas: int = 2,
) -> dict[str, list[float]]:
    """O teste: {UF: [crescimento de hoje − crescimento estimado sabendo o PIB oficial só até
    Y]}, nos trimestres de Y+1 e Y+2, para cada Y possível. É o tamanho da revisão que o
    número do trimestre leva quando o IBGE publica o ano."""
    primeiro = trimestres[0].year
    de_hoje = {s: crescimento(v) for s, v in final.indice.items()}
    saida: dict[str, list[float]] = {s: [] for s in indicador}
    for y in range(primeiro + 2, final.ultimo_oficial):
        e = estimar(trimestres, indicador, volume, corrente, pib_brasil, corrente_brasil, y, voltas)
        for s in indicador:
            antes = crescimento(e.indice[s])
            for t, tri in enumerate(trimestres):
                if y < tri.year <= min(y + 2, final.ultimo_oficial):
                    a, h = antes[t], de_hoje[s][t]
                    if a is not None and h is not None:
                        saida[s].append(h - a)
    return saida
