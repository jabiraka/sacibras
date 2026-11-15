"""Demografia: quantos somos, como envelhecemos e o que isso pede do trabalho, da
produtividade e da previdência.

A projeção é a oficial do IBGE (revisão 2024). Até 2022 é dado ajustado aos Censos; dali em
diante, hipótese: nos gráficos a linha segue tracejada. O IBGE não publica faixa de erro; a
ONU publica (World Population Prospects 2024, projeção probabilística), e vai ao lado.
O envelhecimento contra outros países vem do Banco Mundial (% de 65 anos ou mais) e a
produtividade por hora é conta nossa: PIB em volume sobre as horas habituais da PNAD
(ocupados × horas por semana).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import date
from typing import NamedTuple

from sacibras import contas, relatorios
from sacibras.fontes import (
    banco_mundial,
    ibge_projecao,
    ibge_sidra,
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

PIB_VOLUME = (1620, 583, "c11255/90707")
"""SIDRA 1620, variável 583: série encadeada do índice de volume trimestral (média 1995 = 100),
PIB a preços de mercado. Conferido pela própria resposta em 14/11/2026."""
OCUPADOS = (6318, 1641, "c629/32387")
"""PNAD Contínua, pessoas de 14 anos ou mais ocupadas (mil), trimestre móvel; a mesma tabela
da seção Trabalho."""

HORAS = (6371, 8190, "c2/6794")
"""PNAD Contínua, média de horas habitualmente trabalhadas por semana em todos os trabalhos,
pessoas ocupadas de 14 anos ou mais, os dois sexos; trimestre civil. Conferido pela resposta
em 15/11/2026 (39,8 horas no 2º tri/2026)."""
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


def por_hora(pib: list[Ponto], ocupados: list[Ponto], horas: list[Ponto]) -> list[Ponto]:
    """PIB de quatro trimestres sobre as horas trabalhadas dos mesmos quatro (ocupados × horas
    por semana, na média), com 100 na primeira janela completa."""
    horas_por_tri = dict(horas)
    total = [(d, v * horas_por_tri[d]) for d, v in ocupados if d in horas_por_tri]
    pib_4t = dict(contas.soma_movel(pib, 4))
    horas_4t = dict(contas.media_movel(total, 4))
    datas = sorted(set(pib_4t) & set(horas_4t))
    return contas.base_100([(d, pib_4t[d] / horas_4t[d]) for d in datas])


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


def ambos_os_sexos(quinquenal: dict[str, dict[str, PorAno]]) -> dict[str, PorAno]:
    """{grupo: {ano: pessoas}}, homens mais mulheres."""
    homens, mulheres = quinquenal["Homens"], quinquenal["Mulheres"]
    return {
        g.strip(): {a: v + mulheres[g].get(a, 0.0) for a, v in por_ano.items()}
        for g, por_ano in homens.items()
        if g in mulheres
    }


def _limites(grupo: str) -> tuple[int, int | None]:
    """ "00-04" → (0, 5); "90+" → (90, None)."""
    if grupo.endswith("+"):
        return int(grupo[:-1]), None
    inicio, fim = grupo.split("-")
    return int(inicio), int(fim) + 1


def acima_de(piramide: dict[str, PorAno], ano: int, idade: float) -> float:
    """Pessoas com `idade` anos ou mais; dentro de um grupo de cinco anos, as pessoas se
    repartem por igual entre as idades."""
    total = 0.0
    for grupo, por_ano in piramide.items():
        inicio, fim = _limites(grupo)
        v = por_ano.get(ano, 0.0)
        if idade <= inicio:
            total += v
        elif fim is not None and idade < fim:
            total += v * (fim - idade) / (fim - inicio)
    return total


def idade_que_mantem(piramide: dict[str, PorAno], ano: int, alvo: float) -> float:
    """A idade de corte x em que, no ano, as pessoas de x anos ou mais divididas pelas de 15 até
    x dão `alvo` (a razão de hoje com o corte em 65). Busca por bisseção entre 15 e 100."""
    de_15 = acima_de(piramide, ano, 15)
    baixo, alto = 15.0, 100.0
    for _ in range(60):
        meio = (baixo + alto) / 2
        idosos = acima_de(piramide, ano, meio)
        if de_15 - idosos <= 0 or idosos / (de_15 - idosos) > alvo:
            baixo = meio
        else:
            alto = meio
    return (baixo + alto) / 2


def nivel_de_precos(anos: list[int], inflacao: dict[int, float], depois: float) -> dict[int, float]:
    """{ano: preços do ano sobre os do primeiro}, com a inflação de cada ano (% ao ano; o que
    faltar em `inflacao` usa `depois`)."""
    base = min(anos)
    nivel, fator = {base: 1.0}, 1.0
    for a in range(base + 1, max(anos) + 1):
        fator *= 1 + inflacao.get(a, depois) / 100
        nivel[a] = fator
    return nivel


def por_pessoa_por_mes(
    reais: dict[int, tuple[float, float]],
    pessoas_mil: dict[int, float],
    inflacao: dict[int, float],
    depois: float,
) -> dict[str, list[Ponto]]:
    """Despesa e déficit (R$ milhões correntes) por pessoa (mil pessoas), por mês, em reais do
    primeiro ano."""
    anos = sorted(a for a in reais if a in pessoas_mil)
    nivel = nivel_de_precos(anos, inflacao, depois)
    saida: dict[str, list[Ponto]] = {"beneficios": [], "deficit": []}
    for a in anos:
        por_pessoa = 1e6 / nivel[a] / (pessoas_mil[a] * 1e3) / 12
        saida["beneficios"].append((date(a, 1, 1), reais[a][0] * por_pessoa))
        saida["deficit"].append((date(a, 1, 1), reais[a][1] * por_pessoa))
    return saida


def freio(parte: PorAno, de: int, ate: int) -> float:
    """Quanto a mudança da parte da população em idade de trabalhar soma (ou tira) do
    crescimento do PIB por habitante, em pontos percentuais ao ano, com o PIB por pessoa
    dessa idade crescendo igual."""
    return float((parte[ate] / parte[de]) ** (1 / (ate - de)) - 1) * 100


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
    tabelas_prev: list[Tabela] = []
    try:
        c_prev, g_prev, t_prev = _previdencia_uniao(ctx)
        cartoes.append(c_prev)
        graficos_inss.append(g_prev)
        tabelas_prev.append(t_prev)
    except Exception as erro:
        print(f"    a previdência da União ficou de fora: {str(erro)[:120]}")

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
    try:
        horas = ibge_sidra.serie(HORAS[0], HORAS[1], classificacao=HORAS[2], trimestral=True)
        hora = por_hora(pib_vol, ocupados, horas)
    except Exception as erro:  # sem as horas, fica só o PIB por ocupado
        print(f"    horas da PNAD ficaram de fora da demografia: {str(erro)[:120]}")
        hora = []

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
    fonte_hora = (
        f"{fonte_prod}; horas: PNAD Contínua (SIDRA {HORAS[0]}, horas habituais em todos os "
        "trabalhos); conta nossa"
    )
    if hora:
        cartoes.append(
            cartao(
                "produtividade-hora",
                "PIB por hora trabalhada, em 4 trimestres",
                contas.variacao(hora, 4),
                unidade="%",
                periodicidade="T",
                casas=1,
                detalhe=f"desde {hora[0][0].year}: {br(hora[-1][1] - 100, 1)} % no total",
                fonte=fonte_hora,
                procedencia="calculado",
                secao="demografia",
                mini=40,
            )
        )

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
            "PIB, ocupados e PIB por pessoa e por hora",
            [
                serie("por-ocupado", "PIB por ocupado", prod["por_ocupado"], casas=1),
                *([serie("por-hora", "PIB por hora trabalhada", hora, casas=1)] if hora else []),
                serie("pib", "PIB", prod["pib"], casas=1),
                serie("ocupados", "Ocupados", prod["ocupados"], casas=1),
            ],
            unidade="índice, 2012 = 100",
            casas=1,
            periodicidade="T",
            fonte=fonte_hora if hora else fonte_prod,
            nota=(
                "Somas de quatro trimestres: o PIB em volume e a média de ocupados. A PNAD "
                "começa em 2012. "
                + (
                    "Por hora: o PIB dividido pelas horas da média de quatro trimestres, cada "
                    "uma os ocupados vezes as horas que costumam trabalhar por semana (conta "
                    "nossa). São as horas habituais, não as feitas de fato: férias, faltas e "
                    "hora extra não entram."
                    if hora
                    else "É produto por pessoa, não por hora trabalhada."
                )
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
    try:
        graficos.append(_grafico_onu(populacao))
    except Exception as erro:  # a ONU fora do ar não derruba a seção
        print(f"    a projeção da ONU ficou de fora: {str(erro)[:120]}")
    try:
        graficos.append(_grafico_idosos_paises(agora))
    except Exception as erro:
        print(f"    o Banco Mundial ficou de fora da demografia: {str(erro)[:120]}")
    c_custo, g_custo = _custo_do_envelhecimento(ctx, quinquenal, dep_idosos, fecundidade)
    cartoes += c_custo
    graficos += g_custo
    c_freio, g_freio = _freio(agora, populacao, pia)
    cartoes.append(c_freio)
    graficos.append(g_freio)

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


# ------------------------------------------------------------------ o custo do envelhecimento

ANOS_DAS_BARRAS_IDOSOS = list(range(2030, 2101, 10))
NOMES_DAS_VARIANTES = {
    "media": "ONU, a média",
    "constante": "Fecundidade constante",
    "reposicao": "Volta já a 2,1 filhos",
    "baixa": "Meio filho a menos",
    "alta": "Meio filho a mais",
}


def por_idoso(idosos_por_100: PorAno) -> PorAno:
    """De idosos por 100 pessoas de 15 a 64 anos a pessoas de 15 a 64 por idoso."""
    return {a: 100 / v for a, v in idosos_por_100.items() if v}


def _custo_do_envelhecimento(
    ctx: Contexto,
    quinquenal: dict[str, dict[str, PorAno]],
    dep_idosos: PorAno,
    fecundidade: PorAno,
) -> tuple[list[Cartao], list[Grafico]]:
    """Demografia › O custo do envelhecimento: o INSS até 2100 do PLDO (o mesmo de Riscos), o
    INSS por pessoa em idade de trabalhar, quantas pessoas dessa idade por idoso (com a faixa
    da ONU), os cenários de fecundidade e a idade que manteria a proporção de hoje.

    Só número oficial onde há (Caio, 15/11/2026: *"não vamos colocar as nossas estimativas
    quando temos oficial, só se pedirem"*); a idade de corte é conta nossa porque não há
    número oficial dela."""
    agora = ctx.hoje.year
    cartoes: list[Cartao] = []
    graficos: list[Grafico] = []
    por_idoso_ibge = por_idoso(dep_idosos)
    hoje = por_idoso_ibge[agora]

    def bloco(nome: str, montar_bloco: Callable[[], tuple[list[Cartao], list[Grafico]]]) -> None:
        try:
            c, g = montar_bloco()
        except Exception as erro:  # uma fonte fora do ar não derruba as outras
            print(f"    {nome} ficou de fora da demografia: {str(erro)[:120]}")
            return
        cartoes.extend(c)
        graficos.extend(g)

    def inss() -> tuple[list[Cartao], list[Grafico]]:
        from sacibras.secoes import riscos  # riscos importa estados, que importa daqui

        b = riscos.inss_ate_2100(ctx, secao="demografia")
        return b.cartoes, b.graficos

    def faixa() -> tuple[list[Cartao], list[Grafico]]:
        onu = onu_wpp.idosos_por_100()
        meio = por_idoso(onu.mediana)
        # A ponta de cima de idosos é a de baixo de pessoas por idoso, e vice-versa.
        barras = [
            (date(a, 1, 1), round(100 / onu.superior95[a], 2), round(100 / onu.inferior95[a], 2))
            for a in ANOS_DAS_BARRAS_IDOSOS
            if a in onu.superior95 and a in onu.inferior95
        ]
        barras80 = [
            (date(a, 1, 1), round(100 / onu.superior80[a], 2), round(100 / onu.inferior80[a], 2))
            for a in ANOS_DAS_BARRAS_IDOSOS
            if a in onu.superior80 and a in onu.inferior80
        ]
        a = 2050
        cartao_ = Cartao(
            id="trabalhadores-por-idoso",
            rotulo=f"Pessoas de 15 a 64 anos por idoso em {a}",
            valor=round(meio[a], 3),
            unidade="",
            casas=1,
            referencia=date(a, 1, 1),
            periodicidade="A",
            detalhe=(
                f"hoje {br(hoje)}; 8 em 10 futuros: {br(100 / onu.superior80[a])} "
                f"a {br(100 / onu.inferior80[a])}"
            ),
            fonte=onu_wpp.FONTE,
            procedencia="oficial",
            secao="demografia",
            mini=[(date(x, 1, 1), round(v, 3)) for x, v in sorted(meio.items())],
        )
        primeiro = date(min(meio), 1, 1)
        grafico_ = grafico(
            "trabalhadores-por-idoso",
            "Quantas pessoas em idade de trabalhar para cada idoso",
            [
                serie(
                    "ibge",
                    "IBGE",
                    pontos(por_idoso_ibge),
                    casas=2,
                    tracejado_desde=PROJETADO_DESDE,
                ),
                serie(
                    "onu", "ONU, o meio da faixa", pontos(meio), casas=2, tracejado_desde=primeiro
                ),
            ],
            unidade="por idoso (65 anos ou mais)",
            casas=1,
            periodicidade="A",
            fonte=f"{onu_wpp.FONTE}; {PROJECAO} (tabela 4, RDI65)",
            intervalos=[
                Intervalo(
                    nome="19 em cada 20 futuros da ONU ficam entre as pontas",
                    serie="onu",
                    pontos=barras,
                    meio=barras80,
                    nome_meio="8 em cada 10 ficam na parte grossa",
                )
            ],
            nota=(
                "Quem está em idade de trabalhar paga, pelas contribuições e pelos impostos, a "
                "aposentadoria de quem não está. Como ler: a ONU sorteia milhares de futuros "
                "para a fecundidade e a esperança de vida; a linha é o do meio e a barra, onde "
                f"ficam os futuros. Hoje são {br(hoje)} pessoas de 15 a 64 anos para cada "
                f"idoso; em 2070, {br(meio[2070])} pela ONU e {br(por_idoso_ibge[2070])} pelo "
                "IBGE, que não publica faixa e supõe a fecundidade mais baixa que a ONU. Até "
                f"{ULTIMO_ANO_AJUSTADO}, a linha do IBGE é dado ajustado aos Censos."
            ),
            largura="inteira",
        )
        return [cartao_], [grafico_]

    def cenarios() -> tuple[list[Cartao], list[Grafico]]:
        var = {k: por_idoso(v) for k, v in onu_wpp.variantes().items()}
        inicio = min(var["media"])
        series = [
            serie(
                "ibge",
                "IBGE",
                [(d, v) for d, v in pontos(por_idoso_ibge) if d.year >= inicio],
                casas=2,
            ),
            *(
                serie(k, NOMES_DAS_VARIANTES[k], pontos(var[k]), casas=2)
                for k in NOMES_DAS_VARIANTES
                if k in var
            ),
        ]
        juntas = max(
            (
                a
                for a in sorted(var["media"])
                if max(var[k][a] for k in var) / min(var[k][a] for k in var) < 1.05
            ),
            default=inicio,
        )
        a = 2070
        nota = (
            f"Pessoas de 15 a 64 anos para cada idoso em cada cenário da ONU. Até {juntas}, as "
            "linhas quase não se separam (menos de 5 % entre a mais alta e a mais baixa): "
            "quase todos os que estarão em idade de trabalhar até lá já nasceram. Em "
            f"{a}: {br(var['constante'][a])} com a fecundidade de hoje mantida, "
            f"{br(var['reposicao'][a])} se ela voltasse já aos 2,1 filhos por mulher que "
            f"repõem a população, {br(var['baixa'][a])} com meio filho a menos que a média da "
            f"ONU e {br(por_idoso_ibge[a])} pelo IBGE, que supõe "
            f"{br(fecundidade[2050], 2)} filho por mulher em 2050; hoje, {br(hoje)}. "
            "Fecundidade constante: a de 2023 (1,62 filho por mulher) até 2100; meio filho a "
            "menos e a mais: meio filho em volta da média da ONU. São cenários da ONU, sem "
            "probabilidade; a faixa está no gráfico de cima."
        )
        return [], [
            grafico(
                "fecundidade-cenarios",
                "E se a fecundidade mudar? Pessoas em idade de trabalhar por idoso",
                series,
                unidade="por idoso (65 anos ou mais)",
                casas=1,
                periodicidade="A",
                fonte=f"{onu_wpp.FONTE_VARIANTES}; {PROJECAO} (tabela 4, RDI65)",
                nota=nota,
                largura="inteira",
            )
        ]

    def por_pessoa() -> tuple[list[Cartao], list[Grafico]]:
        pessoas = onu_wpp.populacao_15_64().mediana
        valores = por_pessoa_por_mes(
            relatorios.RGPS_PROJECAO_REAIS,
            pessoas,
            relatorios.INPC_PROJECAO,
            relatorios.INPC_PROJECAO_DEPOIS,
        )
        beneficios, deficit = dict(valores["beneficios"]), dict(valores["deficit"])
        base = valores["beneficios"][0][0]
        d50 = date(2050, 1, 1)
        fonte = (
            f"{relatorios.FONTE_RGPS_PROJECAO} e 5.1 (INPC); pessoas de 15 a 64 anos: "
            f"{onu_wpp.FONTE}, o meio da faixa; conta nossa"
        )
        cartao_ = Cartao(
            id="inss-por-pessoa",
            rotulo="INSS por pessoa de 15 a 64 anos em 2050, por mês",
            valor=round(beneficios[d50], 0),
            unidade="R$",
            casas=0,
            referencia=d50,
            periodicidade="A",
            detalhe=(
                f"R$ {br(beneficios[base], 0)} em {base.year}; déficit: R$ {br(deficit[d50], 0)}"
            ),
            fonte=fonte,
            procedencia="calculado",
            secao="demografia",
            mini=[(d, round(v, 0)) for d, v in valores["beneficios"]],
        )
        grafico_ = grafico(
            "inss-por-pessoa",
            "O INSS por pessoa em idade de trabalhar, na projeção do governo",
            [
                serie("beneficios", "Benefícios", valores["beneficios"], casas=0),
                serie("deficit", "Déficit", valores["deficit"], casas=0),
            ],
            unidade=f"R$ por mês, em reais de {base.year}",
            casas=0,
            periodicidade="A",
            fonte=fonte,
            nota=(
                "A despesa e o déficit do INSS da projeção que o Ministério da Previdência "
                "manda com o projeto da LDO, divididos pelas pessoas de 15 a 64 anos da "
                "projeção da ONU (a mesma população que o ministério usa) e por 12 meses. Em "
                f"reais de {base.year}, descontada a inflação (INPC) da própria projeção. "
                "Déficit é a parte que as contribuições não cobrem e sai dos impostos. Sobe "
                "por dois motivos: há mais idosos por pessoa em idade de trabalhar e o "
                "benefício mínimo, que é um salário mínimo, sobe com o PIB."
            ),
        )
        return [cartao_], [grafico_]

    def idade() -> tuple[list[Cartao], list[Grafico]]:
        piramide = ambos_os_sexos(quinquenal)
        alvo = acima_de(piramide, agora, 65) / (
            acima_de(piramide, agora, 15) - acima_de(piramide, agora, 65)
        )
        anos = [a for a in range(agora, 2071)]
        corte = [(date(a, 1, 1), idade_que_mantem(piramide, a, alvo)) for a in anos]
        valores = dict(corte)
        a50, a70 = date(2050, 1, 1), date(2070, 1, 1)
        fonte = f"{PROJECAO} (tabela 2, grupos de cinco anos); conta nossa"
        cartao_ = Cartao(
            id="idade-mesma-proporcao",
            rotulo="Idade que manteria a proporção de hoje, em 2050",
            valor=round(valores[a50], 2),
            unidade="anos",
            casas=0,
            referencia=a50,
            periodicidade="A",
            detalhe=f"hoje 65 anos; em 2070, {br(valores[a70], 0)}",
            fonte=fonte,
            procedencia="calculado",
            secao="demografia",
            mini=[(d, round(v, 2)) for d, v in corte],
        )
        grafico_ = grafico(
            "idade-mesma-proporcao",
            "A idade de corte que manteria a proporção de hoje",
            [serie("idade", "Idade de corte", corte, casas=1)],
            unidade="anos",
            casas=0,
            periodicidade="A",
            fonte=fonte,
            linhas=[LinhaRef(valor=65, rotulo="65 anos, o corte de hoje")],
            nota=(
                f"Hoje há {br(1 / alvo)} pessoas de 15 a 64 anos para cada pessoa de 65 ou "
                "mais. A linha é a idade que, contada como o começo da velhice, manteria essa "
                "mesma proporção em cada ano da projeção do IBGE: tudo o que está acima dela "
                "conta como idoso, e de 15 até ela, como idade de trabalhar. É uma régua da "
                "pirâmide, não a idade de aposentadoria da lei. Conta nossa: dentro de cada "
                "grupo de cinco anos, as pessoas se repartem por igual entre as idades."
            ),
        )
        return [cartao_], [grafico_]

    bloco("o INSS até 2100", inss)
    bloco("a faixa da ONU dos idosos", faixa)
    bloco("o INSS por pessoa", por_pessoa)
    bloco("a idade que manteria a proporção", idade)
    bloco("os cenários de fecundidade da ONU", cenarios)
    return cartoes, graficos


def _freio(agora: int, populacao: PorAno, pia: PorAno) -> tuple[Cartao, Grafico]:
    """Produtividade: a parte da população em idade de trabalhar e o que a queda dela tira do
    PIB por habitante."""
    parte = {a: pia[a] / v * 100 for a, v in populacao.items() if v and a in pia}
    ate_2050, depois = freio(parte, agora, 2050), freio(parte, 2050, 2070)
    fonte = f"{PROJECAO} (tabela 3, grupos etários)"
    cartao_ = Cartao(
        id="freio-demografico",
        rotulo="O que a idade tira do PIB por habitante até 2050",
        valor=round(ate_2050, 4),
        unidade="pp ao ano",
        casas=2,
        referencia=date(agora, 1, 1),
        periodicidade="A",
        detalhe=f"de 2050 a 2070: {br(depois, 2)} pp ao ano",
        fonte=f"{fonte}; conta nossa",
        procedencia="calculado",
        secao="demografia",
        mini=[(d, round(v, 3)) for d, v in pontos(parte)],
    )
    pico_ano, pico_valor = pico(parte)
    grafico_ = grafico(
        "idade-de-trabalhar-parte",
        "Quanto da população está em idade de trabalhar",
        [
            serie(
                "parte",
                "15 a 64 anos, % da população",
                pontos(parte),
                casas=1,
                tracejado_desde=PROJETADO_DESDE,
            )
        ],
        unidade="% da população",
        casas=1,
        periodicidade="A",
        fonte=fonte,
        nota=(
            f"O pico foi em {pico_ano}, com {br(pico_valor)} %; em 2070 serão "
            f"{br(parte[2070])} %. PIB por habitante = PIB por pessoa de 15 a 64 anos × a "
            "parte da população nessa idade. Se o primeiro crescer como antes, a queda da "
            f"segunda tira {br(-ate_2050, 2)} ponto percentual por ano do crescimento do PIB "
            f"por habitante de {agora} a 2050 e {br(-depois, 2)} de 2050 a 2070 (conta "
            f"nossa, com a projeção do IBGE). {NOTA_PROJECAO}"
        ),
    )
    return cartao_, grafico_
