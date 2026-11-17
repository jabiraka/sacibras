"""O leitor da aba 1.1 do RTN, sem rede: a planilha é montada aqui, com openpyxl."""

import io
from datetime import date, datetime

import openpyxl
import pytest

from sacibras.fontes import tesouro_rtn
from sacibras.fontes.tesouro_rtn import LinhaSumiuError, ler_aba, normalizar

MESES = [datetime(2026, 5, 1), datetime(2026, 6, 1), datetime(2026, 7, 1)]

LINHAS = [
    ("1. RECEITA TOTAL 1/", [300.0, 310.0, 320.0]),
    ("1.1 -  Receita Administrada pela RFB", [1.0, 1.0, 1.0]),
    ("1.3 -  Arrecadação Líquida para o RGPS", [60.0, 61.0, 62.0]),
    ("3. RECEITA LÍQUIDA  (1-2)", [200.0, 210.0, 220.0]),
    ("4. DESPESA TOTAL", [190.0, None, 215.0]),  # junho vazio
    ("4.1  Benefícios Previdenciários ", [80.0, 81.0, 82.0]),
    ("4.2  Pessoal e Encargos Sociais", [40.0, 41.0, 42.0]),
    ("4.3  Outras Despesas Obrigatórias", [30.0, 30.0, 30.0]),
    ("4.3.01 Abono e Seguro Desemprego", [8.0, 8.0, 8.0]),
    ("4.3.05  Benefícios de Prestação Continuada da LOAS/RMV", [9.0, 9.0, 9.0]),
    ("4.4.1 Obrigatórias com Controle de Fluxo", [25.0, 25.0, 25.0]),
    ("4.4.2 Despesas Discricionárias", [15.0, 15.0, 16.0]),
    ("5. RESULTADO PRIMÁRIO GOVERNO CENTRAL - ACIMA DA LINHA (3 - 4)", [10.0, 0.0, 5.0]),
]


def _planilha(linhas: list[tuple[str, list[float | None]]], aba: str = "1.1") -> bytes:
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = "Índice"
    ws = livro.create_sheet(aba)
    ws["A1"] = "Voltar"
    ws["A2"] = "Tabela 1.1. Resultado Primário do Governo Central"
    ws["A3"] = "R$ Milhões - Valores Correntes"
    ws.append([])  # linha 4 em branco; o cabeçalho é a 5
    ws.append(["Discriminação", *MESES])
    for rotulo, valores in linhas:
        ws.append([rotulo, *valores])
    ws.append(["Obs.: Dados sujeitos à alteração."])
    saida = io.BytesIO()
    livro.save(saida)
    return saida.getvalue()


def test_normalizar_tira_numeracao_acento_e_nota() -> None:
    assert normalizar("4.1  Benefícios Previdenciários ") == "beneficios previdenciarios"
    assert normalizar("IV.1 Pessoal e Encargos Sociais") == "pessoal e encargos sociais"
    assert normalizar("1. RECEITA TOTAL 1/") == "receita total"
    assert normalizar("3. RECEITA LÍQUIDA  (1-2)") == "receita liquida (1-2)"
    assert normalizar("1.3 -  Arrecadação Líquida para o RGPS") == "arrecadacao liquida para o rgps"


def test_le_as_linhas_pelo_rotulo_e_pula_mes_vazio() -> None:
    dados = ler_aba(_planilha(LINHAS))
    assert set(dados) == {
        "receita_liquida",
        "receita_rfb",
        "despesa_total",
        "arrecadacao_rgps",
        "rgps",
        "pessoal",
        "outras_obrigatorias",
        "abono_seguro",
        "bpc",
        "obrigatorias_fluxo",
        "discricionarias",
        "primario",
    }
    assert dados["arrecadacao_rgps"][-1] == (date(2026, 7, 1), 62.0)
    assert dados["receita_liquida"][-1] == (date(2026, 7, 1), 220.0)
    assert dados["rgps"][0] == (date(2026, 5, 1), 80.0)
    assert dados["despesa_total"] == [(date(2026, 5, 1), 190.0), (date(2026, 7, 1), 215.0)]
    # Zero é dado, não vazio.
    assert (date(2026, 6, 1), 0.0) in dados["primario"]


def test_ordem_das_linhas_nao_importa() -> None:
    dados = ler_aba(_planilha(list(reversed(LINHAS))))
    assert dados["pessoal"][-1] == (date(2026, 7, 1), 42.0)


def test_rotulo_que_sumiu_levanta_erro_claro() -> None:
    sem_pessoal = [(r, v) for r, v in LINHAS if "Pessoal" not in r]
    with pytest.raises(LinhaSumiuError, match="pessoal e encargos sociais"):
        ler_aba(_planilha(sem_pessoal))


def test_aba_que_sumiu_levanta_erro_claro() -> None:
    with pytest.raises(LinhaSumiuError, match="aba"):
        ler_aba(_planilha(LINHAS, aba="9.9"))


def test_endereco_pega_o_xlsx_mais_recente(monkeypatch: pytest.MonkeyPatch) -> None:
    resposta = {
        "result": {
            "resources": [
                {
                    "format": "XLSX",
                    "url": "https://x/seriehistoricajun26.xlsx",
                    "last_modified": "2026-07-27T10:00:00",
                },
                {
                    "format": "XLSX",
                    "url": "https://x/seriehistoricajul26.xlsx",
                    "last_modified": "2026-08-27T10:00:00",
                },
                {"format": "PDF", "url": "https://x/nota.pdf", "last_modified": "2026-09-01"},
            ]
        }
    }
    monkeypatch.setattr(tesouro_rtn, "baixar_json", lambda url, **kw: resposta)
    assert tesouro_rtn.endereco_da_serie_historica().endswith("seriehistoricajul26.xlsx")


def test_primario_por_quem_mede_poe_bc_e_fmi_nos_mesmos_anos() -> None:
    from datetime import date

    from sacibras.secoes.fiscal import primario_por_quem_mede

    bc = [(date(a, m, 1), -0.5) for a in range(2018, 2027) for m in (6, 12)]
    gc = [(date(a, 12, 1), -0.4) for a in range(2018, 2026)]
    fmi = {a: -0.2 for a in range(2016, 2031)}
    t = primario_por_quem_mede(bc, gc, fmi, 2026)
    assert t is not None
    assert t.colunas == [str(a) for a in range(2019, 2026)]
    assert [len(linha.valores) for linha in t.linhas] == [7, 7, 7]
    assert primario_por_quem_mede(bc[:2], gc, fmi, 2026) is None
