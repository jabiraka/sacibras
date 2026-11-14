"""Dias úteis do mercado brasileiro: fins de semana e feriados nacionais.

Os juros futuros (DI1) contam prazo em dias úteis, base 252. Os feriados aqui são os
nacionais (fixos e os móveis que saem da data da Páscoa); feriado só de praça (aniversário
de São Paulo, por exemplo) não entra na contagem do DI.
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache


def pascoa(ano: int) -> date:
    """Domingo de Páscoa (algoritmo de Meeus/Jones/Butcher, calendário gregoriano)."""
    a, b, c = ano % 19, ano // 100, ano % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    mes = (h + m - 7 * n + 114) // 31
    dia = (h + m - 7 * n + 114) % 31 + 1
    return date(ano, mes, dia)


@lru_cache(maxsize=64)
def feriados(ano: int) -> frozenset[date]:
    p = pascoa(ano)
    dias = {
        date(ano, 1, 1),  # Confraternização Universal
        p - timedelta(days=48),  # segunda de Carnaval
        p - timedelta(days=47),  # terça de Carnaval
        p - timedelta(days=2),  # Sexta-feira Santa
        date(ano, 4, 21),  # Tiradentes
        date(ano, 5, 1),  # Dia do Trabalho
        p + timedelta(days=60),  # Corpus Christi
        date(ano, 9, 7),  # Independência
        date(ano, 10, 12),  # Nossa Senhora Aparecida
        date(ano, 11, 2),  # Finados
        date(ano, 11, 15),  # Proclamação da República
        date(ano, 12, 25),  # Natal
    }
    if ano >= 2024:
        dias.add(date(ano, 11, 20))  # Consciência Negra, nacional desde 2024
    return frozenset(dias)


def dia_util(d: date) -> bool:
    return d.weekday() < 5 and d not in feriados(d.year)


_ORIGEM = date(1990, 1, 1)


@lru_cache(maxsize=1)
def _acumulados() -> tuple[int, ...]:
    """Dias úteis de 1990 até cada dia, até 2100: a contagem vira uma subtração."""
    saida, total, cursor = [0], 0, _ORIGEM
    while cursor.year <= 2100:
        total += dia_util(cursor)
        saida.append(total)
        cursor += timedelta(days=1)
    return tuple(saida)


def dias_uteis(inicio: date, fim: date) -> int:
    """Dias úteis em [inicio, fim): conta o primeiro, não conta o último."""
    if fim <= inicio:
        return 0
    if inicio >= _ORIGEM and fim.year <= 2100:
        acumulados = _acumulados()
        return acumulados[(fim - _ORIGEM).days] - acumulados[(inicio - _ORIGEM).days]
    total, cursor = 0, inicio
    while cursor < fim:
        total += dia_util(cursor)
        cursor += timedelta(days=1)
    return total


def ultimo_dia_util(d: date) -> date:
    while not dia_util(d):
        d -= timedelta(days=1)
    return d
