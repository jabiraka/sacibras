"""Mercados: só os preços que contam a história macro — bolsa, dólar, juros futuros."""

from __future__ import annotations

from datetime import date, timedelta

from sacibras import contas
from sacibras.config import usar_b3
from sacibras.fontes import b3_derivativos, b3_indices, fmi, ipeadata, tesouro_direto
from sacibras.schema import Grafico, LinhaTabela, Secao, Tabela
from sacibras.secoes.base import Contexto, br, cartao, grafico, periodo, serie
from sacibras.tipos import Ponto


def _retornos(pontos: list[Ponto]) -> list[float | None]:
    """[no dia, em 30 dias, no ano, em 12 meses], em %."""
    dia = (pontos[-1][1] / pontos[-2][1] - 1) * 100 if len(pontos) > 1 else None
    return [dia, contas.em_dias(pontos, 30), contas.no_ano(pontos), contas.em_dias(pontos, 365)]


# (código na B3, nome, unidade, divisor do preço, casas, quantos vencimentos)
FUTUROS: list[tuple[str, str, str, float, int, int]] = [
    ("DOL", "Dólar futuro", "R$", 1000, 4, 1),
    ("IND", "Ibovespa futuro", "pontos", 1, 0, 1),
    ("BGI", "Boi gordo", "R$ por arroba", 1, 2, 1),
    ("CCM", "Milho", "R$ por saca", 1, 2, 1),
    ("SJC", "Soja", "US$ por saca", 1, 2, 1),
    ("ICF", "Café arábica", "US$ por saca", 1, 2, 1),
]


def _tabela_futuros(ctx: Contexto) -> Tabela | None:
    """O vencimento mais negociado de cada futuro, e os juros futuros de janeiro."""
    linhas: list[LinhaTabela] = []
    for venc, taxa in ctx.memo.get("curva_di", []):
        if venc.month == 1 and venc.year <= ctx.hoje.year + 5:
            linhas.append(
                LinhaTabela(
                    rotulo=f"Juro futuro (DI) para {periodo(venc, 'M')}",
                    valores=[taxa, None],
                    unidade="% a.a.",
                    casas=2,
                )
            )
    for codigo, nome, unidade, divisor, casas, _ in FUTUROS:
        try:
            contratos = [c for c in b3_derivativos.futuros(codigo) if c.preco]
        except Exception as erro:
            print(f"    futuro {codigo} ficou de fora: {str(erro)[:100]}")
            continue
        if not contratos:
            continue
        # O vencimento com mais contratos em aberto é o que forma preço.
        c = max(contratos[:4], key=lambda x: x.em_aberto)
        preco = float(c.preco or 0) / divisor
        variacao = (
            (c.ultimo / c.ajuste_anterior - 1) * 100 if c.ultimo and c.ajuste_anterior else None
        )
        linhas.append(
            LinhaTabela(
                rotulo=f"{nome}, vence em {periodo(c.vencimento, 'D')}",
                valores=[preco, variacao],
                unidade=unidade,
                casas=casas,
            )
        )
    if not linhas:
        return None
    return Tabela(
        id="futuros",
        titulo="Futuros: o preço de amanhã negociado hoje",
        subtitulo="Último negócio do vencimento com mais contratos em aberto",
        colunas=["Último", "Contra o ajuste anterior (%)"],
        linhas=linhas,
        fonte="B3, cotações de derivativos (atraso de 15 minutos no pregão)",
        nota=(
            "Juro futuro é a taxa prefixada até a data; dólar e Ibovespa futuros embutem o "
            "juro até o vencimento; boi, milho, soja e café antecipam preços de alimentos."
        ),
    )


def _amostrar(pontos: list[Ponto], diario_desde: date) -> list[Ponto]:
    """Diário a partir de `diario_desde`, um ponto por semana antes (o último de cada uma)."""
    saida: list[Ponto] = []
    semana: tuple[int, int] | None = None
    for d, v in pontos:
        if d < diario_desde:
            chave = d.isocalendar()[:2]
            if chave == semana and len(saida) > 1:  # o primeiro fica: é a base
                saida[-1] = (d, v)
                continue
            semana = (chave[0], chave[1])
        saida.append((d, v))
    return saida


def _acumular_diario(taxas: list[Ponto]) -> list[Ponto]:
    """Índice a partir de taxas % ao dia: o rendimento do dia entra no dia seguinte."""
    nivel, saida = 100.0, []
    for d, v in taxas:
        saida.append((d, nivel))
        nivel *= 1 + v / 100
    return saida


def _acumular_mensal(taxas: list[Ponto]) -> list[Ponto]:
    """Índice a partir de taxas % no mês (datadas no 1º dia do mês): o do mês entra no dia
    1º do seguinte."""
    if not taxas:
        return []
    nivel, saida = 100.0, [(taxas[0][0], 100.0)]
    for d, v in taxas:
        nivel *= 1 + v / 100
        seguinte = date(d.year + d.month // 12, d.month % 12 + 1, 1)
        saida.append((seguinte, nivel))
    return saida


# O prazo dos títulos do Tesouro em "Quanto rendeu": compra-se o de vencimento mais perto de
# cinco anos e, quando ele vence, o dinheiro vai para o de prazo mais perto de cinco anos
# naquele dia. Cinco anos é o prazo que os dois tipos (prefixado e IPCA+) tiveram à venda na
# década inteira; o mais curto que se compra é de seis meses.
PRAZO_DO_TESOURO = 5
PRAZO_MINIMO_DIAS = 180


def carteira_rolada(precos: tesouro_direto.Precos, inicio: date, prazo_anos: float) -> list[Ponto]:
    """R$ 100 aplicados em `inicio` num tipo de título do Tesouro Direto, rolados no vencimento.

    Compra o título com vencimento mais perto de `prazo_anos` (e pelo menos seis meses à
    frente); fica com ele, marcado pelo preço de venda do dia; no último dia em que o título
    tem preço (a véspera do vencimento), o dinheiro vai, pelo preço do dia, para o de prazo
    mais perto de `prazo_anos`. Sem imposto, taxa nem a diferença entre compra e venda."""
    por_titulo = {v: dict(p) for v, p in precos.items()}
    ultimo_dia = {v: p[-1][0] for v, p in precos.items() if p}
    datas = sorted({d for p in precos.values() for d, _ in p if d >= inicio})

    def escolher(d: date) -> date | None:
        alvo = d + timedelta(days=round(prazo_anos * 365.25))
        candidatos = [
            v
            for v, p in por_titulo.items()
            if d in p and (v - d).days >= PRAZO_MINIMO_DIAS and ultimo_dia[v] > d
        ]
        return min(candidatos, key=lambda v: abs((v - alvo).days)) if candidatos else None

    saida: list[Ponto] = []
    titulo: date | None = None
    cotas = 0.0
    valor = 100.0
    for d in datas:
        if titulo is None:
            titulo = escolher(d)
            if titulo is None:
                continue
            cotas = valor / por_titulo[titulo][d]
        preco = por_titulo[titulo].get(d)
        if preco is not None:
            valor = cotas * preco
        saida.append((d, valor))
        if d >= ultimo_dia[titulo]:
            # Venceu: o resgate (o último preço) compra o título seguinte no dia seguinte
            # com preço. Até lá, o valor fica parado.
            titulo = None
    return saida


def ouro_em_reais(ouro_usd: list[Ponto], dolar_mes: list[Ponto]) -> list[Ponto]:
    """O ouro em reais por onça, mês a mês: a média do mês em dólares (FMI) vezes o dólar
    médio do mês (Banco Central), na data do dia 15, o meio do mês da média."""
    dolar = {d.replace(day=1): v for d, v in dolar_mes}
    return [(d.replace(day=15), v * dolar[d]) for d, v in ouro_usd if d in dolar]


def retornos_em_reais(ctx: Contexto, ibov: list[Ponto], fonte_ibov: str) -> Grafico:
    """Quanto viraram R$ 100 em cada aplicação: a tela troca o ponto de partida."""
    inicio = date(ctx.hoje.year - 10, 1, 1)
    poupanca = [(d, v) for d, v in ctx.sgs("POUPANCA", anos=10) if d.day == 1]
    niveis = {
        "ibov": ("Ibovespa", [p for p in ibov if p[0] >= inicio], "realizado"),
        "dolar": ("Dólar", ctx.sgs("DOLAR", anos=10), "realizado"),
        "euro": ("Euro", ctx.sgs("EURO", anos=10), "realizado"),
        "cdi": ("CDI", _acumular_diario(ctx.sgs("CDI_DIA", anos=10)), "realizado"),
        "poupanca": ("Poupança", _acumular_mensal(poupanca), "realizado"),
    }
    fontes = [fonte_ibov, ctx.fonte_sgs("DOLAR", "EURO", "CDI_DIA", "POUPANCA", "IPCA")]
    notas: list[str] = []
    # Tesouro Direto e ouro: sem a fonte, a linha fica de fora e o resto sai.
    try:
        for chave, tipo, nome in [
            ("tesouro-pre", tesouro_direto.PREFIXADO, "Tesouro Prefixado"),
            ("tesouro-ipca", tesouro_direto.IPCA, "Tesouro IPCA+"),
        ]:
            precos = tesouro_direto.precos(tipo, inicio - timedelta(days=10))
            niveis[chave] = (nome, carteira_rolada(precos, inicio, PRAZO_DO_TESOURO), "realizado")
        fontes.append("Tesouro Nacional, preços do Tesouro Direto")
        notas.append(
            "Tesouro Prefixado e IPCA+ (os sem juros semestrais): o título que vence em uns "
            f"{PRAZO_DO_TESOURO} anos, trocado no vencimento pelo de prazo mais perto de "
            f"{PRAZO_DO_TESOURO} anos, com o preço de venda do dia (sobe e desce com os juros)."
        )
    except Exception as erro:
        print(f"    retornos: Tesouro Direto ficou de fora: {str(erro)[:120]}")
    try:
        ouro_usd = fmi.preco_commodity(fmi.OURO, inicio - timedelta(days=40))
        niveis["ouro"] = (
            "Ouro",
            ouro_em_reais(ouro_usd, ctx.sgs("DOLAR_MEDIA_MES", anos=11)),
            "realizado",
        )
        fontes.append(f"FMI, preços de commodities (PCPS); {ctx.fonte_sgs('DOLAR_MEDIA_MES')}")
        notas.append(
            "O ouro é a média do mês em dólares (FMI) vezes o dólar médio do mês, e sai com "
            "um mês de atraso."
        )
    except Exception as erro:
        print(f"    retornos: ouro ficou de fora: {str(erro)[:120]}")
    niveis["ipca"] = (
        "Inflação (IPCA)",
        _acumular_mensal(ctx.sgs("IPCA", anos=10)),
        "referencia",
    )
    comum = max(pontos[0][0] for _, pontos, _ in niveis.values())
    diario = ctx.hoje - timedelta(days=400)
    series = []
    for chave, (nome, pontos, papel) in niveis.items():
        # O mensal começa no último valor antes do ponto comum, e nada passa de hoje (a
        # poupança já sabe o rendimento do mês que corre).
        antes = [p for p in pontos if p[0] <= comum][-1:]
        pontos = [(comum, v) for _, v in antes] + [p for p in pontos if comum < p[0] <= ctx.hoje]
        series.append(
            serie(chave, nome, contas.base_100(_amostrar(pontos, diario)), papel=papel, casas=2)
        )
    return grafico(
        "retornos-em-reais",
        "Quanto rendeu R$ 100",
        series,
        unidade="R$",
        casas=2,
        periodicidade="D",
        fonte="; ".join(fontes),
        nota=" ".join(
            [
                "Cada linha é quanto R$ 100 aplicados no início do período valeriam hoje, em "
                "reais, antes de imposto e de taxa. O Ibovespa é só o preço (sem os dividendos: "
                "o índice com eles é da B3, fora daqui); dólar e euro, a cotação de venda do BC; "
                "o CDI rende dia a dia; a poupança, a do aniversário no dia 1º.",
                *notas,
                "O IPCA mostra o que a inflação comeu: acima dele, ganhou poder de compra.",
            ]
        ),
        largura="inteira",
    )


def montar(ctx: Contexto) -> Secao:
    ano = ctx.hoje.year
    b3 = usar_b3()
    dolar = ctx.sgs("DOLAR", anos=6)
    euro = ctx.sgs("EURO", anos=6)
    if b3:
        ibov = b3_indices.fechamentos("IBOV", ano - 10, ctx.hoje)
        fonte_ibov = "B3, estatísticas históricas do Ibovespa"
    else:
        ibov = ipeadata.serie(ipeadata.IBOVESPA, date(ano - 10, 1, 1))
        fonte_ibov = "IPEADATA (série GM366_IBVSP366, fechamento do Ibovespa)"

    indices: dict[str, list[Ponto]] = {"IBOV": [p for p in ibov if p[0].year >= ano - 2]}
    tabelas: list[Tabela] = []
    quando = ibov[-1][0]
    if b3:
        for codigo in b3_indices.INDICES:
            if codigo == "IBOV":
                continue
            try:
                indices[codigo] = b3_indices.fechamentos(codigo, ano - 2, ctx.hoje)
            except Exception as erro:
                print(f"    índice {codigo} ficou de fora: {str(erro)[:100]}")
        futuros = _tabela_futuros(ctx)
        if futuros:
            tabelas.append(futuros)
        tabelas.append(
            Tabela(
                id="indices-b3",
                titulo="Índices da B3",
                subtitulo=f"Fechamento de {periodo(quando, 'D')} e variação",
                colunas=["Pontos", "No dia (%)", "Em 30 dias (%)", "No ano (%)", "Em 12 meses (%)"],
                linhas=[
                    LinhaTabela(
                        rotulo=b3_indices.INDICES[codigo],
                        valores=[pontos[-1][1], *_retornos(pontos)],
                        unidade="",
                        casas=1,
                    )
                    for codigo, pontos in indices.items()
                    if len(pontos) > 2
                ],
                fonte="B3, estatísticas históricas dos índices",
                nota=(
                    "Os setoriais mostram onde o juro e o câmbio pesam: financeiro, consumo e "
                    "imobiliário sentem a Selic; materiais básicos, o dólar e as commodities."
                ),
            )
        )

    ibov_ano = contas.no_ano(ibov)
    dolar_ano = contas.no_ano(dolar)
    # Ibovespa em dólares: o índice dividido pela cotação do dia.
    mapa_dolar = dict(dolar)
    ibov_usd = [(d, v / mapa_dolar[d]) for d, v in ibov if d in mapa_dolar]
    cartoes = [
        cartao(
            "ibovespa",
            "Ibovespa",
            ibov,
            unidade="pontos",
            periodicidade="D",
            casas=0,
            detalhe=f"no ano: {br(ibov_ano or 0)} %",
            fonte=fonte_ibov,
            procedencia="mercado",
            secao="mercados",
            mini=250,
        ),
        cartao(
            "dolar",
            "Dólar",
            dolar,
            unidade="R$",
            periodicidade="D",
            casas=2,
            detalhe=f"no ano: {br(dolar_ano or 0)} %",
            fonte=ctx.fonte_sgs("DOLAR"),
            procedencia="mercado",
            secao="mercados",
            mini=250,
        ),
        cartao(
            "euro",
            "Euro",
            euro,
            unidade="R$",
            periodicidade="D",
            casas=2,
            detalhe=f"no ano: {br(contas.no_ano(euro) or 0)} %",
            fonte=ctx.fonte_sgs("EURO"),
            procedencia="mercado",
            secao="mercados",
            mini=250,
        ),
        cartao(
            "ibovespa-dolar",
            "Ibovespa em dólares",
            ibov_usd,
            unidade="pontos",
            periodicidade="D",
            casas=0,
            detalhe=f"no ano: {br(contas.no_ano(ibov_usd) or 0)} %",
            fonte=f"{fonte_ibov}; {ctx.fonte_sgs('DOLAR')}",
            procedencia="calculado",
            secao="mercados",
            mini=250,
        ),
    ]
    variacoes = Tabela(
        id="variacoes",
        titulo="Bolsa e câmbio em diferentes prazos",
        subtitulo=f"Variação até {periodo(quando, 'D')}",
        colunas=["Último", "No dia (%)", "Em 30 dias (%)", "No ano (%)", "Em 12 meses (%)"],
        linhas=[
            LinhaTabela(
                rotulo=nome,
                valores=[p[-1][1], *_retornos(p)],
                unidade=u,
                casas=0 if u == "pontos" else 2,
            )
            for nome, p, u in [
                ("Ibovespa", ibov, "pontos"),
                ("Ibovespa em dólares", ibov_usd, "pontos"),
                ("Dólar", dolar, "R$"),
                ("Euro", euro, "R$"),
            ]
        ],
        fonte=f"{fonte_ibov}; {ctx.fonte_sgs('DOLAR', 'EURO')}",
    )
    tabelas.insert(0, variacoes)
    graficos = [
        grafico(
            "ibovespa",
            "Ibovespa",
            [serie("ibov", "Ibovespa", ibov, casas=0)],
            unidade="pontos",
            casas=0,
            periodicidade="D",
            janela_anos=1,
            fonte=fonte_ibov,
        ),
        grafico(
            "dolar",
            "Dólar e euro",
            [serie("dolar", "Dólar", dolar, casas=4), serie("euro", "Euro", euro, casas=4)],
            unidade="R$",
            casas=2,
            periodicidade="D",
            janela_anos=1,
            fonte=ctx.fonte_sgs("DOLAR", "EURO"),
        ),
        grafico(
            "ibovespa-dolar",
            "Ibovespa em dólares",
            [serie("ibov-usd", "Ibovespa em dólares", ibov_usd, casas=0)],
            unidade="pontos ÷ R$/US$",
            casas=0,
            periodicidade="D",
            janela_anos=5,
            fonte=f"{fonte_ibov}; {ctx.fonte_sgs('DOLAR')}",
            nota=(
                "Como o estrangeiro enxerga a bolsa brasileira: o índice dividido pelo dólar "
                "do dia."
            ),
        ),
    ]
    if b3 and len(indices) > 1:
        base = date(ano - 1, 1, 1)
        comparados = [
            serie(c.lower(), b3_indices.INDICES[c], contas.base_100(indices[c], base), desde=base)
            for c in ("IBOV", "SMLL", "IFIX", "IDIV")
            if c in indices
        ]
        graficos.insert(
            2,
            grafico(
                "indices-comparados",
                "Bolsa por dentro: grandes, pequenas, fundos imobiliários e dividendos",
                comparados,
                unidade=f"índice, {periodo(comparados[0].pontos[0][0], 'D')} = 100",
                casas=1,
                periodicidade="D",
                fonte="B3, estatísticas históricas dos índices",
            ),
        )
    try:
        graficos.insert(2, retornos_em_reais(ctx, ibov, fonte_ibov))
    except Exception as erro:
        print(f"    retornos em reais ficaram de fora: {str(erro)[:120]}")
    resumo = (
        f"O Ibovespa fechou {periodo(quando, 'D')} em {br(ibov[-1][1], 0)} pontos "
        f"({br(ibov_ano or 0)} % no ano) e o dólar a R$ {br(dolar[-1][1], 2)} "
        f"({br(dolar_ano or 0)} % no ano)."
    )
    return Secao(
        id="mercados",
        titulo="Mercados",
        resumo=resumo,
        cartoes=cartoes,
        graficos=graficos,
        tabelas=tabelas,
        gerado_em=ctx.agora(),
    )
