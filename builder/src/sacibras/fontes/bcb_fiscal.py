"""Tabelas especiais das estatísticas fiscais do Banco Central: o que não está no SGS.

A taxa de juros implícita da dívida bruta do governo geral (DBGG) e o cronograma de
vencimento da DBGG saem só nas planilhas da nota mensal "Estatísticas fiscais" (tabelas 24 e
25, poucos meses por arquivo) e nas "Tabelas especiais" do BC, com a série inteira
(bcb.gov.br/estatisticas/tabelasespeciais, seção "Dívida Líquida e Necessidades de
Financiamento do Setor Público"). Conferido em 15/11/2026:

- `Tximplnp.xlsx`, "Taxa de juros implícita da DLSP e da DBGG", aba `DBGG_12meses`: "Taxa de
  juros implícita - Taxa acumulada em doze meses", em %, de dez/2007 a set/2026; a linha
  "Dívida bruta total" bate com a tabela 24 da nota de 29/10/2026 (13,03 % em set/2026). O
  CKAN do BC não tem a série (package_search por "implícita" dá zero).
- `Cronop.xlsx`, "Cronograma de Vencimento da DLSP e da DBGG", aba `Cronograma_DBGG`, R$
  milhões, de dez/2006 a set/2026; o primeiro bloco (o governo geral inteiro) bate com a
  tabela 25 da mesma nota (R$ 2.975.215 milhões vencem em até um ano, de R$ 11.113.783
  milhões). A dívida do Governo Federal inclui as operações compromissadas do BC (nota 1/).

As duas planilhas têm o mesmo desenho: uma coluna por mês, o ano escrito só em algumas
colunas da linha "Discriminação" e o nome do mês duas linhas abaixo. As linhas se acham pelo
texto do rótulo (sem acento, sem espaço sobrando), nunca pela posição.
"""

from __future__ import annotations

import io
import unicodedata
from datetime import date
from typing import Any

import openpyxl  # type: ignore[import-untyped]

from sacibras.rede import FonteForaDoArError, baixar
from sacibras.tipos import Ponto

BASE = "https://www.bcb.gov.br/content/estatisticas/Documents/Tabelas_especiais/"
TAXA_IMPLICITA = "Tximplnp.xlsx"
CRONOGRAMA = "Cronop.xlsx"
FONTE_TAXA = (
    "Banco Central, Tabelas especiais: taxa de juros implícita da DBGG, acumulada em 12 meses"
)
FONTE_CRONOGRAMA = "Banco Central, Tabelas especiais: cronograma de vencimento da DBGG"

MESES = [
    "janeiro",
    "fevereiro",
    "marco",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]


class PlanilhaMudouError(FonteForaDoArError):
    """A planilha não tem mais a aba, o cabeçalho ou a linha esperada."""


def normalizar(texto: Any) -> str:
    """'   Governo Federal1/' -> 'governo federal1/'; 'Março' -> 'marco'."""
    bruto = unicodedata.normalize("NFKD", str(texto))
    return " ".join("".join(c for c in bruto if not unicodedata.combining(c)).lower().split())


def datas_das_colunas(linhas: list[tuple[Any, ...]]) -> dict[int, date]:
    """{índice da coluna: 1º dia do mês}. O ano vem da linha "Discriminação" (só em algumas
    colunas) e o mês, da primeira linha abaixo dela com nomes de mês. A partir da primeira
    coluna, cada coluna é o mês seguinte; o nome do mês confere a sequência."""
    topo = next(
        (i for i, linha in enumerate(linhas) if linha and normalizar(linha[0]) == "discriminacao"),
        None,
    )
    if topo is None:
        raise PlanilhaMudouError("tabela especial do BC: sem a linha 'Discriminação'")
    anos = linhas[topo]
    meses = next(
        (
            linha
            for linha in linhas[topo + 1 : topo + 5]
            if any(normalizar(c) in MESES for c in linha if c is not None)
        ),
        None,
    )
    if meses is None:
        raise PlanilhaMudouError("tabela especial do BC: sem a linha dos meses")
    primeira = next(i for i, c in enumerate(meses) if c is not None and normalizar(c) in MESES)
    ano = anos[primeira] if primeira < len(anos) else None
    if not isinstance(ano, (int, float)):
        raise PlanilhaMudouError("tabela especial do BC: sem o ano da primeira coluna")
    atual = date(int(ano), MESES.index(normalizar(meses[primeira])) + 1, 1)
    saida: dict[int, date] = {}
    for i in range(primeira, len(meses)):
        if meses[i] is None:
            break
        if normalizar(meses[i]) != MESES[atual.month - 1]:
            raise PlanilhaMudouError(
                f"tabela especial do BC: coluna {i} diz {meses[i]!r}, esperado o mês {atual:%m/%Y}"
            )
        saida[i] = atual
        atual = date(atual.year + atual.month // 12, atual.month % 12 + 1, 1)
    return saida


def linha(linhas: list[tuple[Any, ...]], rotulo: str, colunas: dict[int, date]) -> list[Ponto]:
    """A primeira linha cujo rótulo (coluna A, normalizado) é `rotulo`, como série mensal.
    Célula vazia ou com traço fica de fora."""
    alvo = normalizar(rotulo)
    for registro in linhas:
        if registro and registro[0] is not None and normalizar(registro[0]) == alvo:
            return [
                (d, float(registro[i]))
                for i, d in colunas.items()
                if i < len(registro) and isinstance(registro[i], (int, float))
            ]
    raise PlanilhaMudouError(f"tabela especial do BC: sem a linha {rotulo!r}")


def _aba(conteudo: bytes, aba: str) -> list[tuple[Any, ...]]:
    livro = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    try:
        if aba not in livro.sheetnames:
            raise PlanilhaMudouError(f"tabela especial do BC: sem a aba {aba!r}")
        return list(livro[aba].iter_rows(values_only=True))
    finally:
        livro.close()


def ler_taxa_implicita(conteudo: bytes) -> list[Ponto]:
    linhas = _aba(conteudo, "DBGG_12meses")
    return linha(linhas, "Dívida bruta total", datas_das_colunas(linhas))


def ler_cronograma(conteudo: bytes) -> tuple[list[Ponto], dict[str, list[Ponto]]]:
    """(o total da DBGG, {faixa: saldo}) do primeiro bloco (o governo geral), R$ milhões."""
    linhas = _aba(conteudo, "Cronograma_DBGG")
    colunas = datas_das_colunas(linhas)
    # O primeiro bloco termina onde começa o do Governo Federal: as faixas se repetem abaixo.
    fim = next(
        (i for i, r in enumerate(linhas) if r and normalizar(r[0]).startswith("governo federal")),
        len(linhas),
    )
    bloco = linhas[:fim]
    total = linha(bloco, "Dívida bruta total", colunas)
    faixas = {
        nome: linha(bloco, f"Vencimento {nome}", colunas)
        for nome in (
            "até 1 ano",
            "entre 1 e 3 anos",
            "entre 3 e 5 anos",
            "entre 5 e 10 anos",
            "entre 10 e 20 anos",
            "após 20 anos",
        )
    }
    return total, faixas


def taxa_implicita_dbgg() -> list[Ponto]:
    """A taxa de juros implícita da DBGG acumulada em 12 meses (% no período), mês a mês."""
    return ler_taxa_implicita(baixar(BASE + TAXA_IMPLICITA, validade=24 * 3600, tempo_limite=120))


def cronograma_dbgg() -> tuple[list[Ponto], dict[str, list[Ponto]]]:
    return ler_cronograma(baixar(BASE + CRONOGRAMA, validade=24 * 3600, tempo_limite=120))
