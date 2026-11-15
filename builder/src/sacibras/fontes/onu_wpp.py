"""ONU, World Population Prospects 2024: a projeção probabilística da população, com as faixas
de 80 % e 95 %.

A API de dados da ONU (`population.un.org/dataportalapi/api/v1/data/...`) pede token desde
2024: testada em 15/11/2026, a lista de países responde, os dados dão HTTP 401. Os arquivos da
página de downloads, não: a lista deles está em `population.un.org/wpp/assets/downloads.json`
(a página é um aplicativo em JavaScript que lê esse arquivo) e o da população total, com as
cinco variantes (95 % de baixo, 80 % de baixo, mediana, 80 % de cima, 95 % de cima), é
`UN_PPP2024_Output_PopTot.xlsx`, de 1 MB, que responde de fora do Brasil em menos de um
segundo. Uma aba por variante, cabeçalho na linha que começa por "Index", uma coluna por ano
(2024 a 2100), em mil pessoas, referência em 1º de julho. Licença CC BY 3.0 IGO.

A faixa vem do método da própria ONU: milhares de futuros sorteados por um modelo
estatístico, e as pontas são os percentis desses futuros (a aba NOTES do arquivo vem vazia;
o método está na página da projeção probabilística da ONU).
"""

from __future__ import annotations

import io
import warnings
from dataclasses import dataclass
from typing import Any

import openpyxl  # type: ignore[import-untyped]

from sacibras.rede import FonteForaDoArError, baixar

URL = (
    "https://population.un.org/wpp/assets/Excel%20Files/2_Indicators%20(Probabilistic)/"
    "EXCEL_FILES/2_Population/UN_PPP2024_Output_PopTot.xlsx"
)
FONTE = "ONU, World Population Prospects 2024 (projeção probabilística)"
EDICAO = 2024
ABAS = {
    "inferior95": "Lower 95",
    "inferior80": "Lower 80",
    "mediana": "Median",
    "superior80": "Upper 80",
    "superior95": "Upper 95",
}


@dataclass(frozen=True)
class Projecao:
    """Por ano, em mil pessoas."""

    mediana: dict[int, float]
    inferior80: dict[int, float]
    superior80: dict[int, float]
    inferior95: dict[int, float]
    superior95: dict[int, float]


def _da_aba(linhas: list[tuple[Any, ...]], pais: int) -> dict[int, float]:
    cabecalho = next((i for i, li in enumerate(linhas[:40]) if li and li[0] == "Index"), None)
    if cabecalho is None:
        raise FonteForaDoArError("ONU: sem a linha de cabeçalho (Index)")
    cab = linhas[cabecalho]
    try:
        col_local = cab.index("Location code")
    except ValueError as erro:
        raise FonteForaDoArError("ONU: sem a coluna Location code") from erro
    anos = {i: int(c) for i, c in enumerate(cab) if isinstance(c, (int, float))}
    for linha in linhas[cabecalho + 1 :]:
        if len(linha) > col_local and linha[col_local] == pais:
            return {
                ano: float(linha[i])
                for i, ano in anos.items()
                if i < len(linha) and isinstance(linha[i], (int, float))
            }
    raise FonteForaDoArError(f"ONU: sem o país {pais}")


def ler_planilha(conteudo: bytes, pais: int = 76) -> Projecao:
    """`pais` é o código numérico da ONU (o ISO 3166 numérico: 76 é o Brasil)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        # Sem read_only: no modo de leitura rápida a planilha diz ter só uma coluna de ano.
        livro = openpyxl.load_workbook(io.BytesIO(conteudo), data_only=True)
    try:
        faltam = [a for a in ABAS.values() if a not in livro.sheetnames]
        if faltam:
            raise FonteForaDoArError(f"ONU: abas que sumiram: {faltam}")
        por_variante = {
            campo: _da_aba(list(livro[aba].iter_rows(values_only=True)), pais)
            for campo, aba in ABAS.items()
        }
    finally:
        livro.close()
    return Projecao(**por_variante)


def populacao(pais: int = 76) -> Projecao:
    return ler_planilha(baixar(URL, validade=30 * 24 * 3600, tempo_limite=120), pais)
