"""O índice da busca do site (`busca.json`): cada assunto, número, gráfico e tabela, as métricas
de estados e de países, e os nomes dos estados, com os sinônimos de cada um.

Lido dos JSONs já gravados (os da rodada e os que sobraram da anterior), para que a busca
ache tudo o que o site mostra. Os sinônimos ficam aqui, num dicionário só: quem procura
"desemprego" acha a desocupação; "carestia", o IPCA; "calote", a inadimplência.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

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
    ],
    "pib": ["crescimento", "atividade", "economia", "produto interno bruto", "recessao"],
    "ibc-br": ["previa do pib", "atividade", "pib mensal"],
    "atividade": ["pib", "crescimento", "producao", "economia"],
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
    "crescimento": ["imposto e crescimento", "multiplicador", "efeito no pib"],
    "reforma do consumo": ["reforma tributaria", "iva", "ibs", "cbs"],
    "quem paga": ["justica tributaria", "regressivo", "progressivo", "ricos pagam", "pobres pagam"],
    "imposto de renda por faixa": ["irpf", "leao", "aliquota efetiva", "dividendos", "super ricos"],
    "imposto sobre o lucro": ["irpj", "csll", "imposto das empresas", "corporate tax"],
    "imposto por estado": ["arrecadacao por uf", "quanto cada estado paga", "pacto federativo"],
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
    "exporta": ["exportacoes", "vendas ao exterior", "comercio exterior", "balanca comercial"],
    "importa": ["importacoes", "compras do exterior", "comercio exterior", "balanca comercial"],
    "balanca": ["comercio exterior", "exportacoes", "importacoes", "saldo comercial"],
    "transac": ["transacoes correntes", "conta corrente", "deficit externo", "setor externo"],
    "reservas": ["reservas internacionais", "dolares do banco central", "colchao"],
    "investimento direto": ["idp", "ied", "investimento estrangeiro", "capital estrangeiro"],
    "focus": ["previsao", "projecao", "expectativa", "mercado espera", "consenso", "boletim focus"],
    "previs": ["projecao", "expectativa", "futuro", "focus", "o que vem"],
    "simul": ["simulador", "cenario", "e se"],
    "risco": ["perigo", "crise", "risco pais", "risco brasil", "vulnerabilidade", "alerta"],
    "alerta": ["sinal de alerta", "risco", "termometro", "indicadores de alerta"],
    "estabiliza": ["sustentabilidade da divida", "calote", "divida explode", "trajetoria"],
    "leque": ["trajetoria da divida", "cenarios", "probabilidade", "divida vai subir"],
    "sorteios": ["probabilidade", "chance", "monte carlo", "trajetoria da divida"],
    "se acontecesse de novo": ["teste de estresse", "stress", "crise", "choque", "2008"],
    "se cada crise": ["teste de estresse", "stress", "choque", "cenario de crise"],
    "volatilidade": ["oscilacao", "nervosismo", "turbulencia", "risco de mercado"],
    "distancia do pico": ["queda da bolsa", "drawdown", "tombo"],
    "cambio real": ["real caro", "real barato", "valorizado", "desvalorizado"],
    "reservatorios": ["energia", "apagao", "racionamento", "hidreletricas", "seca hidrica"],
    "juro que a divida paga": ["custo da divida", "taxa implicita", "juros sobre a divida"],
    "juros pagos": ["custo da divida", "juros sobre a divida", "quanto o governo paga de juros"],
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
    "crescimento do pib": ["de onde veio o crescimento", "produtividade", "emprego"],
}


# A página traduzida (traducao.ts) busca no mesmo índice: quem lê em inglês, espanhol ou
# francês procura com as palavras da própria língua (Caio, 14/11/2026: "arrume a busca").
# Termo em português, sem acento, como em SINONIMOS → as palavras nas outras línguas, também
# sem acento e em minúsculas.
OUTRAS_LINGUAS: dict[str, list[str]] = {
    # assuntos e partes
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


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFD", texto)
    return "".join(c for c in sem_acento if unicodedata.category(c) != "Mn").lower()


def sinonimos_de(texto: str) -> str:
    """Os sinônimos em português e as palavras em inglês, espanhol e francês do texto."""
    base = normalizar(texto)
    extras: list[str] = []
    for dicionario in (SINONIMOS, OUTRAS_LINGUAS):
        for termo, palavras in dicionario.items():
            if termo in base:
                extras.extend(p for p in palavras if p not in base and p not in extras)
    return " ".join(extras)


def _no_titulo(titulo: str) -> str:
    base = normalizar(titulo)
    achadas: list[str] = []
    for termo, palavras in OUTRAS_LINGUAS.items():
        if termo in base:
            achadas.extend(p for p in palavras if p not in achadas)
    return " ".join(achadas)


def _item(t: str, o: str, h: str, extra: str = "") -> Item:
    return Item(t=t, o=o, h=h, p=sinonimos_de(f"{t} {extra}"), lt=_no_titulo(t))


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
            itens.append(_item(c["rotulo"], f"{local} · número", f"{h}/{alvo}", c["detalhe"]))
        for g in dados.get("graficos", []):
            alvo = f"g-{g['id']}"
            itens.append(_item(g["titulo"], f"{onde.get(alvo, nome)} · gráfico", f"{h}/{alvo}"))
        for t in dados.get("tabelas", []):
            alvo = f"t-{t['id']}"
            itens.append(_item(t["titulo"], f"{onde.get(alvo, nome)} · tabela", f"{h}/{alvo}"))
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
    return itens


def gravar(saida: Path) -> int:
    itens = montar(saida)
    texto = json.dumps([i.model_dump(exclude_defaults=True) for i in itens], ensure_ascii=False)
    (saida / "busca.json").write_text(texto, encoding="utf-8")
    return len(itens)
