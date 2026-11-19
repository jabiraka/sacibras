"""Números lidos à mão em relatório oficial que não tem API nem planilha: a nota de crédito
do país, as elasticidades da dívida, o teste de estresse dos bancos e o que o Banco Central
estima que a Selic faz com a inflação e com o dólar.

Mesma regra de `leis.py`: só entra o que foi lido na fonte, com a data da leitura e o
endereço ao lado. Cada bloco diz quando precisa ser lido de novo.

Só entra o que sai com regularidade e com método (Caio, 15/11/2026: *"elimine tudo oq não for
publicado regularmente e com metodologia, vamos manter apenas as nossas estimativas nesse
caso"*): estudo, artigo ou nota técnica de uma vez só fica de fora. Saíram por isso os
multiplicadores de imposto (FMI e Ipea), a incidência por décimo de renda (Ipea), as notas da
Fazenda de 2024 sobre a alíquota da reforma e a proposta de Lara Resende no simulador da
Selic. O simulador da Selic fica (Caio, mesmo dia): os modelos semiestruturais são os do BC,
usados em todo Relatório de Política Monetária.
O prazo de cada releitura mora em `leituras.py` (o build e o workflow "Prazos de releitura"
avisam quando vence).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# ------------------------------------------------------------------ nota de crédito

# Degraus em relação ao menor grau de investimento (BBB−/Baa3 = 0). As três agências usam
# escalas equivalentes: BB+ = Ba1, BB = Ba2, BB− = Ba3, B+ = B1, B = B2.
DEGRAU = {
    "BBB": 1,
    "Baa2": 1,
    "BBB-": 0,
    "Baa3": 0,
    "BB+": -1,
    "Ba1": -1,
    "BB": -2,
    "Ba2": -2,
    "BB-": -3,
    "Ba3": -3,
    "B+": -4,
    "B1": -4,
    "B": -5,
    "B2": -5,
}

# Dívida de longo prazo em moeda estrangeira: só as mudanças de nota (a perspectiva fica de
# fora), com a data que o Tesouro Nacional registra. Lido em 14/11/2026:
# - até 24/02/2016: "Histórico da Classificação para a Dívida de Longo Prazo", PDF do Tesouro
#   (tesouro.fazenda.gov.br/documents/10180/265991/Histórico_Ratings.pdf, cópia de 06/05/2016
#   no Internet Archive), lido pela imagem das duas páginas;
# - de 2016 a mai/2024: a consulta "Histórico da classificação de risco da dívida" do Tesouro
#   (sisweb.tesouro.gov.br/apex/f?p=2810:2, cópias de 26/04/2018 e 08/05/2024 no Internet
#   Archive; o sistema respondia 503 em 14/11/2026);
# - Moody's de 01/10/2024: comunicado do Tesouro em gov.br/tesouronacional ("elevou a nota de
#   crédito soberano do Brasil de Ba2 para Ba1").
# LER DE NOVO quando o sisweb voltar e a cada ato de agência: depois de 30/05/2025 não foi
# achado comunicado do Tesouro.
NOTAS: dict[str, list[tuple[date, str]]] = {
    "S&P": [
        (date(1994, 11, 30), "B"),
        (date(1995, 7, 18), "B+"),
        (date(1997, 4, 2), "BB-"),
        (date(1999, 1, 14), "B+"),
        (date(2001, 1, 3), "BB-"),
        (date(2002, 7, 2), "B+"),
        (date(2004, 9, 17), "BB-"),
        (date(2006, 2, 28), "BB"),
        (date(2007, 5, 16), "BB+"),
        (date(2008, 4, 30), "BBB-"),
        (date(2011, 11, 17), "BBB"),
        (date(2014, 3, 21), "BBB-"),
        (date(2015, 9, 9), "BB+"),
        (date(2016, 2, 17), "BB"),
        (date(2018, 1, 11), "BB-"),
        (date(2023, 12, 19), "BB"),
    ],
    "Fitch": [
        (date(1994, 12, 1), "B+"),
        (date(1999, 1, 26), "B"),
        (date(2000, 2, 22), "B+"),
        (date(2000, 5, 19), "BB-"),
        (date(2002, 6, 20), "B+"),
        (date(2002, 10, 21), "B"),
        (date(2003, 11, 6), "B+"),
        (date(2004, 9, 28), "BB-"),
        (date(2006, 6, 28), "BB"),
        (date(2007, 5, 10), "BB+"),
        (date(2008, 5, 29), "BBB-"),
        (date(2011, 4, 4), "BBB"),
        (date(2015, 10, 15), "BBB-"),
        (date(2015, 12, 16), "BB+"),
        (date(2016, 5, 5), "BB"),
        (date(2018, 2, 23), "BB-"),
        (date(2023, 7, 26), "BB"),
    ],
    "Moody's": [
        (date(1994, 11, 30), "B1"),
        (date(1998, 9, 3), "B2"),
        (date(2000, 10, 16), "B1"),
        (date(2002, 8, 12), "B2"),
        (date(2004, 9, 9), "B1"),
        (date(2005, 10, 12), "Ba3"),
        (date(2006, 8, 31), "Ba2"),
        (date(2007, 8, 1), "Ba1"),
        (date(2009, 9, 22), "Baa3"),
        (date(2011, 6, 24), "Baa2"),
        (date(2015, 8, 11), "Baa3"),
        (date(2016, 2, 24), "Ba2"),
        (date(2024, 10, 1), "Ba1"),
    ],
}

# A perspectiva vigente, pelo último ato que o Tesouro publicou (comunicados lidos em
# 14/11/2026): S&P, 19/12/2023 ("de BB- para BB, com perspectiva estável"); Fitch,
# 26/07/2023 ("de BB- para BB, com perspectiva estável"); Moody's, 30/05/2025 ("manteve a
# nota [...] em Ba1, alterando a perspectiva do rating de positiva para estável").
PERSPECTIVA = {"S&P": "estável", "Fitch": "estável", "Moody's": "estável"}
ULTIMO_ATO_LIDO = date(2025, 5, 30)
FONTE_NOTAS = (
    "Tesouro Nacional: Histórico da Classificação para a Dívida de Longo Prazo, consulta do "
    "histórico da classificação de risco e comunicados (lidos em 14/11/2026)"
)


# ------------------------------------------------------------------ elasticidades da dívida


@dataclass(frozen=True)
class Elasticidade:
    """Quanto a dívida muda (pp do PIB) com o choque, pela conta do Banco Central."""

    choque: str
    liquida: float
    bruta: float


# Nota para a imprensa "Estatísticas fiscais" de 29/10/2026 (dados de set/2026), seção 3,
# quadro "Elasticidades da DLSP e DBGG" (o quadro é imagem no PDF; lido em 14/11/2026 em
# bcb.gov.br/content/estatisticas/hist_estatisticasfiscais/, arquivo
# 202610_Texto_de_estatisticas_fiscais.pdf):
#   Desvalorização de 1% na taxa de câmbio:   DLSP -0,07 p.p. PIB; DBGG 0,07
#   Redução de 1 p.p. na taxa Selic:          DLSP -0,53;          DBGG -0,48
#   Redução de 1 p.p. nos índices de preços:  DLSP -0,16;          DBGG -0,15
# Notas do quadro: "2/ Impactos são simétricos no caso de valorização cambial, redução de taxa
# Selic e aumento de índices de preços. 3/ Variação mantida por doze meses."
# Aqui Selic e preços vão como ALTA (o sinal trocado, pela simetria da nota 2).
# LER DE NOVO todo mês: o BC atualiza o quadro a cada nota.
ELASTICIDADES_EM = date(2026, 9, 1)
ELASTICIDADES = [
    Elasticidade("Dólar 1 % mais caro", -0.07, 0.07),
    Elasticidade("Selic 1 pp mais alta, por 12 meses", 0.53, 0.48),
    Elasticidade("Índices de preços 1 pp mais altos, por 12 meses", 0.16, 0.15),
]
ELASTICIDADE_DOLAR, ELASTICIDADE_SELIC, ELASTICIDADE_PRECOS = ELASTICIDADES
FONTE_ELASTICIDADES = (
    "Banco Central, nota para a imprensa Estatísticas fiscais de 29/10/2026, quadro "
    "Elasticidades da DLSP e DBGG"
)

# ------------------------------------------------------------------ estresse dos bancos

# Relatório de Estabilidade Financeira, v. 25, n. 2, outubro de 2026 (data-base jun/2026),
# seção 1.2.5, p. 50 (lido em 14/11/2026 em
# bcb.gov.br/content/publicacoes/ref/202610/RELESTAB202610-refPub.pdf): "A maior necessidade
# de capital seria de 3,5% do PR atual do sistema no oitavo trimestre da simulação no cenário
# de crise de confiança"; "Instituições que representam 81,9% do ativo total do sistema
# continuariam apresentando índices de capitalização acima do mínimo regulamentar de 10,5%";
# "No cenário de recessão aguda, a necessidade atinge 1,7% do PR". Nota 45: "realizados com
# 106 instituições, que representam 97,31% do ativo total do sistema".
# LER DE NOVO a cada edição (duas por ano: maio e outubro).
ESTRESSE_DOS_BANCOS = (
    "O Banco Central faz o teste dos bancos duas vezes por ano. No Relatório de Estabilidade "
    "Financeira de outubro de 2026 (p. 50), no pior cenário, o de crise de confiança, a "
    "necessidade de capital chega a 3,5 % do patrimônio de referência do sistema, e "
    "instituições com 81,9 % dos ativos seguem acima do mínimo regulamentar de 10,5 %; no "
    "de recessão aguda, 1,7 %."
)
BASILEIA_MINIMO = 10.5
BASILEIA_MINIMO_FONTE = (
    "Mínimo regulamentar, com o adicional (Banco Central, Relatório de Estabilidade "
    "Financeira, out/2026, p. 50)"
)

# ------------------------------------------------------------------ o efeito da Selic

# Relatório de Inflação de junho de 2024, boxe "Atualização dos modelos semiestruturais de
# pequeno porte", p. 97 a 106 (lido em 14/11/2026 em
# bcb.gov.br/content/ri/relatorioinflacao/202406/ri202406p.pdf). É a versão vigente: os
# Relatórios de Política Monetária de março e de junho de 2026 ainda remetem a este boxe.
# p. 102: "A taxa Selic anualizada sobe 1 p.p. por quatro trimestres e depois segue
#   comportamento baseado na regra de Taylor (Gráfico 1A). A inflação do IPCA cai, atingindo,
#   no acumulado em quatro trimestres, um efeito máximo estimado de 0,27 p.p. e 0,24 p.p.
#   segundo os modelos agregado e desagregado, respectivamente, alcançados no quarto trimestre
#   após o choque inicial. Considerando os grupos do modelo desagregado, a inflação de
#   serviços é a que responde de forma mais intensa e persistente (Gráfico 1C)".
# p. 106: "A transmissão de um choque de política monetária se faz por vários canais no
#   modelo. Além do impacto sobre a demanda agregada e hiato do produto, representado na curva
#   IS, o choque também afeta a inflação pelo canal de câmbio da equação da UIP e mais
#   indiretamente via impacto nas expectativas de inflação."
# Os caminhos trimestre a trimestre (Gráficos 1A, 1B e 1C, p. 105) são desenho vetorial no
# PDF: os pontos saíram das coordenadas do traço, não do olho, com a escala tirada das marcas
# dos eixos e conferida pelos 0,27 e 0,24 do texto; arredondados a 0,01. Índice = trimestres
# depois do começo (0 a 16).
# LER DE NOVO quando o BC publicar outra atualização dos modelos (o Relatório de Política
# Monetária sai em março, junho, setembro e dezembro; procurar o boxe pelo nome).
EFEITO_SELIC_EM = date(2024, 6, 27)
SELIC_CAMINHO = [0.0, 1.0, 1.0, 1.0, 1.0, 0.88, 0.70, 0.50, 0.31, 0.15, 0.02]
SELIC_CAMINHO += [-0.08, -0.15, -0.19, -0.21, -0.22, -0.22]
IPCA_MODELO_AGREGADO = [0.0, -0.09, -0.15, -0.20, -0.27, -0.24, -0.24, -0.25, -0.24]
IPCA_MODELO_AGREGADO += [-0.22, -0.21, -0.20, -0.19, -0.19, -0.18, -0.17, -0.16]
IPCA_MODELO_DESAGREGADO = [0.0, -0.08, -0.13, -0.18, -0.24, -0.22, -0.22, -0.21, -0.20]
IPCA_MODELO_DESAGREGADO += [-0.18, -0.17, -0.17, -0.16, -0.16, -0.15, -0.15, -0.14]


# A faixa de erro. O boxe de 2024 mostra os dois modelos, mas não a faixa; a última que o BC
# publicou está no Relatório de Inflação de dezembro de 2021, boxe "Revisão do modelo agregado
# de pequeno porte", p. 77 (lido em 14/11/2026 em
# bcb.gov.br/content/ri/relatorioinflacao/202112/ri202112p.pdf), para a versão anterior do mesmo
# modelo: "um aumento temporário de 1 p.p. na taxa Selic, com duração de quatro trimestres, gera
# um efeito máximo de redução na inflação do IPCA, acumulada em quatro trimestres, de
# aproximadamente 0,33 p.p., alcançado no sexto trimestre após o choque inicial". O Gráfico 2b
# traz a resposta e o "Intervalo de credibilidade de 90%"; pontos lidos das coordenadas do
# traço, escala conferida pelo 0,33 do texto. Os dois modelos de 2024 ficam dentro desta faixa
# nos 16 trimestres (o teste confere).
# MENOR = a ponta de menos efeito; MAIOR = a de mais efeito.
FAIXA_DO_IPCA_EM = date(2021, 12, 16)
IPCA_MODELO_2021 = [0.0, -0.10, -0.15, -0.23, -0.31, -0.30, -0.33, -0.33, -0.33]
IPCA_MODELO_2021 += [-0.31, -0.30, -0.28, -0.27, -0.25, -0.23, -0.21, -0.20]
IPCA_FAIXA_90_MENOR = [0.0, -0.03, -0.06, -0.11, -0.17, -0.19, -0.21, -0.20, -0.19]
IPCA_FAIXA_90_MENOR += [-0.16, -0.14, -0.11, -0.10, -0.08, -0.07, -0.07, -0.06]
IPCA_FAIXA_90_MAIOR = [0.0, -0.19, -0.26, -0.40, -0.52, -0.48, -0.53, -0.53, -0.55]
IPCA_FAIXA_90_MAIOR += [-0.56, -0.56, -0.55, -0.54, -0.53, -0.51, -0.49, -0.47]

# A própria estimativa do BC mudou de versão para versão (o efeito máximo de 1 pp por um ano):
# - Relatório de Inflação de set/2020, boxe "Novo modelo agregado de pequeno porte com
#   estimação bayesiana": "efeito máximo de redução na inflação, acumulada em quatro
#   trimestres, de aproximadamente 0,3 p.p.";
# - de mar/2021, boxe "Novo modelo desagregado de pequeno porte" (p. 81): "de 0,26 p.p.";
# - de dez/2021: 0,33 p.p.; de jun/2024: 0,27 e 0,24 p.p.
IPCA_NAS_VERSOES = [
    ("set/2020, modelo agregado", -0.30),
    ("mar/2021, modelo desagregado", -0.26),
    ("dez/2021, modelo agregado", -0.33),
]
FONTE_FAIXA_DO_IPCA = (
    "Banco Central, Relatório de Inflação de dez/2021, boxe Revisão do modelo agregado de "
    "pequeno porte (p. 77, intervalo de credibilidade de 90 %)"
)


@dataclass(frozen=True)
class EfeitoPorGrupo:
    """O maior efeito de 1 pp a mais de Selic por um ano num grupo de preços do IPCA."""

    grupo: str
    maximo: float
    trimestre: int


# Gráfico 1C (p. 105), modelo desagregado: o ponto mais baixo de cada curva.
IPCA_POR_GRUPO = [
    EfeitoPorGrupo("Serviços", -0.37, 9),
    EfeitoPorGrupo("Alimentação no domicílio", -0.36, 4),
    EfeitoPorGrupo("Bens industriais", -0.25, 5),
]

# O dólar, no mesmo boxe. p. 101, equação (4): "Δe_t = Δe_t^ppc − δ (i_t^dif − i_t−1^dif) +
# ε_t^e", com (4.1) "i_t^dif = i_t − (i_t* + CDS_t)": "relaciona a variação da taxa de câmbio
# com a variação do diferencial de juros domésticos e externos (no caso, a Fed Funds rate),
# ajustados pelo prêmio de risco [...] As variações Δe_t e Δe_t^ppc são trimestrais, e as taxas
# i_t, i_t* e CDS_t estão anualizadas." Tabela 1 (p. 103): "δ, Diferencial de taxa de juros
# interna e externa: moda 1,90; intervalo de credibilidade (90%) [0,77; 3,22]".
# Ou seja: 1 pp a mais de Selic, com o juro de fora e o risco parados, é um dólar 1,90 % mais
# barato no trimestre da mudança, e ele fica assim enquanto a distância de juros durar.
DOLAR_POR_PP_DE_SELIC = -1.90
DOLAR_POR_PP_DE_SELIC_FAIXA = (-3.22, -0.77)

# O caminho de volta, do dólar para os preços. Mesmo boxe, p. 103: "Uma depreciação permanente
# do câmbio de 10%, por sua vez, produz um efeito máximo na variação acumulada em quatro
# trimestres do IPCA de aproximadamente 0,96 p.p. e 0,87 p.p. [...] segundo os modelos agregado
# e desagregado". E o Relatório de Política Monetária de março de 2026, boxe "Repasse cambial:
# estimativas por projeções locais", p. 66 (lido em 14/11/2026 em
# bcb.gov.br/content/ri/relatorioinflacao/202603/rpm202603p.pdf): "obtêm-se coeficientes de
# 0,10 e 0,16 para o índice geral, nos horizontes de 12 e 24 meses, respectivamente. Dessa
# forma, uma desvalorização de 10% do real implicaria aumentos de 1 p.p. na inflação acumulada
# nos 12 meses subsequentes e de 1,6 p.p. no acumulado de 24 meses."
# A resposta do IPCA à Selic (acima) já traz este caminho dentro: não se soma de novo.
IPCA_POR_10_DE_DOLAR_MODELOS = (0.96, 0.87)
IPCA_POR_10_DE_DOLAR_12M = 1.0
IPCA_POR_10_DE_DOLAR_24M = 1.6

FONTE_EFEITO_SELIC = (
    "Banco Central, Relatório de Inflação de jun/2024, boxe Atualização dos modelos "
    "semiestruturais de pequeno porte (p. 101 a 105)"
)
FONTE_REPASSE_CAMBIAL = (
    "Banco Central, Relatório de Política Monetária de mar/2026, boxe Repasse cambial: "
    "estimativas por projeções locais (p. 66)"
)

# ------------------------------------------------------------------ alíquotas da reforma

# Quanto vai ser a alíquota cheia do IBS mais a CBS ninguém sabe: o Senado fixa a de cada ano
# no ano anterior (ADCT, art. 130), e a de 2033 só no fim da transição. O que existe são contas
# oficiais, lidas em 14/11/2026:
# As notas técnicas da Fazenda de jul e ago/2024 (26,47 % e +1,47 ponto) saíram em 15/11/2026:
# foram contas de uma vez só, sem série (Caio: só fica o que sai com regularidade e método).
# Ficam as duas contas que a lei manda refazer todo ano:
# 1. Comitê Gestor do IBS, Resolução CGIBS nº 14, de 29/7/2026 (DOU de 31/7/2026, seção 3, p.
#    188-189), anexo, quadro 2 (cgibs.gov.br/upload/arquivos/202607/31144942-...pdf): "Alíquota
#    total inicial (SERT) 26,50%; IBS correspondente 17,70%; Nova alíquota total estimada
#    27,91%; [...] IBS atualizado 18,7%"; "as estimativas públicas passaram a indicar alíquota
#    de referência em torno de 28%".
# 2. Agência Senado, 28/10/2026 e 3/11/2026 (www12.senado.leg.br/noticias/materias/2026/10/28/
#    reforma-tributaria-tcu-calcula-aliquota-da-cbs-em-11-3-para-2027 e .../2026/11/03/
#    senado-deve-receber-calculo-da-cbs-na-proxima-terca-para-definir-aliquota): "O Tribunal de
#    Contas da União (TCU) aprovou nesta quarta-feira (28) uma proposta para que a [CBS] seja
#    de 11,3% no ano que vem. O valor da alíquota precisa ser chancelado pelo Senado até
#    dezembro. Caso isso não ocorra, a alíquota apresentada pelo TCU será efetivada a partir de
#    1º de janeiro de 2027."; "percentual superior à estimativa de 9,21% considerada
#    anteriormente"; "a alíquota de referência do IBS ainda não foi definida". O portal do TCU
#    não abriu daqui: reler o acórdão no PC.
# LER DE NOVO: a resolução do Senado com a CBS de 2027 (o prazo é dezembro de 2026) e, a cada
# ano, as alíquotas do ano seguinte; o IBS de referência só aparece em 2028, para 2029.
CBS_REFERENCIA_2027 = 11.3
CBS_REFERENCIA_2027_EM = date(2026, 10, 28)
CBS_ESTIMATIVA_ANTERIOR = 9.21
ALIQUOTA_COMITE_GESTOR = 27.91
IBS_COMITE_GESTOR = 18.7
ALIQUOTA_COMITE_GESTOR_EM = date(2026, 7, 29)
FONTE_ALIQUOTA_COMITE = "Comitê Gestor do IBS, Resolução nº 14, de 29/7/2026, anexo, quadro 2"
FONTE_CBS_2027 = (
    "Tribunal de Contas da União, cálculo aprovado em 28/10/2026 (Agência Senado, 28/10 e "
    "3/11/2026); o Senado fixa por resolução"
)

# ------------------------------------------------------------------ previsto no ano


@dataclass(frozen=True)
class ReceitaPrevista:
    """O que o governo projeta arrecadar no ano, em R$ bilhões: no orçamento e na avaliação
    bimestral mais nova."""

    linha: str
    rtn: str
    """A linha do RTN (aba 1.1) com o realizado."""
    loa: float
    avaliacao: float


# Receita de 2026. LOA: planilha "quadros de apoio" do Relatório de Avaliação do 2º bimestre de
# 2026 (gov.br/planejamento, relatórios de avaliação fiscal), aba "Tabela 1", coluna "LOA 2026",
# em R$ milhões: "Receita Administrada pela RFB/MF, exceto RGPS e líquida de incentivos
# fiscais" 2.040.990,1; "Arrecadação Líquida para o RGPS" 793.153,5. Avaliação do 4º bimestre:
# a mesma Nota Informativa da Conorf/Senado de 25/9/2026 usada em `leis.AVALIACOES_2026`
# (Tabela 1): "Receita Administrada pela RFB/MF, exceto RGPS e líquida de incentivos fiscais
# 2.079,8 [3º bim.] 2.065,7 [4º bim.]"; "Arrecadação Líquida para o RGPS 784,0 786,4". Lidos em
# 14/11/2026. LER DE NOVO a cada bimestre (o do 5º sai até 22/11) e trocar o ano em janeiro.
ANO_DA_RECEITA_PREVISTA = 2026
AVALIACAO_DA_RECEITA = "4º bimestre"
RECEITA_PREVISTA = [
    ReceitaPrevista("Tributos administrados pela Receita", "receita_rfb", 2041.0, 2065.7),
    ReceitaPrevista("Contribuição ao INSS", "arrecadacao_rgps", 793.2, 786.4),
]

# ------------------------------------------------------------------ dívida ativa

# Estoque: Projeto da LDO 2027, Anexo V (Riscos Fiscais), lido em 14/11/2026 em
# gov.br/planejamento (orçamentos anuais, 2027, PLDO). P. 15: "O estoque da Dívida Ativa da
# União alcançou o valor de R$ 3.226,1 bilhões em 2025 referentes a mais de 29,3 milhões de
# débitos, titularizados por 7,9 milhões de contribuintes. Desse valor, aproximadamente 78,0%
# (R$ 2.517,8 bilhões) foram considerados perdas. Há uma expectativa de recuperação/arrecadação
# de R$ 708,3 bilhões dentro dos próximos 15 anos". Tabela 39 (fonte: BGU e PGFN), linha
# Total: 2.743,1 (2023), 2.990,2 (2024), 3.226,1 (2025).
# Recuperado: PGFN em Números 2026, p. 19: "No exercício de 2025, o órgão atingiu novo recorde
# com R$ 66,1 bilhões recuperados da dívida ativa da União, valor 10% maior que o patamar de
# 2024"; PGFN em Números 2025: R$ 59,9 bi em 2024. LER DE NOVO a cada PLDO (abril) e a cada
# PGFN em Números (março).
DIVIDA_ATIVA_ESTOQUE = {2023: 2743.1, 2024: 2990.2, 2025: 3226.1}  # R$ bilhões
DIVIDA_ATIVA_RECUPERADO = {2024: 59.9, 2025: 66.1}  # R$ bilhões
DIVIDA_ATIVA_PERDA = 78.0  # % do estoque de 2025 considerado perda
DIVIDA_ATIVA_A_RECUPERAR = 708.3  # R$ bilhões esperados em 15 anos
FONTE_DIVIDA_ATIVA = (
    "Projeto da LDO 2027, Anexo de Riscos Fiscais (tabela 39, com dados do Balanço Geral da "
    "União e da PGFN); PGFN em Números 2025 e 2026"
)

# ------------------------------------------------------------------ riscos fiscais da União

# Projeto da LDO 2027, Anexo V (Riscos Fiscais), elaborado pela STN/MF e enviado em abril de
# 2026 (art. 4º, § 3º, da LRF). Lido em 15/11/2026 em gov.br/planejamento, orçamentos anuais,
# 2027, PLDO, arquivo anexo-v-riscos-fiscais.pdf (abre da nuvem).
# Tabela 26, p. 49-50, "Demandas Judiciais de Risco Possível e Risco Provável", R$ bilhões
# (fonte: AGU, SEST e BCB): "Risco Possível 1.195,1 1.528,0 1.540,1 1.316,1 1.260,4 2.741,8
# 2.586,1 2.101,5 1.740,0"; "Risco Provável 162,6 117,6 659,7 707,2 871,9 1.016,9 1.015,7
# 559,0 533,2" (2017 a 2025). Texto, p. 49: "Em 2025, o risco total de demandas judiciais,
# incluindo risco provável e possível, alcançou R$ 2.273,2 bilhões"; a queda do possível
# "decorre, principalmente, da reclassificação de ações previdenciárias de risco possível
# para risco remoto" (p. 14).
# LER DE NOVO a cada PLDO (enviado até 15 de abril).
ANO_DO_ANEXO_DE_RISCOS = 2027
"""O ano da LDO cujo projeto trouxe os números abaixo (os dados vão até o ano anterior)."""
ACOES_JUDICIAIS: dict[int, tuple[float, float]] = {
    # ano: (risco possível, risco provável), R$ bilhões
    2017: (1195.1, 162.6),
    2018: (1528.0, 117.6),
    2019: (1540.1, 659.7),
    2020: (1316.1, 707.2),
    2021: (1260.4, 871.9),
    2022: (2741.8, 1016.9),
    2023: (2586.1, 1015.7),
    2024: (2101.5, 559.0),
    2025: (1740.0, 533.2),
}

# Mesmo anexo, Tabela 27, p. 50, "Despesas Judiciais em relação à Despesa Primária", R$
# bilhões (fonte: AGU, PGFN, SEST, BCB, STN): "Ações Judiciais (Valores pagos) 31,7 36,5 41,3
# 50,3 54,9 58,7 151,9 70,3 101,2 121,3"; "Despesa Primária Total 1.279,6 1.352,5 1.442,3
# 1.947,6 1.614,2 1.809,7 2.129,9 2.204,7 2.394,2 2.613,5" (2017 a 2026). Nota 1: "Valores
# pagos referem-se a todas as despesas da União em cumprimento a sentenças judiciais, com
# exceção para 2026: dotação atualizada em fev/26"; nota 2: despesa de 2026 "Conforme a LOA
# 2026". Texto: "um pico de pagamentos em 2023, em decorrência dos efeitos da decisão proferida
# na Ação Direta de Inconstitucionalidade (ADI) 7064".
SENTENCAS_PAGAS: dict[int, tuple[float, float]] = {
    # ano: (pago em sentenças judiciais, despesa primária total), R$ bilhões
    2017: (31.7, 1279.6),
    2018: (36.5, 1352.5),
    2019: (41.3, 1442.3),
    2020: (50.3, 1947.6),
    2021: (54.9, 1614.2),
    2022: (58.7, 1809.7),
    2023: (151.9, 2129.9),
    2024: (70.3, 2204.7),
    2025: (101.2, 2394.2),
    2026: (121.3, 2613.5),
}
SENTENCAS_PREVISTAS_DESDE = 2026
"""Deste ano em diante, dotação do orçamento, não valor pago."""


@dataclass(frozen=True)
class RiscoFiscal:
    """Um item da tabela-resumo dos riscos fiscais específicos, estoque em R$ bilhões."""

    item: str
    efeito: str
    """"mais despesa" ou "menos receita", como o anexo classifica."""
    anterior: float
    ultimo: float


# Mesmo anexo, Tabela 2, p. 16, "Base de Atuação dos Riscos Fiscais Específicos
# Consolidados", estoque em R$ bilhões, 2024 e 2025: "Garantias da União ↑ despesa 333,9
# 336,6"; "Haveres Finan. Relacionados a Entes Federativos ↓ receita 811,1 888,8"; "Fundos
# Constitucionais ↓ receita 266,3 300,0"; "Passivos relacionados a Demandas Judiciais (Riscos
# Possíveis) ↑ despesa 2.101,5 1.740,0"; "(Riscos Prováveis) ↑ despesa 559,0 533,2"; "Fundo de
# Financiamento Estudantil – Fies ↓ receita 93,2 90,2"; "Total Geral 5.088,2 4.828,6". Ficam
# de fora os itens menores (passivos em reconhecimento, contragarantias, seguro de crédito à
# exportação, fundos garantidores) e a dívida ativa, que já está em Impostos.
RISCOS_FISCAIS = [
    RiscoFiscal("Ações na Justiça, perda possível", "mais despesa", 2101.5, 1740.0),
    RiscoFiscal("Ações na Justiça, perda provável", "mais despesa", 559.0, 533.2),
    RiscoFiscal("Dívidas de estados e municípios com a União", "menos receita", 811.1, 888.8),
    RiscoFiscal("Garantias da União a empréstimos", "mais despesa", 333.9, 336.6),
    RiscoFiscal("Fundos constitucionais (FNO, FNE, FCO)", "menos receita", 266.3, 300.0),
    RiscoFiscal("Fies, crédito a receber", "menos receita", 93.2, 90.2),
]
FONTE_RISCOS_FISCAIS = (
    "Projeto da LDO 2027, Anexo V (Riscos Fiscais), da Secretaria do Tesouro Nacional, "
    "tabelas 2, 26 e 27 (dados de AGU, PGFN, SEST, BCB e STN)"
)

# ------------------------------------------------------------------ o INSS até 2100

# Projeto da LDO 2027, Anexo IV.10, "Projeções Atuariais para o Regime Geral de Previdência
# Social" (art. 4º, § 2º, IV, "a", da LRF), Secretaria de Regime Geral de Previdência Social
# do Ministério da Previdência, abril de 2026. Lido em 15/11/2026 em gov.br/planejamento,
# arquivo anexo-iv-10-avaliacao-atuarial-rgps.pdf. Tabela 5.2, p. 62-63, "Evolução da
# receita, despesa e necessidade de financiamento do RGPS (em R$ mi correntes e em % do PIB)
# ― 2026/2100", colunas "Receita / PIB", "Despesa / PIB" e "Necessidade de Fin. / PIB";
# linhas usadas, por exemplo: "2026 785.289 5,77% 1.123.937 8,26% 338.649 2,49%"; "2060
# 4.057.299 6,40% 7.569.752 11,94% 3.512.454 5,54%"; "2100 17.351.016 6,35% 45.793.855
# 16,76% 28.442.839 10,41%". (O texto da p. 61 diz "R$ 338.275 milhões em 2025"; a tabela
# começa em 2026 e traz 338.649: vale a tabela.) Elaboração com a grade de parâmetros da
# SPE/MF de 05/03/2026 para 2026 a 2030; de 2031 em diante, modelo de longo prazo com a
# população projetada pela ONU. Aqui, 2026 a 2030 ano a ano e depois de cinco em cinco anos.
# LER DE NOVO a cada PLDO (abril).
RGPS_PROJECAO: dict[int, tuple[float, float, float]] = {
    # ano: (receita, despesa, necessidade de financiamento), % do PIB
    2026: (5.77, 8.26, 2.49),
    2027: (6.01, 8.23, 2.22),
    2028: (6.18, 8.16, 1.98),
    2029: (6.36, 8.08, 1.72),
    2030: (6.54, 7.99, 1.45),
    2035: (6.51, 8.42, 1.92),
    2040: (6.48, 8.87, 2.39),
    2045: (6.46, 9.51, 3.05),
    2050: (6.44, 10.23, 3.79),
    2055: (6.43, 10.90, 4.47),
    2060: (6.40, 11.94, 5.54),
    2065: (6.38, 13.08, 6.70),
    2070: (6.37, 13.26, 6.89),
    2075: (6.37, 13.98, 7.61),
    2080: (6.36, 14.62, 8.26),
    2085: (6.36, 15.22, 8.86),
    2090: (6.36, 15.74, 9.38),
    2095: (6.35, 16.31, 9.95),
    2100: (6.35, 16.76, 10.41),
}
FONTE_RGPS_PROJECAO = (
    "Projeto da LDO 2027, Anexo IV.10, Projeções Atuariais para o Regime Geral de "
    "Previdência Social (Ministério da Previdência, abr/2026), tabela 5.2"
)


# ------------------------------------------------------------------ acordos da dívida dos estados


@dataclass(frozen=True)
class AcordoDaDivida:
    """Em que regime de pagamento da dívida com a União o estado está."""

    regime: str
    """"RRF", "Propag" ou "Nenhum"."""
    detalhe: str
    """O que muda dentro do regime, em poucas palavras (até 60 letras, vai ao cartão)."""


# O Regime de Recuperação Fiscal (LC 159/2017) e o Programa de Pleno Pagamento de Dívidas dos
# Estados (Propag, LC 212/2025, art. 2º, § 1º: adesão "até 31 de dezembro de 2025"; LC lida em
# 15/11/2026 no Senado, legis.senado.leg.br/norma/40157164/publicacao/40157952). A LC 212,
# art. 4º, § 6º, dá a quem estava no RRF a saída gradual; a página do Tesouro sobre o Propag
# (gov.br/tesouronacional, "Programa de Pleno Pagamento de Dívidas dos Estados", modificada em
# 29/07/2026, lida em 15/11/2026) diz que "a assinatura do termo aditivo do Propag fica
# condicionada à homologação do encerramento do RRF".
#
# Quem está em cada um, lido em 15/11/2026:
# - Tesouro Nacional, Relatório Mensal de Garantias Honradas (RMGH) de out/2025, publicado em
#   17/11/2025 (cdn.tesouro.gov.br, "RMGH - 2025_10.pdf", p. 5): "Atualmente se encontram no
#   RRF os Estados de Goiás, Rio de Janeiro, Rio Grande do Sul e Minas Gerais." O RMGH de 2026
#   não abriu (o Tesouro Transparente dava "Falha na integração THOT/3PRO").
# - Instituição Fiscal Independente (Senado), Relatório de Acompanhamento Fiscal nº 114, jul/2026,
#   p. 63–65 (www2.senado.leg.br/jspui/bitstream/id/935943/4/RAF114_JUL2026_3_Propag.pdf): "Das
#   27 unidades da federação, 22 aderiram ao Propag [...] Os cinco entes federativos que não
#   aderiram foram Mato Grosso, Pará, Paraná, Santa Catarina e o Distrito Federal. Piauí e
#   Tocantins, apesar de não disporem de dívidas refinanciadas com a União, aderiram ao Propag
#   para acessar os recursos do FEF e do FGF." A Tabela 17 ("Termos aditivos assinados até
#   30/06/2026", fonte: Ministério da Fazenda via LAI) lista AC, AL, AM, AP, BA, CE, ES, GO, MA,
#   MG, MS, PB, PE, RJ, RO, RR, SE e SP com o termo assinado; RN "termo aditivo ainda não
#   assinado"; RS "termo aditivo ainda não assinado (§3º do art. 2º da LCP 212/2025)", que
#   "está sob a regra da LC nº 206, de 2024" e depois "estará sujeito às regras dos estados
#   sob o RRF".
# Daí: GO, MG e RJ assinaram o Propag e, com isso, saíram do RRF; o RS segue no RRF.
# LER DE NOVO a cada RMGH (mensal) ou RAF da IFI que fale do Propag, e quando o RS assinar.
ACORDOS_EM = date(2026, 6, 30)
_SAIU_DO_RRF = "saiu do RRF ao assinar o Propag"
_SEM_DIVIDA = "sem dívida a renegociar; aderiu pelo fundo de investimentos"
ACORDOS: dict[str, AcordoDaDivida] = {
    **{
        uf: AcordoDaDivida("Propag", "termo assinado")
        for uf in ("AC", "AL", "AM", "AP", "BA", "CE", "ES", "MA", "MS", "PB", "PE", "RO")
    },
    **{uf: AcordoDaDivida("Propag", "termo assinado") for uf in ("RR", "SE", "SP")},
    "GO": AcordoDaDivida("Propag", _SAIU_DO_RRF),
    "MG": AcordoDaDivida("Propag", _SAIU_DO_RRF),
    "RJ": AcordoDaDivida("Propag", _SAIU_DO_RRF),
    "PI": AcordoDaDivida("Propag", _SEM_DIVIDA),
    "TO": AcordoDaDivida("Propag", _SEM_DIVIDA),
    "RN": AcordoDaDivida("Propag", "aderiu; termo ainda não assinado"),
    "RS": AcordoDaDivida("RRF", "aderiu ao Propag; termo ainda não assinado"),
    **{
        uf: AcordoDaDivida("Nenhum", "não aderiu ao Propag")
        for uf in ("DF", "MT", "PA", "PR", "SC")
    },
}
FONTE_ACORDOS = (
    "Instituição Fiscal Independente (Senado), Relatório de Acompanhamento Fiscal nº 114, "
    "jul/2026, tabela 17 (termos do Propag assinados até 30/06/2026, dados do Ministério da "
    "Fazenda); Tesouro Nacional, Relatório Mensal de Garantias Honradas de out/2025 (estados "
    "no RRF)"
)


# ------------------------------------------------------------------ conferência do PIB dos estados

# O PIB trimestral por estado é conta nossa (`modelos/pib_estados.py`). Cinco estados publicam
# o seu, por órgão oficial de estatística, com método e série em planilha: é o que há para
# conferir a conta. Lidas em 15/11/2026, todas até o 2º tri/2026:
# - RS, DEE/SPGG: dee.rs.gov.br/pib-trimestral, "serie-historica-2026-ii.xlsx", aba "Série
#   encadeada", coluna PIB (2002 = 100).
# - PR, IPARDES: ipardes.pr.gov.br/Pagina/PIB-Trimestral-do-Parana,
#   "serie_encadeada_2o_trim_2026.xlsx", aba "Série Encadeada", coluna PIB (2005 = 100).
# - MG, Fundação João Pinheiro: anexo estatístico do PIB trimestral (planilha no Google),
#   aba "Série Encadeada", coluna PIB (2002 = 100).
# - BA, SEI: ba.gov.br/sei/pib-estadual-trimestral-0, "pib_trimestral_tabelas_completas.xls",
#   aba "Base Móvel", coluna PIB (2002 = 100).
# - ES, IJSN: ijsn.es.gov.br, "PIB Trimestral (dados em Excel)", aba "Planilha4" (taxa contra o
#   mesmo trimestre do ano anterior), coluna PIB do Espírito Santo.
# A conta: o crescimento contra o mesmo trimestre do ano anterior de cada órgão menos o nosso,
# em todos os trimestres desde 2011 (`scripts/conferir_pib_estados.py` refaz). REFAZER uma
# vez por ano, depois das Contas Regionais (novembro), quando a nossa série muda mais.


@dataclass(frozen=True)
class ConferenciaPibEstados:
    lida_em: date
    estados: tuple[str, ...]
    desde: int
    trimestres: int
    diferenca_media: float
    """Média do módulo da diferença, em pontos percentuais."""
    faixa: tuple[float, float]
    """Onde ficaram 8 de cada 10 diferenças (nossa conta menos a do órgão estadual)."""


CONFERENCIA_PIB_ESTADOS = ConferenciaPibEstados(
    lida_em=date(2026, 11, 15),
    estados=("RS", "PR", "MG", "BA", "ES"),
    desde=2011,
    trimestres=309,
    diferenca_media=1.1,
    faixa=(-1.7, 1.8),
)
FONTE_CONFERENCIA_PIB_ESTADOS = (
    "PIB trimestral estadual: DEE/SPGG (RS), IPARDES (PR), Fundação João Pinheiro (MG), "
    "SEI (BA) e IJSN (ES)"
)


# ------------------------------------------------------------------ servidores


# Quanto ganha, em média, o servidor civil da União de cada poder, na ativa e aposentado
# (Caio, 19/11/2026: *"inclua a distribuição dos gastos por servidores públicos (quem fica
# com mais) e compare o rendimento e benefícios dos servidores com o setor privado"*).
# Lido em 19/11/2026 no PLDO 2027, Anexo IV.11, "Avaliação Atuarial do Regime Próprio de
# Previdência Social dos Servidores Civis" (relatório de março/2026), tabelas 3 a 6, p. 16 e
# 17, coluna "Geral"; as tabelas são imagem no PDF e foram lidas na página.
# gov.br/planejamento/pt-br/assuntos/orcamento/orcamentos-anuais/2027/pldo/
#   anexo-iv-11-avaliacao-atuarial-rpps.pdf
# P. 14-15: "os dados da base cadastral dos servidores, aposentados e pensionistas, usados no
# cálculo atuarial, devem referir-se ao mês de julho de 2025" e "foram considerados 1.557.180
# segurados, sendo 792.702 (50,9%) servidores ativos, 467.837 (30,0%) aposentados e 296.641
# (19,0%) pensionistas" (as quantidades por poder abaixo somam esses totais).
# O Executivo inclui o Banco Central, a Abin e a Defensoria; o Legislativo, o TCU; o
# Ministério Público é o da União. Sai todo ano, em abril, com o PLDO.
@dataclass(frozen=True)
class ServidoresDoPoder:
    poder: str
    ativos: int
    remuneracao: float
    """Remuneração média dos servidores na ativa, R$ por mês."""
    aposentados: int
    provento: float
    """Provento médio dos aposentados, R$ por mês."""
    pensionistas: int
    pensao: float


SERVIDORES_EM = date(2025, 7, 1)
SERVIDORES_POR_PODER = [
    ServidoresDoPoder("Executivo", 663_308, 13_369.72, 421_369, 12_013.58, 281_712, 7_050.41),
    ServidoresDoPoder("Judiciário", 105_545, 14_977.90, 34_919, 22_056.80, 10_145, 16_016.67),
    ServidoresDoPoder(
        "Legislativo (com o TCU)", 6_960, 18_541.40, 8_752, 39_389.57, 3_729, 25_356.55
    ),
    ServidoresDoPoder(
        "Ministério Público da União", 16_889, 16_663.22, 2_797, 23_664.18, 1_055, 17_383.86
    ),
]
FONTE_SERVIDORES = (
    "Ministério da Previdência Social, Avaliação Atuarial do RPPS dos servidores civis da "
    "União (PLDO 2027, Anexo IV.11), tabelas 3 a 6"
)

# Os militares das Forças Armadas, do mesmo PLDO 2027, Anexo IV.12, volume 1 ("Avaliação
# atuarial dos proventos de militares inativos e dos benefícios de pensionistas de
# militares"), seções 3.1.1 e 3.1.2, p. 6 e 7, lido em 19/11/2026: "Os dados correntes
# utilizados foram de maio de 2025, extrapolados para a posição de 31 de dezembro de 2025."
# (grupo, quantidade, remuneração média em R$ por mês). Os praças temporários são, na maior
# parte, recrutas do serviço militar obrigatório.
MILITARES_ATIVOS = [
    ("Oficiais de carreira", 34_076, 21_456.96),
    ("Oficiais temporários", 16_589, 12_840.88),
    ("Praças de carreira", 102_922, 8_854.28),
    ("Praças temporários", 181_334, 2_486.77),
    ("Praças especiais de carreira", 8_063, 2_620.22),
    ("Praças especiais temporários", 7_874, 5_168.51),
]
MILITARES_INATIVOS = [("Oficiais", 53_030, 25_719.58), ("Praças", 115_534, 10_296.38)]
FONTE_MILITARES = (
    "Ministério da Defesa, Avaliação Atuarial do Sistema de Pensões Militares das Forças "
    "Armadas (PLDO 2027, Anexo IV.12, volume 1)"
)

# O que o INSS paga, para comparar. Boletim Estatístico da Previdência Social, set/2026
# (vol. 31, nº 9), quadro 15, "Benefícios emitidos pelo INSS, por clientela, segundo os grupos
# de espécies", p. 32, lido em 19/11/2026; valor médio em R$ por mês:
#   "Aposentadorias [...] 2.051,05 2.339,68 1.437,93" (total, urbano, rural)
#   "Tempo de Contribuição [...] 3.032,35"; "Idade [...] 1.617,72"
# gov.br/previdencia/.../boletins-da-previdencia-social/2026/beps092026_final.pdf. Mensal.
INSS_EM = date(2026, 9, 1)
INSS_APOSENTADORIA_MEDIA = 2_051.05
INSS_APOSENTADORIA_TEMPO = 3_032.35
INSS_APOSENTADORIA_IDADE = 1_617.72
INSS_APOSENTADORIAS = 24_727_767
FONTE_INSS = "Ministério da Previdência Social, Boletim Estatístico da Previdência Social"

# Os dois tetos. O do INSS: Portaria Interministerial MPS/MF nº 13, de 9/1/2026 (DOU de
# 12/1/2026), art. 2º, lida em 19/11/2026 na cópia do DOU no site do ministério: "O salário
# de benefício e o salário de contribuição, a partir de 1º de janeiro de 2026, não poderão ser
# inferiores a R$ 1.621,00 [...] nem superiores a R$ 8.475,55". Muda todo janeiro.
# O do serviço público é o subsídio de ministro do STF: Lei nº 14.520, de 9/1/2023, art. 1º,
# III, lida em 19/11/2026 no Senado (legis.senado.leg.br/norma/36753460/publicacao/36755366):
# "R$ 46.366,19 [...], a partir de 1º de fevereiro de 2025". Nenhuma lei de 2025 ou de 2026
# (até 18/11/2026) com "subsídio" na ementa na lista do Senado.
TETO_INSS = 8_475.55
TETO_INSS_ANO = 2026
TETO_SERVICO_PUBLICO = 46_366.19
FONTE_TETOS = (
    "Portaria Interministerial MPS/MF nº 13/2026, art. 2º (INSS); Lei nº 14.520/2023, "
    "art. 1º (subsídio de ministro do STF)"
)


# ------------------------------------------------------------------ estatais


# O que as estatais federais dão e o que recebem da União, ano a ano (Caio, 19/11/2026:
# *"adicione uma pergunta de quanto as estatais dão lucro ou prejuízo aos cofres
# públicos"*). Lido em 19/11/2026 no "Relatório Agregado das Empresas Estatais Federais 2026 |
# Ano Base 2025" (Sest, Ministério da Gestão, 18/6/2026), p. 86, "Anexo I – Séries históricas,
# Dados gerais (todas as empresas)", e conferido somando as linhas da planilha do mesmo anexo:
#   "Resultado Líquido 187.473,4 275.122,9 197.908,1 116.478,9 169.382,8"
#   "Pagos à União 40.147,4 86.744,4 49.635,1 72.016,9 45.756,7"
#   "Subvenção 20.345,2 22.224,6 23.930,4 27.160,7 30.924,6"
# gov.br/gestao/pt-br/assuntos/estatais/transparencia/defeso_relatorio%20agregado
# O aporte de capital (AFAC, adiantamento para futuro aumento de capital) vem da soma da
# planilha: a tabela da p. 86 traz 3.418,3 em 2025, o dobro, e o texto da p. 17 diz "da ordem
# de R$ 1,7 bilhão", que é a soma (1.709,1). P. 17: "o retorno financeiro das estatais
# federais em 2025 (dividendos e JCP pagos à União menos os valores de subvenções e de [...]
# AFAC) foi de R$ 13,1 bilhões". P. 21: "No universo das 44 empresas de controle direto, 17
# são dependentes e 27 não dependentes de recursos do Tesouro Nacional."
# Sai uma vez por ano, em junho. Valores em R$ milhões.
@dataclass(frozen=True)
class EstataisNoAno:
    lucro: float
    """Resultado líquido de todas as estatais federais somadas (os prejuízos descontados)."""
    dividendos_uniao: float
    """Dividendos e juros sobre capital próprio pagos à União."""
    subvencao: float
    """O que o Tesouro repassou às dependentes para pessoal e custeio."""
    aporte: float
    """Adiantamento para futuro aumento de capital."""
    prejuizos: float
    """A soma só das empresas que fecharam o ano no vermelho (soma nossa da planilha)."""


ESTATAIS_POR_ANO: dict[int, EstataisNoAno] = {
    2021: EstataisNoAno(187_473.4, 40_147.4, 20_345.2, 1_123.6, -3_793.7),
    2022: EstataisNoAno(275_122.9, 86_744.4, 22_224.6, 2_036.0, -3_427.5),
    2023: EstataisNoAno(197_908.1, 49_635.1, 23_930.4, 2_399.5, -3_674.3),
    2024: EstataisNoAno(116_478.9, 72_016.9, 27_160.7, 1_572.2, -4_764.0),
    2025: EstataisNoAno(169_382.8, 45_756.7, 30_924.6, 1_709.1, -10_583.7),
}
ESTATAIS_DIRETAS = 44
ESTATAIS_DEPENDENTES = 17

# Quem recebeu a subvenção em 2025 (mesmo relatório, p. 17, quadro "Recursos recebidos do
# Tesouro Nacional – Subvenção, em 2025 (R$ milhões)": "HU Brasil (Ebserh) 13.678,0 / Embrapa
# 4.501,4 [...] TOTAL 30.925"), com o que cada uma faz, para a tela.
SUBVENCOES_2025: list[tuple[str, float]] = [
    ("Ebserh (hospitais universitários)", 13_678.0),
    ("Embrapa (pesquisa agropecuária)", 4_501.4),
    ("Grupo Hospitalar Conceição", 2_650.1),
    ("Hospital de Clínicas de Porto Alegre", 2_026.5),
    ("Codevasf (obras nos vales do São Francisco e do Parnaíba)", 1_694.6),
    ("Conab (abastecimento)", 1_327.2),
    ("CBTU (trens urbanos)", 1_285.3),
    ("CPRM (Serviço Geológico)", 698.3),
    ("EBC (comunicação pública)", 609.5),
    ("Amazul (programa nuclear da Marinha)", 512.6),
    ("Nuclep (equipamentos pesados)", 450.5),
    ("Telebras", 406.9),
    ("Trensurb (trens de Porto Alegre)", 324.0),
    ("Infra S.A. (ferrovias e projetos)", 274.9),
    ("Imbel (material bélico)", 239.5),
    ("EPE (pesquisa energética)", 176.5),
    ("Ceitec (semicondutores)", 68.7),
]

# O lucro (ou prejuízo) dos maiores, R$ milhões, 2024 e 2025 (mesmo relatório, p. 88 a 105,
# e a planilha do Anexo I, coluna "RESULTADO LÍQUIDO"). P. 15: "Petrobras (R$ 110,6 bilhões),
# BNDES (R$ 25,6 bilhões) e BB (R$ 17,8 bilhões), que responderam por 90,9% do lucro total".
LUCRO_DOS_MAIORES: list[tuple[str, float, float]] = [
    ("Petrobras", 37_009.0, 110_605.0),
    ("BNDES", 26_387.7, 25_571.6),
    ("Banco do Brasil", 35_439.9, 17_808.0),
    ("Caixa", 13_526.5, 16_051.8),
    ("Correios", -2_447.2, -8_457.8),
]
FONTE_ESTATAIS = (
    "Ministério da Gestão (Sest), Relatório Agregado das Empresas Estatais Federais 2026, "
    "ano-base 2025, anexo I"
)
