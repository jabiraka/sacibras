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

A `dca` (Declaração de Contas Anuais, ano fechado, Governo do Estado inteiro: todos os poderes)
devolve todos os anexos numa chamada só por UF (~3 mil linhas, `anexo` + `cod_conta` + `coluna`).
Vistos em SP, RJ, MG, DF e AC (e as 27 UFs de 2025 respondem) em 14/11/2026:

- Anexo I-C (receita), coluna "Receitas Brutas Realizadas": ICMS (`RO1.1.1.4.50.1.0`, mais o
  adicional do fundo de pobreza `RO1.1.1.4.50.2.0`, que 22 UFs têm), IPVA (`RO1.1.1.2.51.0.0`),
  ITCMD (`RO1.1.1.2.52.0.0`), FPE (`RO1.7.1.1.50.0.0`), transferências correntes da União
  (`RO1.7.1.0.00.0.0`), Fundeb (`RO1.7.5.1.00.0.0`) e o total sem as intraorçamentárias
  (`ReceitasExcetoIntraOrcamentarias`).
- Anexo I-D (despesa por natureza), coluna "Despesas Liquidadas": os seis grupos (`DO3.1`, `DO3.2`,
  `DO3.3`, `DO4.4`, `DO4.5`, `DO4.6`), que somam `TotalDespesas`.
- Anexo I-E (despesa por função): a conta é sempre `TotalDespesas`; a função vem no texto da
  conta ("10 - Saúde"), mais "Despesas Exceto Intraorçamentárias".

Dívida com a União: o RGF-Anexo 02 tem `RGF2ReestruturacaoDaDividaDeEstadosEMunicipios`, o saldo da
renegociação da Lei 9.496/1997 (e afins) com o Tesouro. É o que a fonte aberta separa; empréstimos
com a União fora desses programas ficam em "Empréstimos". Os conjuntos de haveres e de estoque do
Tesouro Transparente (`saldos-devedores...por-mutuario`, `estoque-da-divida-de-estados`) pararam
em 2019/2020, então não servem para "hoje".

Armadilhas vistas em 14/11/2026: o DF é esfera D em `entes`, mas o RGF dele só responde com
`co_esfera=E`; o Amapá informa os limites em fração (0,49) e não em pontos percentuais (49), por
isso os limites saem da razão entre os valores em R$ e não da coluna de %.
"""

from __future__ import annotations

import re
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
COL_BRUTA = "Receitas Brutas Realizadas"
COL_LIQUIDADA = "Despesas Liquidadas"
VALIDADE_ANO_FECHADO = 30 * 24 * 3600.0


@dataclass(frozen=True)
class Pessoal:
    """Anexo 01 do RGF: despesa com pessoal do Executivo, em % da RCL ajustada."""

    percentual: float
    maximo: float | None
    prudencial: float | None
    alerta: float | None


@dataclass(frozen=True)
class ComposicaoDivida:
    """RGF-Anexo 02 aberto: do que é feita a dívida consolidada e o que se desconta dela (R$)."""

    total: float
    """Dívida consolidada bruta (DC)."""
    uniao: float
    """Reestruturação da dívida de estados e municípios: o que se deve ao Tesouro (Lei 9.496/97)."""
    emprestimos_internos: float
    """Empréstimos e financiamentos internos."""
    emprestimos_externos: float
    parcelamentos: float
    precatorios: float
    """Precatórios vencidos e não pagos, posteriores a 05/05/2000, dentro da dívida."""
    outras: float
    deducoes: float | None
    caixa: float | None
    """Disponibilidade de caixa (já sem restos a pagar e depósitos vinculados)."""
    haveres: float | None
    liquida: float | None


@dataclass(frozen=True)
class Divida:
    """Anexo 02 do RGF: dívida consolidada líquida e a receita corrente líquida."""

    dcl_percentual: float | None
    rcl: float | None
    """RCL dos últimos 12 meses, em R$."""
    limite: float | None
    """Limite da dívida em % da RCL ajustada, como consta do RGF."""
    alerta: float | None
    composicao: ComposicaoDivida | None = None
    """A dívida aberta em partes (mesmo anexo, mesma coluna), quando o RGF traz."""


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
    tipo: str,
    periodicidade: str,
    ano: int,
    periodo: int,
    anexo: int,
    ente: int,
    validade: float = VALIDADE,
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
        itens = baixar_json(f"{BASE}/{tipo.lower()}", params=params, validade=validade)["items"]
        time.sleep(PAUSA)
        if itens:
            return list(itens)
    return []


def rgf(ano: int, quadrimestre: int, anexo: int, ente: int) -> list[dict[str, Any]]:
    """As linhas do RGF-Anexo `anexo` do Executivo do estado `ente` (vazio se não entregou)."""
    return _demonstrativo("RGF", "Q", ano, quadrimestre, anexo, ente)


def rreo(
    ano: int, bimestre: int, anexo: int, ente: int, validade: float = VALIDADE
) -> list[dict[str, Any]]:
    """As linhas do RREO-Anexo `anexo` do Executivo do estado `ente` (vazio se não entregou)."""
    return _demonstrativo("RREO", "B", ano, bimestre, anexo, ente, validade)


def dca(ano: int, ente: int) -> list[dict[str, Any]]:
    """Todos os anexos da DCA do ano fechado do estado `ente`, numa chamada (vazio se não veio)."""
    params = {"an_exercicio": str(ano), "id_ente": str(ente)}
    itens = baixar_json(f"{BASE}/dca", params=params, validade=VALIDADE_ANO_FECHADO)["items"]
    time.sleep(PAUSA)
    return list(itens)


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
        composicao=parse_composicao_divida(itens, quadrimestre),
    )


def parse_composicao_divida(
    itens: list[dict[str, Any]], quadrimestre: int
) -> ComposicaoDivida | None:
    """RGF-Anexo 02: a dívida consolidada em partes e as deduções até a líquida (R$)."""
    coluna = f"Até o {quadrimestre}º Quadrimestre"

    def v(conta: str) -> float | None:
        return valor(itens, conta, coluna)

    total = v("DividaConsolidada")
    if total is None:
        return None
    return ComposicaoDivida(
        total=total,
        uniao=v("RGF2ReestruturacaoDaDividaDeEstadosEMunicipios") or 0.0,
        # Alguns estados (AM, BA, ES...) lançam em "Financiamentos" em vez de "Empréstimos".
        emprestimos_internos=(v("RGF2EmprestimosInternos") or 0.0)
        + (v("RGF2FinanciamentosInternos") or 0.0),
        emprestimos_externos=(v("RGF2EmprestimosExternos") or 0.0)
        + (v("RGF2FinanciamentosExternos") or 0.0),
        parcelamentos=v("RGF2ParcelamentoERenegociacaoDeDividas") or 0.0,
        precatorios=v("PrecatoriosPosterioresA05052000VencidosENaoPagos") or 0.0,
        outras=v("OutrasDividas") or 0.0,
        deducoes=v("DeducoesDaDividaConsolidada"),
        caixa=v("RGF2DisponibilidadeDeCaixa"),
        haveres=v("DemaisHaveresFinanceiros"),
        liquida=v("DividaConsolidadaLiquida"),
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


@dataclass(frozen=True)
class ReceitaAnual:
    """DCA-Anexo I-C: a receita bruta realizada do ano, em R$, aberta nas fontes que importam."""

    total: float
    """Receitas exceto intraorçamentárias."""
    icms: float | None
    """ICMS mais o adicional do fundo de combate à pobreza, que 22 UFs registram à parte."""
    ipva: float | None
    itcmd: float | None
    tributos: float | None
    """Impostos, taxas e contribuições de melhoria (o ICMS, o IPVA e o ITCMD estão aqui dentro)."""
    fpe: float | None
    uniao: float | None
    """Transferências correntes da União e de suas entidades (o FPE está aqui dentro)."""
    fundeb: float | None
    corrente: float | None
    capital: float | None


@dataclass(frozen=True)
class DespesaAnual:
    """DCA-Anexo I-D: a despesa liquidada do ano por grupo de natureza, em R$."""

    total: float
    pessoal: float
    juros: float
    outras_correntes: float
    investimentos: float
    inversoes: float
    amortizacao: float


@dataclass(frozen=True)
class FuncoesAnuais:
    """DCA-Anexo I-E: a despesa liquidada do ano por função (código de 2 dígitos), em R$."""

    total: float
    """Despesas exceto intraorçamentárias."""
    por_funcao: dict[str, tuple[str, float]]
    """{código: (nome, valor)}."""


@dataclass(frozen=True)
class ContasAnuais:
    receita: ReceitaAnual | None
    despesa: DespesaAnual | None
    funcoes: FuncoesAnuais | None


def _dca(itens: list[dict[str, Any]], anexo: str, conta: str, coluna: str) -> float | None:
    for i in itens:
        if (
            i["anexo"] == f"DCA-Anexo {anexo}"
            and i["cod_conta"] == conta
            and i["coluna"] == coluna
            and i["valor"] is not None
        ):
            return float(i["valor"])
    return None


def _soma(*partes: float | None) -> float | None:
    """A soma do que existe; `None` só se nenhuma parte existe."""
    existentes = [p for p in partes if p is not None]
    return sum(existentes) if existentes else None


def parse_receita_anual(itens: list[dict[str, Any]]) -> ReceitaAnual | None:
    def v(conta: str) -> float | None:
        return _dca(itens, "I-C", conta, COL_BRUTA)

    total = v("ReceitasExcetoIntraOrcamentarias")
    if total is None:
        return None
    return ReceitaAnual(
        total=total,
        icms=_soma(v("RO1.1.1.4.50.1.0"), v("RO1.1.1.4.50.2.0")),
        ipva=v("RO1.1.1.2.51.0.0"),
        itcmd=v("RO1.1.1.2.52.0.0"),
        tributos=v("RO1.1.0.0.00.0.0"),
        fpe=v("RO1.7.1.1.50.0.0"),
        uniao=v("RO1.7.1.0.00.0.0"),
        fundeb=v("RO1.7.5.1.00.0.0"),
        corrente=v("RO1.0.0.0.00.0.0"),
        capital=v("RO2.0.0.0.00.0.0"),
    )


def parse_despesa_anual(itens: list[dict[str, Any]]) -> DespesaAnual | None:
    """DCA-Anexo I-D: os seis grupos (`DO...`) somam o `TotalDespesas` (visto nas 27 UFs)."""

    def grupo(sufixo: str) -> float:
        return _dca(itens, "I-D", f"DO{sufixo}", COL_LIQUIDADA) or 0.0

    total = _dca(itens, "I-D", "TotalDespesas", COL_LIQUIDADA)
    if total is None:
        return None
    return DespesaAnual(
        total=total,
        pessoal=grupo("3.1.00.00.00.00"),
        juros=grupo("3.2.00.00.00.00"),
        outras_correntes=grupo("3.3.00.00.00.00"),
        investimentos=grupo("4.4.00.00.00.00"),
        inversoes=grupo("4.5.00.00.00.00"),
        amortizacao=grupo("4.6.00.00.00.00"),
    )


_FUNCAO = re.compile(r"^(\d{2}) - (.+)$")


def parse_funcoes_anuais(itens: list[dict[str, Any]]) -> FuncoesAnuais | None:
    """DCA-Anexo I-E: as linhas de função ("10 - Saúde") vêm todas com a conta `TotalDespesas`."""
    total: float | None = None
    funcoes: dict[str, tuple[str, float]] = {}
    for i in itens:
        if i["anexo"] != "DCA-Anexo I-E" or i["coluna"] != COL_LIQUIDADA or i["valor"] is None:
            continue
        if i["conta"] == "Despesas Exceto Intraorçamentárias":
            total = float(i["valor"])
        elif achou := _FUNCAO.match(i["conta"]):
            funcoes[achou.group(1)] = (achou.group(2).strip(), float(i["valor"]))
    if total is None or not funcoes:
        return None
    return FuncoesAnuais(total=total, por_funcao=funcoes)


def parse_dca(itens: list[dict[str, Any]]) -> ContasAnuais | None:
    """A receita, a despesa por grupo e a despesa por função da DCA; `None` se não veio nada."""
    contas = ContasAnuais(
        receita=parse_receita_anual(itens),
        despesa=parse_despesa_anual(itens),
        funcoes=parse_funcoes_anuais(itens),
    )
    if contas.receita is None and contas.despesa is None and contas.funcoes is None:
        return None
    return contas


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


@dataclass
class ColetaAnual:
    ano: int
    dca: dict[int, ContasAnuais | None]
    rcl: dict[int, float | None]
    """RCL do ano fechado (RREO-Anexo 03 do 6º bimestre, 12 meses), em R$."""


def coletar_anual(entes_ibge: list[int], hoje: date, minimo: int = 24) -> ColetaAnual | None:
    """A DCA do ano fechado mais recente em que ao menos `minimo` estados já entregaram.

    O ano fechado (e não o bimestre corrente) é o que todas as UFs têm e o que fecha as contas.
    Por UF: uma chamada da `dca` (todos os anexos) e uma do RREO-Anexo 03 do 6º bimestre (a RCL).
    """
    sondagem = [35, 31, 33, 29, 43]
    for ano in (hoje.year - 1, hoje.year - 2):
        try:
            if not any(dca(ano, e) for e in sondagem if e in entes_ibge):
                continue
        except FonteForaDoArError as erro:
            _aviso(sondagem[0], erro)
            continue
        contas: dict[int, ContasAnuais | None] = {}
        rcl: dict[int, float | None] = {}
        for e in entes_ibge:
            try:
                contas[e] = parse_dca(dca(ano, e))
            except FonteForaDoArError as erro:
                contas[e] = None
                _aviso(e, erro)
            try:
                r = parse_receita(rreo(ano, 6, 3, e, VALIDADE_ANO_FECHADO))
                rcl[e] = r.rcl if r else None
            except FonteForaDoArError as erro:
                rcl[e] = None
                _aviso(e, erro)
        if sum(c is not None for c in contas.values()) < minimo:
            continue
        return ColetaAnual(ano, contas, rcl)
    return None
