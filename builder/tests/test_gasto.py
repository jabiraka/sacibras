"""O gasto: obrigatória e discricionária (RTN) e o Brasil contra os grupos (COFOG)."""

from datetime import date

import pytest

from sacibras.secoes import gasto


def test_brasil_contra_a_mediana_dos_grupos() -> None:
    dados = {
        "BRA": {"GF10_T": {2024: 16.5}, "GF0170_T": {2024: 8.3}, "GF07_T": {2024: 5.0}},
        "TUR": {"GF10_T": {2025: 9.0, 2023: 8.0}, "GF0170_T": {2023: 3.8}, "GF07_T": {2023: 4.0}},
        "ZAF": {"GF10_T": {2024: 5.3}, "GF0170_T": {2024: 0.0}, "GF07_T": {2024: 5.0}},
        "IND": {"GF10_T": {2019: 2.0}},  # velho demais: fica fora
        "DEU": {"GF10_T": {2024: 19.5}, "GF0170_T": {2024: 0.9}, "GF07_T": {2024: 7.6}},
    }
    grupos = {"G200": ["BRA", "TUR", "ZAF", "IND"], "G205": ["BRA"], "G110": ["DEU"]}
    cartoes, [tabela] = gasto.contra_os_paises(dados, grupos)  # type: ignore[arg-type]
    assert tabela.colunas[:4] == ["Brasil", "Emergentes (2)", "América Latina (0)", "Avançados (1)"]
    linha = {li.rotulo.strip(): li.valores for li in tabela.linhas}
    # Turquia vale pelo ano mais novo até 2024 (8,0, não o de 2025); a mediana de 8,0 e 5,3.
    assert linha["Proteção social"][:2] == [16.5, pytest.approx(6.65, abs=0.05)]
    # Na subfunção, o zero da África do Sul é "não abriu", e sai da mediana.
    assert linha["dos quais: juros da dívida"][1] == 3.8
    assert cartoes[0].id == "gasto-acima-pares" and cartoes[0].valor == pytest.approx(9.85)
    assert "proteção social" in cartoes[0].detalhe


def test_rigidez_separa_e_soma() -> None:
    meses = [date(2024 + i // 12, i % 12 + 1, 1) for i in range(24)]

    def fixo(v: float) -> list[tuple[date, float]]:
        return [(d, v) for d in meses]

    rtn = {
        "rgps": fixo(80.0),
        "pessoal": fixo(40.0),
        "outras_obrigatorias": fixo(30.0),
        "bpc": fixo(10.0),
        "abono_seguro": fixo(5.0),
        "obrigatorias_fluxo": fixo(25.0),
        "discricionarias": fixo(25.0),
        "despesa_total": fixo(200.0),
    }
    pib = [(d, 12 * 1000.0) for d in meses]
    cartoes, graficos, [tabela] = gasto.rigidez(rtn, pib, "teste", date(2020, 1, 1))
    parte = {c.id: c for c in cartoes}["discricionaria-parte"]
    assert parte.valor == pytest.approx(12.5)
    assert sum(li.valores[1] for li in tabela.linhas) == pytest.approx(100.0)  # type: ignore[misc]
    assert graficos[0].series[0].pontos[-1][1] == pytest.approx(175 * 12 / 12000 * 100)
