"""CAPAG dos estados: a nota de capacidade de pagamento que o Tesouro Nacional dá a cada UF.

Conjunto `capag-estados` no CKAN do Tesouro Transparente (consultado em 15/11/2026): um CSV
por ano de divulgação ("Capag Estados 2025", ano-base 2024, publicado em 10/03/2026) e, às
vezes, uma revisão do mesmo ano ("Capag Estados 2024 - Revisão", feita depois do RREO do 6º
bimestre e do RGF do 3º quadrimestre). O nome do arquivo muda a cada ano: o builder acha o
mais novo pelo `package_show`, e a revisão vale mais que a primeira versão do mesmo ano.

O CSV (`;`, decimal com vírgula, às vezes com BOM): `UF`, `Indicador 1` a `3` (em %), `Nota 1`
a `3` e `Classificação da CAPAG`. Pelos metadados do conjunto, o indicador 1 é o de
endividamento, o 2 o de poupança corrente e o 3 o de liquidez; a nota final é a combinação das
três e, desde 2024, vai de A+ a D (A+, A, B+, B, C, D). Divulgação anual; o Tesouro avisa que
o resultado "não vincula a posição do Tesouro Nacional" e que o cálculo definitivo se faz quando
o estado pede empréstimo com garantia da União. Licença ODbL.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from typing import Any

from sacibras.rede import FonteForaDoArError, baixar, baixar_json

CKAN = "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show"
CONJUNTO = "capag-estados"
FONTE = "Tesouro Nacional, CAPAG dos estados (Tesouro Transparente)"
VALIDADE = 24 * 3600.0

ESCALA: dict[str, int] = {"D": 1, "C": 2, "B": 3, "B+": 4, "A": 5, "A+": 6}
"""A nota em número, para pintar o mapa e ordenar: D é 1, A+ é 6."""

_NOME = re.compile(r"capag\s+estados\s+(\d{4})", re.IGNORECASE)


class PlanilhaMudouError(FonteForaDoArError):
    """O Tesouro trocou o formato do CSV: as colunas não estão onde se espera."""


@dataclass(frozen=True)
class NotaCapag:
    nota: str
    """A classificação final: A+, A, B+, B, C ou D."""
    endividamento: str
    poupanca: str
    liquidez: str
    """As notas de cada indicador (A, B, C ou n.d.)."""


@dataclass(frozen=True)
class Capag:
    ano: int
    """O ano de divulgação; as contas são as do ano anterior (o ano-base)."""
    revisao: bool
    notas: dict[str, NotaCapag]
    """{sigla da UF: nota}."""


def escolher(recursos: list[dict[str, Any]]) -> tuple[int, bool, str] | None:
    """(ano, é revisão, url) do CSV mais novo; a revisão ganha da primeira versão do ano."""
    melhor: tuple[int, bool, str] | None = None
    for r in recursos:
        achou = _NOME.search(r.get("name") or "")
        if not achou or (r.get("format") or "").upper() != "CSV" or not r.get("url"):
            continue
        candidato = (int(achou.group(1)), "revis" in r["name"].lower(), str(r["url"]))
        if melhor is None or candidato[:2] > melhor[:2]:
            melhor = candidato
    return melhor


def ler_csv(conteudo: bytes) -> dict[str, NotaCapag]:
    texto = conteudo.decode("utf-8-sig", errors="replace")
    leitor = csv.DictReader(io.StringIO(texto), delimiter=";")
    campos = {c.strip(): c for c in (leitor.fieldnames or [])}
    precisa = ("UF", "Classificação da CAPAG", "Nota 1", "Nota 2", "Nota 3")
    if any(p not in campos for p in precisa):
        raise PlanilhaMudouError(f"CAPAG: colunas {sorted(campos)}")
    notas: dict[str, NotaCapag] = {}
    for linha in leitor:

        def campo(nome: str, linha: dict[str, str] = linha) -> str:
            return (linha.get(campos[nome]) or "").strip()

        uf, nota = campo("UF").upper(), campo("Classificação da CAPAG").upper()
        if len(uf) != 2:
            continue
        notas[uf] = NotaCapag(
            nota=nota,
            endividamento=campo("Nota 1").upper(),
            poupanca=campo("Nota 2").upper(),
            liquidez=campo("Nota 3").upper(),
        )
    if len(notas) < 20:
        raise PlanilhaMudouError(f"CAPAG: só {len(notas)} estados no CSV")
    return notas


def capag() -> Capag:
    """As notas da divulgação mais nova."""
    pacote = baixar_json(CKAN, params={"id": CONJUNTO}, validade=VALIDADE)
    achado = escolher(pacote["result"]["resources"])
    if achado is None:
        raise PlanilhaMudouError("CAPAG: nenhum CSV com o ano no nome")
    ano, revisao, url = achado
    return Capag(ano, revisao, ler_csv(baixar(url, validade=VALIDADE)))
