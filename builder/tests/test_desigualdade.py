"""Desigualdade sem rede: as contas sobre as classes do SIDRA e as faixas do IRPF."""

from datetime import date
from typing import Any

import pytest

from sacibras import organizacao
from sacibras.fontes import ibge_sidra, ipeadata, receita_irpf
from sacibras.secoes import desigualdade
from sacibras.secoes.base import Contexto
from sacibras.tipos import Ponto

A12, A25 = date(2012, 1, 1), date(2025, 1, 1)


def test_soma_so_nos_anos_com_todas_as_classes() -> None:
    fatias = {"a": [(A12, 1.0), (A25, 2.0)], "b": [(A25, 3.0)]}
    assert desigualdade.soma(fatias, ["a", "b"]) == [(A25, 5.0)]
    assert desigualdade.media(fatias, ["a", "b"]) == [(A25, 2.5)]


def test_razao_indice_e_emenda() -> None:
    assert desigualdade.razao([(A12, 40.0)], [(A12, 10.0)]) == [(A12, 4.0)]
    assert desigualdade.razao([(A12, 40.0)], [(A12, 0.0)]) == []
    assert desigualdade.indice([(A12, 50.0), (A25, 75.0)], A12) == [(A12, 100.0), (A25, 150.0)]
    antiga = [(date(2011, 1, 1), 0.55), (A12, 0.54)]
    assert desigualdade.emendar(antiga, [(A12, 0.53)]) == [(date(2011, 1, 1), 0.55)]


def test_faixas_do_irpf_em_cinco_grupos() -> None:
    nomes = ["Até 1/2", "De 3 a 5", "De 5 a 7", "De 15 a 20", "De 20 a 30", "De 80 a 160"]
    faixas = [receita_irpf.Faixa(n, declarantes=1.0, tributavel=10.0) for n in nomes]
    faixas.append(receita_irpf.Faixa("Mais de 320", declarantes=1.0, isentos=100.0, dividendos=9))
    grupos = desigualdade.agrupar_irpf(faixas)
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


@pytest.fixture
def ctx(monkeypatch: pytest.MonkeyPatch) -> Contexto:
    fatias = {c: _anos(10.0, 10.0) for c, _ in desigualdade.DECIMOS}
    fatias[desigualdade.DEZ_MAIS_RICOS] = _anos(42.8, 40.3)
    fatias[desigualdade.UM_MAIS_RICO] = _anos(12.1, 11.0)

    def series(tabela: int, variavel: int, **kw: Any) -> dict[str, list[Ponto]]:
        if tabela in (7527, 7533):
            return fatias | {"49243": _anos(1782, 2264)}
        if tabela == 7441:
            return {"2776": _anos(3934, 4577), "2777": _anos(2265, 2657), "2779": _anos(2239, 2755)}
        if tabela == 7444:
            return {"4": _anos(3462, 3921), "5": _anos(2539, 3085)}
        if kw.get("nivel") == "n3/all":
            return {"33": _anos(0.53, 0.543), "42": _anos(0.45, 0.425)}
        return {"": _anos(0.54, 0.511)}

    def ipea(codigo: str, desde: date) -> list[Ponto]:
        return [(date(a, 1, 1), 60.0 - a + 1995) for a in range(1995, 2026)]

    def irpf() -> tuple[int, list[receita_irpf.Faixa]]:
        return 2024, [
            receita_irpf.Faixa("De 3 a 5", declarantes=1000.0, tributavel=100.0, dividendos=1.0),
            receita_irpf.Faixa("Mais de 320", declarantes=1.0, isentos=50.0, dividendos=3.0),
        ]

    def sem_banco_mundial() -> None:
        raise RuntimeError("sem rede")

    monkeypatch.setattr(ibge_sidra, "series", series)
    monkeypatch.setattr(ipeadata, "serie", ipea)
    monkeypatch.setattr(receita_irpf, "grandes_numeros", irpf)
    monkeypatch.setattr(desigualdade, "dispersao_paises", sem_banco_mundial)
    return Contexto(hoje=date(2026, 11, 14))


def test_montar_poe_tudo_numa_parte(ctx: Contexto) -> None:
    secao = desigualdade.montar(ctx)
    assert organizacao.aplicar(secao) == []
    cartoes = {c.id: c for c in secao.cartoes}
    assert cartoes["gini"].valor == pytest.approx(0.511)
    assert cartoes["fatia-40-pobres"].valor == pytest.approx(40.0)
    assert cartoes["razao-10-40"].valor == pytest.approx(40.3 / 40.0, abs=1e-3)
    assert cartoes["irpf-topo-dividendos"].valor == pytest.approx(75.0)
    assert cartoes["mulheres-homens"].valor == pytest.approx(3085 / 3921 * 100, abs=1e-2)
    assert all(len(c.detalhe) <= 60 for c in secao.cartoes)
    gini = next(g for g in secao.graficos if g.id == "gini")
    antiga = next(s for s in gini.series if s.id == "pnad")
    assert antiga.pontos[-1][0] == date(2011, 1, 1)  # a PNAD antiga para onde a Contínua começa
    estados = next(t for t in secao.tabelas if t.id == "desigualdade-estados")
    assert [li.rotulo for li in estados.linhas] == ["Brasil", "Rio de Janeiro", "Santa Catarina"]
    assert "0,511 em 2025" in secao.resumo


def test_banco_mundial_fica_com_o_ano_mais_novo_de_cada_pais() -> None:
    from sacibras.fontes import banco_mundial

    linhas = [
        {"countryiso3code": "BRA", "date": "2022", "value": 52.0},
        {"countryiso3code": "BRA", "date": "2024", "value": 50.3},
        {"countryiso3code": "BRA", "date": "2025", "value": None},
        {"countryiso3code": "LCN", "date": "2024", "value": 45.0},
    ]
    assert banco_mundial.ultimos(linhas, {"BRA"}) == {"BRA": (2024, 50.3)}
