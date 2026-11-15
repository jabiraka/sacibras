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
class AvaliacaoBimestral:
    """O que o governo projeta para o primário do ano no Relatório de Avaliação de Receitas e
    Despesas Primárias (o que a LDO 2026, art. 73, § 4º, manda publicar), em R$ bilhões.

    Não é número de lei: é a conta oficial da meta, lida à mão, com a data."""

    bimestre: str
    resultado: float
    """Resultado primário projetado para o ano, sem os descontos."""
    deducao: float
    """O que a apuração da meta desconta (abatimentos que outras normas autorizam)."""
    fonte: str


# Lido em 14/11/2026 na Nota Informativa da Consultoria de Orçamentos do Senado (Conorf) de
# 25/9/2026 sobre o relatório do 4º bimestre de 2026 (www12.senado.leg.br/orcamento/documentos/
# estudos/tipos-de-estudos/notas-tecnicas-e-informativos/ni_rardp_20260925.pdf), Tabela 1, que
# reproduz o relatório do Executivo: "5. Resultado Primário -52,0 [3º bim.] -80,9 [4º bim.]";
# "6. Dedução EC 136, ADPF 1236 e LCs 221, 223 e 235 62,8 67,3"; "7. Resultado Primário após
# Dedução 10,8 -13,6". Nota 3: precatórios (R$ 54,7 bi), defesa (R$ 5,0 bi), saúde e a ADPF
# 1236. LER DE NOVO a cada bimestre (o do 5º sai até 22/11).
AVALIACOES_2026 = [
    AvaliacaoBimestral("3º bimestre", -52.0, 62.8, "Relatório de Avaliação do 3º bimestre de 2026"),
    AvaliacaoBimestral("4º bimestre", -80.9, 67.3, "Relatório de Avaliação do 4º bimestre de 2026"),
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
