"""Arrecadação federal por tributo e por UF, mês a mês: o CSV de dados abertos da Receita.

`gov.br/receitafederal/dados/arrecadacao-estado.csv` (~2,4 MB, latin-1, `;`): uma linha por
ano, mês (escrito: "Janeiro") e UF, uma coluna por tributo, em reais correntes. Lido em
14/11/2026, com dado até set/2026. O que se viu no arquivo e o leitor trata:

- 2001 e 2002 misturam vírgula de milhar ("1,014,655,323") e decimal ("248,5"): não dá para
  ler sem chute, e o leitor começa em 2003. Dali em diante, a vírgula é decimal e o ponto,
  quando aparece (algumas linhas de 2023 e 2024), é de milhar.
- A receita previdenciária só vem por UF a partir de jan/2013 (antes, zero ou só em 2005), e
  as receitas "administradas por outros órgãos" a partir de 2010. Somas comparáveis no tempo,
  então, só desde 2013: `COMPLETO_DESDE`.
- Colunas que se dividiram (Cofins em "financeiras" e "demais" desde 2004; previdência em
  "própria" e "demais" de 2005 a 2017) nunca vêm preenchidas junto com a coluna inteira:
  somar todas não conta nada duas vezes (conferido).

A UF é a do domicílio fiscal de quem pagou: imposto de empresa com sede em São Paulo conta
para São Paulo, mesmo com a operação em outro estado.
"""

from __future__ import annotations

import csv
import io
import unicodedata
from datetime import date

from sacibras.rede import FonteForaDoArError, baixar
from sacibras.tipos import Ponto

URL = "https://www.gov.br/receitafederal/dados/arrecadacao-estado.csv"
FONTE = "Receita Federal, arrecadação por estado e tributo (dados abertos)"
PRIMEIRO_ANO = 2003
COMPLETO_DESDE = date(2013, 1, 1)

MESES = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}

# Grupo -> o começo do nome normalizado das colunas que entram nele. O que não casar com
# nenhum vai para "outros".
GRUPOS: dict[str, tuple[str, ...]] = {
    "ir": ("irpf", "irpj", "irrf"),
    "cofins_pis": ("cofins", "contribuicao para o pis"),
    "previdencia": ("receita previdenciaria",),
    "csll": ("csll",),
    "ipi": ("ipi",),
    "iof": ("imposto s/ operacoes financeiras",),
    "comercio": ("imposto sobre importacao", "imposto sobre exportacao"),
}
NOMES = {
    "ir": "Imposto de Renda",
    "cofins_pis": "Cofins e PIS/Pasep",
    "previdencia": "Contribuição ao INSS",
    "csll": "CSLL",
    "ipi": "IPI",
    "iof": "IOF",
    "comercio": "Importação e exportação",
    "outros": "Outros",
}
FIXAS = ("ano", "mes", "uf")


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto)
    return " ".join("".join(c for c in sem_acento if not unicodedata.combining(c)).lower().split())


def grupo_da_coluna(nome: str) -> str:
    n = normalizar(nome)
    for grupo, inicios in GRUPOS.items():
        if n.startswith(inicios):
            return grupo
    return "outros"


def numero(texto: str) -> float:
    """'1.234.567,89' -> 1234567.89; '' -> 0."""
    texto = texto.strip()
    if not texto:
        return 0.0
    return float(texto.replace(".", "").replace(",", "."))


def ler_csv(texto: str) -> dict[str, dict[str, list[Ponto]]]:
    """{grupo: {UF: [(1º dia do mês, R$)]}}, de 2003 em diante, e a soma do país em "BR"."""
    leitor = csv.reader(io.StringIO(texto), delimiter=";")
    cabecalho = next(leitor)
    if [normalizar(c) for c in cabecalho[:3]] != list(FIXAS):
        raise FonteForaDoArError(f"Receita: cabeçalho inesperado {cabecalho[:4]}")
    grupos = [grupo_da_coluna(c) for c in cabecalho[3:]]
    if not {"ir", "cofins_pis", "previdencia"} <= set(grupos):
        raise FonteForaDoArError("Receita: sumiram colunas de IR, Cofins ou previdência")
    soma: dict[str, dict[str, dict[date, float]]] = {}
    for linha in leitor:
        if len(linha) < 4 or not linha[0].strip().isdigit():
            continue
        ano = int(linha[0])
        mes = MESES.get(normalizar(linha[1]))
        if ano < PRIMEIRO_ANO or mes is None:
            continue
        quando = date(ano, mes, 1)
        uf = linha[2].strip().upper()
        for grupo, valor in zip(grupos, linha[3:], strict=False):
            v = numero(valor)
            for chave in (uf, "BR"):
                por_mes = soma.setdefault(grupo, {}).setdefault(chave, {})
                por_mes[quando] = por_mes.get(quando, 0.0) + v
    return {g: {uf: sorted(m.items()) for uf, m in ufs.items()} for g, ufs in soma.items()}


def arrecadacao() -> dict[str, dict[str, list[Ponto]]]:
    corpo = baixar(URL, validade=24 * 3600, tempo_limite=120)
    return ler_csv(corpo.decode("latin-1"))


def doze_meses_por_uf(dados: dict[str, dict[str, list[Ponto]]]) -> tuple[dict[str, float], date]:
    """{UF: R$ nos 12 meses até o último mês do arquivo} (todos os tributos) e esse mês."""
    por_uf: dict[str, dict[date, float]] = {}
    for ufs in dados.values():
        for uf, pontos in ufs.items():
            if uf == "BR":
                continue
            for d, v in pontos:
                por_uf.setdefault(uf, {})[d] = por_uf.get(uf, {}).get(d, 0.0) + v
    ultimo = max(d for meses in por_uf.values() for d in meses)
    janela = {
        date(ultimo.year - (ultimo.month <= k), (ultimo.month - k - 1) % 12 + 1, 1)
        for k in range(12)
    }
    return {uf: sum(v for d, v in m.items() if d in janela) for uf, m in por_uf.items()}, ultimo
