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
