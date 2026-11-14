"""World Economic Outlook do FMI, pela API SDMX (`api.imf.org`), sem chave.

Uma chamada traz todos os países e indicadores pedidos, com o realizado e as projeções da
edição corrente (abril e outubro de cada ano). A data da edição vem no atributo
PUBLICATION_DATE; o último ano realizado de cada série, em LATEST_ACTUAL_ANNUAL_DATA.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from sacibras.rede import baixar_json

BASE = "https://api.imf.org/external/sdmx/2.1/data/IMF.RES,WEO,9.0.0"


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
