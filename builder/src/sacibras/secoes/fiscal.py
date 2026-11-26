"""Contas públicas e dívida: resultado primário, juros, nominal, DBGG e DLSP.

As séries de NFSP do Banco Central são NECESSIDADE de financiamento (positivo = déficit).
Aqui tudo vira RESULTADO: superávit positivo, déficit negativo.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta

from sacibras import contas, leis
from sacibras.fontes import (
    avaliacao_bimestral,
    bcb_fiscal,
    bcb_focus,
    fmi,
    sest,
    tesouro_direto,
    tesouro_rtn,
)
from sacibras.modelos import decomposicoes
from sacibras.schema import (
    Cartao,
    Faixa,
    FichasEstatais,
    Grafico,
    LinhaRef,
    LinhaTabela,
    Meta,
    Secao,
    Tabela,
)
from sacibras.secoes import estatais, gasto, mercados, servidores
from sacibras.secoes.base import (
    Contexto,
    br,
    cartao,
    com_variantes,
    em_reais_de_hoje,
    grafico,
    periodo,
    serie,
    variante,
)
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
        titulo="O primário por quem mede: Banco Central e FMI",
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
                rotulo="Governo geral (FMI)",
                valores=[round(fmi_anual[a], 2) for a in anos],
                unidade="% do PIB",
                casas=2,
            ),
        ],
        fonte="Banco Central (SGS 5793 e 5783, NFSP em 12 meses, dezembro); FMI, World "
        "Economic Outlook (GGXONLB_NGDP)",
        # O BC soma União, estados, municípios, o próprio BC e as estatais (fora Petrobras,
        # Eletrobras e bancos) e mede "abaixo da linha" (quanto a dívida variou); o FMI mede
        # só o governo geral, "acima da linha" (receitas menos despesas). A meta da LDO vale
        # para o Governo Central.
        nota=(
            "O Banco Central soma também as estatais e mede pela variação da dívida; o FMI "
            "mede só o governo geral, por receita menos despesa. Para o Brasil vale o do "
            "Banco Central; para comparar países, o do FMI."
        ),
    )


def _bi(valor_em_milhoes: float) -> float:
    return valor_em_milhoes / 1000


def despesa_contra_a_faixa(despesa: list[Ponto], ipca: list[Ponto], inicio: date) -> list[Grafico]:
    """O crescimento real, em 12 meses, da despesa primária total do Governo Central, contra a
    faixa em que a lei deixa crescer o limite da despesa (LC 200/2023)."""
    faixa = leis.FAIXA_DA_DESPESA
    reais, _ = em_reais_de_hoje(despesa, ipca)
    cresc = [p for p in contas.variacao(reais, 12) if p[0] >= inicio]
    if not cresc:
        return []
    quando, valor = cresc[-1]
    if valor > faixa.teto:
        onde = "acima do teto"
    elif valor < faixa.piso:
        onde = "abaixo do piso"
    else:
        onde = "dentro"
    banda = [(d, faixa.piso, faixa.teto) for d, _ in cresc if d >= faixa.desde]
    return [
        grafico(
            "despesa-real",
            "Despesa do Governo Central: crescimento acima da inflação",
            [serie("despesa", "Despesa total", cresc)],
            unidade="% em 12 meses, descontada a inflação",
            casas=1,
            periodicidade="M",
            janela_anos=2,
            faixa=Faixa(
                nome=f"faixa do limite da despesa ({br(faixa.piso)} % a {br(faixa.teto)} % ao ano)",
                pontos=banda,
            )
            if banda
            else None,
            manchete=(
                f"{br(valor)} % nos 12 meses até {periodo(quando, 'M')}, {onde} da faixa de "
                f"{br(faixa.piso)} % a {br(faixa.teto)} % ao ano."
            ),
            fonte=(
                "Tesouro Nacional, Resultado do Tesouro Nacional (série histórica, tabela "
                f"1.1); IPCA (Banco Central, SGS 433); faixa: {faixa.referencia}; cálculo próprio"
            ),
            # A faixa é o quanto a lei deixa crescer, por ano, o limite da despesa desde 2024.
            # Pagamento grande num mês só faz a linha saltar, e de novo um ano depois. O limite
            # deixa de fora o complemento da União ao Fundeb e os créditos extraordinários.
            nota=(
                "Despesa primária de 12 meses a preços de hoje contra a dos 12 anteriores. Não "
                "é a apuração oficial: o limite deixa despesas de fora, e a despesa total pode "
                "sair da faixa sem descumprir a lei."
            ),
        )
    ]


RESERVA_DA_AVALIACAO = (
    "Ministério do Planejamento e Orçamento, Relatório de Avaliação de Receitas e Despesas "
    "Primárias, {bimestre} de {ano} (quadros de apoio, tabela 1)"
)


def avaliacoes_do_ano(
    lido: avaliacao_bimestral.Quadros | None, ano: int
) -> tuple[list[leis.AvaliacaoBimestral], str]:
    """As avaliações do ano, da mais velha para a mais nova (no máximo três), e a fonte: as
    lidas à mão, com as da planilha mais nova (`lido`) por cima."""
    por_bimestre = {a.bimestre: a for a in leis.AVALIACOES_2026}
    if lido is not None:
        for a in lido.avaliacoes:
            por_bimestre[a.rotulo] = leis.AvaliacaoBimestral(
                a.rotulo, a.resultado, a.deducao, lido.fonte
            )
    lista = sorted(por_bimestre.values(), key=lambda a: a.bimestre)[-3:]
    fonte = (
        lido.fonte
        if lido is not None and lido.bimestre >= int(lista[-1].bimestre[0])
        else RESERVA_DA_AVALIACAO.format(bimestre=lista[-1].bimestre, ano=ano)
    )
    return lista, fonte


def meta_do_primario(
    ctx: Contexto, lido: avaliacao_bimestral.Quadros | None = None
) -> tuple[Cartao, Grafico, Tabela]:
    """O primário do Governo Central em 12 meses, pelo BC, contra a meta da LDO.

    Decisão do Caio (14/11/2026, opção "b"): o número de quem apura (o BC, LC 200/2023, art.
    2º, § 4º) contra a meta da lei, com o desconto que a apuração oficial faz dito ao lado,
    tirado do relatório bimestral do governo: da planilha do bimestre mais novo (`lido`) ou,
    sem ela, dos números lidos à mão. A meta vale para o ano fechado; a soma de 12 meses
    mostra o caminho.
    """
    meta = leis.META_PRIMARIA_2026
    avaliacoes, fonte_aval = avaliacoes_do_ano(lido, meta.ano)
    centro, piso, teto = _bi(meta.centro), _bi(meta.inferior), _bi(meta.superior)
    doze = contas.escalar(
        contas.soma_movel(_resultado(ctx.sgs("NFSP_PRIMARIO_GC_MES", 12))), 1 / 1000
    )
    ultima = avaliacoes[-1]
    apos = ultima.resultado + ultima.deducao
    fonte_bc = ctx.fonte_sgs("NFSP_PRIMARIO_GC_MES")

    c = cartao(
        "meta-primario",
        "Primário do Governo Central, 12 meses",
        doze,
        unidade="R$ bilhões",
        periodicidade="M",
        casas=1,
        detalhe=(
            f"meta de {meta.ano}; a conta oficial desconta R$ {br(ultima.deducao)} bi "
            f"({ultima.bimestre[:2]} bim.)"
        ),
        fonte=f"{fonte_bc}; meta: {meta.referencia}; desconto: {fonte_aval}",
        secao="fiscal",
        mini=60,
    )
    c.meta = Meta(centro=centro, inferior=piso, superior=teto, norma=meta.referencia)

    inicio_meta = date(meta.ano, 1, 1)
    meses_da_meta = [date(meta.ano, m, 1) for m in range(1, 13)]
    g = grafico(
        "meta-primario",
        f"O primário do Governo Central e a meta de {meta.ano}",
        [serie("gc", "Governo Central, 12 meses", doze, casas=1)],
        unidade="R$ bilhões (superávit +, déficit −)",
        casas=1,
        periodicidade="M",
        janela_anos=5,
        fonte=f"{fonte_bc}; meta: {meta.referencia}, § 1º; desconto: {fonte_aval}",
        faixa=Faixa(
            nome=f"intervalo da meta de {meta.ano} (R$ {br(piso, 0)} a R$ {br(teto)} bi)",
            pontos=[(d, piso, teto) for d in meses_da_meta if d >= inicio_meta],
        ),
        linhas=[LinhaRef(valor=centro, rotulo=f"meta R$ {br(centro)} bi")],
        # O BC é quem apura a meta (LC 200/2023); os descontos são despesas que outras normas
        # tiram da conta, previstos no relatório bimestral.
        nota=(
            "Soma de 12 meses apurada pelo Banco Central; a meta vale para o ano fechado. A "
            f"conta oficial desconta R$ {br(ultima.deducao)} bi ({ultima.bimestre} de {meta.ano})."
        ),
    )

    colunas = [a.bimestre for a in avaliacoes]
    t = Tabela(
        id="meta-primario",
        titulo=f"A meta de {meta.ano} pela conta do governo",
        subtitulo="Projeção para o ano inteiro, em cada relatório bimestral",
        colunas=colunas,
        linhas=[
            LinhaTabela(
                rotulo="Resultado primário projetado",
                valores=[a.resultado for a in avaliacoes],
                unidade="R$ bi",
            ),
            LinhaTabela(
                rotulo="Descontos da apuração",
                valores=[a.deducao for a in avaliacoes],
                unidade="R$ bi",
            ),
            LinhaTabela(
                rotulo="Resultado para a meta",
                valores=[round(a.resultado + a.deducao, 1) for a in avaliacoes],
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
        fonte=f"{fonte_aval}; meta: {meta.referencia}",
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


def fatores_da_divida(ctx: Contexto, anos: int, inicio: date) -> Grafico:
    """Por que a dívida bruta mudou em 12 meses: juros, crescimento do PIB em reais, primário
    e o resto (`decomposicoes.divida_por_fator`), a identidade do simulador olhada para trás."""
    taxa = ctx.memo.get("taxa_implicita_dbgg") or bcb_fiscal.taxa_implicita_dbgg()
    ctx.memo["taxa_implicita_dbgg"] = taxa
    fatores = decomposicoes.divida_por_fator(
        ctx.sgs("DBGG", anos),
        ctx.sgs("PIB_12M", anos),
        taxa,
        ctx.sgs("NFSP_PRIMARIO_12M", anos),
    )
    if not fatores:
        raise ValueError("sem meses comuns entre dívida, PIB, taxa implícita e primário")
    partes: list[tuple[str, str, list[Ponto]]] = [
        ("juros", "Juros da dívida", [(f.quando, f.juros) for f in fatores]),
        ("pib", "Crescimento do PIB em reais", [(f.quando, f.pib) for f in fatores]),
        ("primario", "Déficit primário", [(f.quando, f.primario) for f in fatores]),
        ("resto", "Resto: caixa, reservas, câmbio", [(f.quando, f.resto) for f in fatores]),
        ("total", "Variação da dívida", [(f.quando, f.variacao) for f in fatores]),
    ]
    return grafico(
        "divida-fatores",
        "Por que a dívida bruta mudou em 12 meses",
        [serie(id_, nome, pontos, desde=inicio) for id_, nome, pontos in partes],
        tipo="empilhado",
        total="total",
        unidade="pontos do PIB",
        casas=1,
        periodicidade="M",
        janela_anos=5,
        fonte=(
            f"{ctx.fonte_sgs('DBGG', 'PIB_12M', 'NFSP_PRIMARIO_12M')}; {bcb_fiscal.FONTE_TAXA}; "
            "cálculo próprio"
        ),
        # Juros: a taxa implícita vezes a dívida média. PIB em reais (com a inflação): a mesma
        # dívida fica menor diante de um PIB maior. Superávit entra para baixo. É a conta do
        # simulador olhada para trás; o BC publica a dele (fatores condicionantes) só na nota
        # mensal, com outra abertura.
        nota=(
            "As barras somadas dão a variação da dívida em 12 meses (a linha). O resto é o que "
            "juros, PIB e primário não explicam: caixa, reservas, câmbio."
        ),
    )


def _por_ano(niveis: list[Ponto]) -> dict[int, float]:
    """O retorno de cada ano civil fechado, em %, de um índice (o último ponto de cada ano)."""
    fim: dict[int, float] = {}
    for d, v in niveis:
        fim[d.year] = v
    fechados = [a for a in fim if a - 1 in fim and a < max(fim)]
    return {a: (fim[a] / fim[a - 1] - 1) * 100 for a in fechados}


def _aplicacoes(ctx: Contexto, juro: dict[int, float]) -> dict[str, estatais.Alternativa]:
    """O que o dinheiro das estatais teria rendido em outro lugar (Caio, 25/11/2026: "Compare
    com oq poderia ser investido ao invés delas"), com as contas de "Quanto rendeu R$ 100"."""
    inicio = date(ctx.hoje.year - 7, 12, 1)
    opcoes: dict[str, estatais.Alternativa] = {
        "divida": ("Abater dívida", juro, "realizado"),
        "cdi": (
            "CDI",
            _por_ano(mercados.acumular_diario(ctx.sgs("CDI_DIA", anos=8))),
            "realizado",
        ),
    }
    for chave, tipo, nome in (
        ("tesouro-pre", tesouro_direto.PREFIXADO, "Tesouro Prefixado"),
        ("tesouro-ipca", tesouro_direto.IPCA, "Tesouro IPCA+"),
    ):
        precos = tesouro_direto.precos(tipo, inicio - timedelta(days=10))
        carteira = mercados.carteira_rolada(precos, inicio, mercados.PRAZO_DO_TESOURO)
        opcoes[chave] = (nome, _por_ano(carteira), "realizado")
    opcoes["ipca"] = (
        "Inflação (IPCA)",
        _por_ano(mercados.acumular_mensal(ctx.sgs("IPCA", anos=8))),
        "referencia",
    )
    return opcoes


def _fonte_aplicacoes(ctx: Contexto) -> str:
    return (
        f"juro: {bcb_fiscal.FONTE_TAXA}; {ctx.fonte_sgs('CDI_DIA', 'IPCA')}; "
        "Tesouro Nacional, preços do Tesouro Direto"
    )


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
            "Saldo pelo prazo que falta para vencer, com as compromissadas do Banco Central, "
            "quase todas curtas. A parte de até 1 ano é a que vence nos próximos 12 meses."
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
                    "Focus (fim do ano)",
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
                serie("gc", "Governo Central", primario_gc, desde=inicio),
                serie(
                    "focus",
                    "Focus (fim do ano)",
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

    # "Ver em" (Caio, 19/11/2026): a dívida e o primário também em reais.
    ipca_longo = ctx.sgs("IPCA", anos + 2)
    indice = contas.indice_de_precos(ipca_longo)

    def saldo_de_hoje(chave: str) -> tuple[list[Ponto], list[Ponto], date]:
        """O saldo em R$ tri do mês e a preços do último mês com dado (pelo IPCA)."""
        saldo = [(d, v / 1e6) for d, v in ctx.sgs(chave, anos) if d >= inicio]
        base = max(d for d in indice if d <= saldo[-1][0])
        return saldo, contas.a_precos_de(saldo, indice, base), base

    try:
        dbgg_rs, dbgg_real, base_div = saldo_de_hoje("DBGG_RS")
        dlsp_rs, dlsp_real, _ = saldo_de_hoje("DLSP_RS")
        fonte_div_rs = ctx.fonte_sgs("DBGG_RS", "DLSP_RS")
        graficos[0] = com_variantes(
            graficos[0],
            "% do PIB",
            variante(
                "reais",
                "R$ (valor do mês)",
                "Dívida pública em reais",
                [
                    serie("dbgg", "Dívida bruta do governo geral", dbgg_rs),
                    serie("dlsp", "Dívida líquida do setor público", dlsp_rs),
                ],
                unidade="R$ trilhões",
                casas=1,
                periodicidade="M",
                nota="O saldo no fim de cada mês, em reais daquele mês.",
                fonte=fonte_div_rs,
            ),
            variante(
                "reais-hoje",
                "R$ de hoje",
                "Dívida pública em reais de hoje",
                [
                    serie("dbgg", "Dívida bruta do governo geral", dbgg_real),
                    serie("dlsp", "Dívida líquida do setor público", dlsp_real),
                ],
                unidade=f"R$ trilhões de {periodo(base_div, 'M')}",
                casas=1,
                periodicidade="M",
                nota="O saldo de cada mês levado a preços de hoje pelo IPCA.",
                fonte=f"{fonte_div_rs}; IPCA: {ctx.fonte_sgs('IPCA')}",
            ),
        )
    except Exception as erro:
        print(f"    fiscal: a dívida em reais ficou de fora ({str(erro)[:100]})")
    try:
        fonte_prim_rs = (
            f"{ctx.fonte_sgs('NFSP_PRIMARIO_MES', 'NFSP_PRIMARIO_GC_MES')}; "
            f"IPCA: {ctx.fonte_sgs('IPCA')}"
        )
        cons_r, base_p = em_reais_de_hoje(
            _resultado(ctx.sgs("NFSP_PRIMARIO_MES", anos)), ipca_longo
        )
        gc_r, _ = em_reais_de_hoje(_resultado(ctx.sgs("NFSP_PRIMARIO_GC_MES", anos)), ipca_longo)
        graficos[1] = com_variantes(
            graficos[1],
            "% do PIB",
            variante(
                "reais",
                "R$ de hoje",
                "Resultado primário em 12 meses, em reais de hoje",
                [
                    serie("consolidado", "Setor público consolidado", cons_r, desde=inicio),
                    serie("gc", "Governo Central", gc_r, desde=inicio),
                ],
                unidade=f"R$ bilhões de {periodo(base_p, 'M')} (superávit +, déficit −)",
                casas=0,
                periodicidade="M",
                nota=(
                    "Soma de 12 meses, cada mês a preços de hoje pelo IPCA (cálculo próprio). O "
                    "Focus não projeta o primário em reais."
                ),
                fonte=fonte_prim_rs,
            ),
        )
    except Exception as erro:
        print(f"    fiscal: o primário em reais ficou de fora ({str(erro)[:100]})")

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
    c_meta, g_meta, t_meta = meta_do_primario(
        ctx, avaliacao_bimestral.do_ano(leis.META_PRIMARIA_2026.ano, "fiscal")
    )
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
        ipca = ctx.sgs("IPCA", anos + 2)

        def reais(chave: str) -> list[Ponto]:
            return [p for p in em_reais_de_hoje(rtn[chave], ipca)[0] if p[0] >= inicio]

        mes_base = periodo(em_reais_de_hoje(rtn["despesa_total"], ipca)[1], "M")
        unidade_reais = f"R$ bilhões de {mes_base}, em 12 meses"
        nota_reais = "Soma de 12 meses, cada mês levado a preços de hoje pelo IPCA."
        fonte_reais = (
            "Tesouro Nacional, Resultado do Tesouro Nacional (série histórica, tabela 1.1); "
            f"IPCA: {ctx.fonte_sgs('IPCA')}"
        )
        graficos[-2] = com_variantes(
            graficos[-2],
            "% do PIB",
            variante(
                "reais",
                "R$ de hoje",
                "Receita e despesa do Governo Central, em reais de hoje",
                [
                    serie("receita", "Receita líquida", reais("receita_liquida"), casas=1),
                    serie("despesa", "Despesa total", reais("despesa_total"), casas=1),
                ],
                unidade=unidade_reais,
                casas=0,
                periodicidade="M",
                nota=f"{nota_reais} Receita líquida de transferências a estados e municípios.",
                fonte=fonte_reais,
            ),
        )
        despesa_r, rgps_r, pessoal_r = (
            reais("despesa_total"),
            reais("rgps"),
            reais("pessoal"),
        )
        graficos[-1] = com_variantes(
            graficos[-1],
            "% do PIB",
            variante(
                "reais",
                "R$ de hoje",
                "Para onde vai a despesa, em reais de hoje",
                [
                    serie("rgps", "Benefícios previdenciários", rgps_r, casas=1),
                    serie("pessoal", "Pessoal e encargos sociais", pessoal_r, casas=1),
                    serie(
                        "demais",
                        "Demais despesas",
                        contas.subtrair(contas.subtrair(despesa_r, rgps_r), pessoal_r),
                        casas=1,
                    ),
                ],
                unidade=unidade_reais,
                casas=0,
                periodicidade="M",
                nota=nota_reais,
                fonte=fonte_reais,
            ),
        )
        graficos += despesa_contra_a_faixa(rtn["despesa_total"], ipca_longo, inicio)
        c_rig, g_rig, t_rig = gasto.rigidez(rtn, pib, fonte_rtn, inicio, ipca, fonte_reais)
        cartoes += c_rig
        graficos += g_rig
        tabelas += t_rig
    except Exception as erro:
        print(f"    RTN ficou de fora: {str(erro)[:120]}")
    try:  # o gasto por função contra os outros países (FMI, COFOG)
        c_pais, t_pais = gasto.pecas_dos_paises()
        cartoes += c_pais
        tabelas += t_pais
    except Exception as erro:
        print(f"    o gasto por função (FMI) ficou de fora: {str(erro)[:120]}")

    # --- Servidores e estatais (Caio, 19/11/2026). Cada fonte que falhar deixa só o pedaço
    # dela de fora.
    try:
        pib_12m = ctx.sgs("PIB_12M", anos)
        c_serv, g_serv, t_serv = servidores.pecas(pib_12m, inicio, ctx.hoje)
        cartoes += c_serv
        graficos += g_serv
        tabelas += t_serv
        das_estatais: list[tuple[str, Callable[[], estatais.Pecas]]] = [
            (
                "os dividendos (RTN)",
                lambda: estatais.dividendos(
                    tesouro_rtn.detalhes(),
                    pib_12m,
                    "Tesouro Nacional, Resultado do Tesouro Nacional (série histórica, "
                    f"tabela 1.2); PIB: {ctx.fonte_sgs('PIB_12M')}",
                    inicio,
                ),
            ),
            ("a conta do ano (Sest)", lambda: estatais.conta_do_ano(estatais.sest_mais_nova())),
            (
                "o primário das estatais (BC)",
                lambda: estatais.primario(
                    ctx.sgs("ESTATAIS_FEDERAIS_12M", anos),
                    ctx.sgs("ESTATAIS_ESTADUAIS_12M", anos),
                    ctx.sgs("ESTATAIS_MUNICIPAIS_12M", anos),
                    ctx.sgs("ESTATAIS_FEDERAIS_MES", anos),
                    ctx.fonte_sgs(
                        "ESTATAIS_FEDERAIS_12M",
                        "ESTATAIS_ESTADUAIS_12M",
                        "ESTATAIS_MUNICIPAIS_12M",
                        "ESTATAIS_FEDERAIS_MES",
                    ),
                    inicio,
                ),
            ),
        ]
        for nome, montar in das_estatais:
            try:
                c_est, g_est, t_est = montar()
                cartoes += c_est
                graficos += g_est
                tabelas += t_est
            except Exception as erro:
                print(f"    estatais: {nome} ficou de fora: {str(erro)[:120]}")
        try:  # uma ficha por estatal (Sest, anexo I), num arquivo à parte
            fonte_sest, linhas_sest = sest.empresas_da_mais_nova()
            fichas = estatais.fichas(fonte_sest, linhas_sest)
            ctx.memo["fiscal_estatais"] = FichasEstatais(
                fichas=fichas,
                primeira=next((f.id for f in fichas if f.nome == estatais.PRIMEIRA), fichas[0].id),
                gerado_em=ctx.agora(),
            )
        except Exception as erro:
            print(f"    estatais: as fichas (Sest) ficaram de fora: {str(erro)[:120]}")
            linhas_sest = []
        try:  # o retorno de cada uma contra o juro da dívida (Caio, 25/11/2026)
            if linhas_sest:
                taxa = ctx.memo.get("taxa_implicita_dbgg") or bcb_fiscal.taxa_implicita_dbgg()
                ctx.memo["taxa_implicita_dbgg"] = taxa
                _, g_ret, t_ret = estatais.retorno(
                    fonte_sest, linhas_sest, taxa, bcb_fiscal.FONTE_TAXA
                )
                graficos += g_ret
                tabelas += t_ret
                juro = {d.year: v for d, v in taxa if d.month == 12}
                _, g_alt, t_alt = estatais.alternativas(
                    fonte_sest, linhas_sest, _aplicacoes(ctx, juro), _fonte_aplicacoes(ctx)
                )
                graficos += g_alt
                tabelas += t_alt
                _, g_rank, t_rank = estatais.ranking(fonte_sest, linhas_sest)
                graficos += g_rank
                tabelas += t_rank
        except Exception as erro:
            print(f"    estatais: o retorno contra o juro ficou de fora: {str(erro)[:120]}")
    except Exception as erro:
        print(f"    servidores e estatais ficaram de fora: {str(erro)[:120]}")

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
            "De que é feita a dívida, por indexador",
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
                "Dívida mobiliária federal em carteira. As séries não trazem o IPCA: "
                '"Índices de preços" é o que falta para 100 % (quase todo IPCA, mais os IGPs).'
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

    try:
        graficos.append(fatores_da_divida(ctx, anos, inicio))
    except Exception as erro:
        print(f"  aviso: fiscal: sem os fatores da dívida ({str(erro)[:120]})")

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
