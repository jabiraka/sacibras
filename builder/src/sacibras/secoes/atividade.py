"""Atividade: PIB trimestral, IBC-Br, indústria, varejo, serviços e confiança."""

from __future__ import annotations

from datetime import date

from sacibras import contas
from sacibras.fontes import bcb_focus, fmi, ibge_sidra
from sacibras.modelos import decomposicoes
from sacibras.schema import Cartao, Grafico, LinhaTabela, Secao, Tabela, VisaoTabela
from sacibras.secoes.base import Contexto, br, cartao, grafico, periodo, serie
from sacibras.tipos import Ponto

# SIDRA 5932, classificação 11255 (setores e subsetores). Conferido em 14/11/2026.
COMPONENTES = {
    "90707": "PIB",
    "93404": "Consumo das famílias",
    "93405": "Consumo do governo",
    "93406": "Investimento (FBCF)",
    "93407": "Exportações",
    "93408": "Importações",
    "90687": "Agropecuária",
    "90691": "Indústria",
    "90696": "Serviços",
    "90706": "Impostos sobre produtos",
}
FONTE_PIB = "IBGE, Contas Nacionais Trimestrais (SIDRA 5932)"
# Taxa de investimento (FBCF / PIB, SIDRA 6727, variável 2517) e de poupança (poupança bruta /
# PIB, SIDRA 6726, variável 9774), em % no trimestre, a preços correntes. Conferidas na API do
# SIDRA em 14/11/2026: 16,1 % e 16,6 % no 2º tri/2026. Do Econvitals (saving rate).
FONTE_INVESTIMENTO = "IBGE, Contas Nacionais Trimestrais (SIDRA 6727 e 6726)"
# Valores a preços correntes (SIDRA 1846, variável 585, R$ milhões), para pesar consumo e
# investimento na demanda privada. Conferido na API do SIDRA em 15/11/2026: consumo das
# famílias R$ 2.112.893 mi e FBCF R$ 552.092 mi no 2º tri/2026.
FONTE_DEMANDA_PRIVADA = "IBGE, Contas Nacionais Trimestrais (SIDRA 5932 e 1846); conta nossa"
NOTA_DEMANDA_PRIVADA = (
    "Demanda privada é o consumo das famílias somado ao investimento (FBCF), sem governo, "
    "estoques e exterior: mostra a força do gasto de famílias e empresas. Conta nossa: a "
    "variação em um ano de cada parte, pesada pelo tamanho dela em reais no mesmo trimestre "
    'do ano anterior (preços correntes do IBGE). É a ideia da "real final sales to private '
    'domestic purchasers" que o Econvitals mostra para os EUA.'
)


def demanda_privada(
    consumo: list[Ponto],
    investimento: list[Ponto],
    consumo_reais: list[Ponto],
    investimento_reais: list[Ponto],
) -> list[Ponto]:
    """Variação em um ano (%) de consumo das famílias + investimento.

    Cada parte entra com a variação em volume dela contra o mesmo trimestre do ano anterior,
    pesada pelo valor em reais correntes dela naquele trimestre (a base da comparação).
    """
    c, i = dict(consumo), dict(investimento)
    cr, ir = dict(consumo_reais), dict(investimento_reais)
    saida: list[Ponto] = []
    for d in sorted(set(c) & set(i)):
        base = date(d.year - 1, d.month, d.day)
        if base not in cr or base not in ir:
            continue
        peso_c, peso_i = cr[base], ir[base]
        saida.append((d, (peso_c * c[d] + peso_i * i[d]) / (peso_c + peso_i)))
    return saida


# De onde veio o crescimento: SIDRA 1620 (variável 583, índice de volume trimestral, média de
# 1995 = 100) e 1846 (variável 585, valores correntes), classificação 11255. Códigos conferidos
# pela resposta da API em 15/11/2026 (2º tri/2026: impostos líquidos sobre produtos, 90706,
# R$ 487.859 mi; importação, 93408, R$ 556.418 mi). (id da série, nome, sinal na soma do PIB)
DEMANDA: dict[str, tuple[str, str, int]] = {
    "93404": ("familias", "Consumo das famílias", 1),
    "93405": ("governo", "Consumo do governo", 1),
    "93406": ("fbcf", "Investimento (FBCF)", 1),
    "93407": ("exportacoes", "Exportações", 1),
    "93408": ("importacoes", "Importações", -1),
}
OFERTA: dict[str, tuple[str, str, int]] = {
    "90687": ("agro", "Agropecuária", 1),
    "90691": ("industria", "Indústria", 1),
    "90696": ("servicos", "Serviços", 1),
    "90706": ("impostos", "Impostos sobre produtos", 1),
}
FONTE_CONTRIBUICOES = "IBGE, Contas Nacionais Trimestrais (SIDRA 1620 e 1846); conta nossa"
NOTA_IMPORTACOES = (
    "As importações entram com o sinal trocado não porque tirem do PIB, mas para não contar "
    "duas vezes: o que veio de fora já está no consumo, no investimento e nas exportações."
)
FONTE_CARREGO = "IBGE, Contas Nacionais Trimestrais (SIDRA 1621, com ajuste sazonal); conta nossa"


Contribuicoes = dict[str, list[Ponto]]


def baixar_contas() -> tuple[dict[str, list[Ponto]], dict[str, list[Ponto]]]:
    """O índice de volume e o valor em reais correntes, trimestre a trimestre, do PIB e de
    cada componente da demanda e da oferta."""
    cats = ",".join(["90707", *DEMANDA, *OFERTA])
    volume = ibge_sidra.series(
        1620, 583, classificacao=f"c11255/{cats}", por="Setores", trimestral=True
    )
    valor = ibge_sidra.series(
        1846, 585, classificacao=f"c11255/{cats}", por="Setores", trimestral=True
    )
    return volume, valor


def por_ano(trimestral: dict[str, list[Ponto]]) -> dict[str, list[Ponto]]:
    """A soma dos quatro trimestres de cada ano completo, com a data de 1º de janeiro: o
    volume e o valor do ano, para a conta das contribuições no ano."""
    saida: dict[str, list[Ponto]] = {}
    for c, pontos in trimestral.items():
        anos: dict[int, list[float]] = {}
        for d, v in pontos:
            anos.setdefault(d.year, []).append(v)
        saida[c] = [(date(a, 1, 1), sum(vs)) for a, vs in sorted(anos.items()) if len(vs) == 4]
    return saida


def contribuicoes(
    volume: dict[str, list[Ponto]], valor: dict[str, list[Ponto]]
) -> tuple[Contribuicoes, Contribuicoes]:
    """Os pontos do crescimento do PIB que vieram de cada componente, pela demanda (com o
    resto à parte: estoques e ajuste) e pela oferta (o resto repartido pela fatia). Serve
    para trimestres (contra o mesmo do ano anterior) e para anos (`por_ano`)."""

    def sinais(partes: dict[str, tuple[str, str, int]]) -> dict[str, int]:
        return {c: sinal for c, (_, _, sinal) in partes.items()}

    return (
        decomposicoes.pib_por_componente(volume, valor, "90707", sinais(DEMANDA), True),
        decomposicoes.pib_por_componente(volume, valor, "90707", sinais(OFERTA), False),
    )


def graficos_das_contribuicoes(
    demanda: Contribuicoes, oferta: Contribuicoes, inicio: date
) -> list[Grafico]:
    """De onde veio o crescimento, quem produziu e quem comprou, empilhados, um trimestre por
    barra. A oferta vem primeiro: na tela larga fica à esquerda."""
    saida = []
    for id_, titulo, partes, contrib, resto, nota in (
        (
            "pib-contribuicoes-oferta",
            "De onde veio o crescimento: quem produziu",
            OFERTA,
            oferta,
            "",
            "Quantos pontos do crescimento do PIB, contra o mesmo trimestre do ano anterior, "
            "vieram de cada setor: a fatia dele no PIB um ano antes vezes o quanto cresceu. "
            "As barras somadas dão o crescimento do PIB (a linha); a diferença do encadeamento de "
            "preços (em média, 0,1 ponto) foi repartida pela fatia. Conta nossa.",
        ),
        (
            "pib-contribuicoes-demanda",
            "De onde veio o crescimento: quem comprou",
            DEMANDA,
            demanda,
            "Estoques e ajuste",
            "Quantos pontos do crescimento do PIB, contra o mesmo trimestre do ano anterior, "
            "vieram de cada gasto: a fatia dele no PIB um ano antes vezes o quanto cresceu. "
            "As barras somadas dão o crescimento do PIB (a linha). O IBGE publica o quanto cada "
            "componente cresceu, não a contribuição: a conta é nossa. Estoques e ajuste: o "
            "que sobra, a variação dos estoques mais a diferença do encadeamento de preços. "
            + NOTA_IMPORTACOES,
        ),
    ):
        series = [
            serie(sid, nome, contrib[c], desde=inicio) for c, (sid, nome, _) in partes.items()
        ]
        if resto:
            series.append(serie("resto", resto, contrib[decomposicoes.RESTO], desde=inicio))
        primeiro = next(iter(partes))
        soma = [(t, sum(dict(p)[t] for p in contrib.values())) for t, _ in contrib[primeiro]]
        series.append(serie("total", "PIB", soma, desde=inicio))
        saida.append(
            grafico(
                id_,
                titulo,
                series,
                tipo="empilhado",
                total="total",
                unidade="pontos percentuais",
                casas=1,
                periodicidade="T",
                janela_anos=5,
                fonte=FONTE_CONTRIBUICOES,
                nota=nota,
            )
        )
    return saida


def contribuicoes_do_pib(inicio: date) -> list[Grafico]:
    """Os dois gráficos de onde veio o crescimento, com os dados baixados aqui."""
    return graficos_das_contribuicoes(*contribuicoes(*baixar_contas()), inicio)


TRIMESTRES_NA_TABELA = 20
ANOS_NA_TABELA = 15
NOTA_COMPONENTES = (
    "Taxas: o quanto cada parte cresceu sozinha. Não se somam: cada uma pesa diferente no PIB, "
    "e demanda e oferta são duas maneiras de medir o mesmo PIB. Pontos do PIB: a taxa vezes a "
    "fatia da parte no PIB do ano anterior (conta nossa); estes somam: os de quem comprou dão "
    "o PIB, e os de quem produziu também (a menos do arredondamento). Estoques e ajuste: a "
    "variação dos estoques, que o IBGE não publica em volume, mais a diferença do "
    "encadeamento de preços. " + NOTA_IMPORTACOES
)


def tabela_componentes(
    taxas_tt: dict[str, list[Ponto]],
    taxas_aa: dict[str, list[Ponto]],
    taxas_4t: dict[str, list[Ponto]],
    tri: tuple[Contribuicoes, Contribuicoes],
    ano: tuple[Contribuicoes, Contribuicoes],
) -> Tabela:
    """O PIB por componente, um trimestre ou um ano escolhido na lista: a taxa de cada parte
    e os pontos do PIB que vieram dela. O ano é o fechado: a taxa de quatro trimestres no 4º
    trimestre e a conta das contribuições com os quatro somados."""

    def valor(series: dict[str, list[Ponto]], c: str, t: date) -> float | None:
        return dict(series.get(c, [])).get(t)

    def linhas(
        t: date, taxas: list[dict[str, list[Ponto]]], contrib: tuple[Contribuicoes, Contribuicoes]
    ) -> list[LinhaTabela]:
        demanda, oferta = contrib
        pontos_pib = (
            round(sum(dict(p).get(t, 0.0) for p in demanda.values()), 6)
            if demanda and t in dict(demanda[decomposicoes.RESTO])
            else None
        )
        saida = [
            LinhaTabela(
                rotulo="PIB",
                valores=[valor(x, "90707", t) for x in taxas] + [pontos_pib],
                unidade="",
                casas=1,
            )
        ]
        for grupo, partes, contr in (
            ("Quem comprou (demanda)", DEMANDA, demanda),
            ("Quem produziu (oferta)", OFERTA, oferta),
        ):
            for c, (_, nome, _) in partes.items():
                saida.append(
                    LinhaTabela(
                        rotulo=nome,
                        valores=[valor(x, c, t) for x in taxas] + [valor(contr, c, t)],
                        unidade="",
                        casas=1,
                        grupo=grupo,
                    )
                )
            if contr is demanda:
                saida.append(
                    LinhaTabela(
                        rotulo="Estoques e ajuste",
                        valores=[
                            *(None for _ in taxas),
                            valor(contr, decomposicoes.RESTO, t),
                        ],
                        unidade="",
                        casas=1,
                        grupo=grupo,
                    )
                )
        return saida

    visoes: list[VisaoTabela] = []
    for t, _ in reversed(taxas_aa["90707"][-TRIMESTRES_NA_TABELA:]):
        visoes.append(
            VisaoTabela(
                rotulo=periodo(t, "T"),
                grupo="Trimestres",
                subtitulo=f"{periodo(t, 'T')}: quanto cada parte cresceu e quanto somou ao PIB",
                colunas=[
                    "Contra o trimestre anterior (%)",
                    "Contra um ano antes (%)",
                    "Pontos do PIB em um ano",
                ],
                linhas=linhas(t, [taxas_tt, taxas_aa], tri),
            )
        )
    quartos = [d for d, _ in taxas_4t["90707"] if d.month == 10]
    for d in reversed(quartos[-ANOS_NA_TABELA:]):
        t = date(d.year, 1, 1)
        anual = {c: [(t, v) for q, v in pts if q == d] for c, pts in taxas_4t.items()}
        visoes.append(
            VisaoTabela(
                rotulo=str(d.year),
                grupo="Anos",
                subtitulo=f"{d.year}, o ano inteiro: quanto cada parte cresceu e quanto somou ao "
                "PIB",
                colunas=["No ano (%)", "Pontos do PIB no ano"],
                linhas=linhas(t, [anual], ano),
            )
        )
    primeira = visoes[0]
    return Tabela(
        id="pib-componentes",
        titulo="PIB por componente",
        subtitulo="Escolha o trimestre ou o ano: quanto cada parte cresceu e quanto somou ao PIB",
        colunas=primeira.colunas,
        linhas=primeira.linhas,
        visoes=visoes,
        rotulo_visoes="Período",
        fonte=f"{FONTE_PIB}, variáveis 6564, 6561 e 6562; pontos: {FONTE_CONTRIBUICOES}",
        nota=NOTA_COMPONENTES,
    )


def cartao_carrego() -> Cartao | None:
    """O carrego estatístico: quanto o PIB cresce no ano se ficar parado no nível do último
    trimestre (`decomposicoes.carrego`). Não é previsão; o Focus vai ao lado."""
    dessaz = ibge_sidra.serie(1621, 584, classificacao="c11255/90707", trimestral=True)
    c = decomposicoes.carrego(dessaz)
    if c is None:
        return None
    detalhe = f"se o PIB parar no nível do {periodo(c.ultimo, 'T').split('/')[0]}"
    try:
        focus = bcb_focus.mediana_anual_hoje("PIB Total").get(c.ano)
    except Exception:
        focus = None
    if focus is not None:
        detalhe += f"; Focus: {br(focus)} %"
    return cartao(
        "pib-carrego",
        f"Carrego do PIB para {c.ano}",
        [(c.ultimo, c.valor)],
        unidade="%",
        periodicidade="T",
        casas=1,
        detalhe=detalhe,
        fonte=FONTE_CARREGO,
        procedencia="calculado",
        secao="atividade",
    )


def _investimento_e_poupanca(investimento: list[Ponto], poupanca: list[Ponto]) -> list[Cartao]:
    """Os dois cartões, cada um contra o mesmo trimestre do ano anterior (não há ajuste)."""
    saida: list[Cartao] = []
    for id, rotulo, pontos in (
        ("taxa-investimento", "Taxa de investimento", investimento),
        ("taxa-poupanca", "Taxa de poupança", poupanca),
    ):
        if len(pontos) < 5:
            continue
        um_ano = pontos[-5]
        saida.append(
            cartao(
                id,
                rotulo,
                pontos,
                unidade="% do PIB",
                periodicidade="T",
                casas=1,
                detalhe=f"no {periodo(um_ano[0], 'T')}: {br(um_ano[1])} %",
                fonte=FONTE_INVESTIMENTO,
                secao="atividade",
                mini=40,
            )
        )
    return saida


GRUPOS_FMI = {
    "BRA": "Brasil",
    "G205": "América Latina e Caribe",
    "G200": "Emergentes",
    "G110": "Avançados",
}
"""O Brasil e os três grupos do FMI com que ele se compara (códigos do WEO, conferidos em
16/11/2026 contra os nomes de Brasil no mundo)."""


def investimento_contra_paises(ctx: Contexto) -> tuple[list[Cartao], list[Grafico]]:
    """Investimento e poupança em % do PIB, o Brasil contra os grupos de países (Caio,
    16/11/2026: *"talvez seja melhor comparar com outros países ao invés de mostrar só o
    quanto investimos"*). FMI, WEO: NID_NGDP (investimento total) e NGSD_NGDP (poupança
    nacional bruta), até o ano passado (o último ano pode ser estimativa do FMI)."""
    fim = ctx.hoje.year - 1
    weo = fmi.weo(list(GRUPOS_FMI), ["NID_NGDP", "NGSD_NGDP"], fim - 25, fim)
    fonte = f"FMI, World Economic Outlook de {periodo(weo.publicado_em, 'M')}"
    cartoes: list[Cartao] = []
    graficos: list[Grafico] = []
    for id, codigo, nome, o_que in (
        ("investimento", "NID_NGDP", "Investimento", "investe"),
        ("poupanca", "NGSD_NGDP", "Poupança", "poupa"),
    ):
        linhas = {
            pais: [
                (date(a, 1, 1), v) for a, v in sorted(weo.valores.get((pais, codigo), {}).items())
            ]
            for pais in GRUPOS_FMI
        }
        brasil, emergentes = linhas["BRA"], dict(linhas["G200"])
        if not brasil or brasil[-1][0] not in emergentes:
            continue
        ano = brasil[-1][0]
        partes = [
            f"{curto} {br(dict(linhas[g])[ano])} %"
            for g, curto in (("G205", "Am. Latina"), ("G200", "emergentes"), ("G110", "ricos"))
            if ano in dict(linhas[g])
        ]
        cartoes.append(
            cartao(
                f"{id}-brasil-fmi",
                f"{nome} do Brasil, pela conta do FMI",
                brasil,
                unidade="% do PIB",
                periodicidade="A",
                casas=1,
                detalhe="; ".join(partes),
                fonte=fonte,
                secao="atividade",
            )
        )
        graficos.append(
            grafico(
                f"{id}-paises",
                f"Quanto o Brasil {o_que}, contra outros países",
                [serie(g.lower(), GRUPOS_FMI[g], linhas[g], casas=1) for g in GRUPOS_FMI],
                unidade="% do PIB",
                casas=1,
                periodicidade="A",
                fonte=fonte,
                nota=(
                    f"{nome} em % do PIB, na mesma conta para todos (FMI). Os grupos são a "
                    "média dos países de cada um, pesada pelo tamanho da economia; a China "
                    "puxa a dos emergentes para cima. O último ano pode ser estimativa do FMI."
                ),
            )
        )
    return cartoes, graficos


def montar(ctx: Contexto) -> Secao:
    cats = ",".join(COMPONENTES)
    pib_tt = ibge_sidra.series(
        5932, 6564, classificacao=f"c11255/{cats}", por="Setores", trimestral=True
    )
    pib_aa = ibge_sidra.series(
        5932, 6561, classificacao=f"c11255/{cats}", por="Setores", trimestral=True
    )
    pib_4t_todos = ibge_sidra.series(
        5932, 6562, classificacao=f"c11255/{cats}", por="Setores", trimestral=True
    )
    pib_4t = pib_4t_todos["90707"]
    em_reais = ibge_sidra.series(
        1846, 585, classificacao="c11255/93404,93406", por="Setores", trimestral=True
    )
    privada = demanda_privada(
        pib_aa["93404"], pib_aa["93406"], em_reais["93404"], em_reais["93406"]
    )
    tt, aa = pib_tt["90707"], pib_aa["90707"]
    ctx.memo["pib_aa"] = aa
    ctx.memo["pib_4t"] = pib_4t

    ibc = ctx.sgs("IBCBR_DESSAZ")
    ibc_bruto = ctx.sgs("IBCBR")
    ibc_12m = contas.variacao(
        contas.soma_movel(ibc_bruto, 12), 12
    )  # média de 12 meses contra os 12 anteriores
    ibc_mm = contas.variacao(ibc, 1)

    pim = ibge_sidra.serie(8888, 12607, classificacao="c544/129314")
    pmc = ibge_sidra.serie(8880, 7170, classificacao="c11046/56734")
    pmc_ampliado = ibge_sidra.serie(8881, 7170, classificacao="c11046/56736")
    pms = ibge_sidra.serie(5906, 7168, classificacao="c11046/56726")
    investimento = ibge_sidra.serie(6727, 2517, trimestral=True)
    poupanca = ibge_sidra.serie(6726, 9774, trimestral=True)
    confianca = ctx.sgs("CONFIANCA_CONSUMIDOR")

    trimestre = periodo(tt[-1][0], "T")
    cartoes = [
        cartao(
            "pib-tt",
            "PIB no trimestre",
            tt,
            unidade="%",
            periodicidade="T",
            casas=1,
            detalhe=f"contra o trimestre anterior; {br(aa[-1][1])} % em um ano",
            fonte=FONTE_PIB,
            secao="atividade",
            mini=20,
        ),
        cartao(
            "pib-4t",
            "PIB em quatro trimestres",
            pib_4t,
            unidade="%",
            periodicidade="T",
            casas=1,
            fonte=FONTE_PIB,
            secao="atividade",
            mini=24,
        ),
        cartao(
            "demanda-privada",
            "Demanda privada, em um ano",
            privada,
            unidade="%",
            periodicidade="T",
            casas=1,
            detalhe="consumo das famílias + investimento",
            fonte=FONTE_DEMANDA_PRIVADA,
            procedencia="calculado",
            secao="atividade",
            mini=20,
        ),
        cartao(
            "ibcbr",
            "IBC-Br, 12 meses",
            ibc_12m,
            unidade="%",
            periodicidade="M",
            casas=1,
            detalhe=f"no mês, com ajuste: {br(ibc_mm[-1][1])} %",
            fonte=ctx.fonte_sgs("IBCBR", "IBCBR_DESSAZ"),
            procedencia="calculado",
            secao="atividade",
            mini=60,
        ),
        cartao(
            "industria",
            "Indústria (PIM), no mês",
            contas.variacao(pim, 1),
            unidade="%",
            periodicidade="M",
            casas=1,
            detalhe=f"em um ano: {br(contas.variacao(pim, 12)[-1][1])} %",
            fonte="IBGE, PIM-PF (SIDRA 8888)",
            secao="atividade",
            mini=24,
        ),
        cartao(
            "varejo",
            "Varejo (PMC), no mês",
            contas.variacao(pmc, 1),
            unidade="%",
            periodicidade="M",
            casas=1,
            detalhe=f"em um ano: {br(contas.variacao(pmc, 12)[-1][1])} %",
            fonte="IBGE, PMC (SIDRA 8880)",
            secao="atividade",
            mini=24,
        ),
        cartao(
            "servicos",
            "Serviços (PMS), no mês",
            contas.variacao(pms, 1),
            unidade="%",
            periodicidade="M",
            casas=1,
            detalhe=f"em um ano: {br(contas.variacao(pms, 12)[-1][1])} %",
            fonte="IBGE, PMS (SIDRA 5906)",
            secao="atividade",
            mini=24,
        ),
        *_investimento_e_poupanca(investimento, poupanca),
    ]

    inicio = date(ctx.hoje.year - 12, 1, 1)
    base = date(ctx.hoje.year - 5, 1, 1)
    graficos = [
        grafico(
            "pib-trimestral",
            "PIB: crescimento a cada trimestre",
            [
                serie("tt", "Contra o trimestre anterior (com ajuste sazonal)", tt, desde=inicio),
                serie("aa", "Contra o mesmo trimestre do ano anterior", aa, desde=inicio),
            ],
            tipo="barras",
            unidade="%",
            casas=1,
            periodicidade="T",
            janela_anos=5,
            fonte=FONTE_PIB,
        ),
        grafico(
            "pib-demanda",
            "PIB pela demanda: consumo, investimento e comércio exterior",
            [
                serie("familias", "Consumo das famílias", pib_aa["93404"], desde=inicio),
                serie("fbcf", "Investimento (FBCF)", pib_aa["93406"], desde=inicio),
                serie("governo", "Consumo do governo", pib_aa["93405"], desde=inicio),
                serie("exportacoes", "Exportações", pib_aa["93407"], desde=inicio),
                serie("pib", "PIB", aa, desde=inicio),
            ],
            unidade="% em um ano",
            casas=1,
            periodicidade="T",
            janela_anos=5,
            fonte=FONTE_PIB,
        ),
        grafico(
            "pib-oferta",
            "PIB pela oferta: agropecuária, indústria e serviços",
            [
                serie("agro", "Agropecuária", pib_aa["90687"], desde=inicio),
                serie("industria", "Indústria", pib_aa["90691"], desde=inicio),
                serie("servicos", "Serviços", pib_aa["90696"], desde=inicio),
                serie("pib", "PIB", aa, desde=inicio),
            ],
            unidade="% em um ano",
            casas=1,
            periodicidade="T",
            janela_anos=5,
            fonte=FONTE_PIB,
            nota=(
                "Cada setor contra o mesmo trimestre do ano anterior. A agropecuária pesa "
                "pouco no PIB, mas varia muito com a safra."
            ),
        ),
        grafico(
            "demanda-privada",
            "Demanda privada: o gasto de famílias e empresas",
            [
                serie("privada", "Demanda privada (consumo + investimento)", privada, desde=inicio),
                serie("pib", "PIB", aa, desde=inicio),
            ],
            unidade="% em um ano",
            casas=1,
            periodicidade="T",
            janela_anos=5,
            fonte=FONTE_DEMANDA_PRIVADA,
            nota=NOTA_DEMANDA_PRIVADA,
        ),
        grafico(
            "ibcbr",
            "IBC-Br: a prévia mensal do PIB",
            [serie("ibc", "IBC-Br com ajuste sazonal", ibc, desde=inicio)],
            unidade="índice",
            casas=1,
            periodicidade="M",
            janela_anos=5,
            fonte=ctx.fonte_sgs("IBCBR_DESSAZ"),
        ),
        grafico(
            "setores-mensais",
            "Indústria, varejo e serviços",
            [
                serie("pim", "Indústria (PIM-PF)", contas.base_100(pim, base), desde=base),
                serie("pmc", "Varejo restrito (PMC)", contas.base_100(pmc, base), desde=base),
                serie(
                    "pmca",
                    "Varejo ampliado (PMC)",
                    contas.base_100(pmc_ampliado, base),
                    desde=base,
                ),
                serie("pms", "Serviços (PMS)", contas.base_100(pms, base), desde=base),
            ],
            unidade=f"índice, {periodo(base, 'M')} = 100",
            casas=1,
            periodicidade="M",
            fonte="IBGE, SIDRA 8888, 8880, 8881 e 5906 (volume, com ajuste sazonal)",
            nota="Os quatro índices foram postos na mesma base para se compararem.",
        ),
        grafico(
            "investimento-poupanca",
            "Quanto o país investe e quanto poupa",
            [
                serie("investimento", "Taxa de investimento (FBCF / PIB)", investimento),
                serie("poupanca", "Taxa de poupança (poupança bruta / PIB)", poupanca),
            ],
            unidade="% do PIB no trimestre",
            casas=1,
            periodicidade="T",
            janela_anos=15,
            fonte=FONTE_INVESTIMENTO,
            nota=(
                "Investimento é o que se gasta em máquinas, construções e infraestrutura; "
                "poupança, a parte da renda do país que não vira consumo. Quando o país investe "
                "mais do que poupa, a diferença vem de fora (é o déficit em transações "
                "correntes). Números do trimestre, sem ajuste sazonal: compare com o mesmo "
                "trimestre de outros anos."
            ),
        ),
        grafico(
            "confianca",
            "Confiança do consumidor",
            [serie("icc", "Índice de Confiança do Consumidor", confianca, desde=inicio)],
            unidade="índice",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs("CONFIANCA_CONSUMIDOR"),
        ),
    ]

    vazio: Contribuicoes = {}
    tri, ano = (vazio, vazio), (vazio, vazio)
    try:
        volume, valor = baixar_contas()
        tri = contribuicoes(volume, valor)
        ano = contribuicoes(por_ano(volume), por_ano(valor))
        graficos += graficos_das_contribuicoes(*tri, inicio)
        carrego = cartao_carrego()
        if carrego:
            cartoes.append(carrego)
    except Exception as erro:  # as contas a mais não derrubam a seção
        print(f"  aviso: atividade sem as contribuições ou o carrego: {str(erro)[:120]}")
    tabelas = [tabela_componentes(pib_tt, pib_aa, pib_4t_todos, tri, ano)]
    try:
        c_fmi, g_fmi = investimento_contra_paises(ctx)
        cartoes += c_fmi
        graficos += g_fmi
    except Exception as erro:
        print(f"  aviso: atividade sem o investimento contra outros países: {str(erro)[:120]}")
    resumo = (
        f"O PIB cresceu {br(tt[-1][1])} % no {trimestre} contra o trimestre anterior e "
        f"{br(aa[-1][1])} % contra um ano antes; em quatro trimestres acumula "
        f"{br(pib_4t[-1][1])} %."
    )
    return Secao(
        id="atividade",
        titulo="Atividade",
        resumo=resumo,
        cartoes=cartoes,
        graficos=graficos,
        tabelas=tabelas,
        gerado_em=ctx.agora(),
    )
