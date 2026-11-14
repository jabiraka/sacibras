"""BIS Data Portal (`stats.bis.org/api/v2`), CSV, sem chave.

Juro básico de cada banco central (WS_CBPOL, fim de mês) e inflação ao consumidor em 12 meses
(WS_LONG_CPI, unidade 771). Os países vêm em ISO de duas letras; a zona do euro é XM.
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
        ano, mes = linha["TIME_PERIOD"].split("-")[:2]
        saida.setdefault(linha["REF_AREA"], []).append((date(int(ano), int(mes), 1), float(valor)))
    for pontos in saida.values():
        pontos.sort()
    return saida


def juro_basico(paises: list[str], inicio: date) -> dict[str, list[Ponto]]:
    """{ISO2: [(mês, % a.a. no fim do mês)]}."""
    return _ler("WS_CBPOL", "M." + "+".join(paises), inicio)


def inflacao_12m(paises: list[str], inicio: date) -> dict[str, list[Ponto]]:
    """{ISO2: [(mês, % em 12 meses)]}."""
    return _ler("WS_LONG_CPI", "M." + "+".join(paises) + ".771", inicio)
