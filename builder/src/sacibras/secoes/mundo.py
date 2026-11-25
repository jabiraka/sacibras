"""Brasil no mundo: as mesmas métricas para ~20 países, com as projeções do FMI.

Anuais e projeções: World Economic Outlook (FMI). Juro básico, inflação em 12 meses e câmbio
contra o dólar: BIS. Juro de 10 anos: OCDE (o do Brasil, do Tesouro Direto). Produtividade
(PTF, produto por hora, capital por trabalhador, capital humano, horas, parte do trabalho na
renda, retorno do capital e preço do investimento): Penn World Table, até 2023 (CC BY 4.0).
Cada métrica guarda a fonte; projeção é sempre a da própria fonte.
"""

from __future__ import annotations

import contextlib
import gettext
from collections.abc import Callable
from datetime import date, timedelta

import pycountry

from sacibras.fontes import banco_mundial, bis, fmi, ocde_juros, ocde_receita, pwt, tesouro_direto
from sacibras.modelos import risco
from sacibras.schema import GrupoMundo, MetricaMundo, Mundo, MundoPaises, Pais
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
    ("G119", "", "G7", "agregado"),
    ("G505", "", "Ásia emergente", "agregado"),
    ("G903", "", "Europa emergente", "agregado"),
    ("G400", "", "Oriente Médio e Ásia Central", "agregado"),
    ("G603", "", "África Subsaariana", "agregado"),
]

# Grupos da hierarquia oficial do FMI (H_WEO_COUNTRIES) que se abrem por país. Conferido em
# 14/11/2026: G001 197 países, G110 43, G200 154, G163 21, G205 33, G119 7, G505 30, G903 14,
# G400 32, G603 45. GX123 (outros avançados) fica de fora: não é um grupo que se busque.
GRUPOS: list[tuple[str, str]] = [
    ("G001", "Mundo"),
    ("G110", "Avançados"),
    ("G163", "Zona do euro"),
    ("G119", "G7"),
    ("G200", "Emergentes"),
    ("G205", "América Latina e Caribe"),
    ("G505", "Ásia emergente"),
    ("G903", "Europa emergente"),
    ("G400", "Oriente Médio e Ásia Central"),
    ("G603", "África Subsaariana"),
]

# Códigos do FMI que não são ISO 3166-1 (conferido em 14/11/2026: só estes dois no WEO).
NOMES_FORA_DO_ISO: dict[str, str] = {
    "KOS": "Kosovo",
    "WBG": "Cisjordânia e Gaza",
}

# A tradução pt_BR do ISO sai oficialesca ou em português de Portugal para alguns países;
# aqui, o nome como se diz no Brasil.
NOMES_CORRIGIDOS: dict[str, str] = {
    "AZE": "Azerbaijão",
    "BEN": "Benim",
    "BFA": "Burkina Faso",
    "BHR": "Bahrein",
    "BIH": "Bósnia e Herzegovina",
    "BLR": "Bielorrússia",
    "COD": "RD Congo",
    "CZE": "República Tcheca",
    "ERI": "Eritreia",
    "FSM": "Micronésia",
    "IRN": "Irã",
    "KNA": "São Cristóvão e Nevis",
    "MMR": "Mianmar",
    "PNG": "Papua Nova Guiné",
    "RUS": "Rússia",
    "SGP": "Singapura",
    "SWZ": "Essuatíni",
    "TJK": "Tajiquistão",
    "TLS": "Timor-Leste",
    "TTO": "Trinidad e Tobago",
}

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
        "Dívida bruta do governo geral no conceito do FMI, com os títulos do Tesouro na "
        "carteira do Banco Central: por isso a do Brasil passa da DBGG do Banco Central.",
        "% do PIB",
        1,
        False,
    ),
    (
        "primario",
        "GGXONLB_NGDP",
        "Resultado primário",
        # A tabela lado a lado (FMI e BC) está em Contas públicas › Primário e juros.
        "Receitas menos despesas do governo geral, sem juros; negativo é déficit. No Brasil "
        "difere do Banco Central, que soma as estatais e mede pela variação da dívida.",
        "% do PIB",
        1,
        True,
    ),
    (
        "nominal",
        "GGXCNL_NGDP",
        "Resultado nominal",
        "Receitas menos despesas do governo geral, com juros; negativo é déficit. No Brasil "
        "difere do Banco Central pela mesma razão do primário.",
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

ARQUIVO_PAISES = "mundo-paises.json"

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto"]
MESES += ["setembro", "outubro", "novembro", "dezembro"]


def _fim_de_ano(pontos: list[Ponto], anos: list[int]) -> list[float | None]:
    """O valor de dezembro de cada ano (ou o último mês disponível do ano corrente)."""
    por_ano: dict[int, float] = {}
    for d, v in pontos:
        por_ano[d.year] = v
    return [round(por_ano[a], 2) if a in por_ano else None for a in anos]


def nome_do_pais(iso3: str, traducao: gettext.NullTranslations | None = None) -> str:
    """O nome em português: o mapa manual primeiro, depois o ISO 3166-1 traduzido (pt_BR)."""
    if iso3 in NOMES_CORRIGIDOS:
        return NOMES_CORRIGIDOS[iso3]
    if iso3 in NOMES_FORA_DO_ISO:
        return NOMES_FORA_DO_ISO[iso3]
    pais = pycountry.countries.get(alpha_3=iso3)
    if pais is None:
        raise KeyError(f"País {iso3} sem nome: acrescente em NOMES_FORA_DO_ISO")
    if traducao is None:
        traducao = gettext.translation(
            "iso3166-1", pycountry.LOCALES_DIR, languages=["pt_BR"], fallback=True
        )
    # common_name quando existe ("Coreia do Sul", "Bolívia"); o gettext do common_name em
    # pt_BR às vezes cai em português de Portugal (Irão), por isso o mapa acima o cobre.
    return traducao.gettext(getattr(pais, "common_name", None) or pais.name)


def _iso2_do_bis(iso2: str) -> str | None:
    """ISO3 de um código de área do BIS (XM, a zona do euro, não tem país)."""
    pais = pycountry.countries.get(alpha_2=iso2)
    return str(pais.alpha_3) if pais else None


def _juros(
    desde: date, anos_bis: list[int], so_estes: list[str] | None, zona_do_euro: list[str]
) -> tuple[dict[str, list[float | None]], dict[str, list[float | None]], date]:
    """Juro básico e juro real (ex-post) por ISO3, no fim de cada ano de `anos_bis`.

    `so_estes`: os códigos ISO2 do BIS a pedir; None pede todos os países do BIS (e dá a taxa
    do BCE aos membros da `zona_do_euro` que não têm a própria)."""
    pedir = [] if so_estes is None else so_estes
    juros = bis.juro_basico(pedir, desde)
    cpi = bis.inflacao_12m(
        [] if so_estes is None else sorted({*pedir, "DE", "FR", "IT", "ES"}), desde
    )
    # (ISO3, ISO2 do juro, ISO2 da inflação): a inflação é de cada país (a zona do euro tem
    # a sua); o juro, do banco central comum.
    if so_estes is None:
        ligacoes = []
        for iso2 in juros:
            iso3 = _iso2_do_bis(iso2)
            if iso3:
                ligacoes.append((iso3, iso2, iso2))
        # Países da zona do euro sem taxa própria no BIS usam a do BCE (XM).
        if "XM" in juros:
            tem = {x[0] for x in ligacoes}
            for iso3 in sorted(set(zona_do_euro) - tem):
                membro = pycountry.countries.get(alpha_3=iso3)
                if membro is not None:
                    ligacoes.append((iso3, "XM", membro.alpha_2))
    else:
        espelho = {"DEU": "DE", "FRA": "FR", "ITA": "IT", "ESP": "ES"}
        ligacoes = [(p[0], p[1], espelho.get(p[0], p[1])) for p in PAISES if p[1]]
    v_juro: dict[str, list[float | None]] = {}
    v_real: dict[str, list[float | None]] = {}
    ultimo_mes = date(desde.year, 1, 1)
    for iso3, codigo, codigo_cpi in ligacoes:
        if codigo not in juros:
            continue
        serie_juro = juros[codigo]
        ultimo_mes = max(ultimo_mes, serie_juro[-1][0])
        v_juro[iso3] = _fim_de_ano(serie_juro, anos_bis)
        inflacao = dict(cpi.get(codigo_cpi, []))
        real = [
            (d, ((1 + v / 100) / (1 + inflacao[d] / 100) - 1) * 100)
            for d, v in serie_juro
            if d in inflacao and inflacao[d] > -99
        ]
        if real:
            v_real[iso3] = _fim_de_ano(real, anos_bis)
    return v_juro, v_real, ultimo_mes


def _credito(
    desde: date, anos: list[int], so_estes: list[str] | None
) -> tuple[dict[str, list[float | None]], dict[str, list[float | None]], date]:
    """Serviço da dívida do setor privado e hiato de crédito (BIS, trimestrais) por ISO3, no
    último trimestre de cada ano (no ano corrente, o último publicado)."""
    pedir = [] if so_estes is None else so_estes
    saida: list[dict[str, list[float | None]]] = []
    ultimo = desde
    for ler in (bis.servico_da_divida, bis.hiato_de_credito):
        por_iso3: dict[str, list[float | None]] = {}
        for iso2, pontos in ler(pedir, desde).items():
            iso3 = _iso2_do_bis(iso2)
            if iso3 and pontos:
                por_iso3[iso3] = _fim_de_ano(pontos, anos)
                ultimo = max(ultimo, pontos[-1][0])
        saida.append(por_iso3)
    return saida[0], saida[1], ultimo


def _metricas_de_credito(
    v_dsr: dict[str, list[float | None]],
    v_hiato: dict[str, list[float | None]],
    anos: list[int],
    ultimo: date,
) -> list[MetricaMundo]:
    tri = f"{(ultimo.month - 1) // 3 + 1}º tri/{ultimo.year}"
    return [
        MetricaMundo(
            id="servico_divida",
            nome="Serviço da dívida privada",
            descricao=(
                "Juros e amortizações que famílias e empresas pagam sobre a renda delas, no "
                f"último trimestre de cada ano (em {ultimo.year}, o {tri}). O BIS não separa "
                "as famílias para o Brasil."
            ),
            unidade="% da renda",
            casas=1,
            maior_e_melhor=False,
            fonte="BIS, serviço da dívida do setor privado não financeiro (WS_DSR)",
            anos=anos,
            primeiro_ano_projetado=None,
            valores=v_dsr,
        ),
        MetricaMundo(
            id="hiato_credito",
            nome="Hiato de crédito",
            descricao=(
                "Crédito ao setor privado em % do PIB menos a tendência de longo prazo, no "
                f"último trimestre de cada ano (em {ultimo.year}, o {tri}). Muito acima de "
                "zero, o crédito cresceu rápido demais."
            ),
            unidade="pp do PIB",
            casas=1,
            maior_e_melhor=False,
            fonte="BIS, hiato de crédito sobre o PIB (WS_CREDIT_GAP)",
            anos=anos,
            primeiro_ano_projetado=None,
            valores=v_hiato,
        ),
    ]


# ---- câmbio, inflação em 12 meses e juro de 10 anos: mensais, no fim de cada ano

# Os quatro países do euro da lista principal: o BIS dá a cada um a própria inflação e o câmbio
# do euro (no juro básico, eles usam o XM, o BCE).
EURO_NA_LISTA = ["DE", "FR", "IT", "ES"]


def variacao_no_ano(moedas: dict[str, list[Ponto]], anos: list[int]) -> list[float | None]:
    """Quanto a moeda ganhou (positivo) ou perdeu (negativo) de valor contra o dólar em cada
    ano, em %: o fim do ano (no ano corrente, o último mês) contra o fim do ano anterior, as
    duas pontas na mesma moeda (o ano em que o país trocou de moeda fica em branco).

    `moedas`: {moeda: [(mês, unidades da moeda por dólar)]}. A moeda vale 1/cotação em
    dólares: ganhou valor quando a cotação caiu."""
    saida: list[float | None] = []
    for a in anos:
        valor: float | None = None
        for pontos in moedas.values():
            base = dict(pontos).get(date(a - 1, 12, 1))
            no_ano = [v for d, v in pontos if d.year == a]
            if base and no_ano:
                valor = round((base / no_ano[-1] - 1) * 100, 2)
        saida.append(valor)
    return saida


def _iso3_da_area(iso2: str) -> str | None:
    """ISO3 de uma área do BIS; o XM (zona do euro) vira o grupo do FMI G163."""
    return "G163" if iso2 == "XM" else _iso2_do_bis(iso2)


def _cambio(
    desde: date, anos: list[int], so_estes: list[str] | None
) -> tuple[dict[str, list[float | None]], date]:
    """Variação de cada moeda contra o dólar no ano, por ISO3. Quem usa o dólar fica de fora."""
    pedir = [] if so_estes is None else sorted({*so_estes, *EURO_NA_LISTA})
    dados = bis.cambio_contra_dolar(pedir, date(desde.year - 1, 12, 1))
    saida: dict[str, list[float | None]] = {}
    ultimo = desde
    for iso2, moedas in dados.items():
        iso3 = _iso3_da_area(iso2)
        if iso3 is None or "USD" in moedas:
            continue
        valores = variacao_no_ano(moedas, anos)
        if any(v is not None for v in valores):
            saida[iso3] = valores
            ultimo = max(ultimo, *(p[-1][0] for p in moedas.values()))
    return saida, ultimo


def _inflacao_12m(
    desde: date, anos: list[int], so_estes: list[str] | None
) -> tuple[dict[str, list[float | None]], date]:
    """Inflação ao consumidor em 12 meses, em dezembro de cada ano (no ano corrente, o último
    mês publicado), por ISO3. O mesmo pedido do juro real (`_juros`), que já está guardado."""
    pedir = [] if so_estes is None else sorted({*so_estes, *EURO_NA_LISTA})
    saida: dict[str, list[float | None]] = {}
    ultimo = desde
    for iso2, pontos in bis.inflacao_12m(pedir, desde).items():
        iso3 = _iso3_da_area(iso2)
        if iso3 and pontos:
            saida[iso3] = _fim_de_ano(pontos, anos)
            ultimo = max(ultimo, pontos[-1][0])
    return saida, ultimo


# O título do Tesouro que faz as vezes do de 10 anos no Brasil: o prefixado com juros
# semestrais (a NTN-F, como os títulos de 10 anos dos outros países, que pagam cupom) com
# vencimento mais perto de 10 anos, entre 7 e 13 anos à frente. Antes de 2006 não há nenhum.
PRAZO_10_ANOS = (7.0, 13.0)


def juro_10_anos_brasil(por_data: dict[date, list[Ponto]]) -> list[Ponto]:
    """[(mês, % a.a.)]: a média do mês da taxa (média entre compra e venda) do Tesouro
    Prefixado com Juros Semestrais de vencimento mais perto de 10 anos."""
    por_mes: dict[date, list[float]] = {}
    for d, titulos in por_data.items():
        candidatos = [
            (v, t)
            for v, t in titulos
            if PRAZO_10_ANOS[0] <= (v - d).days / 365.25 <= PRAZO_10_ANOS[1]
        ]
        if not candidatos:
            continue
        _, taxa = min(candidatos, key=lambda x: abs((x[0] - d).days / 365.25 - 10))
        por_mes.setdefault(d.replace(day=1), []).append(taxa)
    return sorted((m, sum(v) / len(v)) for m, v in por_mes.items())


def _juro_10_anos(
    ctx: Contexto, desde: date, anos: list[int]
) -> tuple[dict[str, list[float | None]], date]:
    """Juro de 10 anos em dezembro de cada ano (média do mês; no ano corrente, o último mês),
    por ISO3: a OCDE para todos, menos o Brasil, que vem do Tesouro Direto (a OCDE dá a TJLP)."""
    if "mundo_juro_10a" not in ctx.memo:
        dados = ocde_juros.juro_longo(desde)
        try:
            pre = tesouro_direto.curvas(desde)[tesouro_direto.PREFIXADO_JUROS]
            dados["BRA"] = juro_10_anos_brasil(pre)
        except Exception as erro:
            dados.pop("BRA", None)
            print(f"  aviso: mundo: juro de 10 anos do Brasil indisponível ({str(erro)[:120]})")
        ctx.memo["mundo_juro_10a"] = dados
    brutos: dict[str, list[Ponto]] = ctx.memo["mundo_juro_10a"]
    # O mês mais novo da OCDE (o dos EUA): o Brasil, que o Tesouro Direto tem até ontem, fica
    # no mesmo mês dos outros.
    ultimo = max((p[-1][0] for a, p in brutos.items() if a != "BRA" and p), default=desde)
    saida: dict[str, list[float | None]] = {}
    for area, pontos in brutos.items():
        iso3 = "G163" if area == ocde_juros.ZONA_DO_EURO else area
        if iso3 != "G163" and pycountry.countries.get(alpha_3=iso3) is None:
            continue
        valores = _fim_de_ano([p for p in pontos if anos[0] <= p[0].year and p[0] <= ultimo], anos)
        if any(v is not None for v in valores):
            saida[iso3] = valores
    return saida, ultimo


def _mes_ano(d: date) -> str:
    return f"{MESES[d.month - 1]} de {d.year}"


def _metricas_mensais(
    ctx: Contexto, desde: date, anos: list[int], so_estes: list[str] | None
) -> list[MetricaMundo]:
    """Câmbio no ano, inflação em 12 meses e juro de 10 anos. A que falhar fica de fora."""
    ano = anos[-1]
    saida: list[MetricaMundo] = []
    try:
        valores, ultimo = _inflacao_12m(desde, anos, so_estes)
        saida.append(
            MetricaMundo(
                id="inflacao_12m",
                nome="Inflação em 12 meses",
                descricao=(
                    "Preços ao consumidor nos 12 meses até dezembro de cada ano; em "
                    f"{ano}, até o último mês publicado (o mais novo: {_mes_ano(ultimo)}). "
                    "Sai todo mês; a métrica Inflação, do FMI, é a média do ano."
                ),
                unidade="% em 12 meses",
                casas=1,
                maior_e_melhor=False,
                fonte="BIS, preços ao consumidor (WS_LONG_CPI)",
                anos=anos,
                valores=valores,
            )
        )
    except Exception as erro:
        print(f"  aviso: mundo: inflação em 12 meses indisponível ({str(erro)[:120]})")
    try:
        valores, ultimo = _cambio(desde, anos, so_estes)
        saida.append(
            MetricaMundo(
                id="cambio",
                nome="Moeda contra o dólar",
                descricao=(
                    "Variação da moeda contra o dólar, de fim de ano a fim de ano (em "
                    f"{ano}, até {_mes_ano(ultimo)}); positivo é alta da moeda. Sem os EUA; "
                    "os países do euro têm o número do euro."
                ),
                unidade="% no ano",
                casas=1,
                maior_e_melhor=None,
                fonte="BIS, câmbio contra o dólar no fim do mês (WS_XRU)",
                anos=anos,
                valores=valores,
            )
        )
    except Exception as erro:
        print(f"  aviso: mundo: câmbio do BIS indisponível ({str(erro)[:120]})")
    try:
        valores, ultimo = _juro_10_anos(ctx, desde, anos)
        saida.append(
            MetricaMundo(
                id="juro_10a",
                nome="Juro de 10 anos",
                descricao=(
                    # Brasil fora da OCDE: ela traz a TJLP, que não é título de 10 anos.
                    "Título do governo de 10 anos, média de dezembro (em "
                    f"{ano}, de {_mes_ano(ultimo)}). Brasil: o Prefixado com Juros Semestrais "
                    "mais perto de 10 anos; fora da OCDE, só alguns países."
                ),
                unidade="% a.a.",
                casas=2,
                maior_e_melhor=None,
                fonte=f"{ocde_juros.FONTE}; Brasil: Tesouro Nacional, Tesouro Direto",
                anos=anos,
                valores=valores,
            )
        )
    except Exception as erro:
        print(f"  aviso: mundo: juro de 10 anos indisponível ({str(erro)[:120]})")
    return saida


PWT_DESDE = 1970
"""Os países principais desde 1970 (passa pelo auge da PTF do Brasil, nos anos 1970)."""

PorAnoPWT = dict[str, float]


def _por_hora(x: PorAnoPWT) -> float | None:
    if x.get("rgdpo") and x.get("emp") and x.get("avh"):
        return x["rgdpo"] / (x["emp"] * x["avh"])
    return None


def _capital_por_ocupado(x: PorAnoPWT) -> float | None:
    if x.get("cn") and x.get("emp"):
        return x["cn"] / x["emp"] / 1000
    return None


# (id, nome, descrição, unidade, casas, maior é melhor, conta sobre o ano da PWT)
METRICAS_PWT: list[
    tuple[str, str, str, str, int, bool | None, Callable[[PorAnoPWT], float | None]]
] = [
    (
        "ptf",
        "PTF contra a dos EUA",
        "Produtividade total dos fatores: o que se produz além do que explicam capital, horas "
        "e estudo, em % da dos EUA no mesmo ano (paridade do poder de compra).",
        "% da dos EUA",
        0,
        True,
        lambda x: x["ctfp"] * 100 if "ctfp" in x else None,
    ),
    (
        "produtividade_hora",
        "Produto por hora trabalhada",
        "O PIB (pela produção, em dólares de paridade do poder de compra de 2021) dividido "
        "pelas horas que todos os ocupados trabalharam no ano.",
        "US$ PPC por hora",
        1,
        True,
        _por_hora,
    ),
    (
        "capital_ocupado",
        "Capital por pessoa ocupada",
        "Máquinas, prédios e infraestrutura do país (o estoque de capital, a paridade do poder "
        "de compra do ano) divididos pelas pessoas ocupadas, em mil dólares.",
        "mil US$ PPC por ocupado",
        0,
        True,
        _capital_por_ocupado,
    ),
    (
        "capital_humano",
        "Capital humano",
        "Índice da Penn World Table feito dos anos médios de estudo e do quanto cada ano a mais "
        "costuma render: 1 é ninguém com estudo; os países mais escolarizados passam de 3,5.",
        "índice",
        2,
        True,
        lambda x: x.get("hc"),
    ),
    (
        "horas_ano",
        "Horas trabalhadas no ano",
        "Média de horas trabalhadas no ano por pessoa ocupada. Mais horas para o mesmo produto "
        "quer dizer menos produto por hora.",
        "horas por ocupado",
        0,
        None,
        lambda x: x.get("avh"),
    ),
    (
        "parte_trabalho",
        "Parte do trabalho na renda",
        "A parte da renda que fica com quem trabalha, com a dos autônomos estimada pela PWT; "
        "onde falta dado, a própria PWT completa (o Brasil de 2021 se repete até 2023).",
        "% da renda",
        1,
        None,
        lambda x: x["labsh"] * 100 if "labsh" in x else None,
    ),
    # As duas abaixo vão com a definição da própria PWT (Caio, 15/11/2026: "mostramos de onde
    # vem e a definição da fonte, de resto é com a PWT pra se explicar").
    (
        "retorno_capital",
        "Retorno do capital",
        'Na definição da Penn World Table, "Real internal rate of return": a taxa interna de '
        "retorno real do estoque de capital. Ficam de fora os anos que a própria PWT marca "
        'como "Outlier".',
        "% ao ano",
        1,
        None,
        lambda x: x["irr"] * 100 if "irr" in x else None,
    ),
    (
        "preco_investimento",
        "Nível de preço do investimento",
        'Na definição da Penn World Table, "Price level of capital formation, price level of '
        'USA GDPo in 2021=1": o nível de preço da formação de capital, com o nível de preço '
        "do PIB dos EUA em 2021 igual a 1.",
        "(EUA 2021 = 1)",
        2,
        None,
        lambda x: x.get("pl_i"),
    ),
]


def metricas_pwt(dados: pwt.PorPais, paises: list[str], anos: list[int]) -> list[MetricaMundo]:
    """As métricas da PWT dos `paises` nos `anos`; os últimos anos sem dado saem da lista
    (a PWT vai até 2023). País sem nenhum valor fica de fora da métrica."""
    saida: list[MetricaMundo] = []
    for id, nome, descricao, unidade, casas, melhor, conta in METRICAS_PWT:
        valores: dict[str, list[float | None]] = {}
        for iso in paises:
            por_ano = dados.get(iso, {})
            linha: list[float | None] = []
            for a in anos:
                v = conta(por_ano[a]) if a in por_ano else None
                linha.append(None if v is None else round(v, casas + 2))
            if any(v is not None for v in linha):
                valores[iso] = linha
        if not valores:
            continue
        anos_m, valores = sem_anos_vazios(anos, valores)
        saida.append(
            MetricaMundo(
                id=id,
                nome=nome,
                descricao=f"{descricao} A Penn World Table vai até {anos_m[-1]}.",
                unidade=unidade,
                casas=casas,
                maior_e_melhor=melhor,
                fonte=pwt.FONTE,
                anos=anos_m,
                valores=valores,
            )
        )
    return saida


def _carga_tributaria(ctx: Contexto, inicio: int) -> dict[str, dict[int, float]]:
    """{ISO3: {ano: carga tributária em % do PIB}} de todos os países da OCDE Global Revenue
    Statistics, uma chamada por rodada."""
    if "ocde_carga" not in ctx.memo:
        tabela = ocde_receita.carga(None, ["S13"], ["_T"], inicio=inicio)
        ctx.memo["ocde_carga"] = {p: v for (p, _, _), v in tabela.items() if len(p) == 3}
    return ctx.memo["ocde_carga"]  # type: ignore[no-any-return]


def _metrica_da_carga(
    carga: dict[str, dict[int, float]], paises: list[str], anos: list[int]
) -> MetricaMundo:
    ultimo = max(a for por_ano in carga.values() for a in por_ano)
    return MetricaMundo(
        id="carga",
        nome="Carga tributária",
        descricao=(
            "Impostos e contribuições de todo o governo, no método da OCDE, igual para todos. "
            f"O último ano é {ultimo} ({ultimo - 1} para parte dos países)."
        ),
        unidade="% do PIB",
        casas=1,
        maior_e_melhor=None,
        fonte=ocde_receita.FONTE,
        anos=anos,
        primeiro_ano_projetado=None,
        valores={
            iso: [round(carga[iso][a], 2) if a in carga[iso] else None for a in anos]
            for iso in paises
            if iso in carga and any(a in carga[iso] for a in anos)
        },
    )


def reservas_em_meses(
    reservas: dict[str, dict[int, float]], importacoes: dict[str, dict[int, float]], anos: list[int]
) -> dict[str, list[float | None]]:
    """{ISO3: um valor por ano}: as reservas no fim do ano sobre a importação média de um mês
    do ano (bens e serviços), em meses."""
    saida: dict[str, list[float | None]] = {}
    for iso, por_ano in reservas.items():
        compras = importacoes.get(iso, {})
        valores: list[float | None] = [
            round(por_ano[a] / (compras[a] / 12), 2) if a in por_ano and compras.get(a) else None
            for a in anos
        ]
        if any(v is not None for v in valores):
            saida[iso] = valores
    return saida


def sem_anos_vazios(
    anos: list[int], valores: dict[str, list[float | None]]
) -> tuple[list[int], dict[str, list[float | None]]]:
    """Corta os últimos anos com menos da metade dos países do ano mais cheio: a tela compara
    no último ano, e o ano que o FMI ainda não fechou viria vazio."""
    contagem = [sum(1 for v in valores.values() if v[i] is not None) for i in range(len(anos))]
    fim = len(anos)
    while fim and contagem[fim - 1] < max(contagem, default=0) / 2:
        fim -= 1
    return anos[:fim], {
        iso: v[:fim] for iso, v in valores.items() if any(x is not None for x in v[:fim])
    }


def volatilidade_do_cambio(
    cambio: dict[str, list[Ponto]], janela: int = 21, folga_dias: int = 10
) -> tuple[dict[str, float], date]:
    """{ISO3: volatilidade da moeda contra o dólar nos últimos `janela` dias úteis, % a.a.} e
    a data mais recente. Fica de fora quem está parado há mais de `folga_dias` (a Argentina
    no BIS), quem não tem país (a zona do euro, XM) e os EUA (o dólar contra ele mesmo)."""
    ultimo = max(p[-1][0] for p in cambio.values() if p)
    saida: dict[str, float] = {}
    for iso2, pontos in cambio.items():
        iso3 = _iso2_do_bis(iso2)
        if iso3 in (None, "USA") or not pontos or (ultimo - pontos[-1][0]).days > folga_dias:
            continue
        vol = risco.volatilidade(pontos, janela)
        if vol:
            saida[str(iso3)] = round(vol[-1][1], 2)
    return saida, ultimo


def _metricas_de_risco(ctx: Contexto, ano: int, manter: set[str]) -> list[MetricaMundo]:
    """Só no arquivo de todos os países, para o painel de alerta contra outros países:
    reservas em meses de importação (Banco Mundial) e volatilidade do câmbio (BIS). Cada uma
    que falha fica de fora."""
    saida: list[MetricaMundo] = []
    anos = list(range(ano - 6, ano + 1))
    try:
        # O Banco Mundial publica o número pronto; sem ele, a mesma conta com os dados do FMI.
        try:
            linhas = banco_mundial.indicador(banco_mundial.RESERVAS_MESES, anos[0], anos[-1])
            anos_r, meses = sem_anos_vazios(anos, banco_mundial.por_ano(linhas, anos))
            fonte_reservas = f"{banco_mundial.FONTE} (FI.RES.TOTL.MO)"
        except Exception as erro:
            print(f"  aviso: mundo: reservas do Banco Mundial indisponíveis ({str(erro)[:120]})")
            anos_r, meses = sem_anos_vazios(
                anos,
                reservas_em_meses(
                    fmi.estatistica(fmi.RESERVAS, anos[0]),
                    fmi.estatistica(fmi.IMPORTACOES, anos[0]),
                    anos,
                ),
            )
            fonte_reservas = (
                "FMI, International Liquidity (reservas) e Balance of Payments "
                "(importação de bens e serviços); cálculo próprio"
            )
        saida.append(
            MetricaMundo(
                id="reservas_meses",
                nome="Reservas em meses de importação",
                descricao=(
                    "Reservas internacionais no fim do ano (com o ouro a preço de mercado) "
                    "sobre a importação média de um mês de bens e serviços no ano."
                ),
                unidade="meses",
                casas=1,
                maior_e_melhor=True,
                fonte=fonte_reservas,
                anos=anos_r,
                valores={iso: v for iso, v in sorted(meses.items()) if iso in manter},
            )
        )
    except Exception as erro:
        print(f"  aviso: mundo: reservas do FMI indisponíveis ({str(erro)[:120]})")
    try:
        vol, quando = volatilidade_do_cambio(bis.cambio_diario(ctx.hoje - timedelta(days=60)))
        saida.append(
            MetricaMundo(
                id="vol_cambio",
                nome="Volatilidade da moeda contra o dólar",
                descricao=(
                    "Desvio-padrão das variações diárias da moeda contra o dólar nos últimos "
                    f"21 dias úteis até {quando.strftime('%d/%m/%Y')}, levado ao ano. Os "
                    "países do euro têm todos o euro."
                ),
                unidade="% a.a.",
                casas=1,
                maior_e_melhor=False,
                fonte="BIS, câmbio diário contra o dólar (WS_XRU); cálculo próprio",
                anos=[ano],
                valores={iso: [v] for iso, v in sorted(vol.items()) if iso in manter},
            )
        )
    except Exception as erro:
        print(f"  aviso: mundo: câmbio diário do BIS indisponível ({str(erro)[:120]})")
    return saida


def _todos_os_paises(
    ctx: Contexto,
    ano: int,
    paises: list[str],
    zona_do_euro: list[str],
    metricas: list[MetricaMundo],
) -> MundoPaises:
    """As mesmas métricas de `metricas`, para todos os `paises`, de ano-6 a ano+5 (o arquivo
    que a tela lê só quando a pessoa abre um grupo; por isso a janela curta)."""
    a0, a1 = ano - 6, ano + 5
    anos_weo = list(range(a0, a1 + 1))
    anos_bis = list(range(a0, ano + 1))
    indicador = {m[0]: m[1] for m in WEO}
    # A chave de país vazia traz todos os países numa chamada só.
    weo = fmi.weo([], [m[1] for m in WEO], a0, a1)
    v_juro, v_real, ultimo_mes = _juros(date(a0, 1, 1), anos_bis, None, zona_do_euro)
    credito: dict[str, dict[str, list[float | None]]] = {}
    with contextlib.suppress(Exception):  # sem o BIS trimestral, essas duas ficam de fora
        v_dsr, v_hiato, _ = _credito(date(a0, 1, 1), anos_bis, None)
        credito = {"servico_divida": v_dsr, "hiato_credito": v_hiato}
    quando = f"{MESES[ultimo_mes.month - 1]} de {ultimo_mes.year}"
    manter = set(paises)
    mensais = {x.id: x for x in _metricas_mensais(ctx, date(a0, 1, 1), anos_bis, None)}
    saida: list[MetricaMundo] = []
    ids_pwt = {x[0] for x in METRICAS_PWT}
    for m in metricas:
        if m.id in ids_pwt:
            continue
        if m.id in mensais:
            todos = mensais[m.id].valores
            valores = {iso: todos[iso] for iso in sorted(manter) if iso in todos}
            saida.append(m.model_copy(update={"anos": anos_bis, "valores": valores}))
            continue
        if m.id in indicador:
            valores = {
                iso: [round(mapa[a], m.casas + 1) if a in mapa else None for a in anos_weo]
                for iso in sorted(manter)
                if (mapa := weo.valores.get((iso, indicador[m.id])))
            }
            anos = anos_weo
        elif m.id == "carga":
            copia = _metrica_da_carga(ctx.memo["ocde_carga"], sorted(manter), anos_bis)
            saida.append(copia)
            continue
        else:
            if m.id in ("servico_divida", "hiato_credito"):
                if m.id not in credito:
                    continue
                bruto = credito[m.id]
            else:
                bruto = v_juro if m.id == "juro" else v_real
            valores = {iso: bruto[iso] for iso in sorted(manter) if iso in bruto}
            anos = anos_bis
        descricao = m.descricao
        if m.id == "juro":
            descricao = (
                f"Taxa básica do banco central no fim de cada ano; em {ano}, o último mês "
                f"disponível ({quando}). Os países da zona do euro sem taxa própria têm a do "
                "Banco Central Europeu."
            )
        saida.append(
            m.model_copy(update={"anos": anos, "valores": valores, "descricao": descricao})
        )
    saida += _metricas_de_risco(ctx, ano, manter)
    if any(m.id in ids_pwt for m in metricas):
        with contextlib.suppress(Exception):  # já veio na rodada: só falha se a rede caiu agora
            # Os dez anos que a lista de anos da tela oferece, não só os seis do resto.
            saida += metricas_pwt(pwt.dados(), sorted(manter), list(range(ano - 10, ano + 1)))
    return MundoPaises(metricas=saida, gerado_em=ctx.agora())


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
    desde = date(inicio, 1, 1)
    anos_bis = list(range(inicio, ano + 1))
    v_juro, v_real, ultimo_mes = _juros(desde, anos_bis, sorted({p[1] for p in PAISES if p[1]}), [])
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

    # Crédito privado (BIS, trimestral): serviço da dívida e hiato. Sem eles, segue o resto.
    try:
        v_dsr, v_hiato, ultimo_tri = _credito(
            desde, anos_bis, sorted({p[1] for p in PAISES if p[1]})
        )
        metricas += _metricas_de_credito(v_dsr, v_hiato, anos_bis, ultimo_tri)
    except Exception as erro:
        print(f"  aviso: mundo: crédito do BIS indisponível ({str(erro)[:120]})")

    # Inflação em 12 meses, câmbio no ano e juro de 10 anos (mensais), só dos países da lista.
    for m in _metricas_mensais(ctx, desde, anos_bis, sorted({p[1] for p in PAISES if p[1]})):
        m.valores = {iso: v for iso, v in m.valores.items() if iso in isos}
        metricas.append(m)

    # Carga tributária (OCDE). Sem ela, segue o resto.
    try:
        metricas.append(_metrica_da_carga(_carga_tributaria(ctx, inicio), isos, anos_bis))
    except Exception as erro:
        print(f"  aviso: mundo: carga tributária da OCDE indisponível ({str(erro)[:120]})")

    # Produtividade (Penn World Table). Sem ela, segue o resto.
    try:
        metricas += metricas_pwt(pwt.dados(set(isos)), isos, list(range(PWT_DESDE, ano + 1)))
    except Exception as erro:
        print(f"  aviso: mundo: Penn World Table indisponível ({str(erro)[:120]})")

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
        f"países, com as projeções do FMI até {fim}."
    )
    mundo_obj = Mundo(
        titulo="Brasil no mundo",
        resumo=resumo,
        paises=[Pais(iso3=p[0], nome=p[2], grupo=p[3]) for p in PAISES],  # type: ignore[arg-type]
        metricas=metricas,
        ano_corrente=ano,
        edicao=edicao,
        gerado_em=ctx.agora(),
    )

    # Abrir por país: grupos, nomes e o arquivo com todos os países. Se falhar, o mundo.json
    # sai igual, sem `arquivo_paises`.
    ctx.memo.pop("mundo_paises", None)
    try:
        membros = fmi.grupos()
        todos = membros["G001"]
        nomes_fixos = {p[0]: p[2] for p in PAISES if p[3] != "agregado"}
        nomes = {iso: nomes_fixos.get(iso) or nome_do_pais(iso) for iso in sorted(todos)}
        ctx.memo["mundo_paises"] = _todos_os_paises(ctx, ano, todos, membros["G163"], metricas)
        mundo_obj.grupos = [GrupoMundo(iso3=g, nome=n, membros=membros[g]) for g, n in GRUPOS]
        mundo_obj.nomes = nomes
        mundo_obj.arquivo_paises = ARQUIVO_PAISES
    except Exception as erro:
        print(f"  AVISO mundo: sem o arquivo de todos os países ({str(erro)[:120]})")
    return mundo_obj
