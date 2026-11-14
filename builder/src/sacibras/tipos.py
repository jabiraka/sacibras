"""Os tipos que atravessam o builder: ponto de série, periodicidade e unidade."""

from __future__ import annotations

from datetime import date
from typing import Literal

Ponto = tuple[date, float]
"""(data de referência, valor). Mensal usa o dia 1 do mês; trimestral, o 1º dia do
trimestre; anual, 1º de janeiro."""

Periodicidade = Literal["D", "M", "T", "A"]

Unidade = Literal[
    "% a.a.",
    "% a.m.",
    "% a.d.",
    "% em 12 meses",
    "% no mês",
    "% no trimestre",
    "% no ano",
    "%",
    "pp",
    "% do PIB",
    "% da RCL",
    "R$ milhões",
    "R$ bilhões",
    "US$ milhões",
    "US$ bilhões",
    "R$/US$",
    "R$",
    "US$",
    "pontos",
    "índice",
    "pessoas",
    "mil pessoas",
    "milhões de pessoas",
    "pontos-base",
    "meses",
]


def ultimo(pontos: list[Ponto]) -> Ponto:
    if not pontos:
        raise ValueError("série vazia")
    return pontos[-1]


def desde(pontos: list[Ponto], inicio: date) -> list[Ponto]:
    return [p for p in pontos if p[0] >= inicio]
