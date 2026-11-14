"""Quanto o consenso costuma errar: o histórico de acerto do Focus, medido na própria API.

Para cada ano passado, pega-se a mediana que o Focus tinha *nesta mesma época do ano* e
compara-se com o que aconteceu. O erro típico é a média do erro absoluto. Limite declarado:
o realizado é o dado de hoje (o PIB é revisado), não o que se conhecia na época.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sacibras.fontes import bcb_focus


@dataclass(frozen=True)
class Acerto:
    horizonte: int
    """0: a aposta para o próprio ano; 1: para o ano seguinte."""
    erro_tipico: float
    """Média do erro absoluto, em pontos percentuais."""
    vies: float
    """Média do erro com sinal (aposta menos realizado): positivo = o mercado superestimou."""
    anos: list[int]
    """Os anos-alvo que entraram na conta."""


def medir(
    indicador: str, realizado: dict[int, float], hoje: date, horizonte: int, desde: int = 2010
) -> Acerto | None:
    dia = min(hoje.day, 28)
    erros: list[float] = []
    anos: list[int] = []
    for ano in range(desde, hoje.year):
        alvo = ano + horizonte
        if alvo not in realizado or alvo >= hoje.year:
            continue
        aposta = bcb_focus.mediana_em(indicador, alvo, date(ano, hoje.month, dia))
        if aposta is None:
            continue
        erros.append(aposta - realizado[alvo])
        anos.append(alvo)
    if len(erros) < 5:
        return None
    return Acerto(
        horizonte=horizonte,
        erro_tipico=sum(abs(e) for e in erros) / len(erros),
        vies=sum(erros) / len(erros),
        anos=anos,
    )
