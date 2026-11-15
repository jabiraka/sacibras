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

Da mesma página saem mais três arquivos (testados de fora do Brasil em 15/11/2026):

- `UN_PPP2024_Output_Pop15-64.xlsx` (1 MB): a população de 15 a 64 anos, no formato do de
  população total (uma linha por país, uma coluna por ano, mil pessoas; mais a coluna "Age").
- `UN_PPP2024_Output_Annual_OldAgeDepRatio.xlsx` (29 MB): os idosos para cada 100 pessoas em
  idade de trabalhar, com as mesmas cinco abas da faixa, mas uma linha por país × ano × sexo
  ("Total" são os dois) e uma coluna por recorte de idade ("15-64" é 65+ sobre 15-64).
- `WPP2024_POP_F07_1_DEPENDENCY_RATIOS_BOTH_SEXES.xlsx` (55 MB), da projeção padrão: a mesma
  razão nas variantes determinísticas, uma aba por variante ("Medium variant", "Low variant",
  "High variant", "Constant-fertility", "Instant-replacement"...), uma linha por país × ano,
  coluna "Annual old-age dep. ratio [65+ / 15-64] (%)". As definições das variantes estão na
  metodologia do WPP 2024: baixa e alta, meio filho por mulher abaixo e acima da média;
  fecundidade constante, a de 2023 mantida; reposição imediata, a que repõe a população já.

Os dois grandes se leem no modo rápido do openpyxl, que precisa de `reset_dimensions()` (sem
ele a planilha diz ter uma coluna só), e param depois das linhas do país: uns 25 s no total.
"""

from __future__ import annotations

import io
import warnings
from dataclasses import dataclass
from typing import Any

import openpyxl  # type: ignore[import-untyped]

from sacibras.rede import FonteForaDoArError, baixar

PASTA_PROBABILISTICA = (
    "https://population.un.org/wpp/assets/Excel%20Files/2_Indicators%20(Probabilistic)/"
    "EXCEL_FILES/2_Population"
)
URL = f"{PASTA_PROBABILISTICA}/UN_PPP2024_Output_PopTot.xlsx"
URL_15_64 = f"{PASTA_PROBABILISTICA}/UN_PPP2024_Output_Pop15-64.xlsx"
URL_IDOSOS_POR_100 = f"{PASTA_PROBABILISTICA}/UN_PPP2024_Output_Annual_OldAgeDepRatio.xlsx"
URL_VARIANTES = (
    "https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/"
    "EXCEL_FILES/2_Population/WPP2024_POP_F07_1_DEPENDENCY_RATIOS_BOTH_SEXES.xlsx"
)
FONTE_VARIANTES = "ONU, World Population Prospects 2024 (variantes da projeção)"
COLUNA_IDOSOS = "Annual old-age dep. ratio [65+ / 15-64] (%)"
VARIANTES = {
    "media": "Medium variant",
    "constante": "Constant-fertility",
    "reposicao": "Instant-replacement",
    "baixa": "Low variant",
    "alta": "High variant",
}
"""As abas da F07 lidas: a média e as quatro de fecundidade."""
UM_MES = 30 * 24 * 3600
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
    """Por ano: em mil pessoas (população) ou por 100 (idosos por 100 de 15 a 64)."""

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
    return ler_planilha(baixar(URL, validade=UM_MES, tempo_limite=120), pais)


def populacao_15_64(pais: int = 76) -> Projecao:
    """Pessoas de 15 a 64 anos, em mil, com a faixa."""
    return ler_planilha(baixar(URL_15_64, validade=UM_MES, tempo_limite=120), pais)


def _linhas_do_pais(aba: Any, pais: int) -> tuple[list[str], list[tuple[Any, ...]]]:
    """O cabeçalho (a linha que começa por "Index") e as linhas do país, numa aba aberta no
    modo rápido. As linhas de um país vêm juntas: a leitura para quando elas acabam."""
    aba.reset_dimensions()
    cabecalho: list[str] = []
    linhas: list[tuple[Any, ...]] = []
    col_local = -1
    for linha in aba.iter_rows(values_only=True):
        if not cabecalho:
            if linha and linha[0] == "Index":
                cabecalho = [str(c).strip() if c is not None else "" for c in linha]
                if "Location code" not in cabecalho:
                    raise FonteForaDoArError("ONU: sem a coluna Location code")
                col_local = cabecalho.index("Location code")
            continue
        if len(linha) > col_local and linha[col_local] == pais:
            linhas.append(linha)
        elif linhas:
            break
    if not cabecalho:
        raise FonteForaDoArError("ONU: sem a linha de cabeçalho (Index)")
    if not linhas:
        raise FonteForaDoArError(f"ONU: sem o país {pais}")
    return cabecalho, linhas


def _coluna(cabecalho: list[str], nome: str) -> int:
    if nome not in cabecalho:
        raise FonteForaDoArError(f"ONU: sem a coluna {nome!r}")
    return cabecalho.index(nome)


def _por_ano(
    cabecalho: list[str], linhas: list[tuple[Any, ...]], coluna: str, sexo: str | None = None
) -> dict[int, float]:
    """{ano: valor} das linhas do país (uma por ano; com `sexo`, só as desse sexo)."""
    col_ano, col_valor = _coluna(cabecalho, "Year"), _coluna(cabecalho, coluna)
    col_sexo = _coluna(cabecalho, "Sex") if sexo else -1
    saida: dict[int, float] = {}
    for linha in linhas:
        if sexo and linha[col_sexo] != sexo:
            continue
        ano, valor = linha[col_ano], linha[col_valor]
        if isinstance(ano, (int, float)) and isinstance(valor, (int, float)):
            saida[int(ano)] = float(valor)
    return saida


def _abrir_rapido(conteudo: bytes) -> Any:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)


def ler_idosos_por_100(conteudo: bytes, pais: int = 76) -> Projecao:
    """Idosos (65+) para cada 100 pessoas de 15 a 64 anos, com a faixa (os dois sexos)."""
    livro = _abrir_rapido(conteudo)
    try:
        faltam = [a for a in ABAS.values() if a not in livro.sheetnames]
        if faltam:
            raise FonteForaDoArError(f"ONU: abas que sumiram: {faltam}")
        por_variante = {}
        for campo, aba in ABAS.items():
            cabecalho, linhas = _linhas_do_pais(livro[aba], pais)
            por_variante[campo] = _por_ano(cabecalho, linhas, "15-64", sexo="Total")
    finally:
        livro.close()
    return Projecao(**por_variante)


def ler_variantes(conteudo: bytes, pais: int = 76) -> dict[str, dict[int, float]]:
    """{variante (as chaves de `VARIANTES`): {ano: idosos para cada 100 de 15 a 64}}."""
    livro = _abrir_rapido(conteudo)
    try:
        faltam = [a for a in VARIANTES.values() if a not in livro.sheetnames]
        if faltam:
            raise FonteForaDoArError(f"ONU: abas que sumiram: {faltam}")
        saida = {}
        for chave, aba in VARIANTES.items():
            cabecalho, linhas = _linhas_do_pais(livro[aba], pais)
            saida[chave] = _por_ano(cabecalho, linhas, COLUNA_IDOSOS)
    finally:
        livro.close()
    return saida


def idosos_por_100(pais: int = 76) -> Projecao:
    return ler_idosos_por_100(baixar(URL_IDOSOS_POR_100, validade=UM_MES, tempo_limite=300), pais)


def variantes(pais: int = 76) -> dict[str, dict[int, float]]:
    return ler_variantes(baixar(URL_VARIANTES, validade=UM_MES, tempo_limite=300), pais)
