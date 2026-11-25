"""Produtividade e eficiência: o PIB por pessoa ocupada e por hora, de onde veio o
crescimento e a produtividade total dos fatores (PTF) da Penn World Table.

Morava em Demografia; foi para Atividade (Caio, 15/11/2026: *"eficiência e produtividade
deveriam ficar em Atividade"*). A produtividade por hora é cálculo próprio: PIB em volume sobre as
horas habituais da PNAD (ocupados × horas por semana). A PTF depois do último ano da PWT é
estimativa nossa, pela conta da PWT com os números do IBGE.
"""

from __future__ import annotations

import math
from datetime import date
from itertools import pairwise
from typing import NamedTuple

from sacibras import contas
from sacibras.fontes import ibge_sidra, pwt
from sacibras.schema import Cartao, Grafico, Intervalo, LinhaTabela, Tabela
from sacibras.secoes.base import br, cartao, grafico, periodo, serie
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
PAISES_PTF = {"BRA": "Brasil"}
"""A PTF contra a dos EUA, na tela, é só a do Brasil; os outros países ficam em Brasil no mundo
(Caio, 15/11/2026: *"ou deixe só contra os EUA mesmo"*)."""


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


RENDIMENTO = (6390, 5933)
"""PNAD Contínua, rendimento médio real habitual de todos os trabalhos (R$, a preços do último
mês), trimestre móvel; a mesma série da seção Trabalho."""


def rendimento_e_produto(
    por_ocupado: list[Ponto], rendimento: list[Ponto]
) -> tuple[list[Ponto], list[Ponto]]:
    """(produto por ocupado, rendimento real), os dois com 100 na primeira janela de quatro
    trimestres em que há os dois, nas mesmas datas."""
    renda_4t = dict(contas.media_movel(rendimento, 4))
    datas = [d for d, _ in por_ocupado if d in renda_4t]
    produto = dict(por_ocupado)
    return (
        contas.base_100([(d, produto[d]) for d in datas]),
        contas.base_100([(d, renda_4t[d]) for d in datas]),
    )


def grafico_rendimento_e_produto(por_ocupado: list[Ponto]) -> Grafico | None:
    rendimento = trimestre_civil(ibge_sidra.serie(*RENDIMENTO))
    produto, renda = rendimento_e_produto(por_ocupado, rendimento)
    if not produto:
        return None
    quando = produto[-1][0]
    return grafico(
        "rendimento-produtividade",
        "Rendimento do trabalho e produto por ocupado",
        [
            serie("produto", "PIB por ocupado", produto, casas=1),
            serie("rendimento", "Rendimento real do trabalho", renda, casas=1),
        ],
        unidade="índice, 2012 = 100",
        casas=1,
        periodicidade="T",
        manchete=(
            f"Desde 2012, o PIB por ocupado mudou {br(produto[-1][1] - 100)} % e o "
            f"rendimento real, {br(renda[-1][1] - 100)} % (até o {periodo(quando, 'T')})."
        ),
        fonte=(
            f"IBGE, Contas Nacionais Trimestrais (SIDRA {PIB_VOLUME[0]}) e PNAD Contínua "
            f"(SIDRA {OCUPADOS[0]} e {RENDIMENTO[0]}); cálculo próprio"
        ),
        # O rendimento é o habitual de todos os trabalhos, descontada a inflação pelo IBGE. No
        # longo prazo, o salário só cresce de forma duradoura se cada trabalhador produz mais.
        nota=(
            "Médias de quatro trimestres, 100 em 2012 (início da PNAD). Em prazos curtos os dois "
            "se afastam: em 2020, a média subiu porque quem ganhava menos perdeu o emprego."
        ),
    )


def por_hora(pib: list[Ponto], ocupados: list[Ponto], horas: list[Ponto]) -> list[Ponto]:
    """PIB de quatro trimestres sobre as horas trabalhadas dos mesmos quatro (ocupados × horas
    por semana, na média), com 100 na primeira janela completa."""
    horas_por_tri = dict(horas)
    total = [(d, v * horas_por_tri[d]) for d, v in ocupados if d in horas_por_tri]
    pib_4t = dict(contas.soma_movel(pib, 4))
    horas_4t = dict(contas.media_movel(total, 4))
    datas = sorted(set(pib_4t) & set(horas_4t))
    return contas.base_100([(d, pib_4t[d] / horas_4t[d]) for d in datas])


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


def pecas() -> tuple[list[Cartao], list[Grafico], list[Tabela]]:
    """Os cartões, gráficos e tabelas da produtividade e da eficiência (Atividade)."""
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
        print(f"    horas da PNAD ficaram de fora da produtividade: {str(erro)[:120]}")
        hora = []

    cartoes: list[Cartao] = [
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
            secao="atividade",
            mini=40,
        ),
    ]
    fonte_hora = (
        f"{fonte_prod}; horas: PNAD Contínua (SIDRA {HORAS[0]}, horas habituais em todos os "
        "trabalhos); cálculo próprio"
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
                secao="atividade",
                mini=40,
            )
        )

    graficos: list[Grafico] = [
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
            # Somas de quatro trimestres: o PIB em volume e a média de ocupados. Por hora: o PIB
            # dividido pelas horas da média de quatro trimestres, cada uma os ocupados vezes as
            # horas que costumam trabalhar por semana (cálculo próprio).
            nota=(
                "Quatro trimestres, 100 em 2012 (início da PNAD). "
                + (
                    "Por hora, cálculo próprio com as horas habituais: férias, faltas e hora extra "
                    "não entram."
                    if hora
                    else "É produto por pessoa, não por hora trabalhada."
                )
            ),
        ),
    ]
    try:
        g_renda = grafico_rendimento_e_produto(prod["por_ocupado"])
        if g_renda:
            graficos.append(g_renda)
    except Exception as erro:  # a conta a mais não derruba a seção
        print(f"  aviso: produtividade sem o rendimento ao lado: {str(erro)[:120]}")
    if decomposicao:
        graficos.append(
            grafico(
                "crescimento-decomposto",
                "Crescimento: mais gente ou mais produto por pessoa",
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
                # PIB em volume, média anual de ocupados; repartição pelos logaritmos. Na
                # pandemia, quem perdeu o trabalho saiu da conta e voltou depois.
                nota=(
                    "As duas partes somam o crescimento do PIB no ano (cálculo próprio). De 2020 a "
                    "2022 a pandemia distorce a conta."
                ),
            )
        )
    tabelas: list[Tabela] = []
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
        tabelas.append(t_pwt)
    except Exception as erro:  # a PWT fora do ar não derruba a seção
        print(f"    a Penn World Table ficou de fora: {str(erro)[:120]}")
    return cartoes, graficos, tabelas


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
    fonte_conta = (
        f"{pwt.FONTE}: rgdpna, rnna, emp, avh, hc e labsh; cálculo próprio pelo método da PWT"
    )
    decadas = periodos(parcelas)
    # A PTF daqui contra a da PWT, nas médias de cada período: max(abs(m.ptf - m.ptf_pwt)).
    repetidos = anos_repetidos(brasil, "labsh")
    aviso_labsh = (
        f" A PWT repete a parte do trabalho na renda de {repetidos[0] - 1} em "
        f"{' e '.join(str(a) for a in repetidos)}."
        if repetidos
        else ""
    )

    estendida = estender_ptf(brasil, insumos) if insumos else []
    if estendida:
        erro, _vies, _desde = conferir_ptf(brasil, insumos)  # type: ignore[arg-type]
        fim_est = estendida[-1].ano
        fonte_ibge = (
            f"IBGE: Contas Trimestrais (SIDRA {PIB_VOLUME[0]}, PIB e FBCF) e PNAD Contínua "
            f"(SIDRA {OCUPADOS[0]}, ocupados; {HORAS_EFETIVAS[0]}, horas efetivas; "
            f"{ESTUDO[0]}, anos de estudo); cálculo próprio"
        )
        fonte_est = f"{fonte_ibge}, emendada na {pwt.FONTE.split(' (')[0]} de {ultimo}"
        # A estimativa é a mesma conta da PWT com os números do IBGE (PIB, investimento,
        # ocupados, horas efetivas e anos de estudo da PNAD), emendada no último ano da PWT.
        # Feita nos anos em que a PWT existe, repete a PTF dela desde `_desde` com o erro médio
        # `erro`; o estudo da PNAD sobe mais devagar que o da PWT, e com ele a PTF sai em média
        # `_vies` pp por ano mais alta. A barra vai até a PTF com o capital humano no ritmo dos
        # últimos cinco anos da PWT.
        nota_est = (
            f" De {ultimo + 1} a {fim_est}, estimativa nossa com o IBGE, que nos anos da PWT "
            f"erra em média {br(erro, 1)} pp por ano."
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
            secao="atividade",
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
            secao="atividade",
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
                secao="atividade",
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
            # A PTF é o que o país produz além do que explicam as máquinas e prédios, as horas
            # trabalhadas e o estudo: tecnologia, organização, alocação. A PWT sai a cada dois
            # anos, mais ou menos.
            nota=(
                "O que o país produz além de capital, horas e estudo; como é o resto da conta, "
                "carrega o ciclo." + (nota_est if estendida else "")
            ),
        ),
        grafico(
            "ptf-paises",
            "PTF do Brasil contra a dos EUA",
            [
                serie(cod.lower(), nome, relativa[cod], casas=1)
                for cod, nome in PAISES_PTF.items()
                if relativa.get(cod)
            ],
            unidade="% da PTF dos EUA",
            casas=0,
            periodicidade="A",
            fonte=fonte_rel,
            # Os outros países estão em Brasil no mundo; para a trajetória do Brasil, o certo é o
            # índice de PTF (rtfpna).
            nota=(
                "Nível da PTF do Brasil em % da dos EUA, a paridade de poder de compra. Para a "
                "trajetória, veja o índice de PTF."
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
        # Capital humano é o índice da PWT (anos de estudo e o retorno de cada ano). A PTF da
        # própria PWT difere da daqui nas médias de cada período (ver o comentário acima).
        # Depois de 2020 as horas sobem com a volta da pandemia.
        nota=(
            "Cada fator pesado pela sua parte na renda; a PTF é o que sobra, e as quatro somam "
            "o PIB (em log)." + aviso_labsh
        ),
    )
    return cartoes, graficos, tabela
