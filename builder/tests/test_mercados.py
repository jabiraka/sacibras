"""Mercados sem rede: o Tesouro rolado e o ouro em reais, com preços de mentira."""

from datetime import date, timedelta

import pytest

from sacibras.secoes import mercados


def _dias(inicio: date, fim: date) -> list[date]:
    return [inicio + timedelta(days=i) for i in range((fim - inicio).days + 1)]


def test_tesouro_rolado_troca_de_titulo_no_vencimento() -> None:
    # Dois títulos: o de 2021 (o mais perto de 5 anos em jan/2016) sobe 1 por dia até a
    # véspera do vencimento; o de 2026 começa a ter preço em 2020 e vale 500 + 1 por dia.
    inicio, vence_1 = date(2016, 1, 4), date(2021, 1, 1)
    curto = [(d, 600.0 + i) for i, d in enumerate(_dias(inicio, vence_1 - timedelta(days=1)))]
    longo = [(d, 500.0 + i) for i, d in enumerate(_dias(date(2020, 1, 2), date(2021, 6, 30)))]
    # Um título curto demais (vence em 3 meses) nunca é comprado.
    quase = [(d, 990.0) for d in _dias(inicio, date(2016, 3, 31))]
    precos = {vence_1: curto, date(2026, 1, 1): longo, date(2016, 4, 1): quase}
    rolado = mercados.carteira_rolada(precos, inicio, 5)
    valores = dict(rolado)
    assert rolado[0] == (inicio, 100.0)
    # Até a véspera do vencimento, R$ 100 seguem o título de 2021.
    vespera = vence_1 - timedelta(days=1)
    assert valores[vespera] == pytest.approx(100 * curto[-1][1] / 600)
    # No vencimento, o dinheiro vai para o de 2026 pelo preço do dia e segue esse título.
    troca = valores[vespera]
    dia = date(2021, 1, 1)
    preco_troca = dict(longo)[dia]
    depois = date(2021, 6, 30)
    assert valores[depois] == pytest.approx(troca * dict(longo)[depois] / preco_troca)
    assert rolado[-1][0] == depois


def test_tesouro_rolado_sem_titulo_comeca_quando_houver() -> None:
    # Antes do primeiro preço, nada; um buraco no preço do título deixa o valor parado.
    precos = {date(2030, 1, 1): [(date(2025, 1, 2), 500.0), (date(2025, 1, 6), 510.0)]}
    rolado = mercados.carteira_rolada(precos, date(2025, 1, 1), 5)
    assert rolado == [(date(2025, 1, 2), 100.0), (date(2025, 1, 6), 102.0)]


def test_ouro_em_reais_no_meio_do_mes() -> None:
    ouro = [(date(2026, 9, 1), 4000.0), (date(2026, 10, 1), 4100.0)]
    dolar = [(date(2026, 9, 1), 5.0), (date(2026, 10, 1), 5.5)]
    assert mercados.ouro_em_reais(ouro, dolar) == [
        (date(2026, 9, 15), 20000.0),
        (date(2026, 10, 15), 22550.0),
    ]
    # Sem o dólar do mês, o mês fica de fora.
    assert mercados.ouro_em_reais(ouro, dolar[:1]) == [(date(2026, 9, 15), 20000.0)]
