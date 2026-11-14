"""Estados: as mesmas métricas para as 27 UFs.

Desocupação: PNAD Contínua trimestral (IBGE). Pessoal, dívida e receita: Relatório de Gestão Fiscal
(RGF) do Poder Executivo de cada estado, no SICONFI do Tesouro Nacional. ICMS por habitante e
resultado primário: Relatório Resumido da Execução Orçamentária (RREO), também do SICONFI. Os
limites mostrados são os que o próprio RGF publica; o builder não escreve número de lei.

PIB per capita por UF ficou de fora: a tabela 5938 do IBGE vai só até 2023 e a estimativa de
população do mesmo ano não existe na tabela 6579, então a conta misturaria anos.
"""

from __future__ import annotations

from collections import Counter
from datetime import date

from sacibras.fontes import ibge_sidra, siconfi
from sacibras.schema import UF, Estados, LinhaRef, MetricaEstados
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
    return Estados(
        titulo="Estados",
        resumo=" ".join(frases),
        ufs=[UF(sigla=s, nome=n, regiao=r) for _, s, n, r in UFS],  # type: ignore[arg-type]
        metricas=metricas,
        gerado_em=ctx.agora(),
    )
