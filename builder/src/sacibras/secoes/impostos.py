"""Impostos: quanto se arrecada, sobre o que, quanto se deixa de arrecadar e a carga contra o
crescimento, país a país.

Pedido do Caio (14/11/2026): *"estou sentindo falta de alguma sessão sobre impostos, ou
impacto de impostos no crescimento"*. Das quatro peças oferecidas para o crescimento, ele
escolheu as quatro: a composição da carga (com outros países), a carga contra o crescimento
(um ponto por país, com o aviso de que andar junto não é causa), os multiplicadores lidos em
estudo oficial e o gasto tributário. Os multiplicadores e a incidência por décimo de renda
saíram em 15/11/2026: eram estudos de uma vez só (Caio: só o que sai com regularidade).

Fontes: a arrecadação federal mês a mês vem da Receita (CSV por UF e tributo); a carga
tributária e a composição, da OCDE (Global Revenue Statistics: o mesmo método para ~145
países, Brasil até 2024); o crescimento por habitante, do WEO do FMI; o FPE e o FPM de cada
estado, das transferências constitucionais do Tesouro. Na reforma do consumo, o Imposto
Seletivo, o Simples e a ida do IBS para o destino saem da lei lida (`leis.py`).

O ICMS de hoje por estado (a alíquota modal de cada uma das 27 leis) fica de fora: não há
tabela oficial consolidada que abra daqui (o site do Confaz não respondeu em 15/11/2026), e o
quanto cada estado ganha ou perde com a cobrança no destino não tem número oficial publicado.
"""

from __future__ import annotations

import gettext
import math
from collections.abc import Callable
from datetime import date

import pycountry

from sacibras import contas, leis, relatorios
from sacibras.contas import a_precos_de, indice_de_precos
from sacibras.fontes import (
    avaliacao_bimestral,
    fmi,
    fmi_cofog,
    ocde_receita,
    receita_arrecadacao,
    receita_gastos,
    receita_irpf,
    siconfi,
    tesouro_rtn,
    tesouro_transferencias,
)
from sacibras.fontes.ocde_receita import BASES, ESFERAS
from sacibras.fontes.receita_arrecadacao import COMPLETO_DESDE, NOMES
from sacibras.schema import (
    Cartao,
    Dispersao,
    EixoDispersao,
    EtapaDaReforma,
    Grafico,
    LinhaTabela,
    MarcaDeAliquota,
    PontoDispersao,
    Procedencia,
    Secao,
    SimuladorReforma,
    Tabela,
    TipoDeCompra,
)
from sacibras.secoes.base import (
    Contexto,
    br,
    cartao,
    com_variantes,
    grafico,
    periodo,
    serie,
    variante,
)
from sacibras.secoes.estados import UFS
from sacibras.secoes.mundo import nome_do_pais
from sacibras.tipos import Ponto

# Os seis grupos do gráfico (seis cores de série); os pequenos vão juntos em "Outros".
GRUPOS_DO_GRAFICO = ["ir", "cofins_pis", "previdencia", "csll", "ipi"]
JUNTOS = ["iof", "comercio", "outros"]

AGREGADOS = {"OECD_REP": "Média da OCDE", "A9": "América Latina e Caribe"}
# Para a tabela de composição: os vizinhos e os grandes, como em Brasil no mundo.
COMPARAR = ["ARG", "CHL", "COL", "MEX", "USA", "DEU", "FRA", "GBR", "JPN", "KOR", "ZAF", "CHN"]
ANOS_DA_DISPERSAO = 10
"""A carga média e o crescimento médio por habitante nos mesmos dez anos."""
MINIMO_DE_ANOS = 8
"""País com menos anos que isso, nos dez, fica fora do gráfico."""


Pecas = tuple[list[Cartao], list[Grafico], list[Tabela], str]

# ------------------------------------------------------------------ contas


def variacao_em_12m(soma_12m: list[Ponto]) -> list[Ponto]:
    """A soma de 12 meses contra a dos 12 meses anteriores, em %."""
    return contas.variacao(soma_12m, 12)


def media(valores: list[float]) -> float:
    return sum(valores) / len(valores)


def media_geometrica_da_variacao(nivel: dict[int, float], anos: list[int]) -> float | None:
    """A variação média por ano, em %, do nível do ano antes do primeiro até o último."""
    inicio, fim = anos[0] - 1, anos[-1]
    if inicio not in nivel or fim not in nivel or nivel[inicio] <= 0:
        return None
    razao: float = nivel[fim] / nivel[inicio]
    return float((razao ** (1 / (fim - inicio)) - 1) * 100)


def correlacao(xs: list[float], ys: list[float]) -> float:
    mx, my = media(xs), media(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    vx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    vy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return cov / (vx * vy) if vx and vy else 0.0


def em_palavras(r: float) -> str:
    forca = abs(r)
    if forca < 0.1:
        return "praticamente nenhuma relação"
    if forca < 0.3:
        return "relação fraca"
    if forca < 0.5:
        return "relação moderada"
    return "relação forte"


def _pontos_anuais(por_ano: dict[int, float]) -> list[Ponto]:
    return [(date(a, 1, 1), v) for a, v in sorted(por_ano.items())]


def _nomes() -> gettext.NullTranslations:
    return gettext.translation(
        "iso3166-1", pycountry.LOCALES_DIR, languages=["pt_BR"], fallback=True
    )


# ------------------------------------------------------------------ partes


def _arrecadacao(
    ctx: Contexto,
) -> tuple[list[Cartao], list[Grafico], list[Tabela], str]:
    dados = receita_arrecadacao.arrecadacao()
    br_ = {g: [(d, v) for d, v in ufs["BR"] if d >= COMPLETO_DESDE] for g, ufs in dados.items()}
    total_mensal: dict[date, float] = {}
    for pontos in br_.values():
        for d, v in pontos:
            total_mensal[d] = total_mensal.get(d, 0.0) + v
    total = sorted(total_mensal.items())
    ultimo = total[-1][0]
    indice = indice_de_precos(ctx.sgs("IPCA", 16))
    base = max(d for d in indice if d <= ultimo)
    quando = periodo(base, "M")
    fonte = f"{receita_arrecadacao.FONTE}; IPCA: {ctx.fonte_sgs('IPCA')}"
    fonte_pib = f"{receita_arrecadacao.FONTE}; PIB: {ctx.fonte_sgs('PIB_12M')}"

    def real_12m(mensal: list[Ponto]) -> list[Ponto]:
        return [(d, v / 1e9) for d, v in contas.soma_movel(a_precos_de(mensal, indice, base))]

    total_real = real_12m(total)
    cresc = variacao_em_12m(total_real)
    pib = ctx.sgs("PIB_12M", 16)

    def pct_pib(mensal: list[Ponto]) -> list[Ponto]:
        return contas.em_pct_do_pib([(d, v / 1e6) for d, v in mensal], pib)

    total_pib = pct_pib(total)
    juntos_mensal: dict[date, float] = {}
    for g in JUNTOS:
        for d, v in br_.get(g, []):
            juntos_mensal[d] = juntos_mensal.get(d, 0.0) + v

    cartoes = [
        cartao(
            "arrecadacao-12m",
            "Arrecadação federal, 12 meses",
            total_real,
            unidade="R$ bi",
            casas=0,
            periodicidade="M",
            detalhe=f"a preços de {quando}, pelo IPCA",
            fonte=fonte,
            procedencia="calculado",
            secao="impostos",
            mini=120,
        ),
        cartao(
            "arrecadacao-real",
            "Arrecadação federal, crescimento real",
            cresc,
            unidade="% em 12 meses",
            casas=1,
            periodicidade="M",
            detalhe="12 meses contra os 12 anteriores, descontada a inflação",
            fonte=fonte,
            procedencia="calculado",
            secao="impostos",
            mini=120,
        ),
    ]
    if total_pib:
        cartoes.append(
            cartao(
                "arrecadacao-pib",
                "Arrecadação federal, % do PIB",
                total_pib,
                unidade="% do PIB",
                casas=1,
                periodicidade="M",
                detalhe="soma de 12 meses sobre o PIB de 12 meses",
                fonte=fonte_pib,
                procedencia="calculado",
                secao="impostos",
                mini=120,
            )
        )

    graficos = [
        grafico(
            "arrecadacao-12m",
            "Arrecadação federal em 12 meses, descontada a inflação",
            [serie("total", "Arrecadação federal", total_real, casas=1)],
            unidade=f"R$ bilhões de {quando}",
            casas=0,
            periodicidade="M",
            fonte=fonte,
            # A série começa em 2013: antes, o arquivo da Receita não traz a previdência por
            # estado.
            nota=(
                "Tudo o que a Receita arrecada, INSS incluído, a preços de hoje pelo IPCA. "
                "Começa em 2013, quando o arquivo passa a trazer o INSS."
            ),
        )
    ]
    graficos[0] = com_variantes(
        graficos[0],
        "R$ de hoje",
        *(
            [
                variante(
                    "pib",
                    "% do PIB",
                    "Arrecadação federal em 12 meses, em % do PIB",
                    [serie("total", "Arrecadação federal", total_pib, casas=2)],
                    unidade="% do PIB",
                    periodicidade="M",
                    nota="Soma de 12 meses sobre o PIB dos mesmos meses.",
                    fonte=fonte_pib,
                )
            ]
            if total_pib
            else []
        ),
        variante(
            "crescimento",
            "Crescimento real",
            "Arrecadação federal: crescimento real em 12 meses",
            [serie("total", "Arrecadação federal", cresc, casas=2)],
            unidade="% em 12 meses",
            periodicidade="M",
            nota="12 meses contra os 12 anteriores, a preços de hoje. Negativo é queda real.",
        ),
    )
    graficos += [
        grafico(
            "arrecadacao-tributos",
            "Os maiores tributos federais",
            [
                *[
                    serie(g, NOMES[g], pct_pib(br_[g]), casas=2)
                    for g in GRUPOS_DO_GRAFICO
                    if g in br_
                ],
                serie(
                    "outros",
                    "IOF, comércio exterior e outros",
                    pct_pib(sorted(juntos_mensal.items())),
                    casas=2,
                ),
            ],
            unidade="% do PIB, em 12 meses",
            casas=1,
            periodicidade="M",
            fonte=fonte_pib,
            nota="IR: pessoas, empresas e retido na fonte. INSS: empresas e trabalhadores.",
        ),
    ]
    graficos[-1] = com_variantes(
        graficos[-1],
        "% do PIB",
        variante(
            "reais",
            "R$ de hoje",
            "Os maiores tributos federais, em reais de hoje",
            [
                *[
                    serie(g, NOMES[g], real_12m(br_[g]), casas=1)
                    for g in GRUPOS_DO_GRAFICO
                    if g in br_
                ],
                serie(
                    "outros",
                    "IOF, comércio exterior e outros",
                    real_12m(sorted(juntos_mensal.items())),
                    casas=1,
                ),
            ],
            unidade=f"R$ bilhões de {quando}, em 12 meses",
            casas=0,
            periodicidade="M",
            nota="Soma de 12 meses, a preços de hoje pelo IPCA. IR inclui o retido na fonte.",
            fonte=fonte,
        ),
    )

    # Tabela: cada grupo, em R$ bi de 12 meses, % do PIB e crescimento real.
    linhas: list[LinhaTabela] = []
    ordem = sorted(
        br_,
        key=lambda g: -(real_12m(br_[g])[-1][1] if real_12m(br_[g]) else 0),
    )
    for g in ordem:
        r = real_12m(br_[g])
        if not r:
            continue
        var = variacao_em_12m(r)
        no_pib = pct_pib(br_[g])
        linhas.append(
            LinhaTabela(
                rotulo=NOMES[g],
                valores=[
                    round(r[-1][1], 1),
                    round(no_pib[-1][1], 2) if no_pib else None,
                    round(var[-1][1], 1) if var else None,
                ],
                unidade="",
                casas=1,
            )
        )
    linhas.append(
        LinhaTabela(
            rotulo="Total",
            valores=[
                round(total_real[-1][1], 1),
                round(total_pib[-1][1], 2) if total_pib else None,
                round(cresc[-1][1], 1) if cresc else None,
            ],
            unidade="",
            casas=1,
        )
    )
    tabelas = [
        Tabela(
            id="arrecadacao-tributos",
            titulo="Arrecadação por tributo",
            subtitulo=f"12 meses até {periodo(ultimo, 'M')}",
            colunas=[f"R$ bi de {quando}", "% do PIB", "crescimento real, %"],
            linhas=linhas,
            fonte=fonte_pib,
            nota="Crescimento real: 12 meses contra os 12 anteriores.",
        )
    ]
    frase = (
        f"A Receita arrecadou R$ {br(total_real[-1][1] / 1000, 2)} tri nos 12 meses até "
        f"{periodo(ultimo, 'M')}, a preços de hoje"
    )
    if cresc:
        frase += f", {br(abs(cresc[-1][1]))} % {'a mais' if cresc[-1][1] >= 0 else 'a menos'}"
        frase += " que nos 12 anteriores, sem a inflação"
    return cartoes, graficos, tabelas, frase + "."


def _por_estado(ctx: Contexto) -> tuple[list[Cartao], list[Grafico], list[Tabela], str]:
    """A arrecadação federal dos 12 meses por UF, no total e por habitante."""
    por_uf, ultimo = receita_arrecadacao.doze_meses_por_uf(receita_arrecadacao.arrecadacao())
    populacao = siconfi.entes()
    total = sum(por_uf.values())
    linhas: list[tuple[float, LinhaTabela]] = []
    for codigo, sigla, nome, _ in UFS:
        valor, pop = por_uf.get(sigla), populacao.get(codigo)
        if valor is None or not pop:
            continue
        linhas.append(
            (
                valor / pop,
                LinhaTabela(
                    rotulo=nome,
                    valores=[
                        round(valor / pop / 1e3, 1),
                        round(valor / 1e9, 1),
                        round(valor / total * 100, 1),
                    ],
                    unidade="",
                    casas=1,
                ),
            )
        )
    linhas.sort(key=lambda x: -x[0])
    tabela = Tabela(
        id="arrecadacao-estados",
        titulo="Arrecadação federal por estado",
        subtitulo=f"12 meses até {periodo(ultimo, 'M')}, do maior ao menor por habitante",
        colunas=["R$ mil por habitante", "R$ bi", "% do país"],
        linhas=[linha for _, linha in linhas],
        fonte=(
            f"{receita_arrecadacao.FONTE}; população: Tesouro Nacional, cadastro de entes do "
            "SICONFI (estimativa do IBGE)"
        ),
        # O DF (órgãos federais e estatais), SP e RJ (sedes de empresas e bancos) aparecem
        # com mais do que a economia local explicaria.
        nota=(
            "Conta no estado do endereço fiscal de quem paga, o que infla DF, SP e RJ. O ICMS "
            "por habitante está em Estados."
        ),
    )
    return [], [], [tabela], ""


def _carga(ctx: Contexto) -> tuple[list[Cartao], list[Grafico], list[Tabela], str]:
    base = ocde_receita.carga(["BRA", *AGREGADOS, *COMPARAR], ["S13"], inicio=2000)
    esferas = ocde_receita.carga(["BRA"], list(ESFERAS), ["_T"], inicio=2000)
    fonte = ocde_receita.FONTE

    def de(pais: str, cat: str = "_T", setor: str = "S13") -> dict[int, float]:
        return (base if setor == "S13" else esferas).get((pais, setor, cat), {})

    total_br = de("BRA")
    ultimo = max(total_br)
    # A OCDE publica a parte de cada base na carga; sem ela, a mesma divisão feita aqui.
    try:
        consumo = ocde_receita.carga(["BRA"], ["S13"], ["T_5000"], unidade="PT_OTR_SECTOR")[
            ("BRA", "S13", "T_5000")
        ]
        proc_consumo: Procedencia = "oficial"
    except Exception as erro:
        print(f"  aviso: impostos: parte do consumo da OCDE indisponível ({str(erro)[:100]})")
        consumo = {a: de("BRA", "T_5000")[a] / v * 100 for a, v in total_br.items() if v}
        proc_consumo = "calculado"

    cartoes = [
        cartao(
            "carga-tributaria",
            "Carga tributária",
            _pontos_anuais(total_br),
            unidade="% do PIB",
            casas=1,
            periodicidade="A",
            detalhe=(
                f"União, estados, municípios e INSS; média da OCDE: "
                f"{br(de('OECD_REP').get(ultimo, math.nan))} %"
            ),
            fonte=fonte,
            secao="impostos",
            mini=30,
        ),
        cartao(
            "carga-consumo",
            "Parte da carga sobre bens e serviços",
            _pontos_anuais(consumo),
            unidade="% da carga",
            casas=0,
            periodicidade="A",
            detalhe="ICMS, ISS, IPI, Cofins, PIS e afins",
            fonte=fonte,
            procedencia=proc_consumo,
            secao="impostos",
            mini=30,
        ),
    ]
    graficos = [
        grafico(
            "carga-tributaria",
            "Carga tributária: Brasil, OCDE e América Latina",
            [
                serie("bra", "Brasil", _pontos_anuais(total_br)),
                serie("ocde", "Média da OCDE", _pontos_anuais(de("OECD_REP"))),
                serie("al", "América Latina e Caribe", _pontos_anuais(de("A9"))),
            ],
            unidade="% do PIB",
            casas=1,
            periodicidade="A",
            fonte=fonte,
            nota=(
                "Todo o governo, no método da OCDE, igual para todos os países. O número da "
                "Receita sai um pouco diferente."
            ),
        ),
        grafico(
            "carga-composicao",
            "Sobre o que o Brasil cobra",
            [
                serie(c, BASES[c], _pontos_anuais(de("BRA", c)))
                for c in ["T_5000", "T_1000", "T_2000", "T_4000", "T_3000"]
            ],
            tipo="empilhado",
            unidade="% do PIB",
            casas=1,
            periodicidade="A",
            fonte=fonte,
            # A OCDE põe o IPVA em bens e serviços; o imposto de importação também está lá.
            nota=(
                "Bens e serviços: ICMS, ISS, IPI, PIS e Cofins; renda: IR e CSLL; "
                "contribuições: INSS e previdência dos servidores. Folha: salário-educação e "
                "Sistema S; patrimônio: IPTU, ITBI, ITCMD, ITR e IOF."
            ),
        ),
        grafico(
            "carga-esferas",
            "Quem arrecada",
            [serie(s, nome, _pontos_anuais(de("BRA", "_T", s))) for s, nome in ESFERAS.items()],
            tipo="empilhado",
            unidade="% do PIB",
            casas=1,
            periodicidade="A",
            fonte=fonte,
            nota='Na OCDE, o INSS conta à parte, como "previdência", e não na União.',
        ),
    ]

    # Composição comparada: o último ano em que o Brasil e as duas médias têm a composição
    # (a média da OCDE sai com o total um ano antes da composição).
    paises = ["BRA", *AGREGADOS, *COMPARAR]
    comuns = [
        a for a in sorted(total_br, reverse=True) if all(a in de(p, "T_5000") for p in paises[:3])
    ]
    ano = comuns[0] if comuns else ultimo
    traducao = _nomes()

    def nome(p: str) -> str:
        return "Brasil" if p == "BRA" else AGREGADOS.get(p) or nome_do_pais(p, traducao)

    colunas_cat = ["T_5000", "T_1000", "T_2000", "T_4000"]
    linhas = []
    for p in paises:
        t = de(p).get(ano)
        if t is None:
            continue
        valores: list[float | None] = [round(t, 1)]
        for c in colunas_cat:
            v = de(p, c).get(ano)
            if c == "T_2000":  # contribuições e folha juntas: as duas pesam sobre o salário
                folha = de(p, "T_3000").get(ano)
                v = None if v is None else v + (folha or 0)
            valores.append(None if v is None else round(v / t * 100, 1))
        linhas.append(LinhaTabela(rotulo=nome(p), valores=valores, unidade="", casas=1))
    tabelas = [
        Tabela(
            id="carga-paises",
            titulo="A carga e a composição, Brasil e outros países",
            subtitulo=f"{ano}; carga em % do PIB, bases em % da carga",
            colunas=[
                "carga, % do PIB",
                "bens e serviços, %",
                "renda e lucro, %",
                "salários (INSS e folha), %",
                "patrimônio, %",
            ],
            linhas=linhas,
            fonte=fonte,
            nota=(
                'As bases somam perto de 100 % (o resto é "outros"). Para o crescimento, os '
                "estudos olham mais a composição: imposto sobre lucro e salário tende a pesar "
                "mais que sobre consumo e patrimônio."
            ),
        )
    ]
    frase = (
        f"A carga tributária do Brasil foi de {br(total_br[ultimo])} % do PIB em {ultimo} "
        f"(média da OCDE: {br(de('OECD_REP').get(ultimo, math.nan))} %), e "
        f"{br(consumo[ultimo], 0)} % dela vem de bens e serviços"
    )
    return cartoes, graficos, tabelas, frase + "."


BASES_DETALHADAS = {
    "T_1100": "IR das pessoas",
    "T_1200": "IR e CSLL das empresas",
    "T_5110": "consumo em geral",
    "T_5120": "produtos específicos",
    "salario": "sobre o salário",
}
"""As colunas da tabela de bases contra outros países, códigos da OCDE (o salário soma as
contribuições sociais, T_2000, e a folha, T_3000). Conferido em 15/11/2026 no
`DF_RSGLOBAL`: o Brasil tem todos até 2024, e a média da OCDE e a da América Latina (A9), até
2023."""


def tabela_de_bases(
    dados: ocde_receita.Tabela, paises: list[str], nome: Callable[[str], str]
) -> tuple[int, list[LinhaTabela]]:
    """O ano mais novo em que o Brasil e as duas médias têm o IR das pessoas, e uma linha por
    país com cada base em % do PIB."""

    def de(pais: str, cat: str) -> dict[int, float]:
        return dados.get((pais, "S13", cat), {})

    comuns = sorted(set.intersection(*(set(de(p, "T_1100")) for p in paises[:3])), reverse=True)
    if not comuns:
        raise RuntimeError("OCDE: sem ano comum do IR das pessoas")
    ano = comuns[0]
    linhas = []
    for p in paises:
        valores: list[float | None] = []
        for cat in BASES_DETALHADAS:
            if cat == "salario":
                contrib, folha = de(p, "T_2000").get(ano), de(p, "T_3000").get(ano)
                v = None if contrib is None else contrib + (folha or 0)
            else:
                v = de(p, cat).get(ano)
            valores.append(None if v is None else round(v, 1))
        if any(v is not None for v in valores):
            linhas.append(LinhaTabela(rotulo=nome(p), valores=valores, unidade="", casas=1))
    return ano, linhas


def _bases_paises(ctx: Contexto) -> Pecas:
    """IR das pessoas, consumo e salário em % do PIB, Brasil contra outros países."""
    paises = ["BRA", *AGREGADOS, *COMPARAR]
    categorias = [c for c in BASES_DETALHADAS if c.startswith("T_")] + ["T_2000", "T_3000"]
    dados = ocde_receita.carga(paises, ["S13"], categorias, inicio=ctx.hoje.year - 6)
    traducao = _nomes()

    def nome(p: str) -> str:
        return "Brasil" if p == "BRA" else AGREGADOS.get(p) or nome_do_pais(p, traducao)

    ano, linhas = tabela_de_bases(dados, paises, nome)
    pf = {p: dados.get((p, "S13", "T_1100"), {}) for p in ("BRA", "OECD_REP", "A9")}
    fonte = (
        f"{ocde_receita.FONTE} (que junta o Revenue Statistics da OCDE e o da América Latina e "
        "Caribe, feito com a CEPAL, o CIAT e o BID)"
    )
    cartoes = [
        cartao(
            "ir-pessoas",
            "IR das pessoas físicas",
            _pontos_anuais(pf["BRA"]),
            unidade="% do PIB",
            casas=1,
            periodicidade="A",
            detalhe=(
                f"{ano}: OCDE {br(pf['OECD_REP'][ano])} %, América Latina {br(pf['A9'][ano])} %"
            ),
            fonte=fonte,
            secao="impostos",
            mini=30,
        )
    ]
    tabela = Tabela(
        id="carga-bases-paises",
        titulo="IR, consumo e salário: Brasil e outros países",
        subtitulo=f"{ano}; % do PIB",
        colunas=list(BASES_DETALHADAS.values()),
        linhas=linhas,
        fonte=fonte,
        # IR das pessoas inclui o retido na fonte; mesmo método para todos os países.
        nota=(
            "Consumo em geral: ICMS, IPI, PIS, Cofins e ISS (lá fora, o IVA); produtos "
            "específicos: combustível, bebida, cigarro e importação. Salário: previdência de "
            "quem trabalha e de quem emprega e a folha (salário-educação e Sistema S)."
        ),
    )
    return cartoes, [], [tabela], ""


def _crescimento(ctx: Contexto) -> tuple[list[Grafico], list[Tabela]]:
    """Um ponto por país: carga média e crescimento médio por habitante nos mesmos anos."""
    todos = ocde_receita.carga(None, ["S13"], ["_T"], inicio=ctx.hoje.year - 15)
    carga = {p: v for (p, _, _), v in todos.items() if len(p) == 3}
    weo = fmi.weo([], ["NGDPRPC"], ctx.hoje.year - 16, ctx.hoje.year)
    # O último ano com carga para a maioria dos países fecha a janela.
    contagem: dict[int, int] = {}
    for por_ano in carga.values():
        for a in por_ano:
            contagem[a] = contagem.get(a, 0) + 1
    fim = max(a for a, n in contagem.items() if n >= 0.8 * max(contagem.values()))
    anos = list(range(fim - ANOS_DA_DISPERSAO + 1, fim + 1))
    traducao = _nomes()
    pontos: list[PontoDispersao] = []
    for pais, por_ano in sorted(carga.items()):
        valores = [por_ano[a] for a in anos if a in por_ano]
        nivel = weo.valores.get((pais, "NGDPRPC"), {})
        cresc = media_geometrica_da_variacao(nivel, anos)
        if len(valores) < MINIMO_DE_ANOS or cresc is None:
            continue
        try:
            nome = "Brasil" if pais == "BRA" else nome_do_pais(pais, traducao)
        except KeyError:
            continue
        pontos.append(
            PontoDispersao(chave=pais, nome=nome, x=round(media(valores), 1), y=round(cresc, 2))
        )
    r = correlacao([p.x for p in pontos], [p.y for p in pontos])
    periodo_txt = f"{anos[0]} a {anos[-1]}"
    fonte = f"{ocde_receita.FONTE}; FMI, World Economic Outlook (PIB real por habitante)"
    graficos = [
        Grafico(
            id="carga-crescimento",
            titulo="Carga tributária e crescimento, um ponto por país",
            subtitulo=f"médias de {periodo_txt}",
            unidade="",
            periodicidade="A",
            series=[],
            fonte=fonte,
            largura="inteira",
            dispersao=Dispersao(
                eixo_x=EixoDispersao(nome="Carga tributária média", unidade="% do PIB", casas=1),
                eixo_y=EixoDispersao(
                    nome="Crescimento do PIB por habitante", unidade="% ao ano", casas=1
                ),
                pontos=pontos,
                correlacao=round(r, 2),
            ),
            # País que cresce também pode passar a cobrar mais; o Brasil é um ponto do gráfico.
            nota=(
                f"{len(pontos)} países; correlação de {br(r, 2)} ({em_palavras(r)}). Andar "
                "junto não é causa: país rico tende a cobrar mais e a crescer menos."
            ),
        )
    ]
    return graficos, []


def _gasto_tributario(ctx: Contexto) -> tuple[list[Cartao], list[Grafico], list[Tabela], str]:
    edicoes = receita_gastos.edicoes()
    total: dict[int, float] = {}
    pct: dict[int, float] = {}
    for e in reversed(edicoes):  # da mais velha para a mais nova: a mais nova prevalece
        total.update(e.total)
        pct.update(e.pct_pib)
    nova = edicoes[0]
    ano = max(pct)
    previstos: list[receita_gastos.Previsao] = []
    try:
        previstos = receita_gastos.previsoes(ano)
    except Exception as erro:
        print(f"    impostos: sem o gasto tributário do PLOA ({str(erro)[:120]})")
    fonte = f"{receita_gastos.FONTE} (edição {nova.ano})"
    cartoes = [
        cartao(
            "gasto-tributario",
            "Gasto tributário da União",
            _pontos_anuais(pct),
            unidade="% do PIB",
            casas=1,
            periodicidade="A",
            detalhe=f"R$ {br(total[ano] / 1e9, 0)} bi que a União deixou de arrecadar",
            fonte=fonte,
            secao="impostos",
        )
    ]
    graficos = [
        grafico(
            "gasto-tributario",
            "O que a União deixa de arrecadar",
            [
                serie("gt", "Realizado", _pontos_anuais(pct)),
                *(
                    [
                        serie(
                            "ploa",
                            "Previsto no orçamento",
                            [(date(p.ano, 1, 1), p.pct_pib) for p in previstos],
                            papel="previsao",
                        )
                    ]
                    if previstos
                    else []
                ),
            ],
            tipo="barras",
            unidade="% do PIB",
            casas=1,
            periodicidade="A",
            fonte=fonte + (f"; {receita_gastos.FONTE_PLOA}" if previstos else ""),
            # Realizado: as "bases efetivas" da Receita. Previsto: o que a Receita estimou ao
            # mandar o projeto de orçamento de cada ano ao Congresso.
            nota=(
                "Isenções e regimes especiais federais, sem os de ICMS e ISS; o realizado sai "
                "com dois anos de atraso."
                + (
                    f" Tracejado: o previsto no orçamento (para {previstos[-1].ano}, "
                    f"R$ {br(previstos[-1].total / 1e9, 0)} bi)."
                    if previstos
                    else ""
                )
            ),
        )
    ]
    soma = sum(v for _, v in nova.principais)
    linhas = [
        LinhaTabela(
            rotulo=nome,
            valores=[round(v / 1e9, 1), round(v / soma * 100, 1) if soma else None],
            unidade="",
            casas=1,
        )
        for nome, v in nova.principais[:12]
    ]
    tabelas = [
        Tabela(
            id="gasto-tributario",
            titulo="Os maiores gastos tributários",
            subtitulo=str(nova.ano),
            colunas=["R$ bi", "% do total"],
            linhas=linhas,
            fonte=fonte,
            nota=(
                "Agricultura inclui a cesta básica sem PIS e Cofins. Simples: o que o regime "
                "cobra a menos que as regras gerais."
            ),
        )
    ]
    if nova.regioes:
        soma_regioes = sum(nova.regioes.values())
        tabelas.append(
            Tabela(
                id="gasto-tributario-regioes",
                titulo="O gasto tributário por região",
                subtitulo=str(nova.ano),
                colunas=["R$ bi", "% do total"],
                linhas=[
                    LinhaTabela(
                        rotulo=nome,
                        valores=[round(v / 1e9, 1), round(v / soma_regioes * 100, 1)],
                        unidade="",
                        casas=1,
                    )
                    for nome, v in sorted(nova.regioes.items(), key=lambda x: -x[1])
                ],
                fonte=fonte,
                nota="Região de quem deixou de pagar (sede da empresa ou endereço da pessoa).",
            )
        )
    tabelas += _gasto_por_funcao(nova, fonte)
    frase = (
        f"A União deixou de arrecadar {br(pct[ano])} % do PIB em {ano} com isenções e "
        "regimes especiais"
    )
    return cartoes, graficos, tabelas, frase + "."


def _sigla(nome: str) -> str:
    """ "Contribuição … - COFINS" vira "COFINS"; sem sigla, o próprio nome."""
    return nome.rsplit(" - ", 1)[-1].strip()


def _gasto_por_funcao(nova: receita_gastos.Edicao, fonte: str) -> list[Tabela]:
    """O gasto tributário do último ano por função orçamentária, por benefício e por tributo.

    A Receita não publica por setor de atividade (CNAE) nem por empresa (sigilo fiscal): a
    função é o objetivo do benefício. Soma das funções e dos tributos = o total oficial."""
    tabelas: list[Tabela] = []
    if nova.funcoes:
        total = sum(v for _, v in nova.funcoes)
        grandes, resto = nova.funcoes[:10], nova.funcoes[10:]
        linhas = [(n, v) for n, v in grandes] + (
            [("Demais funções", sum(v for _, v in resto))] if resto else []
        )
        tabelas.append(
            Tabela(
                id="gasto-tributario-funcoes",
                titulo="O gasto tributário por função",
                subtitulo=str(nova.ano),
                colunas=["R$ bi", "% do total"],
                linhas=[
                    LinhaTabela(
                        rotulo=n,
                        valores=[round(v / 1e9, 1), round(v / total * 100, 1)],
                        unidade="",
                        casas=1,
                    )
                    for n, v in linhas
                ],
                fonte=fonte,
                nota=(
                    "Função é o objetivo do benefício, não o setor de quem recebe: a Receita "
                    "não publica por atividade nem por empresa. Inclui pessoas físicas."
                ),
            )
        )
        if nova.beneficios:
            linhas_b: list[LinhaTabela] = []
            for funcao, _ in nova.funcoes[:6]:
                itens = [
                    (n, v) for n, v in nova.beneficios.get(funcao, []) if v > 0 and n != funcao
                ][:3]
                linhas_b += [
                    LinhaTabela(
                        rotulo=f"{funcao}: {n}",
                        valores=[round(v / 1e9, 1), round(v / total * 100, 1)],
                        unidade="",
                        casas=1,
                    )
                    for n, v in itens
                ]
            if linhas_b:
                tabelas.append(
                    Tabela(
                        id="gasto-tributario-beneficios",
                        titulo="Os maiores benefícios de cada função",
                        subtitulo=str(nova.ano),
                        colunas=["R$ bi", "% do total"],
                        linhas=linhas_b,
                        fonte=fonte,
                        nota="As seis maiores funções, três benefícios de cada.",
                    )
                )
    if nova.tributos:
        total_t = sum(v for _, v in nova.tributos)
        tabelas.append(
            Tabela(
                id="gasto-tributario-tributos",
                titulo="O gasto tributário por tributo",
                subtitulo=str(nova.ano),
                colunas=["R$ bi", "% do total"],
                linhas=[
                    LinhaTabela(
                        rotulo=("IRPF (pessoa física)" if _sigla(n) == "IRPF" else _sigla(n)),
                        valores=[round(v / 1e9, 1), round(v / total_t * 100, 1)],
                        unidade="",
                        casas=1,
                    )
                    for n, v in nova.tributos
                    if v >= 1e6
                ],
                fonte=fonte,
                nota=(
                    "O IRPF é de pessoa física; os outros incidem sobretudo sobre empresas, "
                    "mas a Receita não separa quem recebe."
                ),
            )
        )
    return tabelas


# ------------------------------------------------------------------ seção


def _simulador_da_reforma(
    ctx: Contexto,
) -> tuple[list[Cartao], list[Tabela], SimuladorReforma]:
    """A reforma do consumo em números: as contas oficiais da alíquota, os descontos da lei e
    o simulador. O calendário em palavras é a tabela de `_reforma`, mais abaixo.

    Nada aqui é estimativa nossa: as regras saem da emenda e da lei lidas (`leis.py`) e as
    alíquotas, das contas do Comitê Gestor do IBS e do TCU (`relatorios.py`). Nossa
    é só a aritmética (somar e multiplicar), dita onde aparece."""
    r = relatorios
    cbs_2027 = round(r.CBS_REFERENCIA_2027 - leis.CBS_DESCONTO_2027_2028, 2)
    soma_recente = r.IBS_COMITE_GESTOR + r.CBS_REFERENCIA_2027

    cartoes = [
        cartao(
            "reforma-cbs-2027",
            "CBS em 2027",
            [(r.CBS_REFERENCIA_2027_EM, cbs_2027)],
            unidade="%",
            periodicidade="D",
            casas=1,
            detalhe=f"cálculo do TCU ({br(r.CBS_REFERENCIA_2027, 1)} − 0,1); o Senado ainda fixa",
            fonte=f"{r.FONTE_CBS_2027}; ADCT, art. 127, parágrafo único",
            secao="impostos",
        ),
        cartao(
            "reforma-aliquota-cheia",
            "Alíquota cheia de 2033 (IBS + CBS)",
            [(r.ALIQUOTA_COMITE_GESTOR_EM, r.ALIQUOTA_COMITE_GESTOR)],
            unidade="%",
            periodicidade="D",
            casas=1,
            detalhe=f"entre {br(leis.TETO_IBS_CBS, 1)} (teto da lei) e {br(soma_recente, 1)}",
            # O valor é o do Comitê Gestor; só a ponta de cima do detalhe é soma nossa.
            fonte=f"{r.FONTE_ALIQUOTA_COMITE}; {leis.TETO_IBS_CBS_NORMA}; {r.FONTE_CBS_2027}",
            secao="impostos",
        ),
        cartao(
            "reforma-icms-iss",
            f"ICMS e ISS em {ctx.hoje.year + 1}: quanto continua",
            [(date(2023, 12, 20), float(leis.ICMS_ISS_QUE_CONTINUA[ctx.hoje.year + 1]))],
            unidade="%",
            periodicidade="D",
            casas=0,
            detalhe="caem 10 pontos por ano de 2029 a 2032 e acabam em 2033",
            fonte="Emenda Constitucional nº 132/2023 (ADCT, arts. 128 e 129)",
            secao="impostos",
        ),
    ]

    estimativas = Tabela(
        id="reforma-aliquota",
        titulo="A alíquota cheia de 2033: as contas oficiais",
        subtitulo="IBS mais CBS sem desconto; o número final ainda não existe",
        colunas=["Estimativa"],
        linhas=[
            LinhaTabela(
                rotulo="Comitê Gestor do IBS, jul/2026",
                valores=[r.ALIQUOTA_COMITE_GESTOR],
                unidade="%",
                casas=2,
            ),
            LinhaTabela(
                rotulo="IBS do Comitê Gestor + CBS do TCU",
                valores=[round(soma_recente, 2)],
                unidade="%",
                casas=2,
            ),
            LinhaTabela(
                rotulo="Teto da lei",
                valores=[leis.TETO_IBS_CBS],
                unidade="%",
                casas=2,
            ),
        ],
        fonte=(f"{r.FONTE_ALIQUOTA_COMITE}; {r.FONTE_CBS_2027}; {leis.TETO_IBS_CBS_NORMA}"),
        # O Comitê Gestor refaz a conta todo ano; o número definitivo só sai no fim da
        # transição. A CBS do TCU para 2027 ficou acima da estimativa anterior
        # (relatorios.CBS_ESTIMATIVA_ANTERIOR), e a CBS de 2033 pode ser outra. O teto vale
        # pela estimativa de 2030 para 2033.
        nota=(
            "A alíquota cheia repõe a arrecadação que sai: quanto mais desconto, mais alta "
            f"para o resto. Somar a CBS do TCU ({br(r.CBS_REFERENCIA_2027, 1)} %) ao IBS do "
            f"Comitê ({br(r.IBS_COMITE_GESTOR, 1)} %) é cálculo próprio; acima do teto, o governo "
            "tem de propor ao Congresso como voltar a ele."
        ),
    )

    tipos = [
        TipoDeCompra(
            id="cheia",
            rotulo="Compra comum, sem desconto",
            descricao="A maioria das compras e serviços",
            paga=100.0,
            volta_cbs=leis.DEVOLUCAO_GERAL,
            volta_ibs=leis.DEVOLUCAO_GERAL,
            norma="LC nº 214/2025, arts. 14 e 118, II",
        ),
        TipoDeCompra(
            id="contas",
            rotulo="Conta de luz, água, gás, telefone",
            descricao="Luz, água, esgoto, gás e telefone",
            paga=100.0,
            volta_cbs=leis.DEVOLUCAO_CBS_CONTAS_DE_CASA,
            volta_ibs=leis.DEVOLUCAO_IBS_CONTAS_DE_CASA,
            norma="LC nº 214/2025, art. 118, I",
        ),
        TipoDeCompra(
            id="menos-60",
            rotulo="Saúde, educação, alimento (−60 %)",
            descricao="Saúde, educação, remédio, alimento e higiene das listas",
            paga=100.0 - leis.REDUCAO_SAUDE_EDUCACAO_ALIMENTOS,
            volta_cbs=leis.DEVOLUCAO_GERAL,
            volta_ibs=leis.DEVOLUCAO_GERAL,
            norma="LC nº 214/2025, art. 128",
        ),
        TipoDeCompra(
            id="menos-30",
            rotulo="Advogado, engenheiro… (−30 %)",
            descricao="18 profissões com conselho, como advogado e contador",
            paga=100.0 - leis.REDUCAO_PROFISSIONAIS,
            volta_cbs=leis.DEVOLUCAO_GERAL,
            volta_ibs=leis.DEVOLUCAO_GERAL,
            norma="LC nº 214/2025, art. 127",
        ),
        TipoDeCompra(
            id="cesta",
            rotulo="Cesta básica (alíquota zero)",
            descricao="Cesta Básica Nacional, na lista da lei",
            paga=0.0,
            volta_cbs=0.0,
            volta_ibs=0.0,
            norma="LC nº 214/2025, art. 125",
        ),
    ]
    descontos = Tabela(
        id="reforma-descontos",
        titulo="Quem paga menos que a alíquota cheia",
        subtitulo="Descontos da lei e devolução à baixa renda",
        colunas=["Paga da alíquota cheia", "Volta da CBS", "Volta do IBS"],
        linhas=[
            LinhaTabela(
                rotulo=t.descricao, valores=[t.paga, t.volta_cbs, t.volta_ibs], unidade="%", casas=0
            )
            for t in tipos
        ],
        fonte=leis.REFORMA_NORMAS,
        # União, estados e municípios podem devolver mais que o mínimo da lei. Combustíveis,
        # bancos, planos de saúde, imóveis, bares e restaurantes estão na tabela dos regimes.
        nota=(
            "Devolução: à família do Cadastro Único com até meio salário mínimo por pessoa, a "
            f"CBS desde 2027 e o IBS desde {leis.DEVOLUCAO_DO_IBS_DESDE}. O desconto vale só "
            "para as listas da lei, não para todo alimento ou remédio."
        ),
    )

    simulador = SimuladorReforma(
        tipos=tipos,
        etapas=[
            EtapaDaReforma(
                id="2027",
                rotulo="2027 e 2028: entra a CBS",
                cbs=round(cbs_2027, 2),
                ibs=leis.IBS_2027_2028,
                devolve_ibs=False,
                aviso=(
                    "ICMS e ISS seguem inteiros e ficam fora da conta. CBS do TCU; o Senado "
                    "ainda fixa a de 2027."
                ),
            ),
            EtapaDaReforma(
                id="2033",
                rotulo="2033 em diante: sistema inteiro",
                cbs=None,
                ibs=None,
                devolve_ibs=True,
                aviso="Só IBS e CBS no preço; o Imposto Seletivo fica fora da conta.",
            ),
        ],
        etapa_inicial="2033",
        aliquota=round(r.ALIQUOTA_COMITE_GESTOR, 1),
        aliquota_minima=leis.TETO_IBS_CBS,
        aliquota_maxima=round(soma_recente, 1),
        parte_do_ibs=round(r.IBS_COMITE_GESTOR / r.ALIQUOTA_COMITE_GESTOR, 3),
        marcas=[
            MarcaDeAliquota(valor=leis.TETO_IBS_CBS, rotulo="Teto da lei"),
            MarcaDeAliquota(
                valor=round(r.ALIQUOTA_COMITE_GESTOR, 1), rotulo="Comitê Gestor, jul/2026"
            ),
            MarcaDeAliquota(valor=round(soma_recente, 1), rotulo="IBS do Comitê + CBS do TCU"),
        ],
        fonte=(
            f"{leis.REFORMA_NORMAS}; {r.FONTE_ALIQUOTA_COMITE}; {r.FONTE_CBS_2027}; "
            "multiplicações: cálculo próprio"
        ),
        como_ler=(
            "O valor digitado é o preço sem IBS nem CBS. A faixa vai do teto da lei "
            f"({br(leis.TETO_IBS_CBS, 1)} %) à soma das contas oficiais "
            f"({br(soma_recente, 1)} %): a alíquota de 2033 ainda não existe."
        ),
        # A parte que cada compra paga é 100, 70, 40 ou zero % pela lei. Não há número oficial
        # do imposto de hoje por produto (ICMS, ISS, PIS e Cofins se somam de jeitos diferentes
        # em cada estado e cadeia); a reforma foi desenhada para arrecadar o mesmo no total.
        nota=(
            "Imposto = valor × alíquota × a parte que a compra paga; em 2033, o IBS é "
            f"{br(r.IBS_COMITE_GESTOR, 1)} de {br(r.ALIQUOTA_COMITE_GESTOR, 2)} pontos, pela "
            "conta do Comitê Gestor. Não compara com o imposto de hoje (não há número oficial "
            "por produto) e deixa fora os regimes próprios, o Simples e o Seletivo."
        ),
    )
    return cartoes, [estimativas, descontos], simulador


def _por_setor(ctx: Contexto) -> Pecas:
    por_ano = receita_arrecadacao.setores()
    ano = max(por_ano)
    setores = por_ano[ano]
    total = sum(setores.values())
    nomes = {
        "Pessoa Física": "Pessoas físicas (não é setor)",
        "Não informado": "Setor não informado",
    }
    linhas = [
        LinhaTabela(
            rotulo=nomes.get(nome, nome),
            valores=[round(v / 1e9, 1), round(v / total * 100, 1)],
            unidade="",
            casas=1,
        )
        for nome, v in sorted(setores.items(), key=lambda x: -x[1])
        if v / total >= 0.005
    ]
    tabela = Tabela(
        id="arrecadacao-setores",
        titulo="Arrecadação federal por setor da economia",
        subtitulo=f"{ano}, do setor que mais paga ao que menos paga",
        colunas=["R$ bi", "% do total"],
        linhas=linhas,
        fonte="Receita Federal, arrecadação por seção da CNAE (dados abertos)",
        # A administração pública aparece pelo imposto retido dos servidores e pela
        # previdência. Setores com menos de 0,5 % do total ficam fora. Em 2026 a Receita
        # parece ter mudado grandes empresas de setor: por isso só o último ano fechado.
        nota=(
            "O setor é o de quem recolhe, não o de quem arca: a indústria recolhe o que vai no "
            "preço, e o banco, o retido dos clientes. Último ano fechado; em 2026 a Receita "
            "mudou empresas de setor."
        ),
    )
    return [], [], [tabela], ""


def previsto_do_ano(
    lido: avaliacao_bimestral.Quadros | None,
) -> tuple[list[relatorios.ReceitaPrevista], str, str]:
    """(LOA e previsão de cada linha, o bimestre, a fonte): da planilha do bimestre mais novo
    (`lido`) ou, sem ela, dos números lidos à mão."""
    if lido is None or not lido.loa:
        fonte = (
            f"{avaliacao_bimestral.FONTE}, {relatorios.AVALIACAO_DA_RECEITA} de "
            f"{relatorios.ANO_DA_RECEITA_PREVISTA} (quadros de apoio, tabela 1)"
        )
        return relatorios.RECEITA_PREVISTA, relatorios.AVALIACAO_DA_RECEITA, fonte
    ultima = lido.ultima
    lista = [
        relatorios.ReceitaPrevista(r.linha, r.rtn, lido.loa[r.rtn], getattr(ultima, r.rtn))
        for r in relatorios.RECEITA_PREVISTA
    ]
    return lista, ultima.rotulo, lido.fonte


def _previsto(ctx: Contexto, lido: avaliacao_bimestral.Quadros | None = None) -> Pecas:
    """O que entrou no ano contra o que o governo previu arrecadar (relatório bimestral)."""
    rtn = tesouro_rtn.serie_historica()
    ano = relatorios.ANO_DA_RECEITA_PREVISTA
    previstas, bimestre, fonte_aval = previsto_do_ano(lido)
    linhas: list[LinhaTabela] = []
    ate: date | None = None
    for r in previstas:
        no_ano = [(d, v) for d, v in rtn[r.rtn] if d.year == ano]
        antes = {d.month: v for d, v in rtn[r.rtn] if d.year == ano - 1}
        if not no_ano:
            continue
        ate = no_ano[-1][0]
        feito = sum(v for _, v in no_ano) / 1e3
        mesmo_periodo = sum(antes.get(d.month, 0.0) for d, _ in no_ano)
        ano_passado = sum(antes.values())
        linhas.append(
            LinhaTabela(
                rotulo=r.linha,
                valores=[
                    r.loa,
                    r.avaliacao,
                    round(feito, 1),
                    round(feito / r.avaliacao * 100, 1),
                    round(mesmo_periodo / ano_passado * 100, 1) if ano_passado else None,
                ],
                unidade="",
                casas=1,
            )
        )
    if not linhas or ate is None:
        raise RuntimeError(f"RTN sem meses de {ano}")
    meses = f"jan–{periodo(ate, 'M')}"
    tabela = Tabela(
        id="arrecadacao-previsto",
        titulo=f"O previsto para {ano} e o que já entrou",
        subtitulo=f"R$ bilhões; realizado de {meses}",
        colunas=[
            "orçamento",
            f"previsão do {bimestre}",
            f"entrou, {meses}",
            "% da previsão",
            f"% do ano em {ano - 1}, mesmos meses",
        ],
        linhas=linhas,
        fonte=(
            f"{fonte_aval} (orçamento e previsão); Tesouro Nacional, Resultado do Tesouro "
            "Nacional, tabela 1.1 (realizado)"
        ),
        # A previsão desconta incentivos fiscais; o realizado do Tesouro pode ter pequena
        # diferença de conceito. A Receita divulga cada mês entre os dias 21 e 30 do mês
        # seguinte, sem calendário publicado.
        nota=(
            'O governo refaz a previsão a cada dois meses. Se o "% da previsão" está perto '
            "da última coluna, a arrecadação anda no ritmo previsto."
        ),
    )
    return [], [], [tabela], ""


def _divida_ativa(ctx: Contexto) -> Pecas:
    estoque, recuperado = relatorios.DIVIDA_ATIVA_ESTOQUE, relatorios.DIVIDA_ATIVA_RECUPERADO
    anos = sorted(estoque)
    ano = anos[-1]
    cartoes = [
        cartao(
            "divida-ativa",
            "Dívida ativa da União",
            [(date(a, 1, 1), estoque[a] / 1e3) for a in anos],
            unidade="R$ tri",
            casas=2,
            periodicidade="A",
            detalhe=(
                f"dívidas não pagas; {br(relatorios.DIVIDA_ATIVA_PERDA, 0)} % tido como perda"
            ),
            fonte=relatorios.FONTE_DIVIDA_ATIVA,
            secao="impostos",
        )
    ]
    tabela = Tabela(
        id="divida-ativa",
        titulo="O que a União tem a receber e quanto recupera",
        subtitulo="dívida ativa da União, em R$ bilhões",
        colunas=[str(a) for a in anos],
        linhas=[
            LinhaTabela(
                rotulo="Dívida ativa (em cobrança)",
                valores=[estoque[a] for a in anos],
                unidade="",
                casas=1,
            ),
            LinhaTabela(
                rotulo="Recuperado no ano",
                valores=[recuperado.get(a) for a in anos],
                unidade="",
                casas=1,
            ),
            LinhaTabela(
                rotulo="Recuperado, % da dívida",
                valores=[
                    round(recuperado[a] / estoque[a] * 100, 1) if a in recuperado else None
                    for a in anos
                ],
                unidade="",
                casas=1,
            ),
        ],
        fonte=relatorios.FONTE_DIVIDA_ATIVA,
        # A perda é de empresas falidas ou sem bens.
        nota=(
            "Dívida com a União não paga no prazo, cobrada pela Procuradoria da Fazenda. De "
            f"{ano}, o governo conta {br(relatorios.DIVIDA_ATIVA_PERDA, 0)} % como perda e "
            f"espera recuperar R$ {br(relatorios.DIVIDA_ATIVA_A_RECUPERAR, 0)} bi em 15 anos."
        ),
    )
    return cartoes, [], [tabela], ""


def _quem_paga(ctx: Contexto) -> Pecas:
    tabelas: list[Tabela] = []
    frase = ""
    try:
        ano, faixas = receita_irpf.grandes_numeros()
        topo = faixas[-1]
        maior = max(faixas, key=lambda f: f.aliquota)
        tabelas.append(
            Tabela(
                id="quem-paga-irpf",
                titulo="Imposto de Renda por faixa de renda",
                subtitulo=f"declarações de {ano + 1}, renda de {ano}; em salários mínimos",
                colunas=[
                    "declarantes, mil",
                    "renda total, R$ bi",
                    "renda isenta, % da renda",
                    "imposto, % da renda",
                ],
                linhas=[
                    LinhaTabela(
                        rotulo=f.nome,
                        valores=[
                            round(f.declarantes / 1e3, 0),
                            round(f.renda / 1e9, 1),
                            round(f.isentos / f.renda * 100, 1) if f.renda else None,
                            round(f.aliquota, 1),
                        ],
                        unidade="",
                        casas=1,
                    )
                    for f in faixas
                ],
                fonte=f"{receita_irpf.FONTE}, ano-calendário {ano} (tabela 8)",
                # A faixa de até meio salário mínimo tem imposto por rendimentos atrasados
                # recebidos de uma vez. O imposto é o da tabela progressiva da declaração.
                nota=(
                    f"No topo, {br(topo.isentos / topo.renda * 100, 0)} % da renda é isenta "
                    "(boa parte, lucros e dividendos). Imposto da declaração, sem o retido "
                    "sobre 13º, aplicações e ganho de capital, o que diminui a conta no topo; "
                    f"só quem declara ({br(sum(f.declarantes for f in faixas) / 1e6)} milhões)."
                ),
            )
        )
        frase = (
            f"No IR de {ano}, quem declarou mais de 320 salários mínimos pagou "
            f"{br(topo.aliquota)} % da renda, menos que a faixa de "
            f"{maior.nome.lower().removeprefix('de ')} ({br(maior.aliquota)} %)"
        )
    except Exception as erro:
        print(f"    impostos: sem os Grandes Números do IRPF ({str(erro)[:120]})")
    return [], [], tabelas, frase + ("." if frase else "")


def _aliquotas(ctx: Contexto) -> Pecas:
    """O imposto sobre o lucro das empresas, Brasil e outros países (OCDE)."""
    por_pais = ocde_receita.imposto_sobre_lucro(inicio=2000)
    # O último ano com quase todos os países (o ano corrente costuma vir com faltas).
    contagem: dict[int, int] = {}
    for por_ano in por_pais.values():
        for a in por_ano:
            contagem[a] = contagem.get(a, 0) + 1
    ano = max(a for a, n in contagem.items() if n >= 0.97 * max(contagem.values()))
    no_ano = {p: v[ano] for p, v in por_pais.items() if ano in v}
    brasil = no_ano["BRA"]
    acima = sum(1 for v in no_ano.values() if v > brasil)

    def mediana(a: int) -> float | None:
        valores = sorted(v[a] for v in por_pais.values() if a in v)
        if len(valores) < 30:
            return None
        meio = len(valores) // 2
        return valores[meio] if len(valores) % 2 else (valores[meio - 1] + valores[meio]) / 2

    anos = sorted(por_pais["BRA"])
    medianas = [(date(a, 1, 1), m) for a in anos if (m := mediana(a)) is not None]
    traducao = _nomes()
    linhas = [
        LinhaTabela(
            rotulo="Brasil" if p == "BRA" else nome_do_pais(p, traducao),
            valores=[round(no_ano[p], 1)],
            unidade="",
            casas=1,
        )
        for p in sorted(["BRA", *COMPARAR, "IND"], key=lambda p: -no_ano.get(p, -1))
        if p in no_ano
    ]
    linhas.append(
        LinhaTabela(
            rotulo=f"Mediana dos {len(no_ano)} países",
            valores=[round(mediana(ano) or 0, 1)],
            unidade="",
            casas=1,
        )
    )
    fonte = "OCDE, Corporate Tax Statistics (alíquotas legais do imposto sobre o lucro)"
    cartoes = [
        cartao(
            "imposto-lucro",
            "Imposto sobre o lucro das empresas",
            [x for x in _pontos_anuais(por_pais["BRA"]) if x[0].year <= ano],
            unidade="%",
            casas=0,
            periodicidade="A",
            detalhe=f"IRPJ de 25 % mais CSLL de 9 %; {acima} de {len(no_ano)} países cobram mais",
            fonte=fonte,
            secao="impostos",
        )
    ]
    graficos = [
        grafico(
            "imposto-lucro",
            "Imposto sobre o lucro: Brasil e o mundo",
            [
                serie("bra", "Brasil", _pontos_anuais(por_pais["BRA"])),
                serie("mediana", "Mediana dos países", medianas),
            ],
            unidade="% do lucro, alíquota da lei",
            casas=1,
            periodicidade="A",
            fonte=fonte,
            nota=(
                "Alíquota da lei para empresa grande, todas as esferas. Não é o que se paga de "
                "fato (deduções, incentivos, Simples, lucro presumido)."
            ),
        )
    ]
    tabelas = [
        Tabela(
            id="imposto-lucro-paises",
            titulo="Imposto sobre o lucro das empresas, país a país",
            subtitulo=f"alíquota da lei em {ano}, em % do lucro",
            colunas=["alíquota, %"],
            linhas=linhas,
            fonte=fonte,
            nota="Das alíquotas da lei que a OCDE compara, só esta traz o Brasil.",
        )
    ]
    return cartoes, graficos, tabelas, ""


def _reforma(ctx: Contexto) -> Pecas:
    tabela = Tabela(
        id="reforma-linha-do-tempo",
        titulo="A reforma do consumo, ano a ano",
        subtitulo="de 2026 a 2033, pela Emenda Constitucional 132/2023",
        colunas=["O que muda", "Onde está"],
        linhas=[
            LinhaTabela(rotulo=p.quando, valores=[], unidade="", textos=[p.muda, p.norma])
            for p in leis.REFORMA_DO_CONSUMO
        ],
        fonte=(
            "Emenda Constitucional nº 132/2023 (arts. 124 a 133 do ADCT) e Lei Complementar "
            "nº 214/2025, lidas no Senado Federal (publicação original)"
        ),
        # Para 2027, o TCU calculou a CBS (tabela da alíquota cheia). A emenda foi lida na
        # publicação original; a lei complementar, também no texto atualizado.
        nota=(
            "PIS, Cofins, IPI, ICMS e ISS viram a CBS (federal) e o IBS (de estados e "
            "municípios), mais o Imposto Seletivo. As alíquotas cheias ainda não existem: o "
            "Senado fixa cada uma no ano anterior."
        ),
    )
    return [], [], [tabela], ""


def _transferencias(ctx: Contexto) -> Pecas:
    """O FPE e o FPM de cada estado nos 12 meses, ao lado da arrecadação federal dele."""
    fpe, ate_fpe = tesouro_transferencias.doze_meses(tesouro_transferencias.fpe())
    fpm, ate_fpm = tesouro_transferencias.doze_meses(tesouro_transferencias.fpm())
    arrecadado, ate_receita = receita_arrecadacao.doze_meses_por_uf(
        receita_arrecadacao.arrecadacao()
    )
    populacao = siconfi.entes()
    linhas: list[tuple[float, LinhaTabela]] = []
    for codigo, sigla, nome, _ in UFS:
        e, m, pop = fpe.get(sigla, 0.0), fpm.get(sigla, 0.0), populacao.get(codigo)
        if not (e or m) or not pop:
            continue
        receita = arrecadado.get(sigla)
        linhas.append(
            (
                (e + m) / pop,
                LinhaTabela(
                    rotulo=nome,
                    valores=[
                        round((e + m) / pop / 1e3, 2),
                        round((e + m) / 1e9, 1),
                        round((e + m) / receita * 100, 0) if receita else None,
                    ],
                    unidade="",
                    casas=1,
                ),
            )
        )
    if len(linhas) < 20:
        raise RuntimeError(f"FPE e FPM: só {len(linhas)} estados")
    linhas.sort(key=lambda x: -x[0])
    total_fpe, total_fpm = sum(fpe.values()), sum(fpm.values())
    total_receita = sum(arrecadado.values())
    meses = (
        periodo(ate_fpe, "M")
        if ate_fpe == ate_fpm
        else (f"{periodo(ate_fpe, 'M')} (FPE) e {periodo(ate_fpm, 'M')} (FPM)")
    )
    fonte = (
        f"{tesouro_transferencias.FONTE}; arrecadação: {receita_arrecadacao.FONTE}; população: "
        "Tesouro Nacional, cadastro de entes do SICONFI; as divisões: cálculo próprio"
    )
    soma = round((total_fpe + total_fpm) / 1e9, 1)
    cartoes = [
        Cartao(
            id="fpe-fpm-12m",
            rotulo="FPE e FPM, 12 meses",
            valor=soma,
            unidade="R$ bi",
            casas=0,
            referencia=ate_fpe,
            periodicidade="M",
            detalhe=(
                f"{br((total_fpe + total_fpm) / total_receita * 100, 0)} % do que a Receita "
                "arrecada"
            ),
            fonte=fonte,
            secao="impostos",
        )
    ]
    tabela = Tabela(
        id="fpe-fpm-estados",
        titulo="O que volta aos estados: FPE e FPM",
        subtitulo=f"12 meses até {meses}, do maior ao menor por habitante",
        colunas=[
            "R$ mil por habitante",
            "R$ bi",
            "% da arrecadação federal no estado",
        ],
        linhas=[linha for _, linha in linhas],
        fonte=fonte,
        # Valores que chegam ao ente, já sem os 20 % do Fundeb (metadado do Tesouro). Última
        # coluna: FPE e FPM sobre a arrecadação federal no estado (todos os tributos), que
        # conta no endereço fiscal de quem paga e infla DF, SP e RJ.
        nota=(
            "O FPE vai ao estado e o FPM às prefeituras, já sem o Fundeb; saem do IR e do IPI, "
            "com mais peso para os mais pobres. Acima de 100 na última coluna (arrecadação "
            f"até {periodo(ate_receita, 'M')}), o estado recebe mais do que a Receita arrecada "
            "nele."
        ),
    )
    return cartoes, [], [tabela], ""


def _quem_paga_retido(ctx: Contexto) -> Pecas:
    """O imposto pago antes da declaração (retido na fonte, carnê-leão) e o acerto, por faixa."""
    ano, faixas = receita_irpf.grandes_numeros()
    restituir = sum(f.a_restituir for f in faixas)
    a_pagar = sum(f.a_pagar for f in faixas)
    tabela = Tabela(
        id="quem-paga-retido",
        titulo="Imposto retido na fonte e o acerto na declaração",
        subtitulo=f"declarações de {ano + 1}, renda de {ano}; faixas em salários mínimos",
        colunas=["pago antes, % da renda", "devido, % da renda", "saldo do acerto, R$ bi"],
        linhas=[
            LinhaTabela(
                rotulo=f.nome,
                valores=[
                    round(f.pago / f.renda * 100, 1) if f.renda else None,
                    round(f.aliquota, 1),
                    round((f.a_pagar - f.a_restituir) / 1e9, 1),
                ],
                unidade="",
                casas=1,
            )
            for f in faixas
        ],
        fonte=f"{receita_irpf.FONTE}, ano-calendário {ano} (tabela 8)",
        # O retido em definitivo (13º, aplicações, ganho de capital, participação nos lucros)
        # não passa pelo acerto e fica fora; a renda, no denominador, inclui tudo.
        nota=(
            "Pago antes: retido na fonte, carnê-leão e pago no exterior; saldo negativo, a "
            f"faixa recebeu mais de volta. No total, R$ {br(restituir / 1e9, 0)} bi "
            f"restituídos e R$ {br(a_pagar / 1e9, 0)} bi pagos no acerto."
        ),
    )
    return [], [], [tabela], ""


def _reforma_regras(ctx: Contexto) -> Pecas:
    """O Imposto Seletivo e o Simples na reforma, a transição de 2026 a 2033 e o IBS indo para
    o destino, de 2029 a 2077: tudo da lei lida (`leis.py`); a aritmética do art. 131 é nossa e
    está dita na nota."""
    anos = leis.REFORMA_ANOS
    transicao = grafico(
        "reforma-transicao",
        "O que sobra dos impostos de hoje, ano a ano",
        [
            serie(
                "icms-iss",
                "ICMS e ISS",
                [(date(a, 1, 1), float(leis.ICMS_ISS_QUE_CONTINUA[a])) for a in anos],
                casas=0,
            ),
            serie(
                "pis-cofins",
                "PIS e Cofins",
                [(date(a, 1, 1), float(leis.PIS_COFINS_QUE_CONTINUA[a])) for a in anos],
                casas=0,
            ),
        ],
        tipo="degrau",
        unidade="% da alíquota de hoje",
        casas=0,
        periodicidade="A",
        fonte="Emenda Constitucional nº 132/2023 (ADCT, arts. 126, 128 e 129)",
        # O IPI vai a zero em 2027, menos no que a Zona Franca fabrica; os benefícios fiscais
        # do ICMS e do ISS caem na mesma proporção; o IBS sobe no lugar.
        nota=(
            "PIS e Cofins acabam em 2027, quando entra a CBS. ICMS e ISS caem um décimo por "
            "ano de 2029 a 2032 e acabam em 2033."
        ),
    )
    retido = leis.IBS_PELA_RECEITA_ANTIGA
    seguro = leis.IBS_SEGURO_PARA_QUEM_PERDE / 100
    anos_destino = sorted(retido)
    destino = grafico(
        "reforma-destino",
        "O IBS indo para onde se consome, de 2029 a 2077",
        [
            serie(
                "antes",
                "Pela receita antiga",
                [(date(a, 1, 1), retido[a]) for a in anos_destino],
                casas=1,
            ),
            serie(
                "destino",
                "Pelo destino",
                [(date(a, 1, 1), (100 - retido[a]) * (1 - seguro)) for a in anos_destino],
                casas=1,
            ),
            serie(
                "seguro",
                "Para quem mais perde",
                [(date(a, 1, 1), (100 - retido[a]) * seguro) for a in anos_destino],
                casas=1,
            ),
        ],
        tipo="empilhado",
        unidade="% do IBS de estados e municípios",
        casas=1,
        periodicidade="A",
        fonte=f"{leis.IBS_DESTINO_NORMA}; a conta ano a ano: cálculo próprio",
        # De 2029 a 2032, 80 % do IBS vai pela receita média antiga de ICMS e ISS; em 2033,
        # 90 %; depois, cai 1/45 por ano até acabar em 2078. Do resto, 5 % vão aos que mais
        # perdem e 95 % pelo destino.
        nota=(
            "Cálculo próprio, ano a ano, sobre o texto da emenda: a parte pela receita antiga "
            "some até 2078. Quanto cada estado ganha ou perde não tem número oficial."
        ),
        largura="inteira",
    )
    regras = Tabela(
        id="reforma-seletivo-simples",
        titulo="Imposto Seletivo e Simples Nacional",
        subtitulo="as alíquotas do Seletivo ficam para outra lei",
        colunas=["O que a lei diz", "Onde está"],
        linhas=[
            LinhaTabela(rotulo=r.tema, valores=[], unidade="", textos=[r.diz, r.norma])
            for r in leis.SELETIVO_E_SIMPLES
        ],
        fonte=(
            "Lei Complementar nº 214/2025, em texto atualizado (com a LC nº 227/2026), lida na "
            "Câmara dos Deputados; Emenda Constitucional nº 132/2023"
        ),
        nota=(
            "O Seletivo é federal, cobra a mais sobre o que faz mal à saúde ou ao meio ambiente "
            "e não dá crédito. No Simples, quem compra abate menos imposto; por isso a empresa "
            "pode pagar IBS e CBS por fora."
        ),
    )
    regimes = Tabela(
        id="reforma-regimes",
        titulo="Quem tem regra própria na reforma",
        subtitulo="combustíveis, bancos, planos de saúde, imóveis e outros",
        colunas=["O que muda", "Onde está"],
        linhas=[
            LinhaTabela(rotulo=r.tema, valores=[], unidade="", textos=[r.diz, r.norma])
            for r in leis.REGIMES_PROPRIOS
        ],
        fonte=(
            "Lei Complementar nº 214/2025, em texto atualizado (com a LC nº 227/2026), lida na "
            "Câmara dos Deputados (Títulos IV e V do Livro I)"
        ),
        # Os descontos são sobre a alíquota cheia do IBS e da CBS.
        nota=(
            "Muda a base (só a margem, em bancos e planos), a alíquota (por litro, nos "
            "combustíveis) ou o crédito. Sem crédito: a empresa que paga o hotel ou o "
            "restaurante não abate o imposto."
        ),
    )
    return [], [transicao, destino], [regras, regimes], ""


# ------------------------------------------------------- União, estados e municípios
#
# Caio, 19/11/2026: "nos impostos, dá pra separar oq é receita da união e dos Estados e
# outros? E ver onde cada Estado e outros está gastando com a receita?". Quem arrecada sai da
# OCDE (receita por esfera); o repasse geral da União e para onde vai a despesa de cada
# esfera, do FMI (COFOG por esfera, `fmi_cofog.por_esfera`). Cada estado, um por um, fica em
# Estados (as métricas "Gasto com ...", da DCA).


def _esferas(ctx: Contexto) -> Pecas:
    ocde = ocde_receita.carga(["BRA"], list(ESFERAS), ["_T"], inicio=2000)
    por = {s: ocde.get(("BRA", s, "_T"), {}) for s in ESFERAS}
    anos = sorted(a for a in por["S1311"] if all(a in por[s] for s in ESFERAS))
    if not anos:
        raise RuntimeError("OCDE sem a receita do Brasil por esfera")
    total = {a: sum(por[s][a] for s in ESFERAS) for a in anos}
    # O INSS (fundos de seguridade social, S1314) é federal: vai com a União.
    parte = {
        "S1311": {a: (por["S1311"][a] + por["S1314"][a]) / total[a] * 100 for a in anos},
        "S1312": {a: por["S1312"][a] / total[a] * 100 for a in anos},
        "S1313": {a: por["S1313"][a] / total[a] * 100 for a in anos},
    }
    fonte_ocde = f"{ocde_receita.FONTE}; parte de cada esfera: cálculo próprio"
    cartoes = [
        cartao(
            id_,
            rotulo,
            _pontos_anuais(parte[s]),
            unidade="% da carga",
            casas=0,
            periodicidade="A",
            detalhe=detalhe,
            fonte=fonte_ocde,
            secao="impostos",
            mini=30,
        )
        for s, id_, rotulo, detalhe in (
            ("S1311", "carga-uniao", "Arrecadado pela União", "Com o INSS; antes dos repasses"),
            ("S1312", "carga-estados", "Pelos estados", "Sobretudo ICMS e IPVA"),
            ("S1313", "carga-municipios", "Pelos municípios", "ISS e IPTU, sem o que recebem"),
        )
    ]

    cofog = fmi_cofog.por_esfera(2010)
    repasse = cofog.get("S1311", {}).get(fmi_cofog.REPASSES, {}).get("POGDP_PT", {})
    if repasse:
        cartoes.append(
            cartao(
                "repasses-uniao",
                "Repasse geral da União",
                _pontos_anuais(repasse),
                unidade="% do PIB",
                casas=1,
                periodicidade="A",
                detalhe="FPE, FPM e outros, sem destino amarrado",
                fonte=f"{fmi_cofog.FONTE.replace('governo geral', 'por esfera')}",
                secao="impostos",
                mini=30,
            )
        )

    tabelas: list[Tabela] = []
    esferas = [e for e in fmi_cofog.ESFERAS if e in cofog]
    comuns = [
        a
        for a in sorted({a for e in esferas for a in cofog[e].get("GF10_T", {}).get("POTO_PT", {})})
        if all(a in cofog[e].get("GF10_T", {}).get("POTO_PT", {}) for e in esferas)
    ]
    if len(esferas) == 3 and comuns:
        ano = comuns[-1]

        def v(e: str, f: str, u: str) -> float | None:
            return cofog[e].get(f, {}).get(u, {}).get(ano)

        principais = [f for f in fmi_cofog.FUNCOES if len(f) == len("GF10_T")]
        linhas = [
            LinhaTabela(
                rotulo="Despesa total",
                valores=[
                    _arredondar_1(sum(v(e, f, "POGDP_PT") or 0 for f in principais))
                    for e in esferas
                ],
                unidade="% do PIB",
                casas=1,
            )
        ]
        for f, nome in fmi_cofog.FUNCOES.items():
            linhas.append(
                LinhaTabela(
                    rotulo=nome,
                    valores=[_arredondar_1(v(e, f, "POTO_PT")) for e in esferas],
                    unidade="% da despesa",
                    casas=1,
                    grupo="Por função, em % da despesa de cada esfera",
                )
            )
            if f == "GF0170_T":
                linhas.append(
                    LinhaTabela(
                        rotulo="  dos quais: repasses a outras esferas",
                        valores=[
                            _arredondar_1(v(e, fmi_cofog.REPASSES, "POTO_PT")) for e in esferas
                        ],
                        unidade="% da despesa",
                        casas=1,
                        grupo="Por função, em % da despesa de cada esfera",
                    )
                )
        tabelas.append(
            Tabela(
                id="despesa-esferas",
                titulo="Para onde vai a despesa de cada esfera",
                subtitulo=f"{ano}; cada coluna soma 100 % da despesa daquela esfera",
                colunas=[fmi_cofog.ESFERAS[e] for e in esferas],
                linhas=linhas,
                fonte=(
                    "FMI, Government Finance Statistics (COFOG), União (governo central), "
                    f"estados e municípios, {ano}"
                ),
                # FPE, FPM e a cota do ICMS dos municípios estão em repasses; o repasse com
                # destino certo (SUS, Fundeb) fica na função dele. Na União, a proteção social
                # é quase toda o INSS.
                nota=(
                    "Cada esfera conta o que paga, repasses inclusive; por isso a soma passa "
                    "da do governo geral. Cada estado em Estados › Mapa e ranking."
                ),
            )
        )

    u, e_, m = (parte[s][anos[-1]] for s in ("S1311", "S1312", "S1313"))
    frase = (
        f"Em {anos[-1]}, a União (com o INSS) arrecadou {br(u, 0)} % dos tributos, os estados "
        f"{br(e_, 0)} % e os municípios {br(m, 0)} %, antes dos repasses."
    )
    return cartoes, [], tabelas, frase


def _arredondar_1(x: float | None) -> float | None:
    return None if x is None else round(x, 1)


MAIS_PARTES: list[tuple[str, Callable[[Contexto], Pecas]]] = [
    ("bases contra outros países", _bases_paises),
    ("arrecadação por estado", _por_estado),
    ("FPE e FPM", _transferencias),
    ("imposto retido na fonte", _quem_paga_retido),
    ("Seletivo, Simples e destino", _reforma_regras),
    ("arrecadação por setor", _por_setor),
    (
        "previsto × realizado",
        lambda ctx: _previsto(
            ctx,
            avaliacao_bimestral.do_ano(relatorios.ANO_DA_RECEITA_PREVISTA, "impostos"),
        ),
    ),
    ("quem paga", _quem_paga),
    ("dívida ativa", _divida_ativa),
    ("alíquotas", _aliquotas),
    ("reforma", _reforma),
    ("União, estados e municípios", _esferas),
]


def montar(ctx: Contexto) -> Secao:
    cartoes: list[Cartao] = []
    graficos: list[Grafico] = []
    tabelas: list[Tabela] = []
    frases: list[str] = []
    falhas: list[str] = []
    for nome, parte in (("arrecadação", _arrecadacao), ("carga", _carga)):
        try:
            c, g, t, f = parte(ctx)
            cartoes += c
            graficos += g
            tabelas += t
            frases.append(f)
        except Exception as erro:
            falhas.append(nome)
            print(f"    impostos: {nome} ficou de fora: {str(erro)[:160]}")
    for nome, outra in (("gasto tributário", _gasto_tributario), *MAIS_PARTES):
        try:
            c, g, t, f = outra(ctx)
            cartoes += c
            graficos += g
            tabelas += t
            if f:
                frases.append(f)
        except Exception as erro:
            print(f"    impostos: {nome} ficou de fora: {str(erro)[:160]}")
    try:
        g, t = _crescimento(ctx)
        graficos += g
        tabelas += t
    except Exception as erro:
        print(f"    impostos: carga × crescimento ficou de fora: {str(erro)[:160]}")
    simulador_reforma: SimuladorReforma | None = None
    try:
        c, t, simulador_reforma = _simulador_da_reforma(ctx)
        cartoes += c
        tabelas += t
    except Exception as erro:
        print(f"    impostos: reforma do consumo ficou de fora: {str(erro)[:160]}")
    if len(falhas) == 2:
        raise RuntimeError("impostos: sem arrecadação e sem carga")
    return Secao(
        id="impostos",
        titulo="Impostos",
        resumo=" ".join(frases),
        cartoes=cartoes,
        graficos=graficos,
        tabelas=tabelas,
        simulador_reforma=simulador_reforma,
        gerado_em=ctx.agora(),
    )
