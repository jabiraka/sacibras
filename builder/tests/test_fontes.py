"""As fontes sem rede: a resposta de cada API é um trecho real, colado aqui."""

from datetime import date
from typing import Any

import pytest

from sacibras.catalogo import SGS
from sacibras.fontes import b3_indices, bcb_focus, bcb_sgs, ibge_sidra


@pytest.fixture
def respostas(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Troca `baixar_json` das fontes por um dicionário {trecho da URL: resposta}."""
    mapa: dict[str, Any] = {}
    pedidos: list[str] = []

    def falso(url: str, **kw: Any) -> Any:
        pedidos.append(url)
        for trecho, resposta in mapa.items():
            if trecho in url:
                return resposta
        raise AssertionError(f"URL inesperada: {url}")

    for modulo in (bcb_sgs, bcb_focus, ibge_sidra, b3_indices):
        monkeypatch.setattr(modulo, "baixar_json", falso)
    mapa["__pedidos__"] = pedidos
    return mapa


def test_sgs_ordena_por_data_e_pula_valor_vazio(respostas: dict[str, Any]) -> None:
    # Alguns códigos do SGS voltam em ordem decrescente (visto em 14/11/2026).
    respostas["bcdata.sgs.13762"] = [
        {"data": "01/09/2026", "valor": "82.95"},
        {"data": "01/08/2026", "valor": ""},
        {"data": "01/07/2026", "valor": "82.55"},
    ]
    pontos = bcb_sgs.ler(SGS["DBGG"], date(2026, 1, 1), date(2026, 11, 14))
    assert pontos == [(date(2026, 7, 1), 82.55), (date(2026, 9, 1), 82.95)]


def test_sgs_serie_diaria_longa_vai_em_janelas(respostas: dict[str, Any]) -> None:
    respostas["bcdata.sgs.432"] = [{"data": "02/01/2020", "valor": "4.5"}]
    bcb_sgs.ler(SGS["SELIC_META"], date(2006, 1, 1), date(2026, 11, 14))
    assert len(respostas["__pedidos__"]) == 3  # 20 anos em janelas de 9


def test_catalogo_nao_repete_codigo() -> None:
    codigos = [s.codigo for s in SGS.values()]
    assert len(codigos) == len(set(codigos))
    assert SGS["NUCLEO_EX0"].codigo == 11427  # e não 16121, que é o EX1


def test_focus_consulta_com_espaco_codificado_e_pega_a_ultima_edicao(
    respostas: dict[str, Any],
) -> None:
    respostas["ExpectativasMercadoAnuais"] = {
        "value": [
            {"Data": "2026-11-06", "DataReferencia": "2026", "Mediana": 5.2195},
            {"Data": "2026-11-06", "DataReferencia": "2027", "Mediana": 4.9005},
            {"Data": "2026-10-30", "DataReferencia": "2026", "Mediana": 5.2166},
        ]
    }
    assert bcb_focus.mediana_anual_hoje("IPCA") == {2026: 5.2195, 2027: 4.9005}
    url = respostas["__pedidos__"][0]
    assert "+" not in url and "Indicador%20eq%20%27IPCA%27" in url  # a Olinda recusa "+"


def test_focus_selic_ordena_as_reunioes_no_cliente(respostas: dict[str, Any]) -> None:
    # A API ordena texto: "R1/2027" viria antes de "R8/2026".
    respostas["ExpectativasMercadoSelic"] = {
        "value": [
            {"Data": "2026-11-06", "Reuniao": "R1/2027", "Mediana": 13.75},
            {"Data": "2026-11-06", "Reuniao": "R8/2026", "Mediana": 13.75},
            {"Data": "2026-11-06", "Reuniao": "R2/2027", "Mediana": 13.5},
        ]
    }
    _, pares = bcb_focus.selic_por_reuniao()
    assert [r for r, _ in pares] == ["R8/2026", "R1/2027", "R2/2027"]


def test_sidra_le_trimestre_e_ignora_sem_dado(respostas: dict[str, Any]) -> None:
    respostas["t/5932"] = [
        {"V": "Valor", "D2C": "Variável (Código)", "D3C": "Trimestre (Código)",
         "D4C": "Setores e subsetores (Código)"},
        {"V": "0.5", "D2C": "6564", "D3C": "202602", "D4C": "90707"},
        {"V": "...", "D2C": "6564", "D3C": "202603", "D4C": "90707"},
        {"V": "-0.4", "D2C": "6564", "D3C": "202602", "D4C": "93404"},
    ]  # fmt: skip
    series = ibge_sidra.series(
        5932, 6564, classificacao="c11255/90707,93404", por="Setores", trimestral=True
    )
    assert series == {"90707": [(date(2026, 4, 1), 0.5)], "93404": [(date(2026, 4, 1), -0.4)]}


def test_sidra_trimestre_movel_e_mensal(respostas: dict[str, Any]) -> None:
    respostas["t/6381"] = [
        {"V": "Valor", "D2C": "Variável (Código)", "D3C": "Trimestre Móvel (Código)"},
        {"V": "5.2", "D2C": "4099", "D3C": "202609"},
    ]
    assert ibge_sidra.serie(6381, 4099) == [(date(2026, 9, 1), 5.2)]


def test_indices_b3_leem_a_grade_dia_por_mes(respostas: dict[str, Any]) -> None:
    respostas["GetPortfolioDay"] = {
        "results": [
            {"day": 12, "rateValue11": "171.324,31", "rateValue12": ""},
            {"day": 13, "rateValue11": "172.457,76", "rateValue1": None},
        ]
    }
    assert b3_indices.ano("IBOV", 2026, corrente=True) == [
        (date(2026, 11, 12), 171324.31),
        (date(2026, 11, 13), 172457.76),
    ]
