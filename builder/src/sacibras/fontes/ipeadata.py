"""IPEADATA (OData v4), sem chave e com CORS aberto. Usado para o Ibovespa diário."""

from __future__ import annotations

from datetime import date

from sacibras.rede import baixar_json
from sacibras.tipos import Ponto

URL = "https://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{codigo}')"

IBOVESPA = "GM366_IBVSP366"
"""Ibovespa, fechamento diário (conferido no IPEADATA em 14/11/2026; sai com um dia de
atraso em relação à B3)."""
FONTE_IBOVESPA = "B3, Ibovespa (fechamento), pelo IPEADATA (série GM366_IBVSP366)"
"""O índice é da B3 mesmo vindo do IPEADATA: sem CSV nem PNG (`licencas.B3`)."""


def serie(codigo: str, desde: date) -> list[Ponto]:
    bruto = baixar_json(URL.format(codigo=codigo), tempo_limite=90)
    pontos: list[Ponto] = []
    for linha in bruto["value"]:
        if linha.get("VALVALOR") is None:
            continue
        quando = date.fromisoformat(linha["VALDATA"][:10])
        if quando >= desde:
            pontos.append((quando, float(linha["VALVALOR"])))
    return sorted(pontos)


def por_territorio(codigo: str, desde: date) -> dict[str, list[Ponto]]:
    """A série de cada território: {TERCODIGO: pontos}. No Ipeadata, "0" é o Brasil, 1 a 5
    as regiões e os códigos do IBGE de dois dígitos, os estados (vêm misturados; o nível
    está em NIVNOME)."""
    bruto = baixar_json(URL.format(codigo=codigo), tempo_limite=90)
    saida: dict[str, list[Ponto]] = {}
    for linha in bruto["value"]:
        if linha.get("VALVALOR") is None:
            continue
        quando = date.fromisoformat(linha["VALDATA"][:10])
        if quando >= desde:
            chave = str(linha.get("TERCODIGO") or "0")
            saida.setdefault(chave, []).append((quando, float(linha["VALVALOR"])))
    for pontos in saida.values():
        pontos.sort()
    return saida
