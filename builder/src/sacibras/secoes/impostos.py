"""Impostos: quanto se arrecada, sobre o que, quanto se deixa de arrecadar e o que se sabe do
efeito no crescimento.

Pedido do Caio (14/11/2026): *"estou sentindo falta de alguma sessão sobre impostos, ou
impacto de impostos no crescimento"*. Das quatro peças oferecidas para o crescimento, ele
escolheu as quatro: a composição da carga (com outros países), a carga contra o crescimento
(um ponto por país, com o aviso de que andar junto não é causa), os multiplicadores lidos em
estudo oficial e o gasto tributário.

Fontes: a arrecadação federal mês a mês vem da Receita (CSV por UF e tributo); a carga
tributária e a composição, da OCDE (Global Revenue Statistics: o mesmo método para ~145
países, Brasil até 2024); o crescimento por habitante, do WEO do FMI.
"""

from __future__ import annotations

import gettext
import math
from collections.abc import Callable
from datetime import date

import pycountry

from sacibras import contas, leis, relatorios
from sacibras.fontes import (
    fmi,
    ocde_receita,
    receita_arrecadacao,
    receita_gastos,
    receita_irpf,
    siconfi,
)
from sacibras.fontes.ocde_receita import BASES, ESFERAS
from sacibras.fontes.receita_arrecadacao import COMPLETO_DESDE, NOMES
from sacibras.schema import (
    Cartao,
    Dispersao,
    EixoDispersao,
    Grafico,
    LinhaTabela,
    PontoDispersao,
    Secao,
    Tabela,
)
from sacibras.secoes.base import Contexto, br, cartao, grafico, periodo, serie
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


# ------------------------------------------------------------------ contas


def indice_de_precos(variacao_mensal: list[Ponto]) -> dict[date, float]:
    """O número-índice (primeiro mês = 1) de uma variação mensal em %."""
    nivel, saida = 1.0, {}
    for d, v in variacao_mensal:
        nivel *= 1 + v / 100
        saida[d] = nivel
    return saida


def a_precos_de(mensal: list[Ponto], indice: dict[date, float], base: date) -> list[Ponto]:
    """Valores correntes em reais de `base` (o mês sem índice fica de fora)."""
    return [(d, v * indice[base] / indice[d]) for d, v in mensal if d in indice]


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
            nota=(
                "Soma dos 12 meses de tudo o que a Receita arrecada (impostos, contribuições "
                "e a previdência do INSS), cada mês levado a preços de hoje pelo IPCA. A série "
                "começa em 2013: antes, o arquivo da Receita não traz a previdência por estado."
            ),
        ),
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
            nota=(
                "Imposto de Renda junta pessoa física, empresas e o retido na fonte. A "
                "contribuição ao INSS é a de empresas e trabalhadores ao Regime Geral."
            ),
        ),
    ]

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
            nota=(
                "O % do PIB usa o PIB de 12 meses até o último mês com PIB no Banco Central; "
                "o crescimento real compara os 12 meses com os 12 anteriores."
            ),
        )
    ]
    frase = (
        f"A Receita arrecadou R$ {br(total_real[-1][1] / 1000, 2)} tri nos 12 meses até "
        f"{periodo(ultimo, 'M')}, a preços de hoje"
    )
    if cresc:
        frase += f", {br(abs(cresc[-1][1]))} % {'a mais' if cresc[-1][1] >= 0 else 'a menos'}"
        frase += " que nos 12 meses anteriores, descontada a inflação"
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
        nota=(
            "O imposto conta para o estado do endereço fiscal de quem paga, não para onde a "
            "venda ou o trabalho aconteceu: o Distrito Federal (órgãos federais e estatais) e "
            "São Paulo e Rio de Janeiro (sedes de empresas e bancos) aparecem com mais do que "
            "a economia local explicaria. O ICMS de cada estado, por habitante, está em "
            "Estados."
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
    consumo = {a: de("BRA", "T_5000")[a] / v * 100 for a, v in total_br.items() if v}

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
            procedencia="calculado",
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
                "Tributos e contribuições sociais de todo o governo, no método da OCDE (o "
                "mesmo para todos os países). O número da Receita Federal para o Brasil sai "
                "um pouco diferente, por outro método."
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
            nota=(
                "Bens e serviços: ICMS, ISS, IPI, Cofins, PIS, imposto de importação. Renda e "
                "lucro: Imposto de Renda e CSLL. Contribuições sociais: INSS de empresas e "
                "trabalhadores e a previdência dos servidores. Folha: salário-educação e o "
                "Sistema S. Patrimônio: IPTU, ITCMD, ITBI, ITR e o IOF (a OCDE põe o IPVA em "
                "bens e serviços)."
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
            nota=(
                'Na OCDE, a contribuição ao INSS conta à parte, como "previdência" (fundos '
                "de seguridade social), e não na União."
            ),
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
            subtitulo=f"{ano}; a carga em % do PIB e cada base em % da carga",
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
                'As bases somam perto de 100 % (o resto é "outros"). Os estudos que ligam '
                "imposto e crescimento olham mais para esta composição do que para o total: "
                "tributo sobre renda de empresas e sobre salário tende a pesar mais no "
                "investimento e no emprego do que tributo sobre consumo e propriedade."
            ),
        )
    ]
    frase = (
        f"A carga tributária do Brasil foi de {br(total_br[ultimo])} % do PIB em {ultimo} "
        f"(média da OCDE: {br(de('OECD_REP').get(ultimo, math.nan))} %), e "
        f"{br(consumo[ultimo], 0)} % dela vem de bens e serviços"
    )
    return cartoes, graficos, tabelas, frase + "."


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
    brasil = next((p for p in pontos if p.chave == "BRA"), None)
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
                    nome="Crescimento médio do PIB por habitante", unidade="% ao ano", casas=1
                ),
                pontos=pontos,
                correlacao=round(r, 2),
            ),
            nota=(
                f"{len(pontos)} países com carga na OCDE e PIB no FMI. Correlação de "
                f"{br(r, 2)}: {em_palavras(r)}. Andar junto não quer dizer que um cause o "
                "outro: país rico tende a cobrar mais e a crescer menos, por já ter "
                "crescido; e país que cresce pode cobrar mais. Para o efeito do imposto, "
                "ver os estudos na tabela abaixo."
                + (
                    f" Brasil: carga de {br(brasil.x)} % e crescimento de "
                    f"{br(brasil.y)} % ao ano por habitante."
                    if brasil
                    else ""
                )
            ),
        )
    ]
    tabelas = [_tabela_estudos()]
    return graficos, tabelas


def _tabela_estudos() -> Tabela:
    linhas = [
        LinhaTabela(rotulo=e.rotulo, valores=[e.valor], unidade=e.unidade, casas=e.casas)
        for e in relatorios.EFEITOS_DE_IMPOSTO
    ]
    return Tabela(
        id="impostos-estudos",
        titulo="O que os estudos oficiais estimam",
        subtitulo="números lidos nos documentos, com a fonte de cada um na nota",
        colunas=["efeito estimado"],
        linhas=linhas,
        fonte="; ".join(dict.fromkeys(e.fonte for e in relatorios.EFEITOS_DE_IMPOSTO)),
        nota="\n\n".join(e.leitura for e in relatorios.EFEITOS_DE_IMPOSTO),
    )


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
                            "Previsto no projeto de orçamento",
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
            nota=(
                "Isenções, reduções de alíquota e regimes especiais dos tributos federais, no "
                'valor realizado ("bases efetivas") que a Receita publica com uns dois anos '
                "de atraso. Não entram os benefícios de ICMS e ISS dos estados e municípios."
                + (
                    " A linha tracejada é o que a Receita previu ao mandar o orçamento de cada "
                    f"ano ao Congresso; para {previstos[-1].ano}, "
                    f"R$ {br(previstos[-1].total / 1e9, 0)} bi."
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
                "Agricultura e agroindústria inclui a cesta básica sem Cofins e PIS. Simples "
                "Nacional é o quanto o regime cobra a menos do que as regras gerais cobrariam."
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
                nota=(
                    "A região é a de quem deixou de pagar (a sede da empresa ou o endereço da "
                    "pessoa), pela divisão que a própria Receita faz."
                ),
            )
        )
    frase = (
        f"A União deixou de arrecadar {br(pct[ano])} % do PIB em {ano} com isenções e "
        "regimes especiais"
    )
    return cartoes, graficos, tabelas, frase + "."


# ------------------------------------------------------------------ seção


def _quem_paga(ctx: Contexto) -> Pecas:
    tabelas = [
        Tabela(
            id="quem-paga-decimos",
            titulo="Imposto em % da renda, dos mais pobres aos mais ricos",
            subtitulo="famílias em dez grupos de renda por pessoa, 2017-2018",
            colunas=["sobre o consumo, %", "sobre renda e patrimônio, %", "total, %"],
            linhas=[
                LinhaTabela(
                    rotulo=nome,
                    valores=[indiretos, diretos, round(indiretos + diretos, 1)],
                    unidade="",
                    casas=1,
                )
                for nome, indiretos, diretos in relatorios.INCIDENCIA_POR_DECIMO
            ],
            fonte=relatorios.FONTE_INCIDENCIA,
            nota=(
                "Quem ganha menos gasta quase tudo o que ganha, e o imposto embutido nos preços "
                "(ICMS, PIS, Cofins, IPI, ISS) leva uma parte maior da renda: 23,4 % nos 10 % "
                "mais pobres contra 8,6 % nos 10 % mais ricos. O imposto sobre renda e "
                "patrimônio (com a contribuição à previdência, o IPTU e o IPVA) cresce com a "
                "renda, mas não o bastante para compensar. O total é a soma das duas colunas. "
                "É estimativa do Ipea com a pesquisa de orçamentos do IBGE, não dado de "
                "arrecadação."
            ),
        )
    ]
    frase = ""
    try:
        ano, faixas = receita_irpf.grandes_numeros()
        topo = faixas[-1]
        maior = max(faixas, key=lambda f: f.aliquota)
        tabelas.append(
            Tabela(
                id="quem-paga-irpf",
                titulo="Imposto de Renda por faixa de renda de quem declara",
                subtitulo=f"declarações de {ano + 1}, renda de {ano}; faixas em salários mínimos",
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
                nota=(
                    f'O imposto pesa mais na faixa "{maior.nome.lower()}" salários mínimos '
                    f"({br(maior.aliquota)} % da renda) e cai daí para cima: na faixa mais alta, "
                    f"{br(topo.isentos / topo.renda * 100, 0)} % da renda é isenta (boa parte, "
                    "lucros e dividendos) e o imposto fica em "
                    f"{br(topo.aliquota)} %.\n\nO imposto aqui é o da declaração (tabela "
                    "progressiva). Falta o retido na fonte sobre 13º, aplicações e ganho de "
                    "capital, que a planilha não traz: no topo, onde esses rendimentos pesam, "
                    "a conta sai menor do que o que a pessoa pagou. Só entra quem declara "
                    f"({br(sum(f.declarantes for f in faixas) / 1e6)} milhões de pessoas). "
                    "A faixa de até meio salário mínimo tem "
                    "imposto por rendimentos atrasados recebidos de uma vez."
                ),
            )
        )
        frase = (
            f"No Imposto de Renda de {ano}, quem declarou mais de 320 salários mínimos pagou "
            f"{br(topo.aliquota)} % da renda na declaração, menos que a faixa de "
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
            "Imposto sobre o lucro das empresas: Brasil e o mundo",
            [
                serie("bra", "Brasil", _pontos_anuais(por_pais["BRA"])),
                serie("mediana", "Mediana dos países", medianas),
            ],
            unidade="% do lucro, alíquota da lei",
            casas=1,
            periodicidade="A",
            fonte=fonte,
            nota=(
                "A alíquota cheia da lei para uma empresa grande, somando todas as esferas de "
                "governo. Não é o que as empresas pagam de fato: deduções, incentivos e "
                "regimes como o Simples e o lucro presumido fazem a conta efetiva ser outra. "
                "Mediana: metade dos países cobra mais, metade cobra menos."
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
            nota=(
                "A OCDE só publica com o Brasil o imposto sobre o lucro das empresas. Para o "
                "Imposto de Renda da pessoa física, o imposto sobre o consumo e o que pesa "
                "sobre o salário, as bases comparáveis da OCDE não trazem o Brasil."
            ),
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
        nota=(
            "A reforma troca cinco tributos sobre o consumo (PIS, Cofins e IPI, federais; "
            "ICMS, estadual; ISS, municipal) por dois de mesma base, a CBS (federal) e o IBS "
            "(de estados e municípios), mais o Imposto Seletivo. As alíquotas cheias ainda "
            "não existem: o Senado as fixa no ano anterior a cada uma. Texto lido na "
            "publicação original; mudança posterior nesses artigos não foi conferida."
        ),
    )
    return [], [], [tabela], ""


Pecas = tuple[list[Cartao], list[Grafico], list[Tabela], str]
MAIS_PARTES: list[tuple[str, Callable[[Contexto], Pecas]]] = [
    ("arrecadação por estado", _por_estado),
    ("quem paga", _quem_paga),
    ("alíquotas", _aliquotas),
    ("reforma", _reforma),
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
    if len(falhas) == 2:
        raise RuntimeError("impostos: sem arrecadação e sem carga")
    return Secao(
        id="impostos",
        titulo="Impostos",
        resumo=" ".join(frases),
        cartoes=cartoes,
        graficos=graficos,
        tabelas=tabelas,
        gerado_em=ctx.agora(),
    )
