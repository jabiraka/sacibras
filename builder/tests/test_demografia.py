"""Demografia sem rede: as planilhas da projeção montadas aqui, e as séries trocadas por
números de mentira."""

import io
import math
from datetime import date
from typing import Any

import openpyxl
import pytest

from sacibras.fontes import ibge_projecao, ibge_sidra, tesouro_rtn
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
