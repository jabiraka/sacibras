"""Brasil no mundo: as mesmas métricas para ~20 países, com as projeções do FMI.

Anuais e projeções: World Economic Outlook (FMI). Juro básico e inflação em 12 meses, para o
juro real: BIS. Cada métrica guarda a fonte; projeção é sempre a da própria fonte.
"""

from __future__ import annotations

import contextlib
import gettext
from datetime import date

import pycountry

from sacibras.fontes import bis, fmi, ocde_receita
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
        "Receitas menos despesas do governo geral, sem os juros. Negativo é déficit. Para o "
        "Brasil, não é o mesmo número de Contas públicas: o FMI mede só União, estados e "
        "municípios, por receitas e despesas; o Banco Central soma as estatais e o próprio "
        "BC, pela variação da dívida. A tabela lado a lado está em Contas públicas › Primário "
        "e juros.",
        "% do PIB",
        1,
        True,
    ),
    (
        "nominal",
        "GGXCNL_NGDP",
        "Resultado nominal",
        "Receitas menos despesas do governo geral, com os juros. Negativo é déficit. Para o "
        "Brasil, difere do resultado nominal do Banco Central (Contas públicas) pela mesma "
        "razão do primário: outro conjunto de governo e outra forma de medir.",
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
            "Impostos e contribuições sociais de todo o governo (no Brasil: União, estados, "
            "municípios e INSS), no método da OCDE, igual para todos os países. Sai com atraso: "
            f"o último ano é {ultimo}, e para parte dos países, {ultimo - 1}. Os detalhes estão "
            "em Impostos."
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
    saida: list[MetricaMundo] = []
    for m in metricas:
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

    # Carga tributária (OCDE). Sem ela, segue o resto.
    try:
        metricas.append(_metrica_da_carga(_carga_tributaria(ctx, inicio), isos, anos_bis))
    except Exception as erro:
        print(f"  aviso: mundo: carga tributária da OCDE indisponível ({str(erro)[:120]})")

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
