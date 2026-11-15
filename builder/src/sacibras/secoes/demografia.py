"""Demografia: quantos somos, como envelhecemos e o que isso pede da previdência.

A projeção é a oficial do IBGE (revisão 2024). Até 2022 é dado ajustado aos Censos; dali em
diante, hipótese: nos gráficos a linha segue tracejada. O IBGE não publica faixa de erro; a
ONU publica (World Population Prospects 2024, projeção probabilística), e vai ao lado.
O envelhecimento contra outros países vem do Banco Mundial (% de 65 anos ou mais). A
produtividade e a eficiência (PTF) moram em Atividade (`produtividade.py`; Caio, 15/11/2026).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import date

from sacibras import contas
from sacibras.fontes import (
    banco_mundial,
    ibge_projecao,
    onu_wpp,
    siconfi,
    tesouro_rtn,
)
from sacibras.fontes.ibge_projecao import FONTE as PROJECAO
from sacibras.fontes.ibge_projecao import ULTIMO_ANO_AJUSTADO, PorAno
from sacibras.schema import (
    Cartao,
    Grafico,
    Intervalo,
    LinhaRef,
    LinhaTabela,
    Piramide,
    Secao,
    Serie,
    Tabela,
)
from sacibras.secoes.base import Contexto, br, cartao, grafico, serie
from sacibras.secoes.estados import UFS
from sacibras.tipos import Ponto

PAISES_IDOSOS = {
    "BRA": "Brasil",
    "WLD": "Mundo",
    "LCN": "América Latina e Caribe",
    "HIC": "Países de renda alta",
    "CHN": "China",
    "JPN": "Japão",
}
"""As seis séries do envelhecimento contra o mundo (seis cores de série)."""
ANOS_DAS_BARRAS_ONU = list(range(2030, 2101, 10))

PROJETADO_DESDE = date(ULTIMO_ANO_AJUSTADO + 1, 1, 1)
ANOS_DA_PIRAMIDE = [2000, 2010, 2022, 2030, 2040, 2050, 2060, 2070]
REPOSICAO = 2.1
"""Filhos por mulher que repõem a população (convenção demográfica, com mortalidade baixa)."""
ANOS_DA_TABELA = [2000, 2050, 2070]  # mais o corrente, na segunda coluna

NOTA_PROJECAO = (
    "Projeção oficial do IBGE (revisão 2024): até 2022, dado ajustado aos Censos; daí em "
    "diante (tracejado), hipóteses de fecundidade, mortalidade e migração. O IBGE não publica "
    "faixa de erro."
)


# ------------------------------------------------------------------ contas


def soma_do_ano(mensal: list[Ponto]) -> dict[int, float]:
    """{ano: soma dos 12 meses}, só nos anos com os 12 meses."""
    por_ano: dict[int, list[float]] = {}
    for d, v in mensal:
        por_ano.setdefault(d.year, []).append(v)
    return {a: sum(vs) for a, vs in por_ano.items() if len(vs) == 12}


def pib_do_ano(pib_12m: list[Ponto]) -> dict[int, float]:
    """{ano: PIB do ano, R$ milhões}: o acumulado em 12 meses de dezembro."""
    return {d.year: v for d, v in pib_12m if d.month == 12}


def previdencia_em_pct_do_pib(
    anos: list[siconfi.PrevidenciaUniao], inss_deficit: dict[int, float], pib: dict[int, float]
) -> dict[str, list[Ponto]]:
    """O déficit (positivo) de cada regime em % do PIB do ano: o INSS (R$ milhões, do RTN) e
    os servidores civis e os militares da União (R$, do RREO)."""
    saida: dict[str, list[Ponto]] = {"inss": [], "civis": [], "militares": []}
    for p in anos:
        if p.ano not in pib:
            continue
        base = pib[p.ano] * 1e6
        d = date(p.ano, 1, 1)
        saida["civis"].append((d, -p.civis_resultado / base * 100))
        saida["militares"].append((d, -p.militares_resultado / base * 100))
        if p.ano in inss_deficit:
            saida["inss"].append((d, inss_deficit[p.ano] / pib[p.ano] * 100))
    return saida


def pontos(por_ano: PorAno, escala: float = 1.0, ate: int | None = None) -> list[Ponto]:
    return [
        (date(a, 1, 1), v * escala) for a, v in sorted(por_ano.items()) if ate is None or a <= ate
    ]


def pico(por_ano: PorAno) -> tuple[int, float]:
    """O ano do maior valor e o valor."""
    ano = max(por_ano, key=lambda a: por_ano[a])
    return ano, por_ano[ano]


def primeiro_ano(por_ano: PorAno, condicao: Callable[[int], bool]) -> int | None:
    return next((a for a in sorted(por_ano) if condicao(a)), None)


def crescimento(por_ano: PorAno) -> PorAno:
    """Variação % de um ano contra o anterior."""
    return {a: (v / por_ano[a - 1] - 1) * 100 for a, v in por_ano.items() if por_ano.get(a - 1)}


def barras_onu(projecao: onu_wpp.Projecao, anos: list[int]) -> list[tuple[date, float, float]]:
    """A faixa de 80 % da ONU nos anos pedidos, em milhões."""
    return [
        (
            date(a, 1, 1),
            round(projecao.inferior80[a] / 1e3, 1),
            round(projecao.superior80[a] / 1e3, 1),
        )
        for a in anos
        if a in projecao.inferior80 and a in projecao.superior80
    ]


def filhos(taxa: float) -> str:
    """'1,51 filho' (abaixo de 2, singular, como se escreve em português), '2,32 filhos'."""
    return f"{br(taxa, 2)} filho" + ("s" if taxa >= 2 else "")


def rotulo_do_grupo(grupo: str) -> str:
    """'00-04' → '0 a 4'; '90+' → '90 ou mais'."""
    if grupo.endswith("+"):
        return f"{int(grupo[:-1])} ou mais"
    inicio, fim = grupo.split("-")
    return f"{int(inicio)} a {int(fim)}"


def montar_piramide(quinquenal: dict[str, dict[str, PorAno]], ano_corrente: int) -> Piramide:
    homens, mulheres = quinquenal["Homens"], quinquenal["Mulheres"]
    grupos = list(homens)
    existentes = set.intersection(*(set(v) for v in (*homens.values(), *mulheres.values())))
    anos = sorted({*ANOS_DA_PIRAMIDE, ano_corrente} & existentes)

    def tabela(lado: dict[str, PorAno]) -> list[list[float]]:
        return [[round(lado[g][a] / 1000, 1) for g in grupos] for a in anos]

    return Piramide(
        grupos=[rotulo_do_grupo(g) for g in grupos],
        anos=anos,
        homens=tabela(homens),
        mulheres=tabela(mulheres),
        ano_inicial=ano_corrente if ano_corrente in anos else anos[-1],
        ano_contorno=anos[0],
        primeiro_ano_projetado=ULTIMO_ANO_AJUSTADO + 1,
    )


# ------------------------------------------------------------------ seção


def montar(ctx: Contexto) -> Secao:
    agora = ctx.hoje.year
    ind = ibge_projecao.indicadores()["BR"]
    grupos = ibge_projecao.grupos()
    br_grupos = grupos["BR"]
    quinquenal = ibge_projecao.quinquenal()

    populacao = br_grupos["POP_T"]
    pia = br_grupos["15-64_T"]  # população em idade de trabalhar, no recorte do IBGE
    pct_65 = {a: v * 100 for a, v in br_grupos["P_65+_T"].items()}
    pct_80 = {a: v * 100 for a, v in br_grupos["P_80+_T"].items()}
    dep_idosos, dep_jovens, dep_total = ind["RDI65"], ind["RDJ65"], ind["RDT65"]
    fecundidade, mediana = ind["TFT"], ind["ID_MED"]
    nascimentos, obitos = ind["NASC_T"], ind["OBT_T"]

    ano_pico_pop, _ = pico(populacao)
    ano_pico_pia, _ = pico(pia)
    obitos_passam = primeiro_ano(obitos, lambda a: obitos[a] > nascimentos.get(a, math.inf))
    abaixo_da_reposicao = primeiro_ano(fecundidade, lambda a: fecundidade[a] < REPOSICAO)
    idosos_passam = primeiro_ano(dep_idosos, lambda a: dep_idosos[a] > dep_jovens.get(a, math.inf))
    por_idoso_hoje = 100 / dep_idosos[agora]
    fonte_tab3 = f"{PROJECAO} (tabela 3, grupos etários)"
    fonte_tab4 = f"{PROJECAO} (tabela 4, indicadores)"

    def proj(id: str, nome: str, por_ano: PorAno, casas: int = 1, escala: float = 1.0) -> Serie:
        return serie(
            id, nome, pontos(por_ano, escala), casas=casas, tracejado_desde=PROJETADO_DESDE
        )

    def cartao_proj(
        id: str,
        rotulo: str,
        por_ano: PorAno,
        *,
        unidade: str,
        detalhe: str,
        fonte: str,
        casas: int = 1,
        escala: float = 1.0,
    ) -> Cartao:
        return cartao(
            id,
            rotulo,
            pontos(por_ano, escala, ate=agora),
            unidade=unidade,
            periodicidade="A",
            casas=casas,
            detalhe=detalhe,
            fonte=fonte,
            secao="demografia",
            mini=agora - 2000 + 1,
        )

    reposicao_txt = (
        f"abaixo dela desde {abaixo_da_reposicao}"
        if abaixo_da_reposicao and abaixo_da_reposicao > min(fecundidade)
        else f"abaixo dela desde antes de {min(fecundidade) + 1}"
    )
    cartoes = [
        cartao_proj(
            "populacao",
            "População",
            populacao,
            unidade="milhões",
            escala=1e-6,
            detalhe=f"projeção do IBGE; para de crescer em {ano_pico_pop}",
            fonte=fonte_tab3,
        ),
        cartao_proj(
            "fecundidade",
            "Taxa de fecundidade",
            fecundidade,
            unidade="por mulher",
            casas=2,
            detalhe=f"filhos por mulher; reposição: 2,1 ({reposicao_txt})",
            fonte=fonte_tab4,
        ),
        cartao_proj(
            "idosos-por-100",
            "Idosos (65+) para cada 100 pessoas de 15 a 64 anos",
            dep_idosos,
            unidade="por 100",
            detalhe=(
                f"{br(por_idoso_hoje)} em idade de trabalhar por idoso; "
                f"2070: {br(100 / dep_idosos[2070])}"
            ),
            fonte=fonte_tab4,
        ),
    ]

    # --- Previdência: o Regime Geral (INSS) no RTN, em % do PIB de 12 meses ---
    graficos_inss: list[Grafico] = []
    cartao_inss: Cartao | None = None
    try:
        rtn = tesouro_rtn.serie_historica()
        pib_12m = ctx.sgs("PIB_12M", 30)
        beneficios = contas.em_pct_do_pib(rtn["rgps"], pib_12m)
        arrecadacao = contas.em_pct_do_pib(rtn["arrecadacao_rgps"], pib_12m)
        deficit = contas.subtrair(beneficios, arrecadacao)
        fonte_rtn = (
            "Tesouro Nacional, Resultado do Tesouro Nacional (tabela 1.1: benefícios "
            f"previdenciários e arrecadação líquida para o RGPS); PIB: {ctx.fonte_sgs('PIB_12M')}"
        )
        cartao_inss = cartao(
            "deficit-inss",
            "Déficit do INSS em 12 meses",
            deficit,
            unidade="% do PIB",
            periodicidade="M",
            casas=1,
            detalhe=(
                f"benefícios {br(beneficios[-1][1])} % do PIB; "
                f"arrecadação {br(arrecadacao[-1][1])} %"
            ),
            fonte=fonte_rtn,
            procedencia="calculado",
            secao="demografia",
            mini=120,
        )
        graficos_inss.append(
            grafico(
                "inss",
                "INSS: benefícios, arrecadação e o déficit",
                [
                    serie("beneficios", "Benefícios", beneficios),
                    serie("arrecadacao", "Arrecadação líquida", arrecadacao),
                    serie("deficit", "Déficit", deficit),
                ],
                unidade="% do PIB, em 12 meses",
                casas=1,
                periodicidade="M",
                janela_anos=20,
                fonte=fonte_rtn,
                nota=(
                    "Regime Geral de Previdência Social, o do INSS (não inclui servidores nem "
                    "militares). Déficit = benefícios pagos menos a arrecadação líquida para o "
                    "RGPS, os dois somados em 12 meses e divididos pelo PIB dos mesmos 12 meses."
                ),
            )
        )
    except Exception as erro:
        print(f"    RTN ficou de fora da demografia: {str(erro)[:120]}")
    if cartao_inss:
        cartoes.append(cartao_inss)
    tabelas_prev: list[Tabela] = []
    try:
        c_prev, g_prev, t_prev = _previdencia_uniao(ctx)
        cartoes.append(c_prev)
        graficos_inss.append(g_prev)
        tabelas_prev.append(t_prev)
    except Exception as erro:
        print(f"    a previdência da União ficou de fora: {str(erro)[:120]}")

    cartoes += [
        cartao_proj(
            "esperanca-de-vida",
            "Esperança de vida ao nascer",
            ind["e0_T"],
            unidade="anos",
            detalhe=f"homens {br(ind['e0_H'][agora])}; mulheres {br(ind['e0_M'][agora])}",
            fonte=fonte_tab4,
        ),
        cartao_proj(
            "mortalidade-infantil",
            "Mortalidade infantil",
            ind["TMI_T"],
            unidade="por mil nascidos",
            detalhe=f"era {br(ind['TMI_T'][2000])} em 2000",
            fonte=fonte_tab4,
        ),
        cartao_proj(
            "idade-mediana",
            "Idade mediana",
            mediana,
            unidade="anos",
            detalhe=f"era {br(mediana[2000])} em 2000; será {br(mediana[2070])} em 2070",
            fonte=fonte_tab4,
        ),
        cartao_proj(
            "populacao-15-64",
            "Pessoas de 15 a 64 anos",
            pia,
            unidade="milhões",
            escala=1e-6,
            detalhe=f"a idade de trabalhar; para de crescer em {ano_pico_pia}",
            fonte=fonte_tab3,
        ),
    ]
    # --- Gráficos ---
    cresc_pia = crescimento(pia)
    piramide = montar_piramide(quinquenal, agora)
    graficos = [
        grafico(
            "dependencia",
            "Jovens e idosos para cada 100 pessoas de 15 a 64 anos",
            [
                proj("idosos", "Idosos (65 ou mais)", dep_idosos),
                proj("jovens", "Jovens (0 a 14)", dep_jovens),
                proj("total", "Total de dependentes", dep_total),
            ],
            unidade="por 100 pessoas de 15 a 64",
            casas=1,
            periodicidade="A",
            fonte=f"{fonte_tab4}: razões de dependência RDI65, RDJ65 e RDT65",
            nota=(
                f"Os idosos passam os jovens em {idosos_passam}. "
                "Quem está em idade de trabalhar sustenta, pela renda e pelos impostos e "
                f"contribuições, quem não está. {NOTA_PROJECAO}"
            ),
            largura="inteira",
        ),
        grafico(
            "piramide",
            "Pirâmide etária",
            [],
            unidade="% da população",
            casas=1,
            periodicidade="A",
            fonte=f"{PROJECAO} (tabela 2, grupos de cinco anos)",
            nota=(
                f"Homens à esquerda, mulheres à direita, em % da população do ano. O contorno é "
                f"{piramide.ano_contorno}. Até {ULTIMO_ANO_AJUSTADO}, dado ajustado aos Censos; "
                "depois, projeção do IBGE."
            ),
            largura="inteira",
            piramide=piramide,
        ),
        grafico(
            "populacao",
            "População total e de 15 a 64 anos",
            [
                proj("total", "População", populacao, escala=1e-6),
                proj("15-64", "15 a 64 anos", pia, escala=1e-6),
            ],
            unidade="milhões de pessoas",
            casas=1,
            periodicidade="A",
            fonte=fonte_tab3,
            nota=NOTA_PROJECAO,
        ),
        grafico(
            "nascimentos-obitos",
            "Nascimentos e óbitos por ano",
            [
                proj("nascimentos", "Nascimentos", nascimentos, casas=0, escala=1e-3),
                proj("obitos", "Óbitos", obitos, casas=0, escala=1e-3),
            ],
            unidade="mil",
            casas=0,
            periodicidade="A",
            fonte=fonte_tab4,
            nota=(
                (
                    f"Os óbitos passam os nascimentos em {obitos_passam}: daí em diante a "
                    "população só cresce com migração. "
                    if obitos_passam
                    else ""
                )
                + NOTA_PROJECAO
            ),
        ),
        grafico(
            "fecundidade",
            "Filhos por mulher",
            [proj("fecundidade", "Taxa de fecundidade total", fecundidade, casas=2)],
            unidade="filhos por mulher",
            casas=2,
            periodicidade="A",
            linhas=[LinhaRef(valor=REPOSICAO, rotulo="reposição (2,1)")],
            fonte=fonte_tab4,
            nota=(
                "Quantos filhos uma mulher teria na vida com as taxas de cada idade daquele "
                f"ano. Abaixo de 2,1, cada geração é menor que a dos pais. {NOTA_PROJECAO}"
            ),
        ),
        grafico(
            "esperanca-de-vida",
            "Esperança de vida ao nascer",
            [
                proj("total", "Total", ind["e0_T"]),
                proj("mulheres", "Mulheres", ind["e0_M"]),
                proj("homens", "Homens", ind["e0_H"]),
            ],
            unidade="anos",
            casas=1,
            periodicidade="A",
            fonte=fonte_tab4,
            nota=NOTA_PROJECAO,
        ),
        grafico(
            "mortalidade-infantil",
            "Mortalidade infantil",
            [proj("total", "Mortes antes de 1 ano por mil nascidos vivos", ind["TMI_T"])],
            unidade="por mil nascidos",
            casas=1,
            periodicidade="A",
            fonte=fonte_tab4,
            nota=(
                "Quantas crianças, em cada mil nascidas vivas, morrem antes de fazer um ano. "
                "Cai com saneamento, vacina, pré-natal e renda; é uma das medidas mais usadas "
                f"de condição de vida. {NOTA_PROJECAO}"
            ),
        ),
        grafico(
            "idosos",
            "Idosos na população",
            [
                proj("65", "65 anos ou mais", pct_65),
                proj("80", "80 anos ou mais", pct_80),
            ],
            unidade="% da população",
            casas=1,
            periodicidade="A",
            fonte=fonte_tab3,
            nota=NOTA_PROJECAO,
        ),
        grafico(
            "crescimento-15-64",
            "Quanto cresce a população de 15 a 64 anos",
            [proj("15-64", "15 a 64 anos", cresc_pia, casas=2)],
            unidade="% ao ano",
            casas=2,
            periodicidade="A",
            fonte=fonte_tab3,
            nota=(
                "PIB = pessoas ocupadas × produto por ocupado. Enquanto a idade de trabalhar "
                "cresce, a demografia soma ao PIB; abaixo de zero, a economia só cresce com "
                "mais produtividade ou com mais gente dessa idade trabalhando. " + NOTA_PROJECAO
            ),
        ),
    ]
    graficos += graficos_inss
    try:
        graficos.append(_grafico_onu(populacao))
    except Exception as erro:  # a ONU fora do ar não derruba a seção
        print(f"    a projeção da ONU ficou de fora: {str(erro)[:120]}")
    try:
        graficos.append(_grafico_idosos_paises(agora))
    except Exception as erro:
        print(f"    o Banco Mundial ficou de fora da demografia: {str(erro)[:120]}")

    tabelas = [_tabela_marcos(agora, ind, br_grupos), _tabela_estados(agora, grupos)]
    tabelas += tabelas_prev

    resumo = (
        f"O Brasil tem {br(populacao[agora] / 1e6)} milhões de habitantes em {agora} e, "
        f"pela projeção do IBGE, para de crescer em {ano_pico_pop}. Cada mulher tem em média "
        f"{filhos(fecundidade[agora])}, abaixo dos 2,1 que repõem a população; há "
        f"{br(dep_idosos[agora])} idosos para cada 100 pessoas de 15 a 64 anos, e serão "
        f"{br(dep_idosos[2050])} em 2050. Com a idade de trabalhar parando de crescer em "
        f"{ano_pico_pia}, o PIB passa a depender da produtividade, e o INSS paga mais "
        "aposentados com menos gente em idade de contribuir."
    )
    return Secao(
        id="demografia",
        titulo="Demografia",
        resumo=resumo,
        cartoes=cartoes,
        graficos=graficos,
        tabelas=tabelas,
        gerado_em=ctx.agora(),
    )


def _previdencia_uniao(ctx: Contexto) -> tuple[Cartao, Grafico, Tabela]:
    """O INSS ao lado da previdência dos servidores civis e dos militares da União."""
    anos = siconfi.previdencia_uniao(ctx.hoje)
    rtn = tesouro_rtn.serie_historica()
    beneficios = soma_do_ano(rtn["rgps"])
    arrecadacao = soma_do_ano(rtn["arrecadacao_rgps"])
    inss = {a: beneficios[a] - arrecadacao[a] for a in beneficios if a in arrecadacao}
    pib = pib_do_ano(ctx.sgs("PIB_12M", 30))
    pct = previdencia_em_pct_do_pib(anos, inss, pib)
    if not pct["civis"]:
        raise RuntimeError("sem o PIB dos anos da previdência da União")
    ultimo = next(p for p in reversed(anos) if p.ano in pib)
    a = ultimo.ano
    civis, militares = pct["civis"][-1][1], pct["militares"][-1][1]
    fonte_rreo = (
        "Tesouro Nacional, SICONFI: RREO da União, 6º bimestre (Anexo 04: servidores civis e "
        "militares)"
    )
    fonte = (
        f"{fonte_rreo}; INSS: Resultado do Tesouro Nacional (tabela 1.1); "
        f"PIB: {ctx.fonte_sgs('PIB_12M')}"
    )
    cartao_ = Cartao(
        id="deficit-servidores-militares",
        rotulo="Déficit de servidores e militares da União",
        valor=round(civis + militares, 2),
        unidade="% do PIB",
        casas=2,
        referencia=date(a, 1, 1),
        periodicidade="A",
        detalhe=f"civis {br(civis, 2)} %; militares {br(militares, 2)} %",
        fonte=fonte,
        procedencia="calculado",
        mini=[
            (d, round(v + m, 2))
            for (d, v), (_, m) in zip(pct["civis"], pct["militares"], strict=True)
        ],
        secao="demografia",
    )
    grafico_ = grafico(
        "previdencia-uniao",
        "Déficit da previdência: INSS, servidores e militares",
        [
            serie("inss", "INSS", pct["inss"], casas=2),
            serie("civis", "Servidores civis da União", pct["civis"], casas=2),
            serie("militares", "Militares", pct["militares"], casas=2),
        ],
        unidade="% do PIB",
        casas=2,
        periodicidade="A",
        fonte=fonte,
        nota=(
            "O que falta para pagar aposentadorias e pensões depois das contribuições, em cada "
            "ano. Servidores civis: o regime próprio da União (dos três Poderes). Militares: "
            "pensões e militares da reserva e reformados (estes não contribuem). Os números da "
            "União são as despesas liquidadas no ano; os do INSS, os benefícios pagos. Fora: "
            "policiais e bombeiros do DF, que a União paga pelo Fundo Constitucional do DF, e "
            "os servidores de estados e municípios."
        ),
    )

    def linha(nome: str, receita: float, despesa: float) -> LinhaTabela:
        """Em R$ bilhões; o déficit também em % do PIB."""
        deficit = despesa - receita
        return LinhaTabela(
            rotulo=nome,
            valores=[
                round(receita / 1e9, 1),
                round(despesa / 1e9, 1),
                round(deficit / 1e9, 1),
                round(deficit / (pib[a] * 1e6) * 100, 2),
            ],
            unidade="",
            casas=1,
        )

    linhas = []
    if a in beneficios and a in arrecadacao:
        linhas.append(linha("INSS", arrecadacao[a] * 1e6, beneficios[a] * 1e6))
    linhas += [
        linha("Servidores civis da União", ultimo.civis_receita, ultimo.civis_despesa),
        linha("Militares", ultimo.militares_receita, ultimo.militares_despesa),
    ]
    tabela = Tabela(
        id="previdencia-uniao",
        titulo="As três previdências que a União paga",
        subtitulo=f"{a}; R$ bilhões e o déficit em % do PIB",
        colunas=["contribuições", "benefícios", "déficit", "% do PIB"],
        linhas=linhas,
        fonte=fonte,
        nota=(
            "Contribuições: o que se recolhe para cada regime (no dos servidores civis, com "
            "a parte que a União paga como empregadora; no dos militares, só a dos próprios "
            "militares, para as pensões). Benefícios: aposentadorias, pensões e, nos "
            "militares, a remuneração da reserva e dos reformados. INSS: arrecadação líquida "
            "e benefícios pagos no ano, do RTN; União: receitas realizadas e despesas "
            "liquidadas, do RREO."
        ),
    )
    return cartao_, grafico_, tabela


def _tabela_marcos(agora: int, ind: dict[str, PorAno], g: dict[str, PorAno]) -> Tabela:
    anos = [ANOS_DA_TABELA[0], agora, *ANOS_DA_TABELA[1:]]

    def linha(
        rotulo: str, por_ano: PorAno, unidade: str, casas: int = 1, escala: float = 1.0
    ) -> LinhaTabela:
        return LinhaTabela(
            rotulo=rotulo,
            valores=[
                None if a not in por_ano else round(por_ano[a] * escala, casas + 2) for a in anos
            ],
            unidade=unidade,
            casas=casas,
        )

    por_idoso = {a: 100 / v for a, v in ind["RDI65"].items() if v}
    return Tabela(
        id="demografia-marcos",
        titulo="A população em quatro anos",
        subtitulo=f"{anos[0]}, hoje e a projeção até {anos[-1]}",
        colunas=[str(a) for a in anos],
        linhas=[
            linha("População", g["POP_T"], "milhões", escala=1e-6),
            linha("0 a 14 anos", g["0-14_T"], "milhões", escala=1e-6),
            linha("15 a 64 anos", g["15-64_T"], "milhões", escala=1e-6),
            linha("65 anos ou mais", g["65+_T"], "milhões", escala=1e-6),
            linha("80 anos ou mais", g["80+_T"], "milhões", escala=1e-6),
            linha("65 anos ou mais", g["P_65+_T"], "% da população", escala=100),
            linha("Idosos por 100 de 15 a 64", ind["RDI65"], ""),
            linha("Jovens por 100 de 15 a 64", ind["RDJ65"], ""),
            linha("Pessoas de 15 a 64 por idoso", por_idoso, ""),
            linha("Filhos por mulher", ind["TFT"], "", casas=2),
            linha("Esperança de vida ao nascer", ind["e0_T"], "anos"),
            linha("Esperança de vida aos 60", ind["e60_T"], "anos a mais"),
            linha("Idade mediana", ind["ID_MED"], "anos"),
            linha("Nascimentos", ind["NASC_T"], "mil", casas=0, escala=1e-3),
            linha("Óbitos", ind["OBT_T"], "mil", casas=0, escala=1e-3),
        ],
        fonte=f"{PROJECAO} (tabelas 3 e 4)",
        nota=(
            f"Cada ano com referência em 1º de julho. Até {ULTIMO_ANO_AJUSTADO}, dado ajustado "
            "aos Censos; depois, projeção. Idosos: 65 anos ou mais; jovens: 0 a 14 anos."
        ),
    )


def _tabela_estados(agora: int, grupos: dict[str, dict[str, PorAno]]) -> Tabela:
    anos = [agora, 2050, 2070]
    linhas: list[tuple[float, LinhaTabela]] = []
    for _, sigla, nome, _ in UFS:
        fatia = grupos.get(sigla, {}).get("P_65+_T")
        if not fatia:
            continue
        valores = [None if a not in fatia else round(fatia[a] * 100, 3) for a in anos]
        linhas.append(
            (fatia.get(agora, 0.0), LinhaTabela(rotulo=nome, valores=valores, unidade=""))
        )
    linhas.sort(key=lambda x: -x[0])
    brasil = grupos["BR"]["P_65+_T"]
    return Tabela(
        id="demografia-estados",
        titulo="Idosos por estado",
        subtitulo=f"pessoas de 65 anos ou mais, em % da população; do mais velho em {agora} "
        "ao mais novo",
        colunas=[str(a) for a in anos],
        linhas=[
            LinhaTabela(
                rotulo="Brasil",
                valores=[None if a not in brasil else round(brasil[a] * 100, 3) for a in anos],
                unidade="",
            ),
            *(linha for _, linha in linhas),
        ],
        fonte=f"{PROJECAO} (tabela 3, por unidade da federação)",
        nota=f"Até {ULTIMO_ANO_AJUSTADO}, dado ajustado aos Censos; depois, projeção.",
    )


def _grafico_onu(populacao_ibge: PorAno) -> Grafico:
    """A população pela ONU (o meio e a faixa de 80 %) ao lado da projeção do IBGE."""
    onu = onu_wpp.populacao()
    mediana = [(date(a, 1, 1), v / 1e3) for a, v in sorted(onu.mediana.items())]
    if not mediana:
        raise RuntimeError("ONU sem a mediana")
    a50, a100 = 2050, 2100
    return grafico(
        "populacao-onu",
        "População: a projeção da ONU, com a faixa, e a do IBGE",
        [
            serie(
                "ibge",
                "IBGE",
                pontos(populacao_ibge, 1e-6),
                casas=1,
                tracejado_desde=PROJETADO_DESDE,
            ),
            serie("onu", "ONU, o meio da faixa", mediana, casas=1, tracejado_desde=mediana[0][0]),
        ],
        unidade="milhões de pessoas",
        casas=1,
        periodicidade="A",
        fonte=f"{onu_wpp.FONTE}; {PROJECAO} (tabela 3)",
        intervalos=[
            Intervalo(
                nome="8 em cada 10 futuros da ONU ficam entre as pontas",
                serie="onu",
                pontos=barras_onu(onu, ANOS_DAS_BARRAS_ONU),
            )
        ],
        nota=(
            "Como ler: a ONU sorteia milhares de futuros para a fecundidade e a esperança de "
            "vida; a linha é o do meio, e a barra vai de onde ficam os 10 % mais baixos a onde "
            "ficam os 10 % mais altos. Com 19 de cada 20 futuros, a faixa de "
            f"{a50} vai de {br(onu.inferior95[a50] / 1e3, 0)} a "
            f"{br(onu.superior95[a50] / 1e3, 0)} milhões, e a de {a100}, de "
            f"{br(onu.inferior95[a100] / 1e3, 0)} a {br(onu.superior95[a100] / 1e3, 0)}. O "
            "IBGE não publica faixa; até 2022, a linha dele é dado ajustado aos Censos."
        ),
        largura="inteira",
    )


def _grafico_idosos_paises(agora: int) -> Grafico:
    """O peso dos idosos no Brasil e em outros países, pelo Banco Mundial."""
    series = banco_mundial.series_dos_paises(list(PAISES_IDOSOS), banco_mundial.IDOSOS, 1960, agora)
    if "BRA" not in series:
        raise RuntimeError("Banco Mundial sem o Brasil")
    return grafico(
        "idosos-paises",
        "Idosos na população: o Brasil e o mundo",
        [
            serie(cod.lower(), nome, [(date(a, 1, 1), v) for a, v in series[cod]], casas=1)
            for cod, nome in PAISES_IDOSOS.items()
            if series.get(cod)
        ],
        unidade="% da população",
        casas=1,
        periodicidade="A",
        fonte=f"{banco_mundial.FONTE} ({banco_mundial.IDOSOS}), a partir da ONU",
        nota=(
            "Pessoas de 65 anos ou mais em % da população. O número do Brasil é o da ONU e "
            "não bate exatamente com o do IBGE, que já usa o Censo de 2022."
        ),
    )
