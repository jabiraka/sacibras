"""Números lidos à mão em relatório oficial que não tem API nem planilha: a nota de crédito
do país, as elasticidades da dívida e o teste de estresse dos bancos.

Mesma regra de `leis.py`: só entra o que foi lido na fonte, com a data da leitura e o
endereço ao lado. Cada bloco diz quando precisa ser lido de novo.
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


# ------------------------------------------------------------------ imposto e crescimento


@dataclass(frozen=True)
class EfeitoDeImposto:
    """Um número de estudo oficial sobre o efeito de imposto no PIB, com o trecho lido."""

    rotulo: str
    valor: float
    unidade: str
    casas: int
    fonte: str
    leitura: str
    """O que o estudo diz, em palavras de todo dia, com o trecho original e a página."""


# Lidos em 14/11/2026 nos PDFs (texto extraído e conferido contra a frase citada). Pedido do
# Caio no mesmo dia: "multiplicadores lidos". Não há multiplicador de receita publicado pelo
# BC, pelo Tesouro ou pela SPE (a SPE estimou um no Boletim Impulso Estrutural do Gasto,
# dez/2025, mas publicou só os de despesa): RELER quando sair a nota metodológica da SPE. O
# estudo do CCiF (Bráulio Borges, 2020) está no site da Fazenda, mas não é do governo: fica
# de fora pela regra de fonte oficial.
EFEITOS_DE_IMPOSTO: list[EfeitoDeImposto] = [
    EfeitoDeImposto(
        rotulo="Corte de imposto: PIB a mais no pico, um ano depois (FMI)",
        valor=0.5,
        unidade="R$ por R$ 1 de imposto",
        casas=1,
        fonte="FMI, Working Paper 16/79, Fiscal Multipliers for Brazil (2016)",
        leitura=(
            "FMI (Matheson e Pereira, 2016, dados de 1999 a 2014): R$ 1 a menos de imposto "
            "rende uns R$ 0,50 a mais de PIB um ano depois; no médio prazo, somado, uns "
            'R$ 2. "The revenue multiplier peaks at around 0.5 one year after a tax cut '
            "[...] the medium-run (accumulated) multiplier of tax cuts is positive, at about "
            '2" (p. 7). Vale também ao contrário: imposto a mais tira PIB.'
        ),
    ),
    EfeitoDeImposto(
        rotulo="Corte de imposto: PIB a mais, somado no médio prazo (FMI)",
        valor=2.0,
        unidade="R$ por R$ 1 de imposto",
        casas=1,
        fonte="FMI, Working Paper 16/79, Fiscal Multipliers for Brazil (2016)",
        leitura=(
            "O mesmo estudo diz que o efeito da receita ficou estável depois da crise de 2008, "
            'ao contrário do efeito do gasto, que caiu para perto de zero: "the revenue '
            'multiplier has remained broadly stable" (p. 9).'
        ),
    ),
    EfeitoDeImposto(
        rotulo="Receita a mais sem aviso: chance de o PIB cair logo depois (Ipea)",
        valor=56.6,
        unidade="% de chance",
        casas=1,
        fonte="Ipea, Texto para Discussão 1377 (2009)",
        leitura=(
            'Ipea (Mendonça, Medrano e Sachsida, 2009): "Com 56,6% de probabilidade o PIB '
            "decresce após um aumento inesperado nas receitas do governo. Apesar de a "
            "resposta inicial do PIB ser negativa, ela pode se tornar positiva no longo "
            'prazo" (p. 13): o mercado pode ler a receita a mais como contas em ordem.'
        ),
    ),
    EfeitoDeImposto(
        rotulo="Reforma do consumo (texto da Câmara, 2023): PIB a mais até 2032 (Ipea)",
        valor=2.39,
        unidade="%",
        casas=2,
        fonte="Ipea, Carta de Conjuntura nº 60, Nota 1 (2023)",
        leitura=(
            "Ipea (João Maria de Oliveira, jul/2023), sobre o substitutivo da PEC 45 aprovado "
            'na Câmara, que virou a reforma de 2023: "para o substitutivo da PEC no 45/2019, '
            'também até 2032, cresce 2,39%" (p. 13), contra um cenário sem reforma. O texto '
            "original da PEC 45 dava 5,75 % até 2036; a diferença vem dos regimes especiais e "
            "das exceções mantidos."
        ),
    ),
    EfeitoDeImposto(
        rotulo="Reforma do consumo aprovada: PIB a mais no longo prazo, no máximo (Prêmio Tesouro)",
        valor=4.5,
        unidade="%",
        casas=1,
        fonte=(
            "Tesouro Nacional, Cadernos de Finanças Públicas, edição especial do 29º Prêmio "
            "Tesouro (2025)"
        ),
        leitura=(
            "Araujo, Martinez e Navarro, trabalho premiado e publicado pelo Tesouro (não é "
            'estimativa do próprio Tesouro): "estimamos um aumento de até 4,5% no PIB, com '
            "2,7% devidos à aproximação das alíquotas entre os setores e até 1,8% em razão da "
            'simplificação do sistema tributário" (resumo, p. 2).'
        ),
    ),
]


# ------------------------------------------------------------------ quem paga

# Ipea, Texto para Discussão 2823, "Tributação indireta: alíquotas efetivas e incidência sobre
# as famílias" (Silveira, Palomo, Cornelio e Tonon, dez/2022; dados da POF 2017-2018), lido em
# 14/11/2026 em repositorio.ipea.gov.br/handle/11058/11624. Gráfico 3 (p. 25), "Incidência da
# tributação direta e indireta na renda total, segundo décimos de renda familiar per capita":
# os rótulos das barras, conferidos na imagem da página. No texto (p. 25): "a incidência nos
# 10% mais pobres alcançando 26,4%, ao passo que nos 10% mais ricos os tributos representam
# 19,2% da renda"; (p. 23) "na média, os tributos indiretos representam 11,2% da renda total".
# "Diretos" aqui inclui a contribuição à previdência, o IRPF, o IPTU e o IPVA (p. 23): não se
# compara com a alíquota do IRPF dos Grandes Números. RELER quando o Ipea refizer a conta com
# a próxima POF.
FONTE_INCIDENCIA = "Ipea, Texto para Discussão 2823 (2022), gráfico 3, com dados da POF 2017-2018"
INCIDENCIA_POR_DECIMO: list[tuple[str, float, float]] = [
    # (décimo de renda familiar por pessoa, indiretos, diretos), em % da renda total
    ("10 % mais pobres", 23.4, 3.0),
    ("2º décimo", 17.3, 3.8),
    ("3º décimo", 15.6, 3.8),
    ("4º décimo", 14.3, 4.3),
    ("5º décimo", 14.0, 4.9),
    ("6º décimo", 13.1, 5.0),
    ("7º décimo", 12.7, 5.6),
    ("8º décimo", 12.5, 6.7),
    ("9º décimo", 11.5, 8.2),
    ("10 % mais ricos", 8.6, 10.6),
    ("Média", 11.2, 8.0),
]
