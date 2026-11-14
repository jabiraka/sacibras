"""Demografia: quantos somos, como envelhecemos e o que isso pede do trabalho, da
produtividade e da previdência.

A projeção é a oficial do IBGE (revisão 2024). Até 2022 é dado ajustado aos Censos; dali em
diante, hipótese: nos gráficos a linha segue tracejada. O IBGE não publica faixa de erro.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import date
from typing import NamedTuple

from sacibras import contas
from sacibras.fontes import ibge_projecao, ibge_sidra, tesouro_rtn
from sacibras.fontes.ibge_projecao import FONTE as PROJECAO
from sacibras.fontes.ibge_projecao import ULTIMO_ANO_AJUSTADO, PorAno
from sacibras.schema import (
    Cartao,
    Grafico,
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

PIB_VOLUME = (1620, 583, "c11255/90707")
"""SIDRA 1620, variável 583: série encadeada do índice de volume trimestral (média 1995 = 100),
PIB a preços de mercado. Conferido pela própria resposta em 14/11/2026."""
OCUPADOS = (6318, 1641, "c629/32387")
"""PNAD Contínua, pessoas de 14 anos ou mais ocupadas (mil), trimestre móvel; a mesma tabela
da seção Trabalho."""

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


def trimestre_civil(movel: list[Ponto]) -> list[Ponto]:
    """Do trimestre móvel da PNAD (data = último mês) ao trimestre civil (data = 1º mês),
    como as datas trimestrais do SIDRA: o móvel até março é o 1º trimestre."""
    return [(date(d.year, d.month - 2, 1), v) for d, v in movel if d.month in (3, 6, 9, 12)]


def produtividade(pib: list[Ponto], ocupados: list[Ponto]) -> dict[str, list[Ponto]]:
    """PIB de quatro trimestres (volume) sobre a média de ocupados dos mesmos quatro, e as
    duas partes, todos com 100 na primeira janela completa (o ano de 2012, na PNAD)."""
    pib_4t = dict(contas.soma_movel(pib, 4))
    ocup_4t = dict(contas.media_movel(ocupados, 4))
    datas = sorted(set(pib_4t) & set(ocup_4t))
    por_ocupado = [(d, pib_4t[d] / ocup_4t[d]) for d in datas]
    return {
        "pib": contas.base_100([(d, pib_4t[d]) for d in datas]),
        "ocupados": contas.base_100([(d, ocup_4t[d]) for d in datas]),
        "por_ocupado": contas.base_100(por_ocupado),
    }


class Ano(NamedTuple):
    """Um ano da decomposição do crescimento, tudo em %."""

    ano: int
    pib: float
    ocupados: float
    produtividade: float
    """(1 + PIB) / (1 + ocupados) − 1: o crescimento do PIB por ocupado."""
    parte_ocupados: float
    parte_produtividade: float
    """As duas partes somam `pib`: repartem o crescimento na proporção dos logaritmos."""


def decomposicao_anual(pib: list[Ponto], ocupados: list[Ponto]) -> list[Ano]:
    """O crescimento do PIB de cada ano em duas partes: mais gente ocupada e mais produto por
    ocupado. Só anos com os quatro trimestres nas duas séries (PIB somado, ocupados na média).

    O crescimento é o produto (1 + ocupados) · (1 + produtividade); a repartição pelos
    logaritmos faz as partes somarem exatamente o total."""

    def por_ano(serie: list[Ponto]) -> dict[int, list[float]]:
        saida: dict[int, list[float]] = {}
        for d, v in serie:
            saida.setdefault(d.year, []).append(v)
        return {a: vs for a, vs in saida.items() if len(vs) == 4}

    p = {a: sum(vs) for a, vs in por_ano(pib).items()}
    o = {a: sum(vs) / 4 for a, vs in por_ano(ocupados).items()}
    saida: list[Ano] = []
    for ano in sorted(p):
        if ano - 1 not in p or ano not in o or ano - 1 not in o:
            continue
        g = p[ano] / p[ano - 1] - 1
        g_ocup = o[ano] / o[ano - 1] - 1
        g_prod = (1 + g) / (1 + g_ocup) - 1
        log_g = math.log1p(g)
        parte = g * math.log1p(g_ocup) / log_g if abs(log_g) > 1e-12 else g_ocup
        saida.append(Ano(ano, g * 100, g_ocup * 100, g_prod * 100, parte * 100, (g - parte) * 100))
    return saida


def media_geometrica(taxas: list[float]) -> float:
    """A taxa média por período, em %, de taxas em %."""
    if not taxas:
        return 0.0
    fator = math.prod(1 + t / 100 for t in taxas)
    return (fator ** (1 / len(taxas)) - 1) * 100


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

    # --- Produtividade: PIB por pessoa ocupada (Contas Trimestrais e PNAD) ---
    pib_vol = ibge_sidra.serie(
        PIB_VOLUME[0], PIB_VOLUME[1], classificacao=PIB_VOLUME[2], trimestral=True
    )
    ocupados = trimestre_civil(
        ibge_sidra.serie(OCUPADOS[0], OCUPADOS[1], classificacao=OCUPADOS[2])
    )
    prod = produtividade(pib_vol, ocupados)
    decomposicao = decomposicao_anual(pib_vol, ocupados)
    fonte_prod = (
        f"IBGE, Contas Nacionais Trimestrais (SIDRA {PIB_VOLUME[0]}, PIB em volume) e PNAD "
        f"Contínua (SIDRA {OCUPADOS[0]}, ocupados, trimestre civil)"
    )
    var_prod = contas.variacao(prod["por_ocupado"], 4)
    media_anual = media_geometrica([x.produtividade for x in decomposicao])

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
        cartao(
            "produtividade",
            "PIB por pessoa ocupada, em 4 trimestres",
            var_prod,
            unidade="%",
            periodicidade="T",
            casas=1,
            detalhe=(
                f"média de {decomposicao[0].ano} a {decomposicao[-1].ano}: "
                f"{br(media_anual, 2)} % ao ano"
                if decomposicao
                else "contra os quatro trimestres anteriores"
            ),
            fonte=fonte_prod,
            procedencia="calculado",
            secao="demografia",
            mini=40,
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
        grafico(
            "produtividade",
            "PIB, ocupados e PIB por pessoa ocupada",
            [
                serie("por-ocupado", "PIB por ocupado", prod["por_ocupado"], casas=1),
                serie("pib", "PIB", prod["pib"], casas=1),
                serie("ocupados", "Ocupados", prod["ocupados"], casas=1),
            ],
            unidade="índice, 2012 = 100",
            casas=1,
            periodicidade="T",
            fonte=fonte_prod,
            nota=(
                "Somas de quatro trimestres: o PIB em volume e a média de ocupados. A PNAD "
                "começa em 2012. É produto por pessoa, não por hora trabalhada."
            ),
        ),
    ]
    if decomposicao:
        graficos.append(
            grafico(
                "crescimento-decomposto",
                "De onde veio o crescimento do PIB",
                [
                    serie(
                        "ocupados",
                        "Mais gente ocupada",
                        [(date(x.ano, 1, 1), x.parte_ocupados) for x in decomposicao],
                    ),
                    serie(
                        "produtividade",
                        "Mais produto por ocupado",
                        [(date(x.ano, 1, 1), x.parte_produtividade) for x in decomposicao],
                    ),
                ],
                tipo="empilhado",
                unidade="pontos percentuais do PIB no ano",
                casas=1,
                periodicidade="A",
                fonte=fonte_prod,
                nota=(
                    "As duas partes somam o crescimento do PIB no ano (PIB em volume, média "
                    "anual de ocupados; repartição pelos logaritmos, conta nossa). De 2020 a "
                    "2022 a pandemia distorce a conta: quem perdeu o trabalho saiu dela e "
                    "voltou depois."
                ),
            )
        )
    graficos += graficos_inss

    tabelas = [_tabela_marcos(agora, ind, br_grupos), _tabela_estados(agora, grupos)]

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
