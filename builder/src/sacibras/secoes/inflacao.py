"""Inflação: IPCA, núcleos, aberturas, meta e expectativas."""

from __future__ import annotations

from datetime import date

from sacibras import contas
from sacibras.fontes import bcb_focus, ibge_sidra
from sacibras.leis import META_CONTINUA
from sacibras.schema import Faixa, Grafico, LinhaRef, LinhaTabela, Meta, Secao, Tabela
from sacibras.secoes.base import Contexto, br, cartao, grafico, ha_um_ano, periodo, serie
from sacibras.tipos import Ponto

NUCLEOS = ["NUCLEO_EX0", "NUCLEO_EX3", "NUCLEO_MS", "NUCLEO_DP", "NUCLEO_P55"]

# SIDRA 7060, classificação 315 (geral, grupo, subgrupo, item e subitem): os nove grupos.
GRUPOS_IPCA = {
    "7170": "Alimentação e bebidas",
    "7445": "Habitação",
    "7486": "Artigos de residência",
    "7558": "Vestuário",
    "7625": "Transportes",
    "7660": "Saúde e cuidados pessoais",
    "7712": "Despesas pessoais",
    "7766": "Educação",
    "7786": "Comunicação",
}


# As medidas da tabela de 1, 3 e 12 meses: rótulo e as séries mensais (mais de uma, a média).
MEDIDAS: list[tuple[str, list[str]]] = [
    ("IPCA", ["IPCA"]),
    ("Média dos núcleos", NUCLEOS),
    ("Núcleo EX0 (exclusão)", ["NUCLEO_EX0"]),
    ("Núcleo EX3 (exclusão)", ["NUCLEO_EX3"]),
    ("Núcleo MS (médias aparadas)", ["NUCLEO_MS"]),
    ("Núcleo DP (dupla ponderação)", ["NUCLEO_DP"]),
    ("Núcleo P55 (percentil 55)", ["NUCLEO_P55"]),
    ("Serviços", ["IPCA_SERVICOS"]),
    ("Bens industriais", ["IPCA_INDUSTRIAIS"]),
    ("Alimentação no domicílio", ["IPCA_ALIMENTACAO_DOMICILIO"]),
    ("Itens livres", ["IPCA_LIVRES"]),
    ("Administrados", ["IPCA_ADMINISTRADOS"]),
]

SEM_AJUSTE = (
    "O anualizado de 3 meses é sem ajuste sazonal (o Banco Central não publica essas "
    "medidas dessazonalizadas no SGS) e por isso sobe e desce com a época do ano, com "
    "alimentos e serviços: compare com o mesmo período do ano anterior, e não só com a meta."
)


def media_dos_nucleos_12m(ctx: Contexto) -> list[Ponto]:
    return contas.media_das_series([contas.acumulado(ctx.sgs(n), 12) for n in NUCLEOS])


def ritmo(mensais: list[list[Ponto]], n: int, *, anualizar: bool = True) -> list[Ponto]:
    """A média, entre as séries, da variação composta em `n` meses (levada ao ano, ou não).

    Com uma série só, é ela mesma. Com n = 12, anualizado e acumulado dão o mesmo número."""
    if anualizar:
        return contas.media_das_series([contas.anualizado(s, n) for s in mensais])
    return contas.media_das_series([contas.acumulado(s, n) for s in mensais])


def tabela_medidas(medidas: list[tuple[str, list[list[Ponto]], str]], fonte: str) -> Tabela | None:
    """IPCA, núcleos e aberturas no mês, em 3 meses anualizado (agora e um ano antes) e em 12.

    `medidas`: (rótulo, séries mensais em % no mês, fonte da linha). A data de referência é
    o último mês da primeira medida (o IPCA); quem não tem esse mês fica com "–"."""
    if not medidas or not medidas[0][1] or not medidas[0][1][0]:
        return None
    quando = medidas[0][1][0][-1][0]
    antes = quando.replace(year=quando.year - 1)
    linhas = []
    for rotulo, mensais, fonte_linha in medidas:
        mes = dict(ritmo(mensais, 1, anualizar=False))
        tres = dict(ritmo(mensais, 3))
        doze = dict(ritmo(mensais, 12, anualizar=False))
        linhas.append(
            LinhaTabela(
                rotulo=rotulo,
                valores=[mes.get(quando), tres.get(quando), tres.get(antes), doze.get(quando)],
                unidade="",
                casas=2,
                fonte=fonte_linha,
            )
        )
    return Tabela(
        id="ipca-medidas",
        titulo="Medidas de inflação: 1, 3 e 12 meses",
        subtitulo=(
            f"Até {periodo(quando, 'M')}. Um ano antes: os 3 meses até {periodo(antes, 'M')}, "
            "anualizados"
        ),
        colunas=[
            "No mês (%)",
            "3 meses, anualizado (%)",
            "Um ano antes (%)",
            "12 meses (%)",
        ],
        linhas=linhas,
        fonte=fonte,
        nota=(
            "Anualizado: a variação composta dos 3 meses levada a 12, (1 + v)⁴ − 1. "
            "Média dos núcleos: a média simples de EX0, EX3, MS, DP e P55, conta nossa. "
            + SEM_AJUSTE
        ),
    )


def _faixa_da_meta(ate: date) -> Faixa:
    meta = META_CONTINUA
    pontos = []
    cursor = meta.desde
    while cursor <= ate:
        pontos.append((cursor, meta.centro - meta.intervalo, meta.centro + meta.intervalo))
        cursor = date(cursor.year + cursor.month // 12, cursor.month % 12 + 1, 1)
    return Faixa(nome="intervalo da meta (1,5 % a 4,5 %)", pontos=pontos)


def _tabela_grupos() -> Tabela | None:
    """Os nove grupos do IPCA: variação no mês, em 12 meses e peso (SIDRA 7060)."""
    cats = ",".join(GRUPOS_IPCA)
    try:
        mes = ibge_sidra.series(
            7060, 63, periodos="last 1", classificacao=f"c315/{cats}", por="Geral"
        )
        doze = ibge_sidra.series(
            7060, 2265, periodos="last 1", classificacao=f"c315/{cats}", por="Geral"
        )
        peso = ibge_sidra.series(
            7060, 66, periodos="last 1", classificacao=f"c315/{cats}", por="Geral"
        )
    except Exception:
        return None
    if not mes:
        return None
    quando = next(iter(mes.values()))[-1][0]
    linhas = [
        LinhaTabela(
            rotulo=nome,
            valores=[
                mes.get(codigo, [(quando, float("nan"))])[-1][1] if codigo in mes else None,
                doze[codigo][-1][1] if codigo in doze else None,
                peso[codigo][-1][1] if codigo in peso else None,
            ],
            unidade="",
            casas=2,
        )
        for codigo, nome in GRUPOS_IPCA.items()
    ]
    linhas.sort(key=lambda linha: -(linha.valores[1] or 0))
    return Tabela(
        id="ipca-grupos",
        titulo=f"IPCA por grupo em {periodo(quando, 'M')}",
        subtitulo="Ordenado pela variação em 12 meses",
        colunas=["No mês (%)", "Em 12 meses (%)", "Peso no índice (%)"],
        linhas=linhas,
        fonte="IBGE, SIDRA tabela 7060 (variáveis 63, 2265 e 66)",
    )


def montar(ctx: Contexto) -> Secao:
    ipca = ctx.sgs("IPCA")
    ipca12 = ctx.sgs("IPCA_12M")
    nucleos12 = media_dos_nucleos_12m(ctx)
    servicos12 = contas.acumulado(ctx.sgs("IPCA_SERVICOS"), 12)
    livres12 = contas.acumulado(ctx.sgs("IPCA_LIVRES"), 12)
    adm12 = contas.acumulado(ctx.sgs("IPCA_ADMINISTRADOS"), 12)
    igpm12 = contas.acumulado(ctx.sgs("IGPM"), 12)
    inpc12 = contas.acumulado(ctx.sgs("INPC"), 12)
    ipca15 = ctx.sgs("IPCA15")
    difusao = ctx.sgs("IPCA_DIFUSAO")
    meta = META_CONTINUA

    edicao, focus_mensal = bcb_focus.mensais_hoje("IPCA")
    focus_anual = bcb_focus.mediana_anual_hoje("IPCA")
    ctx.memo["focus_ipca_anual"] = focus_anual
    ctx.memo["focus_edicao"] = edicao
    ultimo_mes = ipca[-1][0]
    a_frente = [p for p in focus_mensal if p[0] > ultimo_mes][:12]

    # O IPCA em 12 meses projetado pelo consenso: os meses realizados que ainda ficam na
    # janela, compostos com as medianas mensais do Focus.
    caminho: list[Ponto] = [ipca12[-1]]
    janela = [v for _, v in ipca[-12:]]
    for quando, mediana in a_frente:
        janela = [*janela[1:], mediana]
        fator = 1.0
        for v in janela:
            fator *= 1 + v / 100
        caminho.append((quando, (fator - 1) * 100))

    teto = meta.centro + meta.intervalo
    anterior = ha_um_ano(ipca12)
    piso = meta.centro - meta.intervalo
    distancia = ipca12[-1][1] - meta.centro
    lado = "acima" if distancia > 0 else "abaixo"
    cartao_ipca = cartao(
        "ipca-12m",
        "IPCA em 12 meses",
        ipca12,
        unidade="%",
        periodicidade="M",
        casas=2,
        detalhe=(
            f"{br(abs(distancia), 2)} pp {lado} da meta de {br(meta.centro)} % "
            f"(intervalo de {br(piso)} % a {br(teto)} %)"
        ),
        fonte=f"{ctx.fonte_sgs('IPCA_12M')}; meta: {meta.referencia}",
        secao="inflacao",
        mini=60,
    )
    cartao_ipca.meta = Meta(centro=meta.centro, inferior=piso, superior=teto, norma=meta.referencia)
    cartoes = [
        cartao_ipca,
        cartao(
            "ipca-mes",
            "IPCA do mês",
            ipca,
            unidade="%",
            periodicidade="M",
            casas=2,
            detalhe=f"IPCA-15 de {periodo(ipca15[-1][0], 'M')}: {br(ipca15[-1][1], 2)} %",
            fonte=ctx.fonte_sgs("IPCA"),
            secao="inflacao",
            mini=24,
        ),
        cartao(
            "nucleos-12m",
            "Média dos núcleos, 12 meses",
            nucleos12,
            unidade="%",
            periodicidade="M",
            casas=2,
            detalhe="EX0, EX3, MS, DP e P55",
            fonte=ctx.fonte_sgs(*NUCLEOS),
            procedencia="calculado",
            secao="inflacao",
            mini=60,
        ),
        cartao(
            "servicos-12m",
            "Serviços, 12 meses",
            servicos12,
            unidade="%",
            periodicidade="M",
            casas=2,
            fonte=ctx.fonte_sgs("IPCA_SERVICOS"),
            procedencia="calculado",
            secao="inflacao",
            mini=60,
        ),
        cartao(
            "difusao",
            "Difusão do IPCA",
            difusao,
            unidade="%",
            periodicidade="M",
            casas=1,
            detalhe="parcela dos itens que subiram",
            fonte=ctx.fonte_sgs("IPCA_DIFUSAO"),
            secao="inflacao",
            mini=36,
        ),
    ]
    mensais_nucleos = [ctx.sgs(n) for n in NUCLEOS]
    nucleos3 = ritmo(mensais_nucleos, 3)
    nucleos3_antes = dict(nucleos3).get(nucleos3[-1][0].replace(year=nucleos3[-1][0].year - 1))
    cartoes.append(
        cartao(
            "nucleos-3m",
            "Média dos núcleos, 3 meses anualizado",
            nucleos3,
            unidade="%",
            periodicidade="M",
            casas=2,
            detalhe=(
                "sem ajuste sazonal"
                + (
                    f"; um ano antes: {br(nucleos3_antes, 2)} %"
                    if nucleos3_antes is not None
                    else ""
                )
            ),
            fonte=ctx.fonte_sgs(*NUCLEOS),
            procedencia="calculado",
            secao="inflacao",
            mini=36,
        )
    )
    ano = ctx.hoje.year
    if ano in focus_anual:
        cartoes.append(
            cartao(
                "focus-ipca",
                f"Focus: IPCA de {ano}",
                [(edicao, focus_anual[ano])],
                unidade="%",
                periodicidade="D",
                casas=2,
                detalhe=(
                    f"{ano + 1}: {br(focus_anual[ano + 1], 2)} %" if ano + 1 in focus_anual else ""
                ),
                fonte="Banco Central, Focus (mediana)",
                procedencia="mercado",
                secao="previsoes",
            )
        )

    inicio = date(ctx.hoje.year - 12, 1, 1)
    graficos: list[Grafico] = [
        grafico(
            "ipca-12m",
            "IPCA em 12 meses, a meta e o que o mercado espera",
            [
                serie("ipca", "IPCA", ipca12, desde=inicio),
                serie("nucleos", "Média dos núcleos", nucleos12, desde=inicio),
                serie("focus", "Focus (mediana)", caminho, papel="consenso"),
            ],
            unidade="% em 12 meses",
            casas=2,
            periodicidade="M",
            faixa=_faixa_da_meta(caminho[-1][0]),
            linhas=[LinhaRef(valor=meta.centro, rotulo=f"meta {br(meta.centro)} %")],
            janela_anos=5,
            fonte=f"{ctx.fonte_sgs('IPCA_12M', *NUCLEOS)}; Focus de {periodo(edicao, 'D')}",
            nota=(
                "Tracejado: o IPCA em 12 meses que resulta das medianas mensais do Focus. "
                f"Meta: {meta.referencia}. A faixa aparece a partir de jan/2025, quando a meta "
                "passou a ser contínua."
            ),
            largura="inteira",
        ),
        grafico(
            "ipca-mensal",
            "IPCA mês a mês",
            [
                serie("ipca", "IPCA", ipca, desde=date(ctx.hoje.year - 3, 1, 1)),
                serie("focus", "Focus (mediana)", [ipca[-1], *a_frente[:6]], papel="consenso"),
            ],
            tipo="barras",
            unidade="% no mês",
            casas=2,
            periodicidade="M",
            janela_anos=2,
            fonte=f"{ctx.fonte_sgs('IPCA')}; Focus de {periodo(edicao, 'D')}",
        ),
        grafico(
            "ipca-aberturas",
            "Serviços, livres e administrados",
            [
                serie("servicos", "Serviços", servicos12, desde=inicio),
                serie("livres", "Itens livres", livres12, desde=inicio),
                serie("administrados", "Administrados", adm12, desde=inicio),
            ],
            unidade="% em 12 meses",
            casas=2,
            periodicidade="M",
            janela_anos=5,
            fonte=ctx.fonte_sgs("IPCA_SERVICOS", "IPCA_LIVRES", "IPCA_ADMINISTRADOS"),
            nota="Acumulado em 12 meses composto a partir da variação mensal de cada grupo.",
        ),
        grafico(
            "ipca-difusao",
            "Difusão: quantos itens subiram no mês",
            [
                serie("difusao", "Difusão", difusao, desde=inicio),
                serie("media", "Média de 6 meses", contas.media_movel(difusao, 6), desde=inicio),
            ],
            unidade="% dos itens",
            casas=1,
            periodicidade="M",
            janela_anos=5,
            fonte=ctx.fonte_sgs("IPCA_DIFUSAO"),
        ),
        grafico(
            "outros-indices",
            "IPCA, INPC e IGP-M",
            [
                serie("ipca", "IPCA", ipca12, desde=inicio),
                serie("inpc", "INPC", inpc12, desde=inicio),
                serie("igpm", "IGP-M", igpm12, desde=inicio),
            ],
            unidade="% em 12 meses",
            casas=2,
            periodicidade="M",
            janela_anos=5,
            fonte=ctx.fonte_sgs("IPCA_12M", "INPC", "IGPM"),
        ),
        grafico(
            "nucleos-ritmo",
            "Média dos núcleos: o ritmo de 3 meses e de 12 meses",
            [
                serie("doze", "12 meses", nucleos12, desde=inicio),
                serie("tres", "3 meses, anualizado", nucleos3, desde=inicio),
            ],
            unidade="% ao ano",
            casas=2,
            periodicidade="M",
            linhas=[LinhaRef(valor=meta.centro, rotulo=f"meta {br(meta.centro)} %")],
            janela_anos=5,
            fonte=ctx.fonte_sgs(*NUCLEOS),
            nota=(
                "Média simples dos cinco núcleos (EX0, EX3, MS, DP e P55), conta nossa. "
                "Anualizado: a variação composta dos 3 meses levada a 12, (1 + v)⁴ − 1. "
                f"Meta: {meta.referencia}. " + SEM_AJUSTE
            ),
        ),
    ]

    medidas = tabela_medidas(
        [
            (rotulo, [ctx.sgs(c) for c in chaves], ctx.fonte_sgs(*chaves))
            for rotulo, chaves in MEDIDAS
        ],
        ctx.fonte_sgs(*dict.fromkeys(c for _, chaves in MEDIDAS for c in chaves)),
    )
    tabelas = [t for t in [_tabela_grupos(), medidas] if t]
    fora = "acima do teto" if ipca12[-1][1] > teto else "dentro do intervalo"
    resumo = (
        f"O IPCA acumula {br(ipca12[-1][1], 2)} % em 12 meses até {periodo(ipca12[-1][0], 'M')}, "
        f"{fora} da meta de {br(meta.centro)} %"
    )
    if anterior is not None:
        resumo += f" (um ano antes: {br(anterior, 2)} %)"
    resumo += f". A média dos cinco núcleos está em {br(nucleos12[-1][1], 2)} %."
    return Secao(
        id="inflacao",
        titulo="Inflação",
        resumo=resumo,
        cartoes=cartoes,
        graficos=graficos,
        tabelas=tabelas,
        gerado_em=ctx.agora(),
    )
