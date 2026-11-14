"""Da curva de DI futuro às taxas a termo: o CDI que o mercado embute em cada mês."""

from __future__ import annotations

from datetime import date

from sacibras.calendario import dias_uteis
from sacibras.tipos import Ponto


def a_termo(curva: list[Ponto], referencia: date) -> list[Ponto]:
    """Taxa a termo (% a.a., base 252) entre vértices consecutivos da curva de DI.

    `curva` é [(vencimento, taxa % a.a. da referência até o vencimento)]. O ponto devolvido
    na data D é a taxa embutida entre D e o vértice seguinte; o primeiro vale da referência
    até o primeiro vencimento.
    """
    saida: list[Ponto] = []
    anterior_data, anterior_fator = referencia, 1.0
    for vencimento, taxa in curva:
        prazo = dias_uteis(referencia, vencimento)
        if prazo <= 0:
            continue
        fator = (1 + taxa / 100) ** (prazo / 252)
        dias = dias_uteis(anterior_data, vencimento)
        if dias > 0:
            termo = ((fator / anterior_fator) ** (252 / dias) - 1) * 100
            saida.append((anterior_data, termo))
        anterior_data, anterior_fator = vencimento, fator
    return saida
