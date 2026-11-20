"""Indicadores de 20/11/2026: a inclinação da curva, a inflação esperada contra a meta e o
Ibovespa descontada a inflação."""

from __future__ import annotations

from datetime import date

import pytest

from sacibras.secoes import inflacao, juros, mercados


def test_inclinacao_e_o_prefixado_de_tres_anos_menos_a_selic() -> None:
    pre = {
        date(2026, 1, 15): [(date(2027, 1, 1), 99.0)],  # não é o último dia do mês
        date(2026, 1, 30): [(date(2028, 1, 30), 12.0), (date(2030, 1, 30), 14.0)],
        date(2026, 2, 27): [(date(2028, 2, 27), 12.0), (date(2030, 2, 27), 11.0)],
    }
    selic = [(date(2025, 1, 1), 13.0), (date(2026, 2, 1), 12.0)]
    pontos = juros.inclinacao_no_tempo(pre, selic)
    assert [d for d, _ in pontos] == [date(2026, 1, 1), date(2026, 2, 1)]
    assert pontos[0][1] == pytest.approx(0.0, abs=0.01)  # 13 % no meio do caminho, Selic 13
    assert pontos[1][1] == pytest.approx(-0.5, abs=0.01)  # curva invertida


def test_inclinacao_nao_estica_a_curva_curta_demais() -> None:
    pre = {date(2026, 1, 30): [(date(2027, 1, 30), 12.0), (date(2028, 1, 30), 12.5)]}
    assert juros.inclinacao_no_tempo(pre, [(date(2025, 1, 1), 13.0)]) == []
    # A até 90 dias do prazo, vale a ponta.
    pre = {date(2026, 1, 30): [(date(2027, 1, 30), 12.0), (date(2028, 12, 30), 12.5)]}
    assert juros.inclinacao_no_tempo(pre, [(date(2025, 1, 1), 13.0)]) == [
        (date(2026, 1, 1), pytest.approx(-0.5))
    ]


def test_expectativa_contra_a_meta_do_mesmo_periodo() -> None:
    esperada = [(date(2024, 6, 14), 3.9), (date(2024, 6, 28), 4.0), (date(2026, 10, 30), 4.4)]
    g = inflacao.grafico_expectativa(esperada, {2024: 3.0, 2025: 3.0}, date(2024, 1, 1), "f")
    assert g is not None
    assert g.id == "expectativa-meta"
    assert g.series[0].pontos == [(date(2024, 6, 1), 4.0), (date(2026, 10, 1), 4.4)]
    assert g.series[1].papel == "referencia"
    assert [v for _, v in g.series[1].pontos] == [3.0, 3.0]
    assert g.manchete == "4,40 % em out/2026, 1,40 pp acima do centro da meta."
    assert inflacao.grafico_expectativa([], {2024: 3.0}, date(2024, 1, 1), "f") is None


def test_ibovespa_real_leva_o_passado_a_precos_do_ultimo_ipca() -> None:
    ibov = [
        (date(2026, 8, 14), 90_000.0),
        (date(2026, 8, 31), 100_000.0),
        (date(2026, 9, 30), 100_000.0),
        (date(2026, 10, 20), 101_000.0),  # mês ainda sem IPCA: entra sem correção
    ]
    ipca = [(date(2026, 8, 1), 0.5), (date(2026, 9, 1), 1.0)]
    pontos, base = mercados.ibovespa_real(ibov, ipca)
    assert base == date(2026, 9, 1)
    assert pontos == [
        (date(2026, 8, 1), pytest.approx(101_000.0)),
        (date(2026, 9, 1), pytest.approx(100_000.0)),
        (date(2026, 10, 1), 101_000.0),
    ]
    assert mercados.ibovespa_real([], ipca) == ([], None)
