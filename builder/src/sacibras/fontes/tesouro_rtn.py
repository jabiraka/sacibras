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
    "receita administrada pela rfb": "receita_rfb",
    "receita liquida (1-2)": "receita_liquida",
    "despesa total": "despesa_total",
    "arrecadacao liquida para o rgps": "arrecadacao_rgps",
    "beneficios previdenciarios": "rgps",
    "pessoal e encargos sociais": "pessoal",
    "resultado primario governo central - acima da linha (3 - 4)": "primario",
    # A despesa obrigatória e a discricionária (Caio, 16/11/2026: "tem como separar as
    # despesas das obrigatórias?"). Lidas na aba 1.1 do arquivo de set/2026, em 17/11/2026:
    # 4.1 benefícios, 4.2 pessoal, 4.3 outras obrigatórias e 4.4 "sujeitas à programação
    # financeira", que se abre em 4.4.1 obrigatórias com controle de fluxo e 4.4.2
    # discricionárias.
    "outras despesas obrigatorias": "outras_obrigatorias",
    "abono e seguro desemprego": "abono_seguro",
    "beneficios de prestacao continuada da loas/rmv": "bpc",
    "obrigatorias com controle de fluxo": "obrigatorias_fluxo",
    "despesas discricionarias": "discricionarias",
}


# As outras abas mensais têm o mesmo desenho da 1.1 (cabeçalho na linha 5, uma coluna por
# mês). Rótulos lidos no arquivo de jul/2026, em 19/11/2026 (Caio: "inclua a distribuição dos
# gastos por servidores públicos" e "quanto as estatais dão lucro ou prejuízo").
ABA_DIVIDENDOS = "1.2"
"""Resultado primário, versão aberta: os dividendos que a União recebe, empresa por empresa."""
LINHAS_DIVIDENDOS = {
    "dividendos e participacoes": "dividendos",
    "banco do brasil": "div_bb",
    "bnb": "div_bnb",
    "bndes": "div_bndes",
    "caixa economica federal": "div_caixa",
    "empresa brasileira de correios e telegrafos (correios)": "div_correios",
    "eletrobras": "div_eletrobras",
    "irb": "div_irb",
    "petrobras": "div_petrobras",
    "demais dividendos e participacoes": "div_demais",
}
# A despesa do Tesouro com o Proagro, mensal, na mesma aba 1.2 (linha "4.3.15.2 Proagro", lida
# no arquivo de jul/2026 em 26/11/2026; Caio: "Inclua o proagro e crédito rural").
LINHAS_PROAGRO = {"proagro": "proagro"}

ABA_INVESTIMENTO = "1.3"
"""Investimento e inversões financeiras: o dinheiro que a União põe no capital das estatais."""
LINHAS_INVESTIMENTO = {
    "despesas com aumento de capital de empresas estatais nao dependentes "
    "(participacao da uniao no capital)": "aumento_de_capital",
}
ABA_PAGO = "1.5"
"""Despesas pelo critério de valor pago: a folha aberta em ativos e inativos, civis e
militares (desde 2008)."""
LINHAS_PESSOAL = {
    "pessoal e encargos sociais": "pessoal_pago",
    "ativo civil": "ativo_civil",
    "ativo militar": "ativo_militar",
    "aposentadorias e pensoes civis": "inativo_civil",
    "reformas e pensoes militares": "inativo_militar",
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


def ler_aba(
    conteudo: bytes, aba: str = ABA, rotulos: dict[str, str] | None = None
) -> dict[str, list[Ponto]]:
    """{nome da linha: [(1º dia do mês, R$ milhões)]} da aba (a 1.1, se não disser outra);
    mês vazio é pulado."""
    livro = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    try:
        return _ler_folha(livro, aba, LINHAS if rotulos is None else rotulos)
    finally:
        livro.close()


def _ler_folha(livro: Any, aba: str, rotulos: dict[str, str]) -> dict[str, list[Ponto]]:
    if aba not in livro.sheetnames:
        raise LinhaSumiuError(f"RTN: sem a aba {aba!r} (abas: {livro.sheetnames[:6]}...)")
    linhas = list(livro[aba].iter_rows(values_only=True))

    if len(linhas) < LINHA_DO_CABECALHO:
        raise LinhaSumiuError(f"RTN: a aba {aba} tem só {len(linhas)} linhas")
    cabecalho = linhas[LINHA_DO_CABECALHO - 1]
    colunas = [
        (i, c.date() if isinstance(c, datetime) else c)
        for i, c in enumerate(cabecalho)
        if i > 0 and isinstance(c, (datetime, date))
    ]
    if not colunas:
        raise LinhaSumiuError(f"RTN: sem datas no cabeçalho da aba {aba} (linha 5)")

    achadas: dict[str, tuple[Any, ...]] = {}
    for linha in linhas[LINHA_DO_CABECALHO:]:
        if isinstance(linha[0], str):
            nome = rotulos.get(normalizar(linha[0]))
            if nome and nome not in achadas:  # vale a primeira: os detalhes vêm depois
                achadas[nome] = linha
    faltam = [r for r, n in rotulos.items() if n not in achadas]
    if faltam:
        raise LinhaSumiuError(f"RTN, aba {aba}: rótulo(s) que sumiram da tabela: {faltam}")

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


def ler_detalhes(conteudo: bytes) -> dict[str, list[Ponto]]:
    """Os dividendos por empresa (aba 1.2), o aumento de capital das estatais (1.3) e a folha
    por tipo de servidor (1.5), num dicionário só: os nomes não se repetem entre as abas."""
    livro = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    try:
        saida: dict[str, list[Ponto]] = {}
        for aba, rotulos in (
            (ABA_DIVIDENDOS, LINHAS_DIVIDENDOS | LINHAS_PROAGRO),
            (ABA_INVESTIMENTO, LINHAS_INVESTIMENTO),
            (ABA_PAGO, LINHAS_PESSOAL),
        ):
            saida |= _ler_folha(livro, aba, rotulos)
        return saida
    finally:
        livro.close()


def detalhes() -> dict[str, list[Ponto]]:
    corpo = baixar(endereco_da_serie_historica(), validade=24 * 3600, tempo_limite=180)
    return ler_detalhes(corpo)
