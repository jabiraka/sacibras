"""O índice da busca do site (`busca.json`): cada assunto, número, gráfico e tabela, as métricas
de estados e de países, e os nomes dos estados, com os sinônimos de cada um.

Lido dos JSONs já gravados (os da rodada e os que sobraram da anterior), para que a busca
ache tudo o que o site mostra. Os sinônimos ficam aqui, num dicionário só: quem procura
"desemprego" acha a desocupação; "carestia", o IPCA; "calote", a inadimplência.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from pydantic import BaseModel

# termo que aparece no título → palavras que alguém usaria para procurá-lo
SINONIMOS: dict[str, list[str]] = {
    "ipca": ["inflacao", "precos", "custo de vida", "carestia", "inflação oficial"],
    "inflacao": ["ipca", "precos", "custo de vida", "carestia", "alta dos precos"],
    "nucleo": ["inflacao subjacente", "nucleos", "ritmo da inflacao", "anualizado"],
    "anualizado": ["ritmo", "ritmo da inflacao", "inflacao recente"],
    "selic": ["juros", "taxa basica", "copom", "banco central", "taxa de juros"],
    "juro": ["juros", "selic", "taxa", "rendimento"],
    "copom": ["selic", "juros", "banco central", "reuniao"],
    "cdi": ["di", "renda fixa", "rendimento", "aplicacao"],
    "prefixad": ["tesouro prefixado", "ltn", "titulos publicos", "curva de juros", "di futuro"],
    "ipca+": ["tesouro ipca", "ntn-b", "juro real", "titulos publicos"],
    "implicita": ["inflacao implicita", "breakeven", "expectativa de inflacao", "titulos"],
    "curva": ["curva de juros", "estrutura a termo", "titulos publicos", "vencimento"],
    "dolar": ["cambio", "moeda", "us$", "real", "taxa de cambio", "moeda americana"],
    "euro": ["cambio", "moeda", "europa"],
    "cambio": ["dolar", "euro", "moeda", "real"],
    "ibovespa": ["bolsa", "acoes", "b3", "mercado de acoes", "ibov"],
    "poupanca": ["caderneta", "rendimento", "aplicacao"],
    "rendeu": [
        "retorno",
        "rentabilidade",
        "investimento",
        "aplicacao",
        "rendimento",
        "quanto rende",
        "renda fixa",
        "tesouro direto",
        "titulo publico",
        "ouro",
    ],
    "ouro": ["metal precioso", "reserva de valor", "onca"],
    "tesouro prefixado": ["ltn", "renda fixa", "titulo publico", "prefixado"],
    "moeda contra o dolar": [
        "cambio no ano",
        "desvalorizacao",
        "valorizacao da moeda",
        "moedas emergentes",
        "real contra o dolar",
    ],
    "juro de 10 anos": ["juro longo", "titulo de 10 anos", "treasury", "taxa longa"],
    "inflacao em 12 meses": ["inflacao mensal", "inflacao de outros paises"],
    "por uso": [
        "bens de capital",
        "maquinas importadas",
        "insumos importados",
        "bens de consumo importados",
        "cgce",
    ],
    "servicos com o exterior": [
        "viagens",
        "turismo",
        "fretes",
        "royalties",
        "aluguel de equipamentos",
        "software",
        "balanca de servicos",
    ],
    "setor a setor": [
        "caged por setor",
        "vagas por setor",
        "emprego na industria",
        "emprego no comercio",
        "emprego nos servicos",
    ],
    "pib": ["crescimento", "atividade", "economia", "produto interno bruto", "recessao"],
    "ibc-br": ["previa do pib", "atividade", "pib mensal"],
    "atividade": ["pib", "crescimento", "producao", "economia"],
    "demanda privada": [
        "consumo e investimento",
        "gasto privado",
        "final sales",
        "demanda interna",
    ],
    "oferta": ["agropecuaria", "agro", "setores do pib", "industria e servicos"],
    "taxa de investimento": ["fbcf", "formacao bruta de capital", "investimento produtivo"],
    "taxa de poupanca": ["poupanca do pais", "poupanca nacional", "saving rate", "poupanca bruta"],
    "industria": ["producao industrial", "fabricas", "pim"],
    "varejo": ["comercio", "vendas", "consumo", "lojas", "pmc"],
    "servicos": ["pms", "setor de servicos"],
    "desocupacao": ["desemprego", "emprego", "pnad", "taxa de desemprego", "mercado de trabalho"],
    "ocupad": ["emprego", "trabalho", "empregados"],
    "subutiliz": ["u-6", "subocupacao", "desemprego ampliado", "subemprego"],
    "informal": ["sem carteira", "bico", "trabalho informal", "conta propria"],
    "desalent": ["desistiu de procurar", "desalento"],
    "nivel de ocupacao": ["epop", "emprego sobre a populacao", "taxa de emprego"],
    "forca de trabalho": ["participacao", "pea", "populacao ativa"],
    "juro real": ["ipca+", "ntn-b", "tesouro ipca"],
    "a termo": ["5y5y", "forward", "longo prazo"],
    "imobiliari": ["casa propria", "financiamento habitacional", "hipoteca", "imoveis", "sfh"],
    "ivg-r": ["preco dos imoveis", "valor dos imoveis", "casas", "apartamentos"],
    "imoveis": ["casa propria", "preco das casas", "ivg-r"],
    "balanco de pagamentos": ["bpm6", "contas externas", "conta financeira", "renda primaria"],
    "renda primaria": ["juros e lucros remetidos", "remessa de lucros"],
    "caged": ["emprego formal", "carteira assinada", "vagas", "empregos"],
    "rendimento": ["salario", "renda", "ganho", "massa salarial"],
    "salario": ["renda", "rendimento", "salario minimo"],
    "credito": ["emprestimo", "financiamento", "banco", "concessoes"],
    "inadimplencia": ["calote", "atraso", "dividas atrasadas", "inadimplentes"],
    "spread": ["juros do banco", "custo do credito"],
    "endividamento": ["dividas das familias", "familias endividadas"],
    "divida": ["endividamento", "divida publica", "dbgg", "debito", "deve"],
    "dbgg": ["divida bruta", "divida publica", "divida do governo"],
    "imposto": ["tributo", "tributos", "impostos", "receita federal", "arrecadacao", "leao"],
    "arrecada": ["impostos", "tributos", "receita federal", "quanto o governo arrecada"],
    "carga tributaria": ["impostos", "peso dos impostos", "tributos", "quanto se paga de imposto"],
    "gasto tributario": [
        "isencao",
        "isencoes",
        "renuncia fiscal",
        "beneficio fiscal",
        "desoneracao",
    ],
    "simples nacional": ["pequenas empresas", "mei", "regime simplificado"],
    "crescimento": ["imposto e crescimento", "efeito no pib"],
    "reforma do consumo": [
        "reforma tributaria",
        "iva",
        "ibs",
        "cbs",
        "simulador de impostos",
        "cashback",
        "cesta basica",
        "aliquota",
        "imposto seletivo",
    ],
    "quanto de imposto": [
        "simulador de impostos",
        "calculadora de imposto",
        "reforma tributaria",
        "ibs",
        "cbs",
        "iva",
        "cashback",
        "imposto no preco",
        "aliquota",
    ],
    "transicao": ["reforma tributaria", "calendario da reforma", "icms", "iss", "pis", "cofins"],
    "aliquota cheia": ["aliquota padrao", "aliquota de referencia", "iva", "26,5", "28"],
    "quem paga menos": ["aliquota reduzida", "desconto", "cashback", "cesta basica", "devolucao"],
    "quem paga": ["justica tributaria", "regressivo", "progressivo", "ricos pagam", "pobres pagam"],
    "imposto de renda por faixa": ["irpf", "leao", "aliquota efetiva", "dividendos", "super ricos"],
    "imposto sobre o lucro": ["irpj", "csll", "imposto das empresas", "corporate tax"],
    "imposto por estado": ["arrecadacao por uf", "quanto cada estado paga", "pacto federativo"],
    "fpe": ["fundo de participacao", "repasses da uniao", "transferencias", "pacto federativo"],
    "fpm": ["fundo de participacao dos municipios", "repasses as prefeituras", "transferencias"],
    "retido na fonte": ["irrf", "imposto na fonte", "restituicao", "desconto no salario"],
    "seletivo": ["imposto do pecado", "cigarro", "bebida", "refrigerante", "carros", "apostas"],
    "destino": ["origem e destino", "guerra fiscal", "partilha do ibs", "estados que perdem"],
    "primario": ["deficit", "superavit", "rombo", "resultado fiscal", "contas do governo"],
    "nominal": ["deficit nominal", "juros da divida"],
    "fiscal": ["contas publicas", "governo", "gastos publicos", "orcamento"],
    "receita": ["arrecadacao", "impostos", "tributos"],
    "despesa": ["gastos", "gasto publico", "custeio"],
    "pessoal": ["folha", "servidores", "funcionalismo", "salarios do governo"],
    "icms": ["imposto estadual", "arrecadacao dos estados", "imposto"],
    "rcl": ["receita corrente liquida"],
    "nota de credito": [
        "rating",
        "grau de investimento",
        "classificacao de risco",
        "s&p",
        "moody's",
        "fitch",
        "agencia de risco",
    ],
    "estado": ["estados", "uf", "unidade da federacao", "governo estadual", "regioes"],
    "capag": [
        "capacidade de pagamento",
        "nota do tesouro",
        "nota dos estados",
        "rating dos estados",
        "garantia da uniao",
    ],
    "perto dos limites": [
        "lrf",
        "lei de responsabilidade fiscal",
        "limite prudencial",
        "estados endividados",
        "estados quebrados",
    ],
    "estados perto do limite": ["lrf", "estados endividados", "estados quebrados", "capag"],
    "acordo da divida com a uniao": [
        "regime de recuperacao fiscal",
        "rrf",
        "propag",
        "renegociacao da divida dos estados",
        "socorro aos estados",
    ],
    "capitais contra os limites": [
        "prefeituras",
        "capitais",
        "municipios",
        "contas das prefeituras",
        "divida das capitais",
    ],
    "exportacoes em % do pib": ["abertura comercial", "quanto o estado exporta", "comex"],
    "o que o estado vende ao exterior": [
        "exportacoes do estado",
        "produtos exportados",
        "destino das exportacoes",
    ],
    "piramide etaria do estado": ["idade da populacao do estado", "envelhecimento por estado"],
    "previdencia dos servidores": [
        "deficit da previdencia",
        "rpps",
        "aposentadoria dos servidores",
        "previdencia do estado",
        "militares",
    ],
    "economia por setor": ["pib por setor", "agro", "industria", "servicos", "atividades"],
    "pib por habitante": ["pib per capita", "renda per capita", "riqueza por pessoa"],
    "ibc-r": ["atividade regional", "previa do pib", "pib do estado agora"],
    "peso no pib": ["participacao no pib", "tamanho da economia"],
    "inflacao na capital": ["ipca regional", "inflacao por cidade", "inflacao por estado"],
    "exportacoes por habitante": ["exportacoes por estado", "comex", "quem mais exporta"],
    "credito por habitante": ["credito por estado", "emprestimos por estado"],
    "concentracao do pib": ["gini", "desigualdade entre municipios"],
    "renda media do trabalho": ["salario medio", "salario por estado", "rendimento por estado"],
    "exporta": ["exportacoes", "vendas ao exterior", "comercio exterior", "balanca comercial"],
    "importa": ["importacoes", "compras do exterior", "comercio exterior", "balanca comercial"],
    "balanca": ["comercio exterior", "exportacoes", "importacoes", "saldo comercial"],
    "o que vende e compra": [
        "pauta exportadora",
        "setor exportador",
        "maior exportacao",
        "dependencia de commodities",
        "agronegocio",
        "agro",
        "industria",
        "manufaturados",
    ],
    "produtos que o brasil": [
        "soja",
        "petroleo",
        "minerio de ferro",
        "cafe",
        "carne",
        "acucar",
        "celulose",
        "adubo",
        "fertilizante",
        "diesel",
        "remedio",
    ],
    "negocia": [
        "parceiros comerciais",
        "china",
        "estados unidos",
        "eua",
        "argentina",
        "uniao europeia",
        "destino das exportacoes",
        "de onde vem",
        "tarifa",
    ],
    "transac": ["transacoes correntes", "conta corrente", "deficit externo", "setor externo"],
    "reservas": ["reservas internacionais", "dolares do banco central", "colchao"],
    "investimento direto": ["idp", "ied", "investimento estrangeiro", "capital estrangeiro"],
    "focus": ["previsao", "projecao", "expectativa", "mercado espera", "consenso", "boletim focus"],
    "previs": ["projecao", "expectativa", "futuro", "focus", "o que vem"],
    "simul": ["simulador", "cenario", "e se"],
    "efeito da selic": [
        "impacto da selic",
        "transmissao da politica monetaria",
        "se a selic cair",
        "se o juro cair",
        "corte de juros",
        "queda dos juros",
        "simulador da selic",
        "simulador de juros",
        "e se",
        "cenario",
        "repasse cambial",
    ],
    "e se a selic": [
        "simulador",
        "cenario",
        "impacto da selic",
        "corte de juros",
        "juro cair",
        "faixa de erro",
        "margem de erro",
        "incerteza",
    ],
    "ciclo de": ["ciclos da selic", "historico do copom", "aperto monetario", "afrouxamento"],
    "risco": ["perigo", "crise", "risco pais", "risco brasil", "vulnerabilidade", "alerta"],
    "alerta": ["sinal de alerta", "risco", "termometro", "indicadores de alerta"],
    "estabiliza": ["sustentabilidade da divida", "calote", "divida explode", "trajetoria"],
    "leque": ["trajetoria da divida", "cenarios", "probabilidade", "divida vai subir"],
    "sorteios": ["probabilidade", "chance", "monte carlo", "trajetoria da divida"],
    "se acontecesse de novo": ["teste de estresse", "stress", "crise", "choque", "2008"],
    "se cada crise": ["teste de estresse", "stress", "choque", "cenario de crise"],
    "volatilidade": ["oscilacao", "nervosismo", "turbulencia", "risco de mercado"],
    "brasil menos eua": [
        "juro americano",
        "estados unidos",
        "diferencial de juros",
        "premio de risco",
        "tips",
    ],
    "liquidez": ["caixa dos bancos", "corrida bancaria", "saques", "lcr"],
    "hiato de credito": ["credito demais", "bolha de credito", "credito sobre o pib"],
    "esperada para 12": ["expectativa de inflacao", "desancoragem", "focus", "expectativas"],
    "distancia do pico": ["queda da bolsa", "drawdown", "tombo"],
    "cambio real": ["real caro", "real barato", "valorizado", "desvalorizado"],
    "reservatorios": ["energia", "apagao", "racionamento", "hidreletricas", "seca hidrica"],
    "juro que a divida paga": ["custo da divida", "taxa implicita", "juros sobre a divida"],
    "juros pagos": ["custo da divida", "juros sobre a divida", "quanto o governo paga de juros"],
    "juro medio": ["taxa implicita", "custo da divida", "juro que a divida paga"],
    "juros sobre a receita": [
        "peso dos juros",
        "juros sobre arrecadacao",
        "interest to revenue",
        "quanto da receita vai para juros",
    ],
    "vence em": ["rolagem", "rolar a divida", "vencimentos", "refinanciamento", "curto prazo"],
    "quando a divida": ["vencimentos", "prazo da divida", "rolagem", "cronograma"],
    "acoes": ["justica", "processos", "precatorios", "passivos contingentes", "stf"],
    "sentencas": ["precatorios", "rpv", "justica", "decisoes judiciais"],
    "riscos fiscais": ["passivos contingentes", "garantias", "anexo de riscos fiscais", "ldo"],
    "governanca": ["corrupcao", "estado de direito", "instituicoes", "banco mundial", "wgi"],
    "ate 2100": ["projecao atuarial", "futuro da previdencia", "deficit da previdencia"],
    "mundo": ["paises", "exterior", "internacional", "comparacao internacional", "fmi"],
    "pais": ["paises", "mundo", "exterior", "internacional"],
    "emergentes": ["paises emergentes", "brics"],
    "per capita": ["por habitante", "por pessoa"],
    "demografia": ["populacao", "envelhecimento", "censo", "idosos", "habitantes"],
    "populacao": ["habitantes", "demografia", "censo", "quantos somos", "projecao do ibge"],
    "piramide": ["piramide etaria", "idades", "faixa etaria", "estrutura etaria"],
    "idosos": ["envelhecimento", "terceira idade", "velhice", "aposentados", "65 anos"],
    "para cada 100": ["razao de dependencia", "dependentes", "bonus demografico"],
    "15 a 64": ["idade de trabalhar", "idade ativa", "pia", "bonus demografico"],
    "filhos por mulher": ["fecundidade", "natalidade", "taxa de fecundidade", "bebes"],
    "nascimentos": ["natalidade", "bebes", "mortes", "obitos"],
    "esperanca de vida": ["expectativa de vida", "longevidade", "quanto se vive"],
    "idade mediana": ["idade media", "envelhecimento"],
    "inss": ["previdencia", "aposentadoria", "rgps", "deficit da previdencia", "reforma"],
    "produtividade": ["pib por trabalhador", "eficiencia", "produto por ocupado"],
    "por pessoa ocupada": ["produtividade", "pib por trabalhador"],
    "crescimento do pib": [
        "de onde veio o crescimento",
        "produtividade",
        "emprego",
        "pib estadual",
        "pib dos estados",
        "pib por estado",
        "pib regional",
        "contas regionais",
        "economia dos estados",
    ],
    "pobreza": ["pobres", "miseria", "linha de pobreza", "condicoes de vida", "vulnerabilidade"],
    "fome": ["inseguranca alimentar", "mapa da fome", "comida", "desnutricao", "passar fome"],
    "saneamento": ["esgoto", "agua encanada", "saneamento basico", "lixo", "coleta de lixo"],
    "esgoto": ["saneamento", "saneamento basico", "fossa", "rede de esgoto", "sinisa", "snis"],
    "tratado": ["tratamento de esgoto", "esgoto tratado", "estacao de tratamento"],
    "servidores": [
        "funcionalismo",
        "funcionario publico",
        "previdencia dos servidores",
        "aposentadoria do servidor",
        "rpps",
    ],
    "militares": ["forcas armadas", "previdencia dos militares", "pensao militar", "reformados"],
    "regra propria": [
        "regime especifico",
        "regimes especificos",
        "regime diferenciado",
        "bancos",
        "combustiveis",
        "plano de saude",
        "aluguel",
        "restaurantes",
    ],
    "ir das pessoas": ["irpf", "imposto de renda da pessoa fisica", "imposto sobre a renda"],
    "o topo de quem declara": ["os mais ricos", "super ricos", "concentracao no topo"],
    "agua": ["agua encanada", "abastecimento de agua", "saneamento"],
    "bolsa familia": ["programa social", "auxilio", "transferencia de renda", "bpc", "cadunico"],
    "internet": ["inclusao digital", "banda larga", "acesso a internet"],
    "lenha": ["fogao a lenha", "gas de cozinha", "botijao", "carvao"],
    "mortalidade infantil": ["mortes de bebes", "saude infantil", "obitos infantis"],
    "desigualdade": [
        "concentracao de renda",
        "distribuicao de renda",
        "ricos e pobres",
        "abismo social",
        "injustica social",
    ],
    "gini": ["indice de gini", "coeficiente de gini", "desigualdade de renda"],
    "10 % mais ricos": [
        "os mais ricos",
        "elite",
        "topo da piramide",
        "1% mais rico",
        "super-ricos",
    ],
    "40 % mais pobres": ["os mais pobres", "base da piramide", "baixa renda"],
    "dividendos": ["lucros e dividendos", "super-ricos", "taxacao dos ricos", "imposto dos ricos"],
    "mulheres": ["diferenca salarial", "genero", "desigualdade de genero", "salario das mulheres"],
    "pretos": ["negros", "racismo", "desigualdade racial", "cor ou raca"],
    "pardos": ["negros", "desigualdade racial", "cor ou raca"],
    "analfabetismo": ["analfabetos", "ler e escrever", "educacao", "alfabetizacao"],
    "escolaridade": ["educacao", "diploma", "faculdade", "ensino superior", "anos de estudo"],
    "anos de estudo": ["escolaridade", "educacao", "escola"],
    "aluguel": ["moradia", "casa propria", "habitacao", "deficit habitacional", "inquilinos"],
    "patrimonio": ["riqueza", "bens e direitos", "fortuna", "super-ricos", "ricos"],
    "do pe ao topo": ["centis", "centil", "percentil", "0,1% mais rico", "1% mais rico"],
    "onu": ["nacoes unidas", "world population prospects", "projecao da onu"],
    "por hora": ["produtividade por hora", "horas trabalhadas", "hora de trabalho"],
    "idosos na populacao": ["envelhecimento no mundo", "japao", "china", "paises ricos"],
    # O que alguém procura quando o preço de algo sobe: o grupo do IPCA em que o item mora
    # (15/11/2026: "gasolina", "aluguel", "conta de luz" não achavam nada).
    "ipca por grupo": [
        "alimentos",
        "comida",
        "supermercado",
        "gasolina",
        "combustivel",
        "passagem",
        "aluguel",
        "conta de luz",
        "energia eletrica",
        "condominio",
        "remedio",
        "plano de saude",
        "mensalidade",
        "escola",
        "roupa",
        "celular",
        "internet",
    ],
    "glossario": ["dicionario", "definicoes", "termos", "siglas", "significado", "vocabulario"],
    # Revisão das telas (15/11/2026): o juro de cada modalidade e o salário mínimo.
    "cartao rotativo": ["cartao de credito", "juros do cartao", "fatura", "cheque especial"],
    "por modalidade": [
        "cartao de credito",
        "rotativo",
        "cheque especial",
        "consignado",
        "credito pessoal",
        "emprestimo",
        "juros do emprestimo",
    ],
    "salario minimo": ["piso nacional", "minimo", "decreto do salario minimo"],
    "alimentacao no domicilio": ["comida", "alimentos", "supermercado", "mercado", "feira"],
}


# A página traduzida (traducao.ts) busca no mesmo índice: quem lê em inglês, espanhol ou
# francês procura com as palavras da própria língua (Caio, 14/11/2026: "arrume a busca").
# Termo em português, sem acento, como em SINONIMOS → as palavras nas outras línguas, também
# sem acento e em minúsculas.
OUTRAS_LINGUAS: dict[str, list[str]] = {
    # assuntos e partes
    "o que vende e compra": [
        "exports by sector",
        "commodities",
        "exportaciones por sector",
        "materias primas",
        "exportations par secteur",
        "matieres premieres",
    ],
    "produtos que o brasil": [
        "main exports",
        "soybeans",
        "crude oil",
        "iron ore",
        "principales exportaciones",
        "soja",
        "principales exportations",
    ],
    "negocia": [
        "trading partners",
        "socios comerciales",
        "partenaires commerciaux",
        "china",
        "chine",
    ],
    "reforma do consumo": [
        "tax reform",
        "vat",
        "consumption tax",
        "sales tax",
        "reforma tributaria",
        "impuesto al consumo",
        "reforme fiscale",
        "tva",
    ],
    "quanto de imposto": ["tax calculator", "vat calculator", "calculadora de impuestos"],
    "atividade": ["economic activity", "economy", "actividad economica", "economia", "activite"],
    "pib": [
        "gdp",
        "gross domestic product",
        "growth",
        "output",
        "producto interno bruto",
        "crecimiento",
        "croissance",
        "produit interieur brut",
    ],
    "ibc-br": ["monthly gdp", "economic activity index", "indice de actividad"],
    "industria": [
        "industry",
        "industrial production",
        "manufacturing",
        "produccion industrial",
        "production industrielle",
    ],
    "varejo": [
        "retail",
        "retail sales",
        "ventas minoristas",
        "comercio minorista",
        "commerce de detail",
    ],
    "servicos": ["services", "servicios"],
    "investimento": ["investment", "inversion", "fixed capital"],
    "poupanca": ["savings", "saving", "ahorro", "epargne"],
    "confianca": ["confidence", "sentiment", "confianza"],
    "capacidade": ["capacity utilization", "capacidad instalada", "capacite"],
    "trabalho": ["labor", "labour", "jobs", "employment", "empleo", "trabajo", "emploi", "travail"],
    "desocupacao": ["unemployment", "jobless", "unemployment rate", "desempleo", "paro", "chomage"],
    "desemprego": ["unemployment", "desempleo", "chomage"],
    "subutiliz": ["underemployment", "subempleo", "sous-emploi"],
    "informal": ["informality", "informal jobs", "informalidad", "travail informel"],
    "desalent": ["discouraged workers", "desalentados", "decourages"],
    "renda": ["income", "wages", "earnings", "ingreso", "salarios", "revenu", "salaires"],
    "rendimento": ["income", "wages", "earnings", "ingreso", "revenu"],
    "caged": ["formal jobs", "payrolls", "job creation", "empleo formal"],
    "inflacao": ["inflation", "consumer prices", "cpi", "prices", "inflacion", "precios", "prix"],
    "ipca": [
        "cpi",
        "consumer price index",
        "inflation",
        "indice de precios",
        "prix a la consommation",
    ],
    "nucleo": [
        "core inflation",
        "underlying inflation",
        "inflacion subyacente",
        "inflation sous-jacente",
    ],
    "meta": ["target", "inflation target", "objetivo", "meta de inflacion", "cible"],
    "preco": ["prices", "precios", "prix"],
    "igp": ["wholesale prices", "general price index", "precios mayoristas"],
    "juro": [
        "interest rate",
        "interest rates",
        "rates",
        "tasa de interes",
        "tipos de interes",
        "taux d'interet",
    ],
    "selic": [
        "policy rate",
        "central bank rate",
        "interest rate",
        "tasa de politica monetaria",
        "taux directeur",
    ],
    "copom": [
        "monetary policy committee",
        "central bank meeting",
        "comite de politica monetaria",
        "comite de politique monetaire",
    ],
    "juro real": ["real interest rate", "tasa real", "taux reel"],
    "titulos": [
        "bonds",
        "treasury bonds",
        "government bonds",
        "yield curve",
        "bonos",
        "obligations",
    ],
    "curva": ["yield curve", "term structure", "curva de rendimiento", "courbe des taux"],
    "implicita": [
        "breakeven inflation",
        "inflation expectations",
        "inflacion implicita",
        "point mort d'inflation",
    ],
    "credito": ["credit", "loans", "lending", "prestamos", "creditos", "prets"],
    "inadimplencia": [
        "defaults",
        "non-performing loans",
        "npl",
        "delinquency",
        "morosidad",
        "impayes",
    ],
    "spread": ["lending spread", "diferencial de tasas"],
    "familias": ["households", "household debt", "hogares", "deuda de los hogares", "menages"],
    "endividamento": ["household debt", "indebtedness", "endeudamiento", "endettement"],
    "comprometimento": [
        "debt service",
        "debt burden",
        "servicio de la deuda",
        "service de la dette",
    ],
    "imove": [
        "housing",
        "real estate",
        "house prices",
        "mortgage",
        "vivienda",
        "inmuebles",
        "hipoteca",
        "immobilier",
    ],
    "mercados": ["markets", "financial markets", "mercados financieros", "marches"],
    "bolsa": [
        "stock market",
        "stocks",
        "equities",
        "mercado de valores",
        "acciones",
        "bourse",
        "actions",
    ],
    "ibovespa": ["stock index", "brazil stocks", "indice bursatil", "indice boursier"],
    "cambio": ["exchange rate", "currency", "fx", "tipo de cambio", "taux de change"],
    "dolar": ["dollar", "usd", "exchange rate", "dolar", "dollar americain"],
    "euro": ["euro"],
    "rendeu": ["returns", "performance", "rentabilidad", "rendement"],
    "setor externo": [
        "external sector",
        "balance of payments",
        "sector externo",
        "balanza de pagos",
        "balance des paiements",
    ],
    "conta corrente": ["current account", "cuenta corriente", "compte courant"],
    "transac": ["current account", "cuenta corriente", "compte courant"],
    "comercio exterior": [
        "trade",
        "foreign trade",
        "exports",
        "imports",
        "comercio exterior",
        "commerce exterieur",
    ],
    "exporta": ["exports", "exportaciones", "exportations"],
    "importa": ["imports", "importaciones", "importations"],
    "balanca": ["trade balance", "balanza comercial", "balance commerciale"],
    "investimento direto": [
        "fdi",
        "foreign direct investment",
        "inversion extranjera directa",
        "investissement direct etranger",
    ],
    "reservas": [
        "reserves",
        "international reserves",
        "fx reserves",
        "reservas internacionales",
        "reserves de change",
    ],
    "cambio real": ["real exchange rate", "reer", "tipo de cambio real", "taux de change reel"],
    "contas publicas": [
        "public finances",
        "fiscal",
        "budget",
        "finanzas publicas",
        "presupuesto",
        "finances publiques",
    ],
    "fiscal": ["fiscal", "budget", "fiscal policy", "politica fiscal", "politique budgetaire"],
    "divida": [
        "debt",
        "public debt",
        "government debt",
        "deuda",
        "deuda publica",
        "dette",
        "dette publique",
    ],
    "rolagem": [
        "debt rollover",
        "maturity",
        "interest to revenue",
        "refinanciamiento",
        "vencimientos",
        "refinancement",
        "echeances",
    ],
    "juridicos": [
        "contingent liabilities",
        "fiscal risks",
        "court rulings",
        "governance",
        "pasivos contingentes",
        "riesgos fiscales",
        "gobernanza",
        "passifs eventuels",
        "risques budgetaires",
        "gouvernance",
    ],
    "ate 2100": [
        "pension projections",
        "social security deficit",
        "proyecciones de pensiones",
        "projections des retraites",
    ],
    "primario": [
        "primary balance",
        "primary deficit",
        "primary surplus",
        "fiscal balance",
        "resultado primario",
        "deficit primario",
        "solde primaire",
    ],
    "nominal": ["overall balance", "fiscal deficit", "deficit fiscal", "deficit public"],
    "receita": ["revenue", "tax revenue", "taxes", "ingresos", "impuestos", "recettes", "impots"],
    "despesa": ["spending", "expenditure", "gasto publico", "depenses"],
    "previdencia": ["pensions", "social security", "pensiones", "seguridad social", "retraites"],
    "inss": ["pensions", "social security", "pensiones", "retraites"],
    "estados": ["states", "brazilian states", "regions", "estados de brasil", "etats"],
    "estado": ["state", "regional government", "gobierno estatal", "etat"],
    "pessoal": [
        "payroll",
        "public wages",
        "civil servants",
        "gasto en personal",
        "masse salariale",
    ],
    "icms": ["state sales tax", "vat", "impuesto estatal"],
    "rcl": ["net current revenue", "ingreso corriente neto"],
    "demografia": [
        "demographics",
        "population",
        "aging",
        "demografia",
        "poblacion",
        "envejecimiento",
        "demographie",
        "vieillissement",
    ],
    "populacao": ["population", "poblacion"],
    "desigualdade": [
        "inequality",
        "income inequality",
        "income distribution",
        "desigualdad",
        "distribucion del ingreso",
        "inegalites",
        "inegalite des revenus",
    ],
    "gini": ["gini index", "gini coefficient", "indice de gini", "coeficiente de gini"],
    "pobreza": ["poverty", "extreme poverty", "pobreza extrema", "pauvrete", "extreme pauvrete"],
    "fome": ["hunger", "food insecurity", "hambre", "inseguridad alimentaria", "faim"],
    "saneamento": ["sanitation", "sewage", "water supply", "saneamiento", "assainissement"],
    "mortalidade infantil": ["infant mortality", "mortalidad infantil", "mortalite infantile"],
    "idosos": [
        "elderly",
        "aging",
        "old-age dependency",
        "ancianos",
        "personas mayores",
        "personnes agees",
    ],
    "fecundidade": ["fertility", "birth rate", "fecundidad", "natalidad", "fecondite"],
    "nascimentos": ["births", "deaths", "nacimientos", "naissances"],
    "esperanca de vida": ["life expectancy", "esperanza de vida", "esperance de vie"],
    "piramide": ["population pyramid", "age pyramid", "piramide de poblacion", "pyramide des ages"],
    "produtividade": ["productivity", "labor productivity", "productividad", "productivite"],
    "mundo": [
        "world",
        "countries",
        "international comparison",
        "imf",
        "mundo",
        "paises",
        "fmi",
        "monde",
        "pays",
    ],
    "emergentes": [
        "emerging markets",
        "emerging economies",
        "mercados emergentes",
        "pays emergents",
    ],
    "previs": [
        "forecast",
        "forecasts",
        "projections",
        "outlook",
        "expectations",
        "pronostico",
        "proyecciones",
        "previsions",
    ],
    "focus": ["market expectations", "consensus", "survey", "expectativas del mercado"],
    "simul": ["simulator", "scenario", "what if", "simulador", "escenario", "simulateur"],
    "risco": ["risk", "risks", "riesgo", "riesgos", "risque"],
    "alerta": ["warning", "early warning", "alert", "dashboard", "alerta temprana", "alerte"],
    "sustenta": ["debt sustainability", "sostenibilidad de la deuda", "soutenabilite"],
    "estresse": ["stress test", "crisis scenario", "prueba de estres", "test de resistance"],
    "nota de credito": [
        "credit rating",
        "rating",
        "sovereign rating",
        "investment grade",
        "calificacion crediticia",
        "grado de inversion",
        "notation",
    ],
    "bancos": ["banks", "banking", "capital adequacy", "bancos", "banques"],
    "basileia": ["basel", "capital ratio", "basilea", "bale"],
    "energia": ["energy", "electricity", "hydropower", "energia", "energie"],
    "reservatorios": ["reservoirs", "hydro reservoirs", "embalses", "reservoirs"],
    "volatilidade": ["volatility", "volatilidad", "volatilite"],
    "hiato de credito": ["credit gap", "credit-to-gdp gap", "brecha de credito"],
    "servico da divida": ["debt service ratio", "dsr", "servicio de la deuda"],
    "imposto": ["taxes", "tax", "taxation", "impuestos", "tributos", "impots", "fiscalite"],
}

# Os assuntos em chinês (simplificado e tradicional), japonês e árabe (15/11/2026), para quem
# lê a página traduzida (traducao.ts) e busca na própria escrita. Só os nomes comuns de cada
# assunto, como aparecem em jornal e em site de banco central; o árabe vai com o artigo
# ("التضخم"), porque a busca acha o termo também dentro da palavra ("تضخم" casa). Chinês e
# japonês não separam palavras: o navegador procura o termo dentro do que foi digitado
# ("巴西通货膨胀" acha "通货膨胀").
OUTRAS_ESCRITAS: dict[str, list[str]] = {
    "atividade": ["经济活动", "經濟活動", "景気", "経済活動", "النشاط الاقتصادي"],
    "pib": ["国内生产总值", "國內生產毛額", "國內生產總值", "国内総生産", "الناتج المحلي الإجمالي"],
    "trabalho": [
        "就业",
        "就業",
        "劳动力市场",
        "勞動市場",
        "雇用",
        "労働市場",
        "سوق العمل",
        "التوظيف",
    ],
    "desocupacao": ["失业率", "失業率", "失业", "失業", "البطالة", "معدل البطالة"],
    "inflacao": [
        "通货膨胀",
        "通胀",
        "通貨膨脹",
        "通膨",
        "物价",
        "物價",
        "インフレ",
        "物価",
        "التضخم",
        "الأسعار",
    ],
    "ipca": ["消费者物价指数", "消費者物價指數", "消費者物価指数", "مؤشر أسعار المستهلك"],
    "juro": ["利率", "金利", "سعر الفائدة", "أسعار الفائدة"],
    "selic": ["基准利率", "基準利率", "政策金利", "سعر الفائدة الأساسي"],
    "copom": ["货币政策委员会", "貨幣政策委員會", "金融政策委員会", "لجنة السياسة النقدية"],
    "credito": ["信贷", "信貸", "贷款", "貸款", "融資", "貸出", "الائتمان", "القروض"],
    "mercados": ["金融市场", "金融市場", "الأسواق المالية"],
    "bolsa": ["股市", "股票", "株式市場", "株価", "البورصة", "سوق الأسهم"],
    "cambio": ["汇率", "匯率", "為替", "سعر الصرف"],
    "dolar": ["美元", "ドル", "الدولار"],
    "setor externo": ["国际收支", "國際收支", "国際収支", "القطاع الخارجي", "ميزان المدفوعات"],
    "exporta": ["出口", "輸出", "الصادرات"],
    "importa": ["进口", "進口", "輸入", "الواردات"],
    "contas publicas": ["公共财政", "公共財政", "财政", "財政", "المالية العامة"],
    "divida": ["公共债务", "公共債務", "政府債務", "الدين العام"],
    "imposto": ["税收", "稅收", "税金", "税制", "الضرائب"],
    "reforma do consumo": ["税制改革", "稅制改革", "增值税", "增值稅", "消費税", "الإصلاح الضريبي"],
    "estados": ["巴西各州", "州", "الولايات"],
    "demografia": ["人口", "人口结构", "人口結構", "人口動態", "السكان"],
    "pobreza": ["贫困", "貧困", "الفقر"],
    "desigualdade": ["不平等", "格差", "عدم المساواة"],
    "mundo": ["世界", "国际比较", "國際比較", "国際比較", "العالم"],
    "previs": ["预测", "預測", "予測", "見通し", "التوقعات"],
    "focus": ["市场预期", "市場預期", "市場予想", "توقعات السوق"],
    "risco": ["风险", "風險", "リスク", "المخاطر"],
}


class Item(BaseModel):
    t: str
    """O que aparece no resultado (título do gráfico, rótulo do número...)."""
    o: str
    """Onde está: o nome do assunto, e o tipo."""
    h: str
    """O endereço: `#assunto` ou `#assunto/alvo` (o id do elemento na página)."""
    p: str = ""
    """As palavras a mais da busca (sinônimos, sem acento, em minúsculas)."""
    lt: str = ""
    """O título em outras línguas (OUTRAS_LINGUAS só do título): vale mais que `p`, para
    "unemployment" trazer a Desocupação antes do assunto que só a cita no resumo."""
    n: str = ""
    """Os números que a peça mostra (o do cartão, os da tabela), separados por espaço, no
    formato de `numero`: "13,75" acha o cartão da Selic."""


# Os acentos que a busca ignora: os do alfabeto latino e as vogais curtas do árabe. Os sinais
# do japonês (o "゛" de "デ") ficam: tirá-los trocaria uma letra por outra.
_ACENTOS = re.compile("[\u0300-\u036f\u064b-\u065f\u0670]")


def normalizar(texto: str) -> str:
    sem_acento = _ACENTOS.sub("", unicodedata.normalize("NFD", texto))
    return unicodedata.normalize("NFC", sem_acento).lower()


def numero(valor: float, casas: int) -> str:
    """O número como a busca o compara: com as casas da tela, vírgula decimal e sem o ponto
    de milhar ("13,75", "128450", "-2,1"). O navegador escreve o que se digita do mesmo jeito."""
    texto = f"{abs(valor):.{max(0, casas)}f}".replace(".", ",")
    zero = not texto.strip("0,")
    return texto if valor >= 0 or zero else f"-{texto}"


# Uma tabela grande (os estados, os países) não precisa pôr todos os números no índice.
NUMEROS_POR_TABELA = 400


def _numeros_da_tabela(t: dict[str, Any]) -> str:
    vistos: dict[str, None] = {}
    for linha in t.get("linhas", []):
        casas = int(linha.get("casas", 1))
        for v in linha.get("valores", []):
            if isinstance(v, int | float) and not isinstance(v, bool):
                vistos.setdefault(numero(v, casas))
            if len(vistos) >= NUMEROS_POR_TABELA:
                return " ".join(vistos)
    return " ".join(vistos)


def _palavras(dicionarios: tuple[dict[str, list[str]], ...], base: str) -> list[str]:
    """As palavras dos termos que aparecem em `base`, normalizadas (o árabe é escrito certo
    no dicionário, com a hamza, e vai ao índice como o navegador compara), sem repetir."""
    achadas: list[str] = []
    for dicionario in dicionarios:
        for termo, palavras in dicionario.items():
            if termo in base:
                for p in map(normalizar, palavras):
                    if p not in achadas:
                        achadas.append(p)
    return achadas


def sinonimos_de(texto: str) -> str:
    """Os sinônimos em português e as palavras nas outras línguas e escritas do texto."""
    base = normalizar(texto)
    todas = _palavras((SINONIMOS, OUTRAS_LINGUAS, OUTRAS_ESCRITAS), base)
    return " ".join(p for p in todas if p not in base)


def _no_titulo(titulo: str) -> str:
    return " ".join(_palavras((OUTRAS_LINGUAS, OUTRAS_ESCRITAS), normalizar(titulo)))


def _item(t: str, o: str, h: str, extra: str = "", numeros: str = "", linhas: str = "") -> Item:
    """`linhas`: os nomes das linhas de uma tabela, que vão ao índice como estão ("Soja em
    grão", "Transportes") e trazem os sinônimos deles."""
    palavras = " ".join(x for x in (normalizar(linhas), sinonimos_de(f"{t} {extra} {linhas}")) if x)
    return Item(t=t, o=o, h=h, p=palavras, lt=_no_titulo(t), n=numeros)


# As tabelas dos 27 estados e dos 22 países já têm cada nome no índice (`ufs`, `paises`): as linhas
# entram só nas tabelas curtas (grupos do IPCA, produtos, parceiros, setores).
LINHAS_POR_TABELA = 20


def _linhas_da_tabela(t: dict[str, Any]) -> str:
    linhas = t.get("linhas", [])
    if len(linhas) > LINHAS_POR_TABELA:
        return ""
    return " ".join(str(linha.get("rotulo", "")) for linha in linhas)


def montar(saida: Path) -> list[Item]:
    painel = json.loads((saida / "painel.json").read_text(encoding="utf-8"))
    itens: list[Item] = []
    for s in painel["secoes"]:
        if s["id"] == "resumo" or not (saida / s["arquivo"]).exists():
            continue
        dados = json.loads((saida / s["arquivo"]).read_text(encoding="utf-8"))
        nome, h = s["titulo"], f"#{s['id']}"
        itens.append(_item(nome, "Assunto", h, s.get("resumo", "")))
        # Em que parte do assunto cada peça mora: "Inflação › Núcleos e o ritmo".
        onde: dict[str, str] = {}
        for sub in dados.get("subcategorias", []):
            itens.append(_item(sub["titulo"], f"{nome} · parte", f"{h}/{sub['id']}", sub["resumo"]))
            for tipo, prefixo in (("cartoes", "c"), ("graficos", "g"), ("tabelas", "t")):
                for i in sub.get(tipo, []):
                    onde[f"{prefixo}-{i}"] = f"{nome} › {sub['titulo']}"
        for c in dados.get("cartoes", []):
            alvo = f"c-{c['id']}"
            local = onde.get(alvo, nome)
            valor = c.get("valor")
            n = (
                numero(valor, int(c.get("casas", 1)))
                if isinstance(valor, int | float) and not c.get("texto")
                else ""
            )
            extra = f"{c['detalhe']} {c.get('texto', '')}"
            itens.append(_item(c["rotulo"], f"{local} · número", f"{h}/{alvo}", extra, n))
        for g in dados.get("graficos", []):
            alvo = f"g-{g['id']}"
            itens.append(_item(g["titulo"], f"{onde.get(alvo, nome)} · gráfico", f"{h}/{alvo}"))
        for t in dados.get("tabelas", []):
            alvo = f"t-{t['id']}"
            local = f"{onde.get(alvo, nome)} · tabela"
            itens.append(
                _item(
                    t["titulo"],
                    local,
                    f"{h}/{alvo}",
                    numeros=_numeros_da_tabela(t),
                    linhas=_linhas_da_tabela(t),
                )
            )
        if dados.get("simulador_selic"):
            parte = next(
                (
                    sub
                    for sub in dados.get("subcategorias", [])
                    if "simulador-selic" in sub.get("extras", [])
                ),
                None,
            )
            alvo = f"{h}/{parte['id']}" if parte else h
            local = f"{nome} › {parte['titulo']}" if parte else nome
            itens.append(_item("E se a Selic mudar?", f"{local} · simulador", alvo))
        if dados.get("simulador_reforma"):
            parte = next(
                (
                    sub
                    for sub in dados.get("subcategorias", [])
                    if "simulador-reforma" in sub.get("extras", [])
                ),
                None,
            )
            alvo = f"{h}/{parte['id']}" if parte else h
            local = f"{nome} › {parte['titulo']}" if parte else nome
            itens.append(_item("Quanto de imposto vai numa compra?", f"{local} · simulador", alvo))
        if dados.get("alertas"):
            # O painel fica guardado e é montado no clique: o resultado leva a ele.
            itens.append(_item("Painel de alerta", f"{nome} · painel", f"{h}/t-alertas"))
            for a in dados["alertas"]:
                alvo = f"{h}/a-{a['id']}"
                itens.append(_item(a["nome"], f"{nome} · alerta", alvo, a["grupo"]))
        for m in dados.get("metricas", []):
            itens.append(_item(m["nome"], f"{nome} · comparação", f"{h}/m-{m['id']}"))
        for pais in dados.get("paises", []):
            itens.append(_item(pais["nome"], f"{nome} · país", f"{h}/p-{pais['iso3']}"))
        for uf in dados.get("ufs", []):
            itens.append(_item(uf["nome"], f"{nome} · {uf['sigla']}", f"{h}/uf-{uf['sigla']}"))
        if dados.get("capitais"):
            local = f"{nome} › Perto dos limites"
            itens.append(_item("As capitais contra os limites da lei", local, f"{h}/limites"))
        if dados.get("arquivo_contas"):
            local = f"{nome} › Um estado por dentro"
            itens.append(_item("O que o estado vende ao exterior", local, f"{h}/estado"))
            itens.append(_item("Pirâmide etária do estado", local, f"{h}/estado"))
    # A página com todas as palavras (revisão das telas, 15/11/2026).
    itens.append(_item("Glossário", "Consulta · todas as palavras do painel", "#glossario"))
    return itens


def gravar(saida: Path) -> int:
    itens = montar(saida)
    texto = json.dumps([i.model_dump(exclude_defaults=True) for i in itens], ensure_ascii=False)
    (saida / "busca.json").write_text(texto, encoding="utf-8")
    return len(itens)
