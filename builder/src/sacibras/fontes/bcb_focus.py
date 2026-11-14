"""Focus (Relatório de Mercado do BCB), pela API Olinda de expectativas.

A mediana do mercado para cada indicador e horizonte. O Focus guarda todas as edições, então
tanto a expectativa de hoje quanto a história dela ("o que o mercado esperava há um ano") saem
daqui.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from urllib.parse import quote

from sacibras.rede import baixar_json

BASE = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"


def _consulta(recurso: str, filtro: str, *, topo: int = 5000, ordem: str = "Data desc") -> Any:
    # A Olinda não aceita "+" como espaço: a consulta vai montada à mão, com %20.
    consulta = "&".join(
        f"{chave}={quote(valor, safe='')}"
        for chave, valor in (
            ("$filter", filtro),
            ("$orderby", ordem),
            ("$top", str(topo)),
            ("$format", "json"),
        )
    )
    bruto = baixar_json(f"{BASE}{recurso}?{consulta}")
    return bruto["value"]


def _detalhe(detalhe: str | None) -> str:
    return f" and IndicadorDetalhe eq '{detalhe}'" if detalhe else ""


def anuais(
    indicador: str, *, detalhe: str | None = None, desde: date | None = None
) -> list[dict[str, Any]]:
    """Linhas (Data, DataReferencia=ano, Mediana…) das expectativas anuais, mais nova primeiro."""
    desde = desde or date.today() - timedelta(days=21)
    filtro = (
        f"Indicador eq '{indicador}'{_detalhe(detalhe)} and baseCalculo eq 0 "
        f"and Data ge '{desde.isoformat()}'"
    )
    return list(_consulta("ExpectativasMercadoAnuais", filtro))


def mediana_anual_hoje(indicador: str, *, detalhe: str | None = None) -> dict[int, float]:
    """{ano: mediana} da edição mais recente."""
    linhas = anuais(indicador, detalhe=detalhe)
    if not linhas:
        return {}
    ultima = linhas[0]["Data"]
    return {
        int(linha["DataReferencia"]): float(linha["Mediana"])
        for linha in linhas
        if linha["Data"] == ultima and linha["Mediana"] is not None
    }


def data_da_ultima_edicao(indicador: str = "IPCA") -> date:
    linhas = anuais(indicador)
    return date.fromisoformat(linhas[0]["Data"])


def historia_anual(
    indicador: str, ano: int, *, desde: date, detalhe: str | None = None
) -> list[tuple[date, float]]:
    """Como a mediana para o ano `ano` mudou desde `desde` (uma leitura por semana)."""
    filtro = (
        f"Indicador eq '{indicador}'{_detalhe(detalhe)} and baseCalculo eq 0 "
        f"and DataReferencia eq '{ano}' and Data ge '{desde.isoformat()}'"
    )
    linhas = _consulta("ExpectativasMercadoAnuais", filtro, topo=10000, ordem="Data asc")
    pontos = [
        (date.fromisoformat(linha["Data"]), float(linha["Mediana"]))
        for linha in linhas
        if linha["Mediana"] is not None
    ]
    # Sexta-feira é a data de corte do relatório que sai na segunda.
    semanais = [p for p in pontos if p[0].weekday() == 4]
    if pontos and (not semanais or semanais[-1][0] != pontos[-1][0]):
        semanais.append(pontos[-1])
    return semanais


def selic_por_reuniao() -> tuple[date, list[tuple[str, float]]]:
    """(data da edição, [(reunião 'R8/2026', mediana da Selic meta)]) em ordem de reunião."""
    desde = date.today() - timedelta(days=21)
    filtro = f"Indicador eq 'Selic' and baseCalculo eq 0 and Data ge '{desde.isoformat()}'"
    linhas = _consulta("ExpectativasMercadoSelic", filtro)
    if not linhas:
        return date.today(), []
    ultima = linhas[0]["Data"]

    def chave(reuniao: str) -> tuple[int, int]:
        numero, ano = reuniao.removeprefix("R").split("/")
        return int(ano), int(numero)

    pares = sorted(
        (
            (linha["Reuniao"], float(linha["Mediana"]))
            for linha in linhas
            if linha["Data"] == ultima and linha["Mediana"] is not None
        ),
        key=lambda par: chave(par[0]),
    )
    return date.fromisoformat(ultima), pares


def mensais_hoje(indicador: str) -> tuple[date, list[tuple[date, float]]]:
    """(data da edição, [(mês de referência, mediana)]) — ex.: IPCA de cada mês à frente."""
    desde = date.today() - timedelta(days=21)
    filtro = f"Indicador eq '{indicador}' and baseCalculo eq 0 and Data ge '{desde.isoformat()}'"
    linhas = _consulta("ExpectativaMercadoMensais", filtro)
    if not linhas:
        return date.today(), []
    ultima = linhas[0]["Data"]
    pares: list[tuple[date, float]] = []
    for linha in linhas:
        if linha["Data"] != ultima or linha["Mediana"] is None:
            continue
        mes, ano = linha["DataReferencia"].split("/")
        pares.append((date(int(ano), int(mes), 1), float(linha["Mediana"])))
    return date.fromisoformat(ultima), sorted(pares)


def trimestrais_hoje(indicador: str) -> tuple[date, list[tuple[date, float]]]:
    """(data da edição, [(1º dia do trimestre, mediana)]) — ex.: PIB Total, % a/a."""
    desde = date.today() - timedelta(days=21)
    filtro = f"Indicador eq '{indicador}' and baseCalculo eq 0 and Data ge '{desde.isoformat()}'"
    linhas = _consulta("ExpectativasMercadoTrimestrais", filtro)
    if not linhas:
        return date.today(), []
    ultima = linhas[0]["Data"]
    pares: list[tuple[date, float]] = []
    for linha in linhas:
        if linha["Data"] != ultima or linha["Mediana"] is None:
            continue
        tri, ano = linha["DataReferencia"].split("/")
        pares.append((date(int(ano), 3 * int(tri) - 2, 1), float(linha["Mediana"])))
    return date.fromisoformat(ultima), sorted(pares)
