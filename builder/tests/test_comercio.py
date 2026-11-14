"""Comércio por setor, produto e país (Comex Stat), sem rede: um Comex Stat de mentira."""

from datetime import date

import pytest

from sacibras.fontes import comexstat
from sacibras.fontes.comexstat import Item
from sacibras.secoes import externo
from sacibras.secoes.base import Contexto


def test_grupos_da_unctad_pelos_digitos_da_cuci() -> None:
    assert comexstat.grupo_unctad("222a1") == "alimentos"  # soja
    assert comexstat.grupo_unctad("081") == "alimentos"  # farelo
    assert comexstat.grupo_unctad("333") == "combustiveis"  # petróleo bruto
    assert comexstat.grupo_unctad("281b") == "minerios"  # minério de ferro
    assert comexstat.grupo_unctad("682") == "minerios"  # cobre (68, metais não ferrosos)
    assert comexstat.grupo_unctad("251") == "agricolas"  # celulose
    assert comexstat.grupo_unctad("263") == "agricolas"  # algodão
    assert comexstat.grupo_unctad("672") == "manufaturados"  # aço semiacabado
    assert comexstat.grupo_unctad("792") == "manufaturados"  # aviões
    assert comexstat.grupo_unctad("667") == "ouro"  # pedras preciosas
    assert comexstat.grupo_unctad("971") == "ouro"  # ouro não monetário


def test_nomes_curtos() -> None:
    assert comexstat.nome_curto(Item("2709", "Óleos brutos de petróleo")) == "Petróleo bruto"
    longo = Item(
        "9999",
        "Máquinas e aparelhos de uso muito específico para indústrias diversas; partes",
    )
    nome = comexstat.nome_curto(longo)
    assert ";" not in nome and nome.endswith("…") and len(nome) <= 49
    assert comexstat.nome_curto(Item("1005", "Milho")) == "Milho"
    assert comexstat.setor_curto(Item("29", "Fabricação de veículos")) == "Veículos e peças"
    assert (
        comexstat.setor_curto(Item("99", "Fabricação de coisas diversas n.c")) == "Coisas diversas"
    )


def test_ranking_fecha_no_total_e_compara_no_mesmo_periodo() -> None:
    a, b, c = Item("1", "A"), Item("2", "B"), Item("3", "C")
    fechado = {a: 50e9, b: 30e9, c: 20e9}
    agora = {a: 44e9, b: 20e9, Item("4", "D"): 1e9}  # D só apareceu este ano
    antes = {a: 40e9, b: 25e9, c: 15e9}
    t = externo.tabela_ranking(
        "x",
        "título",
        fechado,
        2025,
        nome=lambda i: i.nome,
        demais="Demais",
        fonte="f",
        nota="",
        acumulado=(agora, antes, 10, 2026),
        n=2,
    )
    assert [linha.rotulo for linha in t.linhas] == ["A", "B", "Demais", "Total"]
    assert t.colunas == [
        "2025 (US$ bi)",
        "% em 2025",
        "jan–out/2026 (US$ bi)",
        "Contra jan–out/2025 (%)",
    ]
    por = {linha.rotulo: linha.valores for linha in t.linhas}
    assert por["A"] == [50.0, 50.0, 44.0, 10.0]
    # Os demais juntam C (do ano fechado) e D (só deste ano); a coluna fecha no total.
    assert por["Demais"] == [20.0, 20.0, 1.0, pytest.approx(-93.3)]
    assert por["Total"][:3] == [100.0, 100.0, 65.0]
    assert sum(v[0] for k, v in por.items() if k != "Total") == pytest.approx(100.0)


def test_parceiros_pela_corrente_de_comercio() -> None:
    china, eua, chile = Item("China", "China"), Item("EUA", "EUA"), Item("Chile", "Chile")
    t = externo.tabela_parceiros(
        {china: 100e9, eua: 40e9, chile: 10e9}, {china: 70e9, eua: 50e9}, 2025, n=2
    )
    assert [linha.rotulo for linha in t.linhas] == ["China", "EUA", "Demais países", "Total"]
    por = {linha.rotulo: linha.valores for linha in t.linhas}
    assert por["EUA"][4] == -10.0  # comprou mais do que vendeu
    assert por["Total"] == [150.0, 100.0, 120.0, 100.0, 30.0]


# ---- a seção inteira com um Comex Stat de mentira: dois anos, um país e um bloco
def _consultar(fluxo: str, detalhe: str, de: int, ate: int, mes_ate: int = 12) -> comexstat.Valores:
    fator = mes_ate / 12
    itens = {
        "ISICDivision": [Item("01", "Produção vegetal"), Item("29", "Veículos")],
        "heading": [Item("2709", "Óleos brutos"), Item("1201", "Soja"), Item("2601", "Minério")],
        "SITCGroup": [Item("333", "Petróleo"), Item("222a1", "Soja"), Item("781", "Carros")],
        "country": [Item("China", "China"), Item("Estados Unidos", "Estados Unidos")],
        "economicBlock": [Item("União Europeia - UE", "União Europeia - UE"), Item("Ásia", "Ásia")],
    }[detalhe]
    return {
        item: {ano: (k + 1) * 10e9 * fator * (1 + (ano - de) / 10) for ano in range(de, ate + 1)}
        for k, item in enumerate(itens)
    }


def test_comercio_detalhado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(comexstat, "ultimo_mes", lambda: date(2026, 10, 1))
    monkeypatch.setattr(comexstat, "consultar", _consultar)
    cartoes, graficos, tabelas, frase = externo.comercio_detalhado(Contexto())
    assert [c.id for c in cartoes] == [
        "commodities-exportacoes",
        "maior-exportacao",
        "china-exportacoes",
    ]
    assert [g.id for g in graficos] == ["exportacoes-composicao", "exportacoes-destinos"]
    assert [t.id for t in tabelas] == [
        "exportacoes-setores",
        "importacoes-setores",
        "exportacoes-produtos",
        "importacoes-produtos",
        "parceiros",
    ]
    # Petróleo (10) + soja (20) de 60: metade são commodities, em todo ano.
    assert cartoes[0].valor == pytest.approx(50.0)
    assert cartoes[0].referencia == date(2025, 1, 1)
    # O maior produto é o de maior valor (minério, 30 de 60), com o nome de todo dia.
    assert cartoes[1].texto == "Minério de ferro" and cartoes[1].valor == 50.0
    composicao = graficos[0]
    ultimo = [s.pontos[-1][1] for s in composicao.series]
    assert sum(ultimo) == pytest.approx(100.0, abs=0.1)
    assert composicao.series[0].pontos[0][0] == date(1997, 1, 1)
    assert "2025" in frase and "minério de ferro" in frase


def test_em_dezembro_o_ano_fechado_e_o_corrente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(comexstat, "ultimo_mes", lambda: date(2025, 12, 1))
    monkeypatch.setattr(comexstat, "consultar", _consultar)
    _, _, tabelas, _ = externo.comercio_detalhado(Contexto())
    assert tabelas[0].colunas == ["2025 (US$ bi)", "% em 2025"]
