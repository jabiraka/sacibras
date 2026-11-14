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

    @property
    def fonte(self) -> str:
        return f"Banco Central (SGS {self.codigo})"


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
    "IGPM": SerieSGS(189, "IGP-M, variação mensal", "% no mês", "M", "13/11/2026"),
    "INPC": SerieSGS(188, "INPC, variação mensal", "% no mês", "M", "14/11/2026"),
    # Os cinco núcleos que o BCB acompanha nos documentos de política monetária.
    # Atenção: 11427 é o EX0 e 16121 é o EX1 (o palpite de memória tinha os dois trocados).
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
    "CONFIANCA_CONSUMIDOR": SerieSGS(
        4393, "Índice de Confiança do Consumidor", "índice", "M", "13/11/2026"
    ),
    "UCI_INDUSTRIA": SerieSGS(
        28561,
        "Utilização da capacidade instalada da indústria de transformação (FGV), dessazonalizada",
        "%",
        "M",
        "14/11/2026",
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
    "IMOB_CONCESSOES": SerieSGS(
        20704,
        "Concessões de crédito, pessoas físicas, financiamento imobiliário total",
        "R$ milhões",
        "M",
        "14/11/2026",
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
}
