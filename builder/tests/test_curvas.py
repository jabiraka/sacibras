"""A curva zero do Tesouro (o método do Jabs) e o Focus na mesma régua."""

from datetime import date

import pytest

from sacibras import curvas
from sacibras.calendario import dias_uteis

BASE = date(2026, 11, 12)


def test_curva_plana_devolve_a_taxa_em_qualquer_prazo() -> None:
    c = curvas.Curva(BASE, ((100, 0.10), (500, 0.10)))
    assert c.taxa(50) == pytest.approx(0.10)
    assert c.taxa(300) == pytest.approx(0.10)
    with pytest.raises(ValueError):
        c.fator_de_desconto(501)  # nunca extrapola depois do último vértice


def test_interpolacao_log_linear_tem_termo_constante_no_trecho() -> None:
    c = curvas.Curva(BASE, ((252, 0.10), (504, 0.12)))
    termo = c.fator_de_desconto(252) / c.fator_de_desconto(504)
    meio = c.fator_de_desconto(252) / c.fator_de_desconto(378)
    assert meio**2 == pytest.approx(termo)


def test_bootstrap_reproduz_o_preco_do_papel_com_cupom() -> None:
    vencimento = date(2035, 1, 1)
    zero = [(date(2028, 1, 1), 14.0), (date(2032, 1, 1), 15.0)]
    c = curvas.montar(BASE, zero, [(vencimento, 15.3)], curvas.CUPOM_NTNF)
    fl = curvas.fluxos(BASE, vencimento, curvas.CUPOM_NTNF)
    preco = sum(v / 1.153 ** (du / 252) for du, v in fl)
    assert sum(v * c.fator_de_desconto(du) for du, v in fl) == pytest.approx(preco, rel=1e-9)
    assert c.fim == dias_uteis(BASE, vencimento)


def test_fluxos_da_ntnb_caem_a_cada_seis_meses_ate_o_vencimento() -> None:
    fl = curvas.fluxos(BASE, date(2028, 8, 15), curvas.CUPOM_NTNB)
    assert len(fl) == 4  # fev/27, ago/27, fev/28, ago/28
    assert fl[-1][1] == pytest.approx(1 + curvas.CUPOM_NTNB)


def test_inflacao_implicita_e_a_razao_entre_as_duas_pernas() -> None:
    nominal = curvas.Curva(BASE, ((100, 0.14), (2000, 0.14)))
    real = curvas.Curva(BASE, ((100, 0.07), (1500, 0.07)))
    pontos = curvas.inflacao_implicita(nominal, real, [date(2029, 1, 1), date(2034, 1, 1)])
    assert [p.vencimento for p in pontos] == [date(2029, 1, 1)]  # 2034 passa da perna real
    assert pontos[0].implicita == pytest.approx((1.14 / 1.07 - 1) * 100)


def test_media_do_caminho() -> None:
    assert curvas.media_do_caminho([(BASE, 10.0)], BASE, date(2030, 1, 1)) == pytest.approx(10)
    meio = date(2028, 1, 1)
    media = curvas.media_do_caminho(
        [(date(2026, 1, 1), 14.0), (meio, 10.0)], BASE, date(2030, 1, 1)
    )
    a, b = dias_uteis(BASE, meio), dias_uteis(meio, date(2030, 1, 1))
    esperado = ((1.14 ** (a / 252) * 1.10 ** (b / 252)) ** (252 / (a + b)) - 1) * 100
    assert media == pytest.approx(esperado)
