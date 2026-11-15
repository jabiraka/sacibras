"""Pobreza e condições de vida sem rede: as contas sobre as classes do SIDRA, a fome, o
saneamento e as faixas do IRPF."""

from datetime import date
from typing import Any

import pytest

from sacibras import organizacao
from sacibras.fontes import banco_mundial, ibge_sidra, ipeadata, receita_centis, receita_irpf
from sacibras.secoes import pobreza
from sacibras.secoes.base import Contexto
from sacibras.tipos import Ponto

A12, A25 = date(2012, 1, 1), date(2025, 1, 1)


def test_soma_so_nos_anos_com_todas_as_classes() -> None:
    fatias = {"a": [(A12, 1.0), (A25, 2.0)], "b": [(A25, 3.0)]}
    assert pobreza.soma(fatias, ["a", "b"]) == [(A25, 5.0)]
    assert pobreza.media(fatias, ["a", "b"]) == [(A25, 2.5)]


def test_razao_indice_e_emenda() -> None:
    assert pobreza.razao([(A12, 40.0)], [(A12, 10.0)]) == [(A12, 4.0)]
    assert pobreza.razao([(A12, 40.0)], [(A12, 0.0)]) == []
    assert pobreza.indice([(A12, 50.0), (A25, 75.0)], A12) == [(A12, 100.0), (A25, 150.0)]
    antiga = [(date(2011, 1, 1), 0.55), (A12, 0.54)]
    assert pobreza.emendar(antiga, [(A12, 0.53)]) == [(date(2011, 1, 1), 0.55)]


def test_faixas_do_irpf_em_cinco_grupos() -> None:
    nomes = ["Até 1/2", "De 3 a 5", "De 5 a 7", "De 15 a 20", "De 20 a 30", "De 80 a 160"]
    faixas = [receita_irpf.Faixa(n, declarantes=1.0, tributavel=10.0) for n in nomes]
    faixas.append(receita_irpf.Faixa("Mais de 320", declarantes=1.0, isentos=100.0, dividendos=9))
    grupos = pobreza.agrupar_irpf(faixas)
    assert [g.nome for g in grupos] == [
        "Até 5",
        "De 5 a 20",
        "De 20 a 80",
        "De 80 a 320",
        "Mais de 320",
    ]
    assert [g.declarantes for g in grupos] == [2, 2, 1, 1, 1]
    assert grupos[-1].renda == 100.0 and grupos[-1].dividendos == 9


def _anos(v0: float, v1: float) -> list[Ponto]:
    return [(date(a, 1, 1), v0 + (v1 - v0) * (a - 2012) / 13) for a in range(2012, 2026)]


def _centis() -> list[receita_centis.Centil]:
    """Cem centis de 1 de renda e 2 de bens, o centil 100 com 10 de renda e 20 de bens; o 110
    (o último milésimo) com 5 e 15; o 120 com 2 e 9."""
    saida = [
        receita_centis.Centil(n, declarantes=100.0, renda=1.0, bens=2.0, imposto=0.01)
        for n in range(1, 100)
    ]
    saida.append(receita_centis.Centil(100, declarantes=100.0, renda=10.0, bens=20.0, imposto=1.0))
    for n in range(101, 121):
        renda, bens = (5.0, 15.0) if n == 110 else (2.0, 9.0) if n == 120 else (0.5, 0.5)
        saida.append(receita_centis.Centil(n, declarantes=10.0, renda=renda, bens=bens))
    return saida


def test_centis_em_grupos() -> None:
    centis = _centis()
    tot = receita_centis.total(centis)
    assert tot.renda == 109.0 and tot.bens == 218.0 and tot.declarantes == 10_000
    grupos = {g.nome: g for g in receita_centis.agrupar(centis)}
    assert grupos["Metade de baixo"].renda == 50.0
    assert grupos["Do meio (40 %)"].renda == 40.0
    assert grupos["10 % de cima"].renda == 19.0  # nove centis de 1 e o centésimo de 10
    assert grupos["1 % de cima"].bens == 20.0
    assert grupos["0,1 % de cima"].bens == 15.0
    assert grupos["0,01 % de cima"].renda == 2.0


def test_centis_acha_as_colunas_nas_duas_linhas_do_cabecalho() -> None:
    em_cima = ("", "Centil", "Quantidade de Contribu intes", "RB4", None, "Rendimentos Isentos")
    em_cima += (None, "Imposto Devido", "Bens e Direitos", "Dívidas e Ônus")
    embaixo = (None, None, None, "Limite superior", "Soma de RB4 do Centil", "Lucros e dividendos")
    embaixo += ("Outros", None, "Total Bens e Direitos", None)
    assert receita_centis.colunas(em_cima, embaixo) == {
        "declarantes": 2,
        "renda": 4,
        "dividendos": 5,
        "imposto": 7,
        "bens": 8,
        "dividas": 9,
    }


@pytest.fixture
def ctx(monkeypatch: pytest.MonkeyPatch) -> Contexto:
    fatias = {c: _anos(10.0, 10.0) for c, _ in pobreza.DECIMOS}
    fatias[pobreza.DEZ_MAIS_RICOS] = _anos(42.8, 40.3)
    fatias[pobreza.UM_MAIS_RICO] = _anos(12.1, 11.0)
    A23, A24 = date(2023, 1, 1), date(2024, 1, 1)

    def series(tabela: int, variavel: int, **kw: Any) -> dict[str, list[Ponto]]:
        por, nivel = kw.get("por", ""), kw.get("nivel", "n1/all")
        if nivel == "n3/all":
            return {"33": [(A24, 3.0)], "42": [(A24, 1.0)]}
        if tabela in (7527, 7533):
            return fatias | {"49243": _anos(1782, 2264)}
        if tabela == 7441:
            return {"2776": _anos(3934, 4577), "2777": _anos(2265, 2657), "2779": _anos(2239, 2755)}
        if tabela == 7444:
            return {"4": _anos(3462, 3921), "5": _anos(2539, 3085)}
        if tabela == 9552 and por.startswith("Situação de"):
            return {"109102": [(A23, 4.0), (A24, 3.1)], "109101": [(A23, 5.5), (A24, 4.6)]}
        if tabela == 9552:
            return {"6795": [(A23, 4.0), (A24, 3.1)], "1": [(A24, 2.8)], "2": [(A24, 4.9)]}
        if tabela == 9751:
            return {"1140": [(A24, 3.0)], "6798": [(A24, 2.0)]}
        if tabela == 7192:  # duas categorias de esgoto por situação, somadas depois
            return {"6795": [(A24, 60.0), (A24, 6.0)], "1": [(A24, 70.0), (A24, 6.0)]}
        if tabela == 7457:
            return {"49238": _anos(16.6, 17.0), "49239": _anos(2.5, 4.0), "82225": _anos(19, 22)}
        if tabela == 7458:
            return {"49238": [(A25, 774.0)], "49240": [(A25, 2682.0)]}
        if tabela in (6738, 7307):
            return {"6795": [(A23, 95.0), (A24, 96.0)], "1": [(A24, 99.0)], "2": [(A24, 80.0)]}
        if tabela == 6739:
            return {"": [(A23, 15.0), (A24, 14.6)]}
        if tabela in (6731, 6736):
            return {"6795": [(A23, 85.0), (A24, 86.0)], "2": [(A24, 30.0)]}
        if tabela == 7113:
            return {"2795": [(A23, 5.4), (A24, 5.2)], "3302": [(A23, 15.0), (A24, 14.5)]}
        if tabela == 7125:
            return {"2776": [(A24, 3.0)], "119525": [(A24, 7.0)]}
        if tabela == 7126:
            return {"": [(A23, 10.0), (A24, 10.1)]}
        if tabela == 7443:
            return {
                "120704": [(A12, 3000.0), (A24, 3500.0)],
                "11630": [(A12, 2800.0), (A24, 2500.0)],
                "99713": [(A12, 7000.0), (A24, 7000.0)],
            }
        if tabela == 7442:
            return {"95253": [(A24, 3500.0)], "3302": [(A12, 3000.0), (A24, 3900.0)]}
        if tabela == 6821:
            return {"1055": [(A23, 21.0), (A24, 22.0)], "4342": [(A24, 62.0)]}
        return {"": _anos(0.54, 0.511)}

    def ipea(codigo: str, desde: date) -> list[Ponto]:
        return [(date(a, 1, 1), 60.0 - a + 1995) for a in range(1995, 2026)]

    def irpf() -> tuple[int, list[receita_irpf.Faixa]]:
        return 2024, [
            receita_irpf.Faixa("De 3 a 5", declarantes=1000.0, tributavel=100.0, dividendos=1.0),
            receita_irpf.Faixa("Mais de 320", declarantes=1.0, isentos=50.0, dividendos=3.0),
        ]

    def centis() -> tuple[int, list[receita_centis.Centil]]:
        return 2024, _centis()

    def sem_banco_mundial(*a: Any, **k: Any) -> Any:
        raise RuntimeError("sem rede")

    monkeypatch.setattr(ibge_sidra, "series", series)
    monkeypatch.setattr(ipeadata, "serie", ipea)
    monkeypatch.setattr(
        ipeadata, "por_territorio", lambda *a, **k: {"33": [(A24, 22.0)], "42": [(A24, 9.0)]}
    )
    monkeypatch.setattr(receita_irpf, "grandes_numeros", irpf)
    monkeypatch.setattr(receita_centis, "mais_novo", centis)
    monkeypatch.setattr(pobreza, "dispersao_paises", sem_banco_mundial)
    monkeypatch.setattr(
        banco_mundial,
        "serie_do_pais",
        lambda pais, codigo, *a: [(2021, 3.5), (2024, 2.5)],
    )
    return Contexto(hoje=date(2026, 11, 14))


def test_montar_poe_tudo_numa_parte(ctx: Contexto) -> None:
    secao = pobreza.montar(ctx)
    assert organizacao.aplicar(secao) == []
    assert [s.id for s in secao.subcategorias] == [
        "linha-de-pobreza",
        "fome",
        "saneamento",
        "desigualdade",
        "quem-ganha-mais",
        "diferencas",
    ]
    assert [c.id for c in secao.cartoes[:4]] == ["pobreza", "fome", "esgoto", "gini"]
    assert secao.graficos[0].id == "pobreza"
    cartoes = {c.id: c for c in secao.cartoes}
    assert cartoes["gini"].valor == pytest.approx(0.511)
    assert cartoes["fatia-40-pobres"].valor == pytest.approx(40.0)
    assert cartoes["razao-10-40"].valor == pytest.approx(40.3 / 40.0, abs=1e-3)
    assert cartoes["irpf-topo-dividendos"].valor == pytest.approx(75.0)
    assert cartoes["mulheres-homens"].valor == pytest.approx(3085 / 3921 * 100, abs=1e-2)
    assert cartoes["fome"].valor == pytest.approx(3.1)
    assert cartoes["inseguranca-moderada-grave"].valor == pytest.approx(7.7)
    assert cartoes["esgoto"].valor == pytest.approx(66.0)  # as duas categorias somadas
    assert cartoes["subalimentacao"].texto == "menos de 2,5 %"
    assert cartoes["bolsa-familia"].detalhe == "R$ 774 por pessoa; sem ele, R$ 2.682"
    assert cartoes["internet"].valor == pytest.approx(96.0)
    assert cartoes["analfabetismo"].valor == pytest.approx(5.2)
    assert cartoes["superior-medio"].valor == pytest.approx(7000 / 2500, abs=1e-3)
    assert cartoes["aluguel"].valor == pytest.approx(22.0)
    assert cartoes["irpf-1-patrimonio"].valor == pytest.approx(20 / 218 * 100, abs=1e-2)
    escola = next(t for t in secao.tabelas if t.id == "pobreza-escola-idade")
    medio = next(li for li in escola.linhas if li.rotulo == "Médio completo")
    assert medio.valores == [2500.0, round(2500 / 3500 * 100), round((2500 / 2800 - 1) * 100, 1)]
    centis = next(t for t in secao.tabelas if t.id == "pobreza-centis")
    assert centis.linhas[0].valores[:2] == [round(50 / 109 * 100, 1), round(100 / 218 * 100, 1)]
    assert cartoes["lenha"].valor == pytest.approx(14.6)
    assert "meta: 90 % até 2033" in cartoes["esgoto"].detalhe
    san = next(g for g in secao.graficos if g.id == "saneamento")
    assert [li.valor for li in san.linhas] == [99.0, 90.0]
    assert all(len(c.detalhe) <= 60 for c in secao.cartoes)
    gini = next(g for g in secao.graficos if g.id == "gini")
    antiga = next(s for s in gini.series if s.id == "pnad")
    assert antiga.pontos[-1][0] == date(2011, 1, 1)  # a PNAD antiga para onde a Contínua começa
    estados = next(t for t in secao.tabelas if t.id == "pobreza-estados")
    assert len(estados.linhas) == 27
    assert [li.rotulo for li in estados.linhas[:2]] == ["Rio de Janeiro", "Santa Catarina"]
    saneamento = next(t for t in secao.tabelas if t.id == "pobreza-saneamento")
    assert saneamento.linhas[1].valores == [66.0, 76.0, None]
    assert saneamento.linhas[-1].valores == [14.6, None, None]  # a lenha, sem cidade e campo
    assert (
        secao.resumo.startswith("Em 2025, ") and "3,1 % moravam em casas com fome" in secao.resumo
    )


def test_banco_mundial_fica_com_o_ano_mais_novo_de_cada_pais() -> None:
    from sacibras.fontes import banco_mundial

    linhas = [
        {"countryiso3code": "BRA", "date": "2022", "value": 52.0},
        {"countryiso3code": "BRA", "date": "2024", "value": 50.3},
        {"countryiso3code": "BRA", "date": "2025", "value": None},
        {"countryiso3code": "LCN", "date": "2024", "value": 45.0},
    ]
    assert banco_mundial.ultimos(linhas, {"BRA"}) == {"BRA": (2024, 50.3)}
