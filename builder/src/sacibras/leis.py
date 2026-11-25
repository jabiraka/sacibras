"""Números que vêm de norma. Cada um com a referência da norma lida.

Regra do projeto: número de lei só entra daqui, e só depois de a norma ter sido lida na fonte
oficial (a data da leitura fica ao lado).
O prazo de cada releitura mora em `leituras.py` (o build e o workflow "Prazos de releitura"
avisam quando vence).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class MetaDeInflacao:
    centro: float
    intervalo: float
    desde: date
    referencia: str


META_CONTINUA = MetaDeInflacao(
    centro=3.0,
    intervalo=1.5,
    desde=date(2025, 1, 1),
    # Lida em 14/11/2026 na API de normativos do BCB (exibenormativo?p1=Resolução CMN&p2=5141):
    # "Art. 2º A meta para a variação acumulada em doze meses do índice de preços indicado no
    # art. 1º, apurada mês a mês, a ser aplicada no período que se inicia em 1º de janeiro de
    # 2025, é fixada em 3,00% (três inteiros por cento), com intervalo de tolerância de menos
    # 1,50 p.p. (um e meio ponto percentual) e de mais 1,50 p.p." O art. 1º indica o IPCA.
    referencia="Resolução CMN nº 5.141, de 26/6/2024, art. 2º",
)


@dataclass(frozen=True)
class FaixaDaDespesa:
    """Entre quanto e quanto pode crescer, acima da inflação, o limite da despesa primária."""

    piso: float
    teto: float
    desde: date
    referencia: str


# Lida em 20/11/2026 no Senado, publicação original
# (legis.senado.leg.br/norma/37553820/publicacao/37556723), Lei Complementar nº 200, de
# 30/8/2023. Art. 3º: "ficam estabelecidos, para cada exercício a partir de 2024 [...] limites
# individualizados para o montante global das dotações orçamentárias relativas a despesas
# primárias". Art. 5º: a variação real dos limites fica em 70 % da variação real da receita
# (50 % se a meta de primário do ano anterior não foi cumprida); § 1º: "O crescimento real dos
# limites da despesa primária [...] não será inferior a 0,6% a.a. (seis décimos por cento ao
# ano) nem superior a 2,5% a.a. (dois inteiros e cinco décimos por cento ao ano)." O art. 4º
# corrige os limites pelo IPCA "no período de 12 (doze) meses encerrado em junho do exercício
# anterior", e o art. 3º, § 2º, deixa despesas de fora: a faixa é do limite, não da despesa
# total do Tesouro.
FAIXA_DA_DESPESA = FaixaDaDespesa(
    piso=0.6,
    teto=2.5,
    desde=date(2024, 1, 1),
    referencia="Lei Complementar nº 200, de 30/8/2023, art. 5º, § 1º",
)


@dataclass(frozen=True)
class LimiteLegal:
    """Um limite em % da receita corrente líquida, com a norma de onde ele sai."""

    valor: float
    referencia: str


# ---- Pessoal do Poder Executivo estadual (o RGF que o SICONFI traz é o do Executivo).
# Lidos em 14/11/2026 no Planalto (ccivil_03/leis/lcp/lcp101.htm):
# art. 19, II: "Estados: 60% (sessenta por cento)" da RCL;
# art. 20, II, c: "49% (quarenta e nove por cento) para o Executivo" (marcado "Vide ADI 6533");
# art. 22, parágrafo único: "Se a despesa total com pessoal exceder a 95% (noventa e cinco por
# cento) do limite, são vedados [...]" (o limite prudencial);
# art. 59, § 1º, II: o Tribunal de Contas alerta quando a despesa com pessoal passa de "90%
# (noventa por cento) do limite" (o limite de alerta).
PESSOAL_EXECUTIVO_ESTADUAL = LimiteLegal(49.0, "LRF, art. 20, II, c")
PESSOAL_PRUDENCIAL = LimiteLegal(round(0.95 * 49.0, 2), "LRF, art. 22, parágrafo único")
PESSOAL_ALERTA = LimiteLegal(round(0.90 * 49.0, 2), "LRF, art. 59, § 1º, II")

# ---- Dívida consolidada líquida dos estados.
# Lida em 14/11/2026 no Senado (legis.senado.leg.br/norma/562458, texto atualizado):
# Resolução do Senado Federal nº 40/2001, art. 3º, I: a dívida consolidada líquida "não poderá
# exceder [...] no caso dos Estados e do Distrito Federal: 2 (duas) vezes a receita corrente
# líquida". O alerta é o mesmo art. 59, § 1º, III, da LRF: "acima de 90% (noventa por cento)".
DIVIDA_ESTADUAL = LimiteLegal(200.0, "Resolução do Senado nº 40/2001, art. 3º, I")
DIVIDA_ALERTA = LimiteLegal(180.0, "LRF, art. 59, § 1º, III")

# ---- Capitais (municípios): pessoal do Executivo e dívida consolidada líquida.
# Lidos em 15/11/2026 no Senado, LC 101/2000 em texto atualizado
# (legis.senado.leg.br/norma/572856/publicacao/34621009), art. 20, III: "na esfera municipal:
# [...] b) 54% (cinqüenta e quatro por cento) para o Executivo"; o prudencial (95 %) e o alerta
# (90 %) são os mesmos arts. 22 e 59 dos estados. E a Resolução do Senado nº 40/2001
# (legis.senado.leg.br/norma/562458/publicacao/16433576), art. 3º, II: "no caso dos Municípios:
# a 1,2 (um inteiro e dois décimos) vezes a receita corrente líquida".
PESSOAL_EXECUTIVO_MUNICIPAL = LimiteLegal(54.0, "LRF, art. 20, III, b")
PESSOAL_PRUDENCIAL_MUNICIPAL = LimiteLegal(round(0.95 * 54.0, 2), "LRF, art. 22, parágrafo único")
PESSOAL_ALERTA_MUNICIPAL = LimiteLegal(round(0.90 * 54.0, 2), "LRF, art. 59, § 1º, II")
DIVIDA_MUNICIPAL = LimiteLegal(120.0, "Resolução do Senado nº 40/2001, art. 3º, II")
DIVIDA_ALERTA_MUNICIPAL = LimiteLegal(108.0, "LRF, art. 59, § 1º, III")


@dataclass(frozen=True)
class MetaPrimaria:
    """A meta de resultado primário do Governo Central para um ano, em R$ milhões correntes."""

    ano: int
    centro: float
    inferior: float
    superior: float
    referencia: str


# Lida em 14/11/2026 no Planalto (ccivil_03/_ato2023-2026/2025/lei/L15321.htm), Lei nº 15.321,
# de 31/12/2025 (LDO 2026), art. 2º: "meta de superávit primário de R$ 34.264.603.518,00 [...]
# para o Governo Central"; § 1º: intervalo de tolerância com "limite superior equivalente a
# superávit primário de R$ 68.529.207.037,00" e "limite inferior equivalente ao resultado
# primário de R$ 0,00". A banda vem da LC 101/2000, art. 4º, § 5º, IV (incluído pela LC
# 200/2023): "menos 0,25 p.p. [...] e de mais 0,25 p.p. [...] do PIB previsto".
# A LC 200/2023, art. 2º, § 4º, diz que a apuração é do Banco Central.
# Na tela (Caio, 14/11/2026, opção "b"): o número do BC contra a meta, com o desconto da
# apuração dito ao lado (`AVALIACAO_2026`).
META_PRIMARIA_2026 = MetaPrimaria(
    ano=2026,
    centro=34_264.603518,
    inferior=0.0,
    superior=68_529.207037,
    referencia="Lei nº 15.321/2025 (LDO 2026), art. 2º",
)


@dataclass(frozen=True)
class MetaDaLDO:
    """A meta de primário do Governo Central (orçamentos fiscal e da seguridade social) no
    texto ORIGINAL da LDO de um exercício: em % do PIB (até 2010) ou em R$ bilhões (de 2011 em
    diante; negativo é déficit), como a lei escreveu."""

    lei: str
    pct_do_pib: float | None = None
    reais_bi: float | None = None
    abatimento: str = ""
    """O que a própria lei deixava descontar da meta (PPI, PAC), em poucas palavras."""


# Lidas em 19/11/2026 na "Publicação Original" de cada lei no Senado
# (legis.senado.leg.br/norma/<id>/publicacao/<id>; os endereços estão em docs/FONTES.md,
# "Metas das LDOs"), art. 2º (arts. 15, 16 ou 18 até 2005, que remetem ao Anexo de Metas
# Fiscais; os anexos de 2002, 2004 e 2005 foram lidos no PDF da Câmara, e o de 2002 é imagem
# escaneada, lida a olho). É a meta como a lei saiu, sem as mudanças feitas durante o ano
# (2009, 2015, 2016, 2017 e 2018 tiveram lei que a mudou: é esse o ponto da comparação).
# Trechos: 2006, "2,45% [...] para os orçamentos fiscal e da seguridade social"; 2011, "R$
# 81.760.000.000,00 [...] para os Orçamentos Fiscal e da Seguridade Social"; 2017, "meta de
# déficit primário dos Orçamentos Fiscal e da Seguridade Social da União de R$
# 139.000.000.000,00"; 2024, "meta de resultado primário de R$ 0,00 (zero real)".
METAS_DAS_LDOS: dict[int, MetaDaLDO] = {
    2002: MetaDaLDO("Lei nº 10.266/2001", pct_do_pib=2.24),
    2003: MetaDaLDO("Lei nº 10.524/2002", pct_do_pib=2.25),
    2004: MetaDaLDO("Lei nº 10.707/2003", pct_do_pib=2.45),
    2005: MetaDaLDO("Lei nº 10.934/2004", pct_do_pib=2.45),
    2006: MetaDaLDO("Lei nº 11.178/2005", pct_do_pib=2.45),
    2007: MetaDaLDO("Lei nº 11.439/2006", pct_do_pib=2.45, abatimento="PPI, até R$ 4,6 bi"),
    2008: MetaDaLDO("Lei nº 11.514/2007", pct_do_pib=2.20, abatimento="PPI, até R$ 13,8 bi"),
    2009: MetaDaLDO("Lei nº 11.768/2008", pct_do_pib=2.20, abatimento="PPI, até R$ 15,6 bi"),
    2010: MetaDaLDO("Lei nº 12.017/2009", pct_do_pib=2.15, abatimento="PAC, até R$ 22,5 bi"),
    2011: MetaDaLDO("Lei nº 12.309/2010", reais_bi=81.76, abatimento="PAC, até R$ 32 bi"),
    2012: MetaDaLDO("Lei nº 12.465/2011", reais_bi=96.973, abatimento="PAC, até R$ 40,6 bi"),
    2013: MetaDaLDO("Lei nº 12.708/2012", reais_bi=108.09, abatimento="até R$ 45,2 bi"),
    2014: MetaDaLDO("Lei nº 12.919/2013", reais_bi=116.072, abatimento="até R$ 67 bi"),
    2015: MetaDaLDO("Lei nº 13.080/2015", reais_bi=55.279),
    2016: MetaDaLDO("Lei nº 13.242/2015", reais_bi=24.0),
    2017: MetaDaLDO("Lei nº 13.408/2016", reais_bi=-139.0),
    2018: MetaDaLDO("Lei nº 13.473/2017", reais_bi=-129.0),
    2019: MetaDaLDO("Lei nº 13.707/2018", reais_bi=-139.0),
    2020: MetaDaLDO("Lei nº 13.898/2019", reais_bi=-124.1),
    2021: MetaDaLDO("Lei nº 14.116/2020", reais_bi=-247.118225),
    2022: MetaDaLDO("Lei nº 14.194/2021", reais_bi=-170.473716),
    2023: MetaDaLDO("Lei nº 14.436/2022", reais_bi=-65.90576),
    2024: MetaDaLDO("Lei nº 14.791/2023", reais_bi=0.0, abatimento="tolerância de R$ 28,8 bi"),
    2025: MetaDaLDO("Lei nº 15.080/2024", reais_bi=0.0, abatimento="tolerância de R$ 31,0 bi"),
    2026: MetaDaLDO("Lei nº 15.321/2025", reais_bi=34.264603518, abatimento="piso em zero"),
}


@dataclass(frozen=True)
class AvaliacaoBimestral:
    """O que o governo projeta para o primário do ano no Relatório de Avaliação de Receitas e
    Despesas Primárias (o que a LDO 2026, art. 73, § 4º, manda publicar), em R$ bilhões.

    Não é número de lei: é a conta oficial da meta. O builder lê a planilha do bimestre mais
    novo (`fontes/avaliacao_bimestral.py`); a lista daqui é a reserva."""

    bimestre: str
    resultado: float
    """Resultado primário projetado para o ano, sem os descontos."""
    deducao: float
    """O que a apuração da meta desconta (abatimentos que outras normas autorizam)."""
    fonte: str


# Reserva: o builder lê sozinho a planilha do bimestre mais novo
# (`fontes/avaliacao_bimestral.py`) e só usa estes números se ela falhar ou for de outro ano.
# Lidos em 25/11/2026 nas planilhas "quadros de apoio" dos relatórios do 4º e do 5º bimestre
# de 2026 (gov.br/planejamento/pt-br/assuntos/orcamento/relatorios-de-avaliacao-fiscal), aba
# "Tabela 1", em R$ milhões: "5. Resultado Primário (3) - (4)" -52.013,9 [3º bim.], -80.936,8
# [4º], -89.306,5 [5º]; "6. Dedução EC 136, ADPF 1236 e LCs 221, 223 e 235" 62.779,0, 67.291,4,
# 76.984,7; "8. Centro da Meta" 34.264,6. O 3º e o 4º batem com a Nota Informativa da Conorf
# (Senado) de 25/9/2026, lida em 14/11/2026. Nota 3 da Conorf: precatórios, defesa, saúde e a
# ADPF 1236. LER DE NOVO a cada bimestre (o do 1º de 2027 sai até 22/3).
AVALIACOES_2026 = [
    AvaliacaoBimestral("3º bimestre", -52.0, 62.8, "Relatório de Avaliação do 3º bimestre de 2026"),
    AvaliacaoBimestral("4º bimestre", -80.9, 67.3, "Relatório de Avaliação do 4º bimestre de 2026"),
    AvaliacaoBimestral("5º bimestre", -89.3, 77.0, "Relatório de Avaliação do 5º bimestre de 2026"),
]

# Lidos em 14/11/2026, ainda sem uso na tela (pedem o RREO Anexo 12 e o Anexo 08 de cada
# estado, que trazem a base de cálculo): saúde, no mínimo 12 % da arrecadação de impostos
# estaduais e transferências (LC 141/2012, art. 6º; Constituição, art. 198, § 2º, II);
# educação, no mínimo 25 % da receita de impostos, incluídas as transferências
# (Constituição, art. 212).


# ------------------------------------------------------------------ reforma do consumo


@dataclass(frozen=True)
class PassoDaReforma:
    quando: str
    muda: str
    """O que muda, em palavras de todo dia."""
    norma: str


# Emenda Constitucional nº 132, de 20/12/2023, art. 2º (acrescenta os arts. 124 a 133 ao ADCT),
# e Lei Complementar nº 214, de 16/1/2025. Lidas em 14/11/2026 no Senado, na PUBLICAÇÃO
# ORIGINAL do Diário Oficial (legis.senado.leg.br/norma/37959796/publicacao/37963893 e
# legis.senado.leg.br/norma/40180341/publicacao/40181429): o Planalto, que tem o texto
# compilado, não responde da nuvem. Conferidos de novo em 15/11/2026 no TEXTO ATUALIZADO da
# Constituição na Câmara (www2.camara.leg.br/legin/fed/consti/1988/
# constituicao-1988-5-outubro-1988-322142-normaatualizada-pl.html): os arts. 124 a 137 do ADCT
# seguem como a EC 132 os escreveu (só "Artigo acrescido pela Emenda Constitucional nº 132"; a
# EC 135/2024 acrescentou o art. 138, fora da reforma). Trechos:
# - ADCT art. 125: "Em 2026, o imposto previsto no art. 156-A será cobrado à alíquota estadual
#   de 0,1% (um décimo por cento), e a contribuição prevista no art. 195, V, ambos da
#   Constituição Federal, será cobrada à alíquota de 0,9% (nove décimos por cento)." § 1º: "O
#   montante recolhido na forma do caput será compensado com o valor devido das contribuições
#   previstas no art. 195, I, "b", e IV, e da contribuição para o Programa de Integração Social".
#   LC 214, art. 348, § 1º: "Fica dispensado o recolhimento do IBS e da CBS relativo aos fatos
#   geradores ocorridos no período indicado no caput em relação aos sujeitos passivos que
#   cumprirem as obrigações acessórias previstas na legislação."
# - ADCT art. 126: "A partir de 2027: I – serão cobrados: a) a contribuição prevista no art.
#   195, V [...]; b) o imposto previsto no art. 153, VIII [...]; II – serão extintas as
#   contribuições previstas no art. 195, I, "b", e IV, e a contribuição para o Programa de
#   Integração Social de que trata o art. 239 [...], desde que instituída a contribuição
#   referida na alínea "a" do inciso I; III – o imposto previsto no art. 153, IV [...]: a) terá
#   suas alíquotas reduzidas a zero, exceto em relação aos produtos que tenham industrialização
#   incentivada na Zona Franca de Manaus".
# - ADCT art. 127: "Em 2027 e 2028, o imposto previsto no art. 156-A da Constituição Federal
#   será cobrado à alíquota estadual de 0,05% (cinco centésimos por cento) e à alíquota
#   municipal de 0,05% (cinco centésimos por cento). Parágrafo único. No período referido no
#   caput, a alíquota da contribuição prevista no art. 195, V, [...] será reduzida em 0,1 (um
#   décimo) ponto percentual."
# - ADCT art. 128: "De 2029 a 2032, as alíquotas dos impostos previstos nos arts. 155, II, e
#   156, III, [...] serão fixadas nas seguintes proporções das alíquotas fixadas nas respectivas
#   legislações: I – 9/10 (nove décimos), em 2029; II – 8/10 (oito décimos), em 2030; III – 7/10
#   (sete décimos), em 2031; IV – 6/10 (seis décimos), em 2032."
# - ADCT art. 129: "Ficam extintos, a partir de 2033, os impostos previstos nos arts. 155, II, e
#   156, III, da Constituição Federal."
# - ADCT art. 130: "Resolução do Senado Federal fixará, para todas as esferas federativas, as
#   alíquotas de referência dos tributos previstos nos arts. 156-A e 195, V [...]". § 4º: "A
#   alíquota de referência da contribuição a que se refere o art. 195, V, [...] será reduzida em
#   2030 caso a média da Receita-Base da União em 2027 e 2028 exceda o Teto de Referência da
#   União." § 5º: as duas alíquotas "serão reduzidas em 2035 caso a média da Receita-Base Total
#   entre 2029 e 2033 exceda o Teto de Referência Total" (os tetos são a média de 2012 a 2021,
#   em proporção do PIB, § 3º).
# Na Constituição: 195, V = CBS; 156-A = IBS; 153, VIII = Imposto Seletivo; 195, I, "b" e IV =
# Cofins; 239 = PIS; 153, IV = IPI; 155, II = ICMS; 156, III = ISS.
REFORMA_DO_CONSUMO: list[PassoDaReforma] = [
    PassoDaReforma(
        "2026",
        "Ano de teste. A CBS (federal) aparece na nota a 0,9 % e o IBS (de estados e "
        "municípios) a 0,1 %, descontados do PIS e da Cofins. Quem cumpre as obrigações de "
        "informar fica dispensado de recolher.",
        "ADCT, art. 125; LC 214/2025, arts. 343, 346 e 348",
    ),
    PassoDaReforma(
        "2027",
        "A CBS passa a valer de fato e o PIS e a Cofins acabam. O IPI vai a zero, menos para "
        "o que também é fabricado com incentivo na Zona Franca de Manaus. Começa o Imposto "
        "Seletivo, sobre o que faz mal à saúde ou ao meio ambiente.",
        "ADCT, art. 126",
    ),
    PassoDaReforma(
        "2027 e 2028",
        "O IBS segue em teste, a 0,1 % (0,05 % dos estados e 0,05 % dos municípios), e a CBS "
        "é cobrada 0,1 ponto abaixo da alíquota de referência.",
        "ADCT, art. 127",
    ),
    PassoDaReforma(
        "2029",
        "O ICMS e o ISS começam a encolher: valem 9/10 das alíquotas de hoje. O IBS sobe o "
        "bastante para repor a receita.",
        "ADCT, arts. 128 e 130",
    ),
    PassoDaReforma("2030", "ICMS e ISS a 8/10 das alíquotas.", "ADCT, art. 128"),
    PassoDaReforma("2031", "ICMS e ISS a 7/10 das alíquotas.", "ADCT, art. 128"),
    PassoDaReforma("2032", "ICMS e ISS a 6/10 das alíquotas.", "ADCT, art. 128"),
    PassoDaReforma(
        "2033",
        "O ICMS e o ISS acabam. Ficam a CBS, o IBS e o Imposto Seletivo.",
        "ADCT, art. 129",
    ),
    PassoDaReforma(
        "Trava da carga",
        "O Senado fixa as alíquotas de referência para a arrecadação não subir nem cair com a "
        "troca. Se a receita passar da média de 2012 a 2021 em proporção do PIB, as alíquotas "
        "caem: a da CBS em 2030, e as duas em 2035.",
        "ADCT, art. 130",
    ),
]


# ------------------------------------------------------------------ reforma: os números

# Os números que o simulador da reforma usa. Os arts. 125 a 129 do ADCT estão citados acima,
# em `REFORMA_DO_CONSUMO`. A Lei Complementar nº 214/2025 foi lida em 14/11/2026 no TEXTO
# ATUALIZADO da Câmara, que já traz as mudanças da LC nº 227, de 13/1/2026
# (www2.camara.leg.br/legin/fed/leicom/2025/
# leicomplementar-214-16-janeiro-2025-796905-normaatualizada-pl.html): os artigos citados
# abaixo e os arts. 343 a 349 conferem com a publicação original, e a LC 227 só mexeu, entre
# eles, no § 10 do art. 475 e no inciso I do § 2º do art. 117.
REFORMA_ANOS = list(range(2026, 2034))
IBS_TESTE_2026 = 0.1
CBS_TESTE_2026 = 0.9
IBS_2027_2028 = 0.1
"""0,05 % estadual mais 0,05 % municipal."""
CBS_DESCONTO_2027_2028 = 0.1
"""Pontos percentuais tirados da alíquota de referência da CBS em 2027 e 2028."""
ICMS_ISS_QUE_CONTINUA = {2026: 100, 2027: 100, 2028: 100, 2029: 90, 2030: 80, 2031: 70}
ICMS_ISS_QUE_CONTINUA |= {2032: 60, 2033: 0}
PIS_COFINS_QUE_CONTINUA = {ano: (100 if ano == 2026 else 0) for ano in REFORMA_ANOS}
"""Também o IPI, zerado em 2027 menos no que a Zona Franca de Manaus produz."""

# LC 214, art. 12: "A base de cálculo do IBS e da CBS é o valor da operação"; § 2º: "Não
#   integram a base de cálculo do IBS e da CBS: I - o montante do IBS e da CBS incidentes sobre
#   a operação" (o imposto é "por fora": cobrado sobre o valor sem ele) e, até 2032, "V - o
#   montante [...]" do ICMS, do ISS, da Cofins e do PIS.
# LC 214, art. 125: "Ficam reduzidas a zero as alíquotas do IBS e da CBS incidentes sobre as
#   vendas de produtos destinados à alimentação humana relacionados no Anexo I [...] que
#   compõem a Cesta Básica Nacional de Alimentos".
# LC 214, art. 127: "Ficam reduzidas em 30% (trinta por cento) as alíquotas do IBS e da CBS
#   incidentes sobre a prestação de serviços pelos seguintes profissionais [...] submetidas à
#   fiscalização por conselho profissional: I - administradores; II - advogados; III -
#   arquitetos e urbanistas; [...] VII - contabilistas; VIII - economistas; [...] XI -
#   engenheiros e agrônomos" (dezoito profissões).
# LC 214, art. 128: "ficam reduzidas em 60% (sessenta por cento) as alíquotas do IBS e da CBS
#   incidentes sobre operações com: I - serviços de educação; II - serviços de saúde; III -
#   dispositivos médicos; IV - dispositivos de acessibilidade [...]; V - medicamentos; VI -
#   alimentos destinados ao consumo humano; VII - produtos de higiene pessoal e limpeza
#   majoritariamente consumidos por famílias de baixa renda; VIII - produtos agropecuários
#   [...] in natura; IX - insumos agropecuários e aquícolas; X - produções nacionais
#   artísticas, culturais, de eventos, jornalísticas e audiovisuais; XI - comunicação
#   institucional; XII - atividades desportivas; e XIII - bens e serviços relacionados à
#   soberania e à segurança nacional". Cada item tem lista própria nos anexos: a redução vale
#   para o que está na lista, não para tudo o que o nome sugere.
# LC 214, arts. 344, parágrafo único, I, e 347, § 1º, I: em 2027 e 2028 as alíquotas valem "com
#   a respectiva redução no caso das operações sujeitas a alíquota reduzida".
REDUCAO_PROFISSIONAIS = 30.0
REDUCAO_SAUDE_EDUCACAO_ALIMENTOS = 60.0

# A devolução a famílias de baixa renda (o "cashback"). LC 214, art. 113: o destinatário é o
#   responsável por família "cadastrada no Cadastro Único" com "renda familiar mensal per
#   capita de até meio salário-mínimo nacional". Art. 118: "O percentual [...] será de: I -
#   100% (cem por cento) para a CBS e 20% (vinte por cento) para o IBS na aquisição de botijão
#   de até 13 kg [...] de gás liquefeito de petróleo, nas operações de fornecimento domiciliar
#   de energia elétrica, abastecimento de água, esgotamento sanitário e gás canalizado e nas
#   operações de fornecimento de telecomunicações; e II - 20% (vinte por cento) para a CBS e
#   para o IBS, nos demais casos." (§ 1º: União, estados e municípios podem dar mais.) Art.
#   123: as devoluções contam o "consumo familiar realizado a partir do: I - mês de janeiro de
#   2027, para a CBS; e II - mês de janeiro de 2029, para o IBS".
DEVOLUCAO_CBS_CONTAS_DE_CASA = 100.0
DEVOLUCAO_IBS_CONTAS_DE_CASA = 20.0
DEVOLUCAO_GERAL = 20.0
DEVOLUCAO_DO_IBS_DESDE = 2029

# O teto. LC 214, art. 475, § 9º: "A primeira avaliação quinquenal será realizada com base nos
#   dados disponíveis no ano-calendário de 2030"; § 10: "serão estimadas as alíquotas de
#   referência de IBS e CBS em 2033"; § 11: "Caso a soma das alíquotas de referência estimadas
#   [...] resulte em percentual superior a 26,5% (vinte e seis inteiros e cinco décimos por
#   cento), o Poder Executivo da União, ouvido o Comitê Gestor do IBS, deverá encaminhar ao
#   Congresso Nacional projeto de lei complementar propondo medidas que reduzam o percentual a
#   patamar igual ou inferior a 26,5%". Não é limite automático: obriga a propor o ajuste.
TETO_IBS_CBS = 26.5
TETO_IBS_CBS_NORMA = "LC nº 214/2025, art. 475, § 11"
REFORMA_NORMAS = (
    "Emenda Constitucional nº 132/2023 (ADCT, arts. 125 a 130) e Lei Complementar nº 214/2025 "
    "(arts. 12, 118, 123, 125, 127, 128, 343 a 349 e 475)"
)


# ------------------------------------------------------------------ reforma: o destino

# Para onde vai o IBS de estados e municípios. Lido em 15/11/2026 no texto atualizado da
# Constituição na Câmara (o mesmo endereço acima), ADCT, art. 131: "De 2029 a 2077, o produto
# da arrecadação dos Estados, do Distrito Federal e dos Municípios com o imposto de que trata o
# art. 156-A [...] será distribuído a esses entes federativos conforme o disposto neste
# artigo. § 1º Serão retidos do produto da arrecadação do imposto de cada Estado, do Distrito
# Federal e de cada Município [...]: I - de 2029 a 2032, 80% (oitenta por cento); II - em 2033,
# 90% (noventa por cento); III - de 2034 a 2077, percentual correspondente ao aplicado em 2033,
# reduzido à razão de 1/45 (um quarenta e cinco avos) por ano. § 2º [...] o montante retido
# [...] será distribuído entre os Estados, o Distrito Federal e os Municípios proporcionalmente
# à receita média de cada ente federativo", contada pelo ICMS (estados) e pelo ISS
# (municípios). § 4º: a parte não retida, depois da retenção do art. 132, vai a cada ente
# "de acordo com os critérios da lei complementar" (o destino, onde se consome: Constituição,
# art. 156-A, § 1º, VII, e LC 214).
# Art. 132: "deduzida a retenção de que trata o art. 131, § 1º, será retido montante
# correspondente a 5% (cinco por cento) para distribuição aos entes com as menores razões"
# entre o que recebem e a receita média (o seguro para quem mais perde); § 3º: a redução
# desse percentual entre 2078 e 2097 fica para lei complementar.
# Leitura nossa da conta, dita na nota do gráfico: "1/45 por ano" sobre os 90 % de 2033, ou
# seja, 90 × (1 − n/45) no ano 2033 + n: 88 % em 2034, 2 % em 2077, zero em 2078.
IBS_PELA_RECEITA_ANTIGA = {ano: 80.0 for ano in range(2029, 2033)} | {
    ano: round(90.0 * (1 - (ano - 2033) / 45), 4) for ano in range(2033, 2078)
}
"""% do IBS de estados e municípios repartido pela receita média de ICMS e ISS de antes."""
IBS_SEGURO_PARA_QUEM_PERDE = 5.0
"""% do que sobra depois da retenção do art. 131, para os que mais perdem (ADCT, art. 132)."""
IBS_DESTINO_NORMA = "ADCT, arts. 131 e 132 (Emenda Constitucional nº 132/2023)"


# ------------------------------------------------------------------ reforma: Seletivo e Simples


@dataclass(frozen=True)
class Regra:
    """Uma regra da lei em palavras de todo dia, com o artigo."""

    tema: str
    diz: str
    norma: str


# Lei Complementar nº 214/2025, Livro II (arts. 409 a 438), lida em 15/11/2026 no texto
# atualizado da Câmara (o endereço em `REFORMA_DO_CONSUMO`, já com a LC 227/2026). Trechos:
# - Art. 409, § 1º: "consideram-se prejudiciais à saúde ou ao meio ambiente os bens
#   classificados nos códigos da NCM/SH e o carvão mineral, e os serviços listados no Anexo
#   XVII, referentes a: I - veículos; II - embarcações e aeronaves; III - produtos fumígenos; IV
#   - bebidas alcoólicas; V - bebidas açucaradas; VI - bens minerais; VII - concursos de
#   prognósticos e fantasy sport."
# - Art. 410: "incidirá uma única vez sobre o bem ou serviço, sendo vedado qualquer tipo de
#   aproveitamento de crédito".
# - Art. 413: "não incide sobre: [...] II - as operações com energia elétrica e com
#   telecomunicações; e III - os bens e serviços cujas alíquotas sejam reduzidas nos termos do
#   § 1º do art. 9º da Emenda Constitucional nº 132". A EC 132, art. 9º (lida no Senado, mesmo
#   dia), § 1º, é a lista do desconto de 60 %, e o § 9º repete: o Seletivo "não incidirá sobre
#   os bens ou serviços cujas alíquotas sejam reduzidas nos termos do § 1º deste artigo".
# - Arts. 419, 421 e 422: as alíquotas de veículos, aeronaves, embarcações e "demais produtos"
#   "serão estabelecidas em lei ordinária". A LC não fixa número, menos este: art. 422, § 2º
#   (redação da LC 227/2026): "As alíquotas do Imposto Seletivo respeitarão o percentual máximo
#   de 0,25% (vinte e cinco centésimos por cento), nas operações com bens minerais extraídos."
# - Art. 422, § 5º (redação da LC 227/2026): para fumo, bebida alcoólica e bebida açucarada, as
#   alíquotas "serão fixadas de forma escalonada, de modo a incorporar, a partir de 2029 até
#   2033, progressivamente, o diferencial entre as alíquotas de ICMS incidentes sobre [esses
#   produtos] e as alíquotas modais desse imposto".
# - Art. 420: alíquota zero para o veículo de quem tem o benefício do art. 149 (I, o taxista;
#   II, a pessoa com deficiência física, visual, auditiva ou mental severa, ou com transtorno do
#   espectro autista); § 1º: para quem está no inciso II, só o veículo de até
#   "R$ 200.000,00 (duzentos mil reais)".
# - Art. 436: "As alíquotas específicas referidas neste Livro serão atualizadas pelo IPCA uma
#   vez ao ano".
# - ADCT, art. 126, I, "b": o Seletivo é cobrado "a partir de 2027".
# Simples Nacional, mesma lei e mesma leitura:
# - Art. 41, § 2º: "Os contribuintes optantes pelo Simples Nacional ou pelo MEI ficam sujeitos
#   às regras desses regimes"; § 3º: "poderão exercer a opção de apurar e recolher o IBS e a
#   CBS pelo regime regular".
# - Art. 47, § 9º: pagando pelo Simples, "I - não será permitida a apropriação de créditos do
#   IBS e da CBS pelo optante pelo Simples Nacional; e II - será permitida ao contribuinte
#   sujeito ao regime regular [...] a apropriação de créditos [...] em montante equivalente ao
#   devido por meio desse regime".
# - LC 123/2006, art. 13, §§ 9º e 10 (acrescidos pela LC 227/2026, no texto da LC 214 na
#   Câmara): a opção pelo regime regular "será exercida para os semestres iniciados em janeiro
#   e julho de cada ano, sendo irretratável para cada um desses períodos, devendo ser exercida
#   nos meses de setembro e março imediatamente anteriores a cada semestre".
SELETIVO_MINERAIS_MAXIMO = 0.25
"""% máximo do Imposto Seletivo sobre bem mineral extraído (LC 214, art. 422, § 2º)."""
SELETIVO_VEICULO_PCD_ATE = 200_000.0
"""R$: até este preço, o carro da pessoa com deficiência não paga o Seletivo (art. 420, § 1º)."""
SELETIVO_E_SIMPLES: list[Regra] = [
    Regra(
        "Seletivo: sobre o quê",
        "Carros, barcos e aviões; cigarro e outros fumígenos; bebida alcoólica; bebida "
        "açucarada; minérios extraídos; loterias e apostas de fantasia (fantasy sport).",
        "LC 214/2025, art. 409, § 1º",
    ),
    Regra(
        "Seletivo: quando",
        "A partir de 2027, uma vez só na cadeia (de quem fabrica, extrai ou importa), sem "
        "crédito para a etapa seguinte.",
        "ADCT, art. 126, I, b; LC 214/2025, arts. 410 e 412",
    ),
    Regra(
        "Seletivo: fora",
        "Luz e telefone, e o que tem o desconto de 60 % no IBS e na CBS (saúde, educação, "
        "remédios, alimentos e o resto das listas desse desconto).",
        "LC 214/2025, art. 413; Emenda Constitucional nº 132/2023, art. 9º, § 9º",
    ),
    Regra(
        "Seletivo: alíquotas",
        "A lei complementar não fixa: ficam para lei ordinária. O único número dela é o teto "
        "de 0,25 % para minérios. Os valores em reais por unidade sobem com o IPCA uma vez "
        "por ano.",
        "LC 214/2025, arts. 419, 421, 422 e 436",
    ),
    Regra(
        "Seletivo: cigarro e bebida",
        "De 2029 a 2033, a alíquota sobe aos poucos para cobrir a diferença entre o ICMS que "
        "esses produtos pagam hoje e o ICMS comum, que acaba.",
        "LC 214/2025, art. 422, § 5º",
    ),
    Regra(
        "Seletivo: carro sem imposto",
        "Alíquota zero para o carro de taxista e de pessoa com deficiência ou autismo; para "
        "estes dois, só até R$ 200 mil.",
        "LC 214/2025, arts. 149 e 420",
    ),
    Regra(
        "Simples: continua",
        "A empresa do Simples Nacional e o MEI seguem pagando numa guia só, com o IBS e a CBS "
        "dentro dela.",
        "LC 214/2025, art. 41, § 2º",
    ),
    Regra(
        "Simples: crédito de quem compra",
        "Quem compra de empresa do Simples abate do próprio imposto só o que ela pagou no "
        "Simples, menos que a alíquota cheia.",
        "LC 214/2025, art. 47, § 9º",
    ),
    Regra(
        "Simples: pode sair só do IBS e da CBS",
        "A empresa pode pagar o IBS e a CBS pelas regras gerais e ficar no Simples no resto; "
        "escolhe a cada semestre, em setembro e em março.",
        "LC 214/2025, art. 41, § 3º; LC 123/2006, art. 13, §§ 9º e 10",
    ),
]


# ------------------------------------------------------------------ reforma: regimes próprios
#
# Lei Complementar nº 214/2025, Título V do Livro I ("Dos regimes específicos do IBS e da CBS",
# arts. 172 a 307) e partes do Título IV ("Dos regimes diferenciados"), lida em 15/11/2026 no
# texto atualizado da Câmara (o mesmo endereço de `REFORMA_DO_CONSUMO`, já com a LC 227/2026).
# Os descontos de 30 % e 60 % e a alíquota zero (arts. 125 a 148) estão em `REDUCAO_*` e na
# tabela dos descontos; aqui fica o que tem regra própria de base, de alíquota ou de crédito.
# Trechos:
# - Art. 172: "O IBS e a CBS incidirão uma única vez sobre as operações [...] com os seguintes
#   combustíveis" (gasolina, etanol, diesel, biodiesel, GLP, querosene de aviação, gás natural
#   e outros); art. 173: "A base de cálculo [...] será a quantidade de combustível"; art. 174:
#   alíquotas "uniformes em todo o território nacional, específicas por unidade de medida e
#   diferenciadas por produto"; § 1º: "As alíquotas da CBS em 2027 serão fixadas de forma a não
#   exceder a carga tributária incidente sobre os combustíveis dos tributos federais extintos
#   ou reduzidos"; art. 176: contribuintes são o produtor de biocombustível, a refinaria, a
#   central petroquímica, a UPGN, o formulador e o importador.
# - Art. 192: nas operações de crédito, câmbio e títulos, a base é a receita "com a dedução de:
#   I - despesas financeiras com a captação de recursos; [...] V - perdas incorridas no
#   recebimento de créditos"; art. 233 (redação da LC 227/2026): "a soma das alíquotas do IBS e
#   da CBS incidentes sobre os serviços financeiros [...] corresponderá: I - em 2027 e 2028, a
#   10,85% [...]; II - em 2029, a 11,00%; III - em 2030, a 11,15%; IV - em 2031, a 11,30%; V -
#   em 2032, a 11,50%; e VI - em 2033, a 12,50%".
# - Art. 235: nos planos de saúde, a base é a receita "com a dedução: a) das indenizações
#   correspondentes a eventos ocorridos, efetivamente pagas"; art. 237: as alíquotas
#   "correspondem às alíquotas de referência de cada esfera federativa, reduzidas em 60%"; art.
#   238: "Fica vedado o crédito de IBS e de CBS para os adquirentes de planos de assistência à
#   saúde" (o parágrafo único abre a exceção do plano dos empregados, art. 57, § 3º, IV, f).
# - Art. 245: nos concursos de prognósticos, a base é "o produto da arrecadação, com a dedução
#   de: I - premiações pagas; e II - destinações obrigatórias por lei"; parágrafo único: "As
#   premiações pagas não ficam sujeitas à incidência"; art. 246: alíquotas que "correspondem à
#   soma das alíquotas de referência".
# - Art. 251, § 1º: a pessoa física que aluga só entra se "a) a receita total com essas
#   operações exceda R$ 240.000 [...]; e b) tenham por objeto mais de 3 (três) bens imóveis
#   distintos"; art. 257: o "redutor de ajuste" vinculado a cada imóvel a partir de 2027 reduz a
#   base da venda; art. 259: "redutor social no valor de R$ 100.000,00 [...] por bem imóvel
#   residencial novo e de R$ 30.000,00 [...] por lote residencial"; art. 260 (redação da LC
#   227/2026): no aluguel residencial, "redutor social no valor de R$ 600,00 (seiscentos
#   reais), por mês, por bem imóvel"; art. 261: as alíquotas "ficam reduzidas em 50%" e, no
#   aluguel, "em 70%".
# - Art. 271: as cooperativas "poderão optar por regime específico [...] no qual ficam
#   reduzidas a zero as alíquotas" na operação do associado com a cooperativa e da cooperativa
#   com o associado que paga pelo regime regular.
# - Arts. 273, 275 e 276: bares e restaurantes, "reduzidas em 40%", e "Fica vedada a
#   apropriação de créditos [...] pelos adquirentes"; arts. 277, 281 e 283: hotelaria, parques
#   de diversão e temáticos, também 40 % e sem crédito para quem compra; art. 289: a agência de
#   turismo paga sobre "o valor da operação, deduzidos os valores repassados para os
#   fornecedores", na alíquota da hotelaria.
# - Art. 286: transporte coletivo de passageiros "rodoviário, ferroviário e hidroviário
#   intermunicipais e interestaduais", alíquotas "reduzidas em 40%"; art. 287: o mesmo para o
#   "transporte aéreo regional coletivo de passageiros ou de carga".
# - Art. 157: "Fica isento do IBS e da CBS o fornecimento de serviços de transporte público
#   coletivo de passageiros rodoviário e metroviário de caráter urbano, semiurbano e
#   metropolitano"; art. 285: no ferroviário e hidroviário urbano, alíquotas "reduzidas em 100%".
# - Art. 293, § 4º (redação da LC 227/2026): a SAF paga numa guia só "4% (quatro por cento)
#   para os tributos federais unificados" (IRPJ, CSLL e as contribuições do art. 22 da Lei
#   8.212), "1% (um por cento) para a CBS" e "1% (um por cento) para o IBS".
# - Art. 164: o produtor rural com "receita inferior a R$ 3.600.000,00 [...] e o produtor rural
#   integrado não serão considerados contribuintes"; art. 168: quem compra dele pode
#   "apropriar créditos presumidos".
REGIMES_PROPRIOS: list[Regra] = [
    Regra(
        "Combustíveis",
        "Cobrado uma vez só, de quem refina, produz ou importa, em reais por litro ou por "
        "quilo, igual no país todo. A CBS de 2027 não pode passar o PIS e a Cofins de hoje.",
        "LC 214/2025, arts. 172 a 174 e 176",
    ),
    Regra(
        "Bancos e serviços financeiros",
        "Imposto sobre a margem: a receita menos o custo de captar o dinheiro e as perdas com "
        "calote. Alíquota própria, somando IBS e CBS: 10,85 % em 2027 e 2028, subindo até "
        "12,5 % em 2033.",
        "LC 214/2025, arts. 181, 192 e 233",
    ),
    Regra(
        "Planos de saúde",
        "Imposto sobre o que a operadora recebe menos o que paga de consultas e internações, "
        "com 60 % de desconto. Quem paga o plano não abate (a não ser a empresa, no plano dos "
        "empregados).",
        "LC 214/2025, arts. 234, 235, 237 e 238",
    ),
    Regra(
        "Loterias e apostas",
        "Imposto sobre o que fica com a empresa depois dos prêmios e dos repasses que a lei "
        "manda, na alíquota cheia. O prêmio não paga.",
        "LC 214/2025, arts. 244 a 246",
    ),
    Regra(
        "Compra e venda de imóveis",
        "Desconto de 50 %. Na venda, abate-se o valor do imóvel (o redutor de ajuste) e mais "
        "R$ 100 mil por casa nova ou R$ 30 mil por lote (o redutor social).",
        "LC 214/2025, arts. 251, 257, 259 e 261",
    ),
    Regra(
        "Aluguel",
        "Desconto de 70 % e R$ 600 por mês abatidos de cada aluguel de moradia. A pessoa física "
        "só paga se receber mais de R$ 240 mil por ano de aluguel de mais de três imóveis.",
        "LC 214/2025, arts. 251, § 1º, 260 e 261, parágrafo único",
    ),
    Regra(
        "Cooperativas",
        "Podem escolher alíquota zero no que o associado vende à cooperativa e no que ela "
        "fornece ao associado que paga pelas regras gerais.",
        "LC 214/2025, art. 271",
    ),
    Regra(
        "Bares e restaurantes",
        "Desconto de 40 %; quem compra a refeição não abate o imposto.",
        "LC 214/2025, arts. 273, 275 e 276",
    ),
    Regra(
        "Hotéis, parques e agências de turismo",
        "Desconto de 40 %. A agência paga só sobre o que fica com ela, depois de repassar ao "
        "hotel e à companhia aérea.",
        "LC 214/2025, arts. 277, 281, 288 e 289",
    ),
    Regra(
        "Ônibus, trem e barco entre cidades; avião regional",
        "Desconto de 40 %.",
        "LC 214/2025, arts. 284, 286 e 287",
    ),
    Regra(
        "Transporte público na cidade",
        "Ônibus e metrô urbanos isentos; trem e barco urbanos com alíquota zero.",
        "LC 214/2025, arts. 157 e 285",
    ),
    Regra(
        "Clubes de futebol (SAF)",
        "Uma guia só sobre a receita: 4 % para IRPJ, CSLL e INSS da empresa, 1 % de CBS e 1 % "
        "de IBS.",
        "LC 214/2025, art. 293, § 4º",
    ),
    Regra(
        "Produtor rural pequeno",
        "Quem fatura menos de R$ 3,6 milhões por ano não paga; quem compra dele abate um "
        "crédito presumido.",
        "LC 214/2025, arts. 164 e 168",
    ),
]


# ---- Meta de universalização do saneamento (o Marco Legal do Saneamento).
@dataclass(frozen=True)
class MetaDeSaneamento:
    agua: float
    """% da população com água potável."""
    esgoto: float
    """% da população com coleta e tratamento de esgotos."""
    prazo: date
    referencia: str


# Lida em 14/11/2026 na Câmara (www2.camara.leg.br/legin/fed/lei/2007/
# lei-11445-5-janeiro-2007-549031-normaatualizada-pl.html, o texto já com as alterações; o
# Planalto não abre da nuvem). Lei 11.445/2007, art. 11-B, acrescido pela Lei 14.026/2020:
# "Os contratos de prestação dos serviços públicos de saneamento básico deverão definir metas
# de universalização que garantam o atendimento de 99% (noventa e nove por cento) da
# população com água potável e de 90% (noventa por cento) da população com coleta e
# tratamento de esgotos até 31 de dezembro de 2033". A meta é dos contratos e de cada
# município (§ 6º), medida pela agência reguladora; não é uma pesquisa do IBGE.
META_SANEAMENTO = MetaDeSaneamento(
    agua=99.0,
    esgoto=90.0,
    prazo=date(2033, 12, 31),
    referencia="Lei 11.445/2007, art. 11-B (Lei 14.026/2020)",
)


# O salário mínimo do ano: o número vem do SGS 1619 (catalogo.py) e a norma de cada ano fica
# aqui, para a tela citá-la (revisão das telas, 15/11/2026). Lido em 15/11/2026 no Senado
# (legis.senado.leg.br/norma/41882097/publicacao/41888369; o Planalto não abre da nuvem).
# Decreto nº 12.797, de 23/12/2025, art. 1º: "A partir de 1º de janeiro de 2026, o valor do
# salário mínimo será de R$ 1.621,00 (mil seiscentos e vinte e um reais)." O SGS 1619 dá
# 1.621,00 de jan a dez/2026. Ano sem norma lida aqui: a tela cita só o SGS.
SALARIO_MINIMO_NORMAS: dict[int, str] = {
    2026: "Decreto nº 12.797, de 23/12/2025, art. 1º",
}
