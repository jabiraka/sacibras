"""Estados: as mesmas métricas para as 27 UFs.

Desocupação: PNAD Contínua trimestral (IBGE). Pessoal, dívida e receita: Relatório de Gestão Fiscal
(RGF) do Poder Executivo de cada estado, no SICONFI do Tesouro Nacional. ICMS por habitante e
resultado primário: Relatório Resumido da Execução Orçamentária (RREO), também do SICONFI. Os
limites de pessoal e de dívida vêm da norma lida (`leis.py`); o estado cujo RGF traz outro
limite é nomeado na descrição.

As contas de cada estado (`estados-contas.json`, lidas quando a pessoa abre um estado) vêm da
Declaração de Contas Anuais (DCA) do ano fechado, que todas as UFs já entregaram, e do RGF-Anexo
02 (dívida em partes). Receita e despesa são do Governo do Estado inteiro (todos os poderes), em
valores brutos: o ICMS sai antes de repassar aos municípios e ao Fundeb, e o Fundeb aparece como
fatia.

PIB, prévia do PIB (IBC-R), trabalho, inflação, crédito e exportações: `estados_economia.py`.
O PIB por habitante usa a população da projeção do IBGE do mesmo ano do PIB.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from statistics import median

from sacibras import leis, organizacao, relatorios
from sacibras.fontes import (
    comexstat,
    ibge_contas_regionais,
    ibge_projecao,
    ibge_sidra,
    ipeadata,
    receita_arrecadacao,
    siconfi,
    tesouro_capag,
)
from sacibras.schema import (
    UF,
    BlocoDeConta,
    Capitais,
    Cartao,
    ContasEstado,
    Estados,
    EstadosContas,
    Fatia,
    HistoricoEstado,
    LinhaRef,
    LinhaTabela,
    MetricaEstados,
    Piramide,
    Tabela,
)
from sacibras.secoes import estados_economia
from sacibras.secoes.base import MESES, Contexto, br, periodo
from sacibras.tipos import Ponto

# (código IBGE, sigla, nome, região)
UFS: list[tuple[int, str, str, str]] = [
    (11, "RO", "Rondônia", "Norte"),
    (12, "AC", "Acre", "Norte"),
    (13, "AM", "Amazonas", "Norte"),
    (14, "RR", "Roraima", "Norte"),
    (15, "PA", "Pará", "Norte"),
    (16, "AP", "Amapá", "Norte"),
    (17, "TO", "Tocantins", "Norte"),
    (21, "MA", "Maranhão", "Nordeste"),
    (22, "PI", "Piauí", "Nordeste"),
    (23, "CE", "Ceará", "Nordeste"),
    (24, "RN", "Rio Grande do Norte", "Nordeste"),
    (25, "PB", "Paraíba", "Nordeste"),
    (26, "PE", "Pernambuco", "Nordeste"),
    (27, "AL", "Alagoas", "Nordeste"),
    (28, "SE", "Sergipe", "Nordeste"),
    (29, "BA", "Bahia", "Nordeste"),
    (31, "MG", "Minas Gerais", "Sudeste"),
    (32, "ES", "Espírito Santo", "Sudeste"),
    (33, "RJ", "Rio de Janeiro", "Sudeste"),
    (35, "SP", "São Paulo", "Sudeste"),
    (41, "PR", "Paraná", "Sul"),
    (42, "SC", "Santa Catarina", "Sul"),
    (43, "RS", "Rio Grande do Sul", "Sul"),
    (50, "MS", "Mato Grosso do Sul", "Centro-Oeste"),
    (51, "MT", "Mato Grosso", "Centro-Oeste"),
    (52, "GO", "Goiás", "Centro-Oeste"),
    (53, "DF", "Distrito Federal", "Centro-Oeste"),
]
SIGLA = {cod: sigla for cod, sigla, _, _ in UFS}
CONTAS = "Contas do governo do estado"


def _desocupacao() -> MetricaEstados:
    # Tabela 4099 (PNAD Contínua trimestral), variável 4099 (taxa de desocupação, 14 anos ou mais).
    periodos = estados_economia.pnad_trimestral(UFS, 4099, 4099)
    return estados_economia.da_pnad(
        MetricaEstados(
            id="desocupacao",
            nome="Desocupação",
            descricao=(
                "Parcela das pessoas na força de trabalho (14 anos ou mais) que procuravam emprego "
                "e não tinham trabalho na semana da pesquisa."
            ),
            unidade="%",
            casas=1,
            referencia="",
            maior_e_melhor=False,
            fonte="IBGE, PNAD Contínua trimestral (SIDRA, tabela 4099)",
            valores={},
            grupo=estados_economia.TRABALHO,
        ),
        periodos,
    )


def _gini() -> MetricaEstados:
    # Tabela 7435 (PNAD Contínua anual, rendimento de todas as fontes), variável 10681: Gini do
    # rendimento domiciliar per capita (conferida em 14/11/2026; a mesma de Desigualdade).
    series, pais = estados_economia.series_por_uf(UFS, 7435, 10681, 15)
    quando = max(p[-1][0] for p in series.values() if p)
    periodos = estados_economia.periodos_por_data(series, pais, "A")
    return estados_economia.com_periodos(
        MetricaEstados(
            id="gini",
            nome="Desigualdade da renda (Gini)",
            grupo=estados_economia.TRABALHO,
            descricao=(
                "Gini da renda domiciliar por pessoa: 0 é todos com a mesma renda, 1 é uma pessoa "
                "com toda a renda. O do Brasil é maior porque soma a distância entre os estados."
            ),
            unidade="índice",
            casas=3,
            referencia=str(quando.year),
            maior_e_melhor=False,
            fonte="IBGE, PNAD Contínua anual (SIDRA, tabela 7435)",
            valores={s: dict(p).get(quando) for s, p in series.items()},
            brasil=dict(pais).get(quando),
        ),
        periodos,
        "A",
    )


def _pobreza() -> MetricaEstados:
    # Ipeadata PNADCA_TXPNUF: % abaixo de US$ 8,30 por dia (PPC de 2021), da Síntese de
    # Indicadores Sociais do IBGE; o ano mais novo é estimado pelo Ipea com a PNAD anual
    # (conferido em 14/11/2026; a mesma de Pobreza › Estados e países).
    por_ter = ipeadata.por_territorio("PNADCA_TXPNUF", date(2012, 1, 1))
    series: dict[str, list[Ponto]] = {s: [] for s in SIGLA.values()}
    for cod, pontos in por_ter.items():
        if len(cod) == 2 and int(cod) in SIGLA:
            series[SIGLA[int(cod)]] = pontos
    if not any(series.values()):
        raise RuntimeError("Ipeadata sem pobreza por UF")
    quando = max(p[-1][0] for p in series.values() if p)
    pais = por_ter.get("0", [])
    periodos = estados_economia.periodos_por_data(series, pais, "A", casas=2)
    return estados_economia.com_periodos(
        MetricaEstados(
            id="pobreza",
            nome="Pobreza",
            grupo=estados_economia.TRABALHO,
            descricao=(
                "Parte das pessoas com renda domiciliar por pessoa abaixo de US$ 8,30 por dia "
                "(PPC de 2021), a linha do Banco Mundial que o IBGE usa."
            ),
            unidade="% das pessoas",
            casas=1,
            referencia=str(quando.year),
            maior_e_melhor=False,
            fonte="IBGE, Síntese de Indicadores Sociais, pelo Ipeadata (PNADCA_TXPNUF)",
            valores={
                s: None if (v := dict(p).get(quando)) is None else round(v, 2)
                for s, p in series.items()
            },
            brasil=None if (b := dict(pais).get(quando)) is None else round(b, 2),
        ),
        periodos,
        "A",
    )


def _diferentes(limites: dict[str, float | None], da_lei: float, folga: float) -> str:
    """Quem registra no RGF limite diferente do da lei (`folga` absorve o arredondamento)."""
    fora = [
        f"{u} ({br(v)} %)" for u, v in limites.items() if v is not None and abs(v - da_lei) > folga
    ]
    return f" O RGF de {', '.join(fora)} traz limite diferente do da lei." if fora else ""


def _fiscais(
    coleta: siconfi.ColetaRgf, populacao: dict[int, float]
) -> tuple[MetricaEstados, MetricaEstados, MetricaEstados, dict[str, float | None]]:
    """Pessoal, dívida e RCL por habitante, mais o limite de alerta de pessoal de cada UF."""
    q, ano = coleta.quadrimestre, coleta.ano
    ref = f"{q}º quadrimestre de {ano}"
    por_uf = {SIGLA[c]: c for c in SIGLA}

    pes = {u: coleta.pessoal.get(c) for u, c in por_uf.items()}
    div = {u: coleta.divida.get(c) for u, c in por_uf.items()}

    max_pes = {u: p.maximo for u, p in pes.items() if p}
    ale_pes = {u: p.alerta for u, p in pes.items() if p}
    limites_pes = [
        LinhaRef(valor=leis.PESSOAL_EXECUTIVO_ESTADUAL.valor, rotulo="limite máximo"),
        LinhaRef(valor=leis.PESSOAL_PRUDENCIAL.valor, rotulo="limite prudencial"),
        LinhaRef(valor=leis.PESSOAL_ALERTA.valor, rotulo="limite de alerta"),
    ]
    pessoal = MetricaEstados(
        id="pessoal",
        nome="Despesa com pessoal",
        descricao=(
            "Gasto do Executivo com salários, aposentadorias e encargos em 12 meses, em % da "
            "receita corrente líquida ajustada. Linhas: o máximo, "
            f"{br(leis.PESSOAL_EXECUTIVO_ESTADUAL.valor, 0)} % da RCL "
            f"({leis.PESSOAL_EXECUTIVO_ESTADUAL.referencia}); o prudencial, 95 % dele "
            f"({leis.PESSOAL_PRUDENCIAL.referencia}); o de alerta, 90 % "
            f"({leis.PESSOAL_ALERTA.referencia})."
            + _diferentes(max_pes, leis.PESSOAL_EXECUTIVO_ESTADUAL.valor, 0.05)
        ),
        unidade="% da RCL",
        casas=1,
        referencia=ref,
        maior_e_melhor=False,
        fonte=f"Tesouro Nacional, SICONFI, Relatório de Gestão Fiscal, Anexo 01 ({ref})",
        valores={u: (p.percentual if p else None) for u, p in pes.items()},
        limites=limites_pes,
        grupo=CONTAS,
    )

    lim_div = {u: d.limite for u, d in div.items() if d}
    limites_div = [
        LinhaRef(valor=leis.DIVIDA_ESTADUAL.valor, rotulo="limite"),
        LinhaRef(valor=leis.DIVIDA_ALERTA.valor, rotulo="limite de alerta"),
    ]
    divida = MetricaEstados(
        id="divida",
        nome="Dívida consolidada líquida",
        descricao=(
            "Dívida descontados o caixa e os haveres, em % da RCL de 12 meses; negativo é mais "
            "ativo financeiro que dívida. Linhas: o limite, "
            f"{br(leis.DIVIDA_ESTADUAL.valor, 0)} % da RCL ({leis.DIVIDA_ESTADUAL.referencia}), "
            f"e o de alerta, 90 % dele ({leis.DIVIDA_ALERTA.referencia})."
            + _diferentes(lim_div, leis.DIVIDA_ESTADUAL.valor, 1.0)
        ),
        unidade="% da RCL",
        casas=1,
        referencia=ref,
        maior_e_melhor=False,
        fonte=f"Tesouro Nacional, SICONFI, Relatório de Gestão Fiscal, Anexo 02 ({ref})",
        valores={u: (d.dcl_percentual if d else None) for u, d in div.items()},
        limites=limites_div,
        grupo=CONTAS,
    )

    per_capita: dict[str, float | None] = {}
    soma_rcl = soma_pop = 0.0
    for u, d in div.items():
        pop = populacao.get(por_uf[u])
        if d and d.rcl is not None and pop:
            per_capita[u] = d.rcl / pop
            soma_rcl += d.rcl
            soma_pop += pop
        else:
            per_capita[u] = None
    rcl = MetricaEstados(
        id="rcl_per_capita",
        nome="Receita corrente líquida por habitante",
        descricao=(
            "Receita corrente líquida de 12 meses por habitante. Mostra quanto o estado "
            "arrecada por pessoa, não se gasta bem."
        ),
        unidade="R$ por pessoa",
        casas=0,
        referencia=ref,
        maior_e_melhor=None,
        fonte=(
            f"Tesouro Nacional, SICONFI, RGF Anexo 02 ({ref}); população estimada do cadastro "
            "de entes do SICONFI (IBGE)"
        ),
        valores=per_capita,
        brasil=soma_rcl / soma_pop if soma_pop else None,
        grupo=CONTAS,
    )
    return pessoal, divida, rcl, ale_pes


def _rreo(
    coleta: siconfi.ColetaRreo, populacao: dict[int, float]
) -> tuple[MetricaEstados, MetricaEstados]:
    """Resultado primário em % da RCL e ICMS por habitante, do RREO de um mesmo bimestre."""
    ano, fim = coleta.ano, MESES[coleta.bimestre * 2 - 1]
    por_uf = {SIGLA[c]: c for c in SIGLA}
    rec = {u: coleta.receita.get(c) for u, c in por_uf.items()}
    pri = {u: coleta.primario.get(c) for u, c in por_uf.items()}

    resultado: dict[str, float | None] = {}
    soma_pri = soma_rcl = 0.0
    for u, r in rec.items():
        p = pri[u]
        if r and r.rcl and p is not None:
            resultado[u] = p / r.rcl * 100
            soma_pri += p
            soma_rcl += r.rcl
        else:
            resultado[u] = None
    ref_pri = f"jan–{fim}/{ano}"
    primario = MetricaEstados(
        id="primario",
        nome="Resultado primário",
        # Sem RPPS: é o que a LDO usa como meta e o que melhor compara estados com regimes de
        # previdência de tamanhos diferentes. Positivo é superávit antes dos juros.
        descricao=(
            "Receitas menos despesas, sem juros, no acumulado do ano até o bimestre, em % da RCL "
            "de 12 meses. Acima da linha e sem os fundos de previdência próprios (RPPS)."
        ),
        unidade="% da RCL",
        casas=1,
        referencia=ref_pri,
        maior_e_melhor=True,
        fonte=(
            "Tesouro Nacional, SICONFI, RREO Anexo 06 (resultado primário, sem RPPS, acima da "
            f"linha, acumulado {ref_pri}) e Anexo 03 (RCL de 12 meses)"
        ),
        valores=resultado,
        brasil=soma_pri / soma_rcl * 100 if soma_rcl else None,
        grupo=CONTAS,
    )

    icms_pc: dict[str, float | None] = {}
    soma_icms = soma_pop = 0.0
    for u, r in rec.items():
        pop = populacao.get(por_uf[u])
        if r and r.icms is not None and pop:
            icms_pc[u] = r.icms / pop
            soma_icms += r.icms
            soma_pop += pop
        else:
            icms_pc[u] = None
    ref_icms = f"12 meses até {fim}/{ano}"
    icms = MetricaEstados(
        id="icms_per_capita",
        nome="ICMS por habitante",
        descricao=(
            "ICMS de 12 meses por habitante, já descontado o que vai aos municípios e ao "
            "Fundeb. Mostra o peso do principal imposto estadual, não se é bem gasto."
        ),
        unidade="R$ por pessoa",
        casas=0,
        referencia=ref_icms,
        maior_e_melhor=None,
        fonte=(
            f"Tesouro Nacional, SICONFI, RREO Anexo 03 (ICMS líquido de transferências e do "
            f"FUNDEB, {ref_icms}); população estimada do cadastro de entes do SICONFI (IBGE)"
        ),
        valores=icms_pc,
        brasil=soma_icms / soma_pop if soma_pop else None,
        grupo=CONTAS,
    )
    return primario, icms


# ---------------------------------------------------------------- CAPAG


def _capag(c: tesouro_capag.Capag) -> MetricaEstados:
    """A nota do Tesouro como métrica: o número (D = 1 a A+ = 6) pinta o mapa, o nome vai na
    tela (`marcas`)."""
    valores: dict[str, float | None] = {}
    for _, sigla, _, _ in UFS:
        n = c.notas.get(sigla)
        valores[sigla] = (
            float(tesouro_capag.ESCALA[n.nota]) if n and n.nota in tesouro_capag.ESCALA else None
        )
    return MetricaEstados(
        id="capag",
        nome="Nota CAPAG do Tesouro",
        descricao=(
            "Nota de capacidade de pagamento do Tesouro, de A+ a D, pela dívida, pela poupança "
            "corrente e pelo caixa. Conta quando o estado pede empréstimo com garantia da União."
        ),
        unidade="nota",
        casas=0,
        referencia=_ref_capag(c),
        maior_e_melhor=True,
        fonte=f"{tesouro_capag.FONTE}, {_ref_capag(c)}",
        valores=valores,
        grupo=CONTAS,
        marcas=[LinhaRef(valor=float(v), rotulo=k) for k, v in tesouro_capag.ESCALA.items()],
    )


def _ref_capag(c: tesouro_capag.Capag) -> str:
    return f"{c.ano}, contas de {c.ano - 1}" + (", revisão" if c.revisao else "")


def _cartao_capag(sigla: str, c: tesouro_capag.Capag) -> Cartao | None:
    n = c.notas.get(sigla)
    if n is None or n.nota not in tesouro_capag.ESCALA:
        return None
    return Cartao(
        id=f"{sigla.lower()}_capag",
        rotulo="Nota CAPAG do Tesouro",
        valor=float(tesouro_capag.ESCALA[n.nota]),
        texto=n.nota,
        unidade="nota",
        casas=0,
        referencia=date(c.ano, 1, 1),
        periodicidade="A",
        detalhe=f"Dívida {n.endividamento} · poupança {n.poupanca} · caixa {n.liquidez}",
        fonte=f"{tesouro_capag.FONTE}, {_ref_capag(c)}",
    )


# ---------------------------------------------------------------- RRF e Propag

REGIMES = {"Nenhum": 0.0, "Propag": 1.0, "RRF": 2.0}
"""O regime como número, para pintar o mapa; a tela escreve o nome (`marcas`)."""


def _ref_acordos() -> str:
    return f"termos até {periodo(relatorios.ACORDOS_EM, 'M')}"


def acordos() -> MetricaEstados:
    """Em que regime da dívida com a União cada estado está (lido à mão: `relatorios.py`)."""
    return MetricaEstados(
        id="acordo_divida",
        nome="Acordo da dívida com a União",
        # Fora da tela: o plano do RRF traz teto de gastos; o Propag pede investir em educação
        # e aportar num fundo dos estados.
        descricao=(
            "O RRF (Lei Complementar 159/2017) suspende parte das parcelas da dívida com a "
            "União em troca de um plano de ajuste. O Propag (Lei Complementar 212/2025) a "
            "refinancia em até 30 anos com juros menores; quem assina sai do RRF."
        ),
        unidade="regime",
        casas=0,
        referencia=_ref_acordos(),
        maior_e_melhor=None,
        fonte=relatorios.FONTE_ACORDOS,
        valores={
            s: (REGIMES[a.regime] if (a := relatorios.ACORDOS.get(s)) else None)
            for s in SIGLA.values()
        },
        grupo=CONTAS,
        marcas=[LinhaRef(valor=v, rotulo=k) for k, v in REGIMES.items()],
    )


def _cartao_acordo(sigla: str) -> Cartao | None:
    a = relatorios.ACORDOS.get(sigla)
    if a is None:
        return None
    return Cartao(
        id=f"{sigla.lower()}_acordo",
        rotulo="Acordo da dívida com a União",
        valor=REGIMES[a.regime],
        texto=a.regime,
        unidade="regime",
        casas=0,
        referencia=relatorios.ACORDOS_EM,
        periodicidade="M",
        detalhe=a.detalhe,
        fonte=relatorios.FONTE_ACORDOS,
    )


# ---------------------------------------------------------------- capitais


def contas_das_capitais(
    coleta: siconfi.ColetaCapitais, capitais: dict[str, tuple[int, str]]
) -> Capitais:
    """Pessoal, dívida e primário das capitais, com os limites da lei para os municípios."""
    ref = f"{coleta.quadrimestre}º quadrimestre de {coleta.ano}"
    fonte_rgf = f"Tesouro Nacional, SICONFI, Relatório de Gestão Fiscal das capitais ({ref})"
    cod = {uf: c for uf, (c, _) in capitais.items()}
    pes = {uf: coleta.pessoal.get(c) for uf, c in cod.items()}
    div = {uf: coleta.divida.get(c) for uf, c in cod.items()}
    metricas = [
        MetricaEstados(
            id="pessoal",
            nome="Despesa com pessoal",
            descricao="Do Poder Executivo da capital, nos últimos 12 meses.",
            unidade="% da RCL",
            casas=1,
            referencia=ref,
            maior_e_melhor=False,
            fonte=f"{fonte_rgf}, Anexo 01",
            valores={uf: (p.percentual if p else None) for uf, p in pes.items()},
            limites=[
                LinhaRef(valor=leis.PESSOAL_EXECUTIVO_MUNICIPAL.valor, rotulo="limite máximo"),
                LinhaRef(valor=leis.PESSOAL_PRUDENCIAL_MUNICIPAL.valor, rotulo="limite prudencial"),
                LinhaRef(valor=leis.PESSOAL_ALERTA_MUNICIPAL.valor, rotulo="limite de alerta"),
            ],
        ),
        MetricaEstados(
            id="divida",
            nome="Dívida consolidada líquida",
            descricao="Dívida já descontados o caixa e os haveres.",
            unidade="% da RCL",
            casas=1,
            referencia=ref,
            maior_e_melhor=False,
            fonte=f"{fonte_rgf}, Anexo 02",
            valores={uf: (d.dcl_percentual if d else None) for uf, d in div.items()},
            limites=[
                LinhaRef(valor=leis.DIVIDA_MUNICIPAL.valor, rotulo="limite"),
                LinhaRef(valor=leis.DIVIDA_ALERTA_MUNICIPAL.valor, rotulo="limite de alerta"),
            ],
        ),
    ]
    if coleta.bimestre:
        ano_b, b = coleta.bimestre
        ref_pri = f"jan–{MESES[b * 2 - 1]}/{ano_b}"
        valores: dict[str, float | None] = {}
        for uf, c in cod.items():
            p, rcl = coleta.primario.get(c), coleta.rcl.get(c)
            valores[uf] = round(p / rcl * 100, 2) if p is not None and rcl else None
        metricas.append(
            MetricaEstados(
                id="primario",
                nome="Resultado primário",
                descricao=(
                    "Receitas menos despesas sem contar juros, no ano até o bimestre, sem os "
                    "fundos de previdência próprios."
                ),
                unidade="% da RCL",
                casas=1,
                referencia=ref_pri,
                maior_e_melhor=True,
                fonte=(
                    "Tesouro Nacional, SICONFI, RREO das capitais, Anexo 06 (resultado primário "
                    f"sem RPPS, acima da linha, {ref_pri}) e Anexo 03 (RCL de 12 meses)"
                ),
                valores=valores,
            )
        )
    return Capitais(nomes={uf: n for uf, (_, n) in capitais.items()}, metricas=metricas)


def _capitais(ctx: Contexto) -> Capitais | None:
    try:
        caps = siconfi.capitais()
        coleta = siconfi.coletar_capitais([c for c, _ in caps.values()], ctx.hoje)
    except Exception as erro:
        print(f"  aviso: contas das capitais indisponíveis: {str(erro)[:160]}")
        return None
    if coleta is None:
        print("  aviso: nenhum quadrimestre recente com 20 capitais no RGF")
        return None
    return contas_das_capitais(coleta, caps)


# ---------------------------------------------------------------- pirâmide


def piramides(
    por_uf: dict[str, dict[str, dict[str, dict[int, float]]]], ano_corrente: int
) -> dict[str, Piramide]:
    """A pirâmide de cada UF, nos mesmos anos da do Brasil em Demografia."""
    from sacibras.secoes import demografia  # demografia importa UFS daqui

    saida: dict[str, Piramide] = {}
    for sigla in SIGLA.values():
        dados = por_uf.get(sigla)
        if dados and {"Homens", "Mulheres"} <= set(dados):
            saida[sigla] = demografia.montar_piramide(dados, ano_corrente)
    return saida


FONTE_PIRAMIDE = f"{ibge_projecao.FONTE} (tabela 2, grupos de cinco anos)"


# ---------------------------------------------------------------- anos fechados

Fracao = tuple[float, float | None, float | None]
"""(o percentual do estado, o numerador e o denominador em R$, para somar os estados)."""

FONTE_RGF_ANUAL = "Tesouro Nacional, SICONFI, RGF do 3º quadrimestre de cada ano"
FONTE_RREO_ANUAL = "Tesouro Nacional, SICONFI, RREO do 6º bimestre de cada ano"


def _pessoal_anual(a: siconfi.AnoFechado) -> Fracao | None:
    p = a.pessoal
    return (p.percentual, p.despesa, p.base) if p else None


def _divida_anual(a: siconfi.AnoFechado) -> Fracao | None:
    d = a.divida
    return (d.percentual, d.liquida, d.base) if d and d.percentual is not None else None


def _primario_anual(a: siconfi.AnoFechado) -> Fracao | None:
    rcl = a.divida.rcl if a.divida else None
    return (a.primario / rcl * 100, a.primario, rcl) if a.primario is not None and rcl else None


def _previdencia_anual(a: siconfi.AnoFechado) -> Fracao | None:
    rcl = a.divida.rcl if a.divida else None
    if a.previdencia is None or not rcl:
        return None
    r = a.previdencia.resultado
    return (r / rcl * 100, r, rcl)


# O fundo em capitalização guarda para os servidores mais novos e costuma sobrar.
NOTA_PREVIDENCIA = (
    "Sem o fundo em capitalização; salto de um ano para outro pode ser só mudança no jeito de "
    "lançar."
)

HISTORICOS: list[tuple[str, str, str, str, Callable[[siconfi.AnoFechado], Fracao | None]]] = [
    (
        "pessoal",
        "Despesa com pessoal",
        f"{FONTE_RGF_ANUAL} (Anexo 01, Poder Executivo)",
        "Em % da receita corrente líquida ajustada, nos 12 meses até dezembro.",
        _pessoal_anual,
    ),
    (
        "divida",
        "Dívida consolidada líquida",
        f"{FONTE_RGF_ANUAL} (Anexo 02)",
        "Em % da receita corrente líquida, em dezembro.",
        _divida_anual,
    ),
    (
        "primario",
        "Resultado primário, com a previdência",
        f"{FONTE_RREO_ANUAL} (Anexo 06) e RGF Anexo 02 (RCL)",
        "Receitas menos despesas no ano, sem juros, em % da RCL. Com a previdência dos "
        "servidores, única forma do relatório antes de 2023; por isso difere do mapa.",
        _primario_anual,
    ),
    (
        "previdencia",
        "Resultado da previdência dos servidores",
        f"{FONTE_RREO_ANUAL} (Anexo 04) e RGF Anexo 02 (RCL)",
        "Contribuições menos benefícios dos servidores civis e militares, em % da RCL; "
        "negativo é o que o Tesouro do estado cobre. " + NOTA_PREVIDENCIA,
        _previdencia_anual,
    ),
]
MINIMO_DE_ESTADOS = 24
"""A soma dos estados só sai no ano em que ao menos este tanto entregou o relatório."""


def _historicos(
    hist: dict[int, dict[int, siconfi.AnoFechado]],
) -> tuple[dict[str, list[HistoricoEstado]], dict[str, dict[int, float]]]:
    """Por UF, as quatro contas no fim de cada ano; e, por conta, a soma dos estados (soma dos
    numeradores sobre a soma dos denominadores, como o país inteiro fosse um estado só)."""
    linhas_pessoal = [
        LinhaRef(valor=leis.PESSOAL_EXECUTIVO_ESTADUAL.valor, rotulo="limite máximo"),
        LinhaRef(valor=leis.PESSOAL_PRUDENCIAL.valor, rotulo="limite prudencial"),
    ]
    linhas_divida = [LinhaRef(valor=leis.DIVIDA_ESTADUAL.valor, rotulo="limite")]
    por_uf: dict[str, list[HistoricoEstado]] = {s: [] for s in SIGLA.values()}
    brasil: dict[str, dict[int, float]] = {}
    for id_, titulo, fonte, nota, conta in HISTORICOS:
        soma: dict[int, float] = {}
        pontos_uf: dict[str, dict[int, float]] = {s: {} for s in SIGLA.values()}
        for ano, estados in sorted(hist.items()):
            num = den = 0.0
            quantos = 0
            for cod, a in estados.items():
                achado = conta(a)
                if achado is None or cod not in SIGLA:
                    continue
                pontos_uf[SIGLA[cod]][ano] = round(achado[0], 2)
                if achado[1] is not None and achado[2]:
                    num, den, quantos = num + achado[1], den + achado[2], quantos + 1
            if quantos >= MINIMO_DE_ESTADOS and den:
                soma[ano] = round(num / den * 100, 2)
        if soma:
            brasil[id_] = soma
        for sigla, pontos in pontos_uf.items():
            if len(pontos) >= 2:
                por_uf[sigla].append(
                    HistoricoEstado(
                        id=id_,
                        titulo=titulo,
                        unidade="% da RCL",
                        pontos=pontos,
                        fonte=fonte,
                        nota=nota,
                        linhas={"pessoal": linhas_pessoal, "divida": linhas_divida}.get(id_, []),
                    )
                )
    return por_uf, brasil


def _previdencia(
    hist: dict[int, dict[int, siconfi.AnoFechado]],
) -> tuple[MetricaEstados, int, dict[str, float]] | None:
    """O resultado da previdência do ano fechado mais novo em que quase todos entregaram:
    a métrica (% da RCL), o ano e o resultado em R$ de cada UF."""
    for ano in sorted(hist, reverse=True):
        fracoes = {
            SIGLA[c]: f
            for c, a in hist[ano].items()
            if c in SIGLA and (f := _previdencia_anual(a)) is not None
        }
        if len(fracoes) < MINIMO_DE_ESTADOS:
            continue
        num = sum(f[1] or 0 for f in fracoes.values())
        den = sum(f[2] or 0 for f in fracoes.values())
        metrica = MetricaEstados(
            id="previdencia",
            nome="Resultado da previdência dos servidores",
            descricao=(
                "Contribuições menos benefícios dos servidores civis e militares no ano, em % "
                "da RCL; negativo é o que o Tesouro do estado cobre. " + NOTA_PREVIDENCIA
            ),
            unidade="% da RCL",
            casas=1,
            referencia=str(ano),
            maior_e_melhor=True,
            fonte=(
                f"Tesouro Nacional, SICONFI, RREO Anexo 04 (6º bimestre de {ano}: fundo em "
                "repartição, benefícios pagos pelo Tesouro e militares) e RGF Anexo 02 (RCL)"
            ),
            valores={
                s: (round(fracoes[s][0], 2) if s in fracoes else None) for s in SIGLA.values()
            },
            brasil=round(num / den * 100, 2) if den else None,
            grupo=CONTAS,
        )
        return metrica, ano, {s: f[1] for s, f in fracoes.items() if f[1] is not None}
    return None


def _cartao_previdencia(
    sigla: str, metrica: MetricaEstados, ano: int, em_reais: dict[str, float]
) -> Cartao | None:
    pct = metrica.valores.get(sigla)
    if pct is None or sigla not in em_reais:
        return None
    deficits = {u: v for u, v in metrica.valores.items() if v is not None and v < 0}
    detalhe = f"{br(pct)} % da RCL"
    if sigla in deficits:
        pos = 1 + sum(1 for v in deficits.values() if v < deficits[sigla])
        detalhe += f"; {pos}º maior déficit de {len(deficits)}"
    reais = em_reais[sigla]
    return Cartao(
        id=f"{sigla.lower()}_previdencia",
        rotulo="Resultado da previdência",
        valor=round(reais / 1e9, 1 if abs(reais) >= 1e9 else 2),
        unidade="R$ bilhões",
        casas=1 if abs(reais) >= 1e9 else 2,
        referencia=date(ano, 1, 1),
        periodicidade="A",
        detalhe=detalhe,
        fonte=metrica.fonte,
    )


# ---------------------------------------------------------------- a economia por atividade

SETORES: list[tuple[str, tuple[str, ...]]] = [
    ("Agropecuária", ("agropecuária",)),
    ("Indústria extrativa (petróleo e minérios)", ("indústrias extrativas",)),
    ("Indústria de transformação", ("indústrias de transformação",)),
    ("Construção, luz e água", ("construção", "eletricidade e gás")),
    ("Comércio", ("comércio e reparação",)),
    ("Governo (administração, saúde e educação públicas)", ("administração, defesa",)),
]
"""As fatias da ficha: (nome, começo do nome das atividades da tab07 que somam). O que não
está aqui (transporte, bancos, aluguéis, informação e outros serviços) vai em "Outras"."""


def _blocos_setores(
    edicao: int,
    vab: dict[str, dict[int, float]],
    participacao: dict[str, dict[int, ibge_contas_regionais.Setores]],
) -> dict[str, BlocoDeConta]:
    """{sigla: o valor adicionado do último ano dividido por atividade}."""
    minusculo = {k.lower(): v for k, v in participacao.items()}
    saida: dict[str, BlocoDeConta] = {}
    for _, sigla, nome, _ in UFS:
        total_por_ano, partes_por_ano = vab.get(nome), minusculo.get(nome.lower())
        if not total_por_ano or not partes_por_ano:
            continue
        ano = max(set(total_por_ano) & set(partes_por_ano))
        total = total_por_ano[ano] * 1e6  # R$ milhões → R$
        atividades = {k.lower(): v for k, v in partes_por_ano[ano].items()}
        partes: list[tuple[str, float | None]] = []
        for rotulo, comecos in SETORES:
            pct = sum(v for k, v in atividades.items() if k.startswith(comecos))
            partes.append((rotulo, total * pct / 100))
        resto = total - sum(v or 0 for _, v in partes)
        saida[sigla] = BlocoDeConta(
            id="pib_setor",
            titulo="O que a economia produz",
            descricao=(
                "O valor adicionado de cada atividade no ano. Em “Outras”, os demais "
                "serviços: transporte, bancos, aluguéis, informação e outros."
            ),
            referencia=str(ano),
            fonte=(
                f"{ibge_contas_regionais.FONTE} {edicao}, tabelas 4 (valor adicionado bruto a "
                "preços correntes) e 7 (participação das atividades)"
            ),
            fatias=_fatias(partes, resto),
            total=_mi(total),
        )
    return saida


# ---------------------------------------------------------------- perto dos limites


def _pessoal_diz(v: float) -> tuple[int, str]:
    """(gravidade, o que dizer) da despesa com pessoal contra os limites da LRF."""
    if v > leis.PESSOAL_EXECUTIVO_ESTADUAL.valor:
        return 3, "acima do máximo"
    if v > leis.PESSOAL_PRUDENCIAL.valor:
        return 2, "acima do prudencial"
    if v > leis.PESSOAL_ALERTA.valor:
        return 1, "acima do alerta"
    return 0, ""


def _divida_diz(v: float) -> tuple[int, str]:
    if v > leis.DIVIDA_ESTADUAL.valor:
        return 3, "acima do limite"
    if v > leis.DIVIDA_ALERTA.valor:
        return 1, "acima do alerta"
    return 0, ""


def _ref_quadrimestre(referencia: str) -> date:
    """O último mês do quadrimestre: "2º quadrimestre de 2026" → 01/08/2026."""
    achado = re.search(r"(\d)º quadrimestre de (\d{4})", referencia)
    if not achado:
        raise ValueError(f"sem quadrimestre em {referencia!r}")
    q, ano = int(achado.group(1)), int(achado.group(2))
    return date(ano, q * 4, 1)


def perto_dos_limites(metricas: list[MetricaEstados]) -> tuple[Cartao, Tabela] | None:
    """Os estados acima de algum limite de alerta (pessoal ou dívida) ou com CAPAG C ou D:
    o número de Riscos e a tabela. Os limites são os da lei (`leis.py`)."""
    por_id = {m.id: m for m in metricas}
    pessoal, divida, capag = por_id.get("pessoal"), por_id.get("divida"), por_id.get("capag")
    if pessoal is None or divida is None:
        return None
    nomes = {s: n for _, s, n, _ in UFS}
    nota_de = {m.valor: m.rotulo for m in capag.marcas} if capag else {}
    fracas = tesouro_capag.ESCALA["C"]
    linhas: list[tuple[tuple[int, int, float], LinhaTabela]] = []
    acima = com_nota_fraca = 0
    for sigla, nome in nomes.items():
        p, d = pessoal.valores.get(sigla), divida.valores.get(sigla)
        n = capag.valores.get(sigla) if capag else None
        gp, fala_p = _pessoal_diz(p) if p is not None else (0, "")
        gd, fala_d = _divida_diz(d) if d is not None else (0, "")
        fraca = n is not None and n <= fracas
        acima += gp > 0 or gd > 0
        com_nota_fraca += fraca
        if not (gp or gd or fraca):
            continue

        def celula(v: float | None, fala: str) -> str:
            return (
                "–" if v is None else f"{br(round(v, 1) + 0.0)} %" + (f", {fala}" if fala else "")
            )

        textos = [celula(p, fala_p), celula(d, fala_d)]
        if capag:
            textos.append(nota_de.get(n, "–") if n is not None else "–")
        linhas.append(
            (
                (max(gp, gd), gp + gd + fraca, p or 0.0),
                LinhaTabela(rotulo=nome, valores=[], unidade="", textos=textos),
            )
        )
    linhas.sort(key=lambda x: x[0], reverse=True)
    colunas = ["Pessoal (% da RCL)", "Dívida (% da RCL)"] + (["CAPAG"] if capag else [])
    ref = f"RGF do {pessoal.referencia}" + (f"; CAPAG {capag.referencia}" if capag else "")
    fontes = f"{pessoal.fonte}; {divida.fonte}" + (f"; {capag.fonte}" if capag else "")
    tabela = Tabela(
        id="estados-no-limite",
        titulo="Estados perto dos limites",
        subtitulo=ref,
        colunas=colunas,
        linhas=[linha for _, linha in linhas],
        fonte=fontes,
        nota=(
            f"Pessoal do Executivo: alerta em {br(leis.PESSOAL_ALERTA.valor)} %, "
            f"prudencial em {br(leis.PESSOAL_PRUDENCIAL.valor, 2)} % e máximo em "
            f"{br(leis.PESSOAL_EXECUTIVO_ESTADUAL.valor, 0)} % da RCL "
            f"({leis.PESSOAL_EXECUTIVO_ESTADUAL.referencia}); dívida: alerta em "
            f"{br(leis.DIVIDA_ALERTA.valor, 0)} % e limite em {br(leis.DIVIDA_ESTADUAL.valor, 0)} "
            f"% ({leis.DIVIDA_ESTADUAL.referencia}). Entra quem passou de um alerta ou tem "
            "CAPAG C ou D."
        ),
    )
    cartao = Cartao(
        id="estados-no-limite",
        rotulo="Estados acima do alerta (pessoal ou dívida)",
        valor=float(acima),
        unidade=f"de {len(nomes)}",
        casas=0,
        referencia=_ref_quadrimestre(pessoal.referencia),
        periodicidade="M",
        detalhe=(f"{com_nota_fraca} com nota CAPAG C ou D" if capag else ""),
        fonte=fontes,
        secao="riscos",
    )
    return cartao, tabela


def metricas_dos_limites(ctx: Contexto) -> list[MetricaEstados]:
    """Pessoal, dívida e CAPAG, para Riscos: da rodada de Estados, se já houve, ou das fontes."""
    guardadas: list[MetricaEstados] | None = ctx.memo.get("estados_limites")
    if guardadas:
        return guardadas
    metricas: list[MetricaEstados] = []
    coleta = siconfi.coletar([c for c, *_ in UFS], ctx.hoje)
    if coleta is not None:
        metricas += list(_fiscais(coleta, siconfi.entes())[:2])
    try:
        metricas.append(_capag(tesouro_capag.capag()))
    except Exception as erro:
        print(f"  aviso: CAPAG indisponível: {str(erro)[:120]}")
    return metricas


@dataclass
class Extras:
    """O que vai à ficha de cada estado além da DCA, cada fonte por conta própria."""

    metricas: list[MetricaEstados] = field(default_factory=list)
    numeros: dict[str, list[Cartao]] = field(default_factory=dict)
    blocos: dict[str, list[BlocoDeConta]] = field(default_factory=dict)
    historicos: dict[str, list[HistoricoEstado]] = field(default_factory=dict)
    brasil: dict[str, dict[int, float]] = field(default_factory=dict)
    piramides: dict[str, Piramide] = field(default_factory=dict)


def _extras(ctx: Contexto) -> Extras:
    x = Extras()
    try:
        hist = siconfi.coletar_historico([c for c, *_ in UFS], ctx.hoje)
        x.historicos, x.brasil = _historicos(hist)
        previdencia = _previdencia(hist)
        if previdencia is None:
            print("  aviso: nenhum ano fechado com 24 estados no RREO Anexo 04")
        else:
            metrica, ano, em_reais = previdencia
            x.metricas.append(metrica)
            for sigla in SIGLA.values():
                if c := _cartao_previdencia(sigla, metrica, ano, em_reais):
                    x.numeros.setdefault(sigla, []).append(c)
    except Exception as erro:
        print(f"  aviso: estados no tempo indisponíveis: {str(erro)[:160]}")
    try:
        nota = tesouro_capag.capag()
        x.metricas.append(_capag(nota))
        for sigla in SIGLA.values():
            if c := _cartao_capag(sigla, nota):
                x.numeros.setdefault(sigla, []).insert(0, c)
    except Exception as erro:
        print(f"  aviso: CAPAG indisponível: {str(erro)[:160]}")
    try:
        edicao, vab, participacao = ibge_contas_regionais.setores()
        for sigla, bloco in _blocos_setores(edicao, vab, participacao).items():
            x.blocos[sigla] = [bloco]
    except Exception as erro:
        print(f"  aviso: PIB por atividade indisponível: {str(erro)[:160]}")
    # O acordo da dívida logo depois da CAPAG (a nota, se veio, é o primeiro número).
    for sigla in SIGLA.values():
        if c := _cartao_acordo(sigla):
            numeros = x.numeros.setdefault(sigla, [])
            numeros.insert(1 if numeros and numeros[0].id.endswith("_capag") else 0, c)
    try:
        fim, produtos = comexstat.exportacoes_por_estado_e("heading")
        _, paises = comexstat.exportacoes_por_estado_e("country")
        for sigla, f in estados_economia.exportacoes_da_ficha(UFS, fim, produtos, paises).items():
            x.numeros.setdefault(sigla, []).append(f.numero)
            x.blocos.setdefault(sigla, []).extend(f.blocos)
    except Exception as erro:
        print(f"  aviso: exportações da ficha indisponíveis: {str(erro)[:160]}")
    try:
        x.piramides = piramides(ibge_projecao.quinquenal_por_uf(), ctx.hoje.year)
    except Exception as erro:
        print(f"  aviso: pirâmide por UF indisponível: {str(erro)[:160]}")
    return x


def _enriquecer(contas: EstadosContas | None, x: Extras, agora: datetime) -> EstadosContas | None:
    """Junta à ficha o que veio de fora da DCA (a nota e a previdência primeiro, nos números)."""
    if not (x.numeros or x.blocos or x.historicos or x.piramides):
        return contas
    veio_vazio = contas is None
    contas = contas or EstadosContas(contas={}, gerado_em=agora)
    for _, sigla, nome, _ in UFS:
        numeros, blocos = x.numeros.get(sigla, []), x.blocos.get(sigla, [])
        historico = x.historicos.get(sigla, [])
        piramide = x.piramides.get(sigla)
        # O acordo da dívida sozinho não abre uma ficha (sem a DCA nem outra fonte).
        so_o_acordo = all(n.id.endswith("_acordo") for n in numeros)
        if so_o_acordo and not (blocos or historico or piramide or sigla in contas.contas):
            continue
        c = contas.contas.get(sigla) or ContasEstado(uf=sigla, nome=nome, blocos=[])
        # Os números da DCA (investimento, dívida com a União, impostos por habitante) ficam
        # entre os de cima (CAPAG, acordo, previdência) e as exportações, que fecham a lista.
        de_fora = [n for n in numeros if not n.id.endswith("_exportacoes")]
        exportacoes = [n for n in numeros if n.id.endswith("_exportacoes")]
        c.numeros = de_fora + c.numeros + exportacoes
        c.blocos = c.blocos + blocos
        c.historico = historico
        if piramide:
            c.piramide = piramide
            c.fonte_piramide = FONTE_PIRAMIDE
        contas.contas[sigla] = c
    contas.historico_brasil = x.brasil
    return None if veio_vazio and not contas.contas else contas


ARQUIVO_CONTAS = "estados-contas.json"
FUNCOES_EM_DESTAQUE = {
    "10": "Saúde",
    "12": "Educação",
    "06": "Segurança pública",
    "09": "Previdência social",
    "04": "Administração",
    "26": "Transporte",
    "28": "Encargos especiais (dívida e repasses a municípios)",
}


def _arrecadacao_federal(populacao: dict[int, float]) -> MetricaEstados:
    """Tributos federais arrecadados no estado em 12 meses, por habitante (CSV da Receita)."""
    por_uf, ultimo = receita_arrecadacao.doze_meses_por_uf(receita_arrecadacao.arrecadacao())
    valores: dict[str, float | None] = {}
    soma = soma_pop = 0.0
    for codigo, sigla, _, _ in UFS:
        pop = populacao.get(codigo)
        if sigla in por_uf and pop:
            valores[sigla] = por_uf[sigla] / pop
            soma += por_uf[sigla]
            soma_pop += pop
        else:
            valores[sigla] = None
    ref = f"12 meses até {periodo(ultimo, 'M')}"
    return MetricaEstados(
        id="arrecadacao_federal_per_capita",
        nome="Arrecadação federal por habitante",
        descricao=(
            "Tributos federais (com o INSS) pelo endereço fiscal de quem paga, não onde a venda "
            "ou o trabalho aconteceu. Por isso DF, SP e RJ, com órgãos federais e sedes de "
            "empresas, aparecem acima da economia local."
        ),
        unidade="R$ por habitante",
        casas=0,
        referencia=ref,
        maior_e_melhor=None,
        fonte=(
            f"{receita_arrecadacao.FONTE}, {ref}; população estimada do cadastro de entes do "
            "SICONFI (IBGE)"
        ),
        valores=valores,
        grupo="Impostos federais",
        brasil=soma / soma_pop if soma_pop else None,
    )


def _mi(valor: float) -> float:
    return round(valor / 1e6, 1)


def _fatias(partes: list[tuple[str, float | None]], outras: float | None = None) -> list[Fatia]:
    """Da maior para a menor, só o que é positivo; "Outras" por último (e só se sobrou)."""
    uteis = sorted(((n, v) for n, v in partes if v is not None and v > 0), key=lambda p: -p[1])
    fatias = [Fatia(nome=n, valor=_mi(v)) for n, v in uteis]
    if outras is not None and outras > 0:
        fatias.append(Fatia(nome="Outras", valor=_mi(outras)))
    return fatias


def _bloco_receita(r: siconfi.ReceitaAnual, ano: int, sigla: str = "") -> BlocoDeConta:
    impostos = (r.icms or 0) + (r.ipva or 0) + (r.itcmd or 0)
    outros_tributos = (r.tributos - impostos) if r.tributos is not None else None
    outras_uniao = (r.uniao - (r.fpe or 0)) if r.uniao is not None else None
    partes: list[tuple[str, float | None]] = [
        ("ICMS", r.icms),
        ("IPVA", r.ipva),
        ("ITCMD (herança e doação)", r.itcmd),
        ("Outros impostos e taxas", outros_tributos),
        ("FPE (Fundo de Participação dos Estados)", r.fpe),
        ("Outras transferências da União", outras_uniao),
        ("Fundeb", r.fundeb),
    ]
    identificado = sum(v for _, v in partes if v is not None and v > 0)
    return BlocoDeConta(
        id="receita",
        titulo="De onde vem a receita",
        descricao=(
            "A arrecadação do ano por fonte, antes dos repasses aos municípios."
            + (
                " O DF também cobra os impostos que nos estados são dos municípios (IPTU, ISS e "
                'ITBI): eles estão em "Outros impostos".'
                if sigla == "DF"
                else ""
            )
        ),
        referencia=f"{ano} (ano fechado)",
        fonte=(
            "Tesouro Nacional, SICONFI, Declaração de Contas Anuais (DCA), Anexo I-C, "
            f"receitas brutas realizadas, exceto intraorçamentárias, {ano}"
        ),
        fatias=_fatias(partes, r.total - identificado),
        total=_mi(r.total),
    )


def _bloco_despesa(d: siconfi.DespesaAnual, ano: int) -> BlocoDeConta:
    partes: list[tuple[str, float | None]] = [
        ("Pessoal e encargos", d.pessoal),
        ("Outras despesas correntes", d.outras_correntes),
        ("Juros e encargos da dívida", d.juros),
        ("Investimentos", d.investimentos),
        ("Inversões financeiras", d.inversoes),
        ("Amortização da dívida", d.amortizacao),
    ]
    return BlocoDeConta(
        id="despesa_grupo",
        titulo="Em que o governo gasta",
        descricao=("O que o estado pagou no ano, por tipo de gasto."),
        referencia=f"{ano} (ano fechado)",
        fonte=(
            "Tesouro Nacional, SICONFI, Declaração de Contas Anuais (DCA), Anexo I-D, "
            f"despesas liquidadas por natureza, {ano}"
        ),
        fatias=_fatias(partes),
        total=_mi(d.total),
    )


def _bloco_funcao(f: siconfi.FuncoesAnuais, ano: int) -> BlocoDeConta:
    partes: list[tuple[str, float | None]] = []
    resto = f.total
    for cod, nome in FUNCOES_EM_DESTAQUE.items():
        achada = f.por_funcao.get(cod)
        if achada:
            partes.append((nome, achada[1]))
            resto -= achada[1]
    return BlocoDeConta(
        id="despesa_funcao",
        titulo="Para onde vai a despesa",
        descricao=(
            'A despesa do ano por área de governo; Justiça, Assembleia e o resto em "Outras".'
        ),
        referencia=f"{ano} (ano fechado)",
        fonte=(
            "Tesouro Nacional, SICONFI, Declaração de Contas Anuais (DCA), Anexo I-E, "
            f"despesas liquidadas por função, exceto intraorçamentárias, {ano}"
        ),
        fatias=_fatias(partes, resto),
        total=_mi(f.total),
    )


def _blocos_divida(c: siconfi.ComposicaoDivida, ref: str) -> list[BlocoDeConta]:
    fonte = f"Tesouro Nacional, SICONFI, Relatório de Gestão Fiscal, Anexo 02 ({ref})"
    partes: list[tuple[str, float | None]] = [
        ("União (renegociação da dívida dos estados, Lei 9.496/97)", c.uniao),
        ("Empréstimos e financiamentos no país", c.emprestimos_internos),
        ("Empréstimos e financiamentos no exterior", c.emprestimos_externos),
        ("Precatórios vencidos e não pagos", c.precatorios),
        ("Parcelamentos (tributos e previdência)", c.parcelamentos),
        ("Demais dívidas contratuais", c.demais_contratuais),
        ("Outras dívidas", c.outras),
    ]
    blocos = [
        BlocoDeConta(
            id="divida",
            titulo="Do que é feita a dívida",
            descricao=("A dívida consolidada por credor, antes de descontar o caixa."),
            referencia=ref,
            fonte=fonte + ", dívida consolidada bruta",
            fatias=_fatias(partes, c.total - sum(v or 0 for _, v in partes)),
            total=_mi(c.total),
        )
    ]
    if c.deducoes:
        blocos.append(
            BlocoDeConta(
                id="deducoes",
                titulo="O que se desconta da dívida",
                descricao=("Caixa e haveres que se abatem para chegar à dívida líquida."),
                referencia=ref,
                fonte=fonte + ", deduções da dívida consolidada",
                fatias=_fatias(
                    [
                        ("Disponibilidade de caixa", c.caixa),
                        ("Demais haveres financeiros", c.haveres),
                    ]
                ),
                total=_mi(c.deducoes),
            )
        )
    return blocos


def _posicao(valores: dict[str, float], uf: str) -> int:
    """1 = o maior valor entre as UFs com dado."""
    return 1 + sum(1 for v in valores.values() if v > valores[uf])


# Caio, 19/11/2026: "ver onde cada Estado [...] está gastando com a receita". A parte de cada
# área na despesa do estado (DCA, Anexo I-E), sem os encargos especiais (função 28: juros e
# amortização da dívida e, em parte dos estados, a cota do ICMS dos municípios lançada como
# despesa), que mudam de estado para estado só pela forma de registrar.
GASTO_POR_AREA = {
    "10": ("gasto_saude", "Saúde"),
    "12": ("gasto_educacao", "Educação"),
    "06": ("gasto_seguranca", "Segurança pública"),
    "09": ("gasto_previdencia", "Previdência"),
}
ENCARGOS_ESPECIAIS = "28"


def _gasto_por_area(anual: siconfi.ColetaAnual) -> list[MetricaEstados]:
    base: dict[str, float] = {}
    por_area: dict[str, dict[str, float]] = {cod: {} for cod in GASTO_POR_AREA}
    for cod_uf, contas in anual.dca.items():
        f = contas.funcoes if contas else None
        if f is None:
            continue
        encargos = f.por_funcao.get(ENCARGOS_ESPECIAIS, ("", 0.0))[1]
        sem = f.total - encargos
        if sem <= 0:
            continue
        base[SIGLA[cod_uf]] = sem
        for cod in GASTO_POR_AREA:
            if cod in f.por_funcao:
                por_area[cod][SIGLA[cod_uf]] = f.por_funcao[cod][1]
    metricas = []
    for cod, (id_, nome) in GASTO_POR_AREA.items():
        valores = por_area[cod]
        if len(valores) < 20:
            continue
        soma_base = sum(base[u] for u in valores)
        metricas.append(
            MetricaEstados(
                id=id_,
                nome=f"Gasto com {nome.lower() if cod != '06' else 'segurança'}",
                grupo=CONTAS,
                descricao=(
                    f"A parte da despesa do estado que foi para {nome.lower()} no ano; conta "
                    "nossa. Sem os encargos especiais (dívida e repasses aos municípios), que "
                    "cada estado registra de um jeito."
                ),
                unidade="% da despesa",
                casas=1,
                referencia=str(anual.ano),
                fonte=(
                    "Tesouro Nacional, SICONFI, Declaração de Contas Anuais (DCA), Anexo I-E, "
                    f"despesas liquidadas por função, {anual.ano}; a parte: conta nossa"
                ),
                valores={
                    u: round(valores[u] / base[u] * 100, 2) if u in valores else None
                    for _, u, _, _ in UFS
                },
                brasil=round(sum(valores.values()) / soma_base * 100, 2),
            )
        )
    return metricas


def _contas(
    anual: siconfi.ColetaAnual,
    rgf: siconfi.ColetaRgf | None,
    populacao: dict[int, float],
    agora: datetime,
) -> EstadosContas:
    """Um `ContasEstado` por UF: receita, despesa (grupo e função), dívida e números soltos."""
    ano = anual.ano
    ref_div = f"{rgf.quadrimestre}º quadrimestre de {rgf.ano}" if rgf else ""
    inicio_ano, inicio_q = (
        date(ano, 1, 1),
        (date(rgf.ano, rgf.quadrimestre * 4 - 3, 1) if rgf else date(ano, 1, 1)),
    )

    # R$ por habitante de cada fonte, para dizer em que posição o estado fica entre as UFs.
    fontes_pc: dict[str, tuple[str, dict[str, float]]] = {}
    for chave, nome, campo in (
        ("icms", "ICMS", "icms"),
        ("ipva", "IPVA", "ipva"),
        ("itcmd", "ITCMD", "itcmd"),
        ("fpe", "FPE", "fpe"),
    ):
        por_uf: dict[str, float] = {}
        for cod, a in anual.dca.items():
            v = getattr(a.receita, campo, None) if a and a.receita else None
            pop = populacao.get(cod)
            if v and pop:
                por_uf[SIGLA[cod]] = v / pop
        fontes_pc[chave] = (nome, por_uf)

    inv_rcl: dict[str, float] = {}
    for cod, a in anual.dca.items():
        rcl = anual.rcl.get(cod)
        if a and a.despesa and rcl:
            inv_rcl[SIGLA[cod]] = a.despesa.investimentos / rcl * 100

    contas: dict[str, ContasEstado] = {}
    for cod, sigla, nome, _ in UFS:
        a = anual.dca.get(cod)
        blocos: list[BlocoDeConta] = []
        numeros: list[Cartao] = []
        fonte_dca = f"Tesouro Nacional, SICONFI, DCA {ano}"
        if a and a.receita:
            blocos.append(_bloco_receita(a.receita, ano, sigla))
        if a and a.despesa:
            blocos.append(_bloco_despesa(a.despesa, ano))
        if a and a.funcoes:
            blocos.append(_bloco_funcao(a.funcoes, ano))
        d = rgf.divida.get(cod) if rgf else None
        comp = d.composicao if d else None
        if comp:
            blocos += _blocos_divida(comp, ref_div)

        if sigla in inv_rcl and a and a.despesa:
            numeros.append(
                Cartao(
                    id=f"{sigla.lower()}_investimento",
                    rotulo="Investimento",
                    valor=round(inv_rcl[sigla], 1),
                    unidade="% da RCL",
                    casas=1,
                    referencia=inicio_ano,
                    periodicidade="A",
                    detalhe=(
                        f"R$ {br(a.despesa.investimentos / 1e9)} bi em obras; "
                        f"mediana das UFs {br(median(inv_rcl.values()))} %"
                    ),
                    fonte=f"{fonte_dca} (Anexo I-D, investimentos) e RREO Anexo 03 (RCL)",
                )
            )
        if comp and comp.uniao > 0:
            rcl = d.rcl if d else None
            falas = [f"{br(comp.uniao / comp.total * 100, 0)} % da dívida"]
            if rcl:
                falas.append(f"{br(comp.uniao / rcl * 100, 0)} % da RCL")
            numeros.append(
                Cartao(
                    id=f"{sigla.lower()}_divida_uniao",
                    rotulo="Dívida com a União",
                    valor=round(comp.uniao / 1e9, 1 if comp.uniao >= 1e9 else 2),
                    unidade="R$ bilhões",
                    casas=1 if comp.uniao >= 1e9 else 2,
                    referencia=inicio_q,
                    periodicidade="T",
                    detalhe="; ".join(falas),
                    fonte=f"Tesouro Nacional, SICONFI, RGF, Anexo 02 ({ref_div})",
                )
            )
        for chave, (rotulo, valores) in fontes_pc.items():
            if sigla not in valores:
                continue
            pos, n = _posicao(valores, sigla), len(valores)
            numeros.append(
                Cartao(
                    id=f"{sigla.lower()}_{chave}_por_habitante",
                    rotulo=f"{rotulo} por habitante",
                    valor=round(valores[sigla]),
                    unidade="R$ por pessoa",
                    casas=0,
                    referencia=inicio_ano,
                    periodicidade="A",
                    detalhe=f"{pos}º maior de {n} UFs",
                    fonte=f"{fonte_dca} (Anexo I-C, receita bruta); população estimada do SICONFI",
                )
            )
        if blocos or numeros:
            contas[sigla] = ContasEstado(uf=sigla, nome=nome, blocos=blocos, numeros=numeros)
    return EstadosContas(contas=contas, gerado_em=agora)


def _exportacoes_no_pib(ctx: Contexto) -> MetricaEstados:
    """O último ano com PIB do IBGE: as exportações dele, mês a mês, contra o PIB dele."""
    edicao, corrente, _ = ibge_contas_regionais.pib()
    ano = max(corrente["Brasil"])
    return estados_economia.exportacoes_no_pib(
        UFS,
        comexstat.exportacoes_por_mes(ano),
        ctx.sgs("DOLAR_MEDIA_MES", ctx.hoje.year - ano + 2),
        corrente,
        ano,
        edicao,
    )


def _economia(ctx: Contexto) -> list[MetricaEstados]:
    """PIB, prévia do PIB, inflação, exportações e concentração; cada fonte por conta própria."""
    saida: list[MetricaEstados] = []

    def previa() -> list[MetricaEstados]:
        # A história inteira do IBC-R (desde 2003) e o PIB oficial, para medir o erro.
        try:
            volume = ibge_contas_regionais.pib()[2]
        except Exception as erro:
            print(f"  aviso: prévia do PIB sem a faixa de erro: {str(erro)[:120]}")
            volume = None
        return estados_economia.ibcr(UFS, lambda k: ctx.sgs(k, 24), volume)

    def trimestral() -> list[MetricaEstados]:
        edicao, corrente, volume = ibge_contas_regionais.pib()
        tabela, variavel, classificacao = estados_economia.PIB_TRIMESTRAL
        pib_brasil = ibge_sidra.serie(
            tabela, variavel, classificacao=classificacao, trimestral=True
        )
        return estados_economia.pib_trimestral(
            UFS, lambda k: ctx.sgs(k, 24), pib_brasil, edicao, corrente, volume
        )

    passos: list[tuple[str, Callable[[], list[MetricaEstados]]]] = [
        ("PIB por UF (Contas Regionais)", lambda: estados_economia.pib(UFS)),
        ("IBC-R", previa),
        ("PIB trimestral por UF (estimativa)", trimestral),
        ("IPCA por área", lambda: [estados_economia.inflacao(UFS)]),
        (
            "exportações por UF",
            lambda: [estados_economia.exportacoes(UFS, siconfi.entes())],
        ),
        ("exportações em % do PIB", lambda: [_exportacoes_no_pib(ctx)]),
        ("concentração do PIB", lambda: [estados_economia.concentracao(UFS)]),
    ]
    for nome, passo in passos:
        try:
            saida += passo()
        except Exception as erro:  # uma fonte fora do ar não derruba a seção
            print(f"  aviso: {nome} indisponível: {str(erro)[:160]}")
    pib = next((m for m in saida if m.id == "pib_crescimento"), None)
    previa_ano = next((m for m in saida if m.id == "ibcr_ano"), None)
    if pib and previa_ano:
        estados_economia.encadear_previa(pib, previa_ano)
    return saida


def montar(ctx: Contexto) -> Estados:
    metricas: list[MetricaEstados] = _economia(ctx)
    deso: MetricaEstados | None = None
    try:
        deso = _desocupacao()
        metricas.append(deso)
    except Exception as erro:  # uma fonte fora do ar não derruba a seção
        print(f"  aviso: desocupação por UF indisponível: {erro}")
    try:
        metricas += estados_economia.trabalho(UFS)
    except Exception as erro:
        print(f"  aviso: PNAD por UF indisponível: {str(erro)[:160]}")
    try:
        metricas += estados_economia.credito(UFS, lambda k: ctx.sgs(k, 4), siconfi.entes())
    except Exception as erro:
        print(f"  aviso: crédito por UF indisponível: {str(erro)[:160]}")
    try:
        metricas.append(_pobreza())
    except Exception as erro:
        print(f"  aviso: pobreza por UF indisponível: {erro}")
    try:
        metricas.append(_gini())
    except Exception as erro:
        print(f"  aviso: Gini por UF indisponível: {erro}")

    fiscal: tuple[MetricaEstados, MetricaEstados, MetricaEstados, dict[str, float | None]] | None
    fiscal = None
    coleta: siconfi.ColetaRgf | None = None
    try:
        coleta = siconfi.coletar([c for c, *_ in UFS], ctx.hoje)
        if coleta is None:
            print("  aviso: nenhum quadrimestre recente com 24 estados no RGF")
        else:
            fiscal = _fiscais(coleta, siconfi.entes())
            metricas += list(fiscal[:2])
    except Exception as erro:
        print(f"  aviso: RGF indisponível: {erro}")

    rreo: tuple[MetricaEstados, MetricaEstados] | None = None
    try:
        recolha = siconfi.coletar_rreo([c for c, *_ in UFS], ctx.hoje)
        if recolha is None:
            print("  aviso: nenhum bimestre recente com 24 estados no RREO")
        else:
            rreo = _rreo(recolha, siconfi.entes())
    except Exception as erro:
        print(f"  aviso: RREO indisponível: {erro}")

    contas: EstadosContas | None = None
    try:
        anual = siconfi.coletar_anual([c for c, *_ in UFS], ctx.hoje)
        if anual is None:
            print("  aviso: nenhuma DCA recente com 24 estados; estados.json sai sem as contas")
        else:
            contas = _contas(anual, coleta, siconfi.entes(), ctx.agora())
            metricas += _gasto_por_area(anual)
    except Exception as erro:
        print(f"  aviso: contas dos estados indisponíveis ({erro}); estados.json sai sem elas")

    if rreo:
        metricas += list(rreo)
        for m in rreo:
            faltam = [u for u, v in m.valores.items() if v is None]
            if faltam:
                print(f"  aviso: {m.nome} sem dado de {', '.join(faltam)}")

    # A ficha de cada estado: CAPAG, previdência, as contas no fim de cada ano e a economia por
    # atividade. Cada fonte por conta própria.
    extras = _extras(ctx)
    metricas += extras.metricas
    metricas.append(acordos())
    contas = _enriquecer(contas, extras, ctx.agora())
    try:
        metricas.append(_arrecadacao_federal(siconfi.entes()))
    except Exception as erro:
        print(f"  aviso: arrecadação federal por UF indisponível: {str(erro)[:120]}")
    if fiscal:
        metricas.append(fiscal[2])  # RCL por habitante fecha a lista

    if not metricas:
        raise RuntimeError("nenhuma métrica dos estados pôde ser montada")
    # Na ordem dos grupos (a lista e a tabela juntam por grupo); dentro dele, a de chegada.
    ordem = [estados_economia.ECONOMIA, estados_economia.TRABALHO, estados_economia.CREDITO]
    ordem += [CONTAS, "Impostos federais"]
    metricas.sort(key=lambda m: ordem.index(m.grupo) if m.grupo in ordem else len(ordem))

    frases: list[str] = []
    pib = next((m for m in metricas if m.id == "pib_crescimento"), None)
    if pib:
        frases.append(estados_economia.frase_pib(pib))
    if deso:
        v = {u: x for u, x in deso.valores.items() if x is not None}
        alto, baixo = max(v, key=lambda u: v[u]), min(v, key=lambda u: v[u])
        frases.append(
            f"No {deso.referencia}, a desocupação vai de {br(v[baixo])} % ({baixo}) a "
            f"{br(v[alto])} % ({alto})"
            + (f", contra {br(deso.brasil)} % no país." if deso.brasil is not None else ".")
        )
    if fiscal:
        pessoal, _, _, alertas = fiscal
        acima = [
            u
            for u, x in pessoal.valores.items()
            if x is not None and alertas.get(u) is not None and x > (alertas[u] or 0)
        ]
        n = len([x for x in pessoal.valores.values() if x is not None])
        frases.append(
            f"No RGF do {pessoal.referencia}, {len(acima)} dos {n} estados com dado gastam com "
            "pessoal mais que o limite de alerta do Executivo."
        )
    if contas:
        ctx.memo["estados_contas"] = contas
    # Riscos (montado depois) usa os mesmos números para "Estados perto dos limites".
    ctx.memo["estados_limites"] = [m for m in metricas if m.id in ("pessoal", "divida", "capag")]
    return Estados(
        titulo="Estados",
        resumo=" ".join(frases),
        ufs=[UF(sigla=s, nome=n, regiao=r) for _, s, n, r in UFS],  # type: ignore[arg-type]
        metricas=metricas,
        arquivo_contas=ARQUIVO_CONTAS if contas else "",
        subcategorias=organizacao.partes_dos_estados(contas is not None),
        capitais=_capitais(ctx),
        gerado_em=ctx.agora(),
    )
