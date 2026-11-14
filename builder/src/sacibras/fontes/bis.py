"""BIS Data Portal (`stats.bis.org/api/v2`), CSV, sem chave.

Juro básico de cada banco central (WS_CBPOL, fim de mês) e inflação ao consumidor em 12 meses
(WS_LONG_CPI, unidade 771). Os países vêm em ISO de duas letras; a zona do euro é XM.

Trimestrais (testados em 14/11/2026, docs/FONTES.md): serviço da dívida do setor privado não
financeiro (WS_DSR, Q.<país>.P, % da renda) e hiato de crédito (WS_CREDIT_GAP, Q.<país>.P.A.C,
pontos do PIB). Neles o país vem em BORROWERS_CTY e o período em "2025-Q3"; a ordem das
colunas muda entre os conjuntos, então se lê pelo nome.
"""

from __future__ import annotations

import csv
import io
from datetime import date

from sacibras.rede import baixar
from sacibras.tipos import Ponto

BASE = "https://stats.bis.org/api/v2/data/dataflow/BIS"


def _ler(fluxo: str, chave: str, inicio: date) -> dict[str, list[Ponto]]:
    corpo = baixar(
        f"{BASE}/{fluxo}/1.0/{chave}",
        params={"startPeriod": inicio.strftime("%Y-%m"), "format": "csv"},
        validade=24 * 3600,
        tempo_limite=120,
    )
    saida: dict[str, list[Ponto]] = {}
    for linha in csv.DictReader(io.StringIO(corpo.decode("utf-8-sig"))):
        valor = linha.get("OBS_VALUE") or ""
        if valor in ("", "NaN"):
            continue
        area = linha.get("REF_AREA") or linha.get("BORROWERS_CTY") or ""
        saida.setdefault(area, []).append((_periodo(linha["TIME_PERIOD"]), float(valor)))
    for pontos in saida.values():
        pontos.sort()
    return saida


def _periodo(texto: str) -> date:
    """ "2025-07" → 1º/07/2025; "2025-Q3" → 1º/07/2025 (o primeiro mês do trimestre)."""
    ano, resto = texto.split("-")[:2]
    mes = (int(resto[1:]) - 1) * 3 + 1 if resto.startswith("Q") else int(resto)
    return date(int(ano), mes, 1)


def juro_basico(paises: list[str], inicio: date) -> dict[str, list[Ponto]]:
    """{ISO2: [(mês, % a.a. no fim do mês)]}."""
    return _ler("WS_CBPOL", "M." + "+".join(paises), inicio)


def inflacao_12m(paises: list[str], inicio: date) -> dict[str, list[Ponto]]:
    """{ISO2: [(mês, % em 12 meses)]}."""
    return _ler("WS_LONG_CPI", "M." + "+".join(paises) + ".771", inicio)


def servico_da_divida(paises: list[str], inicio: date) -> dict[str, list[Ponto]]:
    """{ISO2: [(trimestre, % da renda)]}: juros e amortizações do setor privado não
    financeiro (famílias e empresas) sobre a renda. Lista vazia pede todos os países."""
    return _ler("WS_DSR", "Q." + "+".join(paises) + ".P", inicio)


def hiato_de_credito(paises: list[str], inicio: date) -> dict[str, list[Ponto]]:
    """{ISO2: [(trimestre, pontos do PIB)]}: crédito ao setor privado sobre o PIB menos a
    tendência de longo prazo (o "credit-to-GDP gap" do BIS)."""
    return _ler("WS_CREDIT_GAP", "Q." + "+".join(paises) + ".P.A.C", inicio)
