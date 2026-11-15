"""Demografia sem rede: as planilhas da projeção montadas aqui, e as séries trocadas por
números de mentira."""

import io
import math
from datetime import date
from typing import Any

import openpyxl
import pytest

from sacibras.fontes import (
    banco_mundial,
    ibge_projecao,
    ibge_sidra,
    onu_wpp,
    siconfi,
    tesouro_rtn,
)
from sacibras.fontes.ibge_projecao import PlanilhaMudouError, ler_por_ano, ler_quinquenal
from sacibras.secoes import demografia
from sacibras.secoes.base import Contexto
from sacibras.tipos import Ponto

ANOS = list(range(2000, 2071))


def _livro(linhas: list[list[Any]]) -> bytes:
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = "4) INDICADORES"
    for linha in linhas:
        ws.append(linha)
    saida = io.BytesIO()
    livro.save(saida)
    return saida.getvalue()


def _por_ano(colunas: dict[str, Any], siglas: tuple[str, ...] = ("BR", "SP")) -> bytes:
    """Como a tab3/tab4: quatro linhas de título, cabeçalho com ANO, uma linha por ano × local."""
    linhas: list[list[Any]] = [
        ["Projeções das Populações, Revisão 2024"],
        ["Brasil, Grandes Regiões e Unidades da Federação"],
        [],
        [None, None, None, None, "POPULAÇÃO"],
        ["ANO", "CÓD.", "SIGLA", "LOCAL", *colunas],
    ]
    for cod, sigla in enumerate(siglas):
        for ano in ANOS:
            valores = [f(ano) * (1 + cod) if callable(f) else f for f in colunas.values()]
            linhas.append([ano, cod, sigla, sigla, *valores])
    linhas.append(["Fonte: IBGE"])
    return _livro(linhas)


GRUPOS = [" 00-04", " 05-09", " 60-64", " 65-69", "90+"]


def _quinquenal() -> bytes:
    linhas: list[list[Any]] = [
        ["Projeções das Populações, Revisão 2024"],
        [],
        [None, None, None, None, None, "ANO"],
        ["GRUPO ETÁRIO", "SEXO", "CÓD.", "SIGLA", "LOCAL", *ANOS],
    ]
    for sexo, fator in (("Ambos", 2), ("Homens", 1), ("Mulheres", 1.1)):
        for k, grupo in enumerate(GRUPOS):
            linhas.append(
                [grupo, sexo, 0, "BR", "Brasil", *[1000.0 * (k + 1) * fator for _ in ANOS]]
            )
    linhas.append([" 00-04", "Homens", 35, "SP", "São Paulo", *[1.0 for _ in ANOS]])
    return _livro(linhas)


def test_le_por_ano_pelo_nome_da_coluna() -> None:
    conteudo = _por_ano({"POP_T": lambda a: 1e6 * a, "TFT": 1.5})
    dados = ler_por_ano(conteudo)
    assert set(dados) == {"BR", "SP"}
    assert dados["BR"]["POP_T"][2026] == 1e6 * 2026
    assert dados["SP"]["POP_T"][2026] == 2e6 * 2026
    assert dados["BR"]["TFT"][2070] == 1.5
    assert "LOCAL" not in dados["BR"]


def test_planilha_sem_cabecalho_levanta_erro_claro() -> None:
    with pytest.raises(PlanilhaMudouError, match="ANO"):
        ler_por_ano(_livro([["outra coisa"], [1, 2, 3]]))


def test_le_a_piramide_de_homens_e_mulheres_do_brasil() -> None:
    dados = ler_quinquenal(_quinquenal())
    assert list(dados["Homens"]) == ["00-04", "05-09", "60-64", "65-69", "90+"]
    assert dados["Mulheres"]["90+"][2026] == pytest.approx(5500.0)
    assert dados["Homens"]["00-04"][2000] == 1000.0  # a linha de SP não entra


def test_rotulos_e_plural() -> None:
    assert demografia.rotulo_do_grupo("00-04") == "0 a 4"
    assert demografia.rotulo_do_grupo("90+") == "90 ou mais"
    assert demografia.filhos(1.51) == "1,51 filho"
    assert demografia.filhos(2.32) == "2,32 filhos"


def test_pico_crescimento_e_primeiro_ano() -> None:
    serie = {2000: 1.0, 2001: 3.0, 2002: 2.0}
    assert demografia.pico(serie) == (2001, 3.0)
    assert demografia.crescimento(serie) == {
        2001: pytest.approx(200.0),
        2002: pytest.approx(-100 / 3),
    }
    assert demografia.primeiro_ano(serie, lambda a: serie[a] > 1.5) == 2001
    assert demografia.primeiro_ano(serie, lambda a: serie[a] > 9) is None


def test_trimestre_civil_vem_do_movel_que_fecha_o_trimestre() -> None:
    movel = [(date(2026, m, 1), float(m)) for m in range(1, 10)]
    assert demografia.trimestre_civil(movel) == [
        (date(2026, 1, 1), 3.0),
        (date(2026, 4, 1), 6.0),
        (date(2026, 7, 1), 9.0),
    ]


def _trimestres(anos: range, valor: Any) -> list[Ponto]:
    return [(date(a, 3 * t - 2, 1), valor(a, t)) for a in anos for t in range(1, 5)]


def test_decomposicao_soma_o_crescimento_do_pib() -> None:
    # PIB cresce 3 % ao ano e os ocupados 1 %: a produtividade cresce (1,03 / 1,01) − 1.
    pib = _trimestres(range(2012, 2016), lambda a, t: 100 * 1.03 ** (a - 2012))
    ocupados = _trimestres(range(2012, 2016), lambda a, t: 90_000 * 1.01 ** (a - 2012))
    anos = demografia.decomposicao_anual(pib, ocupados)
    assert [x.ano for x in anos] == [2013, 2014, 2015]
    for x in anos:
        assert x.pib == pytest.approx(3.0)
        assert x.ocupados == pytest.approx(1.0)
        assert x.produtividade == pytest.approx((1.03 / 1.01 - 1) * 100)
        assert x.parte_ocupados + x.parte_produtividade == pytest.approx(x.pib)
        assert x.parte_ocupados == pytest.approx(3.0 * math.log(1.01) / math.log(1.03))
    assert demografia.media_geometrica([x.produtividade for x in anos]) == pytest.approx(
        (1.03 / 1.01 - 1) * 100
    )


def test_decomposicao_pula_ano_incompleto_e_pib_parado() -> None:
    pib = _trimestres(range(2012, 2014), lambda a, t: 100.0)
    ocupados = _trimestres(range(2012, 2014), lambda a, t: 90_000 * (1.02 if a == 2013 else 1))
    pib.append((date(2014, 1, 1), 100.0))  # 2014 só com um trimestre
    ocupados.append((date(2014, 1, 1), 90_000.0))
    anos = demografia.decomposicao_anual(pib, ocupados)
    assert [x.ano for x in anos] == [2013]
    assert anos[0].pib == 0
    assert anos[0].parte_ocupados == pytest.approx(2.0)
    assert anos[0].parte_produtividade == pytest.approx(-2.0)


def test_produtividade_tem_100_na_primeira_janela_completa() -> None:
    pib = _trimestres(range(2012, 2015), lambda a, t: 100 * 1.02 ** (a - 2012))
    ocupados = _trimestres(range(2012, 2015), lambda a, t: 1000.0)
    prod = demografia.produtividade(pib, ocupados)
    assert prod["por_ocupado"][0] == (date(2012, 10, 1), 100.0)
    assert prod["por_ocupado"][-1][1] == pytest.approx(100 * 1.02**2)
    assert prod["ocupados"][-1][1] == pytest.approx(100.0)


def test_por_hora_desconta_as_horas_que_caem() -> None:
    # PIB sobe 2 % ao ano, os ocupados ficam e as horas por semana caem 1 % ao ano.
    pib = _trimestres(range(2012, 2015), lambda a, t: 100 * 1.02 ** (a - 2012))
    ocupados = _trimestres(range(2012, 2015), lambda a, t: 1000.0)
    horas = _trimestres(range(2012, 2015), lambda a, t: 40 * 0.99 ** (a - 2012))
    hora = demografia.por_hora(pib, ocupados, horas)
    assert hora[0] == (date(2012, 10, 1), 100.0)
    assert hora[-1][1] == pytest.approx(100 * (1.02 / 0.99) ** 2)
    # Trimestre sem horas fica de fora da janela, em vez de valer zero.
    assert demografia.por_hora(pib, ocupados, horas[4:])[0][0] == date(2013, 10, 1)


def _projecao() -> onu_wpp.Projecao:
    anos = range(2024, 2101)
    return onu_wpp.Projecao(
        mediana={a: 210_000.0 for a in anos},
        inferior80={a: 200_000.0 - (a - 2024) * 100 for a in anos},
        superior80={a: 220_000.0 + (a - 2024) * 100 for a in anos},
        inferior95={a: 190_000.0 for a in anos},
        superior95={a: 230_000.0 for a in anos},
    )


def _idosos_onu() -> onu_wpp.Projecao:
    anos = range(2024, 2101)
    return onu_wpp.Projecao(
        mediana={a: 20.0 + (a - 2024) * 0.5 for a in anos},
        inferior80={a: 20.0 + (a - 2024) * 0.4 for a in anos},
        superior80={a: 20.0 + (a - 2024) * 0.6 for a in anos},
        inferior95={a: 20.0 + (a - 2024) * 0.3 for a in anos},
        superior95={a: 20.0 + (a - 2024) * 0.8 for a in anos},
    )


def test_barras_da_onu_em_milhoes() -> None:
    barras = demografia.barras_onu(_projecao(), [2030, 2100, 2110])
    assert barras == [(date(2030, 1, 1), 199.4, 220.6), (date(2100, 1, 1), 192.4, 227.6)]


def test_le_a_planilha_da_onu_pelo_codigo_do_pais() -> None:
    livro = openpyxl.Workbook()
    livro.remove(livro.active)
    for k, aba in enumerate(onu_wpp.ABAS.values()):
        ws = livro.create_sheet(aba)
        ws.append(["United Nations"])
        ws.append([None])
        ws.append(["Index", "Variant", "Region", "Notes", "Location code", "ISO3", 2024, 2025])
        ws.append([1, aba, "World", "", 900, "", 8e6, 8.1e6])
        ws.append([2, aba, "Brazil", "", 76, "BRA", 211_000 + k, 212_000 + k])
    saida = io.BytesIO()
    livro.save(saida)
    projecao = onu_wpp.ler_planilha(saida.getvalue())
    assert projecao.inferior95 == {2024: 211_000, 2025: 212_000}
    assert projecao.superior95[2025] == 212_004
    with pytest.raises(onu_wpp.FonteForaDoArError, match="país 32"):
        onu_wpp.ler_planilha(saida.getvalue(), pais=32)


def test_piramide_traz_o_ano_corrente_e_o_contorno() -> None:
    p = demografia.montar_piramide(ler_quinquenal(_quinquenal()), 2026)
    assert p.grupos == ["0 a 4", "5 a 9", "60 a 64", "65 a 69", "90 ou mais"]
    assert 2026 in p.anos and p.ano_inicial == 2026 and p.ano_contorno == 2000
    assert p.homens[0] == [1.0, 2.0, 3.0, 4.0, 5.0]  # mil pessoas
    assert p.primeiro_ano_projetado == 2023


# ------------------------------------------------------------------ o custo do envelhecimento


def _piramide_plana() -> dict[str, dict[int, float]]:
    """Mil pessoas em cada grupo de cinco anos de 0 a 89 e ninguém com 90 ou mais."""
    grupos = {f"{i:02d}-{i + 4:02d}": {2030: 1000.0} for i in range(0, 90, 5)}
    return {**grupos, "90+": {2030: 0.0}}


def test_idade_de_corte_que_mantem_a_proporcao() -> None:
    piramide = _piramide_plana()
    # 65 a 89: 5 grupos; 15 a 64: 10 grupos: meia pessoa idosa por pessoa em idade de trabalhar
    assert demografia.acima_de(piramide, 2030, 65) == 5000
    assert demografia.acima_de(piramide, 2030, 67.5) == 4500  # meio grupo
    assert demografia.idade_que_mantem(piramide, 2030, 0.5) == pytest.approx(65, abs=1e-6)
    # 1/3: (90 - x) / (x - 15) = 1/3 → x = 71,25
    assert demografia.idade_que_mantem(piramide, 2030, 1 / 3) == pytest.approx(71.25, abs=1e-6)


def test_ambos_os_sexos_soma_e_tira_os_espacos() -> None:
    q = {
        "Homens": {" 00-04": {2030: 1.0}, "90+": {2030: 2.0}},
        "Mulheres": {" 00-04": {2030: 3.0}, "90+": {2030: 4.0}},
    }
    assert demografia.ambos_os_sexos(q) == {"00-04": {2030: 4.0}, "90+": {2030: 6.0}}


def test_inss_por_pessoa_em_reais_do_primeiro_ano() -> None:
    reais = {2026: (12_000.0, 6_000.0), 2028: (13_200.0, 0.0), 2030: (1.0, 1.0)}
    pessoas = {2026: 1000.0, 2028: 1000.0}  # mil pessoas; 2030 sem população fica de fora
    v = demografia.por_pessoa_por_mes(reais, pessoas, {2027: 10.0}, 0.0)
    # R$ 12 bi / 1 milhão de pessoas / 12 meses = R$ 1.000; em 2028, 13.200 / 1,1 = 12.000
    assert v["beneficios"] == [(date(2026, 1, 1), 1000.0), (date(2028, 1, 1), 1000.0)]
    assert v["deficit"][0] == (date(2026, 1, 1), 500.0)
    nivel = demografia.nivel_de_precos([2026, 2029], {2027: 10.0}, 5.0)
    assert nivel[2029] == pytest.approx(1.1 * 1.05 * 1.05)


def test_freio_em_pontos_percentuais_ao_ano() -> None:
    parte = {2026: 70.0, 2050: 70.0 * 0.99**24}
    assert demografia.freio(parte, 2026, 2050) == pytest.approx(-1.0)


def _livro_onu(abas: list[str], cabecalho: list[str], linhas: list[list[Any]]) -> bytes:
    livro = openpyxl.Workbook()
    livro.remove(livro.active)
    for aba in abas:
        ws = livro.create_sheet(aba)
        ws.append(["United Nations"])
        ws.append([None])
        ws.append(cabecalho)
        for linha in linhas:
            ws.append([*linha[:-1], linha[-1] + abas.index(aba)])
    saida = io.BytesIO()
    livro.save(saida)
    return saida.getvalue()


def test_le_os_idosos_por_100_da_onu_so_os_dois_sexos() -> None:
    cabecalho = ["Index", "Variant", "Region", "Notes", "Location code", "Year", "Sex", "15-64"]
    linhas = [
        [1, "x", "World", "", 900, 2024, "Total", 15.0],
        [2, "x", "Brazil", "", 76, 2024, "Male", 14.0],
        [3, "x", "Brazil", "", 76, 2024, "Total", 16.6],
        [4, "x", "Brazil", "", 76, 2050, "Total", 35.8],
        [5, "x", "Chile", "", 152, 2024, "Total", 99.0],
    ]
    p = onu_wpp.ler_idosos_por_100(_livro_onu(list(onu_wpp.ABAS.values()), cabecalho, linhas))
    assert p.inferior95 == {2024: 16.6, 2050: 35.8}  # a 1ª aba
    assert p.mediana[2050] == pytest.approx(37.8)  # a 3ª aba soma 2
    with pytest.raises(onu_wpp.FonteForaDoArError, match="país 32"):
        onu_wpp.ler_idosos_por_100(
            _livro_onu(list(onu_wpp.ABAS.values()), cabecalho, linhas), pais=32
        )


def test_le_as_variantes_da_onu_pelo_nome_da_coluna() -> None:
    cabecalho = ["Index", "Variant", "Region", "Notes", "Location code", "Year", "Outra"]
    cabecalho += [onu_wpp.COLUNA_IDOSOS]
    linhas = [[1, "x", "Brazil", "", 76, 2050, 1.0, 35.0]]
    abas = list(onu_wpp.VARIANTES.values())
    v = onu_wpp.ler_variantes(_livro_onu(abas, cabecalho, linhas))
    assert v["media"] == {2050: 35.0} and v["alta"] == {2050: 39.0}
    with pytest.raises(onu_wpp.FonteForaDoArError, match="abas que sumiram"):
        onu_wpp.ler_variantes(_livro_onu(abas[:2], cabecalho, linhas))


# ------------------------------------------------------------------ a seção inteira


def _grupos(a: int) -> dict[str, float]:
    pop = 200e6 + 1e6 * (a - 2000) - 0.05e6 * (a - 2000) ** 2  # sobe e desce
    pia = 140e6 + 0.5e6 * (a - 2000) - 0.03e6 * (a - 2000) ** 2
    idosos = 10e6 + 0.7e6 * (a - 2000)
    return {
        "POP_T": pop,
        "0-14_T": pop - pia - idosos,
        "15-64_T": pia,
        "65+_T": idosos,
        "80+_T": idosos / 5,
        "P_65+_T": idosos / pop,
        "P_80+_T": idosos / 5 / pop,
    }


def _indicadores(a: int) -> dict[str, float]:
    g = _grupos(a)
    return {
        "TFT": 2.3 - 0.01 * (a - 2000),
        "e0_T": 71 + 0.2 * (a - 2000),
        "e0_H": 68 + 0.2 * (a - 2000),
        "e0_M": 75 + 0.2 * (a - 2000),
        "e60_T": 20 + 0.1 * (a - 2000),
        "NASC_T": 3.5e6 - 3e4 * (a - 2000),
        "OBT_T": 1.1e6 + 2.5e4 * (a - 2000),
        "RDI65": g["65+_T"] / g["15-64_T"] * 100,
        "RDJ65": g["0-14_T"] / g["15-64_T"] * 100,
        "RDT65": (g["0-14_T"] + g["65+_T"]) / g["15-64_T"] * 100,
        "ID_MED": 25 + 0.4 * (a - 2000),
        "TMI_T": max(28 - 0.6 * (a - 2000), 6.0),
    }


def _tabela(f: Any) -> dict[str, dict[str, dict[int, float]]]:
    saida: dict[str, dict[str, dict[int, float]]] = {}
    for sigla in ("BR", "SP", "AC"):
        local: dict[str, dict[int, float]] = {}
        for a in ANOS:
            for chave, v in f(a).items():
                local.setdefault(chave, {})[a] = v * (1.1 if sigla == "SP" else 1)
        saida[sigla] = local
    return saida


def _mensal(inicio: date, n: int, valor: float) -> list[Ponto]:
    return [
        (
            date(inicio.year + (inicio.month - 1 + i) // 12, (inicio.month - 1 + i) % 12 + 1, 1),
            valor,
        )
        for i in range(n)
    ]


@pytest.fixture
def ctx(monkeypatch: pytest.MonkeyPatch) -> Contexto:
    monkeypatch.setattr(ibge_projecao, "indicadores", lambda: _tabela(_indicadores))
    monkeypatch.setattr(ibge_projecao, "grupos", lambda: _tabela(_grupos))
    monkeypatch.setattr(ibge_projecao, "quinquenal", lambda: ler_quinquenal(_quinquenal()))

    def serie(tabela: int, variavel: int, **kw: Any) -> list[Ponto]:
        if tabela == demografia.PIB_VOLUME[0]:
            return _trimestres(range(2012, 2027), lambda a, t: 150 * 1.02 ** (a - 2012))[:-2]
        if tabela == demografia.HORAS[0]:
            return _trimestres(range(2012, 2027), lambda a, t: 40.0)
        return [(d, 90_000 * 1.01 ** (d.year - 2012)) for d, _ in _mensal(date(2012, 3, 1), 175, 0)]

    monkeypatch.setattr(ibge_sidra, "serie", serie)
    monkeypatch.setattr(
        tesouro_rtn,
        "serie_historica",
        lambda: {
            "rgps": _mensal(date(2010, 1, 1), 199, 80_000.0),
            "arrecadacao_rgps": _mensal(date(2010, 1, 1), 199, 55_000.0),
        },
    )
    monkeypatch.setattr(onu_wpp, "populacao", _projecao)
    monkeypatch.setattr(onu_wpp, "idosos_por_100", _idosos_onu)
    monkeypatch.setattr(onu_wpp, "populacao_15_64", _projecao)
    monkeypatch.setattr(
        onu_wpp,
        "variantes",
        lambda: {
            k: {a: 20.0 + (a - 2024) * f for a in range(2024, 2101)}
            for k, f in (
                ("media", 0.5),
                ("constante", 0.5),
                ("reposicao", 0.3),
                ("baixa", 0.8),
                ("alta", 0.35),
            )
        },
    )
    monkeypatch.setattr(
        siconfi,
        "previdencia_uniao",
        lambda hoje: [
            siconfi.PrevidenciaUniao(a, 40e9, -60e9, 9e9, -48e9, -5e9) for a in (2024, 2025)
        ],
    )
    monkeypatch.setattr(
        banco_mundial,
        "series_dos_paises",
        lambda paises, *a: {p: [(2000, 5.0), (2025, 10.0)] for p in paises},
    )
    c = Contexto(hoje=date(2026, 11, 14))
    c._sgs[("PIB_12M", 30)] = _mensal(date(2010, 1, 1), 199, 12_000_000.0)
    return c


def test_monta_a_secao_com_o_ano_corrente_e_o_inss(ctx: Contexto) -> None:
    secao = demografia.montar(ctx)
    ids = [c.id for c in secao.cartoes]
    assert ids[:4] == ["populacao", "fecundidade", "idosos-por-100", "deficit-inss"]
    populacao = secao.cartoes[0]
    assert populacao.referencia == date(2026, 1, 1)
    assert populacao.valor == pytest.approx(_grupos(2026)["POP_T"] / 1e6, abs=1e-3)
    inss = next(c for c in secao.cartoes if c.id == "deficit-inss")
    assert inss.valor == pytest.approx(25_000 * 12 / 12_000_000 * 100)
    assert inss.procedencia == "calculado"

    graficos = {g.id: g for g in secao.graficos}
    assert secao.graficos[0].id == "dependencia"
    assert graficos["piramide"].piramide is not None
    dependencia = graficos["dependencia"].series[0]
    assert dependencia.tracejado_desde == date(2023, 1, 1)
    assert dependencia.pontos[-1][0] == date(2070, 1, 1)
    assert "crescimento-decomposto" in graficos and "inss" in graficos
    onu = graficos["populacao-onu"]
    assert [s.id for s in onu.series] == ["ibge", "onu"]
    assert onu.intervalos[0].serie == "onu" and len(onu.intervalos[0].pontos) == 8
    assert len(graficos["idosos-paises"].series) == 6
    assert "por-hora" in [s.id for s in graficos["produtividade"].series]
    hora = next(c for c in secao.cartoes if c.id == "produtividade-hora")
    assert hora.procedencia == "calculado" and len(hora.detalhe) <= 60

    # servidores e militares: R$ 60 bi e R$ 48 bi de déficit, PIB de R$ 12 tri no ano
    uniao = next(c for c in secao.cartoes if c.id == "deficit-servidores-militares")
    assert uniao.valor == pytest.approx(0.9) and uniao.referencia == date(2025, 1, 1)
    assert len(uniao.detalhe) <= 60
    prev = graficos["previdencia-uniao"]
    assert [s.id for s in prev.series] == ["inss", "civis", "militares"]
    assert prev.series[0].pontos[-1] == (date(2025, 1, 1), 2.5)
    tabela = next(t for t in secao.tabelas if t.id == "previdencia-uniao")
    assert [li.rotulo for li in tabela.linhas] == ["INSS", "Servidores civis da União", "Militares"]
    assert tabela.linhas[1].valores == [40.0, 100.0, 60.0, 0.5]
    assert tabela.linhas[2].valores == [9.0, 57.0, 48.0, 0.4]

    # o custo do envelhecimento
    for id_ in ("inss-ate-2100", "inss-por-pessoa", "trabalhadores-por-idoso"):
        assert id_ in graficos, id_
    assert {"fecundidade-cenarios", "idade-mesma-proporcao", "idade-de-trabalhar-parte"} <= set(
        graficos
    )
    novos = {c.id: c for c in secao.cartoes}
    for id_ in (
        "inss-deficit-2060",
        "inss-por-pessoa",
        "trabalhadores-por-idoso",
        "idade-mesma-proporcao",
        "freio-demografico",
    ):
        assert len(novos[id_].detalhe) <= 60, id_
    assert novos["inss-deficit-2060"].secao == "demografia"
    # ONU: 20 + 26 × 0,5 = 33 idosos por 100 em 2050 → 3,03 por idoso
    assert novos["trabalhadores-por-idoso"].valor == pytest.approx(100 / 33, abs=1e-3)
    faixa = graficos["trabalhadores-por-idoso"].intervalos[0]
    assert faixa.serie == "onu" and len(faixa.pontos) == len(faixa.meio) == 8
    _, baixo, alto = faixa.pontos[0]
    assert baixo < alto  # a ponta de cima de idosos vira a de baixo de pessoas por idoso
    assert [s.id for s in graficos["fecundidade-cenarios"].series] == [
        "ibge",
        "media",
        "constante",
        "reposicao",
        "baixa",
        "alta",
    ]
    assert novos["inss-por-pessoa"].procedencia == "calculado"
    assert novos["idade-mesma-proporcao"].valor > 60

    estados = next(t for t in secao.tabelas if t.id == "demografia-estados")
    assert [linha.rotulo for linha in estados.linhas] == ["Brasil", "São Paulo", "Acre"]
    assert "filho," in secao.resumo or "filhos," in secao.resumo
    secao.model_dump_json()  # o JSON do site sai


def test_sem_o_rtn_a_secao_sai_sem_o_inss(ctx: Contexto, monkeypatch: pytest.MonkeyPatch) -> None:
    def falha() -> dict[str, list[Ponto]]:
        raise tesouro_rtn.FonteForaDoArError("fora do ar")

    monkeypatch.setattr(tesouro_rtn, "serie_historica", falha)
    secao = demografia.montar(ctx)
    assert "deficit-inss" not in [c.id for c in secao.cartoes]
    assert "inss" not in [g.id for g in secao.graficos]


def test_banco_mundial_traduz_o_agregado_sem_codigo_de_tres_letras(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resposta = [
        {"page": 1},
        [
            {"country": {"id": "XD"}, "countryiso3code": "", "date": "2025", "value": 20.0},
            {"country": {"id": "XD"}, "countryiso3code": "", "date": "2024", "value": 19.6},
            {"country": {"id": "BR"}, "countryiso3code": "BRA", "date": "2025", "value": 11.5},
            {"country": {"id": "BR"}, "countryiso3code": "BRA", "date": "2024", "value": None},
        ],
    ]
    monkeypatch.setattr(banco_mundial, "baixar_json", lambda *a, **k: resposta)
    series = banco_mundial.series_dos_paises(["BRA", "HIC"], banco_mundial.IDOSOS, 2024, 2025)
    assert series == {"HIC": [(2024, 19.6), (2025, 20.0)], "BRA": [(2025, 11.5)]}


def test_previdencia_da_uniao_pela_coluna_do_ano_do_relatorio() -> None:
    """O RREO de 2020 traz o ano anterior ao lado; o de 2021, a coluna sem o ano."""

    def item(conta: str, coluna: str, valor: float) -> dict[str, Any]:
        return {"cod_conta": conta, "coluna": coluna, "valor": valor}

    itens = [
        item("RREO4ResultadoRPPSPrevidenciario", "DESPESAS LIQUIDADAS ATÉ O BIMESTRE / 2019", -1),
        item("RREO4ResultadoRPPSPrevidenciario", "DESPESAS LIQUIDADAS ATÉ O BIMESTRE / 2020", -48),
        item("TotalReceitasRPPSPrevidenciario", "PREVISÃO INICIAL", 43),
        item("TotalReceitasRPPSPrevidenciario", "Até o Bimestre / 2020", 39),
        item("RREO4ResultadoRPPSFinanceiro", "DESPESAS LIQUIDADAS ATÉ O BIMESTRE / 2020", -17),
        item("ResultadoInativosMilitares", "DESPESAS LIQUIDADAS ATÉ O BIMESTRE / 2020", -28),
        item("TotalReceitasRPPSFinanceiro", "Até o Bimestre / 2020", 7),
    ]
    p = siconfi.parse_previdencia_uniao(itens, 2020)
    assert p is not None
    assert (p.civis_resultado, p.civis_receita, p.civis_despesa) == (-48, 39, 87)
    assert (p.militares_resultado, p.militares_despesa, p.fcdf_resultado) == (-45, 52, 0)
    sem_ano = [item("RREO4ResultadoRPPSPrevidenciario", "DESPESAS LIQUIDADAS ATÉ O BIMESTRE", -9)]
    assert (
        siconfi.do_ano(
            sem_ano,
            "RREO4ResultadoRPPSPrevidenciario",
            ("DESPESAS LIQUIDADAS ATÉ O BIMESTRE",),
            2021,
        )
        == -9
    )
    assert siconfi.parse_previdencia_uniao(sem_ano, 2021) is None  # sem os militares


def test_soma_do_ano_so_com_os_doze_meses() -> None:
    mensal = _mensal(date(2024, 3, 1), 22, 1.0)
    assert demografia.soma_do_ano(mensal) == {2025: 12.0}
