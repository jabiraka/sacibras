"""Registro explícito de séries, com unidade. Nunca um código solto.

Série nova só entra depois de conferida no catálogo da fonte — para o SGS,
`dadosabertos.bcb.gov.br/api/3/action/package_search?fq=codigo_sgs:N` — e a data da
conferência fica no campo `conferida`.
"""

from __future__ import annotations

from dataclasses import dataclass

from sacibras.tipos import Periodicidade, Unidade


@dataclass(frozen=True)
class SerieSGS:
    codigo: int
    nome: str
    unidade: Unidade
    periodicidade: Periodicidade
    conferida: str
    """Data (dd/mm/aaaa) em que título, unidade e periodicidade foram conferidos no BCB."""
    origem: str = ""
    """Quem faz o número, quando não é o governo ("FGV IBRE"). Vai escrito na fonte, e a
    fonte decide se o gráfico pode ser baixado (`licencas.py`)."""

    @property
    def fonte(self) -> str:
        de = f"; {self.origem}" if self.origem else ""
        return f"Banco Central (SGS {self.codigo}{de})"


SGS: dict[str, SerieSGS] = {
    # ---- juros
    "SELIC_META": SerieSGS(
        432, "Meta para a taxa Selic definida pelo Copom", "% a.a.", "D", "13/11/2026"
    ),
    "SELIC_DIA": SerieSGS(11, "Taxa Selic efetiva, ao dia", "% a.d.", "D", "13/11/2026"),
    "CDI_DIA": SerieSGS(12, "Taxa CDI, ao dia", "% a.d.", "D", "13/11/2026"),
    "SELIC_ANUAL": SerieSGS(
        1178, "Taxa Selic efetiva anualizada, base 252", "% a.a.", "D", "14/11/2026"
    ),
    # Conferida no package_search do BCB em 14/11/2026: "Depósitos de poupança a partir de
    # 04.05.2012 - Rentabilidade no período". Cada dia traz o rendimento do mês que começa nele
    # (o aniversário); a conta usa o do dia 1º.
    "POUPANCA": SerieSGS(
        195, "Depósitos de poupança, rentabilidade no período", "% no mês", "D", "14/11/2026"
    ),
    "CDI_ANUAL": SerieSGS(4389, "Taxa CDI anualizada, base 252", "% a.a.", "D", "14/11/2026"),
    # ---- preços
    "IPCA": SerieSGS(433, "IPCA, variação mensal", "% no mês", "M", "13/11/2026"),
    "IPCA_12M": SerieSGS(13522, "IPCA acumulado em 12 meses", "% em 12 meses", "M", "14/11/2026"),
    "IPCA15": SerieSGS(7478, "IPCA-15, variação mensal", "% no mês", "M", "14/11/2026"),
    # O CKAN não lista o 1619 (count 0). Conferido em 15/11/2026 no serviço de metadados do SGS
    # (FachadaWSSGS, getUltimoValorXML): "Salário mínimo", periodicidade M, unidade "u.m.c."
    # (moeda corrente; antes de jul/1994, outras moedas: a tela usa desde 1995), último ponto
    # dez/2026, 1.621,00. E na norma: Decreto nº 12.797, de 23/12/2025, art. 1º, lido no Senado
    # (legis.senado.leg.br/norma/41882097) em 15/11/2026: "A partir de 1º de janeiro de 2026, o
    # valor do salário mínimo será de R$ 1.621,00".
    "SALARIO_MINIMO": SerieSGS(1619, "Salário mínimo", "R$", "M", "15/11/2026"),
    # O IGP-M é da FGV IBRE: o SGS só repassa (não está no catálogo aberto do BC). Os termos
    # da FGV vedam também a divulgação: fora da tela até autorização (`licencas.FGV_IBRE`,
    # Caio, 15/11/2026); `ctx.sgs` recusa a série.
    "IGPM": SerieSGS(
        189, "IGP-M, variação mensal", "% no mês", "M", "13/11/2026", origem="IGP-M: FGV IBRE"
    ),
    "INPC": SerieSGS(188, "INPC, variação mensal", "% no mês", "M", "14/11/2026"),
    # Os cinco núcleos que o BCB acompanha nos documentos de política monetária.
    # Atenção: 11427 é o EX0. O 16121 (fora daqui) o CKAN chama de EX2 e o SGS de EX1: não usar
    # sem tirar a dúvida (14/11/2026).
    "NUCLEO_EX0": SerieSGS(11427, "IPCA, núcleo por exclusão EX0", "% no mês", "M", "14/11/2026"),
    "NUCLEO_EX3": SerieSGS(27839, "IPCA, núcleo por exclusão EX3", "% no mês", "M", "14/11/2026"),
    "NUCLEO_MS": SerieSGS(
        4466, "IPCA, núcleo de médias aparadas com suavização", "% no mês", "M", "14/11/2026"
    ),
    "NUCLEO_DP": SerieSGS(16122, "IPCA, núcleo de dupla ponderação", "% no mês", "M", "14/11/2026"),
    "NUCLEO_P55": SerieSGS(28750, "IPCA, núcleo percentil 55", "% no mês", "M", "14/11/2026"),
    "IPCA_ADMINISTRADOS": SerieSGS(
        4449, "IPCA, preços administrados", "% no mês", "M", "14/11/2026"
    ),
    "IPCA_LIVRES": SerieSGS(11428, "IPCA, itens livres", "% no mês", "M", "14/11/2026"),
    "IPCA_SERVICOS": SerieSGS(10844, "IPCA, serviços", "% no mês", "M", "14/11/2026"),
    "IPCA_COMERCIALIZAVEIS": SerieSGS(
        4447, "IPCA, comercializáveis", "% no mês", "M", "14/11/2026"
    ),
    "IPCA_NAO_COMERCIALIZAVEIS": SerieSGS(
        4448, "IPCA, não comercializáveis", "% no mês", "M", "14/11/2026"
    ),
    "IPCA_DIFUSAO": SerieSGS(21379, "IPCA, índice de difusão", "%", "M", "14/11/2026"),
    # As duas não estão no CKAN do BCB (package_search?fq=codigo_sgs:N dá count 0, como o
    # EX3 e o P55): título, unidade e periodicidade conferidos em 14/11/2026 no serviço de
    # metadados do próprio SGS (FachadaWSSGS, getUltimoValorXML): "IPCA - Industriais" e
    # "IPCA - Alimentação no domicílio", "Var. % mensal", periodicidade M, último ponto out/2026.
    # Serviços subjacentes não foi achado no CKAN nem nos códigos vizinhos: fica de fora.
    "IPCA_INDUSTRIAIS": SerieSGS(27863, "IPCA, bens industriais", "% no mês", "M", "14/11/2026"),
    "IPCA_ALIMENTACAO_DOMICILIO": SerieSGS(
        27864, "IPCA, alimentação no domicílio", "% no mês", "M", "14/11/2026"
    ),
    # ---- câmbio
    "DOLAR": SerieSGS(
        1, "Taxa de câmbio livre, dólar dos EUA (venda)", "R$/US$", "D", "13/11/2026"
    ),
    "DOLAR_MEDIA_MES": SerieSGS(
        3698, "Dólar dos EUA (venda), média do mês", "R$/US$", "M", "14/11/2026"
    ),
    "EURO": SerieSGS(21619, "Taxa de câmbio livre, euro (venda)", "R$", "D", "14/11/2026"),
    "CAMBIO_REAL_EFETIVO": SerieSGS(
        11752, "Taxa de câmbio real efetiva (IPCA), jun/1994 = 100", "índice", "M", "14/11/2026"
    ),
    # ---- atividade e trabalho
    "IBCBR": SerieSGS(24363, "IBC-Br", "índice", "M", "13/11/2026"),
    "IBCBR_DESSAZ": SerieSGS(24364, "IBC-Br com ajuste sazonal", "índice", "M", "13/11/2026"),
    "PIB_12M": SerieSGS(
        4382, "PIB acumulado em 12 meses, valores correntes", "R$ milhões", "M", "14/11/2026"
    ),
    "PIB_VAR_ANUAL": SerieSGS(7326, "PIB, variação real no ano", "% no ano", "A", "14/11/2026"),
    # Da Fecomercio-SP (o catálogo do BC diz "Fonte: Federação do Comércio...", 15/11/2026).
    "CONFIANCA_CONSUMIDOR": SerieSGS(
        4393,
        "Índice de Confiança do Consumidor",
        "índice",
        "M",
        "13/11/2026",
        origem="Fecomercio-SP",
    ),
    "UCI_INDUSTRIA": SerieSGS(
        28561,
        "Utilização da capacidade instalada da indústria de transformação (FGV), dessazonalizada",
        "%",
        "M",
        "14/11/2026",
        origem="FGV IBRE",
    ),
    "DESOCUPACAO": SerieSGS(24369, "Taxa de desocupação, PNAD Contínua", "%", "M", "14/11/2026"),
    # O SGS só tem o ESTOQUE do emprego formal (28763 não é o saldo do Caged): o saldo do
    # mês sai da diferença do estoque.
    "EMPREGO_FORMAL": SerieSGS(
        28763, "Estoque de empregos formais, total", "pessoas", "M", "14/11/2026"
    ),
    "EMPREGO_FORMAL_DESSAZ": SerieSGS(
        28784, "Estoque de empregos formais, total, dessazonalizado", "pessoas", "M", "14/11/2026"
    ),
    # O estoque por setor (Novo Caged), sem ajuste sazonal. O CKAN não lista 28764 a 28783
    # (package_search?fq=codigo_sgs:N dá count 0): nome, unidade ("Unidades") e periodicidade
    # conferidos um a um em 15/11/2026 no serviço de metadados do SGS (FachadaWSSGS,
    # getUltimoValorXML), último ponto set/2026. "Estoque de empregos formais – <setor>". SIUP
    # (28767) é a soma de 28768 e 28769; Serviços (28772), a de 28773 a 28783. De 28784 em
    # diante vêm os mesmos, dessazonalizados.
    "EMPREGO_AGRO": SerieSGS(
        28764, "Estoque de empregos formais, agropecuária", "pessoas", "M", "15/11/2026"
    ),
    "EMPREGO_EXTRATIVAS": SerieSGS(
        28765, "Estoque de empregos formais, indústrias extrativas", "pessoas", "M", "15/11/2026"
    ),
    "EMPREGO_TRANSFORMACAO": SerieSGS(
        28766,
        "Estoque de empregos formais, indústrias de transformação",
        "pessoas",
        "M",
        "15/11/2026",
    ),
    "EMPREGO_SIUP": SerieSGS(
        28767,
        "Estoque de empregos formais, eletricidade, gás, água e esgoto (SIUP)",
        "pessoas",
        "M",
        "15/11/2026",
    ),
    "EMPREGO_CONSTRUCAO": SerieSGS(
        28770, "Estoque de empregos formais, construção", "pessoas", "M", "15/11/2026"
    ),
    "EMPREGO_COMERCIO": SerieSGS(
        28771, "Estoque de empregos formais, comércio", "pessoas", "M", "15/11/2026"
    ),
    "EMPREGO_SERVICOS": SerieSGS(
        28772, "Estoque de empregos formais, serviços", "pessoas", "M", "15/11/2026"
    ),
    "EMPREGO_TRANSPORTE": SerieSGS(
        28773,
        "Estoque de empregos formais, transporte, armazenamento e correio",
        "pessoas",
        "M",
        "15/11/2026",
    ),
    "EMPREGO_ALOJAMENTO": SerieSGS(
        28774,
        "Estoque de empregos formais, alojamento e alimentação",
        "pessoas",
        "M",
        "15/11/2026",
    ),
    "EMPREGO_INFORMACAO": SerieSGS(
        28775,
        "Estoque de empregos formais, informação e comunicação",
        "pessoas",
        "M",
        "15/11/2026",
    ),
    "EMPREGO_FINANCEIRAS": SerieSGS(
        28776,
        "Estoque de empregos formais, atividades financeiras e seguros",
        "pessoas",
        "M",
        "15/11/2026",
    ),
    "EMPREGO_IMOBILIARIAS": SerieSGS(
        28777,
        "Estoque de empregos formais, atividades imobiliárias",
        "pessoas",
        "M",
        "15/11/2026",
    ),
    "EMPREGO_PROFISSIONAIS": SerieSGS(
        28778,
        "Estoque de empregos formais, atividades profissionais, científicas e técnicas",
        "pessoas",
        "M",
        "15/11/2026",
    ),
    "EMPREGO_ADMINISTRATIVAS": SerieSGS(
        28779,
        "Estoque de empregos formais, atividades administrativas e serviços complementares",
        "pessoas",
        "M",
        "15/11/2026",
    ),
    "EMPREGO_ADM_PUBLICA": SerieSGS(
        28780,
        "Estoque de empregos formais, administração pública, defesa e seguridade social",
        "pessoas",
        "M",
        "15/11/2026",
    ),
    "EMPREGO_EDUCACAO": SerieSGS(
        28781, "Estoque de empregos formais, educação", "pessoas", "M", "15/11/2026"
    ),
    "EMPREGO_SAUDE": SerieSGS(
        28782,
        "Estoque de empregos formais, saúde e serviços sociais",
        "pessoas",
        "M",
        "15/11/2026",
    ),
    "EMPREGO_OUTROS_SERVICOS": SerieSGS(
        28783,
        "Estoque de empregos formais, outras atividades de serviços",
        "pessoas",
        "M",
        "15/11/2026",
    ),
    # ---- setor externo
    "RESERVAS": SerieSGS(3546, "Reservas internacionais, total", "US$ milhões", "M", "14/11/2026"),
    "RESERVAS_DIA": SerieSGS(
        13621, "Reservas internacionais, total, diária", "US$ milhões", "D", "14/11/2026"
    ),
    "BALANCA_COMERCIAL": SerieSGS(
        22707,
        "Balança comercial (balanço de pagamentos), saldo mensal",
        "US$ milhões",
        "M",
        "13/11/2026",
    ),
    "TRANSACOES_CORRENTES": SerieSGS(
        22701, "Transações correntes, saldo mensal", "US$ milhões", "M", "13/11/2026"
    ),
    "TC_12M_PIB": SerieSGS(
        23079, "Transações correntes em 12 meses", "% do PIB", "M", "13/11/2026"
    ),
    "IDP": SerieSGS(
        22885, "Investimentos diretos no país, líquido mensal", "US$ milhões", "M", "14/11/2026"
    ),
    "IDP_12M_PIB": SerieSGS(
        23080, "Investimento direto no país em 12 meses", "% do PIB", "M", "14/11/2026"
    ),
    # Balanço de pagamentos (BPM6) em partes. Conferidas no package_search do BCB em
    # 14/11/2026 (título, "Milhões de dólares americanos", mensal, desde jan/1995). Na conta
    # financeira o BPM6 lança ativos menos passivos: positivo é SAÍDA líquida de recursos.
    "TC_12M": SerieSGS(
        24419, "Transações correntes acumulado em 12 meses", "US$ milhões", "M", "14/11/2026"
    ),
    "BP_SERVICOS": SerieSGS(22719, "Serviços, líquido mensal", "US$ milhões", "M", "14/11/2026"),
    # Os serviços em partes (BPM6), saldo (receita menos despesa) mensal. Conferidas no
    # package_search do BCB em 15/11/2026 ("<nome> - mensal - líquido", US$ milhões, mensal,
    # dado até set/2026). As treze somam o 22719.
    "BP_SERV_MANUFATURA": SerieSGS(
        22722,
        "Serviços de manufatura sobre insumos físicos de outros, líquido mensal",
        "US$ milhões",
        "M",
        "15/11/2026",
    ),
    "BP_SERV_MANUTENCAO": SerieSGS(
        22725, "Serviços de manutenção e reparo, líquido mensal", "US$ milhões", "M", "15/11/2026"
    ),
    "BP_SERV_TRANSPORTES": SerieSGS(
        22728, "Transportes, líquido mensal", "US$ milhões", "M", "15/11/2026"
    ),
    "BP_SERV_VIAGENS": SerieSGS(22740, "Viagens, líquido mensal", "US$ milhões", "M", "15/11/2026"),
    "BP_SERV_CONSTRUCAO": SerieSGS(
        22761, "Construção, líquido mensal", "US$ milhões", "M", "15/11/2026"
    ),
    "BP_SERV_SEGUROS": SerieSGS(22764, "Seguros, líquido mensal", "US$ milhões", "M", "15/11/2026"),
    "BP_SERV_FINANCEIROS": SerieSGS(
        22767, "Serviços financeiros, líquido mensal", "US$ milhões", "M", "15/11/2026"
    ),
    "BP_SERV_PROPRIEDADE": SerieSGS(
        22776,
        "Serviços de propriedade intelectual, líquido mensal",
        "US$ milhões",
        "M",
        "15/11/2026",
    ),
    "BP_SERV_TELECOM": SerieSGS(
        22779,
        "Telecomunicação, computação e informações, líquido mensal",
        "US$ milhões",
        "M",
        "15/11/2026",
    ),
    "BP_SERV_ALUGUEL": SerieSGS(
        22782, "Aluguel de equipamentos, líquido mensal", "US$ milhões", "M", "15/11/2026"
    ),
    "BP_SERV_NEGOCIOS": SerieSGS(
        22785,
        "Outros serviços de negócio, incluindo arquitetura e engenharia, líquido mensal",
        "US$ milhões",
        "M",
        "15/11/2026",
    ),
    "BP_SERV_CULTURAIS": SerieSGS(
        22788,
        "Serviços culturais, pessoais e recreativos, líquido mensal",
        "US$ milhões",
        "M",
        "15/11/2026",
    ),
    "BP_SERV_GOVERNO": SerieSGS(
        22797, "Serviços governamentais, líquido mensal", "US$ milhões", "M", "15/11/2026"
    ),
    "BP_RENDA_PRIMARIA": SerieSGS(
        22800, "Renda primária, líquido mensal", "US$ milhões", "M", "14/11/2026"
    ),
    "BP_RENDA_SECUNDARIA": SerieSGS(
        22838, "Renda secundária, líquido mensal", "US$ milhões", "M", "14/11/2026"
    ),
    "BP_CONTA_FINANCEIRA": SerieSGS(
        22863, "Conta financeira, líquido mensal", "US$ milhões", "M", "14/11/2026"
    ),
    "BP_IDE": SerieSGS(
        22865,
        "Investimentos diretos no exterior (IDE), líquido mensal",
        "US$ milhões",
        "M",
        "14/11/2026",
    ),
    "BP_CARTEIRA": SerieSGS(
        22905, "Investimentos em carteira, líquido mensal", "US$ milhões", "M", "14/11/2026"
    ),
    "BP_DERIVATIVOS": SerieSGS(
        22966, "Derivativos, líquido mensal", "US$ milhões", "M", "14/11/2026"
    ),
    "BP_OUTROS_INVESTIMENTOS": SerieSGS(
        22969, "Outros investimentos, líquido mensal", "US$ milhões", "M", "14/11/2026"
    ),
    "BP_ATIVOS_RESERVA": SerieSGS(
        23043, "Ativos de reserva, fluxo mensal", "US$ milhões", "M", "14/11/2026"
    ),
    "ICBR": SerieSGS(27574, "Índice de Commodities Brasil (IC-Br)", "índice", "M", "14/11/2026"),
    "ICBR_AGRO": SerieSGS(27575, "IC-Br, agropecuária", "índice", "M", "14/11/2026"),
    "ICBR_METAL": SerieSGS(27576, "IC-Br, metal", "índice", "M", "14/11/2026"),
    "ICBR_ENERGIA": SerieSGS(27577, "IC-Br, energia", "índice", "M", "14/11/2026"),
    # ---- crédito
    "CREDITO_SALDO": SerieSGS(
        20539, "Saldo da carteira de crédito, total", "R$ milhões", "M", "13/11/2026"
    ),
    "CREDITO_PIB": SerieSGS(
        20622, "Saldo da carteira de crédito em relação ao PIB", "% do PIB", "M", "14/11/2026"
    ),
    "CREDITO_CONCESSOES": SerieSGS(
        20631, "Concessões de crédito, total", "R$ milhões", "M", "14/11/2026"
    ),
    "CREDITO_TAXA": SerieSGS(
        20714, "Taxa média de juros das operações de crédito, total", "% a.a.", "M", "13/11/2026"
    ),
    "CREDITO_SPREAD": SerieSGS(
        20783, "Spread médio das operações de crédito, total", "pp", "M", "14/11/2026"
    ),
    # Juros das pessoas físicas por modalidade (recursos livres): conferidos no package_search
    # do BCB em 15/11/2026, título, "Percentual ao ano" e mensal. Revisão das telas: quem busca
    # "juros do cartão" ou "cheque especial" não achava nada.
    "PF_CARTAO_ROTATIVO": SerieSGS(
        22022,
        "Taxa média de juros, pessoas físicas, cartão de crédito rotativo",
        "% a.a.",
        "M",
        "15/11/2026",
    ),
    "PF_CARTAO_PARCELADO": SerieSGS(
        22023,
        "Taxa média de juros, pessoas físicas, cartão de crédito parcelado",
        "% a.a.",
        "M",
        "15/11/2026",
    ),
    "PF_CHEQUE_ESPECIAL": SerieSGS(
        20741,
        "Taxa média de juros, pessoas físicas, cheque especial",
        "% a.a.",
        "M",
        "15/11/2026",
    ),
    "PF_PESSOAL": SerieSGS(
        20742,
        "Taxa média de juros, pessoas físicas, crédito pessoal não consignado",
        "% a.a.",
        "M",
        "15/11/2026",
    ),
    "PF_CONSIGNADO": SerieSGS(
        20747,
        "Taxa média de juros, pessoas físicas, crédito pessoal consignado total",
        "% a.a.",
        "M",
        "15/11/2026",
    ),
    "CREDITO_INADIMPLENCIA": SerieSGS(
        21082, "Inadimplência da carteira de crédito, total", "%", "M", "14/11/2026"
    ),
    "FAMILIAS_ENDIVIDAMENTO": SerieSGS(
        29037,
        "Endividamento das famílias com o SFN, em relação à renda de 12 meses",
        "%",
        "M",
        "14/11/2026",
    ),
    "FAMILIAS_COMPROMETIMENTO": SerieSGS(
        29034,
        "Comprometimento de renda das famílias com o serviço da dívida, com ajuste sazonal",
        "%",
        "M",
        "14/11/2026",
    ),
    # Casa própria e bolso das famílias. Conferidas no package_search do BCB em 14/11/2026
    # (título, unidade_medida e periodicidade mensal).
    "FAMILIAS_COMPROMETIMENTO_JUROS": SerieSGS(
        29033,
        "Comprometimento de renda das famílias com juros da dívida com o SFN, com ajuste sazonal",
        "%",
        "M",
        "14/11/2026",
    ),
    "FAMILIAS_ENDIVIDAMENTO_SEM_HABITACAO": SerieSGS(
        29038,
        "Endividamento das famílias com o SFN exceto crédito habitacional, em relação à renda "
        "de 12 meses",
        "%",
        "M",
        "14/11/2026",
    ),
    "IMOB_TAXA_MERCADO": SerieSGS(
        20772,
        "Taxa média de juros, pessoas físicas, financiamento imobiliário com taxas de mercado",
        "% a.a.",
        "M",
        "14/11/2026",
    ),
    "IMOB_TAXA_REGULADA": SerieSGS(
        20773,
        "Taxa média de juros, pessoas físicas, financiamento imobiliário com taxas reguladas",
        "% a.a.",
        "M",
        "14/11/2026",
    ),
    # No CKAN (conferido em 25/11/2026) o 20704 está entre os recursos direcionados: é o
    # financiamento imobiliário inteiro (taxas de mercado, 20702, mais reguladas, 20703),
    # porque o BC classifica todo o imobiliário como direcionado; nos livres não há linha dele.
    "IMOB_CONCESSOES": SerieSGS(
        20704,
        "Concessões de crédito com recursos direcionados, pessoas físicas, financiamento "
        "imobiliário total",
        "R$ milhões",
        "M",
        "25/11/2026",
    ),
    # IVG-R: valor de avaliação dos imóveis dados em garantia de financiamento residencial
    # (alienação fiduciária e hipoteca), 13 regiões metropolitanas; tendência de longo prazo.
    "IVGR": SerieSGS(
        21340,
        "Índice de Valores de Garantia de Imóveis Residenciais Financiados (IVG-R)",
        "índice",
        "M",
        "14/11/2026",
    ),
    # ---- contas públicas. As séries de NFSP são NECESSIDADE de financiamento: positivo é
    # déficit. Na tela mostramos o RESULTADO (superávit positivo), com o sinal trocado.
    "DBGG": SerieSGS(
        13762,
        "Dívida bruta do governo geral, metodologia a partir de 2008",
        "% do PIB",
        "M",
        "13/11/2026",
    ),
    "DLSP": SerieSGS(
        4513, "Dívida líquida do setor público consolidado", "% do PIB", "M", "13/11/2026"
    ),
    # Os saldos em reais, para o "Ver em" do gráfico da dívida (Caio, 19/11/2026). 4478:
    # conferida no package_search em 19/11/2026 ("Dívida Líquida do Setor Público - Saldos em
    # R$ milhões - Total - Setor público consolidado", mensal, milhões de reais). 13761: o
    # CKAN não a lista; conferida em 19/11/2026 no serviço de metadados do SGS (FachadaWSSGS,
    # getUltimoValorXML): "Dívida bruta do governo geral - Saldos em R$ milhões - Metodologia
    # utilizada a partir de 2008", M, R$ (milhões), set/2026 = 11.113.782,53. Contra a 13762 e o
    # PIB de 12 meses (4382): 11.113.782,53 / 13.398.451,0 = 82,95 %, o mesmo da 13762; a
    # 4478 dá 70,00 %, o mesmo da 4513.
    "DBGG_RS": SerieSGS(
        13761,
        "Dívida bruta do governo geral, saldo, metodologia a partir de 2008",
        "R$ milhões",
        "M",
        "19/11/2026",
    ),
    "DLSP_RS": SerieSGS(
        4478,
        "Dívida líquida do setor público consolidado, saldo",
        "R$ milhões",
        "M",
        "19/11/2026",
    ),
    "NFSP_PRIMARIO_12M": SerieSGS(
        5793,
        "NFSP, resultado primário em 12 meses, setor público consolidado",
        "% do PIB",
        "M",
        "13/11/2026",
    ),
    "NFSP_PRIMARIO_GC_12M": SerieSGS(
        5783,
        "NFSP, resultado primário em 12 meses, Governo Federal e Banco Central",
        "% do PIB",
        "M",
        "14/11/2026",
    ),
    "NFSP_NOMINAL_12M": SerieSGS(
        5727,
        "NFSP, resultado nominal em 12 meses, setor público consolidado",
        "% do PIB",
        "M",
        "13/11/2026",
    ),
    "NFSP_JUROS_12M": SerieSGS(
        5760,
        "NFSP, juros nominais em 12 meses, setor público consolidado",
        "% do PIB",
        "M",
        "14/11/2026",
    ),
    "NFSP_PRIMARIO_MES": SerieSGS(
        4649,
        "NFSP, resultado primário, fluxo mensal, setor público consolidado",
        "R$ milhões",
        "M",
        "14/11/2026",
    ),
    # Conferidas no package_search em 19/11/2026 (fq=codigo_sgs:N): "NFSP sem desvalorização
    # cambial (% PIB) - Fluxo acumulado em 12 meses - Resultado primário - Total - Empresas
    # estatais federais" (5790), "estaduais" (5791) e "municipais" (5792), Percentual, e
    # "NFSP sem desvalorização cambial - Fluxo mensal corrente - Resultado primário - Total -
    # Empresas estatais federais" (4646), Milhões de reais. As estatísticas fiscais do BC não
    # contam os bancos públicos nem, desde 2009 e 2010, a Petrobras e a Eletrobras.
    "ESTATAIS_FEDERAIS_12M": SerieSGS(
        5790,
        "NFSP, resultado primário em 12 meses, empresas estatais federais",
        "% do PIB",
        "M",
        "19/11/2026",
    ),
    "ESTATAIS_ESTADUAIS_12M": SerieSGS(
        5791,
        "NFSP, resultado primário em 12 meses, empresas estatais estaduais",
        "% do PIB",
        "M",
        "19/11/2026",
    ),
    "ESTATAIS_MUNICIPAIS_12M": SerieSGS(
        5792,
        "NFSP, resultado primário em 12 meses, empresas estatais municipais",
        "% do PIB",
        "M",
        "19/11/2026",
    ),
    "ESTATAIS_FEDERAIS_MES": SerieSGS(
        4646,
        "NFSP, resultado primário, fluxo mensal, empresas estatais federais",
        "R$ milhões",
        "M",
        "19/11/2026",
    ),
    # Conferida no package_search em 14/11/2026: "NFSP sem desvalorização cambial - Fluxo
    # mensal corrente - Resultado primário - Total - Governo Federal e Banco Central" (o
    # Governo Central, que é o da meta da LDO), mensal, mesma família e unidade da 4649.
    "NFSP_PRIMARIO_GC_MES": SerieSGS(
        4639,
        "NFSP, resultado primário, fluxo mensal, Governo Federal e Banco Central",
        "R$ milhões",
        "M",
        "14/11/2026",
    ),
    # Conferida no package_search em 15/11/2026: "NFSP sem desvalorização cambial - Fluxo
    # mensal corrente - Juros nominais - Total - Governo Federal e Banco Central", mensal,
    # "Milhões de reais", desde jan/1991 (set/2026: 104.837,22). Juros por competência, sem o
    # efeito do câmbio; líquidos (o que se paga menos o que se recebe de juros, as reservas
    # inclusive). Par da 4639, para os juros sobre a receita do Governo Central.
    "NFSP_JUROS_GC_MES": SerieSGS(
        4606,
        "NFSP, juros nominais, fluxo mensal, Governo Federal e Banco Central",
        "R$ milhões",
        "M",
        "15/11/2026",
    ),
    # Dívida mobiliária federal, participação por indexador (Percentual, mensal, desde jan/2000).
    # Conferidas no package_search do BCB em 14/11/2026. A família não traz o IPCA (NTN-B):
    # as oito parcelas somam ~76 % em set/2026; o que falta para 100 % é o IPCA.
    "DIVIDA_IDX_CAMBIO": SerieSGS(
        4173,
        "Dívida mobiliária - Participação por indexador - Posição em carteira - Câmbio",
        "%",
        "M",
        "14/11/2026",
    ),
    "DIVIDA_IDX_TR": SerieSGS(
        4174,
        "Dívida mobiliária - Participação por indexador - Posição em carteira - TR",
        "%",
        "M",
        "14/11/2026",
    ),
    "DIVIDA_IDX_IGPM": SerieSGS(
        4175,
        "Dívida mobiliária - Participação por indexador - Posição em carteira - IGP-M",
        "%",
        "M",
        "14/11/2026",
    ),
    "DIVIDA_IDX_IGPDI": SerieSGS(
        4176,
        "Dívida mobiliária - Participação por indexador - Posição em carteira - IGP-DI",
        "%",
        "M",
        "14/11/2026",
    ),
    "DIVIDA_IDX_SELIC": SerieSGS(
        4177,
        "Dívida mobiliária - Participação por indexador - Posição em carteira - Over/Selic",
        "%",
        "M",
        "14/11/2026",
    ),
    "DIVIDA_IDX_PREFIXADO": SerieSGS(
        4178,
        "Dívida mobiliária - Participação por indexador - Posição em carteira - Prefixado",
        "%",
        "M",
        "14/11/2026",
    ),
    "DIVIDA_IDX_TJLP": SerieSGS(
        4179,
        "Dívida mobiliária - Participação por indexador - Posição em carteira - TJLP",
        "%",
        "M",
        "14/11/2026",
    ),
    "DIVIDA_IDX_OUTROS": SerieSGS(
        4180,
        "Dívida mobiliária - Participação por indexador - Posição em carteira - Outros",
        "%",
        "M",
        "14/11/2026",
    ),
    # ---- riscos. Conferidas em 14/11/2026. As marcadas "CKAN" no package_search do BCB
    # (título, unidade, periodicidade); as outras o CKAN não lista (count 0) e foram
    # conferidas no serviço de metadados do próprio SGS (FachadaWSSGS, getUltimoValorXML:
    # nome, unidade e periodicidade) e no dado (último ponto entre parênteses).
    # Juros em reais: o par do 5760 (% do PIB). SGS-meta (set/2026: 1.204.960,77).
    "NFSP_JUROS_12M_RS": SerieSGS(
        5045,
        "NFSP, juros nominais em 12 meses, setor público consolidado",
        "R$ milhões",
        "M",
        "14/11/2026",
    ),
    # CKAN (set/2026: 48,09 meses).
    "DIVIDA_PRAZO_MEDIO": SerieSGS(
        10618,
        "Dívida mobiliária federal, títulos do Tesouro Nacional emitidos, prazo médio",
        "meses",
        "M",
        "14/11/2026",
    ),
    # SGS-meta (set/2026: -3,34). Negativa = o setor público tem mais a receber do que a
    # pagar em moeda estrangeira (as reservas passam a dívida externa).
    "DLSP_EXTERNA": SerieSGS(
        4535,
        "Dívida líquida do setor público, externa, setor público consolidado",
        "% do PIB",
        "M",
        "14/11/2026",
    ),
    # SGS-meta, trimestrais com a data no 1º mês do trimestre (2º tri/2026: 407.102,75 e
    # 113.307,7). O título da 21519 não diz se o prazo é o original ou o residual; a única
    # série "por vencimento residual" (12504) parou em 2018. Antes de 2000, um ponto por ano.
    "DIVIDA_EXTERNA": SerieSGS(3684, "Dívida externa bruta", "US$ milhões", "T", "14/11/2026"),
    "DIVIDA_EXTERNA_CURTO_PRAZO": SerieSGS(
        21519, "Dívida externa bruta, curto prazo", "US$ milhões", "T", "14/11/2026"
    ),
    # CKAN (set/2026: 27.715,2).
    "IMPORTACOES": SerieSGS(
        22709,
        "Importação de bens (balanço de pagamentos), mensal",
        "US$ milhões",
        "M",
        "14/11/2026",
    ),
    # SGS-meta (13/11/2026: 90.250,00). Positivo = o Banco Central vendido em dólar (deu
    # proteção cambial ao mercado). A mensal 29533 tem o sinal contrário e atrasa: não usar.
    "SWAP_CAMBIAL": SerieSGS(
        29723,
        "Estoque de swap cambial do Banco Central, nocional",
        "US$ milhões",
        "D",
        "14/11/2026",
    ),
    # CKAN (set/2026: 5,99; 3,28; 4,86).
    "CREDITO_INADIMPLENCIA_PF": SerieSGS(
        21084, "Inadimplência da carteira de crédito, pessoas físicas", "%", "M", "14/11/2026"
    ),
    "CREDITO_INADIMPLENCIA_PJ": SerieSGS(
        21083, "Inadimplência da carteira de crédito, pessoas jurídicas", "%", "M", "14/11/2026"
    ),
    "CREDITO_ATRASO_15_90": SerieSGS(
        21003,
        "Percentual da carteira de crédito com atraso entre 15 e 90 dias, total",
        "%",
        "M",
        "14/11/2026",
    ),
    # SGS-meta (mar/2026: 16,6038 e 13,8438). Saem com meses de atraso. As antigas 21424 e
    # 21802 pararam em jun/2023. Até set/2013 a 29663 repete o Nível 1 (não havia o conceito).
    "BASILEIA": SerieSGS(
        29661, "Índice de Basileia de todo o Sistema Financeiro Nacional", "%", "M", "14/11/2026"
    ),
    "CAPITAL_PRINCIPAL": SerieSGS(
        29663, "Índice de Capital Principal no Sistema Financeiro Nacional", "%", "M", "14/11/2026"
    ),
    # Liquidez dos bancos. O CKAN não lista (count 0); conferidas em 15/11/2026 no serviço de
    # metadados do SGS (FachadaWSSGS, getUltimoValorXML): 29407 "Índice de Liquidez", T,
    # "Índice" (2º tri/2026: 2,38; desde o 4º tri/2015); 29408 "Indicador de Liquidez de Curto
    # Prazo (LCR)", T, "%" (2º tri/2026: 197,3; desde o 1º tri/2016). As duas são as do
    # Relatório de Estabilidade Financeira: ativos líquidos sobre as saídas de 30 dias de
    # estresse (o IL, conta do BC; acima de 1, sobra) e o LCR de Basileia. O lado ruim é o
    # baixo. O vizinho 29409 é o NSFR (liquidez de longo prazo), fora daqui.
    "LIQUIDEZ_IL": SerieSGS(
        29407, "Índice de Liquidez do sistema bancário", "índice", "T", "15/11/2026"
    ),
    "LIQUIDEZ_LCR": SerieSGS(
        29408, "Indicador de Liquidez de Curto Prazo (LCR)", "%", "T", "15/11/2026"
    ),
    # A meta de cada ano, para medir a distância da expectativa e da inflação implícita. O CKAN
    # não lista; conferida em 15/11/2026 no serviço de metadados do SGS: "Meta para a
    # inflação", A, "%" (de 8,00 em 1999 a 3,00 em 2026; bate com a Resolução CMN 5.141 de
    # `leis.META_CONTINUA`).
    "META_INFLACAO": SerieSGS(
        13521, "Meta para a inflação (centro), por ano", "%", "A", "15/11/2026"
    ),
}

# ---- estados. Conferidas uma a uma em 14/11/2026 no serviço de metadados do próprio SGS
# (FachadaWSSGS, getUltimoValorXML: nome com o estado, unidade e periodicidade M); o CKAN não
# lista as de crédito por UF. Os códigos seguem a ordem alfabética do nome do estado.
# "Saldo das operações de crédito do Sistema Financeiro Nacional - <UF> - Total", R$ (milhões),
# último ponto set/2026 (SP: 2.144.269).
CREDITO_SALDO_UF: dict[str, int] = {
    "AC": 14056,
    "AL": 14057,
    "AP": 14058,
    "AM": 14059,
    "BA": 14060,
    "CE": 14061,
    "DF": 14062,
    "ES": 14063,
    "GO": 14064,
    "MA": 14065,
    "MT": 14066,
    "MS": 14067,
    "MG": 14068,
    "PA": 14069,
    "PB": 14070,
    "PR": 14071,
    "PE": 14072,
    "PI": 14073,
    "RJ": 14074,
    "RN": 14075,
    "RS": 14076,
    "RO": 14077,
    "RR": 14078,
    "SC": 14079,
    "SP": 14080,
    "SE": 14081,
    "TO": 14082,
}
# "Taxa de inadimplência das operações de crédito do Sistema Financeiro Nacional - <UF> -
# Total", %, último ponto set/2026 (SP: 4,03).
CREDITO_INADIMPLENCIA_UF: dict[str, int] = {
    "AC": 15925,
    "AL": 15926,
    "AP": 15927,
    "AM": 15928,
    "BA": 15929,
    "CE": 15930,
    "DF": 15931,
    "ES": 15932,
    "GO": 15933,
    "MA": 15934,
    "MT": 15935,
    "MS": 15936,
    "MG": 15937,
    "PA": 15938,
    "PB": 15939,
    "PR": 15940,
    "PE": 15941,
    "PI": 15942,
    "RJ": 15943,
    "RN": 15944,
    "RS": 15945,
    "RO": 15946,
    "RR": 15947,
    "SC": 15948,
    "SP": 15949,
    "SE": 15950,
    "TO": 15951,
}
# "Índice de Atividade Econômica Regional - <UF> - IBCR-<UF>", sem ajuste sazonal, índice,
# último ponto ago/2026 (SP: 113,34). Treze estão no CKAN (package_search?q=IBCR, 36 séries:
# os 13 e as 5 regiões, com e sem ajuste). Os outros quatro (MA, MS, MT e RN) entraram com o
# boxe "IBCR: inclusão de quatro novas Unidades da Federação e revisão metodológica" do
# Boletim Regional de 2025 do BC (lido em 15/11/2026: "amplia sua cobertura de treze para
# dezessete Unidades da Federação [...] de 85,2% para 91,6% do total nacional"; MT desde
# jan/2013, os outros três desde jan/2023, "em função da disponibilidade de dados da
# Pesquisa Industrial Mensal"; o boxe dá os códigos). O CKAN não os lista
# (fq=codigo_sgs:N devolve zero): conferidos no serviço de metadados do SGS (FachadaWSSGS,
# getUltimoValorXML, 15/11/2026): "Índice de Atividade Econômica Regional - Maranhão -
# IBCR-MA" (29701), "- Rio Grande do Norte - IBCR-RN" (29702), "- Mato Grosso do Sul -
# IBCR-MS" (29703) e "- Mato Grosso - IBCR-MT" (29704), todos M, índice, até ago/2026.
IBCR_UF: dict[str, int] = {
    "AM": 25411,
    "BA": 25415,
    "CE": 25390,
    "ES": 25398,
    "GO": 25383,
    "MA": 29701,
    "MG": 25379,
    "MS": 29703,
    "MT": 29704,
    "PA": 25409,
    "PE": 25417,
    "PR": 25408,
    "RJ": 25396,
    "RN": 29702,
    "RS": 25401,
    "SC": 25402,
    "SP": 25392,
}
# "Índice de Atividade Econômica Regional - Região <nome> - IBCR-<sigla>", sem ajuste, índice
# (CKAN, package_search?q=IBCR, 14/11/2026). Servem à prévia do PIB dos estados sem IBC-R.
IBCR_REGIAO: dict[str, int] = {"N": 25406, "NE": 25388, "SE": 25393, "S": 25400, "CO": 25381}

for _uf, _c in CREDITO_SALDO_UF.items():
    SGS[f"CREDITO_SALDO_{_uf}"] = SerieSGS(
        _c, f"Saldo das operações de crédito do SFN, {_uf}", "R$ milhões", "M", "14/11/2026"
    )
for _uf, _c in CREDITO_INADIMPLENCIA_UF.items():
    SGS[f"CREDITO_INADIMPLENCIA_{_uf}"] = SerieSGS(
        _c, f"Inadimplência das operações de crédito do SFN, {_uf}", "%", "M", "14/11/2026"
    )
for _uf, _c in IBCR_UF.items():
    SGS[f"IBCR_{_uf}"] = SerieSGS(
        _c, f"IBC-R {_uf}", "índice", "M", "15/11/2026" if _c > 29000 else "14/11/2026"
    )
for _r, _c in IBCR_REGIAO.items():
    SGS[f"IBCR_REGIAO_{_r}"] = SerieSGS(_c, f"IBC-R, região {_r}", "índice", "M", "14/11/2026")
