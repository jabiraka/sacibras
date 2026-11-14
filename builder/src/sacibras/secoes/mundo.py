"""Brasil no mundo: as mesmas métricas para ~20 países, com as projeções do FMI.

Anuais e projeções: World Economic Outlook (FMI). Juro básico e inflação em 12 meses, para o
juro real: BIS. Cada métrica guarda a fonte; projeção é sempre a da própria fonte.
"""

from __future__ import annotations

from datetime import date

from sacibras.fontes import bis, fmi
from sacibras.schema import MetricaMundo, Mundo, Pais
from sacibras.secoes.base import Contexto, br
from sacibras.tipos import Ponto

# (ISO3 do FMI, ISO2 do BIS, nome, grupo)
PAISES: list[tuple[str, str, str, str]] = [
    ("BRA", "BR", "Brasil", "america_latina"),
    ("MEX", "MX", "México", "america_latina"),
    ("ARG", "AR", "Argentina", "america_latina"),
    ("CHL", "CL", "Chile", "america_latina"),
    ("COL", "CO", "Colômbia", "america_latina"),
    ("PER", "PE", "Peru", "america_latina"),
    ("CHN", "CN", "China", "emergentes"),
    ("IND", "IN", "Índia", "emergentes"),
    ("IDN", "ID", "Indonésia", "emergentes"),
    ("TUR", "TR", "Turquia", "emergentes"),
    ("ZAF", "ZA", "África do Sul", "emergentes"),
    ("RUS", "RU", "Rússia", "emergentes"),
    ("USA", "US", "Estados Unidos", "avancados"),
    ("CAN", "CA", "Canadá", "avancados"),
    ("DEU", "XM", "Alemanha", "avancados"),
    ("FRA", "XM", "França", "avancados"),
    ("ITA", "XM", "Itália", "avancados"),
    ("ESP", "XM", "Espanha", "avancados"),
    ("GBR", "GB", "Reino Unido", "avancados"),
    ("JPN", "JP", "Japão", "avancados"),
    ("KOR", "KR", "Coreia do Sul", "avancados"),
    ("AUS", "AU", "Austrália", "avancados"),
    ("G001", "", "Mundo", "agregado"),
    ("G200", "", "Emergentes", "agregado"),
    ("G205", "", "América Latina e Caribe", "agregado"),
    ("G110", "", "Avançados", "agregado"),
    ("G163", "XM", "Zona do euro", "agregado"),
]

# (id, indicador do WEO, nome, descrição, unidade, casas, maior é melhor)
WEO: list[tuple[str, str, str, str, str, int, bool | None]] = [
    ("pib", "NGDP_RPCH", "Crescimento do PIB", "Variação real do PIB no ano.", "% no ano", 1, True),
    (
        "inflacao",
        "PCPIPCH",
        "Inflação",
        "Preços ao consumidor, média do ano contra a média do ano anterior.",
        "% no ano",
        1,
        False,
    ),
    ("desemprego", "LUR", "Desemprego", "Taxa de desemprego, média do ano.", "%", 1, False),
    (
        "divida",
        "GGXWDG_NGDP",
        "Dívida bruta do governo",
        "Dívida bruta do governo geral no conceito do FMI, que inclui os títulos do Tesouro "
        "na carteira do Banco Central — por isso o número do Brasil é maior que a DBGG "
        "divulgada pelo Banco Central.",
        "% do PIB",
        1,
        False,
    ),
    (
        "primario",
        "GGXONLB_NGDP",
        "Resultado primário",
        "Receitas menos despesas do governo geral, sem os juros. Negativo é déficit.",
        "% do PIB",
        1,
        True,
    ),
    (
        "nominal",
        "GGXCNL_NGDP",
        "Resultado nominal",
        "Receitas menos despesas do governo geral, com os juros. Negativo é déficit.",
        "% do PIB",
        1,
        True,
    ),
    (
        "conta_corrente",
        "BCA_NGDPD",
        "Conta corrente",
        "Saldo das transações correntes com o exterior. Negativo é déficit.",
        "% do PIB",
        1,
        None,
    ),
    (
        "investimento",
        "NID_NGDP",
        "Investimento",
        "Formação bruta de capital, pública e privada.",
        "% do PIB",
        1,
        True,
    ),
    (
        "pib_per_capita",
        "PPPPC",
        "PIB per capita (PPC)",
        "PIB por habitante em dólares internacionais correntes, pela paridade do poder de "
        "compra: corrige a diferença de preços entre os países.",
        "US$ PPC",
        0,
        True,
    ),
]

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto"]
MESES += ["setembro", "outubro", "novembro", "dezembro"]


def _fim_de_ano(pontos: list[Ponto], anos: list[int]) -> list[float | None]:
    """O valor de dezembro de cada ano (ou o último mês disponível do ano corrente)."""
    por_ano: dict[int, float] = {}
    for d, v in pontos:
        por_ano[d.year] = v
    return [round(por_ano[a], 2) if a in por_ano else None for a in anos]


def montar(ctx: Contexto) -> Mundo:
    ano = ctx.hoje.year
    inicio, fim = ano - 20, ano + 5
    isos = [p[0] for p in PAISES]
    weo = fmi.weo(isos, [m[1] for m in WEO], inicio, fim)
    anos = list(range(inicio, fim + 1))
    edicao_ano = weo.publicado_em.year
    edicao = f"World Economic Outlook, {MESES[weo.publicado_em.month - 1]} de {edicao_ano}"
    fonte_weo = f"FMI, {edicao}"

    metricas: list[MetricaMundo] = []
    for id, indicador, nome, descricao, unidade, casas, melhor in WEO:
        valores: dict[str, list[float | None]] = {}
        for iso in isos:
            mapa = weo.valores.get((iso, indicador), {})
            if mapa:
                valores[iso] = [round(mapa[a], casas + 1) if a in mapa else None for a in anos]
        metricas.append(
            MetricaMundo(
                id=id,
                nome=nome,
                descricao=descricao,
                unidade=unidade,
                casas=casas,
                maior_e_melhor=melhor,
                fonte=fonte_weo,
                anos=anos,
                # O WEO de um ano traz esse ano ainda como projeção.
                primeiro_ano_projetado=edicao_ano,
                valores=valores,
            )
        )

    # Juro básico e juro real, pelo BIS (mensal → fim de cada ano).
    iso2 = sorted({p[1] for p in PAISES if p[1]})
    desde = date(inicio, 1, 1)
    juros = bis.juro_basico(iso2, desde)
    # A inflação é de cada país (a zona do euro tem a sua); o juro, do banco central comum.
    cpi = bis.inflacao_12m(sorted({*iso2, "DE", "FR", "IT", "ES"}), desde)
    cpi_iso2 = {"DEU": "DE", "FRA": "FR", "ITA": "IT", "ESP": "ES"}
    anos_bis = list(range(inicio, ano + 1))
    v_juro: dict[str, list[float | None]] = {}
    v_real: dict[str, list[float | None]] = {}
    ultimo_mes = date(inicio, 1, 1)
    for iso3, codigo, _, _ in PAISES:
        if not codigo or codigo not in juros:
            continue
        serie_juro = juros[codigo]
        ultimo_mes = max(ultimo_mes, serie_juro[-1][0])
        v_juro[iso3] = _fim_de_ano(serie_juro, anos_bis)
        inflacao = dict(cpi.get(cpi_iso2.get(iso3, codigo), []))
        real = [
            (d, ((1 + v / 100) / (1 + inflacao[d] / 100) - 1) * 100)
            for d, v in serie_juro
            if d in inflacao and inflacao[d] > -99
        ]
        if real:
            v_real[iso3] = _fim_de_ano(real, anos_bis)
    quando = f"{MESES[ultimo_mes.month - 1]} de {ultimo_mes.year}"
    metricas.insert(
        2,
        MetricaMundo(
            id="juro",
            nome="Juro básico",
            descricao=(
                f"Taxa básica do banco central no fim de cada ano; em {ano}, o último mês "
                f"disponível ({quando}). Alemanha, França, Itália e Espanha têm a taxa do Banco "
                "Central Europeu."
            ),
            unidade="% a.a.",
            casas=2,
            maior_e_melhor=None,
            fonte="BIS, taxas básicas dos bancos centrais (WS_CBPOL)",
            anos=anos_bis,
            primeiro_ano_projetado=None,
            valores=v_juro,
        ),
    )
    metricas.insert(
        3,
        MetricaMundo(
            id="juro_real",
            nome="Juro real",
            descricao=(
                "Juro básico descontado da inflação ao consumidor dos 12 meses anteriores "
                "(ex-post), no fim de cada ano ou no último mês com os dois dados."
            ),
            unidade="% a.a.",
            casas=1,
            maior_e_melhor=None,
            fonte="Cálculo sobre dados do BIS (WS_CBPOL e WS_LONG_CPI)",
            anos=anos_bis,
            primeiro_ano_projetado=None,
            valores=v_real,
        ),
    )

    def do_brasil(id: str, a: int) -> float | None:
        m = next(x for x in metricas if x.id == id)
        return m.valores["BRA"][m.anos.index(a)] if "BRA" in m.valores and a in m.anos else None

    pib, mundo = do_brasil("pib", ano), None
    m_pib = next(x for x in metricas if x.id == "pib")
    if "G001" in m_pib.valores:
        mundo = m_pib.valores["G001"][m_pib.anos.index(ano)]
    resumo = f"Para {ano}, o FMI projeta crescimento de {br(pib or 0)} % para o Brasil"
    if mundo is not None:
        resumo += f" e de {br(mundo)} % para o mundo"
    resumo += (
        f". Abaixo, o Brasil ao lado de {len([p for p in PAISES if p[3] != 'agregado']) - 1} "
        "países em crescimento, inflação, juros, contas públicas e contas externas, com as "
        f"projeções do FMI até {fim}."
    )
    return Mundo(
        titulo="Brasil no mundo",
        resumo=resumo,
        paises=[Pais(iso3=p[0], nome=p[2], grupo=p[3]) for p in PAISES],  # type: ignore[arg-type]
        metricas=metricas,
        ano_corrente=ano,
        edicao=edicao,
        gerado_em=ctx.agora(),
    )
