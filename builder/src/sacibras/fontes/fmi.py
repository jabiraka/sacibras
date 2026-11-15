"""World Economic Outlook do FMI, pela API SDMX (`api.imf.org`), sem chave.

Uma chamada traz todos os países e indicadores pedidos, com o realizado e as projeções da
edição corrente (abril e outubro de cada ano). A data da edição vem no atributo
PUBLICATION_DATE; o último ano realizado de cada série, em LATEST_ACTUAL_ANNUAL_DATA.

Da mesma API, os conjuntos do departamento de estatística (IMF.STA), anuais e com todos os
países numa chamada (testados em 15/11/2026): reservas internacionais (IL,
`<país>.TRGMV_REVS.USD.A`, total com o ouro a preço de mercado, US$, no fim do ano) e
importação de bens e serviços do balanço de pagamentos (BOP, `<país>.DB_T.GS.USD.A`, US$ no
ano). Valores em dólares, sem multiplicador.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date
from typing import Any

from sacibras.rede import baixar, baixar_json

BASE = "https://api.imf.org/external/sdmx/2.1/data/IMF.RES,WEO,9.0.0"
BASE_STA = "https://api.imf.org/external/sdmx/2.1/data/IMF.STA,"
RESERVAS = ("IL", "TRGMV_REVS.USD.A")
IMPORTACOES = ("BOP", "DB_T.GS.USD.A")
HIERARQUIAS = "https://api.imf.org/external/sdmx/2.1/hierarchicalcodelist/all/all/latest"
HIERARQUIA_PAISES = "H_WEO_COUNTRIES"
COMMODITIES = "https://api.imf.org/external/sdmx/2.1/data/IMF.RES,PCPS"
OURO = "PGOLD"
"""Ouro, US$ por onça troy, média do mês (conferido em 15/11/2026: mensal desde 1990, com
dado até out/2026; chave `G001.PGOLD.USD.M`)."""


@dataclass(frozen=True)
class Weo:
    publicado_em: date
    valores: dict[tuple[str, str], dict[int, float]]
    """{(país ou agregado, indicador): {ano: valor}}."""
    ultimo_realizado: dict[tuple[str, str], int]


def _atributo(estrutura: list[dict[str, Any]], indices: list[Any], nome: str) -> str | None:
    for definicao, indice in zip(estrutura, indices, strict=False):
        if definicao["id"] == nome and indice is not None:
            valor = definicao["values"][indice]
            return str(valor.get("id") or valor.get("name"))
    return None


def weo(paises: list[str], indicadores: list[str], inicio: int, fim: int) -> Weo:
    """Os indicadores dos países pedidos; lista vazia traz todos (a chave vazia do SDMX)."""
    url = f"{BASE}/{'+'.join(paises)}.{'+'.join(indicadores)}.A"
    bruto = baixar_json(
        url,
        params={"startPeriod": str(inicio), "endPeriod": str(fim)},
        cabecalhos={"Accept": "application/json"},
        validade=24 * 3600,
        tempo_limite=120,
    )
    estrutura, dados = bruto["structure"], bruto["dataSets"][0]
    dimensoes = estrutura["dimensions"]["series"]
    anos = [int(v["id"]) for v in estrutura["dimensions"]["observation"][0]["values"]]
    atributos_serie = estrutura["attributes"].get("series", [])
    valores: dict[tuple[str, str], dict[int, float]] = {}
    realizado: dict[tuple[str, str], int] = {}
    for chave, serie in dados["series"].items():
        i_pais, i_indicador, *_ = (int(x) for x in chave.split(":"))
        par = (dimensoes[0]["values"][i_pais]["id"], dimensoes[1]["values"][i_indicador]["id"])
        valores[par] = {
            anos[int(t)]: float(obs[0])
            for t, obs in serie["observations"].items()
            if obs and obs[0] not in (None, "")
        }
        ultimo = _atributo(
            atributos_serie, serie.get("attributes", []), "LATEST_ACTUAL_ANNUAL_DATA"
        )
        if ultimo and ultimo[:4].isdigit():
            realizado[par] = int(ultimo[:4])
    publicado = _atributo(
        estrutura["attributes"]["dataSet"], dados.get("attributes", []), "PUBLICATION_DATE"
    )
    quando = date.fromisoformat(publicado[:10]) if publicado else date.today()
    return Weo(quando, valores, realizado)


def anuais_por_pais(bruto: dict[str, Any]) -> dict[str, dict[int, float]]:
    """{país: {ano: valor}} de uma resposta SDMX-JSON com o país na primeira dimensão e uma
    série só por país."""
    estrutura, dados = bruto["structure"], bruto["dataSets"][0]
    paises = estrutura["dimensions"]["series"][0]["values"]
    anos = [int(v["id"][:4]) for v in estrutura["dimensions"]["observation"][0]["values"]]
    saida: dict[str, dict[int, float]] = {}
    for chave, serie in dados["series"].items():
        iso = paises[int(chave.split(":")[0])]["id"]
        saida[iso] = {
            anos[int(t)]: float(obs[0])
            for t, obs in serie["observations"].items()
            if obs and obs[0] not in (None, "")
        }
    return saida


def estatistica(conjunto: tuple[str, str], inicio: int) -> dict[str, dict[int, float]]:
    """{ISO3: {ano: valor}} de todos os países num conjunto do IMF.STA (`RESERVAS`,
    `IMPORTACOES`)."""
    fluxo, resto = conjunto
    bruto = baixar_json(
        f"{BASE_STA}{fluxo}/.{resto}",
        params={"startPeriod": str(inicio)},
        cabecalhos={"Accept": "application/json"},
        validade=24 * 3600,
        tempo_limite=120,
    )
    return anuais_por_pais(bruto)


def _codigo(no: dict[str, Any]) -> str:
    """O código do nó: o que vem depois do último ponto de `code` (G205, BRA…)."""
    return str(no["code"]).rsplit(".", 1)[-1]


def _folhas(no: dict[str, Any], destino: dict[str, None]) -> None:
    filhos = no.get("hierarchicalCodes") or []
    if not filhos:
        destino[_codigo(no)] = None  # dict como conjunto ordenado
    for filho in filhos:
        _folhas(filho, destino)


def _grupos_da_arvore(nos: list[dict[str, Any]], saida: dict[str, list[str]]) -> None:
    for no in nos:
        filhos = no.get("hierarchicalCodes") or []
        if filhos:
            paises: dict[str, None] = {}
            _folhas(no, paises)
            saida[_codigo(no)] = list(paises)
            _grupos_da_arvore(filhos, saida)


def grupos_da_resposta(bruto: dict[str, Any]) -> dict[str, list[str]]:
    """{grupo: países ISO3 únicos}, achatando os subgrupos, da hierarquia H_WEO_COUNTRIES."""
    for lista in bruto.get("data", {}).get("hierarchicalCodelists", []):
        if lista.get("id") == HIERARQUIA_PAISES:
            saida: dict[str, list[str]] = {}
            for hierarquia in lista.get("hierarchies", []):
                _grupos_da_arvore(hierarquia.get("hierarchicalCodes", []), saida)
            return saida
    raise RuntimeError(
        f"A hierarquia {HIERARQUIA_PAISES} não está na lista de hierarquias do FMI "
        f"({HIERARQUIAS}); o FMI mudou o nome ou tirou a hierarquia."
    )


def grupos() -> dict[str, list[str]]:
    """Os grupos de países do WEO (G001 Mundo, G110 Avançados, G205 América Latina…), cada um
    com todos os países dentro dele, subgrupos achatados."""
    bruto = baixar_json(
        HIERARQUIAS,
        cabecalhos={"Accept": "application/json"},
        validade=7 * 86400,
        tempo_limite=180,
    )
    return grupos_da_resposta(bruto)


def preco_commodity(indicador: str, inicio: date) -> list[tuple[date, float]]:
    """O preço mensal de uma commodity no Primary Commodity Price System (PCPS) do FMI, em
    US$, média do mês: [(1º dia do mês, preço)]. O PCPS converte em média do mês as cotações
    diárias ou semanais de referência (no ouro, o fixing de Londres)."""
    corpo = baixar(
        f"{COMMODITIES}/G001.{indicador}.USD.M",
        params={"startPeriod": f"{inicio:%Y-%m}"},
        cabecalhos={"Accept": "application/vnd.sdmx.data+csv"},
        validade=24 * 3600,
        tempo_limite=120,
    )
    saida: list[tuple[date, float]] = []
    for linha in csv.DictReader(io.StringIO(corpo.decode("utf-8-sig"))):
        valor = linha.get("OBS_VALUE") or ""
        ano, _, mes = (linha.get("TIME_PERIOD") or "").partition("-M")
        if valor in ("", "NaN") or not mes:
            continue
        saida.append((date(int(ano), int(mes), 1), float(valor)))
    return sorted(saida)
