from datetime import date

from sacibras.secoes.atividade import demanda_privada


def test_demanda_privada_pesa_pelo_tamanho_em_reais_do_ano_anterior() -> None:
    t0, t1 = date(2025, 4, 1), date(2026, 4, 1)
    consumo = [(t1, 2.0)]
    investimento = [(t1, 6.0)]
    # Um ano antes, consumo valia 3 vezes o investimento: peso 3/4 e 1/4.
    consumo_reais = [(t0, 300.0), (t1, 999.0)]
    investimento_reais = [(t0, 100.0), (t1, 1.0)]
    assert demanda_privada(consumo, investimento, consumo_reais, investimento_reais) == [(t1, 3.0)]


def test_demanda_privada_pula_trimestre_sem_base() -> None:
    t1 = date(2026, 4, 1)
    assert demanda_privada([(t1, 2.0)], [(t1, 6.0)], [(t1, 1.0)], [(t1, 1.0)]) == []
