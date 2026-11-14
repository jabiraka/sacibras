"""A conta do simulador da reforma do consumo e os números de lei que ela usa."""

from datetime import UTC, datetime

import pytest

from sacibras import leis, organizacao, relatorios
from sacibras.modelos import reforma
from sacibras.schema import Secao
from sacibras.secoes import impostos
from sacibras.secoes.base import Contexto


def test_imposto_por_fora_com_desconto_e_aliquota_zero() -> None:
    cheia = reforma.compra(100.0, cbs=9.2, ibs=18.7)
    assert cheia.imposto == pytest.approx(27.9) and cheia.devolucao == 0.0
    # 60 % de desconto: paga 40 % da alíquota cheia.
    com_desconto = reforma.compra(250.0, cbs=11.2, ibs=0.1, paga=40.0)
    assert (com_desconto.cbs, com_desconto.ibs) == pytest.approx((11.2, 0.1))
    assert reforma.compra(80.0, cbs=9.2, ibs=18.7, paga=0.0).imposto == 0.0


def test_devolucao_a_baixa_renda_pela_lei() -> None:
    # Conta de luz: volta 100 % da CBS e 20 % do IBS (LC 214, art. 118, I).
    luz = reforma.compra(
        250.0,
        cbs=9.2,
        ibs=18.7,
        volta_cbs=leis.DEVOLUCAO_CBS_CONTAS_DE_CASA,
        volta_ibs=leis.DEVOLUCAO_IBS_CONTAS_DE_CASA,
    )
    assert luz.devolucao == pytest.approx(250 * 0.092 + 250 * 0.187 * 0.2)
    assert luz.liquido == pytest.approx(250 * 0.187 * 0.8)
    # Demais compras: 20 % dos dois (art. 118, II).
    comum = reforma.compra(
        100.0, cbs=10.0, ibs=20.0, volta_cbs=leis.DEVOLUCAO_GERAL, volta_ibs=leis.DEVOLUCAO_GERAL
    )
    assert comum.devolucao == pytest.approx(6.0)


def test_repartir_e_a_parte_do_preco_que_e_imposto() -> None:
    cbs, ibs = reforma.repartir(27.91, relatorios.IBS_COMITE_GESTOR / 27.91)
    assert (cbs, ibs) == pytest.approx((9.21, 18.7))
    # O Comitê Gestor e a Agência Senado dão a mesma CBS esperada antes do cálculo do TCU.
    assert cbs == pytest.approx(relatorios.CBS_ESTIMATIVA_ANTERIOR)
    assert reforma.no_preco(25.0) == pytest.approx(20.0)


def test_calendario_da_emenda() -> None:
    assert pytest.approx(1.0) == leis.IBS_TESTE_2026 + leis.CBS_TESTE_2026
    continua = leis.ICMS_ISS_QUE_CONTINUA
    assert [continua[a] for a in leis.REFORMA_ANOS] == [100, 100, 100, 90, 80, 70, 60, 0]
    assert leis.PIS_COFINS_QUE_CONTINUA[2026] == 100 and leis.PIS_COFINS_QUE_CONTINUA[2027] == 0


def test_a_parte_da_reforma_sai_da_lei_e_das_contas_oficiais() -> None:
    cartoes, tabelas, simulador = impostos._simulador_da_reforma(Contexto())
    assert all(len(c.detalhe) <= 60 for c in cartoes)
    por_id = {c.id: c for c in cartoes}
    assert por_id["reforma-cbs-2027"].valor == pytest.approx(11.2)  # 11,3 do TCU menos 0,1
    # A faixa do simulador: do teto da lei à soma das contas mais recentes.
    assert simulador.aliquota_minima == leis.TETO_IBS_CBS == 26.5
    assert simulador.aliquota_maxima == pytest.approx(18.7 + 11.3)
    assert simulador.aliquota_minima < simulador.aliquota < simulador.aliquota_maxima
    pagam = {t.id: t.paga for t in simulador.tipos}
    assert pagam == {"cheia": 100, "contas": 100, "menos-60": 40, "menos-30": 70, "cesta": 0}
    # Rótulos curtos: a lista suspensa do celular corta o que passar disso.
    assert all(len(t.rotulo) <= 34 for t in simulador.tipos)
    assert all(len(e.rotulo) <= 34 for e in simulador.etapas)
    de_2027 = next(e for e in simulador.etapas if e.id == "2027")
    assert (de_2027.cbs, de_2027.ibs, de_2027.devolve_ibs) == (11.2, 0.1, False)
    # A linha do tempo em palavras (`_reforma`) mora na mesma parte que o simulador.
    _, _, linha_do_tempo, _ = impostos._reforma(Contexto())
    tabelas = [*tabelas, *linha_do_tempo]
    assert {t.id for t in tabelas} == {
        "reforma-linha-do-tempo",
        "reforma-aliquota",
        "reforma-descontos",
    }

    secao = Secao(
        id="impostos",
        titulo="Impostos",
        cartoes=cartoes,
        tabelas=tabelas,
        simulador_reforma=simulador,
        gerado_em=datetime(2026, 11, 14, tzinfo=UTC),
    )
    assert organizacao.aplicar(secao) == []
    (parte,) = secao.subcategorias
    assert (parte.id, parte.extras) == ("reforma", ["simulador-reforma"])
