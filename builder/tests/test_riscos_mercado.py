"""Riscos › juro real contra os EUA, expectativa e implícita contra a meta, e os números do
painel contra outros países (reservas, câmbio), com dados fabricados."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from sacibras import curvas
from sacibras.calendario import dias_uteis
from sacibras.fontes import bis, fmi, fred, tesouro_direto
from sacibras.secoes import mundo, riscos


def test_ultimo_de_cada_mes_fica_com_o_ultimo_dia() -> None:
    pontos = [(date(2026, 1, 5), 1.0), (date(2026, 1, 30), 2.0), (date(2026, 2, 2), 3.0)]
    assert riscos.ultimo_de_cada_mes(pontos) == [(date(2026, 1, 30), 2.0), (date(2026, 2, 2), 3.0)]


def test_meta_media_pesa_cada_ano_pelos_meses_dele() -> None:
    metas = {2018: 4.5, 2019: 4.25, 2020: 4.0}
    # Medido em out/2018: nov e dez de 2018 (4,5) e jan a out de 2019 (4,25).
    assert riscos.meta_media(metas, date(2018, 10, 31), 12) == pytest.approx(
        (2 * 4.5 + 10 * 4.25) / 12
    )
    # Em dezembro, os 12 meses seguintes são o ano seguinte inteiro.
    assert riscos.meta_media(metas, date(2018, 12, 31), 12) == pytest.approx(4.25)
    # Ano sem meta fixada leva a última; antes da primeira, a primeira.
    assert riscos.meta_media(metas, date(2020, 6, 30), 24) == pytest.approx(4.0)
    assert riscos.meta_media(metas, date(2010, 12, 31), 12) == pytest.approx(4.5)


def test_acima_da_meta_em_pontos() -> None:
    saida = riscos.acima_da_meta([(date(2025, 12, 31), 5.0)], {2025: 3.0, 2026: 3.0}, 12)
    assert saida == [(date(2025, 12, 31), pytest.approx(2.0))]


def test_juro_real_e_implicita_no_prazo_da_curva() -> None:
    base = date(2026, 1, 2)
    real = curvas.Curva(base, ((dias_uteis(base, date(2028, 1, 2)), 0.06), (3000, 0.07)))
    nominal = curvas.Curva(base, ((250, 0.12), (3000, 0.12)))
    r10 = riscos.real_no_prazo(real, 10)
    assert r10 is not None
    du = dias_uteis(base, date(2036, 1, 2))
    assert r10 == pytest.approx(real.taxa(du) * 100)
    i8 = riscos.implicita_no_prazo(nominal, real, 8)
    assert i8 is not None
    r8 = riscos.real_no_prazo(real, 8)
    assert r8 is not None
    assert i8 == pytest.approx((1.12 / (1 + r8 / 100) - 1) * 100)
    # Antes do primeiro IPCA+ não há juro real (nada se estica para trás).
    assert riscos.real_no_prazo(real, 1) is None
    # Depois do último vértice, nada.
    assert riscos.real_no_prazo(real, 15) is None


def test_diferenca_por_mes_so_onde_os_dois_tem() -> None:
    brasil = [(date(2026, 9, 30), 7.5), (date(2026, 10, 30), 7.7)]
    eua = [(date(2026, 10, 29), 1.9), (date(2026, 11, 12), 2.0)]
    assert riscos.diferenca_por_mes(brasil, eua) == [(date(2026, 10, 30), pytest.approx(5.8))]


def test_tesouro_direto_sem_linha_sem_preco_nem_taxa_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    cabeca = "Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha;"
    cabeca += "PU Compra Manha;PU Venda Manha;PU Base Manha\n"
    ntnf = "Tesouro Prefixado com Juros Semestrais"
    linhas = [
        f"{ntnf};01/01/2017;29/01/2010;13,23;13,29;871,51;869,22;868,79",
        f"{ntnf};01/01/2021;29/01/2010;0,00;0,06;0,00;0,00;0,00",  # sem preço: fora
        f"{ntnf};01/01/2014;29/01/2010;0,00;12,76;0,00;929,20;928,76",  # só a venda
    ]
    corpo = (cabeca + "\n".join(linhas)).encode("latin-1")
    monkeypatch.setattr(tesouro_direto, "baixar", lambda *a, **k: corpo)
    saida = tesouro_direto.curvas(date(2010, 1, 1))[ntnf][date(2010, 1, 29)]
    assert saida == [(date(2014, 1, 1), 12.76), (date(2017, 1, 1), pytest.approx(13.26))]


def test_csv_do_fred_sem_os_dias_em_branco() -> None:
    texto = "observation_date,DFII10\n2026-11-10,2.78\n2026-11-11,\n2026-11-12,2.86\n"
    assert fred.ler_csv(texto) == [(date(2026, 11, 10), 2.78), (date(2026, 11, 12), 2.86)]


def test_periodo_diario_do_bis() -> None:
    assert bis._periodo("2026-11-10") == date(2026, 11, 10)
    assert bis._periodo("2025-Q3") == date(2025, 7, 1)
    assert bis._periodo("2025-07") == date(2025, 7, 1)


def test_resposta_do_fmi_por_pais() -> None:
    bruto = {
        "structure": {
            "dimensions": {
                "series": [{"values": [{"id": "BRA"}, {"id": "MEX"}]}],
                "observation": [{"values": [{"id": "2024"}, {"id": "2025"}]}],
            }
        },
        "dataSets": [
            {
                "series": {
                    "0:0:0:0": {"observations": {"0": ["330"], "1": ["358"]}},
                    "1:0:0:0": {"observations": {"1": ["250"], "0": [None]}},
                }
            }
        ],
    }
    assert fmi.anuais_por_pais(bruto) == {
        "BRA": {2024: 330.0, 2025: 358.0},
        "MEX": {2025: 250.0},
    }


def test_reservas_em_meses_de_importacao() -> None:
    saida = mundo.reservas_em_meses(
        {"BRA": {2024: 330.0, 2025: 360.0}, "XYZ": {2025: 10.0}},
        {"BRA": {2025: 400.0}},
        [2024, 2025],
    )
    # 360 ÷ (400 ÷ 12) = 10,8 meses; sem importação, nada.
    assert saida == {"BRA": [None, 10.8]}


def test_volatilidade_do_cambio_tira_parados_e_os_eua() -> None:
    inicio = date(2026, 9, 1)
    dias = [inicio + timedelta(days=i) for i in range(40)]
    sobe_desce = [(d, 5.0 * (1.01 if i % 2 else 1.0)) for i, d in enumerate(dias)]
    parado = [(d, 5.0 * (1.01 if i % 2 else 1.0)) for i, d in enumerate(dias[:20])]
    fixo = [(d, 1.0) for d in dias]
    vol, quando = mundo.volatilidade_do_cambio(
        {"BR": sobe_desce, "AR": parado, "US": fixo, "XM": sobe_desce}
    )
    assert quando == dias[-1]
    assert set(vol) == {"BRA"}
    assert vol["BRA"] > 0


def test_sem_anos_vazios_corta_o_ano_que_o_fmi_nao_fechou() -> None:
    anos, valores = mundo.sem_anos_vazios(
        [2024, 2025, 2026],
        {"BRA": [1.0, 2.0, None], "MEX": [1.0, None, None], "CHL": [None, 0.0, None]},
    )
    assert anos == [2024, 2025]
    assert valores == {"BRA": [1.0, 2.0], "MEX": [1.0, None], "CHL": [None, 0.0]}
