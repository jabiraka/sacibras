"""Brasil no mundo: hierarquia de grupos do FMI e nomes dos países (sem rede)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from sacibras.fontes import bis, fmi, ocde_juros, pwt
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


# ---- câmbio no ano, juro de 10 anos e as leituras do BIS e da OCDE


def test_variacao_da_moeda_no_ano_contra_o_dolar() -> None:
    real = {
        "BRL": [
            (date(2024, 12, 1), 6.0),
            (date(2025, 6, 1), 5.6),
            (date(2025, 12, 1), 5.0),
            (date(2026, 10, 1), 5.5),
        ]
    }
    # 2025: a cotação caiu de 6 para 5, o real ganhou 20 %; 2026, até outubro, perdeu 1/11.
    assert mundo.variacao_no_ano(real, [2024, 2025, 2026]) == [None, 20.0, -9.09]


def test_ano_da_troca_de_moeda_fica_em_branco() -> None:
    croacia = {
        "HRK": [(date(2021, 12, 1), 6.6), (date(2022, 12, 1), 7.0)],
        "EUR": [(date(2023, 1, 1), 0.93), (date(2023, 12, 1), 0.9), (date(2024, 12, 1), 0.96)],
    }
    assert mundo.variacao_no_ano(croacia, [2022, 2023, 2024]) == [-5.71, None, -6.25]


def test_juro_de_10_anos_do_brasil_pelo_titulo_mais_perto_de_10_anos() -> None:
    d1, d2, d3 = date(2026, 10, 1), date(2026, 10, 2), date(2026, 11, 3)
    curvas = {
        # 4 anos (fora da faixa), 9 e 12 anos: o de 9 anos é o mais perto de 10.
        d1: [(date(2030, 10, 1), 13.0), (date(2035, 10, 1), 14.0), (date(2038, 10, 1), 15.0)],
        d2: [(date(2035, 10, 1), 14.5), (date(2038, 10, 1), 15.0)],
        # Só títulos curtos: o dia fica de fora.
        d3: [(date(2029, 1, 1), 14.0)],
    }
    assert mundo.juro_10_anos_brasil(curvas) == [(date(2026, 10, 1), 14.25)]


def test_le_o_cambio_do_bis_por_moeda() -> None:
    texto = (
        "FREQ,REF_AREA,CURRENCY,COLLECTION,TIME_PERIOD,OBS_VALUE\n"
        "M,BR,BRL,E,2025-12,5.4778\n"
        "M,BR,BRL,E,2025-11,5.3\n"
        "M,HR,HRK,E,2022-12,7.0\n"
        "M,HR,EUR,E,2023-01,0.93\n"
        "M,XX,XXX,E,2023-01,NaN\n"
    )
    lido = bis.ler_cambio(texto)
    assert lido["BR"] == {"BRL": [(date(2025, 11, 1), 5.3), (date(2025, 12, 1), 5.4778)]}
    assert set(lido["HR"]) == {"HRK", "EUR"}
    assert "XX" not in lido


def test_le_o_juro_longo_da_ocde() -> None:
    texto = (
        "DATAFLOW,REF_AREA,FREQ,MEASURE,TIME_PERIOD,OBS_VALUE\n"
        "x,USA,M,IRLT,2026-10,4.06\n"
        "x,USA,M,IRLT,2026-09,4.12\n"
        "x,EA20,M,IRLT,2026-10,\n"
    )
    assert ocde_juros.ler(texto) == {"USA": [(date(2026, 9, 1), 4.12), (date(2026, 10, 1), 4.06)]}


def test_metricas_da_pwt_por_pais_e_sem_os_anos_que_a_pwt_nao_tem() -> None:
    ano = {"rgdpo": 4000.0, "emp": 100.0, "avh": 2000.0, "cn": 17_000.0, "hc": 3.3}
    dados: pwt.PorPais = {
        "BRA": {2022: ano | {"ctfp": 0.5, "labsh": 0.51}, 2023: ano | {"ctfp": 0.497}},
        "USA": {2023: {"rgdpo": 9000.0, "emp": 50.0, "ctfp": 1.0}},
    }
    metricas = {
        m.id: m for m in mundo.metricas_pwt(dados, ["BRA", "USA", "G001"], [2022, 2023, 2024])
    }
    ptf = metricas["ptf"]
    assert ptf.anos == [2022, 2023] and ptf.valores == {"BRA": [50.0, 49.7], "USA": [None, 100.0]}
    assert "vai até 2023" in ptf.descricao and "CC BY 4.0" in ptf.fonte
    # US$ por hora: 4000 milhões / (100 milhões de pessoas × 2000 horas) = US$ 0,02
    assert metricas["produtividade_hora"].valores == {"BRA": [0.02, 0.02]}
    assert metricas["capital_ocupado"].valores["BRA"] == [0.17, 0.17]
    parte = metricas["parte_trabalho"]
    assert parte.anos == [2022] and parte.valores == {"BRA": [51.0]}
    assert "G001" not in ptf.valores  # a PWT não tem os grupos do FMI


def test_reservas_do_banco_mundial_por_ano() -> None:
    from sacibras.fontes import banco_mundial

    linhas = [
        {"countryiso3code": "BRA", "date": "2025", "value": 8.42},
        {"countryiso3code": "BRA", "date": "2024", "value": 7.95},
        {"countryiso3code": "MEX", "date": "2025", "value": None},
        {"countryiso3code": "", "date": "2025", "value": 1.0},
    ]
    assert banco_mundial.por_ano(linhas, [2024, 2025]) == {"BRA": [7.95, 8.42]}
