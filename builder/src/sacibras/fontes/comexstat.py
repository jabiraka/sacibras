"""Comex Stat (Ministério do Desenvolvimento, Indústria, Comércio e Serviços): exportações por
estado de origem do produto.

API pública `api-comexstat.mdic.gov.br` (testada em 14/11/2026, responde de fora do Brasil):
`POST /general` com o filtro em JSON; `GET /general/dates/updated` diz o último mês fechado.
Valores FOB em US$. O estado é o de **origem** da mercadoria (onde foi produzida), não o do
porto nem o da sede da empresa; o que não se sabe de onde veio cai em "Não Declarada".
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sacibras.rede import FonteForaDoArError, baixar_json

BASE = "https://api-comexstat.mdic.gov.br"
FONTE = "Ministério do Desenvolvimento, Indústria, Comércio e Serviços, Comex Stat"


def ultimo_mes() -> date:
    r = baixar_json(f"{BASE}/general/dates/updated", validade=6 * 3600)
    d = r["data"]
    return date(int(d["year"]), int(d["monthNumber"]), 1)


def _menos(mes: date, n: int) -> date:
    total = mes.year * 12 + mes.month - 1 - n
    return date(total // 12, total % 12 + 1, 1)


def _por_estado(inicio: date, fim: date) -> dict[str, float]:
    """US$ exportados de `inicio` a `fim`, os dois no mesmo ano: período que cruza o ano vem
    vazio da API (visto em 14/11/2026, com `success: true`)."""
    filtro: dict[str, Any] = {
        "flow": "export",
        "monthDetail": False,
        "period": {"from": f"{inicio:%Y-%m}", "to": f"{fim:%Y-%m}"},
        "filters": [],
        "details": ["state"],
        "metrics": ["metricFOB"],
    }
    r = baixar_json(
        f"{BASE}/general?language=pt", metodo="POST", corpo_json=filtro, validade=24 * 3600
    )
    saida: dict[str, float] = {}
    for linha in r.get("data", {}).get("list") or []:
        nome = str(linha.get("state", "")).strip()
        if nome:
            saida[nome] = saida.get(nome, 0.0) + float(linha["metricFOB"])
    return saida


def exportacoes_12_meses() -> tuple[date, dict[str, float]]:
    """(último mês, {nome do estado: US$ exportados nos 12 meses até ele})."""
    fim = ultimo_mes()
    inicio = _menos(fim, 11)
    pedacos = (
        [(inicio, fim)]
        if inicio.year == fim.year
        else [(inicio, date(inicio.year, 12, 1)), (date(fim.year, 1, 1), fim)]
    )
    saida: dict[str, float] = {}
    for de, ate in pedacos:
        for nome, valor in _por_estado(de, ate).items():
            saida[nome] = saida.get(nome, 0.0) + valor
    if len(saida) < 27:
        raise FonteForaDoArError(
            f"Comex Stat: só {len(saida)} estados em {inicio:%m/%Y}–{fim:%m/%Y}"
        )
    return fim, saida
