"""As contas do Laboratório, sem rede."""

from datetime import date

import pytest

from sacibras.modelos import estatistica
from sacibras.secoes import laboratorio as lab


def test_juro_neutro_do_focus_desconta_o_ipca_do_mesmo_ano() -> None:
    selic = {date(2026, 9, 25): {2029: 10.5}, date(2026, 9, 24): {2029: 10.0}}
    ipca = {date(2026, 9, 25): {2029: 3.5}, date(2026, 9, 24): {2029: 3.5}}
    [(trimestre, real)] = lab.neutro_do_focus(selic, ipca)
    assert trimestre == date(2026, 7, 1)
    assert real == pytest.approx((1.105 / 1.035 - 1) * 100)  # vale a coleta mais nova


def test_media_de_dez_anos_do_juro_real() -> None:
    meses = [date(2000 + i // 12, i % 12 + 1, 1) for i in range(12 * 11)]
    selic = [(d, 10.0) for d in meses]
    esperada = [(d, 4.0) for d in meses]
    media = lab.neutro_da_media(selic, esperada)
    assert media[0][0] == date(2009, 10, 1)  # o primeiro trimestre com 40 antes dele
    assert media[-1][1] == pytest.approx((1.10 / 1.04 - 1) * 100)


def test_regra_de_taylor_com_a_faixa_entre_os_metodos() -> None:
    t = date(2026, 7, 1)
    [(trimestre, meio, lo, hi)] = lab.regra_de_taylor(
        {"a": {t: 5.0}, "b": {t: 7.0}},
        {"hp": {date(2026, 4, 1): -1.0}, "hamilton": {date(2026, 4, 1): 2.0}},
        {t: 4.0},
        {2026: 3.0},
    )
    # r + 4 + 0,5·(4 − 3) + 0,5·h: de 5 + 4,5 − 0,5 = 9 a 7 + 4,5 + 1 = 12,5.
    assert (trimestre, lo, hi) == (t, 9.0, 12.5)
    assert meio == pytest.approx((10.0 + 11.5) / 2)


def test_hiatos_por_dois_filtros() -> None:
    pib = [(date(1996 + i // 4, 3 * (i % 4) + 1, 1), 100 * 1.005**i) for i in range(60)]
    gaps = lab.hiatos(pib)
    assert len(gaps["hp"]) == 60 and len(gaps["hamilton"]) == 60 - 11
    assert max(abs(v) for _, v in gaps["hp"]) < 1e-6  # crescer em ritmo fixo não tem hiato


def test_reacao_fiscal_acha_a_reacao_que_foi_posta() -> None:
    anos = list(range(2000, 2026))
    divida = {a: 40.0 + (a % 7) * 3 for a in range(1999, 2026)}
    hiato = {a: ((a * 37) % 11 - 5) / 5 for a in anos}
    primario = {a: -2.0 + 0.08 * divida[a - 1] + 0.3 * hiato[a] for a in anos}
    r = lab.reacao_fiscal(primario, divida, hiato, anos)
    assert r.coef[1] == pytest.approx(0.08) and r.coef[2] == pytest.approx(0.3)


def test_decomposicao_soma_e_pib_contra_os_eua() -> None:
    brasil = {
        2000: {"rgdpna": 100.0, "pop": 10.0, "emp": 4.0},
        2010: {"rgdpna": 150.0, "pop": 11.0, "emp": 5.0},
    }
    pc, prod, ocup = lab.decompor(brasil, 2000, 2010)
    assert pc == pytest.approx(prod + ocup)
    dados = {
        "BRA": {2000: {"rgdpe": 50.0, "pop": 10.0}},
        "USA": {2000: {"rgdpe": 200.0, "pop": 10.0}},
    }
    assert lab.contra_os_eua(dados, "BRA") == [(date(2000, 1, 1), 25.0)]


def test_reunioes_rotuladas_como_o_focus() -> None:
    from sacibras.fontes.bcb_copom import Reuniao

    todas = [Reuniao(1, date(2025, 12, 10), 15.0), Reuniao(2, date(2026, 1, 28), 15.0)]
    todas += [Reuniao(3, date(2026, 3, 18), 14.75)]
    rotulos = [k for k, _ in lab.reunioes_rotuladas(todas)]
    assert rotulos == ["R1/2025", "R1/2026", "R2/2026"]
    assert estatistica.mqo([1.0, 2.0, 3.1], [[1.0], [2.0], [3.0]]).n == 3
