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


def test_termo_de_curva_plana_e_a_propria_taxa_e_compoe_com_o_trecho_anterior() -> None:
    plana = curvas.Curva(BASE, ((100, 0.10), (3000, 0.10)))
    assert curvas.termo(plana, 500, 1500) == pytest.approx(10.0)
    inclinada = curvas.Curva(BASE, ((252, 0.10), (504, 0.12)))
    termo = curvas.termo(inclinada, 252, 504) / 100
    assert (1.10 * (1 + termo)) == pytest.approx(1.12**2)
    with pytest.raises(ValueError):
        curvas.termo(inclinada, 252, 600)


def test_perna_real_sem_preco_antes_do_primeiro_vertice() -> None:
    real = curvas.Curva(BASE, ((600, 0.07), (2000, 0.075)))
    assert not curvas.tem_real(real, 300)
    assert curvas.tem_real(real, 600)
    assert not curvas.tem_real(real, 2001)


def test_taxa_do_preco_desfaz_o_preco_da_taxa() -> None:
    vencimento = date(2028, 8, 15)
    fl = curvas.fluxos(BASE, vencimento, curvas.CUPOM_NTNB)
    cotacao = sum(v / 1.0725 ** (du / 252) for du, v in fl)
    taxa = curvas.taxa_do_preco(BASE, vencimento, curvas.CUPOM_NTNB, cotacao)
    assert taxa == pytest.approx(7.25, abs=1e-6)


def test_vna_projetado_anda_do_dia_15_ao_seguinte() -> None:
    # 15/11/2026 é domingo: a conta de dias úteis começa na segunda, 16.
    assert curvas.mes_do_vna(date(2026, 11, 13)) == date(2026, 10, 1)
    assert curvas.mes_do_vna(date(2026, 11, 16)) == date(2026, 11, 1)
    assert curvas.vna_projetado(1000.0, date(2026, 10, 15), 0.5) == pytest.approx(1000.0)
    quase = curvas.vna_projetado(1000.0, date(2026, 11, 13), 0.5)
    assert 1004.5 < quase < 1005.0


def test_papel_curto_com_cupom_entra_no_comeco_da_curva() -> None:
    zero = [(date(2029, 5, 15), 7.5), (date(2032, 8, 15), 7.8)]
    curtos = [(date(2027, 5, 15), 4.0), (date(2028, 8, 15), 7.3)]
    curva = curvas.montar(BASE, zero, [], curvas.CUPOM_NTNB, curtos)
    assert len(curva.vertices) == 4
    # O primeiro papel vira a própria taxa; o segundo tem o preço refeito pela curva.
    assert curva.vertices[0][1] == pytest.approx(0.04, abs=1e-6)
    fl = curvas.fluxos(BASE, date(2028, 8, 15), curvas.CUPOM_NTNB)
    pela_taxa = sum(v / 1.073 ** (du / 252) for du, v in fl)
    pela_curva = sum(v * curva.fator_de_desconto(du) for du, v in fl)
    assert pela_curva == pytest.approx(pela_taxa, abs=1e-9)
    # Sem os curtos, a curva é a de antes.
    assert curvas.montar(BASE, zero, [], curvas.CUPOM_NTNB).vertices == curva.vertices[2:]
