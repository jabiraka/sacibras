from datetime import date

import pytest

from sacibras.calendario import dia_util, dias_uteis, feriados, pascoa, ultimo_dia_util
from sacibras.juros_futuros import a_termo


@pytest.mark.parametrize(
    ("ano", "esperado"),
    [(2024, date(2024, 3, 31)), (2025, date(2025, 4, 20)), (2026, date(2026, 4, 5))],
)
def test_pascoa(ano: int, esperado: date) -> None:
    assert pascoa(ano) == esperado


def test_feriados_moveis_de_2026() -> None:
    f = feriados(2026)
    assert date(2026, 2, 16) in f and date(2026, 2, 17) in f  # Carnaval
    assert date(2026, 4, 3) in f  # Sexta-feira Santa
    assert date(2026, 6, 4) in f  # Corpus Christi
    assert date(2026, 11, 20) in f  # Consciência Negra, nacional desde 2024
    assert date(2023, 11, 20) not in feriados(2023)


def test_dias_uteis_conta_o_primeiro_e_nao_o_ultimo() -> None:
    # De sexta 13/11/2026 a 1º/12/2026: 13, 16–19 (20 é feriado), 23–27 e 30/11 → 11 dias.
    assert dias_uteis(date(2026, 11, 13), date(2026, 12, 1)) == 11
    assert dias_uteis(date(2026, 1, 1), date(2027, 1, 1)) == 249


def test_ultimo_dia_util_volta_do_fim_de_semana() -> None:
    assert not dia_util(date(2026, 11, 14))
    assert ultimo_dia_util(date(2026, 11, 14)) == date(2026, 11, 13)


def test_taxa_a_termo_recompoe_a_curva() -> None:
    # Curva chata em 10 %: toda taxa a termo é 10 %.
    referencia = date(2026, 11, 13)
    chata = [(date(2027, 1, 4), 10.0), (date(2028, 1, 3), 10.0)]
    assert [round(v, 6) for _, v in a_termo(chata, referencia)] == [10.0, 10.0]
    # Curva que sobe: o trecho a termo fica acima da taxa longa.
    sobe = [(date(2027, 1, 4), 10.0), (date(2028, 1, 3), 12.0)]
    termo = a_termo(sobe, referencia)
    assert termo[0] == (referencia, pytest.approx(10.0))
    assert termo[1][0] == date(2027, 1, 4) and termo[1][1] > 12.0
