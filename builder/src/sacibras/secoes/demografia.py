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
from itertools import pairwise
from typing import NamedTuple

from sacibras import contas
from sacibras.fontes import (
    banco_mundial,
    ibge_projecao,
    ibge_sidra,
    onu_wpp,
    pwt,
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
HORAS_EFETIVAS = (6371, 8192, "c2/6794")
"""PNAD Contínua, média de horas efetivamente trabalhadas na semana de referência em todos os
trabalhos, os dois sexos; trimestre civil. As habituais (8190) não pegam a queda de 2020: com
elas a PTF estendida erra 4 pp em 2020 e 2021 contra a PWT; com estas, 0,2 pp (15/11/2026)."""
FBCF_VOLUME = (1620, 583, "c11255/93406")
"""Contas Trimestrais, formação bruta de capital fixo, a mesma série encadeada do PIB."""
ESTUDO = (7126, 3593, "c2/6794/c58/2795")
"""PNAD Contínua anual, número médio de anos de estudo das pessoas de 15 anos ou mais, os dois
sexos. Sem 2020 e 2021 (o módulo de educação não foi a campo); uma casa decimal."""
PAISES_IDOSOS = {
    "BRA": "Brasil",
    "WLD": "Mundo",
    "LCN": "América Latina e Caribe",
    "HIC": "Países de renda alta",
    "CHN": "China",
    "JPN": "Japão",
}
"""As seis séries do envelhecimento contra o mundo (seis cores de série)."""
PAISES_PTF = {
    "BRA": "Brasil",
    "MEX": "México",
    "CHL": "Chile",
    "ARG": "Argentina",
    "KOR": "Coreia do Sul",
    "CHN": "China",
}
"""A PTF contra a dos EUA: o Brasil, três vizinhos e dois emergentes da Ásia (seis cores)."""
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


class Parcela(NamedTuple):
    """Um ano da contabilidade do crescimento (PWT), em pontos percentuais (log × 100)."""

    ano: int
    pib: float
    capital: float
    horas: float
    escolaridade: float
    ptf: float
    """O que sobra do PIB depois das outras três partes."""
    ptf_pwt: float
    """A variação da PTF publicada pela PWT (`rtfpna`), para conferir."""


def contabilidade(anos: dict[int, dict[str, float]]) -> list[Parcela]:
    """O crescimento do PIB de cada ano em capital, horas trabalhadas, escolaridade e PTF.

    O método da PWT 11 (índice de Törnqvist): o peso do trabalho é a média da parte do
    trabalho na renda (`labsh`) nos dois anos, o do capital é o resto; o trabalho é ocupados ×
    horas por ano × capital humano. As quatro partes somam o crescimento do PIB (em log)."""
    precisa = ("rgdpna", "rnna", "emp", "avh", "hc", "labsh", "rtfpna")
    completos = {a: v for a, v in anos.items() if all(c in v for c in precisa)}
    saida: list[Parcela] = []
    for ano in sorted(completos):
        antes = completos.get(ano - 1)
        if antes is None:
            continue
        agora = completos[ano]
        peso = (agora["labsh"] + antes["labsh"]) / 2

        def log(campo: str, a: dict[str, float] = agora, b: dict[str, float] = antes) -> float:
            return math.log(a[campo] / b[campo]) * 100

        pib = log("rgdpna")
        capital = (1 - peso) * log("rnna")
        horas = peso * (log("emp") + log("avh"))
        escolaridade = peso * log("hc")
        saida.append(
            Parcela(
                ano,
                pib,
                capital,
                horas,
                escolaridade,
                pib - capital - horas - escolaridade,
                log("rtfpna"),
            )
        )
    return saida


def retorno_do_estudo(anos: float) -> float:
    """A conta do capital humano da PWT (Caselli, 2005): cada ano de estudo rende 13,4 % até o
    4º, 10,1 % do 5º ao 8º e 6,8 % daí em diante; o capital humano é exp(isto)."""
    return 0.134 * min(anos, 4) + 0.101 * max(0.0, min(anos, 8) - 4) + 0.068 * max(0.0, anos - 8)


def anual(trimestral: list[Ponto], media: bool = False) -> dict[int, float]:
    """{ano: soma (ou média) dos quatro trimestres}, só nos anos com os quatro."""
    por: dict[int, list[float]] = {}
    for d, v in trimestral:
        por.setdefault(d.year, []).append(v)
    return {a: sum(v) / (4 if media else 1) for a, v in por.items() if len(v) == 4}


class Insumos(NamedTuple):
    """O que o IBGE publica para estender a PTF, por ano: PIB e FBCF em volume (soma dos
    trimestres), ocupados e horas efetivas (média) e anos de estudo (PNAD anual)."""

    pib: dict[int, float]
    fbcf: dict[int, float]
    ocupados: dict[int, float]
    horas: dict[int, float]
    estudo: dict[int, float]

    def estudo_em(self, ano: int) -> float | None:
        """Os anos de estudo do ano; ano sem PNAD (2020, 2021), na reta entre os vizinhos."""
        if ano in self.estudo:
            return self.estudo[ano]
        antes = [a for a in self.estudo if a < ano]
        depois = [a for a in self.estudo if a > ano]
        if not antes or not depois:
            return None
        a, b = max(antes), min(depois)
        return self.estudo[a] + (self.estudo[b] - self.estudo[a]) * (ano - a) / (b - a)


class Estendida(NamedTuple):
    """Um ano depois da PWT: o nível da PTF (2021 = 100) com o capital humano da PNAD e com
    ele no ritmo dos últimos cinco anos da PWT, e as partes do crescimento (com o da PNAD)."""

    ano: int
    ptf: float
    ptf_ritmo_pwt: float
    parcela: Parcela


def _log(a: float, b: float) -> float:
    return math.log(a / b) * 100


def _capital_seguinte(
    capital: float, investimento: float, depreciacao: float, fbcf: dict[int, float], ano: int
) -> tuple[float, float]:
    """Inventário perpétuo, como a PWT: o investimento do ano cresce como a FBCF do IBGE e o
    capital é o do ano anterior depreciado mais esse investimento."""
    novo_investimento = investimento * fbcf[ano] / fbcf[ano - 1]
    return (1 - depreciacao) * capital + novo_investimento, novo_investimento


def estender_ptf(brasil: dict[int, dict[str, float]], ins: Insumos) -> list[Estendida]:
    """A PTF dos anos depois da PWT, pela conta da PWT com os números do IBGE: PIB, FBCF
    (capital pelo inventário perpétuo, com a depreciação da PWT), ocupados, horas efetivas e
    anos de estudo; o peso do trabalho é a última parte do trabalho na renda da PWT. Para no
    primeiro ano em que falta algum número."""
    ult = max(a for a, v in brasil.items() if "rtfpna" in v)
    fim, antes = brasil[ult], brasil.get(ult - 1, {})
    precisa = ("rnna", "delta", "labsh", "hc")
    if any(c not in fim for c in precisa) or "rnna" not in antes:
        return []
    peso = fim["labsh"]
    capital = fim["rnna"]
    # O investimento implícito do último ano da PWT; daí em diante, a depreciação dela fica.
    investimento = fim["rnna"] - (1 - fim["delta"]) * antes["rnna"]
    inicio_ritmo = brasil.get(ult - 5, {}).get("hc")
    ritmo_hc = _log(fim["hc"], inicio_ritmo) / 5 if inicio_ritmo else 0.0
    nivel = nivel_ritmo = fim["rtfpna"] * 100
    saida: list[Estendida] = []
    ano = ult + 1
    while all(ano in x and ano - 1 in x for x in (ins.pib, ins.fbcf, ins.ocupados, ins.horas)):
        s_ano, s_antes = ins.estudo_em(ano), ins.estudo_em(ano - 1)
        if s_ano is None or s_antes is None:
            break
        novo_capital, investimento = _capital_seguinte(
            capital, investimento, fim["delta"], ins.fbcf, ano
        )
        pib = _log(ins.pib[ano], ins.pib[ano - 1])
        parte_capital = (1 - peso) * _log(novo_capital, capital)
        horas = peso * (
            _log(ins.ocupados[ano], ins.ocupados[ano - 1])
            + _log(ins.horas[ano], ins.horas[ano - 1])
        )
        estudo = peso * (retorno_do_estudo(s_ano) - retorno_do_estudo(s_antes)) * 100
        ptf = pib - parte_capital - horas - estudo
        nivel *= math.exp(ptf / 100)
        nivel_ritmo *= math.exp((ptf + estudo - peso * ritmo_hc) / 100)
        saida.append(
            Estendida(
                ano,
                nivel,
                nivel_ritmo,
                Parcela(ano, pib, parte_capital, horas, estudo, ptf, math.nan),
            )
        )
        capital = novo_capital
        ano += 1
    return saida


def conferir_ptf(brasil: dict[int, dict[str, float]], ins: Insumos) -> tuple[float, float, int]:
    """A conta da extensão nos anos em que a PWT existe, um ano de cada vez a partir do capital
    da PWT do ano anterior: (erro médio, em módulo, com o capital humano da PWT; quanto a PTF
    sai mais alta, em média, com o da PNAD; primeiro ano conferido), em pp por ano."""
    erros: list[float] = []
    vies: list[float] = []
    primeiro = 0
    for ano in sorted(brasil):
        a, b, c = brasil[ano], brasil.get(ano - 1, {}), brasil.get(ano - 2, {})
        campos = ("rnna", "delta", "labsh", "hc", "rtfpna")
        if not all(k in x for x in (a, b) for k in campos) or "rnna" not in c:
            continue
        if not all(ano in x and ano - 1 in x for x in (ins.pib, ins.fbcf, ins.ocupados, ins.horas)):
            continue
        # Como na extensão: o investimento implícito do ano anterior e a depreciação dele.
        investimento = b["rnna"] - (1 - b["delta"]) * c["rnna"]
        capital, _ = _capital_seguinte(b["rnna"], investimento, b["delta"], ins.fbcf, ano)
        peso = (a["labsh"] + b["labsh"]) / 2
        resto = (
            _log(ins.pib[ano], ins.pib[ano - 1])
            - (1 - peso) * _log(capital, b["rnna"])
            - peso
            * (
                _log(ins.ocupados[ano], ins.ocupados[ano - 1])
                + _log(ins.horas[ano], ins.horas[ano - 1])
            )
        )
        da_pwt = _log(a["rtfpna"], b["rtfpna"])
        erros.append(abs(resto - peso * _log(a["hc"], b["hc"]) - da_pwt))
        primeiro = primeiro or ano
        s_ano, s_antes = ins.estudo_em(ano), ins.estudo_em(ano - 1)
        if s_ano is not None and s_antes is not None:
            com_pnad = resto - peso * (retorno_do_estudo(s_ano) - retorno_do_estudo(s_antes)) * 100
            vies.append(com_pnad - da_pwt)
    if not erros:
        return math.nan, math.nan, 0
    return sum(erros) / len(erros), (sum(vies) / len(vies) if vies else math.nan), primeiro


def anos_repetidos(anos: dict[int, dict[str, float]], campo: str) -> list[int]:
    """Os últimos anos em que o campo só repete o do ano anterior (a PWT estende assim a
    parte do trabalho quando falta o dado)."""
    serie = [(a, v[campo]) for a, v in sorted(anos.items()) if campo in v]
    saida: list[int] = []
    for (_, antes), (ano, valor) in reversed(list(pairwise(serie))):
        if valor != antes:
            break
        saida.insert(0, ano)
    return saida


def periodos(parcelas: list[Parcela]) -> list[tuple[str, Parcela]]:
    """A média por ano de cada parte, por década (1961 a 1970...); a primeira e a última
    ficam com os anos que houver. O rótulo é "1961 a 1970"."""
    grupos: dict[int, list[Parcela]] = {}
    for p in parcelas:
        grupos.setdefault((p.ano - 1) // 10, []).append(p)
    saida: list[tuple[str, Parcela]] = []
    for chave in sorted(grupos):
        g = grupos[chave]
        n = len(g)
        media = Parcela(
            g[-1].ano,
            *(sum(getattr(p, c) for p in g) / n for c in Parcela._fields[1:]),
        )
        saida.append((f"{g[0].ano} a {g[-1].ano}", media))
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
    tabelas_pwt: list[Tabela] = []
    insumos: Insumos | None = None
    try:  # o que o IBGE publica para estender a PTF depois da PWT
        insumos = Insumos(
            pib=anual(pib_vol),
            fbcf=anual(
                ibge_sidra.serie(*FBCF_VOLUME[:2], classificacao=FBCF_VOLUME[2], trimestral=True)
            ),
            ocupados=anual(ocupados, media=True),
            horas=anual(
                ibge_sidra.serie(
                    *HORAS_EFETIVAS[:2], classificacao=HORAS_EFETIVAS[2], trimestral=True
                ),
                media=True,
            ),
            estudo={d.year: v for d, v in ibge_sidra.serie(*ESTUDO[:2], classificacao=ESTUDO[2])},
        )
    except Exception as erro:  # sem o IBGE, fica só a PWT
        print(f"    a PTF estendida ficou de fora: {str(erro)[:120]}")
    try:
        c_pwt, g_pwt, t_pwt = _pwt(insumos)
        cartoes += c_pwt
        graficos += g_pwt
        tabelas_pwt.append(t_pwt)
    except Exception as erro:  # a PWT fora do ar não derruba a seção
        print(f"    a Penn World Table ficou de fora: {str(erro)[:120]}")
    try:
        graficos.append(_grafico_onu(populacao))
    except Exception as erro:  # a ONU fora do ar não derruba a seção
        print(f"    a projeção da ONU ficou de fora: {str(erro)[:120]}")
    try:
        graficos.append(_grafico_idosos_paises(agora))
    except Exception as erro:
        print(f"    o Banco Mundial ficou de fora da demografia: {str(erro)[:120]}")

    tabelas = [_tabela_marcos(agora, ind, br_grupos), _tabela_estados(agora, grupos)]
    tabelas += tabelas_prev + tabelas_pwt

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


def _pwt(insumos: Insumos | None = None) -> tuple[list[Cartao], list[Grafico], Tabela]:
    """A eficiência da economia (PTF) e de onde veio o crescimento desde 1955, pela PWT; com
    os `insumos` do IBGE, a estimativa nossa dos anos depois dela."""
    todos = pwt.dados(set(PAISES_PTF))
    brasil = todos.get("BRA")
    if not brasil:
        raise RuntimeError("PWT sem o Brasil")
    parcelas = contabilidade(brasil)
    if not parcelas:
        raise RuntimeError("PWT sem anos completos do Brasil")
    ptf = [(date(a, 1, 1), v["rtfpna"] * 100) for a, v in sorted(brasil.items()) if "rtfpna" in v]
    relativa = {
        cod: [
            (date(a, 1, 1), v["ctfp"] * 100) for a, v in sorted(todos[cod].items()) if "ctfp" in v
        ]
        for cod in PAISES_PTF
        if cod in todos
    }
    ultimo = ptf[-1][0].year
    ano_pico, valor_pico = max(((d.year, v) for d, v in ptf), key=lambda x: x[1])
    rel_br = relativa["BRA"]
    ano_pico_rel, pico_rel = max(((d.year, v) for d, v in rel_br), key=lambda x: x[1])
    fonte_ptf = f"{pwt.FONTE}: rtfpna"
    fonte_rel = f"{pwt.FONTE}: ctfp, PTF a paridade de poder de compra"
    fonte_conta = f"{pwt.FONTE}: rgdpna, rnna, emp, avh, hc e labsh; conta nossa pelo método da PWT"
    decadas = periodos(parcelas)
    diferenca = max(abs(m.ptf - m.ptf_pwt) for _, m in decadas)
    repetidos = anos_repetidos(brasil, "labsh")
    aviso_labsh = (
        f" A PWT repete a parte do trabalho na renda de {repetidos[0] - 1} em "
        f"{' e '.join(str(a) for a in repetidos)}."
        if repetidos
        else ""
    )

    estendida = estender_ptf(brasil, insumos) if insumos else []
    if estendida:
        erro, vies, desde = conferir_ptf(brasil, insumos)  # type: ignore[arg-type]
        fim_est = estendida[-1].ano
        fonte_ibge = (
            f"IBGE: Contas Trimestrais (SIDRA {PIB_VOLUME[0]}, PIB e FBCF) e PNAD Contínua "
            f"(SIDRA {OCUPADOS[0]}, ocupados; {HORAS_EFETIVAS[0]}, horas efetivas; "
            f"{ESTUDO[0]}, anos de estudo); conta nossa"
        )
        fonte_est = f"{fonte_ibge}, emendada na {pwt.FONTE.split(' (')[0]} de {ultimo}"
        nota_est = (
            f" De {ultimo + 1} a {fim_est}, estimativa nossa: a mesma conta da PWT com os "
            "números do IBGE (PIB, investimento, ocupados, horas efetivas e anos de estudo da "
            "PNAD), emendada no último ano da PWT. Feita nos anos em que a PWT existe, a conta "
            f"repete a PTF dela desde {desde} com erro médio de {br(erro, 1)} pp por ano, mas "
            f"o estudo da PNAD sobe mais devagar que o da PWT, e com ele a PTF sai em média "
            f"{br(vies, 1)} pp por ano mais alta. A barra vai até a PTF com o capital humano "
            "no ritmo dos últimos cinco anos da PWT."
        )
    cartoes = [
        cartao(
            "ptf-eua",
            "PTF do Brasil contra a dos EUA",
            rel_br,
            unidade="% da dos EUA",
            periodicidade="A",
            casas=0,
            detalhe=f"{br(pico_rel, 0)} % em {ano_pico_rel}, o auge",
            fonte=fonte_rel,
            secao="demografia",
            mini=80,
        ),
        cartao(
            "ptf-desde-o-pico",
            f"PTF do Brasil desde {ano_pico}",
            [(d, (v / valor_pico - 1) * 100) for d, v in ptf if d.year >= ano_pico],
            unidade="%",
            periodicidade="A",
            casas=0,
            detalhe=f"{ultimo} contra {ano_pico}, o auge da série",
            fonte=fonte_ptf,
            procedencia="calculado",
            secao="demografia",
            mini=80,
        ),
    ]
    series_ptf = [serie("ptf", "PTF do Brasil (Penn World Table)", ptf, casas=1)]
    intervalos: list[Intervalo] = []
    if estendida:
        series_ptf.append(
            serie(
                "estimativa",
                "Estimativa nossa (IBGE)",
                [ptf[-1]] + [(date(x.ano, 1, 1), x.ptf) for x in estendida],
                casas=1,
            )
        )
        intervalos.append(
            Intervalo(
                nome="Com o capital humano no ritmo da PWT",
                serie="estimativa",
                pontos=[
                    (
                        date(x.ano, 1, 1),
                        round(min(x.ptf, x.ptf_ritmo_pwt), 2),
                        round(max(x.ptf, x.ptf_ritmo_pwt), 2),
                    )
                    for x in estendida
                ],
            )
        )
        base = ptf[-1][1]
        cartoes.append(
            cartao(
                "ptf-estimativa",
                f"PTF de {ultimo} a {fim_est}, estimativa nossa",
                [(ptf[-1][0], 0.0)]
                + [(date(x.ano, 1, 1), (x.ptf / base - 1) * 100) for x in estendida],
                unidade="%",
                periodicidade="A",
                casas=1,
                detalhe=(
                    "com o estudo no ritmo da PWT: "
                    f"{br((estendida[-1].ptf_ritmo_pwt / base - 1) * 100, 1)} %"
                ),
                fonte=fonte_est,
                procedencia="calculado",
                secao="demografia",
            )
        )
    graficos = [
        grafico(
            "ptf-brasil",
            "Eficiência da economia brasileira (PTF)",
            series_ptf,
            unidade="índice, 2021 = 100",
            casas=1,
            periodicidade="A",
            fonte=f"{fonte_ptf}"
            + (f"; {ultimo + 1} a {fim_est}: {fonte_ibge}" if estendida else ""),
            intervalos=intervalos,
            nota=(
                "A produtividade total dos fatores é o que o país produz além do que explicam "
                "as máquinas e prédios, as horas trabalhadas e o estudo de quem trabalha: "
                "tecnologia, organização, alocação. A PWT a calcula como o resto da conta, "
                f"então ela carrega o ciclo. Atualizada a cada dois anos, mais ou menos; vai "
                f"até {ultimo}." + (nota_est if estendida else "")
            ),
        ),
        grafico(
            "ptf-paises",
            "PTF contra a dos EUA",
            [
                serie(cod.lower(), nome, relativa[cod], casas=1)
                for cod, nome in PAISES_PTF.items()
                if relativa.get(cod)
            ],
            unidade="% da PTF dos EUA",
            casas=0,
            periodicidade="A",
            fonte=fonte_rel,
            nota=(
                "O nível da PTF de cada país em % da dos EUA no mesmo ano, com os preços "
                "convertidos pela paridade do poder de compra. Compara o nível entre países; "
                "para a trajetória de um país só, o índice de PTF (rtfpna) é o certo."
            ),
        ),
    ]
    tabela = Tabela(
        id="pwt-contabilidade",
        titulo="De onde veio o crescimento, década a década",
        subtitulo=(
            f"Média por ano, em pontos percentuais (pp); {decadas[0][0].split()[0]} a {ultimo}"
        ),
        colunas=["PIB", "Capital", "Horas", "Capital humano", "PTF"],
        linhas=[
            LinhaTabela(
                rotulo=rotulo,
                valores=[m.pib, m.capital, m.horas, m.escolaridade, m.ptf],
                unidade="",
                casas=1,
            )
            for rotulo, m in decadas
        ]
        + (
            [
                LinhaTabela(
                    rotulo=f"{ultimo + 1} a {fim_est}, estimativa nossa",
                    valores=[
                        sum(getattr(x.parcela, c) for x in estendida) / len(estendida)
                        for c in ("pib", "capital", "horas", "escolaridade", "ptf")
                    ],
                    unidade="",
                    casas=1,
                )
            ]
            if estendida
            else []
        ),
        fonte=fonte_conta + (f"; {ultimo + 1} a {fim_est}: {fonte_ibge}" if estendida else ""),
        nota=(
            "Capital, horas trabalhadas e capital humano somam o crescimento que as máquinas e "
            "prédios, o trabalho e o estudo explicam, cada um pesado pela sua parte na renda; "
            "a PTF é o que sobra, e as quatro somam o PIB (em log). Capital humano é o índice "
            "da PWT "
            "(anos de estudo e o retorno de cada ano). A PTF da própria PWT difere da daqui em "
            f"até {br(diferenca, 1)} pp por ano nas médias. Depois de 2020 as horas sobem com "
            "a volta da pandemia." + aviso_labsh
        ),
    )
    return cartoes, graficos, tabela


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
