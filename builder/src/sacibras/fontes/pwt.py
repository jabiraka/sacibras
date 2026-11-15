"""Penn World Table (PWT), da Universidade de Groningen: o PIB, o capital, as horas, a
escolaridade e a produtividade total dos fatores (PTF) de 185 países, ano a ano desde 1950.

Licença CC BY 4.0 (lida em 15/11/2026; `licencas.PWT`): pode mostrar e baixar, com o crédito
e a citação que os autores pedem. A versão 11.0 saiu em 07/10/2025 e vai até 2023; as
anteriores saíram em 2015 (9.0), 2019 (9.1), 2021 (10.0) e 2023 (10.01), cada uma com o
método publicado (Feenstra, Inklaar e Timmer, 2015, e o guia de cada versão).

O arquivo mora no DataverseNL (doi:10.34894/FABVLR). O id do arquivo muda a cada revisão, então
o builder pergunta à API do Dataverse qual é o `pwt<versão>.xlsx` da versão mais nova (~6 MB,
aba "Data", uma linha por país e ano). Testado de fora do Brasil em 15/11/2026: responde em
poucos segundos, sem chave. Versão nova (12.0) virá com outro DOI: trocar `DOI` e `VERSAO`.
"""

from __future__ import annotations

import io
import re
import warnings
from typing import Any

import openpyxl  # type: ignore[import-untyped]

from sacibras.rede import FonteForaDoArError, baixar, baixar_json

DOI = "doi:10.34894/FABVLR"
VERSAO = "11.0"
API = "https://dataverse.nl/api/datasets/:persistentId/"
ARQUIVO = "https://dataverse.nl/api/access/datafile/{id}"
FONTE = (
    f"Penn World Table {VERSAO} (Feenstra, Inklaar e Timmer, 2015, American Economic Review "
    "105(10); licença CC BY 4.0)"
)
CAMPOS = ("rgdpna", "rnna", "emp", "avh", "hc", "labsh", "rtfpna", "ctfp")
"""PIB e capital a preços nacionais constantes, ocupados (milhões), horas por ano, índice de
capital humano, parte do trabalho na renda, PTF (2021 = 1) e PTF contra a dos EUA (EUA = 1)."""

PorPais = dict[str, dict[int, dict[str, float]]]
"""{ISO3: {ano: {campo: valor}}}; campo vazio na fonte não entra."""


def id_da_planilha(metadados: dict[str, Any]) -> int:
    """O id do `pwt<versão>.xlsx` (a tabela principal) na versão mais nova do conjunto."""
    for arquivo in metadados["data"]["latestVersion"]["files"]:
        dado = arquivo["dataFile"]
        if re.fullmatch(r"pwt\d+\.xlsx", dado["filename"]):
            return int(dado["id"])
    raise FonteForaDoArError("PWT: o Dataverse não lista mais o pwt<versão>.xlsx")


def ler_planilha(conteudo: bytes, paises: set[str] | None = None) -> PorPais:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        livro = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    try:
        if "Data" not in livro.sheetnames:
            raise FonteForaDoArError("PWT: sem a aba Data")
        linhas = livro["Data"].iter_rows(values_only=True)
        cabeca = list(next(linhas))
        faltam = [c for c in ("countrycode", "year", *CAMPOS) if c not in cabeca]
        if faltam:
            raise FonteForaDoArError(f"PWT: colunas que sumiram: {faltam}")
        col = {c: cabeca.index(c) for c in ("countrycode", "year", *CAMPOS)}
        saida: PorPais = {}
        for linha in linhas:
            pais = linha[col["countrycode"]]
            if not isinstance(pais, str) or (paises and pais not in paises):
                continue
            valores = {
                c: float(linha[col[c]]) for c in CAMPOS if isinstance(linha[col[c]], (int, float))
            }
            saida.setdefault(pais, {})[int(linha[col["year"]])] = valores
    finally:
        livro.close()
    if not saida:
        raise FonteForaDoArError("PWT: nenhum país lido")
    return saida


def dados(paises: set[str] | None = None) -> PorPais:
    validade = 30 * 24 * 3600  # sai uma versão a cada dois anos, mais ou menos
    meta = baixar_json(API, params={"persistentId": DOI}, validade=validade)
    conteudo = baixar(ARQUIVO.format(id=id_da_planilha(meta)), validade=validade, tempo_limite=180)
    return ler_planilha(conteudo, paises)
