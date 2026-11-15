"""Onde cada coisa mora: as categorias de assuntos e as subcategorias dentro de cada assunto.

Pedido do Caio (14/11/2026): *"humanos não conseguem ler muitas informações em uma página
[...] classifique melhor em categorias, crie subcategorias"*. O menu lateral e a entrada
agrupam os assuntos por categoria; cada assunto abre num resumo (quatro números, um gráfico
e a lista das partes) e cada parte abre numa tela só dela.

Aqui ficam só ids e nomes, num lugar só, para as seções não precisarem saber disso. O que
uma seção trouxer e não estiver listado aqui não some: vai para a parte "Outros", e o
builder avisa, para alguém pôr no lugar certo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from sacibras.schema import Categoria, Elo, Secao, Subcategoria

Extra = Literal["simulador", "simulador-selic", "simulador-reforma", "alertas"]

CATEGORIAS: list[Categoria] = [
    Categoria(
        id="atividade-emprego",
        titulo="Atividade e emprego",
        secoes=["atividade", "trabalho", "pobreza", "demografia"],
    ),
    Categoria(
        id="precos-juros",
        titulo="Preços, juros e crédito",
        secoes=["inflacao", "juros", "credito"],
    ),
    Categoria(
        id="mercados-exterior",
        titulo="Mercados e exterior",
        secoes=["mercados", "externo", "mundo"],
    ),
    Categoria(
        id="contas-publicas", titulo="Contas públicas", secoes=["fiscal", "impostos", "estados"]
    ),
    Categoria(id="adiante", titulo="O que vem pela frente", secoes=["previsoes", "riscos"]),
]


@dataclass(frozen=True)
class Parte:
    id: str
    titulo: str
    resumo: str
    cartoes: list[str] = field(default_factory=list)
    graficos: list[str] = field(default_factory=list)
    tabelas: list[str] = field(default_factory=list)
    extras: list[Extra] = field(default_factory=list)
    veja: list[Elo] = field(default_factory=list)


EFEITO_DA_SELIC = "#juros/efeito"
# Ids de parte não podem começar como os de peça (c-, g-, t-, m-, p-, uf-): o endereço
# "#assunto/x" é parte ou peça.
PARTES: dict[str, list[Parte]] = {
    "atividade": [
        Parte(
            "pib",
            "PIB",
            "O crescimento a cada trimestre, pela demanda, pela oferta e o gasto privado.",
            cartoes=["pib-tt", "pib-4t", "demanda-privada"],
            graficos=["pib-trimestral", "pib-demanda", "pib-oferta", "demanda-privada"],
            tabelas=["pib-componentes"],
        ),
        Parte(
            "mes-a-mes",
            "Indicadores do mês",
            "IBC-Br, indústria, varejo e serviços: o que sai antes do PIB.",
            cartoes=["ibcbr", "industria", "varejo", "servicos"],
            graficos=["ibcbr", "setores-mensais"],
        ),
        Parte(
            "investimento",
            "Investimento e poupança",
            "Quanto do PIB vira máquinas e obras, e quanto o país poupa.",
            cartoes=["taxa-investimento", "taxa-poupanca"],
            graficos=["investimento-poupanca"],
        ),
        Parte(
            "confianca",
            "Confiança e capacidade",
            "Confiança do consumidor e uso da capacidade da indústria.",
            graficos=["confianca", "uci"],
        ),
    ],
    "trabalho": [
        Parte(
            "desemprego",
            "Desemprego",
            "Desocupação, subutilização, desalento e quem procura há muito tempo.",
            cartoes=["desocupacao", "subutilizacao"],
            graficos=["desocupacao", "subutilizacao", "desalento", "procura-longa"],
        ),
        Parte(
            "renda",
            "Renda",
            "O rendimento médio e a massa de rendimento, já descontada a inflação.",
            cartoes=["rendimento", "massa"],
            graficos=["rendimento", "massa"],
        ),
        Parte(
            "quem-trabalha",
            "Quem trabalha",
            "Emprego com carteira, informalidade e participação na força de trabalho.",
            cartoes=["emprego-formal", "informalidade", "participacao", "nivel-ocupacao"],
            graficos=["emprego-formal", "informalidade", "participacao"],
            tabelas=["trabalho-detalhe"],
        ),
    ],
    "demografia": [
        Parte(
            "populacao",
            "População",
            "Quantos somos, a pirâmide etária e quem está em idade de trabalhar.",
            cartoes=["populacao", "populacao-15-64", "idade-mediana"],
            graficos=["piramide", "populacao", "crescimento-15-64"],
            tabelas=["demografia-marcos"],
        ),
        Parte(
            "nascimentos",
            "Nascimentos e vida",
            "Filhos por mulher, nascimentos, óbitos, esperança de vida e mortalidade infantil.",
            cartoes=["fecundidade", "esperanca-de-vida", "mortalidade-infantil"],
            graficos=[
                "nascimentos-obitos",
                "fecundidade",
                "esperanca-de-vida",
                "mortalidade-infantil",
            ],
        ),
        Parte(
            "envelhecimento",
            "Envelhecimento e Previdência",
            "Idosos para cada pessoa em idade de trabalhar, por estado, e o déficit do INSS.",
            cartoes=["idosos-por-100", "deficit-inss"],
            graficos=["dependencia", "idosos", "inss"],
            tabelas=["demografia-estados"],
        ),
        Parte(
            "produtividade",
            "Produtividade",
            "PIB por pessoa ocupada e de onde veio o crescimento.",
            cartoes=["produtividade"],
            graficos=["produtividade", "crescimento-decomposto"],
        ),
    ],
    "pobreza": [
        Parte(
            "linha-de-pobreza",
            "Pobreza",
            "Quantos vivem abaixo das linhas de pobreza e quantas casas recebem Bolsa Família.",
            cartoes=["pobreza", "extrema-pobreza", "bolsa-familia"],
            graficos=["pobreza", "programas-sociais"],
        ),
        Parte(
            "fome",
            "Fome",
            "Quantos moram em casas onde falta comida, e se o Brasil está no Mapa da Fome.",
            cartoes=["fome", "inseguranca-moderada-grave", "subalimentacao"],
            graficos=["fome-fao"],
            tabelas=["pobreza-fome"],
        ),
        Parte(
            "saneamento",
            "A casa: água, esgoto, luz",
            "Água, esgoto e lixo contra a meta de 2033, luz, internet e fogão a lenha.",
            cartoes=["agua", "esgoto", "lixo", "internet", "lenha"],
            graficos=["saneamento", "internet-lenha"],
            tabelas=["pobreza-saneamento"],
        ),
        Parte(
            "desigualdade",
            "Desigualdade",
            "O Gini e quem fica com quanto da renda: os mais pobres, o meio e os mais ricos.",
            cartoes=["gini", "fatia-10-ricos", "fatia-1-rico", "fatia-40-pobres", "razao-10-40"],
            graficos=["gini", "fatias", "renda-por-grupo"],
            tabelas=["pobreza-decimos"],
        ),
        Parte(
            "quem-ganha-mais",
            "Quem ganha mais",
            "O topo pelo Imposto de Renda e a renda do trabalho por sexo e cor.",
            cartoes=[
                "irpf-topo-renda",
                "irpf-topo-dividendos",
                "mulheres-homens",
                "pretos-brancos",
                "pardos-brancos",
            ],
            graficos=["diferencas", "renda-trabalho-grupos"],
            tabelas=["pobreza-irpf"],
        ),
        Parte(
            "estados-e-paises",
            "Estados e países",
            "Pobreza, fome, esgoto e água por estado, e o Gini do Brasil no mundo.",
            graficos=["gini-paises"],
            tabelas=["pobreza-estados"],
        ),
    ],
    "inflacao": [
        Parte(
            "ipca",
            "IPCA e a meta",
            "A inflação oficial em 12 meses e no mês, contra a meta.",
            cartoes=["ipca-12m", "ipca-mes"],
            graficos=["ipca-12m", "ipca-mensal"],
            veja=[
                Elo(
                    endereco=EFEITO_DA_SELIC,
                    titulo="Efeito da Selic",
                    resumo="Quanto a inflação muda com 1 ponto de Selic, nas contas do BC.",
                )
            ],
        ),
        Parte(
            "nucleos",
            "Núcleos e o ritmo",
            "A inflação sem os itens mais voláteis, em 3 e 12 meses, e a difusão.",
            cartoes=["nucleos-12m", "nucleos-3m", "difusao"],
            graficos=["nucleos-ritmo", "ipca-difusao"],
            tabelas=["ipca-medidas"],
        ),
        Parte(
            "grupos",
            "Por tipo de preço",
            "Serviços, livres, administrados e cada grupo do IPCA.",
            cartoes=["servicos-12m"],
            graficos=["ipca-aberturas"],
            tabelas=["ipca-grupos"],
        ),
        Parte(
            "outros-indices",
            "Outros índices e o Focus",
            "INPC e IGP-M ao lado do IPCA, e o que o mercado espera.",
            cartoes=["focus-ipca"],
            graficos=["outros-indices"],
        ),
    ],
    "juros": [
        Parte(
            "selic",
            "Selic e Copom",
            "A taxa básica, a efetiva e o caminho que o mercado espera.",
            cartoes=["selic-meta", "selic-efetiva", "focus-selic"],
            graficos=["selic-trajetoria", "selic-ipca"],
        ),
        Parte(
            "efeito",
            "Efeito da Selic",
            "O que muda na inflação, no dólar e na dívida quando a Selic cai ou sobe.",
            cartoes=["selic-efeito-ipca", "selic-efeito-dolar", "selic-efeito-divida"],
            graficos=["selic-ciclos-alinhados", "ipca-ciclos-alinhados"],
            tabelas=["selic-contas-bc", "selic-ciclos-corte", "selic-ciclos-alta"],
            extras=["simulador-selic"],
        ),
        Parte(
            "juro-real",
            "Juro real",
            "A Selic descontada da inflação: a que passou e a esperada.",
            cartoes=["juro-real-ex-ante", "juro-real-ex-post"],
            graficos=["juro-real"],
        ),
        Parte(
            "curva",
            "Juros dos títulos",
            "A curva prefixada e a de juro real do Tesouro, prazo a prazo, contra o Focus.",
            cartoes=["prefixado", "inclinacao", "juro-real-longo", "premio-curva"],
            graficos=[
                "curva-prefixada",
                "curva-real",
                "juro-titulos-focus",
                "prefixado-decomposto",
            ],
            tabelas=["titulos-por-prazo"],
        ),
        Parte(
            "implicita",
            "Inflação implícita",
            "A inflação que os títulos embutem, contra o Focus e daqui a 5 anos.",
            cartoes=["inflacao-implicita", "inflacao-implicita-focus", "implicita-a-termo"],
            graficos=["inflacao-implicita", "inflacao-titulos-focus"],
        ),
    ],
    "credito": [
        Parte(
            "volume-custo",
            "Volume e custo",
            "Quanto crédito há, quanto custa, o spread e a inadimplência.",
            cartoes=["credito-pib", "credito-taxa", "credito-spread", "inadimplencia"],
            graficos=["credito-pib", "credito-custo", "inadimplencia"],
        ),
        Parte(
            "familias",
            "Dívida das famílias",
            "Endividamento e quanto da renda vai para pagar dívida e juros.",
            cartoes=[
                "endividamento",
                "comprometimento",
                "comprometimento-juros",
                "endividamento-sem-casa",
            ],
            graficos=["familias", "familias-juros", "familias-sem-casa"],
        ),
        Parte(
            "imoveis",
            "Imóveis",
            "Juro e volume do financiamento imobiliário e o preço dos imóveis.",
            cartoes=["imobiliario-taxa", "imobiliario-concessoes", "ivgr"],
            graficos=["imobiliario-taxa", "imobiliario-concessoes", "ivgr"],
        ),
    ],
    "mercados": [
        Parte(
            "bolsa",
            "Bolsa",
            "O Ibovespa em reais e em dólares.",
            cartoes=["ibovespa", "ibovespa-dolar"],
            graficos=["ibovespa", "ibovespa-dolar"],
        ),
        Parte(
            "cambio",
            "Câmbio",
            "Dólar e euro.",
            cartoes=["dolar", "euro"],
            graficos=["dolar"],
        ),
        Parte(
            "retornos",
            "Quanto rendeu",
            "R$ 100 aplicados em bolsa, dólar, CDI ou poupança, contra a inflação.",
            graficos=["retornos-em-reais"],
            tabelas=["variacoes"],
        ),
    ],
    "externo": [
        Parte(
            "conta-corrente",
            "Conta corrente",
            "O que entra e sai do país, em partes, e o investimento estrangeiro.",
            cartoes=["transacoes-correntes"],
            graficos=["conta-corrente", "conta-corrente-partes"],
            tabelas=["balanco-pagamentos"],
        ),
        Parte(
            "comercio",
            "Comércio exterior",
            "O saldo da balança e o preço do que o Brasil vende.",
            cartoes=["balanca"],
            graficos=["balanca", "commodities"],
        ),
        Parte(
            "setores",
            "O que vende e compra",
            "Commodities nas exportações e os setores de cada lado do comércio.",
            cartoes=["commodities-exportacoes"],
            graficos=["exportacoes-composicao"],
            tabelas=["exportacoes-setores", "importacoes-setores"],
        ),
        Parte(
            "produtos",
            "Principais produtos",
            "Petróleo, soja, minério: os produtos que mais pesam na venda e na compra.",
            cartoes=["maior-exportacao"],
            tabelas=["exportacoes-produtos", "importacoes-produtos"],
        ),
        Parte(
            "parceiros",
            "Com quem negocia",
            "Para onde vão as exportações e o saldo com cada país.",
            cartoes=["china-exportacoes"],
            graficos=["exportacoes-destinos"],
            tabelas=["parceiros"],
        ),
        Parte(
            "reservas-cambio",
            "Reservas e câmbio real",
            "As reservas internacionais e se o real está caro ou barato.",
            cartoes=["reservas", "cambio-real"],
            graficos=["reservas", "cambio-real"],
        ),
    ],
    "fiscal": [
        Parte(
            "divida",
            "Dívida pública",
            "Dívida bruta e líquida, o que o mercado projeta e de que ela é feita.",
            cartoes=["dbgg", "dlsp", "divida-selic"],
            graficos=["divida", "divida-indexador"],
            veja=[
                Elo(
                    endereco=EFEITO_DA_SELIC,
                    titulo="Efeito da Selic",
                    resumo="Quanto a dívida muda com 1 ponto de Selic, nas contas do BC.",
                )
            ],
        ),
        Parte(
            "resultado",
            "Primário e juros",
            "O resultado do setor público antes e depois dos juros.",
            cartoes=["primario", "juros-divida", "nominal"],
            graficos=["primario", "nominal", "primario-mensal"],
            tabelas=["primario-bc-fmi"],
        ),
        Parte(
            "meta",
            "Meta fiscal",
            "O primário do Governo Central contra a meta da LDO e os descontos da apuração.",
            cartoes=["meta-primario"],
            graficos=["meta-primario"],
            tabelas=["meta-primario"],
        ),
        Parte(
            "receita-despesa",
            "Receita e despesa da União",
            "Quanto o Governo Central arrecada e gasta, e com o quê.",
            cartoes=["despesa-gc", "previdencia-rgps"],
            graficos=["receita-despesa", "despesa-composicao"],
        ),
    ],
    "impostos": [
        Parte(
            "arrecadacao",
            "Arrecadação federal",
            "Quanto a Receita arrecada mês a mês, de quais tributos, e contra o previsto.",
            cartoes=["arrecadacao-12m", "arrecadacao-real", "arrecadacao-pib"],
            graficos=["arrecadacao-12m", "arrecadacao-tributos"],
            tabelas=["arrecadacao-tributos", "arrecadacao-previsto"],
        ),
        Parte(
            "por-estado",
            "Por estado e por setor",
            "De onde vem a arrecadação federal: cada estado e cada setor da economia.",
            tabelas=["arrecadacao-estados", "arrecadacao-setores"],
        ),
        Parte(
            "reforma",
            "Reforma do consumo",
            "O que muda no imposto das compras de 2026 a 2033, e quanto vai numa compra.",
            cartoes=["reforma-cbs-2027", "reforma-aliquota-cheia", "reforma-icms-iss"],
            tabelas=["reforma-linha-do-tempo", "reforma-aliquota", "reforma-descontos"],
            extras=["simulador-reforma"],
        ),
        Parte(
            "carga",
            "Carga tributária",
            "Quanto do PIB vai para impostos, quem arrecada, sobre o que se cobra e como o "
            "Brasil se compara, também no crescimento.",
            cartoes=["carga-tributaria", "carga-consumo"],
            graficos=["carga-tributaria", "carga-composicao", "carga-esferas", "carga-crescimento"],
            tabelas=["carga-paises"],
        ),
        Parte(
            "quem-paga",
            "Quem paga",
            "O Imposto de Renda por faixa de quem declara e o imposto das empresas.",
            cartoes=["imposto-lucro"],
            graficos=["imposto-lucro"],
            tabelas=["quem-paga-irpf", "imposto-lucro-paises"],
        ),
        Parte(
            "gasto-tributario",
            "O que não entra",
            "O que a União deixa de arrecadar com isenções e o que tem a receber de imposto "
            "não pago.",
            cartoes=["gasto-tributario", "divida-ativa"],
            graficos=["gasto-tributario", "divida-ativa"],
            tabelas=["gasto-tributario", "gasto-tributario-regioes", "divida-ativa"],
        ),
    ],
    "previsoes": [
        Parte(
            "pib",
            "PIB",
            "O trimestre que ainda não saiu, o Focus e o FMI.",
            cartoes=["pib-agora", "focus-pib-2026"],
            graficos=["pib-agora", "pib-focus-fmi", "focus-pib"],
        ),
        Parte(
            "inflacao-juros-dolar",
            "Inflação, Selic e dólar",
            "O que o mercado espera e como a aposta mudou.",
            cartoes=["focus-ipca-2026", "focus-selic-2027", "focus-câmbio-2026"],
            graficos=["ipca-focus-fmi", "focus-ipca", "focus-selic", "focus-câmbio"],
        ),
        Parte(
            "focus",
            "O Focus e o quanto erra",
            "As medianas do Focus e o erro típico delas no passado.",
            tabelas=["focus", "acerto-focus"],
        ),
        Parte(
            "simulador",
            "Simulador da dívida",
            "Mexa no juro, no crescimento, na inflação e no primário e veja a dívida.",
            extras=["simulador"],
        ),
    ],
    "riscos": [
        Parte(
            "alerta",
            "Painel de alerta",
            "Os indicadores de risco contra a própria história.",
            cartoes=["alertas-acesos"],
            extras=["alertas"],
        ),
        Parte(
            "divida",
            "A dívida se sustenta?",
            "O primário que estabiliza a dívida, o juro contra o crescimento e o leque.",
            cartoes=[
                "primario-estabiliza",
                "divida-sobe-em-5-anos",
                "juro-menos-crescimento",
                "juro-da-divida",
                "juros-em-reais",
                "prazo-da-divida",
            ],
            graficos=["divida-leque", "primario-necessario", "juro-crescimento"],
            tabelas=["elasticidades-da-divida"],
        ),
        Parte(
            "estresse",
            "Testes de estresse",
            "A dívida se cada crise do passado se repetisse agora.",
            graficos=["estresse-divida"],
            tabelas=["estresse-episodios"],
        ),
        Parte(
            "mercado-externo",
            "Mercado e contas externas",
            "Volatilidade, nota de crédito, reservas e dívida externa.",
            cartoes=[
                "vol-dolar",
                "queda-ibovespa",
                "nota-de-credito",
                "reservas-cobertura",
                "divida-externa-liquida",
                "swaps-cambiais",
            ],
            graficos=[
                "vol-dolar",
                "queda-ibovespa",
                "cambio-real",
                "nota-de-credito",
                "reservas-cobertura",
            ],
        ),
        Parte(
            "bancos",
            "Bancos e crédito",
            "Atrasos no crédito e o capital dos bancos.",
            cartoes=["credito-atrasos", "basileia"],
            graficos=["credito-atrasos", "basileia"],
        ),
        Parte(
            "energia-populacao",
            "Energia e população",
            "Os reservatórios das hidrelétricas e o envelhecimento.",
            cartoes=["reservatorios", "idosos-por-100"],
            graficos=["reservatorios"],
        ),
    ],
}


# Estados tem peças próprias (mapa, ranking, ficha, duas métricas), montadas no navegador:
# as partes dizem só o nome e o resumo, e o site sabe o que vai em cada uma (Caio,
# 14/11/2026: "diminua a tela ao abrir por estado, também não precisa mostrar tudo em uma
# página só").
PARTES_ESTADOS: list[Parte] = [
    Parte("mapa", "Mapa e ranking", "Uma métrica nos 27 estados, do maior ao menor."),
    Parte(
        "estado",
        "Um estado por dentro",
        "Receita, despesa e dívida de um estado, uma parte de cada vez.",
    ),
    Parte("duas-metricas", "Duas métricas", "Um ponto por estado, com duas métricas juntas."),
    Parte("tabela", "Tabela completa", "Todas as métricas, estado por estado."),
]


def partes_dos_estados(tem_contas: bool) -> list[Subcategoria]:
    return [
        Subcategoria(id=p.id, titulo=p.titulo, resumo=p.resumo)
        for p in PARTES_ESTADOS
        if tem_contas or p.id != "estado"
    ]


def esperados(secao_id: str) -> dict[str, set[str]]:
    """Os ids de cartão, gráfico e tabela que as partes do assunto listam: o que a tela espera
    ver. Só estes vêm da rodada anterior quando a fonte falha (peça tirada do código não fica
    voltando)."""
    partes = PARTES.get(secao_id, [])
    return {
        k: {i for p in partes for i in getattr(p, k)} for k in ("cartoes", "graficos", "tabelas")
    }


def aplicar(secao: Secao) -> list[str]:
    """Põe as subcategorias na seção; devolve o que ficou sem lugar (foi para "Outros").

    Id listado que a seção não trouxe nesta rodada é ignorado, e parte que fica vazia some."""
    partes = PARTES.get(secao.id)
    if not partes:
        return []
    tem = {
        "cartoes": [c.id for c in secao.cartoes],
        "graficos": [g.id for g in secao.graficos],
        "tabelas": [t.id for t in secao.tabelas],
    }
    extras_da_secao: list[Extra] = []
    if secao.simulador:
        extras_da_secao.append("simulador")
    if secao.simulador_selic:
        extras_da_secao.append("simulador-selic")
    if secao.simulador_reforma:
        extras_da_secao.append("simulador-reforma")
    if secao.alertas:
        extras_da_secao.append("alertas")
    usados: dict[str, set[str]] = {k: set() for k in tem}
    subcategorias: list[Subcategoria] = []
    for p in partes:
        listas = {k: [i for i in getattr(p, k) if i in tem[k] and i not in usados[k]] for k in tem}
        extras = [e for e in p.extras if e in extras_da_secao]
        for k, ids in listas.items():
            usados[k].update(ids)
        if any(listas.values()) or extras:
            subcategorias.append(
                Subcategoria(
                    id=p.id,
                    titulo=p.titulo,
                    resumo=p.resumo,
                    extras=extras,
                    veja=p.veja,
                    cartoes=listas["cartoes"],
                    graficos=listas["graficos"],
                    tabelas=listas["tabelas"],
                )
            )
    sobra = {k: [i for i in tem[k] if i not in usados[k]] for k in tem}
    extras_sobrando = [e for e in extras_da_secao if not any(e in s.extras for s in subcategorias)]
    if any(sobra.values()) or extras_sobrando:
        subcategorias.append(
            Subcategoria(
                id="outros",
                titulo="Outros",
                resumo="O que ainda não ganhou lugar nas outras partes.",
                extras=extras_sobrando,
                cartoes=sobra["cartoes"],
                graficos=sobra["graficos"],
                tabelas=sobra["tabelas"],
            )
        )
    secao.subcategorias = subcategorias
    return [f"{k[0]}-{i}" for k, ids in sobra.items() for i in ids] + extras_sobrando
