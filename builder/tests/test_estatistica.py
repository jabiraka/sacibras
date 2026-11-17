"""Mínimos quadrados, HP e Hamilton contra casos de resposta conhecida."""

import math

import pytest

from sacibras.modelos import estatistica as e


def test_mqo_acha_a_reta_exata_e_o_intervalo_cobre_o_verdadeiro() -> None:
    x = [[float(i)] for i in range(20)]
    y = [2.0 + 0.5 * i for i in range(20)]
    r = e.mqo(y, x)
    assert r.coef == pytest.approx([2.0, 0.5]) and r.r2 == pytest.approx(1.0)
    # Com ruído determinístico, o 0,5 fica dentro do intervalo de 90 %.
    ruido = [math.sin(i * 1.7) for i in range(40)]
    r = e.mqo([1 + 0.5 * i + ruido[i] for i in range(40)], [[float(i)] for i in range(40)])
    lo, hi = r.intervalo(1)
    assert lo < 0.5 < hi and hi - lo < 0.1


def test_mqo_recusa_variavel_repetida() -> None:
    with pytest.raises(ValueError):
        e.mqo([1.0, 2.0, 3.0, 4.0], [[1.0, 2.0], [2.0, 4.0], [3.0, 6.0], [4.0, 8.0]])


def test_hp_deixa_a_reta_e_alisa_o_vaivem() -> None:
    reta = [float(i) for i in range(30)]
    assert e.hp(reta) == pytest.approx(reta, abs=1e-6)
    vaivem = [i + (1 if i % 2 else -1) for i in range(40)]
    tendencia = e.hp(vaivem)
    assert max(abs(t - i) for i, t in enumerate(tendencia[5:-5], start=5)) < 0.2


def test_hamilton_tira_a_tendencia_e_deixa_o_ciclo() -> None:
    serie = [0.02 * i * i + math.sin(i / 2) for i in range(80)]
    ciclo = e.hamilton(serie)
    assert ciclo[:11] == [None] * 11 and len(ciclo) == 80
    valores = [c for c in ciclo if c is not None]
    assert abs(sum(valores) / len(valores)) < 1e-9  # resíduo de MQO com constante
    assert max(abs(c) for c in valores) < 3  # a parábola sai; sobra o vaivém
