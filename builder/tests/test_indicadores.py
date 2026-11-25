"""Indicadores de 20/11/2026: a inclinação da curva, a inflação esperada contra a meta e o
Ibovespa descontada a inflação."""

from __future__ import annotations

from datetime import date

import pytest

from sacibras.secoes import inflacao, juros


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


def test_pib_por_habitante_desconta_o_crescimento_da_populacao() -> None:
    from sacibras.secoes import atividade

    pib, por_hab = atividade.pib_por_habitante(
        {2023: 100.0, 2024: 103.0, 2025: 103.0}, {2023: 200.0, 2024: 202.0, 2025: 206.12}
    )
    assert [d.year for d, _ in pib] == [2024, 2025]
    assert pib[0][1] == pytest.approx(3.0)
    assert por_hab[0][1] == pytest.approx((1.03 / 1.01 - 1) * 100)
    assert pib[1][1] == pytest.approx(0.0)
    assert por_hab[1][1] < 0  # o PIB parou e a população cresceu


def test_rendimento_e_produto_partem_de_100_nas_mesmas_datas() -> None:
    from sacibras.secoes import produtividade

    tri = [date(2012 + i // 4, 3 * (i % 4) + 1, 1) for i in range(8)]
    por_ocupado = [(d, 100.0 + i) for i, d in enumerate(tri[3:])]
    rendimento = [(d, 2000.0) for d in tri[:4]] + [(d, 2200.0) for d in tri[4:]]
    produto, renda = produtividade.rendimento_e_produto(por_ocupado, rendimento)
    assert [d for d, _ in produto] == [d for d, _ in renda] == tri[3:]
    assert produto[0][1] == renda[0][1] == 100.0
    assert renda[-1][1] == pytest.approx(110.0)
    assert produto[-1][1] == pytest.approx(104.0)


def test_desocupacao_mais_inflacao_soma_as_duas_no_mesmo_mes() -> None:
    from sacibras.secoes import trabalho

    g = trabalho.grafico_desocupacao_mais_inflacao(
        [(date(2026, 8, 1), 5.6), (date(2026, 9, 1), 5.4)],
        [(date(2026, 9, 1), 4.5), (date(2026, 10, 1), 4.7)],
        date(2020, 1, 1),
        "f",
    )
    assert g is not None
    assert g.series[0].pontos == [(date(2026, 9, 1), 9.9)]
    assert g.manchete.startswith("9,9 em set/2026")


def test_phillips_e_okun_um_ponto_por_ano_com_o_ultimo_em_destaque() -> None:
    from sacibras.secoes import trabalho

    taxa = {2019: 12.0, 2020: 13.5, 2021: 13.2, 2022: 9.3, 2023: 8.0, 2024: 6.9, 2025: 6.0}
    servicos = {2019: 3.5, 2020: 1.7, 2021: 4.8, 2022: 7.6, 2023: 6.2, 2024: 4.8, 2025: 6.0}
    pib = {2020: -3.3, 2021: 4.8, 2022: 3.0, 2023: 3.2, 2024: 3.4, 2025: 2.3}
    phillips = trabalho.grafico_phillips(taxa, servicos, "f")
    assert phillips is not None and phillips.dispersao is not None
    assert len(phillips.dispersao.pontos) == 7
    assert phillips.dispersao.destaque == "2025"
    assert phillips.dispersao.rotular_todos
    assert phillips.dispersao.correlacao is not None and phillips.dispersao.correlacao < 0
    okun = trabalho.grafico_okun(pib, taxa, "f")
    assert okun is not None and okun.dispersao is not None
    ponto_2020 = next(p for p in okun.dispersao.pontos if p.chave == "2020")
    assert (ponto_2020.x, ponto_2020.y) == (-3.3, 1.5)
    assert trabalho.grafico_okun({2024: 3.4}, taxa, "f") is None  # poucos anos
    assert trabalho.media_do_ano([(date(2026, m, 1), 6.0) for m in range(1, 10)]) == {}


def test_despesa_real_contra_a_faixa_do_arcabouco() -> None:
    from sacibras.secoes import fiscal

    meses = [date(2023 + i // 12, i % 12 + 1, 1) for i in range(36)]
    despesa = [(d, 100.0 if d.year == 2023 else 104.0 if d.year == 2024 else 105.0) for d in meses]
    ipca = [(d, 0.0) for d in meses]
    (g,) = fiscal.despesa_contra_a_faixa(despesa, ipca, date(2024, 1, 1))
    assert g.series[0].pontos[-1] == (date(2025, 12, 1), pytest.approx(0.96, abs=0.01))
    assert dict(g.series[0].pontos)[date(2024, 12, 1)] == pytest.approx(4.0)
    assert g.faixa is not None and g.faixa.pontos[0] == (date(2024, 12, 1), 0.6, 2.5)
    assert "dentro da faixa de 0,6 % a 2,5 %" in g.manchete
    assert fiscal.despesa_contra_a_faixa(despesa[:12], ipca, date(2024, 1, 1)) == []


def test_pib_por_habitante_usa_o_ibge_e_so_completa_depois() -> None:
    from sacibras.secoes import atividade

    oficial = [(date(2023, 1, 1), 3.2), (date(2024, 1, 1), 3.4)]
    conta = [(date(2023, 1, 1), 3.1), (date(2024, 1, 1), 3.5), (date(2025, 1, 1), 2.3)]
    junta, extra = atividade.com_a_conta_depois(oficial, conta)
    assert junta == [(date(2023, 1, 1), 3.2), (date(2024, 1, 1), 3.4), (date(2025, 1, 1), 2.3)]
    assert extra == 1
