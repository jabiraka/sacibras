"""A dinâmica da dívida: de onde ela parte e o que a move.

    d₊₁ = d · (1 + i) / ((1 + g) · (1 + π)) − p

`d` é a dívida em % do PIB, `i` o juro nominal que ela paga, `g` o crescimento real do PIB,
`π` a inflação e `p` o resultado primário em % do PIB (superávit positivo). A conta é feita
aqui para a linha de base e refeita no navegador quando a pessoa mexe nos controles.
"""

from __future__ import annotations


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
