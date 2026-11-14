from datetime import date
from typing import Any

import pytest

from sacibras.modelos import acerto_focus, divida, pib_agora


def _trimestres(n: int, inicio: int = 2010) -> list[date]:
    return [date(inicio + i // 4, 3 * (i % 4) + 1, 1) for i in range(n)]


def test_ibc_trimestral_compara_os_mesmos_meses_de_um_ano_antes() -> None:
    # 2025 inteiro em 100; em 2026 só jan e fev saíram, em 110: o trimestre vale +10 %, com 2
    # meses (e não a média de dois meses contra a de três).
    ibc = [(date(2025, m, 1), 100.0) for m in range(1, 13)]
    ibc += [(date(2026, 1, 1), 110.0), (date(2026, 2, 1), 110.0)]
    assert pib_agora.ibc_trimestral(ibc)[date(2026, 1, 1)] == (pytest.approx(10.0), 2)


def test_pib_agora_recupera_a_reta_e_erra_zero_quando_a_relacao_e_exata() -> None:
    # PIB a/a = 0,5 + 0,8 × IBC-Br a/a, sem ruído: a estimativa tem de cair na reta.
    trimestres = _trimestres(48)
    nivel: dict[date, float] = {}
    for i, t in enumerate(trimestres):
        crescimento = 0.0 if i < 4 else (i % 7) - 2.0  # varia de −2 a +4
        for k in range(3):
            mes = date(t.year, t.month + k, 1)
            base = nivel.get(date(mes.year - 1, mes.month, 1), 100.0)
            nivel[mes] = base * (1 + crescimento / 100)
    ibc = sorted(nivel.items())
    pib = [(t, 0.5 + 0.8 * pib_agora.ibc_trimestral(ibc)[t][0]) for t in trimestres[4:-1]]
    # Do último trimestre só saíram dois meses do IBC-Br.
    resultado = pib_agora.estimar(pib, ibc[:-1])
    assert resultado is not None
    assert resultado.trimestre == trimestres[-1]
    assert resultado.meses_disponiveis == 2
    assert resultado.inclinacao == pytest.approx(0.8)
    assert resultado.previsao == pytest.approx(0.5 + 0.8 * resultado.ibc_no_trimestre)
    assert resultado.erro_tipico == pytest.approx(0.0, abs=1e-9)


def test_pib_agora_nao_estima_sem_mes_do_trimestre() -> None:
    trimestres = _trimestres(48)
    ibc = [
        (date(t.year, t.month + k, 1), 100.0 + i)
        for i, t in enumerate(trimestres)
        for k in range(3)
    ]
    pib = [(t, 1.0) for t in trimestres[4:]]  # o PIB já saiu até o último trimestre do IBC-Br
    assert pib_agora.estimar(pib, ibc) is None


def test_divida_sobe_quando_o_juro_real_passa_do_crescimento() -> None:
    # 80 % do PIB, juro de 10 %, inflação de 4 %, crescimento de 2 %, primário zero.
    (fim,) = divida.trajetoria(80.0, [10.0], [2.0], [4.0], [0.0])
    assert fim == pytest.approx(80.0 * 1.10 / (1.02 * 1.04))
    # Um superávit primário de 1 % do PIB abate exatamente 1 ponto.
    (com_superavit,) = divida.trajetoria(80.0, [10.0], [2.0], [4.0], [1.0])
    assert fim - com_superavit == pytest.approx(1.0)


def test_estender_repete_a_ultima_mediana() -> None:
    assert divida.estender({2027: 1.0, 2028: 2.0}, [2027, 2028, 2029, 2030]) == [1.0, 2.0, 2.0, 2.0]


def test_acerto_do_focus_mede_erro_absoluto_e_vies(monkeypatch: pytest.MonkeyPatch) -> None:
    # A aposta foi sempre 1 ponto acima do realizado nos anos pares e 1 abaixo nos ímpares.
    realizado = {ano: 4.0 for ano in range(2010, 2026)}

    def aposta(indicador: str, alvo: int, quando: date, **kw: Any) -> float:
        assert quando.year == alvo and (quando.month, quando.day) == (11, 14)
        return 5.0 if alvo % 2 == 0 else 3.0

    monkeypatch.setattr(acerto_focus.bcb_focus, "mediana_em", aposta)
    medido = acerto_focus.medir("IPCA", realizado, date(2026, 11, 14), horizonte=0)
    assert medido is not None
    assert medido.erro_tipico == pytest.approx(1.0)
    assert medido.vies == pytest.approx(0.0)
    assert medido.anos == list(range(2010, 2026))
