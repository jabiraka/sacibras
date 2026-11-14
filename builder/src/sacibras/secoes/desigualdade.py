"""Desigualdade: o Gini, quem fica com quanto da renda, o topo pelo Imposto de Renda, a
pobreza, as diferenças por sexo e cor, e a comparação entre estados e países.

Pedido do Caio (14/11/2026): *"Coloque uma aba de Desigualdade no Sacibras [...] tem gini,
concentração de renda?"*.

De onde vem cada coisa (tudo conferido em 14/11/2026):

- **IBGE, PNAD Contínua anual, "rendimento de todas as fontes"** (SIDRA; sai em maio, com o
  ano anterior): o Gini da renda domiciliar por pessoa (7435) e o da renda do trabalho
  (7453); a fatia da renda de cada grupo de 10 % das pessoas, do 1 % e dos 5 % do topo
  (7527); a renda média por pessoa de cada grupo, a preços do último ano (7533); a renda do
  trabalho por cor ou raça (7441) e por sexo (7444), também a preços do último ano.
- **Ipea (Ipeadata)**: o Gini e a pobreza desde 1995, com a PNAD antiga emendada à
  Contínua (Souza e Hecksher, 2025): `PNADS_GINI` e as linhas de pobreza do Banco Mundial
  (US$ 3,00 e US$ 8,30 por dia, PPC de 2021).
- **Receita Federal, Grandes Números do IRPF** (o mesmo arquivo de Impostos › Quem paga):
  quanto da renda declarada e dos lucros e dividendos vai para cada faixa de quem declara.
- **Banco Mundial**: o Gini dos outros países, contra o PIB por habitante.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sacibras.fontes import banco_mundial, ibge_sidra, ipeadata, receita_irpf
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
from sacibras.secoes.base import Contexto, br, cartao, grafico, serie
from sacibras.secoes.estados import SIGLA, UFS
from sacibras.tipos import Ponto

PNADA = "IBGE, PNAD Contínua anual"

GINI = (7435, 10681)
"""Índice de Gini do rendimento domiciliar per capita, a preços médios do ano."""
GINI_TRABALHO = (7453, 10806)
"""Índice de Gini do rendimento habitual de todos os trabalhos (ocupados de 14 anos ou mais)."""
FATIAS = (7527, 10826, "c1019/all")
"""Distribuição da massa de rendimento domiciliar per capita (%) por classe de percentual
das pessoas em ordem crescente de renda (classificação 1019)."""
RENDA_POR_GRUPO = (7533, 10816, "c1019/all")
"""Rendimento médio mensal real domiciliar per capita (R$), a preços médios do último ano,
pelas mesmas classes."""
POR_COR = (7441, 10774, "c86/all")
"""Rendimento médio mensal real habitual de todos os trabalhos (R$), a preços médios do
último ano, por cor ou raça (classificação 86)."""
POR_SEXO = (7444, 10774, "c2/all")
"""O mesmo, por sexo (classificação 2)."""

# Categorias da classificação 1019, da resposta do SIDRA em 14/11/2026.
DECIMOS = [
    ("49246", "10 % mais pobres"),
    ("49247", "do 10º ao 20º percentil"),
    ("49248", "do 20º ao 30º"),
    ("49249", "do 30º ao 40º"),
    ("49250", "do 40º ao 50º"),
    ("49251", "do 50º ao 60º"),
    ("49252", "do 60º ao 70º"),
    ("49253", "do 70º ao 80º"),
    ("49254", "do 80º ao 90º"),
    ("49255", "10 % mais ricos"),
]
CINCO_MAIS_RICOS = ("49257", "49258")
"""Do 95º ao 99º percentil e acima do 99º: somados, os 5 % do topo."""
UM_MAIS_RICO = "49258"
QUARENTA_MAIS_POBRES = [c for c, _ in DECIMOS[:4]]
CINQUENTA_DO_MEIO = [c for c, _ in DECIMOS[4:9]]
DEZ_MAIS_RICOS = DECIMOS[9][0]

BRANCA, PRETA, PARDA = "2776", "2777", "2779"
HOMENS, MULHERES = "4", "5"

GINI_IPEA = "PNADS_GINI"
"""Ipea: Gini da renda domiciliar per capita × 100, PNAD até 2011 ajustada para casar com a
PNAD Contínua em 2012."""
POBREZA_IPEA = "PNADS_PERCPOBRE830"
"""Ipea: % das pessoas abaixo de US$ 8,30 por dia (PPC de 2021), a linha do Banco Mundial
para países de renda média-alta, que o IBGE usa como linha de pobreza."""
EXTREMA_IPEA = "PNADS_PERCPOBRE300"
"""Ipea: % das pessoas abaixo de US$ 3,00 por dia (PPC de 2021), a linha internacional de
extrema pobreza."""
IPEA = "Ipea (Ipeadata), com a PNAD e a PNAD Contínua do IBGE"

# Faixas de quem declara, em salários mínimos (piso de cada grupo), da menor para a maior.
GRUPOS_IRPF = [(0.0, "Até 5"), (5.0, "De 5 a 20"), (20.0, "De 20 a 80"), (80.0, "De 80 a 320")]
TOPO_IRPF = 320.0


def _ano(d: date) -> date:
    return date(d.year, 1, 1)


def soma(fatias: dict[str, list[Ponto]], chaves: list[str]) -> list[Ponto]:
    """A soma das classes, ano a ano, só nos anos em que todas têm dado."""
    por_ano: dict[date, list[float]] = {}
    for chave in chaves:
        for d, v in fatias.get(chave, []):
            por_ano.setdefault(d, []).append(v)
    return [(d, sum(vs)) for d, vs in sorted(por_ano.items()) if len(vs) == len(chaves)]


def media(classes: dict[str, list[Ponto]], chaves: list[str]) -> list[Ponto]:
    """A renda média de grupos de mesmo tamanho (cada classe, 10 % das pessoas)."""
    return [(d, v / len(chaves)) for d, v in soma(classes, chaves)]


def razao(de_cima: list[Ponto], de_baixo: list[Ponto], escala: float = 1.0) -> list[Ponto]:
    baixo = dict(de_baixo)
    return [(d, v / baixo[d] * escala) for d, v in de_cima if baixo.get(d)]


def indice(pontos: list[Ponto], base: date) -> list[Ponto]:
    """A série com `base` = 100."""
    valor = dict(pontos).get(base)
    return [(d, v / valor * 100) for d, v in pontos if d >= base] if valor else []


def emendar(antiga: list[Ponto], nova: list[Ponto]) -> list[Ponto]:
    """A série antiga até o ano antes da nova começar."""
    if not nova:
        return antiga
    return [p for p in antiga if p[0] < nova[0][0]]


@dataclass(frozen=True)
class GrupoIrpf:
    nome: str
    declarantes: float
    renda: float
    dividendos: float


def agrupar_irpf(faixas: list[receita_irpf.Faixa]) -> list[GrupoIrpf]:
    """As faixas da Receita em cinco grupos (até 5, 5 a 20, 20 a 80, 80 a 320 e mais de 320
    salários mínimos)."""
    limites = [*GRUPOS_IRPF, (TOPO_IRPF + 0.5, f"Mais de {TOPO_IRPF:.0f}")]
    somas = {nome: [0.0, 0.0, 0.0] for _, nome in limites}
    for f in faixas:
        piso = receita_irpf.piso(f.nome)
        nome = [n for p, n in limites if piso >= p][-1]
        somas[nome][0] += f.declarantes
        somas[nome][1] += f.renda
        somas[nome][2] += f.dividendos
    return [GrupoIrpf(n, *somas[n]) for _, n in limites]


def _cartao_anual(
    id: str, rotulo: str, pontos: list[Ponto], unidade: str, fonte: str, detalhe: str, casas: int
) -> Cartao:
    return cartao(
        id,
        rotulo,
        pontos,
        unidade=unidade,
        periodicidade="A",
        casas=casas,
        detalhe=detalhe,
        fonte=fonte,
        secao="desigualdade",
        mini=40,
    )


def montar(ctx: Contexto) -> Secao:
    cartoes: list[Cartao] = []
    graficos: list[Grafico] = []
    tabelas: list[Tabela] = []
    avisos: list[str] = []

    # ---------------------------------------------------------------- Gini
    gini = ibge_sidra.serie(*GINI)
    gini_trab = ibge_sidra.serie(*GINI_TRABALHO)
    if not gini:
        raise RuntimeError("SIDRA 7435 sem o Gini")
    try:
        gini_ipea = [(_ano(d), v / 100) for d, v in ipeadata.serie(GINI_IPEA, date(1990, 1, 1))]
    except Exception as erro:  # o Ipea fora do ar não derruba a seção
        gini_ipea = []
        avisos.append(f"Gini do Ipea: {erro}")
    gini_antigo = emendar(gini_ipea, gini)
    ano = gini[-1][0].year
    menor_ano, menor = min(gini, key=lambda p: (p[1], -p[0].year))
    cartoes.append(
        _cartao_anual(
            "gini",
            "Gini da renda por pessoa",
            gini,
            "",
            f"{PNADA} (SIDRA 7435)",
            (
                "o menor da série"
                if menor_ano == gini[-1][0]
                else f"o menor foi {br(menor, 3)}, em {menor_ano.year}"
            ),
            3,
        )
    )
    if gini_trab:
        cartoes.append(
            _cartao_anual(
                "gini-trabalho",
                "Gini da renda do trabalho",
                gini_trab,
                "",
                f"{PNADA} (SIDRA 7453)",
                f"{gini_trab[0][0].year}: {br(gini_trab[0][1], 3)}",
                3,
            )
        )
    series_gini = [serie("pnadc", "Renda por pessoa (PNAD Contínua)", gini, casas=3)]
    if gini_antigo:
        series_gini.append(
            serie("pnad", "Renda por pessoa (PNAD antiga, Ipea)", gini_antigo, casas=3)
        )
    if gini_trab:
        series_gini.append(serie("trabalho", "Só a renda do trabalho", gini_trab, casas=3))
    graficos.append(
        grafico(
            "gini",
            "Índice de Gini",
            series_gini,
            unidade="índice",
            casas=3,
            periodicidade="A",
            fonte=f"{PNADA} (SIDRA 7435 e 7453); antes de 2012, {IPEA} ({GINI_IPEA})",
            nota=(
                "Vai de 0 (todos com a mesma renda) a 1 (uma pessoa com toda a renda). A renda "
                "por pessoa é a de todas as fontes da casa (trabalho, aposentadoria, aluguel, "
                "programas sociais) dividida pelos moradores. Antes de 2012, a PNAD antiga, "
                "que o Ipea ajusta para casar com a PNAD Contínua em 2012."
            ),
            largura="inteira",
        )
    )

    # ---------------------------------------------------------------- quem fica com quanto
    fatias = ibge_sidra.series(FATIAS[0], FATIAS[1], classificacao=FATIAS[2], por="Classes")
    pobres40 = soma(fatias, QUARENTA_MAIS_POBRES)
    meio50 = soma(fatias, CINQUENTA_DO_MEIO)
    ricos10 = fatias.get(DEZ_MAIS_RICOS, [])
    ricos1 = fatias.get(UM_MAIS_RICO, [])
    if not (pobres40 and ricos10 and ricos1):
        raise RuntimeError("SIDRA 7527 sem as classes de percentual")
    palma = razao(ricos10, pobres40)
    cartoes += [
        _cartao_anual(
            "fatia-10-ricos",
            "Renda dos 10 % mais ricos",
            ricos10,
            "% da renda",
            f"{PNADA} (SIDRA 7527)",
            f"{ricos10[0][0].year}: {br(ricos10[0][1])} %",
            1,
        ),
        _cartao_anual(
            "fatia-1-rico",
            "Renda do 1 % mais rico",
            ricos1,
            "% da renda",
            f"{PNADA} (SIDRA 7527)",
            f"{ricos1[0][0].year}: {br(ricos1[0][1])} %",
            1,
        ),
        _cartao_anual(
            "fatia-40-pobres",
            "Renda dos 40 % mais pobres",
            pobres40,
            "% da renda",
            f"{PNADA} (SIDRA 7527)",
            f"{pobres40[0][0].year}: {br(pobres40[0][1])} %",
            1,
        ),
        _cartao_anual(
            "razao-10-40",
            "Razão 10/40",
            palma,
            "vezes",
            f"{PNADA} (SIDRA 7527); conta nossa",
            "10 % mais ricos ÷ 40 % mais pobres",
            1,
        ),
    ]
    cartoes[-1] = cartoes[-1].model_copy(update={"procedencia": "calculado"})
    graficos.append(
        grafico(
            "fatias",
            "Quem fica com quanto da renda",
            [
                serie("pobres", "40 % mais pobres", pobres40, casas=1),
                serie("meio", "50 % do meio", meio50, casas=1),
                serie("ricos", "10 % mais ricos", ricos10, casas=1),
            ],
            tipo="empilhado",
            unidade="% da renda",
            periodicidade="A",
            fonte=f"{PNADA} (SIDRA 7527)",
            nota=(
                "As pessoas em fila, da menor renda por pessoa para a maior, e a parte da renda "
                "de todas as fontes que cabe a cada grupo. O IBGE arredonda cada fatia em uma "
                "casa: a soma pode dar 99,9 ou 100,1."
            ),
        )
    )

    classes = ibge_sidra.series(
        RENDA_POR_GRUPO[0], RENDA_POR_GRUPO[1], classificacao=RENDA_POR_GRUPO[2], por="Classes"
    )
    renda_pobres40 = media(classes, QUARENTA_MAIS_POBRES)
    renda_meio50 = media(classes, CINQUENTA_DO_MEIO)
    renda_ricos10 = classes.get(DEZ_MAIS_RICOS, [])
    renda_ricos1 = classes.get(UM_MAIS_RICO, [])
    renda_todos = classes.get("49243", [])
    base = renda_todos[0][0] if renda_todos else date(2012, 1, 1)
    graficos.append(
        grafico(
            "renda-por-grupo",
            f"Quanto a renda de cada grupo cresceu desde {base.year}",
            [
                serie("pobres", "40 % mais pobres", indice(renda_pobres40, base), casas=1),
                serie("meio", "50 % do meio", indice(renda_meio50, base), casas=1),
                serie("ricos", "10 % mais ricos", indice(renda_ricos10, base), casas=1),
                serie("um", "1 % mais rico", indice(renda_ricos1, base), casas=1),
            ],
            unidade=f"{base.year} = 100",
            periodicidade="A",
            fonte=f"{PNADA} (SIDRA 7533); conta nossa",
            nota=(
                "Renda média por pessoa de cada grupo, já descontada a inflação (a preços do "
                f"último ano), com {base.year} = 100. Acima de 100, o grupo ganha mais do que "
                f"em {base.year}."
            ),
        )
    )
    ultimo = ricos10[-1][0]

    def linha(rotulo: str, chave: str) -> LinhaTabela:
        renda, fatia = dict(classes.get(chave, [])), dict(fatias.get(chave, []))
        r, rb = renda.get(ultimo), renda.get(base)
        return LinhaTabela(
            rotulo=rotulo,
            valores=[
                r,
                fatia.get(ultimo),
                fatia.get(base),
                None if r is None or not rb else round((r / rb - 1) * 100, 1),
            ],
            unidade="",
            casas=1,
        )

    tabelas.append(
        Tabela(
            id="desigualdade-decimos",
            titulo="A renda de cada grupo de 10 %",
            subtitulo=f"as pessoas em fila, da menor renda por pessoa para a maior; {ultimo.year}",
            colunas=[
                f"renda por pessoa, R$ por mês ({ultimo.year})",
                f"% da renda ({ultimo.year})",
                f"% da renda ({base.year})",
                f"renda real desde {base.year}, %",
            ],
            linhas=[
                *(linha(nome, c) for c, nome in DECIMOS),
                linha("1 % mais rico", UM_MAIS_RICO),
            ],
            fonte=f"{PNADA} (SIDRA 7527 e 7533)",
            nota=(
                "Renda de todas as fontes da casa dividida pelos moradores, a preços do último "
                "ano. Cada linha é um décimo das pessoas; o 1 % mais rico está dentro dos 10 % "
                "mais ricos."
            ),
        )
    )

    # ---------------------------------------------------------------- o topo pelo IR
    try:
        ano_irpf, faixas = receita_irpf.grandes_numeros()
        grupos = agrupar_irpf(faixas)
        tot = GrupoIrpf(
            "Total",
            sum(g.declarantes for g in grupos),
            sum(g.renda for g in grupos),
            sum(g.dividendos for g in grupos),
        )
        topo = grupos[-1]
        ref = date(ano_irpf, 1, 1)
        fonte_irpf = f"{receita_irpf.FONTE}, ano-calendário {ano_irpf} (tabela 8)"
        cartoes += [
            Cartao(
                id="irpf-topo-renda",
                rotulo="Renda declarada do topo",
                valor=round(topo.renda / tot.renda * 100, 2),
                unidade="% da renda",
                casas=1,
                referencia=ref,
                periodicidade="A",
                detalhe=(
                    f"{br(topo.declarantes / 1e3, 1)} mil pessoas acima de 320 salários mínimos"
                ),
                fonte=fonte_irpf,
                procedencia="calculado",
                secao="desigualdade",
            ),
            Cartao(
                id="irpf-topo-dividendos",
                rotulo="Dividendos do topo",
                valor=round(topo.dividendos / tot.dividendos * 100, 2),
                unidade="% dos dividendos",
                casas=1,
                referencia=ref,
                periodicidade="A",
                detalhe=f"{br(topo.declarantes / tot.declarantes * 100, 2)} % de quem declara",
                fonte=fonte_irpf,
                procedencia="calculado",
                secao="desigualdade",
            ),
        ]
        tabelas.append(
            Tabela(
                id="desigualdade-irpf",
                titulo="Quanto da renda declarada fica com cada faixa",
                subtitulo=(
                    f"declarações de {ano_irpf + 1}, renda de {ano_irpf}; "
                    "faixas em salários mínimos por mês"
                ),
                colunas=[
                    "% de quem declara",
                    "% da renda declarada",
                    "% dos lucros e dividendos",
                    "renda média, R$ mil por ano",
                ],
                linhas=[
                    LinhaTabela(
                        rotulo=g.nome,
                        valores=[
                            round(g.declarantes / tot.declarantes * 100, 2),
                            round(g.renda / tot.renda * 100, 1),
                            round(g.dividendos / tot.dividendos * 100, 1),
                            round(g.renda / g.declarantes / 1e3, 0) if g.declarantes else None,
                        ],
                        unidade="",
                        casas=1,
                    )
                    for g in grupos
                ],
                fonte=fonte_irpf,
                nota=(
                    f"Só quem entregou a declaração ({br(tot.declarantes / 1e6)} milhões de "
                    "pessoas). Renda é a tributável, a de tributação exclusiva e a isenta "
                    "somadas. A PNAD subestima a renda do topo (quem ganha muito responde menos "
                    "e declara menos à pesquisa); o Imposto de Renda vê melhor essa ponta, mas "
                    "não vê quem não declara."
                ),
            )
        )
    except Exception as erro:  # a Receita fora do ar não derruba a seção
        topo = None
        avisos.append(f"IRPF: {erro}")

    # ---------------------------------------------------------------- pobreza
    try:
        pobreza = [(_ano(d), v) for d, v in ipeadata.serie(POBREZA_IPEA, date(1990, 1, 1))]
        extrema = [(_ano(d), v) for d, v in ipeadata.serie(EXTREMA_IPEA, date(1990, 1, 1))]
    except Exception as erro:
        pobreza, extrema = [], []
        avisos.append(f"pobreza do Ipea: {erro}")
    if pobreza and extrema:
        cartoes += [
            _cartao_anual(
                "pobreza",
                "Pobreza",
                pobreza,
                "% das pessoas",
                f"{IPEA} ({POBREZA_IPEA})",
                f"abaixo de US$ 8,30 por dia; {pobreza[0][0].year}: {br(pobreza[0][1], 0)} %",
                1,
            ),
            _cartao_anual(
                "extrema-pobreza",
                "Extrema pobreza",
                extrema,
                "% das pessoas",
                f"{IPEA} ({EXTREMA_IPEA})",
                f"abaixo de US$ 3 por dia; {extrema[0][0].year}: {br(extrema[0][1], 0)} %",
                1,
            ),
        ]
        graficos.append(
            grafico(
                "pobreza",
                "Pobreza e extrema pobreza",
                [
                    serie("pobreza", "Abaixo de US$ 8,30 por dia", pobreza, casas=1),
                    serie("extrema", "Abaixo de US$ 3,00 por dia", extrema, casas=1),
                ],
                unidade="% das pessoas",
                periodicidade="A",
                fonte=f"{IPEA} ({POBREZA_IPEA} e {EXTREMA_IPEA})",
                nota=(
                    "As linhas do Banco Mundial, em dólares de paridade do poder de compra de "
                    "2021: US$ 8,30 por dia por pessoa é a de pobreza para países de renda "
                    "média-alta, como o Brasil, e US$ 3,00, a de extrema pobreza. Até 2011, a "
                    "PNAD antiga; depois, a PNAD Contínua."
                ),
                largura="inteira",
            )
        )

    # ---------------------------------------------------------------- sexo e cor
    cor = ibge_sidra.series(POR_COR[0], POR_COR[1], classificacao=POR_COR[2], por="Cor")
    sexo = ibge_sidra.series(POR_SEXO[0], POR_SEXO[1], classificacao=POR_SEXO[2], por="Sexo")
    mulheres_homens = razao(sexo.get(MULHERES, []), sexo.get(HOMENS, []), 100)
    pretos_brancos = razao(cor.get(PRETA, []), cor.get(BRANCA, []), 100)
    pardos_brancos = razao(cor.get(PARDA, []), cor.get(BRANCA, []), 100)
    for id, rotulo, pontos, quem in (
        ("mulheres-homens", "Mulheres, contra homens", mulheres_homens, "7444"),
        ("pretos-brancos", "Pretos, contra brancos", pretos_brancos, "7441"),
        ("pardos-brancos", "Pardos, contra brancos", pardos_brancos, "7441"),
    ):
        if pontos:
            c = _cartao_anual(
                id,
                rotulo,
                pontos,
                "% da renda",
                f"{PNADA} (SIDRA {quem}); conta nossa",
                f"renda do trabalho; {pontos[0][0].year}: {br(pontos[0][1], 0)} %",
                1,
            )
            cartoes.append(c.model_copy(update={"procedencia": "calculado"}))
    graficos += [
        grafico(
            "diferencas",
            "Quanto ganham, para cada R$ 100 de quem ganha mais",
            [
                serie("mulheres", "Mulheres (contra homens)", mulheres_homens, casas=1),
                serie("pretos", "Pretos (contra brancos)", pretos_brancos, casas=1),
                serie("pardos", "Pardos (contra brancos)", pardos_brancos, casas=1),
            ],
            unidade="% da renda",
            periodicidade="A",
            fonte=f"{PNADA} (SIDRA 7441 e 7444); conta nossa",
            nota=(
                "A renda média do trabalho de um grupo em proporção da do outro. Compara médias: "
                "não separa o que vem de escolaridade, idade, região ou ocupação do que vem de "
                "discriminação."
            ),
        ),
        grafico(
            "renda-trabalho-grupos",
            "Renda do trabalho por sexo e cor",
            [
                serie("homens", "Homens", sexo.get(HOMENS, []), casas=0),
                serie("mulheres", "Mulheres", sexo.get(MULHERES, []), casas=0),
                serie("brancos", "Brancos", cor.get(BRANCA, []), casas=0),
                serie("pardos", "Pardos", cor.get(PARDA, []), casas=0),
                serie("pretos", "Pretos", cor.get(PRETA, []), casas=0),
            ],
            unidade="R$ por mês",
            casas=0,
            periodicidade="A",
            fonte=f"{PNADA} (SIDRA 7441 e 7444)",
            nota=(
                "Rendimento médio habitual de todos os trabalhos, das pessoas ocupadas de 14 "
                "anos ou mais, a preços do último ano."
            ),
        ),
    ]

    # ---------------------------------------------------------------- estados e países
    por_uf = ibge_sidra.series(GINI[0], GINI[1], nivel="n3/all", por="Unidade da Federação")
    tabelas.append(tabela_estados(por_uf, gini))
    try:
        graficos.append(dispersao_paises())
    except Exception as erro:
        avisos.append(f"Banco Mundial: {erro}")

    for aviso in avisos:
        print(f"  aviso: desigualdade: {aviso}")

    resumo = (
        f"O Gini da renda por pessoa foi de {br(gini[-1][1], 3)} em {ano}, entre os mais altos "
        f"do mundo; os 10 % mais ricos ficaram com {br(ricos10[-1][1])} % da renda e os 40 % "
        f"mais pobres, com {br(pobres40[-1][1])} %."
    )
    if gini[-1][1] < gini[0][1]:
        resumo += f" Em {gini[0][0].year}, o Gini era {br(gini[0][1], 3)}."
    if pobreza:
        resumo += (
            f" A pobreza (menos de US$ 8,30 por dia) atingiu {br(pobreza[-1][1], 1)} % das "
            f"pessoas em {pobreza[-1][0].year}."
        )
    return Secao(
        id="desigualdade",
        titulo="Desigualdade",
        resumo=resumo,
        cartoes=cartoes,
        graficos=graficos,
        tabelas=tabelas,
        gerado_em=ctx.agora(),
    )


def tabela_estados(por_uf: dict[str, list[Ponto]], brasil: list[Ponto]) -> Tabela:
    """O Gini de cada estado no primeiro ano, em 2019 e no último, do mais desigual ao menos."""
    if not brasil:
        raise RuntimeError("sem o Gini do Brasil")
    primeiro, ultimo = brasil[0][0], brasil[-1][0]
    meio = date(2019, 1, 1)
    anos = [primeiro, meio, ultimo] if primeiro < meio < ultimo else [primeiro, ultimo]
    linhas: list[tuple[float, LinhaTabela]] = []
    for cod, pontos in por_uf.items():
        if int(cod) not in SIGLA or not pontos:
            continue
        valores = dict(pontos)
        nome = next(n for c, _, n, _ in UFS if c == int(cod))
        ult = valores.get(ultimo)
        linhas.append(
            (
                -(ult or 0),
                LinhaTabela(
                    rotulo=nome,
                    valores=[valores.get(a) for a in anos],
                    unidade="",
                    casas=3,
                ),
            )
        )
    linhas.sort(key=lambda x: x[0])
    vb = dict(brasil)
    return Tabela(
        id="desigualdade-estados",
        titulo="Gini por estado",
        subtitulo=f"renda domiciliar por pessoa; do mais desigual em {ultimo.year} ao menos",
        colunas=[str(a.year) for a in anos],
        linhas=[
            LinhaTabela(rotulo="Brasil", valores=[vb.get(a) for a in anos], unidade="", casas=3),
            *(lin for _, lin in linhas),
        ],
        fonte=f"{PNADA} (SIDRA 7435)",
        nota=(
            "O Gini de cada estado mede a desigualdade dentro dele; o do Brasil é maior que o "
            "da maioria dos estados porque soma também a distância entre eles. O mapa está em "
            "Estados."
        ),
    )


def dispersao_paises() -> Grafico:
    """Um ponto por país: o PIB por habitante e o Gini mais novo (dos últimos dez anos)."""
    from sacibras.secoes.mundo import nome_do_pais

    hoje = date.today().year
    nomes = banco_mundial.paises()
    so = set(nomes)
    gini = banco_mundial.ultimos(banco_mundial.indicador(banco_mundial.GINI, hoje - 11, hoje), so)
    pib = banco_mundial.ultimos(
        banco_mundial.indicador(banco_mundial.PIB_POR_HABITANTE_PPC, hoje - 11, hoje), so
    )
    pontos: list[PontoDispersao] = []
    for iso, (_, g) in gini.items():
        if iso not in pib:
            continue
        try:
            nome = nome_do_pais(iso)
        except KeyError:
            nome = nomes[iso]
        pontos.append(
            PontoDispersao(chave=iso, nome=nome, x=round(pib[iso][1] / 1e3, 1), y=round(g / 100, 3))
        )
    if len(pontos) < 30 or "BRA" not in gini:
        raise RuntimeError(f"só {len(pontos)} países com Gini e PIB")
    ordem = sorted(gini, key=lambda i: -gini[i][1])
    posicao = ordem.index("BRA") + 1
    anos = sorted({a for a, _ in gini.values()})
    return grafico(
        "gini-paises",
        "Gini e renda dos países",
        [],
        unidade="",
        casas=1,
        periodicidade="A",
        fonte=(
            f"{banco_mundial.FONTE} ({banco_mundial.GINI} e {banco_mundial.PIB_POR_HABITANTE_PPC})"
        ),
        nota=(
            f"Cada ponto é um país, no ano mais novo com Gini ({anos[0]} a {anos[-1]}; o Brasil, "
            f"{gini['BRA'][0]}). O Brasil é o {posicao}º mais "
            f"desigual de {len(gini)} países. Em parte dos países (Índia, Indonésia e boa "
            "parte da África e da Ásia) o Banco Mundial mede o consumo, e não a renda, o que "
            "dá Gini menor."
        ),
        largura="inteira",
        dispersao=Dispersao(
            eixo_x=EixoDispersao(nome="PIB por habitante", unidade="US$ mil PPC de 2021", casas=1),
            eixo_y=EixoDispersao(nome="Gini", unidade="0 a 1", casas=3),
            pontos=pontos,
        ),
    )
