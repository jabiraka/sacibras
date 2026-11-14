"""As contas da aba de riscos, com números que se conferem à mão."""

from __future__ import annotations

import itertools
from datetime import date, timedelta

import pytest

from sacibras.modelos import divida, risco


def test_primario_que_estabiliza_mantem_a_divida_parada() -> None:
    # Dívida de 80 % do PIB, juro de 10 %, PIB nominal crescendo 6 %.
    p = risco.primario_que_estabiliza(80.0, 10.0, 6.0)
    assert p == pytest.approx(80 * 0.04 / 1.06)
    # Posta na conta da dívida (crescimento real 6 %, inflação 0), a dívida não sai do lugar.
    assert divida.trajetoria(80.0, [10.0], [6.0], [0.0], [p])[0] == pytest.approx(80.0)


def test_primario_que_estabiliza_e_negativo_quando_o_pib_cresce_mais_que_o_juro() -> None:
    assert risco.primario_que_estabiliza(80.0, 5.0, 8.0) < 0


def test_serie_do_primario_so_onde_ha_as_tres() -> None:
    d1, d2 = date(2026, 1, 1), date(2026, 2, 1)
    saida = risco.serie_do_primario_que_estabiliza(
        [(d1, 80.0), (d2, 81.0)], [(d1, 10.0)], [(d1, 6.0), (d2, 6.0)]
    )
    assert [d for d, _ in saida] == [d1]


def test_choques_da_historia_somam_zero() -> None:
    anos = {2020: (8.0, -3.0, 4.5, -9.0), 2021: (6.0, 5.0, 10.0, 0.7), 2022: (10.0, 3.0, 5.8, 1.3)}
    choques = risco.choques_da_historia(anos)
    assert len(choques) == 3
    for k in range(4):
        assert sum(c[k] for c in choques) == pytest.approx(0.0)
    assert choques[0][3] == pytest.approx(-9.0 - (-9.0 + 0.7 + 1.3) / 3)


def test_leque_sem_choque_e_a_linha_de_base() -> None:
    base = divida.trajetoria(80.0, [10.0] * 5, [2.0] * 5, [4.0] * 5, [0.0] * 5)
    leque = risco.leque(80.0, [10.0] * 5, [2.0] * 5, [4.0] * 5, [0.0] * 5, [(0, 0, 0, 0)])
    assert leque.mediana == pytest.approx(base)
    assert leque.p10 == pytest.approx(base)
    assert leque.chance_de_subir == 100.0  # juro acima do crescimento e primário zero: sobe


def test_leque_abre_com_o_prazo_e_repete_com_a_mesma_semente() -> None:
    choques = [(1.0, -2.0, 0.5, -1.5), (-1.0, 2.0, -0.5, 1.5), (0.0, 0.0, 0.0, 0.0)]
    args = (80.0, [9.0] * 5, [2.0] * 5, [4.0] * 5, [0.5] * 5, choques)
    a = risco.leque(*args, sorteios=500)
    b = risco.leque(*args, sorteios=500)
    assert a == b
    larguras = [alto - baixo for baixo, alto in zip(a.p10, a.p90, strict=True)]
    assert larguras[-1] > larguras[0] > 0
    for i in range(5):
        assert a.p10[i] <= a.p25[i] <= a.mediana[i] <= a.p75[i] <= a.p90[i]
    assert 0 <= a.chance_de_subir <= 100


def test_posicao_na_historia_nos_dois_sentidos() -> None:
    pontos = [(date(2020, m, 1), float(m)) for m in range(1, 11)]  # 1 a 10, hoje = 10
    alto = risco.posicao_na_historia(pontos, "alto")
    assert alto.pior_que == pytest.approx(90.0)  # nove dos dez meses foram melhores
    assert (alto.minimo, alto.maximo, alto.mediana) == (1.0, 10.0, 5.5)
    assert alto.desde == date(2020, 1, 1)
    assert risco.posicao_na_historia(pontos, "baixo").pior_que == 0.0


def test_volatilidade_de_preco_parado_e_zero_e_de_preco_que_oscila_nao() -> None:
    dia = date(2026, 1, 1)
    parado = [(dia + timedelta(days=i), 5.0) for i in range(30)]
    assert all(v == 0 for _, v in risco.volatilidade(parado))
    oscila = [(dia + timedelta(days=i), 5.0 * (1.01 if i % 2 else 1.0)) for i in range(30)]
    vol = risco.volatilidade(oscila, janela=21)
    assert len(vol) == 30 - 1 - 21 + 1
    # Retornos de ±1 % ao dia: desvio de ~1 % × raiz de 252 ≈ 16 % ao ano.
    assert vol[-1][1] == pytest.approx(16.2, abs=0.6)


def test_queda_desde_o_pico() -> None:
    dia = date(2026, 1, 1)
    niveis = [100.0, 120.0, 90.0, 132.0]
    queda = risco.queda_desde_o_pico([(dia + timedelta(days=i), v) for i, v in enumerate(niveis)])
    assert [round(v, 1) for _, v in queda] == [0.0, 0.0, -25.0, 0.0]


def test_maior_alta_e_maior_queda_respeitam_a_ordem_e_a_janela() -> None:
    dia = date(2002, 4, 1)
    niveis = [3.0, 2.0, 4.0, 3.0, 10.0]
    pontos = [(dia + timedelta(days=i), v) for i, v in enumerate(niveis)]
    fim = dia + timedelta(days=3)  # o 10,0 fica fora da janela
    assert risco.maior_alta(pontos, dia, fim) == pytest.approx(100.0)  # de 2 para 4
    assert risco.maior_queda(pontos, dia, fim) == pytest.approx(-100 / 3)  # de 3 para 2
    assert risco.maior_alta(pontos, date(1990, 1, 1), date(1990, 12, 31)) is None
    assert risco.maior_mudanca(pontos, dia, fim) == pytest.approx(-1.0)


def test_choques_do_episodio_contra_os_dois_anos_anteriores() -> None:
    anos = {
        2018: (8.0, 1.8, 3.7, -1.5),
        2019: (7.0, 1.2, 4.3, -0.9),
        2020: (5.0, -3.3, 4.5, -9.2),
    }
    choques = risco.choques_do_episodio(anos, [2020])
    assert choques is not None
    assert choques[0] == pytest.approx((5.0 - 7.5, -3.3 - 1.5, 4.5 - 4.0, -9.2 + 1.2))
    assert risco.choques_do_episodio(anos, [2019]) is None  # falta 2017
    assert risco.choques_do_episodio(anos, []) is None


def test_repetir_episodio_piora_a_divida_e_depois_segue_a_base() -> None:
    args = (80.0, [9.0] * 4, [2.0] * 4, [4.0] * 4, [0.0] * 4)
    base = divida.trajetoria(*args)
    choque = [(0.0, -5.0, 0.0, -8.0)]
    estresse = risco.repetir_episodio(*args, choque)
    assert estresse[0] > base[0] + 8  # o primário pior entra inteiro; a recessão soma
    # Depois do choque a diferença não some: a dívida maior segue rendendo juro.
    assert estresse[-1] - base[-1] >= estresse[0] - base[0]


# ------------------------------------------------------------------ a seção e as fontes


def test_reservatorios_do_ons_somam_os_quatro_subsistemas() -> None:
    from sacibras.fontes import ons

    csv = (
        "id_subsistema;nom_subsistema;ear_data;ear_max_subsistema;"
        "ear_verif_subsistema_mwmes;ear_verif_subsistema_percentual\n"
        "NE;NORDESTE;2026-01-01;50;25;50\n"
        "N ;NORTE;2026-01-01;10;10;100\n"
        "SE;SUDESTE;2026-01-01;200;50;25\n"
        "S ;SUL;2026-01-01;40;15;37.5\n"
        "NE;NORDESTE;2026-01-02;50;25;50\n"  # dia incompleto: fica de fora
    )
    pontos = ons.ler_csv(csv)
    assert pontos == [(date(2026, 1, 1), pytest.approx(100 / 300 * 100))]
    assert ons.media_mensal([(date(2026, 1, 1), 40.0), (date(2026, 1, 15), 50.0)]) == [
        (date(2026, 1, 1), 45.0)
    ]


def test_reservas_contra_a_divida_de_curto_prazo_e_as_importacoes() -> None:
    from sacibras.secoes import riscos

    # A trimestral vem datada no 1º mês; a posição é a do fim do trimestre (junho).
    reservas = [(date(2026, 4, 1), 300.0), (date(2026, 6, 1), 360.0)]
    cobertura = riscos.cobertura_das_reservas(reservas, [(date(2026, 4, 1), 120.0)])
    assert cobertura == [(date(2026, 4, 1), pytest.approx(300.0))]
    assert riscos.cobertura_das_reservas(reservas, [(date(2026, 7, 1), 120.0)]) == []

    importacoes = [(date(2025, m, 1), 20.0) for m in range(1, 13)]
    meses = riscos.meses_de_importacao([(date(2025, 12, 1), 360.0)], importacoes)
    assert meses == [(date(2025, 12, 1), pytest.approx(18.0))]


def test_alerta_poe_o_lado_ruim_conforme_o_indicador() -> None:
    from sacibras.secoes import riscos

    pontos = [(date(2020, m, 1), float(m)) for m in range(1, 11)]
    alto = riscos.alerta(
        "x", "Grupo", "Nome", pontos, pior_quando="alto", unidade="%", periodicidade="M", fonte="f"
    )
    assert alto.pior_que == 90.0 and alto.pior_que >= riscos.ACESO
    assert (alto.valor, alto.minimo, alto.maximo, alto.desde) == (10.0, 1.0, 10.0, date(2020, 1, 1))
    baixo = riscos.alerta(
        "x", "Grupo", "Nome", pontos, pior_quando="baixo", unidade="%", periodicidade="M", fonte="f"
    )
    assert baixo.pior_que == 0.0


def test_semanal_fica_com_o_ultimo_ponto_de_cada_semana() -> None:
    from sacibras.secoes import riscos

    segunda = date(2026, 11, 9)
    pontos = [(segunda + timedelta(days=i), float(i)) for i in range(7)]  # seg a dom
    pontos.append((segunda + timedelta(days=7), 7.0))  # a segunda seguinte
    assert riscos.semanal(pontos) == [(segunda + timedelta(days=6), 6.0), pontos[-1]]


def test_notas_de_credito_em_ordem_e_na_escala() -> None:
    from sacibras import relatorios
    from sacibras.secoes import riscos

    for agencia, historia in relatorios.NOTAS.items():
        datas = [d for d, _ in historia]
        assert datas == sorted(datas), agencia
        assert all(nota in relatorios.DEGRAU for _, nota in historia), agencia
        # Cada linha é uma mudança de nota: nunca a mesma duas vezes seguidas.
        assert all(a[1] != b[1] for a, b in itertools.pairwise(historia)), agencia
        assert agencia in relatorios.PERSPECTIVA
    # O grau de investimento (2008 a 2015–16) aparece nas três.
    for agencia in relatorios.NOTAS:
        degraus = riscos.degraus(agencia, date(2026, 11, 14))
        assert max(v for _, v in degraus) == 1.0
        assert degraus[-1][0] == date(2026, 11, 14)
    assert riscos.saldo(-0.52) == "déficit primário de 0,52 %"
    assert riscos.saldo(1.2) == "superávit primário de 1,20 %"
