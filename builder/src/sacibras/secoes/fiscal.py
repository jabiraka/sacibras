"""Contas públicas e dívida: resultado primário, juros, nominal, DBGG e DLSP.

As séries de NFSP do Banco Central são NECESSIDADE de financiamento (positivo = déficit).
Aqui tudo vira RESULTADO: superávit positivo, déficit negativo.
"""

from __future__ import annotations

from datetime import date

from sacibras import contas, leis
from sacibras.fontes import bcb_fiscal, bcb_focus, fmi, tesouro_rtn
from sacibras.schema import (
    Cartao,
    Faixa,
    Grafico,
    LinhaRef,
    LinhaTabela,
    Meta,
    Secao,
    Tabela,
)
from sacibras.secoes.base import Contexto, br, cartao, grafico, periodo, serie
from sacibras.tipos import Ponto


def _resultado(nfsp: list[Ponto]) -> list[Ponto]:
    return contas.escalar(nfsp, -1)


def primario_por_quem_mede(
    primario: list[Ponto], primario_gc: list[Ponto], fmi_anual: dict[int, float], ano: int
) -> Tabela | None:
    """O primário do Brasil pelo Banco Central e pelo FMI, nos mesmos anos.

    Caio, 14/11/2026: *"O déficit primário da aba Brasil no mundo e [o daqui] se conversam?"*
    Conversam, mas não são a mesma conta; a tabela põe os três lado a lado e a nota diz por
    que diferem."""
    dez = {d.year: v for d, v in primario if d.month == 12}
    dez_gc = {d.year: v for d, v in primario_gc if d.month == 12}
    anos = [a for a in range(ano - 7, ano) if a in dez and a in fmi_anual]
    if len(anos) < 3:
        return None
    return Tabela(
        id="primario-bc-fmi",
        titulo="O primário do Brasil por quem mede: Banco Central e FMI",
        subtitulo="% do PIB no ano; negativo é déficit",
        colunas=[str(a) for a in anos],
        linhas=[
            LinhaTabela(
                rotulo="Setor público consolidado (Banco Central)",
                valores=[round(dez[a], 2) for a in anos],
                unidade="% do PIB",
                casas=2,
            ),
            LinhaTabela(
                rotulo="Governo Federal e Banco Central (Banco Central)",
                valores=[round(dez_gc[a], 2) if a in dez_gc else None for a in anos],
                unidade="% do PIB",
                casas=2,
            ),
            LinhaTabela(
                rotulo="Governo geral (FMI, em Brasil no mundo)",
                valores=[round(fmi_anual[a], 2) for a in anos],
                unidade="% do PIB",
                casas=2,
            ),
        ],
        fonte="Banco Central (SGS 5793 e 5783, NFSP em 12 meses, dezembro); FMI, World "
        "Economic Outlook (GGXONLB_NGDP)",
        nota=(
            "Conversam, mas não são a mesma conta. Quem entra: o Banco Central soma União, "
            "estados, municípios, o próprio Banco Central e as estatais (fora Petrobras, "
            "Eletrobras e bancos); o FMI mede só o governo geral (União, estados e municípios). "
            'Como se mede: o Banco Central olha quanto a dívida variou no ano ("abaixo da '
            'linha"); o FMI soma receitas e despesas ("acima da linha"). Os dois andam '
            "juntos na maior parte dos anos, mas há anos de diferença grande. Para o Brasil, o "
            "número oficial é o do Banco Central (e a meta da LDO vale para o Governo Central); "
            "para comparar países, o do FMI, que mede todos do mesmo jeito."
        ),
    )


def _bi(valor_em_milhoes: float) -> float:
    return valor_em_milhoes / 1000


def meta_do_primario(ctx: Contexto) -> tuple[Cartao, Grafico, Tabela]:
    """O primário do Governo Central em 12 meses, pelo BC, contra a meta da LDO.

    Decisão do Caio (14/11/2026, opção "b"): o número de quem apura (o BC, LC 200/2023, art.
    2º, § 4º) contra a meta da lei, com o desconto que a apuração oficial faz dito ao lado,
    tirado do relatório bimestral do governo. A meta vale para o ano fechado; a soma de 12
    meses mostra o caminho.
    """
    meta = leis.META_PRIMARIA_2026
    centro, piso, teto = _bi(meta.centro), _bi(meta.inferior), _bi(meta.superior)
    doze = contas.escalar(
        contas.soma_movel(_resultado(ctx.sgs("NFSP_PRIMARIO_GC_MES", 12))), 1 / 1000
    )
    ultima = leis.AVALIACOES_2026[-1]
    apos = ultima.resultado + ultima.deducao
    fonte_bc = ctx.fonte_sgs("NFSP_PRIMARIO_GC_MES")

    c = cartao(
        "meta-primario",
        "Primário do Governo Central, 12 meses",
        doze,
        unidade="R$ bilhões",
        periodicidade="M",
        casas=1,
        detalhe=f"meta de {meta.ano}; a conta oficial desconta R$ {br(ultima.deducao)} bi",
        fonte=f"{fonte_bc}; meta: {meta.referencia}",
        secao="fiscal",
        mini=60,
    )
    c.meta = Meta(centro=centro, inferior=piso, superior=teto, norma=meta.referencia)

    inicio_meta = date(meta.ano, 1, 1)
    meses_da_meta = [date(meta.ano, m, 1) for m in range(1, 13)]
    g = grafico(
        "meta-primario",
        f"O primário do Governo Central e a meta de {meta.ano}",
        [serie("gc", "Governo Federal e Banco Central, 12 meses", doze, casas=1)],
        unidade="R$ bilhões (superávit +, déficit −)",
        casas=1,
        periodicidade="M",
        janela_anos=5,
        fonte=f"{fonte_bc}; meta: {meta.referencia}, § 1º",
        faixa=Faixa(
            nome=f"intervalo da meta de {meta.ano} (R$ {br(piso, 0)} a R$ {br(teto)} bi)",
            pontos=[(d, piso, teto) for d in meses_da_meta if d >= inicio_meta],
        ),
        linhas=[LinhaRef(valor=centro, rotulo=f"meta R$ {br(centro)} bi")],
        nota=(
            "Soma de 12 meses do resultado que o Banco Central apura (quem apura a meta, "
            "pela LC 200/2023). A meta vale para o ano fechado. Na verificação, o governo "
            f"desconta despesas que outras normas tiram da conta: R$ {br(ultima.deducao)} bi "
            f"previstos para {meta.ano} no relatório do {ultima.bimestre}."
        ),
    )

    colunas = [a.bimestre for a in leis.AVALIACOES_2026]
    t = Tabela(
        id="meta-primario",
        titulo=f"A meta de {meta.ano} pela conta do governo",
        subtitulo="Projeção para o ano inteiro, em cada relatório bimestral",
        colunas=colunas,
        linhas=[
            LinhaTabela(
                rotulo="Resultado primário projetado",
                valores=[a.resultado for a in leis.AVALIACOES_2026],
                unidade="R$ bi",
            ),
            LinhaTabela(
                rotulo="Descontos da apuração",
                valores=[a.deducao for a in leis.AVALIACOES_2026],
                unidade="R$ bi",
            ),
            LinhaTabela(
                rotulo="Resultado para a meta",
                valores=[round(a.resultado + a.deducao, 1) for a in leis.AVALIACOES_2026],
                unidade="R$ bi",
            ),
            LinhaTabela(
                rotulo="Piso da meta",
                valores=[piso for _ in colunas],
                unidade="R$ bi",
            ),
            LinhaTabela(
                rotulo="Centro da meta",
                valores=[round(centro, 1) for _ in colunas],
                unidade="R$ bi",
            ),
        ],
        fonte=(
            "Relatórios de Avaliação de Receitas e Despesas Primárias do Poder Executivo, "
            "pela Nota Informativa da Consultoria de Orçamentos do Senado de 25/9/2026; "
            f"meta: {meta.referencia}"
        ),
        nota=(
            "Os descontos vêm da EC 136, da ADPF 1236 e das LCs 221, 223 e 235 (precatórios, "
            "defesa, saúde). "
            + (
                f"No {ultima.bimestre}, o resultado para a meta fica R$ {br(abs(apos - piso))} "
                "bi abaixo do piso, e o relatório manda contingenciar esse valor."
                if apos < piso
                else f"No {ultima.bimestre}, o resultado para a meta fica dentro do intervalo."
            )
        ),
    )
    return c, g, t


FAIXAS_DE_PRAZO = [
    ("ate-1", "Até 1 ano", ("até 1 ano",)),
    ("1-a-3", "De 1 a 3 anos", ("entre 1 e 3 anos",)),
    ("3-a-5", "De 3 a 5 anos", ("entre 3 e 5 anos",)),
    ("5-a-10", "De 5 a 10 anos", ("entre 5 e 10 anos",)),
    ("mais-de-10", "Mais de 10 anos", ("entre 10 e 20 anos", "após 20 anos")),
]


def prazos_da_divida(total: list[Ponto], faixas: dict[str, list[Ponto]]) -> dict[str, list[Ponto]]:
    """{faixa: % do saldo da dívida bruta} nas cinco faixas da tela (as duas mais longas do BC
    somadas), nos meses em que todas existem."""
    mapas = {nome: dict(pontos) for nome, pontos in faixas.items()}
    todo = dict(total)
    meses = sorted(d for d in todo if todo[d] and all(d in m for m in mapas.values()))
    return {
        id: [(d, sum(mapas[f][d] for f in fontes) / todo[d] * 100) for d in meses]
        for id, _, fontes in FAIXAS_DE_PRAZO
    }


def juro_e_prazos(ctx: Contexto, inicio: date) -> tuple[Cartao, Grafico]:
    """O juro médio da dívida bruta (taxa implícita de 12 meses) e quando ela vence."""
    taxa = ctx.memo.get("taxa_implicita_dbgg") or bcb_fiscal.taxa_implicita_dbgg()
    ctx.memo["taxa_implicita_dbgg"] = taxa
    total, faixas = bcb_fiscal.cronograma_dbgg()
    partes = prazos_da_divida(total, faixas)
    c = cartao(
        "juro-implicito",
        "Juro médio da dívida bruta, 12 meses",
        taxa,
        unidade="% a.a.",
        periodicidade="M",
        casas=1,
        detalhe=f"Selic hoje: {br(ctx.sgs('SELIC_META', 2)[-1][1], 2)} %",
        fonte=bcb_fiscal.FONTE_TAXA,
        secao="fiscal",
        mini=120,
    )
    g = grafico(
        "divida-vencimento",
        "Quando a dívida bruta vence",
        [serie(id, nome, partes[id], casas=1, desde=inicio) for id, nome, _ in FAIXAS_DE_PRAZO],
        tipo="empilhado",
        unidade="% da dívida bruta",
        casas=1,
        periodicidade="M",
        janela_anos=10,
        fonte=f"{bcb_fiscal.FONTE_CRONOGRAMA}; cálculo próprio",
        nota=(
            "O saldo da dívida bruta do governo geral pelo prazo que falta para vencer, como "
            "parte do total, no cronograma que o Banco Central publica. Inclui as operações "
            "compromissadas do Banco Central, quase todas de prazo curto. A parte de até um "
            "ano é a que o governo precisa trocar por dívida nova nos próximos 12 meses."
        ),
    )
    return c, g


def montar(ctx: Contexto) -> Secao:
    anos = 20
    primario = _resultado(ctx.sgs("NFSP_PRIMARIO_12M", anos))
    primario_gc = _resultado(ctx.sgs("NFSP_PRIMARIO_GC_12M", anos))
    nominal = _resultado(ctx.sgs("NFSP_NOMINAL_12M", anos))
    juros = ctx.sgs("NFSP_JUROS_12M", anos)
    dbgg = ctx.sgs("DBGG", anos)
    dlsp = ctx.sgs("DLSP", anos)
    primario_mes = contas.escalar(_resultado(ctx.sgs("NFSP_PRIMARIO_MES")), 1 / 1000)

    focus_divida = bcb_focus.mediana_anual_hoje("Dívida bruta do governo geral")
    focus_primario = bcb_focus.mediana_anual_hoje("Resultado primário")
    focus_nominal = bcb_focus.mediana_anual_hoje("Resultado nominal")
    edicao = bcb_focus.data_da_ultima_edicao()
    ctx.memo["focus_divida"] = focus_divida
    ctx.memo["focus_primario"] = focus_primario
    ctx.memo["focus_nominal"] = focus_nominal

    def fim_de_ano(mapa: dict[int, float]) -> list[Ponto]:
        # Só até quatro anos à frente: depois disso poucas casas respondem.
        return [
            (date(ano, 12, 1), valor)
            for ano, valor in sorted(mapa.items())
            if ano <= ctx.hoje.year + 4
        ]

    ano = ctx.hoje.year
    cartoes = [
        cartao(
            "dbgg",
            "Dívida bruta do governo",
            dbgg,
            unidade="% do PIB",
            periodicidade="M",
            casas=1,
            detalhe=(
                f"Focus para o fim de {ano}: {br(focus_divida[ano])} %"
                if ano in focus_divida
                else ""
            ),
            fonte=ctx.fonte_sgs("DBGG"),
            secao="fiscal",
            mini=120,
        ),
        cartao(
            "primario",
            "Resultado primário, 12 meses",
            primario,
            unidade="% do PIB",
            periodicidade="M",
            casas=2,
            detalhe="setor público consolidado; negativo é déficit",
            fonte=ctx.fonte_sgs("NFSP_PRIMARIO_12M"),
            secao="fiscal",
            mini=120,
        ),
        cartao(
            "juros-divida",
            "Juros da dívida, 12 meses",
            juros,
            unidade="% do PIB",
            periodicidade="M",
            casas=2,
            fonte=ctx.fonte_sgs("NFSP_JUROS_12M"),
            secao="fiscal",
            mini=120,
        ),
        cartao(
            "nominal",
            "Resultado nominal, 12 meses",
            nominal,
            unidade="% do PIB",
            periodicidade="M",
            casas=2,
            detalhe="primário menos juros",
            fonte=ctx.fonte_sgs("NFSP_NOMINAL_12M"),
            secao="fiscal",
            mini=120,
        ),
        cartao(
            "dlsp",
            "Dívida líquida do setor público",
            dlsp,
            unidade="% do PIB",
            periodicidade="M",
            casas=1,
            fonte=ctx.fonte_sgs("DLSP"),
            secao="fiscal",
            mini=120,
        ),
    ]
    inicio = date(ctx.hoje.year - anos, 1, 1)
    graficos = [
        grafico(
            "divida",
            "Dívida pública e o que o mercado projeta",
            [
                serie("dbgg", "Dívida bruta do governo geral", dbgg, desde=inicio),
                serie("dlsp", "Dívida líquida do setor público", dlsp, desde=inicio),
                serie(
                    "focus",
                    "Focus: dívida bruta no fim do ano (mediana)",
                    [dbgg[-1], *[p for p in fim_de_ano(focus_divida) if p[0] > dbgg[-1][0]]],
                    papel="consenso",
                ),
            ],
            unidade="% do PIB",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=f"{ctx.fonte_sgs('DBGG', 'DLSP')}; Focus de {periodo(edicao, 'D')}",
            largura="inteira",
        ),
        grafico(
            "primario",
            "Resultado primário em 12 meses",
            [
                serie("consolidado", "Setor público consolidado", primario, desde=inicio),
                serie("gc", "Governo Federal e Banco Central", primario_gc, desde=inicio),
                serie(
                    "focus",
                    "Focus: setor público no fim do ano (mediana)",
                    [
                        primario[-1],
                        *[p for p in fim_de_ano(focus_primario) if p[0] > primario[-1][0]],
                    ],
                    papel="consenso",
                ),
            ],
            unidade="% do PIB (superávit +, déficit −)",
            casas=2,
            periodicidade="M",
            janela_anos=10,
            fonte=f"{ctx.fonte_sgs('NFSP_PRIMARIO_12M', 'NFSP_PRIMARIO_GC_12M')}; Focus",
            nota=(
                "O Banco Central publica a necessidade de financiamento; aqui o sinal está "
                "trocado para ler como resultado."
            ),
        ),
        grafico(
            "nominal",
            "Do primário ao nominal: a conta de juros",
            [
                serie("primario", "Resultado primário", primario, desde=inicio),
                serie("juros", "Juros nominais (despesa)", contas.escalar(juros, -1), desde=inicio),
                serie("nominal", "Resultado nominal", nominal, desde=inicio),
            ],
            unidade="% do PIB, em 12 meses",
            casas=2,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs("NFSP_PRIMARIO_12M", "NFSP_JUROS_12M", "NFSP_NOMINAL_12M"),
            nota="Resultado nominal = primário − juros. Setor público consolidado.",
        ),
        grafico(
            "primario-mensal",
            "Resultado primário mês a mês",
            [serie("mes", "Setor público consolidado", primario_mes, casas=1)],
            tipo="barras",
            unidade="R$ bilhões",
            casas=1,
            periodicidade="M",
            janela_anos=5,
            fonte=ctx.fonte_sgs("NFSP_PRIMARIO_MES"),
        ),
    ]

    tabelas: list[Tabela] = []
    try:  # o FMI fora do ar não derruba a seção: só a comparação fica de fora
        weo = fmi.weo(["BRA"], ["GGXONLB_NGDP"], ctx.hoje.year - 8, ctx.hoje.year)
        t_bc_fmi = primario_por_quem_mede(
            primario, primario_gc, weo.valores.get(("BRA", "GGXONLB_NGDP"), {}), ctx.hoje.year
        )
        if t_bc_fmi:
            tabelas.append(t_bc_fmi)
    except Exception as erro:
        print(f"  aviso: fiscal: sem o primário do FMI ({str(erro)[:120]})")
    c_meta, g_meta, t_meta = meta_do_primario(ctx)
    cartoes.append(c_meta)
    graficos.append(g_meta)
    tabelas.append(t_meta)

    # --- Receitas e despesas do Governo Central (RTN, em R$ milhões correntes) ---
    # O site do Tesouro cai de vez em quando: sem o RTN, a seção sai com o resto.
    try:
        rtn = tesouro_rtn.serie_historica()
        pib = ctx.sgs("PIB_12M", anos)
        receita_pib = contas.em_pct_do_pib(rtn["receita_liquida"], pib)
        despesa_pib = contas.em_pct_do_pib(rtn["despesa_total"], pib)
        rgps_pib = contas.em_pct_do_pib(rtn["rgps"], pib)
        pessoal_pib = contas.em_pct_do_pib(rtn["pessoal"], pib)
        demais_pib = contas.subtrair(contas.subtrair(despesa_pib, rgps_pib), pessoal_pib)
        fonte_rtn = (
            "Tesouro Nacional, Resultado do Tesouro Nacional (série histórica, tabela 1.1); "
            f"PIB: {ctx.fonte_sgs('PIB_12M')}"
        )
        cartoes += [
            cartao(
                "despesa-gc",
                "Despesa do Governo Central, 12 meses",
                despesa_pib,
                unidade="% do PIB",
                periodicidade="M",
                casas=1,
                detalhe="soma de 12 meses sobre o PIB",
                fonte=fonte_rtn,
                procedencia="calculado",
                secao="fiscal",
                mini=120,
            ),
            cartao(
                "previdencia-rgps",
                "Previdência (RGPS), 12 meses",
                rgps_pib,
                unidade="% do PIB",
                periodicidade="M",
                casas=1,
                detalhe="benefícios previdenciários do Regime Geral",
                fonte=fonte_rtn,
                procedencia="calculado",
                secao="fiscal",
                mini=120,
            ),
        ]
        graficos += [
            grafico(
                "receita-despesa",
                "Receita e despesa do Governo Central",
                [
                    serie("receita", "Receita líquida", receita_pib, desde=inicio),
                    serie("despesa", "Despesa total", despesa_pib, desde=inicio),
                ],
                unidade="% do PIB, em 12 meses",
                casas=1,
                periodicidade="M",
                janela_anos=10,
                fonte=fonte_rtn,
                nota=(
                    "Receita líquida de transferências a estados e municípios; soma dos últimos "
                    "12 meses sobre o PIB de 12 meses."
                ),
            ),
            grafico(
                "despesa-composicao",
                "Para onde vai a despesa",
                [
                    serie("rgps", "Benefícios previdenciários", rgps_pib, desde=inicio),
                    serie("pessoal", "Pessoal e encargos sociais", pessoal_pib, desde=inicio),
                    serie("demais", "Demais despesas", demais_pib, desde=inicio),
                ],
                unidade="% do PIB, em 12 meses",
                casas=1,
                periodicidade="M",
                janela_anos=10,
                fonte=fonte_rtn,
                nota="Demais despesas = despesa total menos benefícios previdenciários e pessoal.",
            ),
        ]
    except Exception as erro:
        print(f"    RTN ficou de fora: {str(erro)[:120]}")

    # --- Dívida por indexador (SGS 4173 a 4180: dívida mobiliária federal, posição em carteira) ---
    chaves_divida = [
        "DIVIDA_IDX_SELIC",
        "DIVIDA_IDX_PREFIXADO",
        "DIVIDA_IDX_CAMBIO",
        "DIVIDA_IDX_TR",
        "DIVIDA_IDX_TJLP",
        "DIVIDA_IDX_OUTROS",
        "DIVIDA_IDX_IGPM",
        "DIVIDA_IDX_IGPDI",
    ]
    idx = {c: dict(ctx.sgs(c, anos)) for c in chaves_divida}
    meses_div = sorted(set.intersection(*(set(m) for m in idx.values())))
    selic_div = [(d, idx["DIVIDA_IDX_SELIC"][d]) for d in meses_div]
    pre_div = [(d, idx["DIVIDA_IDX_PREFIXADO"][d]) for d in meses_div]
    cambio_div = [(d, idx["DIVIDA_IDX_CAMBIO"][d]) for d in meses_div]
    resto_div = [
        (d, sum(idx[c][d] for c in ("DIVIDA_IDX_TR", "DIVIDA_IDX_TJLP", "DIVIDA_IDX_OUTROS")))
        for d in meses_div
    ]
    # O BCB não publica o IPCA nessa família (4173 a 4180 não o trazem; o IPCA são as NTN-B).
    # Índices de preços = o que falta para 100 %: IPCA + IGP-M + IGP-DI.
    precos_div = [
        (
            d,
            100
            - sum(
                idx[c][d] for c in chaves_divida if c not in ("DIVIDA_IDX_IGPM", "DIVIDA_IDX_IGPDI")
            ),
        )
        for d in meses_div
    ]
    cartoes.append(
        cartao(
            "divida-selic",
            "Dívida atrelada à Selic",
            selic_div,
            unidade="%",
            periodicidade="M",
            casas=1,
            detalhe="dívida mobiliária federal, posição em carteira",
            fonte=ctx.fonte_sgs("DIVIDA_IDX_SELIC"),
            secao="fiscal",
            mini=120,
        )
    )
    graficos.append(
        grafico(
            "divida-indexador",
            "De que é feita a dívida: participação por indexador",
            [
                serie("selic", "Selic (Over)", selic_div, desde=inicio),
                serie("prefixado", "Prefixado", pre_div, desde=inicio),
                serie("precos", "Índices de preços (IPCA e IGP)", precos_div, desde=inicio),
                serie("cambio", "Câmbio", cambio_div, desde=inicio),
                serie("resto", "TR, TJLP e outros", resto_div, desde=inicio),
            ],
            tipo="empilhado",
            unidade="% da dívida mobiliária federal",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs(*chaves_divida),
            nota=(
                "Dívida mobiliária federal, posição em carteira (títulos do Tesouro Nacional). "
                "As séries de participação por indexador não trazem o IPCA: "
                '"Índices de preços" é o que falta para 100 % depois dos demais indexadores '
                "(IPCA, em sua maior parte, mais IGP-M e IGP-DI)."
            ),
        )
    )

    # --- O juro e os prazos da dívida bruta: as tabelas especiais do BC (não estão no SGS) ---
    try:
        c_juro, g_prazos = juro_e_prazos(ctx, inicio)
        cartoes.append(c_juro)
        graficos.append(g_prazos)
    except Exception as erro:
        print(f"  aviso: fiscal: sem o juro e os prazos da dívida bruta ({str(erro)[:120]})")

    sinal = "déficit" if primario[-1][1] < 0 else "superávit"
    resumo = (
        f"A dívida bruta está em {br(dbgg[-1][1])} % do PIB ({periodo(dbgg[-1][0], 'M')}). "
        f"O setor público tem {sinal} primário de {br(abs(primario[-1][1]), 2)} % do PIB em "
        "12 meses e paga "
        f"{br(juros[-1][1], 2)} % do PIB em juros: o resultado nominal é de "
        f"{br(nominal[-1][1], 2)} % do PIB."
    )
    return Secao(
        id="fiscal",
        titulo="Contas públicas e dívida",
        resumo=resumo,
        cartoes=cartoes,
        graficos=graficos,
        tabelas=tabelas,
        gerado_em=ctx.agora(),
    )
