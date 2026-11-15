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


def test_baixar_json_tenta_de_novo_quando_vem_html(monkeypatch: pytest.MonkeyPatch) -> None:
    # O SGS às vezes devolve uma página HTML no meio de uma rodada boa (14/11/2026).
    from sacibras import rede

    respostas = iter([b"<?xml version='1.0'?><html>erro</html>", b'[{"valor": "4.63"}]'])
    monkeypatch.setattr(rede, "baixar", lambda url, **kw: next(respostas))
    monkeypatch.setattr(rede.time, "sleep", lambda s: None)
    assert rede.baixar_json("https://exemplo") == [{"valor": "4.63"}]


def test_secundario_le_so_a_ntnb_inteira_com_negocios_bastantes() -> None:
    import io
    import zipfile
    from datetime import date

    from sacibras.fontes import bcb_secundario

    cabecalho = (
        "DATA MOV;SIGLA;CODIGO;CODIGO ISIN;EMISSAO;VENCIMENTO;NUM DE OPER;QUANT NEGOCIADA;"
        "VALOR NEGOCIADO;PU MIN;PU MED;PU MAX;PU LASTRO;VALOR PAR;TAXA MIN;TAXA MED;TAXA MAX;"
        "NUM OPER COM CORRETAGEM;QUANT NEG COM CORRETAGEM"
    )
    linhas = [
        # a NTN-B inteira, com negócios: entra
        "13/11/2026;NTN-B;760199;X;10/01/2018;15/08/2028;907;1;;1;4748,59861900;1;1;"
        "4766,33511200;;;;0;0",
        # cupom destacado (760197), poucos negócios (3) e outro título: ficam de fora
        "13/11/2026;NTN-B;760197;X;15/08/2004;15/05/2028;30;1;;1;129,36;1;1;;;;;0;0",
        "13/11/2026;NTN-B;760199;X;10/01/2018;15/05/2027;3;1;;1;4961,86;1;1;4766,33;;;;0;0",
        "13/11/2026;LFT;210100;X;03/07/2020;01/03/2027;376;1;;1;20212,06;1;1;20211,30;;;;0;0",
    ]
    corpo = io.BytesIO()
    with zipfile.ZipFile(corpo, "w") as pacote:
        pacote.writestr("NegT202611.CSV", "\n".join([cabecalho, *linhas]).encode("latin-1"))
    por_dia = bcb_secundario.ler(corpo.getvalue())
    assert list(por_dia) == [date(2026, 11, 13)]
    (negocio,) = por_dia[date(2026, 11, 13)]
    assert negocio.vencimento == date(2028, 8, 15)
    assert negocio.pu_medio == 4748.598619
    assert negocio.valor_par == 4766.335112
    assert negocio.operacoes == 907


def test_secundario_sem_negocio_no_dia_fica_com_o_do_ultimo_dia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import date

    from sacibras.fontes import bcb_secundario
    from sacibras.fontes.bcb_secundario import Negocio

    v27, v28 = date(2027, 5, 15), date(2028, 8, 15)
    por_dia = {
        date(2026, 11, 12): [Negocio(v27, 4950.0, 4766.0, 50), Negocio(v28, 4740.0, 4766.0, 80)],
        date(2026, 11, 13): [Negocio(v28, 4748.0, 4766.0, 90)],  # a de 2027 não negociou
        date(2026, 11, 16): [Negocio(v27, 4999.0, 4773.0, 70)],  # depois do alvo: não entra
    }
    monkeypatch.setattr(bcb_secundario, "baixar", lambda *a, **k: b"")
    monkeypatch.setattr(bcb_secundario, "ler", lambda corpo: por_dia)
    recentes = bcb_secundario.ntnb_recentes(date(2026, 11, 13))
    assert [(d, n.vencimento, n.pu_medio) for d, n in recentes] == [
        (date(2026, 11, 12), v27, 4950.0),
        (date(2026, 11, 13), v28, 4748.0),
    ]
