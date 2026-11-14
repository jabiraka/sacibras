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
