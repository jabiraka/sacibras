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
    pwt,
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


def _ano_pwt(a: int) -> dict[str, float]:
    """Um país que cresce 3 % ao ano, com a PTF subindo até 1980 e caindo depois."""
    t = a - 1954
    return {
        "rgdpna": 100 * 1.03**t,
        "rnna": 300 * 1.04**t,
        "emp": 20 * 1.02**t,
        "avh": 2000.0,
        "hc": 2 * 1.005**t,
        "labsh": 0.6 if a < 2021 else 0.5,
        "rtfpna": 1 + 0.01 * min(t, 26) - 0.005 * max(0, t - 26),
        "ctfp": 0.5 + 0.01 * min(t, 26) - 0.004 * max(0, t - 26),
    }


def _pwt() -> pwt.PorPais:
    return {cod: {a: _ano_pwt(a) for a in range(1954, 2024)} for cod in demografia.PAISES_PTF}


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
    monkeypatch.setattr(pwt, "dados", lambda paises=None: _pwt())
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

    estados = next(t for t in secao.tabelas if t.id == "demografia-estados")
    assert [linha.rotulo for linha in estados.linhas] == ["Brasil", "São Paulo", "Acre"]
    assert "filho," in secao.resumo or "filhos," in secao.resumo

    # A PWT: o pico da PTF relativa é 1980, e a tabela vai década a década.
    ptf_eua = next(c for c in secao.cartoes if c.id == "ptf-eua")
    assert ptf_eua.referencia == date(2023, 1, 1) and ptf_eua.detalhe == "76 % em 1980, o auge"
    assert len(graficos["ptf-paises"].series) == 6
    assert "CC BY 4.0" in graficos["ptf-brasil"].fonte and not graficos["ptf-brasil"].sem_download
    contabil = next(t for t in secao.tabelas if t.id == "pwt-contabilidade")
    assert (
        contabil.linhas[0].rotulo == "1955 a 1960" and contabil.linhas[-1].rotulo == "2021 a 2023"
    )
    assert "parte do trabalho na renda de 2021 em 2022 e 2023" in contabil.nota
    secao.model_dump_json()  # o JSON do site sai


def test_contabilidade_soma_o_pib_e_bate_com_a_ptf_da_pwt() -> None:
    """Com a PTF da fonte feita pela mesma conta, o resto é ela, e as partes somam o PIB."""
    anos: dict[int, dict[str, float]] = {}
    for a in range(2000, 2011):
        t = a - 2000
        y = {"rnna": 300 * 1.04**t, "emp": 20 * 1.02**t, "avh": 1900.0, "hc": 2 * 1.01**t}
        y["labsh"] = 0.55 + 0.001 * t
        y["rtfpna"] = 1.01**t
        anos[a] = y
    for a in range(2000, 2011):  # o PIB que sai de Y = A · K^(1-α) · (L·hc)^α, ano a ano
        anos[a]["rgdpna"] = 0.0
    anos[2000]["rgdpna"] = 100.0
    for a in range(2001, 2011):
        x, ant = anos[a], anos[a - 1]
        peso = (x["labsh"] + ant["labsh"]) / 2
        crescimento = (
            math.log(x["rtfpna"] / ant["rtfpna"])
            + (1 - peso) * math.log(x["rnna"] / ant["rnna"])
            + peso * math.log(x["emp"] * x["avh"] * x["hc"] / (ant["emp"] * ant["avh"] * ant["hc"]))
        )
        x["rgdpna"] = ant["rgdpna"] * math.exp(crescimento)
    parcelas = demografia.contabilidade(anos)
    assert [p.ano for p in parcelas] == list(range(2001, 2011))
    for p in parcelas:
        assert p.capital + p.horas + p.escolaridade + p.ptf == pytest.approx(p.pib)
        assert p.ptf == pytest.approx(p.ptf_pwt) and p.ptf == pytest.approx(math.log(1.01) * 100)
    decadas = demografia.periodos(parcelas)
    assert [r for r, _ in decadas] == ["2001 a 2010"]
    assert decadas[0][1].horas == pytest.approx(0.0 + 100 * math.log(1.02) * 0.5555, rel=1e-2)


def test_anos_em_que_a_pwt_repete_o_dado() -> None:
    anos = {2019: {"labsh": 0.57}, 2020: {"labsh": 0.54}, 2021: {"labsh": 0.51}}
    anos |= {2022: {"labsh": 0.51}, 2023: {"labsh": 0.51}}
    assert demografia.anos_repetidos(anos, "labsh") == [2022, 2023]
    assert demografia.anos_repetidos({2020: {"labsh": 0.5}, 2021: {"labsh": 0.6}}, "labsh") == []


def test_pwt_le_a_aba_data_e_acha_a_planilha_no_dataverse() -> None:
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = "Data"
    ws.append(["countrycode", "country", "year", "i_irr", *pwt.CAMPOS])
    resto = [6, 7, 0.13, 0.49]  # rgdpo, cn, irr, pl_i
    ws.append(["BRA", "Brazil", 2023, "Regular", 1, 2, 3, 4, 5, 0.5, 0.97, 0.49, *resto])
    ws.append(["BRA", "Brazil", 2022, "Outlier", 1, 2, 3, 4, 5, 0.5, 0.96, None, *resto])
    ws.append(["USA", "United States", 2023, "Regular", 1, 2, 3, 4, 5, 0.6, 1.0, 1.0, *resto])
    saida = io.BytesIO()
    livro.save(saida)
    lido = pwt.ler_planilha(saida.getvalue(), {"BRA"})
    assert set(lido) == {"BRA"}
    assert lido["BRA"][2023]["ctfp"] == 0.49 and "ctfp" not in lido["BRA"][2022]
    # o retorno que a própria PWT marca como "Outlier" não entra
    assert lido["BRA"][2023]["irr"] == 0.13 and "irr" not in lido["BRA"][2022]
    meta = {
        "data": {
            "latestVersion": {
                "files": [
                    {"dataFile": {"id": 1, "filename": "pwt110_na_data.xlsx"}},
                    {"dataFile": {"id": 7, "filename": "pwt110.xlsx"}},
                ]
            }
        }
    }
    assert pwt.id_da_planilha(meta) == 7


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


def _economia(ate: int) -> tuple[dict[int, dict[str, float]], demografia.Insumos]:
    """Uma economia em que a PWT e o IBGE contam a mesma história: capital pelo inventário
    perpétuo (5 % de depreciação), PIB Cobb-Douglas com o trabalho pesando 0,5 e PTF subindo
    1 % ao ano; a PWT vai até 2023 e o IBGE, até `ate`."""
    brasil: dict[int, dict[str, float]] = {}
    pib, fbcf, ocupados, horas, estudo = {}, {}, {}, {}, {}
    capital = 1000.0
    for a in range(2010, ate + 1):
        t = a - 2010
        investimento = 60 * 1.03**t
        capital = 0.95 * capital + investimento
        s = 9.0 + 0.1 * t
        hc = math.exp(demografia.retorno_do_estudo(s))
        emp, avh, ptf = 50 * 1.01**t, 1900 * 0.999**t, 1.01 ** (a - 2021)
        y = ptf * capital**0.5 * (emp * avh * hc) ** 0.5
        pib[a], fbcf[a], ocupados[a], horas[a], estudo[a] = y, investimento, emp, avh, s
        if a <= 2023:
            brasil[a] = {
                "rgdpna": y,
                "rnna": capital,
                "delta": 0.05,
                "labsh": 0.5,
                "hc": hc,
                "rtfpna": ptf,
                "emp": emp,
                "avh": avh,
            }
    return brasil, demografia.Insumos(pib, fbcf, ocupados, horas, estudo)


def test_ptf_estendida_com_o_ibge_segue_a_conta_da_pwt() -> None:
    brasil, insumos = _economia(2025)
    estendida = demografia.estender_ptf(brasil, insumos)
    assert [x.ano for x in estendida] == [2024, 2025]
    for x in estendida:
        assert x.ptf == pytest.approx(100 * 1.01 ** (x.ano - 2021))
        assert x.ptf_ritmo_pwt == pytest.approx(x.ptf)  # o estudo sobe no mesmo ritmo
        p = x.parcela
        assert p.capital + p.horas + p.escolaridade + p.ptf == pytest.approx(p.pib)
    erro, vies, desde = demografia.conferir_ptf(brasil, insumos)
    assert erro == pytest.approx(0, abs=1e-9) and vies == pytest.approx(0, abs=1e-9)
    assert desde == 2012


def test_ptf_estendida_para_onde_falta_numero_do_ibge() -> None:
    brasil, insumos = _economia(2025)
    sem_estudo = insumos._replace(estudo={a: v for a, v in insumos.estudo.items() if a != 2025})
    assert [x.ano for x in demografia.estender_ptf(brasil, sem_estudo)] == [2024]
    assert demografia.estender_ptf(brasil, insumos._replace(pib={})) == []


def test_ano_sem_pnad_de_educacao_fica_na_reta() -> None:
    ins = demografia.Insumos({}, {}, {}, {}, {2019: 9.8, 2022: 10.1})
    assert ins.estudo_em(2020) == pytest.approx(9.9) and ins.estudo_em(2023) is None
    # 4 anos a 13,4 %, 4 a 10,1 % e 2 a 6,8 %
    assert demografia.retorno_do_estudo(10) == pytest.approx(0.536 + 0.404 + 0.136)
