"""SICONFI (Tesouro Nacional): o Relatório de Gestão Fiscal (RGF) e o RREO dos estados.

`apidatalake.tesouro.gov.br/ords/siconfi/tt/`. O `rgf` devolve uma linha por conta e coluna do
demonstrativo (`cod_conta` + `coluna` + `valor`). Do Poder Executivo estadual (`co_poder=E`):

- Anexo 01 (despesa com pessoal): `DespesaComPessoalTotal`, coluna "% sobre a RCL Ajustada", e as
  contas de limite (máximo, prudencial e de alerta), em "Valor" (R$) e em "% sobre a RCL Ajustada".
- Anexo 02 (dívida): `PercentualDaDCLSobreARCL`, `RGF2ReceitaCorrenteLiquida` e o limite
  (`LimiteDefinidoPorResolucaoDoSenadoFederal`), na coluna "Até o Nº Quadrimestre".

O `rreo` (Relatório Resumido da Execução Orçamentária, bimestral, `in_periodicidade=B`) tem o mesmo
formato. Do Executivo estadual:

- Anexo 03 (receita corrente líquida): `ICMSLiquidoExcetoTransferenciasEFUNDEB` (o ICMS já sem as
  transferências aos municípios e o FUNDEB) e `RREO3ReceitaCorrenteLiquida`, os dois na coluna
  "TOTAL (ÚLTIMOS 12 MESES)", em R$.
- Anexo 06 (resultado primário e nominal): `ResultadoPrimarioSemRPPSAcimaDaLinha`, coluna "VALOR",
  em R$, acumulado do ano até o bimestre. A "com RPPS" também existe, mas soma o resultado dos
  fundos de previdência próprios, que cada estado tem num tamanho; a "sem RPPS" é a que a LDO usa
  como meta e a mais comparável. Vista em SP, DF e AC em 14/11/2026 (4º bimestre de 2026; o 5º
  ainda voltava vazio).

Armadilhas vistas em 14/11/2026: o DF é esfera D em `entes`, mas o RGF dele só responde com
`co_esfera=E`; o Amapá informa os limites em fração (0,49) e não em pontos percentuais (49), por
isso os limites saem da razão entre os valores em R$ e não da coluna de %.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from datetime import date
from typing import Any

from sacibras.rede import FonteForaDoArError, baixar_json

BASE = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
DF = 53
PAUSA = 0.3
VALIDADE = 24 * 3600.0

COL_PCT = "% sobre a RCL Ajustada"
COL_12M = "TOTAL (ÚLTIMOS 12 MESES)"
COL_PRIMARIO = "VALOR"


@dataclass(frozen=True)
class Pessoal:
    """Anexo 01 do RGF: despesa com pessoal do Executivo, em % da RCL ajustada."""

    percentual: float
    maximo: float | None
    prudencial: float | None
    alerta: float | None


@dataclass(frozen=True)
class Divida:
    """Anexo 02 do RGF: dívida consolidada líquida e a receita corrente líquida."""

    dcl_percentual: float | None
    rcl: float | None
    """RCL dos últimos 12 meses, em R$."""
    limite: float | None
    """Limite da dívida em % da RCL ajustada, como consta do RGF."""
    alerta: float | None


@dataclass(frozen=True)
class Receita:
    """RREO-Anexo 03: o ICMS líquido e a receita corrente líquida dos últimos 12 meses, em R$."""

    icms: float | None
    rcl: float | None


def entes() -> dict[int, float]:
    """{código IBGE: população} das 26 UFs e do DF (a esfera do DF no cadastro é D)."""
    bruto = baixar_json(f"{BASE}/entes", validade=VALIDADE)
    return {
        int(e["cod_ibge"]): float(e["populacao"])
        for e in bruto["items"]
        if e.get("populacao") and (e.get("esfera") == "E" or int(e["cod_ibge"]) == DF)
    }


def _demonstrativo(
    tipo: str, periodicidade: str, ano: int, periodo: int, anexo: int, ente: int
) -> list[dict[str, Any]]:
    """As linhas de um anexo do Executivo do estado `ente` (vazio se não entregou)."""
    for esfera in ("E", "D") if ente == DF else ("E",):
        params = {
            "an_exercicio": str(ano),
            "in_periodicidade": periodicidade,
            "nr_periodo": str(periodo),
            "co_tipo_demonstrativo": tipo,
            "no_anexo": f"{tipo}-Anexo {anexo:02d}",
            "co_esfera": esfera,
            "co_poder": "E",
            "id_ente": str(ente),
        }
        itens = baixar_json(f"{BASE}/{tipo.lower()}", params=params, validade=VALIDADE)["items"]
        time.sleep(PAUSA)
        if itens:
            return list(itens)
    return []


def rgf(ano: int, quadrimestre: int, anexo: int, ente: int) -> list[dict[str, Any]]:
    """As linhas do RGF-Anexo `anexo` do Executivo do estado `ente` (vazio se não entregou)."""
    return _demonstrativo("RGF", "Q", ano, quadrimestre, anexo, ente)


def rreo(ano: int, bimestre: int, anexo: int, ente: int) -> list[dict[str, Any]]:
    """As linhas do RREO-Anexo `anexo` do Executivo do estado `ente` (vazio se não entregou)."""
    return _demonstrativo("RREO", "B", ano, bimestre, anexo, ente)


def valor(itens: list[dict[str, Any]], conta: str, coluna: str) -> float | None:
    for i in itens:
        if i["cod_conta"] == conta and i["coluna"] == coluna and i["valor"] is not None:
            return float(i["valor"])
    return None


def _razao(itens: list[dict[str, Any]], conta: str, base: float | None) -> float | None:
    """O limite em % da base, pelos valores em R$ (a coluna de % vem em fração em alguns)."""
    v = valor(itens, conta, "Valor")
    if v is None or not base:
        return None
    return round(v / base * 100, 2)


def parse_pessoal(itens: list[dict[str, Any]]) -> Pessoal | None:
    pct = valor(itens, "DespesaComPessoalTotal", COL_PCT)
    if pct is None:
        return None
    base = valor(itens, "ReceitaCorrenteLiquidaAjustada", "Valor")

    def limite(conta: str) -> float | None:
        r = _razao(itens, conta, base)
        return r if r is not None else valor(itens, conta, COL_PCT)

    return Pessoal(
        percentual=pct,
        maximo=limite("LimiteMaximoDespesaComPessoalTotal"),
        prudencial=limite("LimitePrudencialDespesaComPessoalTotal"),
        alerta=limite("LimiteDeAlertaDespesaComPessoalTotal"),
    )


def parse_divida(itens: list[dict[str, Any]], quadrimestre: int) -> Divida | None:
    coluna = f"Até o {quadrimestre}º Quadrimestre"
    dcl = valor(itens, "PercentualDaDCLSobreARCL", coluna)
    rcl = valor(itens, "RGF2ReceitaCorrenteLiquida", coluna)
    if dcl is None and rcl is None:
        return None
    base = valor(
        itens, "ReceitaCorrenteLiquidaAjustadaParaCalculoDosLimitesDeEndividamento", coluna
    )

    def limite(conta: str) -> float | None:
        v = valor(itens, conta, coluna)
        return round(v / base * 100, 2) if v is not None and base else None

    return Divida(
        dcl_percentual=dcl,
        rcl=rcl,
        limite=limite("LimiteDefinidoPorResolucaoDoSenadoFederal"),
        alerta=limite("LimiteDeAlerta"),
    )


def parse_receita(itens: list[dict[str, Any]]) -> Receita | None:
    """RREO-Anexo 03: ICMS líquido de transferências e do FUNDEB, e a RCL, em 12 meses."""
    icms = valor(itens, "ICMSLiquidoExcetoTransferenciasEFUNDEB", COL_12M)
    rcl = valor(itens, "RREO3ReceitaCorrenteLiquida", COL_12M)
    if icms is None and rcl is None:
        return None
    return Receita(icms=icms, rcl=rcl)


def parse_primario(itens: list[dict[str, Any]]) -> float | None:
    """RREO-Anexo 06: resultado primário sem RPPS, acima da linha, no ano até o bimestre (R$)."""
    return valor(itens, "ResultadoPrimarioSemRPPSAcimaDaLinha", COL_PRIMARIO)


def candidatos(hoje: date, quantos: int = 4) -> list[tuple[int, int]]:
    """(ano, quadrimestre) do corrente para trás: o quadrimestre só sai semanas depois de fechar."""
    ano, q = hoje.year, (hoje.month - 1) // 4 + 1
    saida = []
    for _ in range(quantos):
        saida.append((ano, q))
        ano, q = (ano - 1, 3) if q == 1 else (ano, q - 1)
    return saida


def bimestres(hoje: date, quantos: int = 4) -> list[tuple[int, int]]:
    """(ano, bimestre) do corrente para trás: o bimestre só sai semanas depois de fechar."""
    ano, b = hoje.year, (hoje.month - 1) // 2 + 1
    saida = []
    for _ in range(quantos):
        saida.append((ano, b))
        ano, b = (ano - 1, 6) if b == 1 else (ano, b - 1)
    return saida


@dataclass
class ColetaRgf:
    ano: int
    quadrimestre: int
    pessoal: dict[int, Pessoal | None]
    divida: dict[int, Divida | None]


def _aviso(ente: int, erro: Exception) -> None:
    print(f"  aviso: SICONFI sem dado para o ente {ente}: {erro}", file=sys.stderr)


def coletar(entes_ibge: list[int], hoje: date, minimo: int = 24) -> ColetaRgf | None:
    """O RGF do período mais recente em que ao menos `minimo` estados já entregaram o Anexo 01.

    Um período só para todos: estado que ainda não entregou fica `None`, e não com o anterior.
    """
    sondagem = [35, 31, 33, 29, 43]  # SP, MG, RJ, BA, RS: se nenhum entregou, nem varre o resto
    for ano, q in candidatos(hoje):
        try:
            if not any(rgf(ano, q, 1, e) for e in sondagem if e in entes_ibge):
                continue
        except FonteForaDoArError as erro:
            _aviso(sondagem[0], erro)
            continue
        pessoal: dict[int, Pessoal | None] = {}
        for e in entes_ibge:
            try:
                pessoal[e] = parse_pessoal(rgf(ano, q, 1, e))
            except FonteForaDoArError as erro:
                pessoal[e] = None
                _aviso(e, erro)
        if sum(p is not None for p in pessoal.values()) < minimo:
            continue
        divida: dict[int, Divida | None] = {}
        for e in entes_ibge:
            try:
                divida[e] = parse_divida(rgf(ano, q, 2, e), q)
            except FonteForaDoArError as erro:
                divida[e] = None
                _aviso(e, erro)
        return ColetaRgf(ano, q, pessoal, divida)
    return None


@dataclass
class ColetaRreo:
    ano: int
    bimestre: int
    receita: dict[int, Receita | None]
    primario: dict[int, float | None]
    """Resultado primário (sem RPPS) do ano até o bimestre, em R$."""


def coletar_rreo(entes_ibge: list[int], hoje: date, minimo: int = 24) -> ColetaRreo | None:
    """O RREO do bimestre mais recente em que ao menos `minimo` estados já entregaram o Anexo 03.

    Um bimestre só para todos, como no RGF. Quem não entregou fica `None`.
    """
    sondagem = [35, 31, 33, 29, 43]
    for ano, b in bimestres(hoje):
        try:
            if not any(rreo(ano, b, 3, e) for e in sondagem if e in entes_ibge):
                continue
        except FonteForaDoArError as erro:
            _aviso(sondagem[0], erro)
            continue
        receita: dict[int, Receita | None] = {}
        for e in entes_ibge:
            try:
                receita[e] = parse_receita(rreo(ano, b, 3, e))
            except FonteForaDoArError as erro:
                receita[e] = None
                _aviso(e, erro)
        if sum(r is not None for r in receita.values()) < minimo:
            continue
        primario: dict[int, float | None] = {}
        for e in entes_ibge:
            try:
                primario[e] = parse_primario(rreo(ano, b, 6, e))
            except FonteForaDoArError as erro:
                primario[e] = None
                _aviso(e, erro)
        return ColetaRreo(ano, b, receita, primario)
    return None
