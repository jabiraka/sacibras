"""Juro de longo prazo da OCDE (`sdmx.oecd.org`, Main Economic Indicators), CSV, sem chave.

Fluxo `OECD.SDD.STES,DSD_STES@DF_FINMARK`, medida IRLT (juro de longo prazo, % a.a., média do
mês): para quase todos os países, a taxa dos títulos do governo de 10 anos. Conferido em
15/11/2026: 44 áreas (os membros, mais Brasil, China, Índia, África do Sul, Bulgária, Croácia,
Romênia e a zona do euro como EA20), com dado até out/2026 (China até set/2026).

**O Brasil da OCDE é a TJLP** (5 % em set/2014, 6,75 % em fev/2018, 7,37 % em fev/2023: os
valores da TJLP de cada trimestre), que não é juro de título de 10 anos; Brasil no mundo põe
no lugar a taxa do Tesouro Direto. A API devolve 429 depois de uns 8 pedidos seguidos: um
pedido só, com todos os países.
"""

from __future__ import annotations

import csv
import io
from datetime import date

from sacibras.rede import baixar
from sacibras.tipos import Ponto

URL = "https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_FINMARK,/.M.IRLT......"
FONTE = "OCDE, Main Economic Indicators (juro de longo prazo)"
ZONA_DO_EURO = "EA20"


def ler(texto: str) -> dict[str, list[Ponto]]:
    saida: dict[str, list[Ponto]] = {}
    for linha in csv.DictReader(io.StringIO(texto)):
        valor = linha.get("OBS_VALUE") or ""
        if valor in ("", "NaN"):
            continue
        ano, mes = linha["TIME_PERIOD"].split("-")[:2]
        saida.setdefault(linha["REF_AREA"], []).append((date(int(ano), int(mes), 1), float(valor)))
    for pontos in saida.values():
        pontos.sort()
    return saida


def juro_longo(inicio: date) -> dict[str, list[Ponto]]:
    """{ISO3 (ou EA20): [(mês, % a.a.)]}, de todos os países que a OCDE publica."""
    corpo = baixar(
        URL,
        params={"startPeriod": f"{inicio:%Y-%m}", "format": "csvfile"},
        validade=24 * 3600,
        tempo_limite=180,
    )
    return ler(corpo.decode("utf-8-sig"))
