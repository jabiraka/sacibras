"""Os ciclos da Selic, a conta do efeito e os números do BC que ela usa."""

from datetime import UTC, date, datetime, timedelta

import pytest

from sacibras import organizacao, relatorios
from sacibras.modelos import selic
from sacibras.schema import Secao, SimuladorSelic
from sacibras.tipos import Ponto


def _diaria(degraus: list[tuple[date, float]], fim: date) -> list[Ponto]:
    """Uma série diária a partir das datas em que o valor muda."""
    pontos: list[Ponto] = []
    for (dia, valor), proximo in zip(degraus, [*degraus[1:], (fim, 0.0)], strict=True):
        while dia < proximo[0]:
            pontos.append((dia, valor))
            dia += timedelta(days=1)
    return pontos


META = _diaria(
    [
        (date(2016, 1, 1), 14.25),
        (date(2016, 10, 20), 14.0),  # começa a cortar
        (date(2017, 5, 31), 10.25),
        (date(2017, 12, 7), 7.0),  # seis meses de pausa não encerram o ciclo
        (date(2018, 3, 22), 6.5),  # último corte, e mais de um ano parada
        (date(2019, 8, 1), 6.0),  # corte de novo: outro ciclo
        (date(2020, 2, 6), 4.25),
        (date(2020, 8, 6), 2.0),
        (date(2021, 3, 18), 2.75),  # vira: ciclo de alta
        (date(2021, 5, 6), 3.5),
    ],
    date(2021, 6, 1),
)


def test_ciclos_viram_no_sentido_e_depois_de_um_ano_parado() -> None:
    ciclos = selic.ciclos(META)
    assert [(c.sentido, c.rotulo) for c in ciclos] == [
        ("corte", "2016–18"),
        ("corte", "2019–20"),
        ("alta", "2021"),
    ]
    primeiro = ciclos[0]
    assert (primeiro.inicio, primeiro.fim) == (date(2016, 10, 20), date(2018, 3, 22))
    assert (primeiro.selic_antes, primeiro.selic_depois) == (14.25, 6.5)
    assert (ciclos[2].selic_antes, ciclos[2].selic_depois) == (2.0, 3.5)


def test_depois_do_ciclo_conta_do_mes_do_comeco_e_deixa_vazio_o_que_nao_ha() -> None:
    ciclo = selic.ciclos(META)[0]
    ipca12 = [(date(2016, 10, 1), 7.9), (date(2017, 10, 1), 2.7), (date(2018, 10, 1), 4.6)]
    dolar = [(date(2016, 10, 19), 3.20), (date(2016, 10, 20), 3.0), (date(2017, 10, 19), 3.3)]
    dolar.append((date(2017, 10, 23), 3.4))
    divida = [(date(2016, 10, 1), 68.0)]  # acaba antes dos dois anos
    depois = selic.depois_do_ciclo(ciclo, ipca12, dolar, divida)
    assert (depois.ipca_no_comeco, depois.ipca_um_ano, depois.ipca_dois_anos) == (7.9, 2.7, 4.6)
    assert depois.dolar_um_ano == pytest.approx(10.0)  # 3,00 → 3,30, o último até um ano depois
    assert depois.divida_dois_anos is None
    # Ciclo que começou há pouco: nada do que vem depois existe ainda.
    recente = selic.Ciclo("corte", date(2018, 6, 1), date(2018, 6, 1), 6.5, 6.25)
    vazio = selic.depois_do_ciclo(recente, ipca12, dolar, divida)
    assert vazio.ipca_um_ano is None and vazio.dolar_um_ano is None


def _efeito(pp: float) -> selic.Efeito:
    return selic.efeito(
        pp,
        ipca_por_pp=relatorios.IPCA_MODELO_AGREGADO[4],
        ipca_por_pp_outro=relatorios.IPCA_MODELO_DESAGREGADO[4],
        dolar_por_pp=relatorios.DOLAR_POR_PP_DE_SELIC,
        dolar_por_pp_faixa=relatorios.DOLAR_POR_PP_DE_SELIC_FAIXA,
        divida_por_pp_de_selic=relatorios.ELASTICIDADE_SELIC.bruta,
        divida_por_1_de_dolar=relatorios.ELASTICIDADE_DOLAR.bruta,
        divida_por_pp_de_precos=relatorios.ELASTICIDADE_PRECOS.bruta,
    )


def test_corte_de_1_pp_sobe_a_inflacao_e_o_dolar_e_alivia_a_divida() -> None:
    e = _efeito(-1.0)
    assert e.ipca == pytest.approx(0.27) and e.ipca_outro_modelo == pytest.approx(0.24)
    assert e.dolar == pytest.approx(1.90)
    assert e.dolar_faixa == pytest.approx((0.77, 3.22))
    # Juros −0,48; dólar 1,9 % × 0,07; inflação 0,27 × 0,15.
    assert e.divida_pelos_juros == pytest.approx(-0.48)
    assert e.divida_pelo_dolar == pytest.approx(0.133)
    assert e.divida_pela_inflacao == pytest.approx(0.0405)
    assert e.divida == pytest.approx(-0.3065)


def test_efeito_e_linear_e_simetrico() -> None:
    corte, alta = _efeito(-2.0), _efeito(2.0)
    assert alta.ipca == pytest.approx(-corte.ipca) == pytest.approx(-0.54)
    assert alta.divida == pytest.approx(-corte.divida)
    assert alta.dolar_faixa == pytest.approx((-6.44, -1.54))
    assert _efeito(0.0).divida == 0.0


def test_caminhos_lidos_do_bc_conferem_com_o_texto_do_boxe() -> None:
    """O boxe diz 0,27 e 0,24 pp de efeito máximo, no quarto trimestre, com 1 pp por um ano."""
    r = relatorios
    assert len(r.SELIC_CAMINHO) == len(r.IPCA_MODELO_AGREGADO) == len(r.IPCA_MODELO_DESAGREGADO)
    assert r.SELIC_CAMINHO[:5] == [0.0, 1.0, 1.0, 1.0, 1.0]
    for caminho, maximo in [(r.IPCA_MODELO_AGREGADO, -0.27), (r.IPCA_MODELO_DESAGREGADO, -0.24)]:
        assert min(caminho) == maximo and caminho.index(maximo) == 4 and caminho[0] == 0.0
    piso, teto = r.DOLAR_POR_PP_DE_SELIC_FAIXA
    assert piso < r.DOLAR_POR_PP_DE_SELIC < teto < 0
    assert r.ELASTICIDADE_SELIC.choque.startswith("Selic")
    assert r.ELASTICIDADE_DOLAR.choque.startswith("Dólar")
    assert r.ELASTICIDADE_PRECOS.choque.startswith("Índices de preços")


def test_o_simulador_da_selic_vai_para_a_parte_dele() -> None:
    r = relatorios
    simulador = SimuladorSelic(
        ano=2027,
        focus_selic=12.5,
        focus_ipca=4.0,
        focus_dolar=5.4,
        focus_divida=87.5,
        meta=None,
        trimestres=[date(2026, 10, 1)] * len(r.SELIC_CAMINHO),
        selic_caminho=r.SELIC_CAMINHO,
        ipca_agregado=r.IPCA_MODELO_AGREGADO,
        ipca_desagregado=r.IPCA_MODELO_DESAGREGADO,
        dolar_por_pp=r.DOLAR_POR_PP_DE_SELIC,
        dolar_por_pp_faixa=r.DOLAR_POR_PP_DE_SELIC_FAIXA,
        divida_por_pp_de_selic=0.48,
        divida_por_1_de_dolar=0.07,
        divida_por_pp_de_precos=0.15,
        pib_em_reais=13000.0,
        fonte="x",
        nota="",
        como_ler="",
    )
    secao = Secao(
        id="juros",
        titulo="Juros",
        simulador_selic=simulador,
        gerado_em=datetime(2026, 11, 14, tzinfo=UTC),
    )
    assert organizacao.aplicar(secao) == []
    assert [(s.id, s.extras) for s in secao.subcategorias] == [("efeito", ["simulador-selic"])]
