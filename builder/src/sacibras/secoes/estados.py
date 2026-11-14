"""Estados: as mesmas métricas para as 27 UFs.

Desocupação: PNAD Contínua trimestral (IBGE). Pessoal, dívida e receita: Relatório de Gestão Fiscal
(RGF) do Poder Executivo de cada estado, no SICONFI do Tesouro Nacional. ICMS por habitante e
resultado primário: Relatório Resumido da Execução Orçamentária (RREO), também do SICONFI. Os
limites mostrados são os que o próprio RGF publica; o builder não escreve número de lei.

As contas de cada estado (`estados-contas.json`, lidas quando a pessoa abre um estado) vêm da
Declaração de Contas Anuais (DCA) do ano fechado, que todas as UFs já entregaram, e do RGF-Anexo
02 (dívida em partes). Receita e despesa são do Governo do Estado inteiro (todos os poderes), em
valores brutos: o ICMS sai antes de repassar aos municípios e ao Fundeb, e o Fundeb aparece como
fatia.

PIB per capita por UF ficou de fora: a tabela 5938 do IBGE vai só até 2023 e a estimativa de
população do mesmo ano não existe na tabela 6579, então a conta misturaria anos.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from statistics import median

from sacibras.fontes import ibge_sidra, siconfi
from sacibras.schema import (
    UF,
    BlocoDeConta,
    Cartao,
    ContasEstado,
    Estados,
    EstadosContas,
    Fatia,
    LinhaRef,
    MetricaEstados,
)
from sacibras.secoes.base import MESES, Contexto, br, periodo

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


def _desocupacao() -> MetricaEstados:
    # Tabela 4099 (PNAD Contínua trimestral), variável 4099 (taxa de desocupação, 14 anos ou mais).
    por_uf = ibge_sidra.series(
        4099,
        4099,
        periodos="last 1",
        nivel="n3/all",
        por="Unidade da Federação",
        trimestral=True,
    )
    pais = ibge_sidra.serie(4099, 4099, periodos="last 1", nivel="n1/all", trimestral=True)
    valores: dict[str, float | None] = {s: None for s in SIGLA.values()}
    quando: date | None = None
    for cod, pontos in por_uf.items():
        if int(cod) in SIGLA and pontos:
            quando, valores[SIGLA[int(cod)]] = pontos[-1]
    if quando is None:
        raise RuntimeError("SIDRA 4099 sem dado por UF")
    return MetricaEstados(
        id="desocupacao",
        nome="Desocupação",
        descricao=(
            "Parcela das pessoas na força de trabalho (14 anos ou mais) que procuravam emprego "
            "e não tinham trabalho na semana da pesquisa."
        ),
        unidade="%",
        casas=1,
        referencia=periodo(quando, "T"),
        maior_e_melhor=False,
        fonte="IBGE, PNAD Contínua trimestral (SIDRA, tabela 4099)",
        valores=valores,
        brasil=pais[-1][1] if pais and pais[-1][0] == quando else None,
    )


def _limite_comum(valores: list[float | None]) -> float | None:
    """O limite que a maioria dos estados registra (alguns trazem um próprio no RGF)."""
    vistos = [v for v in valores if v is not None]
    return Counter(vistos).most_common(1)[0][0] if vistos else None


def _diferentes(limites: dict[str, float | None], comum: float | None, folga: float) -> str:
    """Quem registra limite diferente do comum (`folga` absorve o arredondamento da razão)."""
    fora = [
        f"{u} ({br(v)} %)"
        for u, v in limites.items()
        if v is not None and comum is not None and abs(v - comum) > folga
    ]
    return f" O RGF de {', '.join(fora)} traz limite diferente." if fora else ""


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
    pru_pes = {u: p.prudencial for u, p in pes.items() if p}
    ale_pes = {u: p.alerta for u, p in pes.items() if p}
    c_max, c_pru, c_ale = (_limite_comum(list(d.values())) for d in (max_pes, pru_pes, ale_pes))
    limites_pes = [
        LinhaRef(valor=v, rotulo=r)
        for v, r in (
            (c_max, "limite máximo do RGF"),
            (c_pru, "limite prudencial do RGF"),
            (c_ale, "limite de alerta do RGF"),
        )
        if v is not None
    ]
    pessoal = MetricaEstados(
        id="pessoal",
        nome="Despesa com pessoal",
        descricao=(
            "Quanto da receita corrente líquida ajustada o Poder Executivo do estado gasta com "
            "salários, aposentadorias e encargos, nos últimos 12 meses. As linhas são os "
            "limites que o próprio Relatório de Gestão Fiscal traz."
            + _diferentes(max_pes, c_max, 0.05)
        ),
        unidade="% da RCL",
        casas=1,
        referencia=ref,
        maior_e_melhor=False,
        fonte=f"Tesouro Nacional, SICONFI, Relatório de Gestão Fiscal, Anexo 01 ({ref})",
        valores={u: (p.percentual if p else None) for u, p in pes.items()},
        limites=limites_pes,
    )

    lim_div = {u: d.limite for u, d in div.items() if d}
    ale_div = {u: d.alerta for u, d in div.items() if d}
    c_lim, c_ale_div = _limite_comum(list(lim_div.values())), _limite_comum(list(ale_div.values()))
    limites_div = [
        LinhaRef(valor=v, rotulo=r)
        for v, r in (
            (c_lim, "limite do RGF (definido por Resolução do Senado)"),
            (c_ale_div, "limite de alerta do RGF"),
        )
        if v is not None
    ]
    divida = MetricaEstados(
        id="divida",
        nome="Dívida consolidada líquida",
        descricao=(
            "Dívida do estado já descontados o caixa e os haveres, em proporção da receita "
            "corrente líquida dos últimos 12 meses. Negativo quer dizer que o estado tem mais "
            "ativos financeiros que dívida." + _diferentes(lim_div, c_lim, 1.0)
        ),
        unidade="% da RCL",
        casas=1,
        referencia=ref,
        maior_e_melhor=False,
        fonte=f"Tesouro Nacional, SICONFI, Relatório de Gestão Fiscal, Anexo 02 ({ref})",
        valores={u: (d.dcl_percentual if d else None) for u, d in div.items()},
        limites=limites_div,
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
            "Receita corrente líquida do estado nos últimos 12 meses dividida pela população "
            "estimada. Mostra quanto cada estado arrecada por pessoa, não o quanto gasta bem."
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
        descricao=(
            "Receitas menos despesas do estado, sem contar juros, em proporção da receita "
            "corrente líquida dos últimos 12 meses. É o acumulado do ano até o bimestre, não "
            "12 meses. Positivo é superávit: sobrou dinheiro antes de pagar juros da dívida. "
            "Usa o resultado acima da linha sem os fundos de previdência próprios (RPPS), o que "
            "a LDO usa como meta e o que melhor compara estados com regimes de tamanhos "
            "diferentes."
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
            "ICMS que o estado arrecadou nos últimos 12 meses, já descontados o que vai aos "
            "municípios e ao Fundeb, dividido pela população estimada. Mostra o peso do "
            "principal imposto estadual, não o quanto é bem gasto."
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
    )
    return primario, icms


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


def _mi(valor: float) -> float:
    return round(valor / 1e6, 1)


def _fatias(partes: list[tuple[str, float | None]], outras: float | None = None) -> list[Fatia]:
    """Da maior para a menor, só o que é positivo; "Outras" por último (e só se sobrou)."""
    uteis = sorted(((n, v) for n, v in partes if v is not None and v > 0), key=lambda p: -p[1])
    fatias = [Fatia(nome=n, valor=_mi(v)) for n, v in uteis]
    if outras is not None and outras > 0:
        fatias.append(Fatia(nome="Outras", valor=_mi(outras)))
    return fatias


def _bloco_receita(r: siconfi.ReceitaAnual, ano: int) -> BlocoDeConta:
    impostos = (r.icms or 0) + (r.ipva or 0) + (r.itcmd or 0)
    outros_tributos = (r.tributos - impostos) if r.tributos is not None else None
    outras_uniao = (r.uniao - (r.fpe or 0)) if r.uniao is not None else None
    partes: list[tuple[str, float | None]] = [
        ("ICMS", r.icms),
        ("IPVA", r.ipva),
        ("ITCMD (herança e doação)", r.itcmd),
        ("Outros impostos, taxas e contribuições de melhoria", outros_tributos),
        ("FPE (Fundo de Participação dos Estados)", r.fpe),
        ("Outras transferências da União", outras_uniao),
        ("Fundeb", r.fundeb),
    ]
    identificado = sum(v for _, v in partes if v is not None and v > 0)
    return BlocoDeConta(
        id="receita",
        titulo="De onde vem a receita",
        descricao=(
            "O dinheiro que o governo do estado arrecadou no ano, por fonte: impostos próprios, "
            "repasses da União e o que volta do Fundeb. Valores brutos, antes de repassar aos "
            "municípios."
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
        descricao=(
            "O que o estado pagou no ano, por tipo de gasto: salários e aposentadorias, custeio, "
            "obras e equipamentos (investimentos), e o serviço da dívida. Inversão financeira é "
            "compra de participação em empresa ou empréstimo concedido."
        ),
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
            'A despesa do ano por área de governo. Em "Outras" ficam Justiça, Assembleia, '
            "assistência social, segurança prisional, cultura, meio ambiente e as demais funções."
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
    ]
    blocos = [
        BlocoDeConta(
            id="divida",
            titulo="Do que é feita a dívida",
            descricao=(
                "A dívida consolidada do estado por credor e tipo, antes de descontar o caixa. "
                "A parte da União é o saldo da renegociação das dívidas dos estados."
            ),
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
                descricao=(
                    "Do que o estado tem em caixa e em haveres financeiros, que se abate da dívida "
                    "para chegar à dívida líquida, a que vale para o limite do Senado."
                ),
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
            blocos.append(_bloco_receita(a.receita, ano))
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
                        f"R$ {br(a.despesa.investimentos / 1e9)} bi em obras e equipamentos em "
                        f"{ano}. Mediana das UFs: {br(median(inv_rcl.values()))} % da RCL."
                    ),
                    fonte=f"{fonte_dca} (Anexo I-D, investimentos) e RREO Anexo 03 (RCL)",
                )
            )
        if comp and comp.uniao > 0:
            rcl = d.rcl if d else None
            falas = [f"{br(comp.uniao / comp.total * 100)} % da dívida consolidada"]
            if rcl:
                falas.append(f"{br(comp.uniao / rcl * 100)} % da RCL")
            numeros.append(
                Cartao(
                    id=f"{sigla.lower()}_divida_uniao",
                    rotulo="Dívida com a União",
                    valor=round(comp.uniao / 1e9, 1 if comp.uniao >= 1e9 else 2),
                    unidade="R$ bilhões",
                    casas=1 if comp.uniao >= 1e9 else 2,
                    referencia=inicio_q,
                    periodicidade="T",
                    detalhe=(
                        "Saldo da renegociação das dívidas dos estados (Lei 9.496/97): "
                        + "; ".join(falas)
                        + "."
                    ),
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
                    detalhe=(
                        f"{pos}º maior entre as {n} UFs com dado; a maior arrecada "
                        f"R$ {br(max(valores.values()), 0)} por pessoa."
                    ),
                    fonte=f"{fonte_dca} (Anexo I-C, receita bruta); população estimada do SICONFI",
                )
            )
        if blocos or numeros:
            contas[sigla] = ContasEstado(uf=sigla, nome=nome, blocos=blocos, numeros=numeros)
    return EstadosContas(contas=contas, gerado_em=agora)


def montar(ctx: Contexto) -> Estados:
    metricas: list[MetricaEstados] = []
    deso: MetricaEstados | None = None
    try:
        deso = _desocupacao()
        metricas.append(deso)
    except Exception as erro:  # uma fonte fora do ar não derruba a seção
        print(f"  aviso: desocupação por UF indisponível: {erro}")

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
    except Exception as erro:
        print(f"  aviso: contas dos estados indisponíveis ({erro}); estados.json sai sem elas")

    if rreo:
        metricas += list(rreo)
        for m in rreo:
            faltam = [u for u, v in m.valores.items() if v is None]
            if faltam:
                print(f"  aviso: {m.nome} sem dado de {', '.join(faltam)}")
    if fiscal:
        metricas.append(fiscal[2])  # RCL por habitante fecha a lista

    if not metricas:
        raise RuntimeError("nenhuma métrica dos estados pôde ser montada")

    frases: list[str] = []
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
    return Estados(
        titulo="Estados",
        resumo=" ".join(frases),
        ufs=[UF(sigla=s, nome=n, regiao=r) for _, s, n, r in UFS],  # type: ignore[arg-type]
        metricas=metricas,
        arquivo_contas=ARQUIVO_CONTAS if contas else "",
        gerado_em=ctx.agora(),
    )
