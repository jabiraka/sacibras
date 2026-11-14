from datetime import date

import pytest

from sacibras import contas


def _mensal(valores: list[float], ano: int = 2025) -> list[tuple[date, float]]:
    return [(date(ano + i // 12, i % 12 + 1, 1), v) for i, v in enumerate(valores)]


def test_acumulado_compoe_as_taxas_e_nao_soma() -> None:
    # 12 meses de 1 % ao mês são 12,68 %, e não 12 %.
    serie = _mensal([1.0] * 12)
    assert contas.acumulado(serie, 12) == [(date(2025, 12, 1), pytest.approx(12.6825, abs=1e-4))]


def test_variacao_contra_12_meses_antes() -> None:
    serie = _mensal([100.0] * 12 + [110.0])
    assert contas.variacao(serie, 12) == [(date(2026, 1, 1), pytest.approx(10.0))]


def test_no_ano_compara_com_o_ultimo_ponto_do_ano_anterior() -> None:
    serie = [(date(2025, 12, 30), 100.0), (date(2026, 1, 2), 90.0), (date(2026, 11, 13), 107.0)]
    assert contas.no_ano(serie) == pytest.approx(7.0)


def test_em_dias_usa_o_ponto_anterior_quando_a_data_exata_nao_existe() -> None:
    # 30 dias antes de 13/11 é 14/10, que não teve pregão: vale o de 13/10.
    serie = [(date(2026, 10, 13), 200.0), (date(2026, 10, 15), 180.0), (date(2026, 11, 13), 100.0)]
    assert contas.em_dias(serie, 30) == pytest.approx(-50.0)


def test_media_das_series_so_onde_todas_tem_valor() -> None:
    a = _mensal([1.0, 2.0, 3.0])
    b = _mensal([3.0, 4.0])
    assert contas.media_das_series([a, b]) == [(date(2025, 1, 1), 2.0), (date(2025, 2, 1), 3.0)]


def test_soma_movel_e_diferenca() -> None:
    serie = _mensal([1.0, 2.0, 3.0, 4.0])
    assert [v for _, v in contas.soma_movel(serie, 3)] == [6.0, 9.0]
    assert [v for _, v in contas.diferenca(serie)] == [1.0, 1.0, 1.0]
