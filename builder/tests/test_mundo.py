"""Brasil no mundo: hierarquia de grupos do FMI e nomes dos países (sem rede)."""

from __future__ import annotations

from typing import Any

import pytest

from sacibras.fontes import fmi
from sacibras.secoes import mundo


def _no(codigo: str, *filhos: dict[str, Any]) -> dict[str, Any]:
    urn = f"urn:sdmx:org.sdmx.infomodel.codelist.Code=IMF.RES:CL_WEO_COUNTRY(1.0.1).{codigo}"
    return {"id": f"CL_WEO_COUNTRY___{codigo}", "code": urn, "hierarchicalCodes": list(filhos)}


def _resposta(*hierarquias: tuple[str, list[dict[str, Any]]]) -> dict[str, Any]:
    return {
        "data": {
            "hierarchicalCodelists": [
                {"id": id, "agencyID": "IMF.RES", "hierarchies": [{"hierarchicalCodes": nos}]}
                for id, nos in hierarquias
            ]
        }
    }


def test_grupos_achata_subgrupos_e_tira_repetidos() -> None:
    arvore = [
        _no(
            "G001",
            _no("G110", _no("G163", _no("DEU"), _no("FRA")), _no("G119", _no("DEU"), _no("USA"))),
            _no("G200", _no("G205", _no("BRA"), _no("MEX"))),
        )
    ]
    resposta = _resposta(("H_OUTRA", [_no("X", _no("ZZZ"))]), ("H_WEO_COUNTRIES", arvore))
    g = fmi.grupos_da_resposta(resposta)
    assert g["G163"] == ["DEU", "FRA"]
    assert g["G110"] == ["DEU", "FRA", "USA"]  # DEU está em dois subgrupos e aparece uma vez
    assert g["G200"] == ["BRA", "MEX"]
    assert g["G001"] == ["DEU", "FRA", "USA", "BRA", "MEX"]
    assert "DEU" not in g  # país não é grupo
    assert "ZZZ" not in g["G001"]


def test_hierarquia_que_sumiu_levanta_erro_claro() -> None:
    with pytest.raises(RuntimeError, match="H_WEO_COUNTRIES"):
        fmi.grupos_da_resposta(_resposta(("H_OUTRA", [_no("G001", _no("BRA"))])))


def test_nome_de_pais_do_iso() -> None:
    assert mundo.nome_do_pais("DEU") == "Alemanha"
    assert mundo.nome_do_pais("KOR") == "Coreia do Sul"


def test_nome_corrigido_a_mao() -> None:
    assert mundo.nome_do_pais("RUS") == "Rússia"
    assert mundo.nome_do_pais("IRN") == "Irã"
    assert mundo.nome_do_pais("COD") == "RD Congo"


def test_nome_do_kosovo_e_de_codigo_fora_do_iso() -> None:
    assert mundo.nome_do_pais("KOS") == "Kosovo"
    assert mundo.nome_do_pais("WBG") == "Cisjordânia e Gaza"
    with pytest.raises(KeyError):
        mundo.nome_do_pais("XXX")
