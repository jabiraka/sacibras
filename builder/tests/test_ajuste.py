"""As contas de pressão e de ajuste fiscal do Laboratório, sem rede."""

import math
from datetime import date, timedelta

import pytest

from sacibras.modelos import ajuste


def _dias(n: int) -> list[date]:
    return [date(2020, 1, 1) + timedelta(days=i) for i in range(n)]


def test_o_dolar_repartido_fecha_com_o_total_e_acha_o_beta() -> None:
    n = 400
    fora = [((i * 37) % 11 - 5) / 10 for i in range(n)]
    daqui = [0.3 if 300 <= i < 320 else 0.0 for i in range(n)]  # um choque só do Brasil
    brasil = [1.5 * f + d for f, d in zip(fora, daqui, strict=True)]
    partes = ajuste.repartir_dolar(_dias(n), brasil, fora, janela=50, janela_beta=200)
    assert partes[0].dia == _dias(n)[199]  # o primeiro dia com a janela do β cheia
    antes = next(p for p in partes if p.dia == _dias(n)[290])
    assert antes.beta == pytest.approx(1.5) and antes.do_brasil == pytest.approx(0.0, abs=1e-9)
    ultimo = partes[-1]
    assert ultimo.total == pytest.approx(sum(brasil[-50:]))
    assert ultimo.de_fora + ultimo.do_brasil == pytest.approx(ultimo.total)
    # O choque de 20 dias × 0,3 fica quase todo na parte do Brasil (ele mexe um pouco no β).
    no_choque = next(p for p in partes if p.dia == _dias(n)[340])
    assert no_choque.do_brasil == pytest.approx(6.0, abs=0.5)


def test_variacoes_e_composta() -> None:
    a, b, c = date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 5)
    v = ajuste.variacoes({a: 5.0, b: 5.5, c: 5.0}, [a, b, c])
    assert v == pytest.approx([100 * math.log(1.1), -100 * math.log(1.1)])
    assert ajuste.composta(v[0]) == pytest.approx(10.0)


def test_faixa_do_brasil_contem_o_ponto_e_some_sem_movimento_de_fora() -> None:
    n = 600
    fora = [((i * 37) % 11 - 5) / 10 for i in range(n)]
    ruido = [((i * 53) % 7 - 3) / 20 for i in range(n)]
    brasil = [1.5 * f + r for f, r in zip(fora, ruido, strict=True)]
    lo, hi = ajuste.faixa_do_brasil(brasil, fora, janela=100, janelas_beta=(200, 400))
    beta, _, _ = ajuste.beta_com_intervalo(brasil, fora, 400)
    ponto = sum(brasil[-100:]) - beta * sum(fora[-100:])
    assert lo <= ponto <= hi


def test_maiores_altas_uma_por_episodio() -> None:
    totais = [0, 1, 9, 10, 8, 0, 0, 7, 0, 0, 3]
    partes = [
        ajuste.Reparticao(dia=d, total=float(t), de_fora=0.0, beta=1.0)
        for d, t in zip(_dias(len(totais)), totais, strict=True)
    ]
    altas = ajuste.maiores_altas(partes, quantas=3, afastamento=3)
    assert [p.total for p in altas] == [3.0, 7.0, 10.0]  # 9 e 8 são o mesmo episódio do 10


def test_divida_com_o_mesmo_primario_e_a_oficial() -> None:
    divida = {2013: 50.0, 2014: 56.0, 2015: 65.0}
    juro = {2014: 10.0, 2015: 12.0}
    g = {2014: 6.0, 2015: 4.0}
    primario = {2014: -1.0, 2015: -2.0}
    igual = ajuste.divida_com_outro_primario(divida, juro, g, primario, {}, 2014)
    assert igual == {2014: 56.0, 2015: 65.0}


def test_divida_com_outro_primario_rende_o_juro_do_ano() -> None:
    divida = {2013: 50.0, 2014: 56.0, 2015: 65.0, 2016: 70.0}
    juro = {2014: 10.0, 2015: 12.0, 2016: 12.0}
    g = {2014: 6.0, 2015: 4.0, 2016: 4.0}
    primario = {2014: -1.0, 2015: -2.0, 2016: -3.0}
    outra = ajuste.divida_com_outro_primario(
        divida, juro, g, primario, {2014: 0.0, 2015: 0.0}, 2014
    )
    assert outra[2014] == pytest.approx(55.0)
    # O ponto de 2014 rende 12 % contra 4 % de PIB, e somem os 2 pontos de 2015.
    assert outra[2015] == pytest.approx(65.0 - 1.0 * 1.12 / 1.04 - 2.0)
    # 2016 não está em `outro`: vale o primário que houve, e a diferença só rende.
    assert outra[2016] == pytest.approx(70.0 - (1.0 * 1.12 / 1.04 + 2.0) * 1.12 / 1.04)


def test_erro_por_horizonte() -> None:
    safras = {a: {a + 1: 2.0, a + 2: 3.0} for a in range(2000, 2010)}
    realizado = {a: 1.0 for a in range(2001, 2011)}
    realizado[2005] = 9.0
    um = ajuste.erro_por_horizonte(safras, realizado, 1)
    assert um is not None and um.anos == list(range(2001, 2011))
    assert um.media == pytest.approx((9 * 1.0 - 7.0) / 10) and um.otimistas == 9
    assert um.de < um.media < um.ate
    sem = ajuste.erro_por_horizonte(safras, realizado, 1, sem=[2005])
    assert sem is not None and sem.media == pytest.approx(1.0) and len(sem.anos) == 9
    dois = ajuste.erro_por_horizonte(safras, realizado, 2)
    assert dois is not None and dois.anos[0] == 2002  # 2011 não tem realizado
    assert ajuste.erro_por_horizonte({2000: {2001: 1.0}}, realizado, 1) is None
    assert ajuste.previsto_antes(safras, 2)[2002] == 3.0


def test_corridas_de_melhora_e_de_piora() -> None:
    primario = {1997: 0.2, 1998: 0.8, 1999: 1.9, 2000: 1.8, 2001: 1.7, 2002: 2.1, 2003: 0.9}
    primario |= {2010: 0.0, 2011: 5.0}  # depois de um buraco na série, começa de novo
    assert ajuste.corridas(primario) == [(1997, 1999), (2002, 2003), (2010, 2011)]
    assert ajuste.corridas(primario, minimo=0.1) == [
        (1997, 1999),
        (1999, 2001),
        (2001, 2002),
        (2002, 2003),
        (2010, 2011),
    ]


def test_meta_da_ldo_em_pct_do_pib() -> None:
    from sacibras import leis
    from sacibras.secoes.laboratorio_ajuste import janela_do_anuncio, meta_em_pct

    assert meta_em_pct(leis.MetaDaLDO("x", pct_do_pib=2.45), 1000.0) == 2.45
    assert meta_em_pct(leis.MetaDaLDO("x", reais_bi=-139.0), 6950.0) == pytest.approx(-2.0)
    assert meta_em_pct(leis.MetaDaLDO("x", reais_bi=10.0), None) is None
    assert sorted(leis.METAS_DAS_LDOS) == list(range(2002, 2027))
    # Anúncio de manhã numa terça: da segunda à quarta; à noite: da terça à quinta.
    assert janela_do_anuncio(date(2016, 6, 14), False) == (date(2016, 6, 13), date(2016, 6, 15))
    assert janela_do_anuncio(date(2016, 6, 14), True) == (date(2016, 6, 14), date(2016, 6, 16))
    # Sexta à noite: o primeiro pregão que vê é o de segunda.
    assert janela_do_anuncio(date(2016, 6, 17), True) == (date(2016, 6, 17), date(2016, 6, 21))


def _governo() -> tuple[float, dict[int, ajuste.AnoDaDivida], dict[int, float]]:
    from sacibras import relatorios

    proj = relatorios.PLDO_2027
    partida = proj[2026].divida
    governo = {
        a: ajuste.AnoDaDivida(
            x.implicita, ajuste.nominal(x.pib, x.deflator), x.primario + x.regionais
        )
        for a, x in proj.items()
        if a > 2026
    }
    return partida, governo, {a: proj[a].divida for a in governo}


def test_a_conta_da_divida_chega_a_do_governo_com_sobra_pequena_e_estavel() -> None:
    partida, governo, divida = _governo()
    sobra = ajuste.sobras(partida, governo, divida)
    assert all(0.3 < v < 1.0 for v in sobra.values())
    refeita = ajuste.caminho(partida, governo, sobra)
    assert all(abs(refeita[a] - divida[a]) < 1e-9 for a in divida)


def test_a_conta_repete_a_sensibilidade_do_tesouro() -> None:
    from sacibras import relatorios
    from sacibras.secoes.laboratorio_ajuste import _conferencia_com_o_tesouro

    partida, governo, divida = _governo()
    sobra = ajuste.sobras(partida, governo, divida)
    assert _conferencia_com_o_tesouro(partida, governo, sobra) < 0.4
    assert set(relatorios.PLDO_2027_SENSIBILIDADE) == {"pib", "primario"}


def test_juro_que_fecha_e_reparticao_que_soma() -> None:
    partida, governo, divida = _governo()
    sobra = ajuste.sobras(partida, governo, divida)
    outro = {
        a: ajuste.AnoDaDivida(x.juro + 0.5, x.nominal - 0.8, x.primario - 1.0)
        for a, x in governo.items()
        if a <= 2035
    }
    alvo = ajuste.caminho(partida, outro, sobra)
    x = outro[2027]
    juro = ajuste.juro_que_fecha(partida, alvo[2027], x.nominal, x.primario, sobra[2027])
    assert abs(juro - x.juro) < 1e-9
    partes = ajuste.repartir_a_diferenca(partida, governo, outro, sobra, 2035)
    assert abs(sum(partes.values()) - (alvo[2035] - divida[2035])) < 1e-9
    assert all(v > 0 for v in partes.values())
    assert ajuste.trocar(governo, outro, ()) == {a: governo[a] for a in outro}
