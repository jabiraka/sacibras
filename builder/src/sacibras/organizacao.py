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

Extra = Literal["simulador", "simulador-selic", "simulador-reforma", "alertas", "salario-minimo"]

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
            "O rendimento médio e a massa de rendimento, já descontada a inflação, e o salário "
            "mínimo.",
            cartoes=["rendimento", "massa", "salario-minimo"],
            graficos=["rendimento", "massa"],
            extras=["salario-minimo"],
        ),
        Parte(
            "quem-trabalha",
            "Quem trabalha",
            "Emprego com carteira, setor a setor, informalidade e participação na força de "
            "trabalho.",
            cartoes=["emprego-formal", "informalidade", "participacao", "nivel-ocupacao"],
            graficos=["emprego-formal", "emprego-setores", "informalidade", "participacao"],
            tabelas=["emprego-setores", "trabalho-detalhe"],
        ),
    ],
    "demografia": [
        Parte(
            "populacao",
            "População",
            "Quantos somos, a pirâmide etária, quem está em idade de trabalhar e a projeção "
            "da ONU, com a faixa.",
            cartoes=["populacao", "populacao-15-64", "idade-mediana"],
            graficos=["piramide", "populacao", "populacao-onu", "crescimento-15-64"],
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
            "Idosos para cada pessoa em idade de trabalhar, por estado e contra o mundo, e o "
            "déficit do INSS, dos servidores e dos militares da União.",
            cartoes=["idosos-por-100", "deficit-inss", "deficit-servidores-militares"],
            graficos=["dependencia", "idosos", "idosos-paises", "inss", "previdencia-uniao"],
            tabelas=["demografia-estados", "previdencia-uniao"],
        ),
        Parte(
            "produtividade",
            "Produtividade",
            "PIB por pessoa ocupada e por hora trabalhada, e de onde veio o crescimento.",
            cartoes=["produtividade", "produtividade-hora"],
            graficos=["produtividade", "crescimento-decomposto"],
        ),
    ],
    "pobreza": [
        Parte(
            "linha-de-pobreza",
            "Pobreza",
            "Quantos vivem abaixo das linhas de pobreza, quantas casas recebem Bolsa Família e "
            "a pobreza em cada estado.",
            cartoes=["pobreza", "extrema-pobreza", "bolsa-familia"],
            graficos=["pobreza", "programas-sociais"],
            tabelas=["pobreza-estados"],
        ),
        Parte(
            "fome",
            "Fome",
            "Quantos moram em casas onde falta comida, desde 2004, e se o Brasil está no Mapa "
            "da Fome.",
            cartoes=["fome", "inseguranca-moderada-grave", "subalimentacao"],
            graficos=["fome-fao", "fome-pesquisas"],
            tabelas=["pobreza-fome"],
        ),
        Parte(
            "saneamento",
            "A casa: água, esgoto, aluguel",
            "Água, esgoto e lixo contra a meta de 2033, o esgoto tratado em cada estado, luz, "
            "internet, fogão a lenha e quem mora de aluguel.",
            cartoes=["agua", "esgoto", "lixo", "internet", "lenha", "aluguel"],
            graficos=["saneamento", "internet-lenha", "moradia"],
            tabelas=["pobreza-saneamento", "pobreza-sinisa"],
        ),
        Parte(
            "desigualdade",
            "Desigualdade",
            "O Gini e quem fica com quanto da renda: os mais pobres, o meio e os mais ricos; e "
            "o Gini do Brasil no mundo.",
            cartoes=["gini", "fatia-10-ricos", "fatia-1-rico", "fatia-40-pobres", "razao-10-40"],
            graficos=["gini", "fatias", "renda-por-grupo", "gini-paises"],
            tabelas=["pobreza-decimos"],
        ),
        Parte(
            "quem-ganha-mais",
            "O topo pelo Imposto de Renda",
            "Renda, patrimônio e dividendos de quem declara, do pé ao topo, e o topo ano a ano.",
            cartoes=["irpf-topo-renda", "irpf-topo-dividendos", "irpf-1-patrimonio"],
            graficos=["irpf-topo-tempo"],
            tabelas=["pobreza-irpf", "pobreza-centis"],
        ),
        Parte(
            "diferencas",
            "Sexo, cor, escola e idade",
            "A renda do trabalho por sexo, cor, escolaridade e idade, e quem não sabe ler.",
            cartoes=[
                "mulheres-homens",
                "pretos-brancos",
                "pardos-brancos",
                "superior-medio",
                "analfabetismo",
                "anos-de-estudo",
            ],
            graficos=[
                "diferencas",
                "renda-trabalho-grupos",
                "renda-escolaridade",
                "analfabetismo",
            ],
            tabelas=["pobreza-escola-idade"],
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
            "Serviços, livres, administrados, cada grupo do IPCA e os itens que mais pesam, "
            "como gasolina, luz e aluguel.",
            cartoes=["servicos-12m"],
            graficos=["ipca-aberturas", "ipca-itens"],
            tabelas=["ipca-grupos", "ipca-itens"],
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
            "Quanto crédito há, quanto custa, o spread, a inadimplência e o juro de cada "
            "modalidade, do cartão ao consignado.",
            cartoes=[
                "credito-pib",
                "credito-taxa",
                "credito-spread",
                "inadimplencia",
                "juro-cartao",
            ],
            graficos=["credito-pib", "credito-custo", "inadimplencia", "juros-modalidades"],
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
            "R$ 100 aplicados em bolsa, dólar, CDI, poupança, Tesouro ou ouro, contra a inflação.",
            graficos=["retornos-em-reais"],
            tabelas=["variacoes"],
        ),
    ],
    "externo": [
        Parte(
            "conta-corrente",
            "Conta corrente",
            "O que entra e sai do país, em partes, os serviços e o investimento estrangeiro.",
            cartoes=["transacoes-correntes"],
            graficos=["conta-corrente", "conta-corrente-partes", "servicos-partes"],
            tabelas=["balanco-pagamentos", "servicos-partes"],
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
            "Commodities nas exportações, os setores de cada lado do comércio e o uso do que "
            "se importa.",
            cartoes=["commodities-exportacoes"],
            graficos=["exportacoes-composicao", "importacoes-uso"],
            tabelas=["exportacoes-setores", "importacoes-setores", "importacoes-uso"],
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
            "Dívida bruta e líquida, o que o mercado projeta, de que ela é feita, quanto "
            "custa e quando vence.",
            cartoes=["dbgg", "dlsp", "divida-selic", "juro-implicito"],
            graficos=["divida", "divida-indexador", "divida-vencimento"],
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
            "De onde vem a arrecadação federal, cada estado e cada setor, e o que volta aos "
            "estados no FPE e no FPM.",
            cartoes=["fpe-fpm-12m"],
            tabelas=["arrecadacao-estados", "fpe-fpm-estados", "arrecadacao-setores"],
        ),
        Parte(
            "reforma",
            "Reforma do consumo",
            "O que muda no imposto das compras de 2026 a 2033, quanto vai numa compra, o "
            "Imposto Seletivo, o Simples, os setores com regra própria e o IBS indo para o "
            "destino.",
            cartoes=["reforma-cbs-2027", "reforma-aliquota-cheia", "reforma-icms-iss"],
            graficos=["reforma-transicao", "reforma-destino"],
            tabelas=[
                "reforma-linha-do-tempo",
                "reforma-aliquota",
                "reforma-descontos",
                "reforma-seletivo-simples",
                "reforma-regimes",
            ],
            extras=["simulador-reforma"],
        ),
        Parte(
            "carga",
            "Carga tributária",
            "Quanto do PIB vai para impostos, quem arrecada, sobre o que se cobra (renda, "
            "consumo, salário) e como o Brasil se compara, também no crescimento.",
            cartoes=["carga-tributaria", "carga-consumo", "ir-pessoas"],
            graficos=["carga-tributaria", "carga-composicao", "carga-esferas", "carga-crescimento"],
            tabelas=["carga-paises", "carga-bases-paises"],
        ),
        Parte(
            "quem-paga",
            "Quem paga",
            "O Imposto de Renda por faixa de quem declara, o retido na fonte e o imposto das "
            "empresas.",
            cartoes=["imposto-lucro"],
            graficos=["imposto-lucro"],
            tabelas=["quem-paga-irpf", "quem-paga-retido", "imposto-lucro-paises"],
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
            "O primário que estabiliza a dívida, o juro contra o crescimento, o leque e a dívida "
            "se cada crise do passado se repetisse agora.",
            cartoes=[
                "primario-estabiliza",
                "divida-sobe-em-5-anos",
                "juro-menos-crescimento",
                "juro-da-divida",
            ],
            graficos=["divida-leque", "primario-necessario", "juro-crescimento", "estresse-divida"],
            tabelas=["elasticidades-da-divida", "estresse-episodios"],
        ),
        Parte(
            "custo",
            "Custo e rolagem da dívida",
            "Quanto se paga de juros, quanto da receita eles levam e quanto vence logo.",
            cartoes=[
                "juros-em-reais",
                "juros-sobre-receita",
                "vence-em-12-meses",
                "prazo-da-divida",
            ],
            graficos=["juros-sobre-receita", "vence-em-12-meses"],
        ),
        Parte(
            "juridico",
            "Riscos fiscais: Justiça, Previdência e estados",
            "Ações na Justiça, precatórios, governança, o INSS até 2100, o envelhecimento e os "
            "estados perto dos limites da lei.",
            cartoes=[
                "acoes-perda-provavel",
                "sentencas-pagas",
                "inss-deficit-2060",
                "idosos-por-100",
                "estados-no-limite",
            ],
            graficos=["acoes-judiciais", "sentencas-judiciais", "inss-ate-2100"],
            tabelas=["riscos-fiscais-uniao", "estados-no-limite", "governanca"],
            veja=[
                Elo(
                    endereco="#estados/limites",
                    titulo="Estados › Perto dos limites",
                    resumo="Os 27 estados contra os limites da lei, com a nota CAPAG.",
                )
            ],
        ),
        Parte(
            "mercado-externo",
            "Mercado e contas externas",
            "Volatilidade, juro real contra os EUA, nota de crédito, reservas e dívida externa.",
            cartoes=[
                "juro-real-brasil-eua",
                "vol-dolar",
                "queda-ibovespa",
                "nota-de-credito",
                "reservas-cobertura",
                "divida-externa-liquida",
                "swaps-cambiais",
            ],
            graficos=[
                "juro-real-brasil-eua",
                "vol-dolar",
                "queda-ibovespa",
                "cambio-real",
                "nota-de-credito",
                "reservas-cobertura",
            ],
        ),
        Parte(
            "bancos",
            "Bancos e energia",
            "Atrasos no crédito, o capital dos bancos e os reservatórios das hidrelétricas.",
            cartoes=["credito-atrasos", "basileia", "reservatorios"],
            graficos=["credito-atrasos", "basileia", "reservatorios"],
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
        "Receita, gasto, dívida, exportações, a pirâmide etária e as contas no tempo.",
    ),
    Parte(
        "limites",
        "Perto dos limites",
        "Estados e capitais contra os limites da lei, com a CAPAG e o acordo da dívida.",
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
    if secao.salario_minimo:
        extras_da_secao.append("salario-minimo")
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
