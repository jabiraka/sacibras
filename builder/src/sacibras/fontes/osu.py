"""Orçamento de Subsídios da União (OSU): quanto a União dá em subsídios, de 2003 em diante.

O Ministério do Planejamento publica uma edição por ano, com um Anexo Estatístico em XLSX. Soma
três tipos (lido em 26/11/2026, edição de 2026, dados até 2025):
- benefícios **financeiros**: gasto do Orçamento (subvenção, equalização de juros), "explícito";
- benefícios **creditícios**: juro abaixo do de mercado em fundos e empréstimos da União
  (FAT, fundos constitucionais, FIES…), "implícito";
- benefícios **tributários**: o gasto tributário do DGT da Receita. Os dois últimos anos são a
  projeção dele.

A página de listagem traz um XLSX por edição (o nome muda: `osu_2026-anexos-publicacao_enviado`,
`osu_2025-anexos-publicacao`, `osu_2024-anexo-estatistico`…); o endereço vem do `href`, com
`/@@download/file`. Dentro, a `Tab_1` (R$ mil correntes) e a `Tab_4` (% do PIB) têm uma linha
por tipo (o total) seguida das linhas dos programas dele, com os anos na linha do cabeçalho.
Linhas e colunas se acham pelo rótulo, nunca pela posição.
"""

from __future__ import annotations

import io
import re
import warnings
from dataclasses import dataclass

import openpyxl  # type: ignore[import-untyped]

from sacibras.rede import FonteForaDoArError, baixar

PAGINA = (
    "https://www.gov.br/planejamento/pt-br/assuntos/avaliacao-de-politicas-publicas/"
    "orcamento-de-subsidios-da-uniao"
)
FONTE = "Ministério do Planejamento e Orçamento, Orçamento de Subsídios da União"
PADRAO = re.compile(r'href="(?P<url>[^"]*/osu_(?P<ed>\d{4})-[^"/]*\.xlsx)/@@download/file"')

FINANCEIROS = "Benefícios Financeiros"
CREDITICIOS = "Benefícios Creditícios"
TRIBUTARIOS = "Benefícios Tributários"
TIPOS = (FINANCEIROS, CREDITICIOS, TRIBUTARIOS)

# A área de cada programa, pelo nome (primeira regra que casa): é agrupamento nosso, para
# responder "para qual setor vai". Quem não casa fica em "Outros".
AREAS: list[tuple[str, str]] = [
    ("Desenvolvimento regional", r"constitucionais|\bFDNE\b|\bFDCO\b|\bFDA\b|\bFRD\b|SUDENE"),
    ("Habitação", r"minha casa|\bFCVS\b|habita"),
    ("Energia elétrica", r"energia el"),
    ("Educação", r"\bFIES\b"),
    ("Trabalho e emprego", r"\bFAT\b|\bPESE\b"),
    ("Exportação", r"\bPROEX\b|\bFGE\b|exporta"),
    (
        "Agropecuária",
        r"PRONAF|rural|agropecu|agr[ií]cola|lavoura|\bAGF\b|\bEGF\b|pre[çc]os|\bPESA\b|"
        r"cerealistas|borracha|RECOOP|sucroalcoolei|FUNCAF|pesqueiras|reforma agr[aá]ria",
    ),
    (
        "Indústria, inovação e crédito às empresas",
        r"\bPSI\b|BNDES|FNDCT|marinha mercante|\bFMM\b|PROER|\bFGPC\b|clima|\bFND\b|Peac|"
        r"microcr[eé]dito|turismo|Revitaliza",
    ),
]
OUTROS = "Outros"


def area_do_programa(nome: str) -> str:
    for area, padrao in AREAS:
        if re.search(padrao, nome, re.IGNORECASE):
            return area
    return OUTROS


@dataclass(frozen=True)
class Programa:
    nome: str
    tipo: str
    """Um de `TIPOS`."""
    valores: dict[int, float]
    """{ano: valor} na unidade da tabela (R$ mil na Tab_1, % do PIB na Tab_4)."""


@dataclass(frozen=True)
class Tabela:
    totais: dict[str, dict[int, float]]
    """{tipo, ou "TOTAL": {ano: valor}}."""
    programas: list[Programa]


@dataclass(frozen=True)
class Subsidios:
    edicao: int
    nominal: Tabela
    """Tab_1: R$ mil correntes."""
    pct_pib: Tabela
    """Tab_4: % do PIB."""

    @property
    def ultimo_ano(self) -> int:
        return max(self.nominal.totais["TOTAL"])


def _numero(v: object) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def ler_tabela(linhas: list[tuple[object, ...]]) -> Tabela:
    """Uma tabela do anexo (Tab_1 ou Tab_4): o cabeçalho tem "Discriminação" e os anos."""
    cabecalho = next(
        (
            i
            for i, linha in enumerate(linhas)
            if any(isinstance(c, str) and c.strip() == "Discriminação" for c in linha)
        ),
        None,
    )
    if cabecalho is None:
        raise FonteForaDoArError("OSU: sem a linha 'Discriminação'")
    topo = linhas[cabecalho]
    nome_col = next(
        i for i, c in enumerate(topo) if isinstance(c, str) and c.strip() == "Discriminação"
    )
    anos = {
        i: int(c)
        for i, c in enumerate(topo)
        if isinstance(c, (int, float)) and not isinstance(c, bool) and 1990 < c < 2100
    }
    if len(anos) < 3:
        raise FonteForaDoArError("OSU: sem os anos no cabeçalho")
    totais: dict[str, dict[int, float]] = {}
    programas: list[Programa] = []
    atual: str | None = None
    for linha in linhas[cabecalho + 1 :]:
        rotulo = linha[nome_col] if nome_col < len(linha) else None
        if not isinstance(rotulo, str):
            continue
        nome = " ".join(rotulo.split())
        valores = {
            a: v for i, a in anos.items() if i < len(linha) and (v := _numero(linha[i])) is not None
        }
        if nome.upper() == "TOTAL":
            totais["TOTAL"] = valores
            break
        if nome in TIPOS:
            atual = nome
            totais[nome] = valores
        elif atual is not None and valores:
            programas.append(Programa(nome, atual, valores))
    if set(TIPOS) - set(totais) or "TOTAL" not in totais:
        raise FonteForaDoArError("OSU: faltam os totais por tipo ou o TOTAL")
    return Tabela(totais, programas)


def ler_anexo(conteudo: bytes, edicao: int) -> Subsidios:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        livro = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    try:
        if "Tab_1" not in livro.sheetnames or "Tab_4" not in livro.sheetnames:
            raise FonteForaDoArError(f"OSU {edicao}: sem as abas Tab_1 e Tab_4")
        t1 = list(livro["Tab_1"].iter_rows(values_only=True))
        t4 = list(livro["Tab_4"].iter_rows(values_only=True))
    finally:
        livro.close()
    return Subsidios(edicao, ler_tabela(t1), ler_tabela(t4))


def edicoes_na_pagina(html: str) -> dict[int, str]:
    """{ano da edição: endereço de download}."""
    return {
        int(m["ed"]): (m["url"] if m["url"].startswith("http") else "https://www.gov.br" + m["url"])
        + "/@@download/file"
        for m in PADRAO.finditer(html)
    }


def subsidios() -> Subsidios:
    """A edição mais nova, lida da página de listagem."""
    html = baixar(PAGINA, validade=24 * 3600).decode("utf-8", "replace")
    achadas = edicoes_na_pagina(html)
    if not achadas:
        raise FonteForaDoArError("OSU: nenhum anexo na página de listagem")
    ano = max(achadas)
    return ler_anexo(baixar(achadas[ano], validade=7 * 24 * 3600, tempo_limite=120), ano)
