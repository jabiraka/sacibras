"""Resultado do Tesouro Nacional (RTN): receitas e despesas do Governo Central, mês a mês.

Tesouro Transparente (CKAN), conjunto `resultado-do-tesouro-nacional`. O recurso é um XLSX de
~4 MB cujo NOME MUDA TODO MÊS (`seriehistoricajul26.xlsx`), então o endereço se descobre pela
API do CKAN. Aba "1.1": resultado primário resumido, R$ milhões correntes, desde jan/1997,
cabeçalho na linha 5 ("Discriminação" + uma coluna por mês, data no 1º dia). As linhas se
acham pelo TEXTO do rótulo, nunca pela posição: o Tesouro já reordenou a tabela.
"""

from __future__ import annotations

import io
import re
import unicodedata
from datetime import date, datetime
from typing import Any

import openpyxl  # type: ignore[import-untyped]

from sacibras.rede import FonteForaDoArError, baixar, baixar_json
from sacibras.tipos import Ponto

CKAN = "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show"
CONJUNTO = "resultado-do-tesouro-nacional"
ABA = "1.1"
LINHA_DO_CABECALHO = 5

# Rótulo normalizado (sem acento, minúsculas, sem numeração) -> nome que o resto do código usa.
LINHAS = {
    "receita liquida (1-2)": "receita_liquida",
    "despesa total": "despesa_total",
    "arrecadacao liquida para o rgps": "arrecadacao_rgps",
    "beneficios previdenciarios": "rgps",
    "pessoal e encargos sociais": "pessoal",
    "resultado primario governo central - acima da linha (3 - 4)": "primario",
}


class LinhaSumiuError(FonteForaDoArError):
    """Um rótulo esperado não está mais na tabela (o Tesouro mudou o arquivo)."""


def normalizar(rotulo: str) -> str:
    """'4.1  Benefícios Previdenciários ' -> 'beneficios previdenciarios'; '1.3 -  Arrecadação
    Líquida para o RGPS' -> 'arrecadacao liquida para o rgps'."""
    texto = unicodedata.normalize("NFKD", rotulo)
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    texto = re.sub(r"\s+\d+/\s*$", "", texto.strip())  # nota de rodapé: "receita total 1/"
    texto = re.sub(r"^(?:[ivx]+|\d+)(?:\.\d+)*\.?\s+", "", texto)  # "IV.1", "4.1", "3."
    texto = re.sub(r"^-\s+", "", texto)  # "1.3 -  Arrecadação Líquida para o RGPS"
    return re.sub(r"\s+", " ", texto).strip()


def ler_aba(conteudo: bytes) -> dict[str, list[Ponto]]:
    """{nome da linha: [(1º dia do mês, R$ milhões)]} da aba 1.1; mês vazio é pulado."""
    livro = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    try:
        if ABA not in livro.sheetnames:
            raise LinhaSumiuError(f"RTN: sem a aba {ABA!r} (abas: {livro.sheetnames[:6]}...)")
        linhas = list(livro[ABA].iter_rows(values_only=True))
    finally:
        livro.close()

    if len(linhas) < LINHA_DO_CABECALHO:
        raise LinhaSumiuError(f"RTN: a aba {ABA} tem só {len(linhas)} linhas")
    cabecalho = linhas[LINHA_DO_CABECALHO - 1]
    colunas = [
        (i, c.date() if isinstance(c, datetime) else c)
        for i, c in enumerate(cabecalho)
        if i > 0 and isinstance(c, (datetime, date))
    ]
    if not colunas:
        raise LinhaSumiuError(f"RTN: sem datas no cabeçalho da aba {ABA} (linha 5)")

    achadas: dict[str, tuple[Any, ...]] = {}
    for linha in linhas[LINHA_DO_CABECALHO:]:
        if isinstance(linha[0], str):
            nome = LINHAS.get(normalizar(linha[0]))
            if nome and nome not in achadas:  # vale a primeira: os detalhes vêm depois
                achadas[nome] = linha
    faltam = [r for r, n in LINHAS.items() if n not in achadas]
    if faltam:
        raise LinhaSumiuError(f"RTN, aba {ABA}: rótulo(s) que sumiram da tabela: {faltam}")

    return {
        nome: [
            (d, float(linha[i]))
            for i, d in colunas
            if i < len(linha) and isinstance(linha[i], (int, float))
        ]
        for nome, linha in achadas.items()
    }


def endereco_da_serie_historica() -> str:
    """O XLSX da série histórica mais recente, pelo CKAN (o nome do arquivo muda todo mês)."""
    dados = baixar_json(CKAN, params={"id": CONJUNTO}, validade=6 * 3600, tempo_limite=180)
    recursos = dados["result"]["resources"]
    candidatos = [
        r
        for r in recursos
        if str(r.get("format", "")).lower() == "xlsx"
        and "seriehistorica" in str(r.get("url", "")).lower()
    ]
    if not candidatos:
        raise FonteForaDoArError(f"RTN: nenhum XLSX de série histórica em {CONJUNTO}")
    mais_novo = max(candidatos, key=lambda r: str(r.get("last_modified") or r.get("created") or ""))
    return str(mais_novo["url"])


def serie_historica() -> dict[str, list[Ponto]]:
    corpo = baixar(endereco_da_serie_historica(), validade=24 * 3600, tempo_limite=180)
    return ler_aba(corpo)
