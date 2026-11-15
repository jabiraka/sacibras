"""Banco Mundial, API de indicadores (`api.worldbank.org/v2`), sem chave.

Usado para comparar o Gini do Brasil com o de outros países (Desigualdade › Estados e
países). Conferido em 14/11/2026: `SI.POV.GINI` (índice de Gini, 0 a 100, da Plataforma de
Pobreza e Desigualdade do próprio Banco Mundial) e `NY.GDP.PCAP.PP.KD` (PIB por habitante em
dólares PPC constantes de 2021). Em português (`/v2/pt/…`) a API demora uns 25 s e deixa
nomes em branco; em inglês responde em menos de um segundo, então os dados vêm em inglês e
o nome do país sai do `mundo.nome_do_pais`. Agregados (regiões, grupos de renda) têm
região "NA" na lista de países e ficam de fora.
"""

from __future__ import annotations

from typing import Any

from sacibras.rede import FonteForaDoArError, baixar_json

BASE = "https://api.worldbank.org/v2"
GINI = "SI.POV.GINI"
PIB_POR_HABITANTE_PPC = "NY.GDP.PCAP.PP.KD"
SUBALIMENTACAO = "SN.ITK.DEFC.ZS"
"""Prevalência de subalimentação (% da população), da FAO; média de três anos. Quando a FAO
publica "menos de 2,5 %", o Banco Mundial grava 2,5."""
INSEGURANCA_GRAVE = "SN.ITK.SVFI.ZS"
"""Insegurança alimentar grave (% da população), escala FIES da FAO; média de três anos."""
IDOSOS = "SP.POP.65UP.TO.ZS"
"""População de 65 anos ou mais (% do total), da Divisão de População da ONU (World Population
Prospects) e das estatísticas dos países; conferido em 15/11/2026, de 1960 a 2025."""
FONTE = "Banco Mundial, World Development Indicators"
AGREGADOS = {"1W": "WLD", "ZJ": "LCN", "XD": "HIC", "OE": "OED"}
"""O `country.id` de duas letras de alguns agregados e o código de três que se pede."""
VALIDADE = 7 * 24 * 3600
"""O Gini dos países muda poucas vezes por ano; a API às vezes demora ou recusa."""


def paises() -> dict[str, str]:
    """{ISO3: nome em inglês} dos países, sem os agregados."""
    bruto = baixar_json(
        f"{BASE}/country", params={"format": "json", "per_page": "400"}, validade=VALIDADE
    )
    if not isinstance(bruto, list) or len(bruto) < 2:
        raise FonteForaDoArError(f"Banco Mundial: lista de países inesperada: {str(bruto)[:200]}")
    return {
        str(p["id"]): str(p["name"])
        for p in bruto[1]
        if p.get("region", {}).get("id") != "NA" and len(str(p.get("id", ""))) == 3
    }


def ultimos(linhas: list[dict[str, Any]], so: set[str]) -> dict[str, tuple[int, float]]:
    """{ISO3: (ano, valor)} do ano mais novo com dado de cada país em `so`."""
    saida: dict[str, tuple[int, float]] = {}
    for linha in linhas:
        iso, valor = str(linha.get("countryiso3code") or ""), linha.get("value")
        if valor is None or iso not in so:
            continue
        ano = int(linha["date"])
        if iso not in saida or ano > saida[iso][0]:
            saida[iso] = (ano, float(valor))
    return saida


def indicador(codigo: str, desde: int, ate: int) -> list[dict[str, Any]]:
    """As linhas de um indicador para todos os países e agregados, de `desde` a `ate`."""
    bruto = baixar_json(
        f"{BASE}/country/all/indicator/{codigo}",
        params={"format": "json", "date": f"{desde}:{ate}", "per_page": "20000"},
        validade=VALIDADE,
        tempo_limite=120,
    )
    if not isinstance(bruto, list) or len(bruto) < 2 or not bruto[1]:
        raise FonteForaDoArError(f"Banco Mundial {codigo}: sem dados: {str(bruto)[:200]}")
    return list(bruto[1])


def serie_do_pais(pais: str, codigo: str, desde: int, ate: int) -> list[tuple[int, float]]:
    """(ano, valor) de um indicador para um país, do mais velho ao mais novo."""
    bruto = baixar_json(
        f"{BASE}/country/{pais}/indicator/{codigo}",
        params={"format": "json", "date": f"{desde}:{ate}", "per_page": "200"},
        validade=VALIDADE,
        tempo_limite=120,
    )
    if not isinstance(bruto, list) or len(bruto) < 2 or not bruto[1]:
        raise FonteForaDoArError(f"Banco Mundial {codigo} ({pais}): sem dados")
    return sorted((int(x["date"]), float(x["value"])) for x in bruto[1] if x["value"] is not None)


def series_dos_paises(
    paises: list[str], codigo: str, desde: int, ate: int
) -> dict[str, list[tuple[int, float]]]:
    """{código: [(ano, valor)]} de vários países ou agregados numa chamada só. Alguns agregados
    vêm com `countryiso3code` vazio (o de alta renda, HIC, em 15/11/2026): a chave sai do
    `country.id` de duas letras, traduzido por `AGREGADOS`."""
    bruto = baixar_json(
        f"{BASE}/country/{';'.join(paises)}/indicator/{codigo}",
        params={"format": "json", "date": f"{desde}:{ate}", "per_page": "2000"},
        validade=VALIDADE,
        tempo_limite=180,
    )
    if not isinstance(bruto, list) or len(bruto) < 2 or not bruto[1]:
        raise FonteForaDoArError(f"Banco Mundial {codigo}: sem dados")
    saida: dict[str, list[tuple[int, float]]] = {}
    for x in bruto[1]:
        if x.get("value") is None:
            continue
        id2 = str(x.get("country", {}).get("id") or "")
        chave = str(x.get("countryiso3code") or AGREGADOS.get(id2, id2))
        saida.setdefault(chave, []).append((int(x["date"]), float(x["value"])))
    return {k: sorted(v) for k, v in saida.items()}
