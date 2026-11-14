"""Pobreza e condições de vida: a pobreza, a fome, água, esgoto e lixo, a desigualdade (o
Gini e quem fica com quanto da renda), o topo e as diferenças por sexo e cor, e a comparação
entre estados e países.

Pedidos do Caio (14/11/2026): *"Coloque uma aba de Desigualdade no Sacibras [...] tem gini,
concentração de renda?"*; e depois *"Na verdade coloque algo como Pobreza, onde a
desigualdade vai ser um campo, tbm coloque índices de saneamento básico lá, fome, etc"*.

De onde vem cada coisa (tudo conferido em 14/11/2026):

- **IBGE, PNAD Contínua anual** (SIDRA). "Rendimento de todas as fontes" (sai em maio, com o
  ano anterior): o Gini da renda domiciliar por pessoa (7435) e o da renda do trabalho
  (7453); a fatia da renda de cada grupo de 10 % das pessoas, do 1 % e dos 5 % do topo
  (7527); a renda média por pessoa de cada grupo (7533); a renda do trabalho por cor (7441) e
  por sexo (7444). "Características dos domicílios": água (6731), esgoto (7192, desde 2019;
  antes a classificação era outra) e lixo (6736). "Segurança alimentar" (2023 e 2024, escala
  EBIA): 9552 (por situação do domicílio) e 9751 (por idade).
- **Ipea (Ipeadata)**: o Gini e a pobreza desde 1995, com a PNAD antiga emendada à
  Contínua (Souza e Hecksher, 2025), e a pobreza por estado (SIS do IBGE).
- **Receita Federal, Grandes Números do IRPF** (o mesmo arquivo de Impostos › Quem paga).
- **Banco Mundial**: o Gini dos outros países e as séries da FAO para o Brasil
  (subalimentação, o critério do Mapa da Fome, e insegurança alimentar grave).

Os códigos das classificações do SIDRA (825 água, 11558 esgoto, 67 lixo, 12404 segurança
alimentar, 58 idade, 1 situação) saíram tentando cada número contra a tabela: o catálogo do
IBGE não responde de fora do Brasil.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sacibras import leis
from sacibras.fontes import banco_mundial, ibge_sidra, ipeadata, receita_irpf
from sacibras.schema import (
    Cartao,
    Dispersao,
    EixoDispersao,
    Grafico,
    LinhaRef,
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

AGUA = (6731, 10117, "c1/6795/c825/46285")
"""% dos moradores em domicílios com água da rede geral de distribuição (classificação 825,
categoria 46285), Brasil urbano e rural (classificação 1, 6795)."""
ESGOTO = (7192, 10133, "c11558/47930,47931")
"""% dos moradores em domicílios com banheiro ligados à rede geral de esgoto ou pluvial
(47930) ou com fossa séptica ligada à rede (47931): somadas, o esgoto adequado."""
LIXO = (6736, 10117, "c67/4661,92864")
"""% dos moradores em domicílios com lixo coletado na porta (4661) ou em caçamba (92864)."""
SITUACAO = {"6795": "Brasil", "1": "Urbana", "2": "Rural"}
LUZ = (6738, 10141, "c1/all")
"""% dos moradores em domicílios com energia da rede geral em tempo integral."""
INTERNET = (7307, 10117, "c1/all/c688/48534")
"""% dos moradores em domicílios em que havia uso de internet (classificação 688)."""
LENHA = (6739, 10252, "c828/46299")
"""% dos moradores em domicílios que cozinham com lenha ou carvão, mesmo que também com gás
(classificação 828; um domicílio pode usar mais de um combustível). Sem abertura por
situação."""
PROGRAMAS = (7457, 9784, "c1035/49238,49239,82225")
"""% dos domicílios em que alguém recebe Bolsa Família (49238), BPC (49239) ou algum programa
social (82225), classificação 1035."""
RENDA_PROGRAMAS = (7458, 10816, "c1035/49238,49240")
"""Renda domiciliar por pessoa (R$, preços do último ano) de quem recebe Bolsa Família
(49238) e de quem não recebe (49240)."""
BOLSA, BPC, ALGUM_PROGRAMA, SEM_BOLSA = "49238", "49239", "82225", "49240"
FOME = (9552, 10117, "c12404/109102,109101")
"""% dos moradores em domicílios com insegurança alimentar grave (109102) e moderada (109101),
escala EBIA. A grave é a fome: alguém da casa passou um dia sem comer por falta de dinheiro."""
FOME_GRAVE, FOME_MODERADA = "109102", "109101"
FOME_IDADE = (9751, 10117, "c58/1140,100448,109110,104871,6798/c12404/109102")
IDADES = {
    "1140": "0 a 4 anos",
    "100448": "5 a 17 anos",
    "109110": "18 a 49 anos",
    "104871": "50 a 64 anos",
    "6798": "65 anos ou mais",
}
POBREZA_UF = "PNADCA_TXPNUF"
"""Ipea: % das pessoas abaixo de US$ 8,30 por dia, por estado (SIS do IBGE)."""

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
MAPA_DA_FOME = 2.5
"""A FAO põe no Mapa da Fome o país com mais de 2,5 % da população subalimentada."""

A_VISTA_CARTOES = ["pobreza", "fome", "esgoto", "gini"]
"""Os números da visão geral do assunto, um de cada parte principal."""
A_VISTA_GRAFICOS = ["pobreza"]
"""O gráfico da visão geral."""

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
        secao="pobreza",
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
            id="pobreza-decimos",
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
                secao="pobreza",
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
                secao="pobreza",
            ),
        ]
        tabelas.append(
            Tabela(
                id="pobreza-irpf",
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

    # ---------------------------------------------------------------- programas sociais
    try:
        c_prog, g_prog = programas_sociais()
        cartoes += c_prog
        graficos += g_prog
    except Exception as erro:
        avisos.append(f"programas sociais: {erro}")

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

    # ---------------------------------------------------------------- fome
    fome_grave: list[Ponto] = []
    try:
        c_fome, g_fome, t_fome, fome_grave = fome(avisos)
        cartoes += c_fome
        graficos += g_fome
        tabelas += t_fome
    except Exception as erro:
        avisos.append(f"fome: {erro}")

    # ---------------------------------------------------------------- saneamento
    esgoto: list[Ponto] = []
    try:
        c_san, g_san, t_san, esgoto = saneamento()
        cartoes += c_san
        graficos += g_san
        tabelas += t_san
    except Exception as erro:
        avisos.append(f"saneamento: {erro}")

    # ---------------------------------------------------------------- estados e países
    try:
        tabelas.append(tabela_estados(gini))
    except Exception as erro:
        avisos.append(f"estados: {erro}")
    try:
        graficos.append(dispersao_paises())
    except Exception as erro:
        avisos.append(f"Banco Mundial: {erro}")

    for aviso in avisos:
        print(f"  aviso: pobreza: {aviso}")

    partes: list[str] = []
    if pobreza and extrema:
        partes.append(
            f"Em {pobreza[-1][0].year}, {br(pobreza[-1][1])} % dos brasileiros viviam abaixo da "
            f"linha de pobreza (US$ 8,30 por dia) e {br(extrema[-1][1])} %, na extrema pobreza."
        )
    if fome_grave:
        partes.append(
            f"Em {fome_grave[-1][0].year}, {br(fome_grave[-1][1])} % moravam em casas com fome "
            "(insegurança alimentar grave)."
        )
    if esgoto:
        partes.append(
            f"{br(100 - esgoto[-1][1], 0)} % não tinham esgoto ligado à rede em "
            f"{esgoto[-1][0].year}."
        )
    partes.append(
        f"O Gini da renda foi de {br(gini[-1][1], 3)} em {ano}, entre os mais altos do mundo: os "
        f"10 % mais ricos ficaram com {br(ricos10[-1][1])} % da renda."
    )
    # A visão geral do assunto mostra os quatro primeiros números e o primeiro gráfico.
    cartoes.sort(key=lambda c: _ordem(c.id, A_VISTA_CARTOES))
    graficos.sort(key=lambda g: _ordem(g.id, A_VISTA_GRAFICOS))
    return Secao(
        id="pobreza",
        titulo="Pobreza e condições de vida",
        resumo=" ".join(partes),
        cartoes=cartoes,
        graficos=graficos,
        tabelas=tabelas,
        gerado_em=ctx.agora(),
    )


def _ordem(id: str, primeiros: list[str]) -> int:
    return primeiros.index(id) if id in primeiros else len(primeiros)


def _pct(tabela: tuple[int, int, str], por: str) -> dict[str, list[Ponto]]:
    return ibge_sidra.series(tabela[0], tabela[1], classificacao=tabela[2], por=por)


def fome(avisos: list[str]) -> tuple[list[Cartao], list[Grafico], list[Tabela], list[Ponto]]:
    """A insegurança alimentar da PNAD (2023 em diante) e a série da FAO para o Brasil."""
    por_situacao = ibge_sidra.series(
        FOME[0], FOME[1], classificacao=f"c1/all/{FOME[2].replace(',109101', '')}", por="Situação"
    )
    tipos = _pct(FOME, por="Situação de segurança")
    grave = tipos.get(FOME_GRAVE, [])
    if not grave:
        raise RuntimeError("SIDRA 9552 sem a insegurança grave")
    mod_ou_grave = soma(tipos, [FOME_GRAVE, FOME_MODERADA])
    fonte = f"{PNADA}, segurança alimentar (SIDRA 9552)"
    cartoes = [
        _cartao_anual(
            "fome",
            "Fome (insegurança grave)",
            grave,
            "% das pessoas",
            fonte,
            f"{grave[-2][0].year}: {br(grave[-2][1])} %" if len(grave) > 1 else "",
            1,
        ),
        _cartao_anual(
            "inseguranca-moderada-grave",
            "Comida faltando (moderada ou grave)",
            mod_ou_grave,
            "% das pessoas",
            fonte,
            f"{mod_ou_grave[-2][0].year}: {br(mod_ou_grave[-2][1])} %"
            if len(mod_ou_grave) > 1
            else "",
            1,
        ),
    ]
    graficos: list[Grafico] = []
    try:
        hoje = date.today().year
        fao = banco_mundial.serie_do_pais("BRA", banco_mundial.SUBALIMENTACAO, 2000, hoje)
        grave_fao = banco_mundial.serie_do_pais("BRA", banco_mundial.INSEGURANCA_GRAVE, 2000, hoje)
        sub = [(date(a, 1, 1), v) for a, v in fao]
        ano_sub, valor_sub = fao[-1]
        cartoes.append(
            Cartao(
                id="subalimentacao",
                rotulo="Subalimentação (FAO)",
                valor=valor_sub,
                unidade="% das pessoas",
                casas=1,
                referencia=date(ano_sub, 1, 1),
                periodicidade="A",
                texto="menos de 2,5 %" if valor_sub <= MAPA_DA_FOME else "",
                detalhe=(
                    "fora do Mapa da Fome"
                    if valor_sub <= MAPA_DA_FOME
                    else "no Mapa da Fome (acima de 2,5 %)"
                ),
                fonte=f"FAO, pelo {banco_mundial.FONTE} ({banco_mundial.SUBALIMENTACAO})",
                mini=[(d, round(v, 2)) for d, v in sub],
                secao="pobreza",
            )
        )
        graficos.append(
            grafico(
                "fome-fao",
                "Fome pela FAO, média de três anos",
                [
                    serie("sub", "Subalimentação", sub, casas=1),
                    serie(
                        "grave",
                        "Insegurança alimentar grave",
                        [(date(a, 1, 1), v) for a, v in grave_fao],
                        casas=1,
                    ),
                ],
                unidade="% das pessoas",
                periodicidade="A",
                fonte=(
                    f"FAO, pelo {banco_mundial.FONTE} ({banco_mundial.SUBALIMENTACAO} e "
                    f"{banco_mundial.INSEGURANCA_GRAVE})"
                ),
                linhas=[LinhaRef(valor=MAPA_DA_FOME, rotulo="Mapa da Fome")],
                nota=(
                    "Subalimentação: a parte da população que não come o bastante para as "
                    "necessidades mínimas de energia, pela conta da FAO. Acima de 2,5 % o país "
                    'entra no Mapa da Fome; quando a FAO publica "menos de 2,5 %", a série '
                    "mostra 2,5. Cada ano é a média dos três anos que terminam nele. A "
                    "insegurança grave é a da escala da FAO, outra pesquisa que a do IBGE."
                ),
                largura="inteira",
            )
        )
    except Exception as erro:
        avisos.append(f"FAO pelo Banco Mundial: {erro}")

    ultimo = grave[-1][0]
    idade = ibge_sidra.series(
        FOME_IDADE[0], FOME_IDADE[1], classificacao=FOME_IDADE[2], por="Grupo de idade"
    )
    linhas = [
        LinhaTabela(
            rotulo=nome,
            valores=[dict(por_situacao.get(cod, [])).get(d) for d in (ultimo, grave[0][0])],
            unidade="",
            casas=1,
        )
        for cod, nome in SITUACAO.items()
    ] + [
        LinhaTabela(
            rotulo=nome,
            valores=[dict(idade.get(cod, [])).get(d) for d in (ultimo, grave[0][0])],
            unidade="",
            casas=1,
        )
        for cod, nome in IDADES.items()
    ]
    tabela = Tabela(
        id="pobreza-fome",
        titulo="Fome por lugar e idade",
        subtitulo="% das pessoas em casas com insegurança alimentar grave",
        colunas=[str(ultimo.year), str(grave[0][0].year)],
        linhas=linhas,
        fonte=f"{PNADA}, segurança alimentar (SIDRA 9552 e 9751)",
        nota=(
            "Escala Brasileira de Insegurança Alimentar (EBIA): oito perguntas sobre os últimos "
            "três meses. Grave é quando alguém da casa, adulto ou criança, ficou sem comer ou "
            "passou fome por falta de dinheiro. A PNAD Contínua mede desde 2023; as pesquisas "
            "de antes (PNAD 2004, 2009 e 2013, POF 2018) não se comparam direto."
        ),
    )
    return cartoes, graficos, [tabela], grave


def saneamento() -> tuple[list[Cartao], list[Grafico], list[Tabela], list[Ponto]]:
    """Água da rede, esgoto ligado à rede e lixo coletado, em % dos moradores."""
    agua = {
        c: pts
        for c, pts in ibge_sidra.series(
            AGUA[0], AGUA[1], classificacao=AGUA[2].replace("c1/6795", "c1/all"), por="Situação"
        ).items()
    }
    esgoto_sit = ibge_sidra.series(
        ESGOTO[0], ESGOTO[1], classificacao=f"c1/all/{ESGOTO[2]}", por="Situação"
    )
    # Com "por" na situação, o SIDRA devolve as duas categorias de esgoto como linhas da mesma
    # situação: somar por situação e ano.
    esgoto = {c: _somar_por_ano(pts) for c, pts in esgoto_sit.items()}
    lixo_sit = ibge_sidra.series(
        LIXO[0], LIXO[1], classificacao=f"c1/all/{LIXO[2]}", por="Situação"
    )
    lixo = {c: _somar_por_ano(pts) for c, pts in lixo_sit.items()}
    luz = ibge_sidra.series(LUZ[0], LUZ[1], classificacao=LUZ[2], por="Situação")
    internet = ibge_sidra.series(
        INTERNET[0], INTERNET[1], classificacao=INTERNET[2], por="Situação"
    )
    lenha = ibge_sidra.serie(LENHA[0], LENHA[1], classificacao=LENHA[2])
    a, e, li = agua.get("6795", []), esgoto.get("6795", []), lixo.get("6795", [])
    if not (a and e and li):
        raise RuntimeError("SIDRA sem água, esgoto ou lixo do Brasil")
    fonte = f"{PNADA}, características dos domicílios"

    def det(pts: list[Ponto]) -> str:
        return f"{pts[0][0].year}: {br(pts[0][1])} %"

    meta = leis.META_SANEAMENTO
    net = internet.get("6795", [])

    def ate(valor: float) -> str:
        return f"meta: {br(valor, 0)} % até {meta.prazo.year}"

    cartoes = [
        _cartao_anual(
            "agua",
            "Água da rede",
            a,
            "% das pessoas",
            f"{fonte} (SIDRA 6731)",
            f"{det(a)}; {ate(meta.agua)}",
            1,
        ),
        _cartao_anual(
            "esgoto",
            "Esgoto ligado à rede",
            e,
            "% das pessoas",
            f"{fonte} (SIDRA 7192)",
            f"{det(e)}; {ate(meta.esgoto)}",
            1,
        ),
        _cartao_anual(
            "lixo", "Lixo coletado", li, "% das pessoas", f"{fonte} (SIDRA 6736)", det(li), 1
        ),
    ]
    if net:
        cartoes.append(
            _cartao_anual(
                "internet",
                "Internet em casa",
                net,
                "% das pessoas",
                f"{fonte} (SIDRA 7307)",
                det(net),
                1,
            )
        )
    if lenha:
        cartoes.append(
            _cartao_anual(
                "lenha",
                "Cozinha com lenha ou carvão",
                lenha,
                "% das pessoas",
                f"{fonte} (SIDRA 6739)",
                det(lenha),
                1,
            )
        )
    grafico_san = grafico(
        "saneamento",
        "Água, esgoto e lixo",
        [
            serie("agua", "Água da rede geral", a, casas=1),
            serie("esgoto", "Esgoto ligado à rede", e, casas=1),
            serie("lixo", "Lixo coletado", li, casas=1),
        ],
        unidade="% das pessoas",
        periodicidade="A",
        fonte=f"{fonte} (SIDRA 6731, 7192 e 6736); metas: {meta.referencia}",
        linhas=[
            LinhaRef(valor=meta.agua, rotulo=f"meta de água para {meta.prazo.year}"),
            LinhaRef(valor=meta.esgoto, rotulo=f"meta de esgoto para {meta.prazo.year}"),
        ],
        nota=(
            "Parte dos moradores que tem cada serviço em casa. Esgoto ligado à rede: rede geral "
            "de esgoto ou pluvial, ou fossa séptica ligada a ela; fossa não ligada, vala ou "
            "rio ficam de fora. O esgoto começa em 2019, quando o IBGE mudou as categorias. Em "
            "2020 e 2021 a pesquisa não perguntou sobre a casa. As metas são as do Marco Legal "
            f"do Saneamento ({meta.referencia}): {br(meta.agua, 0)} % da população com água "
            f"potável e {br(meta.esgoto, 0)} % com coleta e tratamento de esgoto até "
            f"{meta.prazo.strftime('%d/%m/%Y')}. A PNAD vê se o esgoto sai pela rede, não se é "
            "tratado: a parte tratada é menor que a linha do esgoto."
        ),
    )
    grafico_casa = grafico(
        "internet-lenha",
        "Internet, luz e fogão a lenha",
        [
            serie("internet", "Internet em casa", net, casas=1),
            serie("luz", "Luz da rede o tempo todo", luz.get("6795", []), casas=1),
            serie("lenha", "Cozinha com lenha ou carvão", lenha, casas=1),
        ],
        unidade="% das pessoas",
        periodicidade="A",
        fonte=f"{fonte} (SIDRA 7307, 6738 e 6739)",
        nota=(
            "Lenha ou carvão: a casa usa para cozinhar, mesmo que tenha gás também. A fumaça "
            "dentro de casa faz mal à saúde, e quem volta à lenha costuma ser quem não consegue "
            "pagar o botijão."
        ),
    )
    ultimo = a[-1][0]
    tabela = Tabela(
        id="pobreza-saneamento",
        titulo="Na cidade e no campo",
        subtitulo=f"% das pessoas com cada serviço em casa, {ultimo.year}",
        colunas=["Brasil", "Urbana", "Rural"],
        linhas=[
            LinhaTabela(
                rotulo=nome,
                valores=[dict(dados.get(c, [])).get(ultimo) for c in ("6795", "1", "2")],
                unidade="",
                casas=1,
            )
            for nome, dados in (
                ("Água da rede geral", agua),
                ("Esgoto ligado à rede", esgoto),
                ("Lixo coletado", lixo),
                ("Luz da rede o tempo todo", luz),
                ("Internet em casa", internet),
                ("Cozinha com lenha ou carvão", {"6795": lenha}),
            )
        ],
        fonte=f"{fonte} (SIDRA 6731, 7192, 6736, 6738, 7307 e 6739)",
        nota=(
            "No campo, poço e fossa são comuns e nem sempre ruins. A lenha não sai aberta entre "
            "cidade e campo."
        ),
    )
    return cartoes, [grafico_san, grafico_casa], [tabela], e


def programas_sociais() -> tuple[list[Cartao], list[Grafico]]:
    """Bolsa Família, BPC e algum programa social, em % das casas, e a renda de quem recebe."""
    programas = _pct(PROGRAMAS, por="Recebimento")
    renda = _pct(RENDA_PROGRAMAS, por="Recebimento")
    bolsa = programas.get(BOLSA, [])
    if not bolsa:
        raise RuntimeError("SIDRA 7457 sem o Bolsa Família")
    com, sem = renda.get(BOLSA, []), renda.get(SEM_BOLSA, [])
    rendas = (
        f"R$ {br(com[-1][1], 0)} por pessoa; sem ele, R$ {br(sem[-1][1], 0)}" if com and sem else ""
    )
    cartao_bolsa = _cartao_anual(
        "bolsa-familia",
        "Casas com Bolsa Família",
        bolsa,
        "% das casas",
        f"{PNADA} (SIDRA 7457 e 7458)",
        rendas,
        1,
    )
    grafico_prog = grafico(
        "programas-sociais",
        "Casas que recebem programas sociais",
        [
            serie("algum", "Algum programa", programas.get(ALGUM_PROGRAMA, []), casas=1),
            serie("bolsa", "Bolsa Família", bolsa, casas=1),
            serie("bpc", "BPC", programas.get(BPC, []), casas=1),
        ],
        unidade="% das casas",
        periodicidade="A",
        fonte=f"{PNADA} (SIDRA 7457 e 7458)",
        nota=(
            "Parte dos domicílios em que algum morador recebeu o programa. BPC: o benefício de "
            "um salário mínimo a idosos e pessoas com deficiência de baixa renda. "
            + (
                f"Em {com[-1][0].year}, a renda por pessoa de quem recebe o Bolsa Família, já "
                f"com o benefício, era R$ {br(com[-1][1], 0)} por mês; a de quem não recebe, "
                f"R$ {br(sem[-1][1], 0)}."
                if com and sem
                else ""
            )
        ),
    )
    return [cartao_bolsa], [grafico_prog]


def _somar_por_ano(pontos: list[Ponto]) -> list[Ponto]:
    por_ano: dict[date, float] = {}
    for d, v in pontos:
        por_ano[d] = por_ano.get(d, 0.0) + v
    return sorted(por_ano.items())


def _por_uf(series: dict[str, list[Ponto]]) -> dict[str, float]:
    """{sigla: valor mais novo} das séries por código de UF do IBGE."""
    return {SIGLA[int(c)]: pts[-1][1] for c, pts in series.items() if int(c) in SIGLA and pts}


def tabela_estados(gini_brasil: list[Ponto]) -> Tabela:
    """Uma linha por estado: pobreza, fome, esgoto e água, do mais pobre ao menos."""
    ufs = "n3/all"
    fome_uf = _por_uf(
        ibge_sidra.series(
            FOME[0],
            FOME[1],
            classificacao="c1/6795/c12404/109102",
            nivel=ufs,
            periodos="last 1",
            por="Unidade",
        )
    )
    esgoto_por_uf = ibge_sidra.series(
        ESGOTO[0],
        ESGOTO[1],
        classificacao=f"c1/6795/{ESGOTO[2]}",
        nivel=ufs,
        periodos="last 1",
        por="Unidade",
    )
    esgoto_uf = _por_uf({c: _somar_por_ano(p) for c, p in esgoto_por_uf.items()})
    agua_uf = _por_uf(
        ibge_sidra.series(
            AGUA[0], AGUA[1], classificacao=AGUA[2], nivel=ufs, periodos="last 1", por="Unidade"
        )
    )
    try:
        pobreza_uf = _por_uf(
            {
                c: p
                for c, p in ipeadata.por_territorio(POBREZA_UF, date(2012, 1, 1)).items()
                if len(c) == 2
            }
        )
    except Exception:
        pobreza_uf = {}
    linhas = []
    for _, sigla, nome, _ in UFS:
        linhas.append(
            LinhaTabela(
                rotulo=nome,
                valores=[
                    _arred(pobreza_uf.get(sigla), 1),
                    fome_uf.get(sigla),
                    _arred(esgoto_uf.get(sigla), 1),
                    agua_uf.get(sigla),
                ],
                unidade="",
                casas=1,
            )
        )
    linhas.sort(key=lambda li: -(li.valores[0] or 0))
    return Tabela(
        id="pobreza-estados",
        titulo="Os estados lado a lado",
        subtitulo="% das pessoas; em ordem de pobreza, da maior para a menor",
        colunas=["pobreza", "fome", "esgoto", "água"],
        linhas=linhas,
        fonte=(
            f"{PNADA} (SIDRA 9552, 7192 e 6731); pobreza: {IPEA}, a partir da Síntese de "
            f"Indicadores Sociais do IBGE ({POBREZA_UF})"
        ),
        nota=(
            "O ano mais novo de cada fonte. Pobreza: abaixo de US$ 8,30 por dia. Fome: "
            "insegurança alimentar grave. Esgoto: ligado à rede; água: da rede geral. O Gini de "
            "cada estado (o do Brasil é "
            f"{br(gini_brasil[-1][1], 3)}) e a pobreza também estão no mapa de Estados."
        ),
    )


def _arred(v: float | None, casas: int) -> float | None:
    return None if v is None else round(v, casas)


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
