"""SIDRA do IBGE: `apisidra.ibge.gov.br/values/...`.

A resposta é uma lista em que a primeira linha é o cabeçalho; cada linha seguinte traz o valor
em "V" e os códigos das dimensões em D1C, D2C… O período vem como `202609` (mensal) ou
`202603` (trimestral: ano + trimestre com dois dígitos).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sacibras.rede import baixar_json
from sacibras.tipos import Ponto

BASE = "https://apisidra.ibge.gov.br/values"


def _periodo(codigo: str, trimestral: bool) -> date:
    ano, resto = int(codigo[:4]), int(codigo[4:6] or 1)
    if len(codigo) == 4:
        return date(ano, 1, 1)
    return date(ano, 3 * resto - 2, 1) if trimestral else date(ano, resto, 1)


def consultar(caminho: str) -> list[dict[str, Any]]:
    """As linhas de dados (sem o cabeçalho) de `/values/<caminho>`."""
    bruto = baixar_json(f"{BASE}/{caminho.strip('/')}")
    return list(bruto[1:])


def _coluna(cabecalho: dict[str, str], nome: str) -> str:
    """A chave (D3C, D4C…) cuja descrição no cabeçalho começa por `nome`."""
    for chave, descricao in cabecalho.items():
        if chave.endswith("C") and chave.startswith("D") and descricao.startswith(nome):
            return chave
    raise KeyError(f"dimensão {nome!r} não está em {list(cabecalho.values())}")


def series(
    tabela: int,
    variavel: int,
    *,
    periodos: str = "all",
    classificacao: str = "",
    por: str | None = None,
    nivel: str = "n1/all",
    trimestral: bool = False,
) -> dict[str, list[Ponto]]:
    """Séries de uma variável. Sem `por`, devolve {"": pontos}; com `por` (o começo do nome de
    uma dimensão, ex. "Setores"), devolve {código da categoria: pontos}.

    `classificacao` é o trecho do caminho, ex. "c11255/90707,93404".
    """
    caminho = f"t/{tabela}/{nivel}/v/{variavel}/p/{periodos}"
    if classificacao:
        caminho += f"/{classificacao.strip('/')}"
    bruto = baixar_json(f"{BASE}/{caminho}")
    cabecalho, linhas = bruto[0], bruto[1:]
    col_periodo = _coluna(cabecalho, "Trimestre") if trimestral else None
    if col_periodo is None:
        for nome in ("Mês", "Trimestre Móvel", "Trimestre", "Ano"):
            try:
                col_periodo = _coluna(cabecalho, nome)
                break
            except KeyError:
                continue
    if col_periodo is None:
        raise KeyError(f"sem dimensão de período em {cabecalho}")
    col_por = _coluna(cabecalho, por) if por else None
    saida: dict[str, list[Ponto]] = {}
    for linha in linhas:
        valor = linha["V"]
        if valor in ("...", "-", "..", "X", ""):
            continue
        chave = str(linha[col_por]) if col_por else ""
        saida.setdefault(chave, []).append(
            (_periodo(str(linha[col_periodo]), trimestral), float(valor))
        )
    for pontos in saida.values():
        pontos.sort()
    return saida


def serie(tabela: int, variavel: int, **kw: Any) -> list[Ponto]:
    return series(tabela, variavel, **kw).get("", [])
