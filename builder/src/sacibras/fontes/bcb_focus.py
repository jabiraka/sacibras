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


def _consulta(
    recurso: str,
    filtro: str,
    *,
    topo: int = 5000,
    ordem: str = "Data desc",
    validade: float | None = None,
) -> Any:
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
    bruto = baixar_json(f"{BASE}{recurso}?{consulta}", validade=validade)
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


def inflacao_12_meses(desde: date) -> list[tuple[date, float]]:
    """A mediana do IPCA dos 12 meses seguintes, suavizada (a que o BC usa: pesa os dois anos
    do calendário pelos meses de cada um), um ponto por dia de coleta. Conferido em
    15/11/2026: `ExpectativasMercadoInflacao12Meses`, desde 12/12/2001."""
    filtro = (
        "Indicador eq 'IPCA' and Suavizada eq 'S' and baseCalculo eq 0 "
        f"and Data ge '{desde.isoformat()}'"
    )
    linhas = _consulta("ExpectativasMercadoInflacao12Meses", filtro, topo=10000, ordem="Data asc")
    return [
        (date.fromisoformat(linha["Data"]), float(linha["Mediana"]))
        for linha in linhas
        if linha["Mediana"] is not None
    ]


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


def mediana_em(
    indicador: str, alvo: int, quando: date, *, detalhe: str | None = None
) -> float | None:
    """A mediana para o ano `alvo` na edição do Focus vigente em `quando` (a última das duas
    semanas anteriores). Edição antiga não muda: fica um mês no cache."""
    filtro = (
        f"Indicador eq '{indicador}'{_detalhe(detalhe)} and baseCalculo eq 0 "
        f"and DataReferencia eq '{alvo}' and Data ge '{(quando - timedelta(days=14)).isoformat()}' "
        f"and Data le '{quando.isoformat()}'"
    )
    linhas = _consulta("ExpectativasMercadoAnuais", filtro, topo=20, validade=30 * 86400)
    for linha in linhas:
        if linha["Mediana"] is not None:
            return float(linha["Mediana"])
    return None


def medianas_no_tempo(
    recurso: str, indicador: str, desde: date, *, campo: str = "DataReferencia"
) -> list[tuple[str, date, float]]:
    """[(referência, dia da coleta, mediana)], da coleta mais nova à mais antiga.

    `recurso`: `ExpectativaMercadoMensais` (referência "10/2026"),
    `ExpectativasMercadoTrimestrais` ("3/2026") ou `ExpectativasMercadoSelic` (com
    `campo="Reuniao"`, "R7/2026"). O Focus para de coletar a referência quando o número sai:
    a coleta mais nova de um mês já divulgado é a da véspera (conferido em 16/11/2026: a do
    IPCA de out/2026 é de 06/11 e a de set/2026 é de 08/10)."""
    filtro = f"Indicador eq '{indicador}' and baseCalculo eq 0 and Data ge '{desde.isoformat()}'"
    linhas = _consulta(recurso, filtro, topo=10000)
    return [
        (str(linha[campo]), date.fromisoformat(linha["Data"]), float(linha["Mediana"]))
        for linha in linhas
        if linha["Mediana"] is not None and linha.get(campo)
    ]


def selic_antes_das_reunioes(
    reunioes: list[tuple[str, date]], *, lote: int = 50
) -> dict[str, tuple[date, float]]:
    """{reunião "R7/2026": (dia da coleta, mediana da Selic)}: a última coleta do Focus nos
    sete dias antes de cada reunião. Uma consulta por lote de reuniões (a Olinda aceita o
    filtro com dezenas de cláusulas; conferido em 17/11/2026), para não fazer uma por ano."""
    saida: dict[str, tuple[date, float]] = {}
    for i in range(0, len(reunioes), lote):
        partes = [
            f"(Reuniao eq '{rotulo}' and Data ge '{(dia - timedelta(days=7)).isoformat()}' "
            f"and Data lt '{dia.isoformat()}')"
            for rotulo, dia in reunioes[i : i + lote]
        ]
        filtro = f"Indicador eq 'Selic' and baseCalculo eq 0 and ({' or '.join(partes)})"
        for linha in _consulta("ExpectativasMercadoSelic", filtro, topo=10000, validade=7 * 86400):
            if linha["Mediana"] is None:
                continue
            coleta = date.fromisoformat(linha["Data"])
            if linha["Reuniao"] not in saida or coleta > saida[linha["Reuniao"]][0]:
                saida[linha["Reuniao"]] = (coleta, float(linha["Mediana"]))
    return saida


def anuais_nas_datas(indicador: str, datas: list[date]) -> dict[date, dict[int, float]]:
    """{dia da coleta: {ano: mediana}} só nos dias pedidos (uma consulta só, com as datas no
    filtro). Dia sem coleta (feriado) fica de fora: peça dois dias vizinhos."""
    if not datas:
        return {}
    clausulas = " or ".join(f"Data eq '{d.isoformat()}'" for d in sorted(set(datas)))
    filtro = f"Indicador eq '{indicador}' and baseCalculo eq 0 and ({clausulas})"
    saida: dict[date, dict[int, float]] = {}
    for linha in _consulta("ExpectativasMercadoAnuais", filtro, topo=10000, validade=7 * 86400):
        if linha["Mediana"] is None:
            continue
        dia = date.fromisoformat(linha["Data"])
        saida.setdefault(dia, {})[int(linha["DataReferencia"])] = float(linha["Mediana"])
    return saida
