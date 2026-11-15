"""SINISA, o Sistema Nacional de Informações em Saneamento Básico (Ministério das Cidades).

Substituiu o SNIS em 2024. Uma coleta por ano, com os prestadores de cada município, e uma
publicação por ano com relatórios e planilhas de indicadores, cada indicador com a fórmula na
aba "Nota metodológica". Conferido em 15/11/2026: a mais nova é o "SINISA 2025", ano de
referência 2024, publicado em 18/12/2025, na página
`gov.br/cidades/.../saneamento/sinisa/resultados-sinisa/resultados-sinisa-2025`. Abre de fora
do Brasil.

Usado o módulo de esgoto: um ZIP (~9 MB, `SINISA_ESGOTO_Planilhas_2024.zip`; o nome muda por
ano) com a base municipal e o consolidado por UF, região e Brasil
(`SINISA_ESGOTO_Indicadores_UF_MR_BR_2024.xlsx`, aba "Indicadores - Esgoto"). Na planilha, o
cabeçalho tem três linhas (nome, unidade e código); as colunas se acham pelo código (IES0001…),
nunca pela posição. A sigla de Sergipe e a do Sudeste são as duas "SE": a linha se acha pelo
nome. A base municipal só tem os ~2.750 municípios com prestador de esgoto: não serve para
contar quantos municípios não têm rede.
"""

from __future__ import annotations

import io
import re
import unicodedata
import warnings
import zipfile
from dataclasses import dataclass
from functools import cache
from typing import Any

import openpyxl  # type: ignore[import-untyped]

from sacibras.rede import FonteForaDoArError, baixar

PAGINAS = [
    "https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/saneamento/sinisa",
    "https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/saneamento/sinisa/"
    "resultados-sinisa",
]
"""Onde se acham as edições. A página do SINISA lista a mais nova ("resultados-sinisa-2025");
a de resultados abre a edição anterior (ano de referência 2023, com o esgoto em RAR)."""
FONTE = "Ministério das Cidades, SINISA"
EDICAO = re.compile(r'href="(?P<url>[^"]*/resultados-sinisa-(?P<ano>\d{4}))/?"')
ZIP_ESGOTO = re.compile(r'href="(?P<url>[^"]*SINISA_ESGOTO_Planilhas_(?P<ano>\d{4})\.zip)"')
CONSOLIDADO = "Indicadores_UF_MR_BR"

INDICADORES = {
    "rede": "IES0001",
    "rede_urbana": "IES0002",
    "tratado_domicilios": "IES0007",
    "tratado_coletado": "IES2004",
}
"""IES0001: população total com rede coletora de esgoto, %; IES0002: a urbana; IES0007:
domicílios com coleta e tratamento, %; IES2004: esgoto tratado sobre o coletado, %."""


@dataclass(frozen=True)
class Esgoto:
    ano: int
    """O ano de referência (o da coleta é o seguinte)."""
    publicado: str
    """A data de publicação, como vem na planilha ("18/12/2025")."""
    por_lugar: dict[str, dict[str, float]]
    """{nome sem acento em minúsculas ("brasil", "sergipe"…): {indicador: valor}}."""


def chave(nome: str) -> str:
    texto = unicodedata.normalize("NFKD", nome)
    return "".join(c for c in texto if not unicodedata.combining(c)).lower().strip()


def _numero(valor: Any) -> float | None:
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str):
        try:
            return float(valor.replace(".", "").replace(",", ".")) if "," in valor else float(valor)
        except ValueError:
            return None  # "Não calculado (condições não atendidas)"
    return None


def ler_planilha(conteudo: bytes) -> Esgoto:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        livro = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    try:
        linhas = list(livro.worksheets[0].iter_rows(values_only=True))
    finally:
        livro.close()
    texto_topo = " ".join(str(c) for li in linhas[:10] for c in li if c)
    ano = re.search(r"Ano de refer[eê]ncia (\d{4})", texto_topo)
    publicado = re.search(r"publica[cç][aã]o: (\d{2}/\d{2}/\d{4})", texto_topo)
    if not ano:
        raise FonteForaDoArError("SINISA: sem o ano de referência no topo da planilha")
    codigos = next(
        (i for i, li in enumerate(linhas[:20]) if any(c == INDICADORES["rede"] for c in li)), None
    )
    if codigos is None:
        raise FonteForaDoArError("SINISA: sem a linha dos códigos dos indicadores")
    onde = {
        campo: list(linhas[codigos]).index(cod)
        for campo, cod in INDICADORES.items()
        if cod in linhas[codigos]
    }
    if "rede" not in onde:
        raise FonteForaDoArError("SINISA: sem o indicador IES0001")
    por_lugar: dict[str, dict[str, float]] = {}
    for linha in linhas[codigos + 1 :]:
        nome = linha[0]
        if not isinstance(nome, str) or not nome.strip():
            continue
        valores = {c: _numero(linha[i]) for c, i in onde.items() if i < len(linha)}
        if valores.get("rede") is None:
            continue  # o rodapé com os critérios
        por_lugar[chave(nome)] = {c: v for c, v in valores.items() if v is not None}
    if "brasil" not in por_lugar or len(por_lugar) < 28:
        raise FonteForaDoArError(f"SINISA: só {len(por_lugar)} linhas no consolidado")
    return Esgoto(int(ano[1]), publicado[1] if publicado else "", por_lugar)


def do_zip(conteudo: bytes) -> Esgoto:
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        nome = next(
            (n for n in z.namelist() if CONSOLIDADO in n and "Indicadores" in n.split("/")[-1]),
            None,
        )
        if nome is None:
            raise FonteForaDoArError("SINISA: o ZIP de esgoto não tem o consolidado por UF")
        return ler_planilha(z.read(nome))


@cache
def esgoto() -> Esgoto:
    """Os indicadores de esgoto por UF, região e Brasil, da publicação mais nova."""
    edicoes: dict[int, str] = {}
    for pagina in PAGINAS:
        html = baixar(pagina, validade=24 * 3600).decode("utf-8", "replace")
        edicoes |= {int(m["ano"]): m["url"] for m in EDICAO.finditer(html)}
    for edicao in sorted(edicoes, reverse=True):
        html = baixar(edicoes[edicao], validade=24 * 3600).decode("utf-8", "replace")
        achado = max(ZIP_ESGOTO.finditer(html), key=lambda m: int(m["ano"]), default=None)
        if achado:
            conteudo = baixar(achado["url"], validade=30 * 24 * 3600, tempo_limite=300)
            return do_zip(conteudo)
    raise FonteForaDoArError("SINISA: nenhuma edição com as planilhas de esgoto")
