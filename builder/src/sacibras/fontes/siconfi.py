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
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date
from functools import partial
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
    demais_contratuais: float = 0.0
    """"Demais dívidas contratuais" (TO e PR lançam parte da dívida aqui)."""


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
    esfera_do_ente: str = "E",
) -> list[dict[str, Any]]:
    """As linhas de um anexo do Executivo do ente (vazio se não entregou). `esfera_do_ente` é
    "E" para os estados e "M" para os municípios (as capitais)."""
    esferas = ("E", "D") if ente == DF and esfera_do_ente == "E" else (esfera_do_ente,)
    for esfera in esferas:
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


def rgf(
    ano: int, quadrimestre: int, anexo: int, ente: int, esfera: str = "E"
) -> list[dict[str, Any]]:
    """As linhas do RGF-Anexo `anexo` do Executivo do ente (vazio se não entregou)."""
    if esfera == "E":
        return _demonstrativo("RGF", "Q", ano, quadrimestre, anexo, ente)
    return _demonstrativo("RGF", "Q", ano, quadrimestre, anexo, ente, esfera_do_ente=esfera)


PODERES_DA_UNIAO = {
    "E": "Executivo",
    "J": "Judiciário",
    "L": "Legislativo (com o TCU)",
    "M": "Ministério Público da União",
    "D": "Defensoria Pública da União",
}
"""`co_poder` do RGF da União. Conferido em 19/11/2026 no 3º quadrimestre de 2025: o
Executivo vem num demonstrativo só (linhas "União", "Distrito Federal", "Amapá" e "Roraima":
as três últimas são o que a União paga de pessoal do DF e dos ex-territórios); o Judiciário,
num por tribunal (mais de 90), em páginas de 5.000 linhas; o Legislativo, em três (Câmara,
Senado e TCU)."""
CONTA_BRUTA = "DespesaComPessoalBruta"
CONTA_LIQUIDA = "DespesaComPessoalLiquida"
COL_12_MESES = "TOTAL (ÚLTIMOS 12 MESES)"
PAGINA = 5000


def rgf_da_uniao(ano: int, quadrimestre: int, poder: str) -> list[dict[str, Any]]:
    """Todas as linhas do RGF-Anexo 01 dos órgãos de um poder da União (a API pagina)."""
    itens: list[dict[str, Any]] = []
    while True:
        params = {
            "an_exercicio": str(ano),
            "in_periodicidade": "Q",
            "nr_periodo": str(quadrimestre),
            "co_tipo_demonstrativo": "RGF",
            "no_anexo": "RGF-Anexo 01",
            "co_esfera": "U",
            "co_poder": poder,
            "id_ente": "1",
            "offset": str(len(itens)),
        }
        resposta = baixar_json(f"{BASE}/rgf", params=params, validade=VALIDADE, tempo_limite=120)
        pagina = list(resposta["items"])
        itens += pagina
        time.sleep(PAUSA)
        if len(pagina) < PAGINA or not resposta.get("hasMore", True):
            return itens


def pessoal_do_poder(itens: list[dict[str, Any]]) -> tuple[float, int] | None:
    """(despesa bruta com pessoal em 12 meses, em R$; quantos órgãos) de um poder: a soma dos
    demonstrativos. Órgão que só informa a despesa líquida (a Defensoria) entra por ela."""
    por_orgao: dict[tuple[str, str], dict[str, float]] = {}
    for i in itens:
        coluna = re.sub(r"\s+", " ", str(i.get("coluna", "")))
        if not coluna.startswith(COL_12_MESES) or i.get("cod_conta") not in (
            CONTA_BRUTA,
            CONTA_LIQUIDA,
        ):
            continue
        if i.get("valor") is None:
            continue
        orgao = (str(i.get("instituicao", "")), str(i.get("rotulo", "")))
        por_orgao.setdefault(orgao, {})[str(i["cod_conta"])] = float(i["valor"])
    if not por_orgao:
        return None
    total = sum(v.get(CONTA_BRUTA, v.get(CONTA_LIQUIDA, 0.0)) for v in por_orgao.values())
    return total, len({orgao for orgao, _ in por_orgao})


def pessoal_da_uniao_por_poder(hoje: date) -> tuple[int, dict[str, tuple[float, int]]] | None:
    """(ano, {poder: (R$ em 12 meses até dezembro, órgãos)}) do último ano fechado em que os
    cinco poderes entregaram o RGF do 3º quadrimestre."""
    for ano in (hoje.year - 1, hoje.year - 2):
        achados: dict[str, tuple[float, int]] = {}
        for poder in PODERES_DA_UNIAO:
            soma = pessoal_do_poder(rgf_da_uniao(ano, 3, poder))
            if soma is None:
                break
            achados[poder] = soma
        if len(achados) == len(PODERES_DA_UNIAO):
            return ano, achados
    return None


def rreo(
    ano: int,
    bimestre: int,
    anexo: int,
    ente: int,
    validade: float = VALIDADE,
    esfera: str = "E",
) -> list[dict[str, Any]]:
    """As linhas do RREO-Anexo `anexo` do Executivo do ente (vazio se não entregou)."""
    if esfera == "E":
        return _demonstrativo("RREO", "B", ano, bimestre, anexo, ente, validade)
    return _demonstrativo("RREO", "B", ano, bimestre, anexo, ente, validade, esfera)


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
        demais_contratuais=v("RGF2DemaisDividasContratuais") or 0.0,
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


# ---------------------------------------------------------------- previdência e anos fechados
#
# RREO-Anexo 04 (receitas e despesas previdenciárias), visto em SP, RJ, ES e RS em 15/11/2026,
# 6º bimestre de 2021 a 2025: o resultado de cada plano vem nas colunas de despesa; a de
# "DESPESAS LIQUIDADAS ATÉ O BIMESTRE (e)" é o ano inteiro no 6º bimestre. Até 2020 o anexo era
# outro (os militares dentro do plano financeiro, colunas "/ 2019"): a série começa em 2021.
# - `RREO4ResultadoRPPSFinanceiro`: o fundo em repartição (plano financeiro), quase sempre no
#   vermelho: o Tesouro do estado cobre a diferença.
# - `ResultadoDosBeneficiosMantidosPeloTesouro`: aposentadorias pagas direto pelo Tesouro.
# - `ResultadoAssociadoAInativosEPensionistasMilirares`: inativos e pensionistas militares.
# - `RREO4ResultadoRPPSPrevidenciario`: o fundo em capitalização (plano previdenciário), que
#   guarda para os servidores mais novos e costuma sobrar; fica fora do resultado, porque a
#   sobra fica aplicada para o futuro e não paga as aposentadorias de hoje.
#
# Resultado primário nos anos fechados (RREO-Anexo 06): desde 2023 o anexo separa "com RPPS" e
# "sem RPPS"; até 2022 só havia `RREO6ResultadoPrimarioEstadosMunicipios`, que inclui o RPPS
# (coluna "VALOR", ou "VALOR INCORRIDO" em 2019 e 2020). A série no tempo usa a "com RPPS" para
# não mudar de conta no meio.

COL_LIQUIDADA_BIMESTRE = "DESPESAS LIQUIDADAS ATÉ O BIMESTRE (e)"
PREVIDENCIA_DESDE = 2021
RGF_DESDE = 2019


@dataclass(frozen=True)
class Previdencia:
    """RREO-Anexo 04: o resultado da previdência no ano até o bimestre, em R$ (negativo é
    déficit)."""

    reparticao: float
    tesouro: float
    militares: float
    capitalizacao: float | None

    @property
    def resultado(self) -> float:
        """O que o Tesouro do estado cobre: repartição, benefícios do Tesouro e militares."""
        return self.reparticao + self.tesouro + self.militares


def parse_previdencia(itens: list[dict[str, Any]]) -> Previdencia | None:
    def v(conta: str) -> float | None:
        return valor(itens, conta, COL_LIQUIDADA_BIMESTRE)

    partes = (
        v("RREO4ResultadoRPPSFinanceiro"),
        v("ResultadoDosBeneficiosMantidosPeloTesouro"),
        v("ResultadoAssociadoAInativosEPensionistasMilirares"),
    )
    if all(p is None for p in partes):
        return None
    return Previdencia(
        reparticao=partes[0] or 0.0,
        tesouro=partes[1] or 0.0,
        militares=partes[2] or 0.0,
        capitalizacao=v("RREO4ResultadoRPPSPrevidenciario"),
    )


def parse_primario_com_rpps(itens: list[dict[str, Any]]) -> float | None:
    """RREO-Anexo 06: o primário com a previdência própria, pela conta de cada edição."""
    for conta, coluna in (
        ("ResultadoPrimarioComRPPSAcimaDaLinha", COL_PRIMARIO),
        ("RREO6ResultadoPrimarioEstadosMunicipios", COL_PRIMARIO),
        ("RREO6ResultadoPrimarioEstadosMunicipios", "VALOR INCORRIDO"),
    ):
        achado = valor(itens, conta, coluna)
        if achado is not None:
            return achado
    return None


@dataclass(frozen=True)
class PessoalAnual:
    percentual: float
    despesa: float | None
    base: float | None
    """RCL ajustada (a base do limite), em R$."""


def parse_pessoal_anual(itens: list[dict[str, Any]]) -> PessoalAnual | None:
    """RGF-Anexo 01 com os reais: o percentual e a soma de vários estados saem da mesma conta."""
    despesa = valor(itens, "DespesaComPessoalTotal", "Valor")
    base = valor(itens, "ReceitaCorrenteLiquidaAjustada", "Valor")
    pct = valor(itens, "DespesaComPessoalTotal", COL_PCT)
    if pct is None and despesa is not None and base:
        pct = despesa / base * 100
    if pct is None:
        return None
    return PessoalAnual(percentual=pct, despesa=despesa, base=base)


@dataclass(frozen=True)
class DividaAnual:
    percentual: float | None
    liquida: float | None
    base: float | None
    """RCL ajustada para os limites de endividamento, em R$."""
    rcl: float | None


def parse_divida_anual(itens: list[dict[str, Any]], quadrimestre: int = 3) -> DividaAnual | None:
    coluna = f"Até o {quadrimestre}º Quadrimestre"
    pct = valor(itens, "PercentualDaDCLSobreARCL", coluna)
    rcl = valor(itens, "RGF2ReceitaCorrenteLiquida", coluna)
    if pct is None and rcl is None:
        return None
    base = valor(
        itens, "ReceitaCorrenteLiquidaAjustadaParaCalculoDosLimitesDeEndividamento", coluna
    )
    return DividaAnual(
        percentual=pct,
        liquida=valor(itens, "DividaConsolidadaLiquida", coluna),
        base=base if base else rcl,
        rcl=rcl,
    )


@dataclass
class AnoFechado:
    """O que um estado entregou no fim de um ano: RGF do 3º quadrimestre, RREO do 6º bimestre."""

    pessoal: PessoalAnual | None = None
    divida: DividaAnual | None = None
    primario: float | None = None
    """Com RPPS, no ano, em R$."""
    previdencia: Previdencia | None = None


def ultimo_ano_fechado(hoje: date) -> int:
    """O RGF do 3º quadrimestre e o RREO do 6º bimestre saem até o fim de janeiro."""
    return hoje.year - 1 if hoje.month >= 3 else hoje.year - 2


def coletar_historico(
    entes_ibge: list[int], hoje: date, trabalhadores: int = 6
) -> dict[int, dict[int, AnoFechado]]:
    """{ano: {ente: AnoFechado}} dos anos fechados: o RGF desde `RGF_DESDE`, o RREO desde
    `PREVIDENCIA_DESDE`. São ~650 chamadas: vão em paralelo (`trabalhadores` de cada vez) e,
    por serem de ano fechado, ficam 30 dias no cache."""
    ultimo = ultimo_ano_fechado(hoje)
    tarefas: list[tuple[str, int, int]] = []
    for ano in range(RGF_DESDE, ultimo + 1):
        for e in entes_ibge:
            tarefas += [("pessoal", ano, e), ("divida", ano, e)]
            if ano >= PREVIDENCIA_DESDE:
                tarefas += [("primario", ano, e), ("previdencia", ano, e)]

    def fazer(tarefa: tuple[str, int, int]) -> object:
        tipo, ano, e = tarefa
        try:
            if tipo == "pessoal":
                return parse_pessoal_anual(
                    _demonstrativo("RGF", "Q", ano, 3, 1, e, VALIDADE_ANO_FECHADO)
                )
            if tipo == "divida":
                return parse_divida_anual(
                    _demonstrativo("RGF", "Q", ano, 3, 2, e, VALIDADE_ANO_FECHADO)
                )
            if tipo == "primario":
                return parse_primario_com_rpps(rreo(ano, 6, 6, e, VALIDADE_ANO_FECHADO))
            return parse_previdencia(rreo(ano, 6, 4, e, VALIDADE_ANO_FECHADO))
        except FonteForaDoArError as erro:
            _aviso(e, erro)
            return None

    with ThreadPoolExecutor(max_workers=trabalhadores) as grupo:
        resultados = list(grupo.map(fazer, tarefas))
    saida: dict[int, dict[int, AnoFechado]] = {}
    for (tipo, ano, e), achado in zip(tarefas, resultados, strict=True):
        if achado is None:
            continue
        setattr(saida.setdefault(ano, {}).setdefault(e, AnoFechado()), tipo, achado)
    return saida


# ------------------------------------------------------------------ capitais

# As capitais respondem ao mesmo RGF e RREO, com `co_esfera=M` e os mesmos códigos de conta
# (conferido em São Paulo, 3550308, no RGF do 2º quadrimestre e no RREO do 4º bimestre de
# 2026, em 15/11/2026: pessoal 26,08 % da RCL, limite máximo 54 %, dívida 14,73 %, limite em
# R$ igual a 1,2 vez a RCL ajustada). Brasília não tem relatório municipal: o DF é estado.
SONDAGEM_CAPITAIS = [3550308, 3304557, 3106200]  # São Paulo, Rio de Janeiro, Belo Horizonte


def capitais() -> dict[str, tuple[int, str]]:
    """{sigla da UF: (código IBGE, nome)} das capitais com relatório municipal (sem Brasília)."""
    bruto = baixar_json(f"{BASE}/entes", validade=VALIDADE)
    return {
        str(e["uf"]).strip(): (int(e["cod_ibge"]), str(e["ente"]).strip())
        for e in bruto["items"]
        if str(e.get("capital", "")).strip() == "1"
        and e.get("esfera") == "M"
        and str(e["uf"]).strip() != "DF"
    }


@dataclass
class ColetaCapitais:
    ano: int
    quadrimestre: int
    pessoal: dict[int, Pessoal | None]
    divida: dict[int, Divida | None]
    bimestre: tuple[int, int] | None = None
    """(ano, bimestre) do RREO, quando houve um com quase todas as capitais."""
    primario: dict[int, float | None] = field(default_factory=dict)
    """Resultado primário (sem RPPS) do ano até o bimestre, em R$."""
    rcl: dict[int, float | None] = field(default_factory=dict)
    """RCL de 12 meses no mesmo bimestre (RREO-Anexo 03), em R$."""


def _em_paralelo[T](tarefa: Callable[[int], T | None], cods: list[int]) -> dict[int, T | None]:
    def fazer(e: int) -> T | None:
        try:
            return tarefa(e)
        except FonteForaDoArError as erro:
            _aviso(e, erro)
            return None

    with ThreadPoolExecutor(max_workers=6) as grupo:
        return dict(zip(cods, grupo.map(fazer, cods), strict=True))


def _pessoal_municipal(ano: int, q: int, e: int) -> Pessoal | None:
    return parse_pessoal(rgf(ano, q, 1, e, "M"))


def _divida_municipal(ano: int, q: int, e: int) -> Divida | None:
    return parse_divida(rgf(ano, q, 2, e, "M"), q)


def _receita_municipal(ano: int, b: int, e: int) -> Receita | None:
    return parse_receita(rreo(ano, b, 3, e, esfera="M"))


def _primario_municipal(ano: int, b: int, e: int) -> float | None:
    return parse_primario(rreo(ano, b, 6, e, esfera="M"))


def coletar_capitais(cods: list[int], hoje: date, minimo: int = 20) -> ColetaCapitais | None:
    """O RGF do quadrimestre mais recente em que ao menos `minimo` capitais entregaram o Anexo
    01, e o RREO do bimestre mais recente com o mesmo tanto. Um período só para todas."""
    sondagem = [c for c in SONDAGEM_CAPITAIS if c in cods] or cods[:3]
    for ano, q in candidatos(hoje):
        try:
            if not any(rgf(ano, q, 1, e, "M") for e in sondagem):
                continue
        except FonteForaDoArError as erro:
            _aviso(sondagem[0], erro)
            continue

        pessoal = _em_paralelo(partial(_pessoal_municipal, ano, q), cods)
        if sum(p is not None for p in pessoal.values()) < minimo:
            continue
        coleta = ColetaCapitais(
            ano, q, pessoal, _em_paralelo(partial(_divida_municipal, ano, q), cods)
        )
        for ano_b, b in bimestres(hoje):
            receita = _em_paralelo(partial(_receita_municipal, ano_b, b), cods)
            if sum(r is not None for r in receita.values()) < minimo:
                continue
            coleta.bimestre = (ano_b, b)
            coleta.primario = _em_paralelo(partial(_primario_municipal, ano_b, b), cods)
            coleta.rcl = {e: (r.rcl if r else None) for e, r in receita.items()}
            break
        return coleta
    return None


# ------------------------------------------------------------------ a previdência da União
#
# RREO da União (`id_ente=1`, `co_esfera=U`, sem `co_poder`: o relatório é de todos os poderes),
# 6º bimestre (o ano fechado). Conferido em 15/11/2026, de 2016 a 2025: o Anexo 04 se divide em
# 04.1, 04.2 e 04.3, e a numeração MUDA com os anos (até 2022, os civis no 04.1 e os militares
# no 04.2; desde 2023, os civis no 04.2 e os militares no 04.3). As contas têm o mesmo código:
# - `RREO4ResultadoRPPSPrevidenciario` e `TotalReceitasRPPSPrevidenciario`: os servidores civis
#   (o RPPS da União);
# - `ResultadoRPPSPrevidenciarioFCDF`: as aposentadorias e pensões que o Fundo Constitucional
#   do DF paga (policiais e bombeiros do DF, que a União sustenta);
# - `RREO4ResultadoRPPSFinanceiro` e `TotalReceitasRPPSFinanceiro`: as pensões militares, com a
#   contribuição dos militares; `ResultadoInativosMilitares`: os militares da reserva e
#   reformados, sem receita própria. Militares inativos só aparecem separados desde 2019.
# O resultado vem na coluna das despesas liquidadas do ano ("DESPESAS LIQUIDADAS ATÉ O
# BIMESTRE / 2025"; em 2021 e 2022, sem o ano), a receita na das realizadas; nos anos com o ano
# anterior ao lado, vale a coluna com o ano do relatório.
UNIAO = 1
ANEXOS_PREVIDENCIA_UNIAO = ("RREO-Anexo 04.1", "RREO-Anexo 04.2", "RREO-Anexo 04.3")
PREVIDENCIA_UNIAO_DESDE = 2019
COL_RESULTADO_UNIAO = ("DESPESAS LIQUIDADAS ATÉ O BIMESTRE",)
COL_RECEITA_UNIAO = ("RECEITAS REALIZADAS ATÉ O BIMESTRE", "ATÉ O BIMESTRE")
"""A receita, em 2019 e 2020, vem em "Até o Bimestre / 2020"."""


@dataclass(frozen=True)
class PrevidenciaUniao:
    """Um ano fechado, em R$ (resultado negativo é déficit)."""

    ano: int
    civis_receita: float
    civis_resultado: float
    militares_receita: float
    militares_resultado: float
    """Pensões militares e militares inativos somados."""
    fcdf_resultado: float

    @property
    def civis_despesa(self) -> float:
        return self.civis_receita - self.civis_resultado

    @property
    def militares_despesa(self) -> float:
        return self.militares_receita - self.militares_resultado


def rreo_uniao(
    ano: int, anexo: str, validade: float = VALIDADE_ANO_FECHADO
) -> list[dict[str, Any]]:
    params = {
        "an_exercicio": str(ano),
        "in_periodicidade": "B",
        "nr_periodo": "6",
        "co_tipo_demonstrativo": "RREO",
        "no_anexo": anexo,
        "co_esfera": "U",
        "id_ente": str(UNIAO),
    }
    itens = baixar_json(f"{BASE}/rreo", params=params, validade=validade)["items"]
    time.sleep(PAUSA)
    return list(itens)


def do_ano(
    itens: list[dict[str, Any]], conta: str, colunas: tuple[str, ...], ano: int
) -> float | None:
    """O valor da `conta` na coluna que começa por um de `colunas` e é a do ano do relatório."""
    for i in itens:
        col = re.sub(r"\s+", " ", str(i.get("coluna") or "")).strip().upper()
        if i["cod_conta"] != conta or i["valor"] is None:
            continue
        for coluna in colunas:
            if col == coluna or (col.startswith(coluna) and re.search(rf"/ ?{ano}$", col)):
                return float(i["valor"])
    return None


def parse_previdencia_uniao(itens: list[dict[str, Any]], ano: int) -> PrevidenciaUniao | None:
    def res(conta: str) -> float | None:
        return do_ano(itens, conta, COL_RESULTADO_UNIAO, ano)

    def rec(conta: str) -> float | None:
        return do_ano(itens, conta, COL_RECEITA_UNIAO, ano)

    civis = res("RREO4ResultadoRPPSPrevidenciario")
    pensoes = res("RREO4ResultadoRPPSFinanceiro")
    inativos = res("ResultadoInativosMilitares")
    if civis is None or pensoes is None or inativos is None:
        return None
    return PrevidenciaUniao(
        ano=ano,
        civis_receita=rec("TotalReceitasRPPSPrevidenciario") or 0.0,
        civis_resultado=civis,
        militares_receita=rec("TotalReceitasRPPSFinanceiro") or 0.0,
        militares_resultado=pensoes + inativos,
        fcdf_resultado=res("ResultadoRPPSPrevidenciarioFCDF") or 0.0,
    )


def previdencia_uniao(hoje: date) -> list[PrevidenciaUniao]:
    """Os anos fechados desde 2019, do mais velho ao mais novo. O 6º bimestre sai em janeiro:
    o ano passado só entra quando a União entregou."""
    saida: list[PrevidenciaUniao] = []
    for ano in range(PREVIDENCIA_UNIAO_DESDE, hoje.year):
        validade = VALIDADE if ano == hoje.year - 1 else VALIDADE_ANO_FECHADO
        itens = [i for a in ANEXOS_PREVIDENCIA_UNIAO for i in rreo_uniao(ano, a, validade)]
        achado = parse_previdencia_uniao(itens, ano)
        if achado:
            saida.append(achado)
    if not saida:
        raise FonteForaDoArError("SICONFI: o RREO da União não trouxe a previdência")
    return saida
