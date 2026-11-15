"""Decomposições: IPCA por grupo, PIB por componente, dívida por fator, desocupação por fator
e o carrego do PIB. Cada uma tem de fechar, na soma, com o número de que partiu."""

from __future__ import annotations

from datetime import date

import pytest

from sacibras.modelos import decomposicoes as dc
from sacibras.tipos import Ponto


def _meses(inicio: date, valores: list[float]) -> list[Ponto]:
    saida = []
    for i, v in enumerate(valores):
        t = inicio.year * 12 + inicio.month - 1 + i
        saida.append((date(t // 12, t % 12 + 1, 1), v))
    return saida


def _trimestres(inicio: int, valores: list[float]) -> list[Ponto]:
    return [(date(inicio + i // 4, 3 * (i % 4) + 1, 1), v) for i, v in enumerate(valores)]


# ------------------------------------------------------------------ IPCA


def test_ipca_por_grupo_soma_o_acumulado_e_segue_o_peso() -> None:
    jan = date(2025, 1, 1)
    # Dois grupos: comida (30 % do índice) sobe 1 % ao mês; o resto (70 %) fica parado.
    variacao = {"comida": _meses(jan, [1.0] * 14), "resto": _meses(jan, [0.0] * 14)}
    peso = {"comida": _meses(jan, [30.0] * 14), "resto": _meses(jan, [70.0] * 14)}
    geral = _meses(jan, [0.3] * 14)
    c = dc.ipca_por_grupo(geral, variacao, peso)
    # Só há resultado com os 12 meses: dez/2025, jan e fev/2026.
    assert [d for d, _ in c["comida"]] == [date(2025, 12, 1), date(2026, 1, 1), date(2026, 2, 1)]
    acumulado = (1.003**12 - 1) * 100
    assert c["comida"][0][1] + c["resto"][0][1] == pytest.approx(acumulado)
    assert c["resto"][0][1] == pytest.approx(0.0, abs=1e-9)


def test_ipca_por_grupo_reparte_a_sobra_do_arredondamento_pelo_peso() -> None:
    jan = date(2025, 1, 1)
    variacao = {"a": _meses(jan, [0.5] * 12), "b": _meses(jan, [0.5] * 12)}
    peso = {"a": _meses(jan, [75.0] * 12), "b": _meses(jan, [25.0] * 12)}
    # O geral publicado vem arredondado para cima (0,51 no lugar de 0,50).
    c = dc.ipca_por_grupo(_meses(jan, [0.51] * 12), variacao, peso)
    a, b = c["a"][0][1], c["b"][0][1]
    assert a + b == pytest.approx((1.0051**12 - 1) * 100)
    assert a / b == pytest.approx(3.0)


# ------------------------------------------------------------------ PIB


def _pib() -> tuple[dict[str, list[Ponto]], dict[str, list[Ponto]]]:
    # Um ano antes: consumo 80, exportações 30, importações 10 → PIB 100, a preços correntes.
    valor = {
        "pib": _trimestres(2025, [100.0] * 8),
        "consumo": _trimestres(2025, [80.0] * 8),
        "exp": _trimestres(2025, [30.0] * 8),
        "imp": _trimestres(2025, [10.0] * 8),
    }
    # Em volume: consumo +5 %, exportações +10 %, importações +20 %, PIB +4,5 %.
    volume = {
        "pib": _trimestres(2025, [100.0] * 4 + [104.5] * 4),
        "consumo": _trimestres(2025, [100.0] * 4 + [105.0] * 4),
        "exp": _trimestres(2025, [100.0] * 4 + [110.0] * 4),
        "imp": _trimestres(2025, [100.0] * 4 + [120.0] * 4),
    }
    return volume, valor


def test_pib_por_componente_e_a_fatia_vezes_o_crescimento_com_importacao_negativa() -> None:
    volume, valor = _pib()
    c = dc.pib_por_componente(volume, valor, "pib", {"consumo": 1, "exp": 1, "imp": -1}, True)
    t = date(2026, 4, 1)
    assert dict(c["consumo"])[t] == pytest.approx(4.0)  # 80 % × 5 %
    assert dict(c["exp"])[t] == pytest.approx(3.0)  # 30 % × 10 %
    assert dict(c["imp"])[t] == pytest.approx(-2.0)  # −10 % × 20 %
    # O PIB cresceu 4,5: o que falta (estoques e encadeamento) fica à parte.
    assert dict(c[dc.RESTO])[t] == pytest.approx(-0.5)
    assert len(c["consumo"]) == 4  # só os trimestres com o de um ano antes


def test_pib_por_componente_sem_resto_a_parte_reparte_pela_fatia() -> None:
    volume, valor = _pib()
    c = dc.pib_por_componente(volume, valor, "pib", {"consumo": 1, "exp": 1, "imp": -1}, False)
    t = date(2026, 1, 1)
    assert dc.RESTO not in c
    assert sum(dict(c[k])[t] for k in c) == pytest.approx(4.5)
    # A sobra de −0,5 vai na proporção de 80 : 30 : 10.
    assert dict(c["consumo"])[t] == pytest.approx(4.0 - 0.5 * 80 / 120)


# ------------------------------------------------------------------ dívida


def test_divida_por_fator_fecha_com_a_variacao_e_separa_juros_pib_e_primario() -> None:
    jan = date(2024, 1, 1)
    n = 25
    # A dívida fica em 80 % do PIB; o PIB em reais cresce 10 % em 12 meses; juro de 12 %.
    pib = _meses(jan, [1000.0 * 1.1 ** (i / 12) for i in range(n)])
    divida = _meses(jan, [80.0] * n)
    taxa = _meses(jan, [12.0] * n)
    primario = _meses(jan, [1.0] * n)
    fatores = dc.divida_por_fator(divida, pib, taxa, primario)
    # Um resultado por mês, a partir do primeiro que tem os 12 anteriores.
    assert (fatores[0].quando, fatores[-1].quando, len(fatores)) == (
        date(2025, 1, 1),
        date(2026, 1, 1),
        13,
    )
    f = fatores[-1]
    assert f.variacao == pytest.approx(0.0)
    # O PIB 10 % maior tira 80 × 0,1 ÷ 1,1 pontos.
    assert f.pib == pytest.approx(-80 * 0.1 / 1.1)
    # Juros: 12 % sobre a dívida média dos 12 meses, medida contra o PIB de agora.
    media = sum(0.8 * v for _, v in pib[12:24]) / 12
    assert f.juros == pytest.approx(12 * media / pib[24][1])
    assert f.primario == 1.0
    assert f.juros + f.pib + f.primario + f.resto == pytest.approx(f.variacao)


def test_divida_por_fator_pula_mes_sem_a_janela_inteira() -> None:
    jan = date(2025, 1, 1)
    curto = _meses(jan, [80.0] * 12)
    assert dc.divida_por_fator(curto, _meses(jan, [1000.0] * 12), curto, curto) == []


# ------------------------------------------------------------------ desocupação


def test_desocupacao_cai_por_mais_emprego_ou_por_menos_procura() -> None:
    jan = date(2025, 1, 1)
    populacao = _meses(jan, [1000.0] * 13)
    # Mais emprego: 540 → 560 ocupados, com a mesma força de trabalho (600).
    ocupados = _meses(jan, [540.0] * 12 + [560.0])
    desocupados = _meses(jan, [60.0] * 12 + [40.0])
    mudanca, ocupacao, participacao = dc.desocupacao_por_fator(ocupados, desocupados, populacao)
    assert mudanca == [(date(2026, 1, 1), pytest.approx(40 / 6 - 10))]
    assert ocupacao[0][1] == pytest.approx(mudanca[0][1]) and participacao[0][1] == pytest.approx(0)
    # Menos procura: os mesmos 540 ocupados, e 20 desocupados desistem de procurar.
    desistem = _meses(jan, [60.0] * 12 + [40.0])
    mudanca, ocupacao, participacao = dc.desocupacao_por_fator(
        _meses(jan, [540.0] * 13), desistem, populacao
    )
    assert mudanca[0][1] < 0 and ocupacao[0][1] == pytest.approx(0)
    assert participacao[0][1] == pytest.approx(mudanca[0][1])


def test_desocupacao_as_duas_partes_somam_a_mudanca() -> None:
    jan = date(2025, 1, 1)
    ocupados = _meses(jan, [540.0] * 12 + [575.0])
    desocupados = _meses(jan, [60.0] * 12 + [52.0])
    populacao = _meses(jan, [1000.0] * 12 + [1015.0])
    mudanca, ocupacao, participacao = dc.desocupacao_por_fator(ocupados, desocupados, populacao)
    assert ocupacao[0][1] + participacao[0][1] == pytest.approx(mudanca[0][1])
    assert ocupacao[0][1] < 0 < participacao[0][1]


# ------------------------------------------------------------------ carrego


def test_carrego_no_meio_do_ano_repete_o_ultimo_trimestre() -> None:
    indice = _trimestres(2025, [100.0, 100.0, 100.0, 100.0, 102.0, 103.0])
    c = dc.carrego(indice)
    assert c is not None and (c.ano, c.trimestres, c.ultimo) == (2026, 2, date(2026, 4, 1))
    assert c.valor == pytest.approx((102 + 103 * 3) / 400 * 100 - 100)


def test_carrego_depois_do_quarto_trimestre_vale_para_o_ano_seguinte() -> None:
    c = dc.carrego(_trimestres(2025, [100.0, 101.0, 102.0, 103.0]))
    assert c is not None and (c.ano, c.trimestres) == (2026, 0)
    assert c.valor == pytest.approx(103 / 101.5 * 100 - 100)
    assert dc.carrego(_trimestres(2025, [100.0, 101.0])) is None and dc.carrego([]) is None


# ------------------------------------------------------------------ nas seções


def test_grafico_do_ipca_empilha_cinco_grupos_os_demais_e_a_linha_do_total() -> None:
    from sacibras.secoes import inflacao

    meses = [date(2026, 9, 1), date(2026, 10, 1)]
    contrib = {g: [(m, 0.5) for m in meses] for g in inflacao.GRUPOS_IPCA}
    g = inflacao.grafico_contribuicoes(contrib, date(2020, 1, 1))
    assert g is not None and g.tipo == "empilhado" and g.total == "total"
    assert [s.id for s in g.series][-2:] == ["demais", "total"] and len(g.series) == 7
    por_id = {s.id: s.pontos[-1][1] for s in g.series}
    assert por_id["demais"] == 2.0 and por_id["total"] == 4.5  # 4 e 9 grupos de 0,5
    assert g.linhas[0].rotulo.startswith("meta")
    # Falta um grupo: não há gráfico (a soma não daria o IPCA).
    del contrib["7170"]
    assert inflacao.grafico_contribuicoes(contrib, date(2020, 1, 1)) is None


def test_grafico_da_desocupacao_traz_as_duas_partes_e_a_mudanca() -> None:
    from sacibras.secoes import trabalho

    jan = date(2025, 1, 1)
    g = trabalho.grafico_fatores_da_desocupacao(
        _meses(jan, [540.0] * 12 + [560.0]),
        _meses(jan, [60.0] * 12 + [40.0]),
        _meses(jan, [1000.0] * 13),
        jan,
    )
    assert g is not None and [s.id for s in g.series] == ["ocupacao", "participacao", "total"]
    assert g.total == "total" and g.series[2].pontos[-1][1] == pytest.approx(-3.33)
    assert trabalho.grafico_fatores_da_desocupacao([], [], [], jan) is None


def test_cartao_do_carrego_diz_o_trimestre_e_poe_o_focus_ao_lado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sacibras.secoes import atividade

    indice = _trimestres(2025, [100.0, 100.0, 100.0, 100.0, 102.0, 103.0])
    monkeypatch.setattr(atividade.ibge_sidra, "serie", lambda *a, **k: indice)
    monkeypatch.setattr(atividade.bcb_focus, "mediana_anual_hoje", lambda *a, **k: {2026: 2.1})
    c = atividade.cartao_carrego()
    assert c is not None and c.id == "pib-carrego" and c.rotulo == "Carrego do PIB para 2026"
    assert c.valor == pytest.approx(2.75) and c.procedencia == "calculado"
    assert c.detalhe == "se o PIB parar no nível do 2º tri; Focus: 2,1 %" and len(c.detalhe) <= 60


def test_contribuicoes_do_pib_saem_pela_demanda_e_pela_oferta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sacibras.secoes import atividade

    codigos = ["90707", *atividade.DEMANDA, *atividade.OFERTA]

    def series(tabela: int, variavel: int, **k: object) -> dict[str, list[Ponto]]:
        if tabela == 1846:
            return {c: _trimestres(2025, [100.0] * 8) for c in codigos}
        return {c: _trimestres(2025, [100.0] * 4 + [102.0] * 4) for c in codigos}

    monkeypatch.setattr(atividade.ibge_sidra, "series", series)
    oferta, demanda = atividade.contribuicoes_do_pib(date(2020, 1, 1))  # a oferta à esquerda
    assert demanda.id == "pib-contribuicoes-demanda" and oferta.id == "pib-contribuicoes-oferta"
    assert [s.id for s in demanda.series][-2:] == ["resto", "total"]
    assert [s.id for s in oferta.series] == ["agro", "industria", "servicos", "impostos", "total"]
    ultimo = {s.id: s.pontos[-1][1] for s in demanda.series}
    # Tudo cresce 2 % com fatia de 100 %: quatro somam, as importações tiram, o resto fecha.
    assert ultimo["importacoes"] == -2.0 and ultimo["total"] == 2.0 and ultimo["resto"] == -4.0
