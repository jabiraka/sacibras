"""O custo, os prazos e os riscos fiscais da dívida: as planilhas do BC lidas com dados
fabricados, as contas novas e os números lidos à mão conferidos contra o próprio anexo."""

from __future__ import annotations

import io
from datetime import date
from typing import Any

import openpyxl  # type: ignore[import-untyped]
import pytest

from sacibras import relatorios
from sacibras.fontes import bcb_fiscal
from sacibras.modelos import divida
from sacibras.secoes import fiscal, riscos


def _planilha(aba: str, linhas: list[list[Any]]) -> bytes:
    livro = openpyxl.Workbook()
    folha = livro.active
    folha.title = aba
    for linha in linhas:
        folha.append(linha)
    saida = io.BytesIO()
    livro.save(saida)
    return saida.getvalue()


# O desenho das tabelas especiais: o ano só em algumas colunas (às vezes no meio do ano), o
# mês duas linhas abaixo, rótulos com espaços e nota de rodapé.
CABECALHO = [
    ["Dívida bruta do governo geral"],
    ["Taxa de juros implícita - Taxa acumulada em doze meses"],
    [],
    ["Discriminação", None, 2025, 2026, None, 2026],
    [],
    [None, None, "Novembro", "Dezembro", "Janeiro", "Fevereiro"],
]


def test_taxa_implicita_le_as_datas_em_sequencia() -> None:
    # A primeira coluna (nov) leva o ano 2025; o "2026" de dezembro é rótulo deslocado.
    cabecalho = [list(x) for x in CABECALHO]
    cabecalho[3] = ["Discriminação", None, 2025, None, 2026, None]
    conteudo = _planilha(
        "DBGG_12meses",
        [
            *cabecalho,
            [],
            ["Dívida bruta total", None, 12.5, 12.7, "-  ", 13.0],
            ["   Governo Federal1/", None, 1.0, 1.0, 1.0, 1.0],
        ],
    )
    assert bcb_fiscal.ler_taxa_implicita(conteudo) == [
        (date(2025, 11, 1), 12.5),
        (date(2025, 12, 1), 12.7),
        (date(2026, 2, 1), 13.0),
    ]


def test_taxa_implicita_recusa_mes_fora_da_sequencia() -> None:
    cabecalho = [list(x) for x in CABECALHO]
    cabecalho[5] = [None, None, "Novembro", "Janeiro", "Fevereiro", "Março"]
    conteudo = _planilha("DBGG_12meses", [*cabecalho, ["Dívida bruta total", None, 1, 2, 3, 4]])
    with pytest.raises(bcb_fiscal.PlanilhaMudouError):
        bcb_fiscal.ler_taxa_implicita(conteudo)


def test_cronograma_le_so_o_bloco_do_governo_geral() -> None:
    faixas = [
        "até 1 ano",
        "entre 1 e 3 anos",
        "entre 3 e 5 anos",
        "entre 5 e 10 anos",
        "entre 10 e 20 anos",
        "após 20 anos",
    ]

    def bloco(total: float) -> list[list[Any]]:
        return [
            ["  Dívida bruta total", None, total, total, total, total],
            *[[f"     Vencimento {f}", None, 10.0, 10.0, 10.0, 10.0] for f in faixas],
        ]

    conteudo = _planilha(
        "Cronograma_DBGG",
        [*CABECALHO, [], *bloco(100.0), ["Governo Federal1/"], *bloco(90.0)],
    )
    total, por_faixa = bcb_fiscal.ler_cronograma(conteudo)
    assert total[-1] == (date(2026, 2, 1), 100.0)
    assert set(por_faixa) == set(faixas)
    assert divida.parcela(por_faixa["até 1 ano"], total)[0][1] == pytest.approx(10.0)


def test_prazos_da_divida_somam_cem_e_juntam_as_faixas_longas() -> None:
    d = date(2026, 9, 1)
    faixas = {
        "até 1 ano": [(d, 30.0)],
        "entre 1 e 3 anos": [(d, 20.0)],
        "entre 3 e 5 anos": [(d, 20.0)],
        "entre 5 e 10 anos": [(d, 15.0)],
        "entre 10 e 20 anos": [(d, 10.0)],
        "após 20 anos": [(d, 5.0)],
    }
    partes = fiscal.prazos_da_divida([(d, 100.0)], faixas)
    assert sum(p[0][1] for p in partes.values()) == pytest.approx(100.0)
    assert partes["mais-de-10"][0][1] == pytest.approx(15.0)


def test_juros_sobre_receita_soma_doze_meses_seguidos() -> None:
    meses = [date(2025 + (m // 12), m % 12 + 1, 1) for m in range(14)]
    juros = [(d, 10.0) for d in meses]
    receita = [(d, 40.0) for d in meses]
    saida = divida.juros_sobre_receita(juros, receita)
    # Os 12 primeiros meses fecham a primeira soma; daí, um ponto por mês.
    assert [d for d, _ in saida] == meses[11:]
    assert saida[0][1] == pytest.approx(25.0)
    # Mês faltando na receita: não há soma curta.
    sem_um = [p for p in receita if p[0] != meses[5]]
    assert divida.juros_sobre_receita(juros, sem_um) == []


def test_diferenca_de_conceito_no_ano_mais_novo_em_comum() -> None:
    fmi = {2023: 84.0, 2024: 87.0, 2025: 93.3, 2026: 97.0}
    bc = {2023: 73.8, 2024: 76.3, 2025: 78.6}
    assert divida.diferenca_de_conceito(fmi, bc, ate=2025) == (2025, pytest.approx(14.7))
    assert divida.diferenca_de_conceito(fmi, bc, ate=2024) == (2024, pytest.approx(10.7))
    assert divida.diferenca_de_conceito(fmi, {}, ate=2025) is None


def test_tabela_de_governanca_brasil_primeiro_e_faixa_na_nota() -> None:
    dados: dict[tuple[str, str], dict[int, float]] = {
        ("BRA", "GOV_WGI_GE.SC"): {2015: 53.2, 2025: 51.6},
        ("BRA", "GOV_WGI_RL.SC"): {2015: 55.2, 2025: 50.6},
        ("BRA", "GOV_WGI_GE.SC_LB"): {2025: 44.2},
        ("BRA", "GOV_WGI_GE.SC_UB"): {2025: 59.0},
        ("BRA", "GOV_WGI_RL.SC_LB"): {2025: 46.5},
        ("BRA", "GOV_WGI_RL.SC_UB"): {2025: 54.7},
        ("CHL", "GOV_WGI_GE.SC"): {2025: 73.7},
    }
    nomes = {iso: iso for iso in riscos.PARES_DE_GOVERNANCA}
    tabela = riscos.tabela_de_governanca(dados, nomes)
    assert tabela is not None
    assert [x.rotulo for x in tabela.linhas] == ["Brasil, 2025", "Brasil, 2015", "CHL"]
    assert tabela.linhas[0].valores[:2] == [52.0, 51.0]
    assert "de 44 a 59" in tabela.nota
    assert riscos.tabela_de_governanca({}, nomes) is None


def test_numeros_do_anexo_de_riscos_conferem_com_o_texto() -> None:
    # Tabela 26: "Total 2.273,2" em 2025 e "2.660,4" em 2024.
    assert sum(relatorios.ACOES_JUDICIAIS[2025]) == pytest.approx(2273.2)
    assert sum(relatorios.ACOES_JUDICIAIS[2024]) == pytest.approx(2660.5, abs=0.2)
    # Tabela 27: "Percentual da Despesa Primária Total ... 3,2% 4,2% 4,6%".
    for ano, esperado in [(2023, 7.1), (2024, 3.2), (2025, 4.2), (2026, 4.6)]:
        pago, despesa = relatorios.SENTENCAS_PAGAS[ano]
        assert pago / despesa * 100 == pytest.approx(esperado, abs=0.05)
    # Tabela 2: as linhas usadas batem com a tabela 26.
    possivel, provavel = relatorios.RISCOS_FISCAIS[0], relatorios.RISCOS_FISCAIS[1]
    assert (possivel.ultimo, provavel.ultimo) == relatorios.ACOES_JUDICIAIS[2025]


def test_projecao_do_inss_fecha_receita_menos_despesa() -> None:
    for receita, despesa, necessidade in relatorios.RGPS_PROJECAO.values():
        assert despesa - receita == pytest.approx(necessidade, abs=0.015)
