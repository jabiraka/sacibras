"""A dinâmica da dívida: de onde ela parte e o que a move.

    d₊₁ = d · (1 + i) / ((1 + g) · (1 + π)) − p

`d` é a dívida em % do PIB, `i` o juro nominal que ela paga, `g` o crescimento real do PIB,
`π` a inflação e `p` o resultado primário em % do PIB (superávit positivo). A conta é feita
aqui para a linha de base e refeita no navegador quando a pessoa mexe nos controles.
"""

from __future__ import annotations

from datetime import date

from sacibras.tipos import Ponto


def trajetoria(
    inicial: float,
    juro: list[float],
    crescimento: list[float],
    inflacao: list[float],
    primario: list[float],
) -> list[float]:
    """A dívida (% do PIB) ao fim de cada ano, dadas as hipóteses ano a ano (todas em %)."""
    divida, saida = inicial, []
    for i, g, pi, p in zip(juro, crescimento, inflacao, primario, strict=True):
        divida = divida * (1 + i / 100) / ((1 + g / 100) * (1 + pi / 100)) - p
        saida.append(divida)
    return saida


def estender(valores: dict[int, float], anos: list[int]) -> list[float]:
    """Um valor por ano de `anos`: o do Focus onde existe, e o último conhecido daí em diante."""
    saida: list[float] = []
    ultimo = valores[min(valores)]
    for ano in anos:
        ultimo = valores.get(ano, ultimo)
        saida.append(ultimo)
    return saida


def _doze_meses(mensal: list[Ponto]) -> dict[date, float]:
    """{mês: soma dos 12 meses até ele}, só com os 12 meses seguidos na série."""
    por_mes = dict(mensal)
    saida: dict[date, float] = {}
    for d in sorted(por_mes):
        meses = [date(d.year - (d.month <= k), (d.month - k - 1) % 12 + 1, 1) for k in range(12)]
        if all(m in por_mes for m in meses):
            saida[d] = sum(por_mes[m] for m in meses)
    return saida


def juros_sobre_receita(juros_mes: list[Ponto], receita_mes: list[Ponto]) -> list[Ponto]:
    """Quanto da receita de 12 meses foi para os juros de 12 meses (%), mês a mês.

    Os dois fluxos mensais na mesma unidade (R$ milhões correntes); só os meses em que as
    duas somas de 12 meses estão completas."""
    juros, receita = _doze_meses(juros_mes), _doze_meses(receita_mes)
    return [(d, juros[d] / receita[d] * 100) for d in sorted(juros) if receita.get(d)]


def diferenca_de_conceito(
    outra: dict[int, float], bc: dict[int, float], ate: int
) -> tuple[int, float] | None:
    """(ano, outra − bc) no ano mais novo, até `ate`, em que as duas medidas existem: quanto
    a dívida de outro conceito (a do FMI) passa a do Banco Central no mesmo ano."""
    comuns = [a for a in outra if a in bc and a <= ate]
    if not comuns:
        return None
    ano = max(comuns)
    return ano, outra[ano] - bc[ano]


def parcela(parte: list[Ponto], total: list[Ponto]) -> list[Ponto]:
    """A parte como % do total, nas datas em que os dois existem."""
    todo = dict(total)
    return [(d, v / todo[d] * 100) for d, v in parte if todo.get(d)]
