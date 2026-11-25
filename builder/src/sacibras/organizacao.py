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

from dataclasses import dataclass, field, replace
from typing import Literal

from sacibras.schema import Categoria, Elo, Grafico, Secao, Subcategoria, Tabela

Extra = Literal[
    "simulador",
    "simulador-selic",
    "simulador-reforma",
    "simulador-ldo",
    "alertas",
    "salario-minimo",
    "fichas-estatais",
]

CATEGORIAS: list[Categoria] = [
    Categoria(
        id="atividade-emprego", titulo="Atividade e emprego", secoes=["atividade", "trabalho"]
    ),
    Categoria(id="precos-juros", titulo="Preços e juros", secoes=["inflacao", "juros"]),
    Categoria(id="contas-publicas", titulo="Contas públicas", secoes=["fiscal", "impostos"]),
    Categoria(
        id="exterior-longo-prazo",
        titulo="Exterior, longo prazo e riscos",
        secoes=["externo", "longo-prazo", "riscos"],
    ),
    Categoria(id="comparar", titulo="Comparar", secoes=["estados", "mundo"]),
    Categoria(id="laboratorio", titulo="Laboratório", secoes=["laboratorio", "previsoes"]),
]
"""Nove assuntos em quatro grupos, os dois comparadores e o Laboratório (16/11/2026), que
por enquanto só tem as Previsões: o consenso do Focus, a estimativa do PIB e o simulador."""


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
    juntos: dict[str, list[str]] = field(default_factory=dict)
    """{gráfico da parte: os parecidos que ficam atrás da lista dele} (Caio,
    19/11/2026: *"mudando o parâmetro muda o gráfico ou tabela, podendo acrescentar
    informações ao site sem ter que excluir coisas e sem ficar pesado"*). Os de trás não
    contam no orçamento de atenção: na tela fica só o principal."""
    tabelas_juntas: dict[str, list[str]] = field(default_factory=dict)
    """O mesmo para as tabelas (gráfico e tabela podem ter o mesmo id)."""
    rotulos: dict[str, str] = field(default_factory=dict)
    """{id: nome curto na lista}, de gráfico ou de tabela; sem nome, vale o título."""


EFEITO_DA_SELIC = "#juros/efeito"
# Ids de parte não podem começar como os de peça (c-, g-, t-, m-, p-, uf-): o endereço
# "#assunto/x" é parte ou peça.
PARTES: dict[str, list[Parte]] = {
    "atividade": [
        Parte(
            "pib",
            "PIB",
            "O crescimento a cada trimestre, e quem produziu e quem comprou.",
            cartoes=["pib-tt", "pib-4t", "demanda-privada", "pib-carrego"],
            graficos=["pib-trimestral", "pib-contribuicoes-oferta", "pib-contribuicoes-demanda"],
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
            "Quanto do PIB vira máquinas e obras, quanto o país poupa, e os outros países.",
            cartoes=[
                "taxa-investimento",
                "taxa-poupanca",
                "investimento-brasil-fmi",
                "poupanca-brasil-fmi",
            ],
            graficos=["investimento-paises", "poupanca-paises", "investimento-poupanca"],
        ),
    ],
    "trabalho": [
        Parte(
            "desemprego",
            "Desemprego",
            "A desocupação, a subutilização, quanta gente está no mercado e por que a taxa mudou.",
            cartoes=["desocupacao", "subutilizacao", "participacao", "nivel-ocupacao"],
            graficos=["desocupacao", "desocupacao-fatores", "subutilizacao"],
        ),
        Parte(
            "quem-trabalha",
            "Carteira e informalidade",
            "O emprego com carteira, quem trabalha sem ela e quanta gente está no mercado.",
            cartoes=["emprego-formal", "informalidade"],
            graficos=["emprego-formal", "informalidade", "participacao"],
            tabelas=["emprego-setores", "trabalho-detalhe"],
        ),
        Parte(
            "renda",
            "Renda",
            "O rendimento médio e a massa de rendimento, já descontada a inflação, e o "
            "salário mínimo.",
            cartoes=["rendimento", "massa", "salario-minimo"],
            graficos=["rendimento", "massa", "massa-fatores"],
            extras=["salario-minimo"],
        ),
        Parte(
            "linha-de-pobreza",
            "Pobreza e desigualdade",
            "Quantos vivem abaixo da linha de pobreza e quem fica com quanto da renda.",
            cartoes=["pobreza", "extrema-pobreza", "fatia-10-ricos", "fatia-40-pobres"],
            graficos=["pobreza", "renda-por-grupo", "fatias"],
            tabelas=["pobreza-estados", "pobreza-decimos", "pobreza-fome"],
        ),
        Parte(
            "quem-ganha-mais",
            "O topo e as diferenças",
            "A renda do topo pela Receita, o Brasil contra os outros países e as diferenças "
            "entre grupos.",
            cartoes=["irpf-topo-renda", "irpf-topo-dividendos", "fatia-1-rico", "gini"],
            graficos=["irpf-topo-tempo", "diferencas", "gini-paises"],
            tabelas=["pobreza-irpf", "pobreza-centis"],
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
                    endereco="#juros/efeito",
                    titulo="Efeito da Selic",
                    resumo="Quanto a inflação muda com 1 ponto de Selic, nas contas do BC.",
                ),
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
            graficos=["ipca-contribuicoes", "ipca-aberturas", "ipca-itens"],
            tabelas=["ipca-grupos", "ipca-itens"],
        ),
        Parte(
            "outros-indices",
            "Outros índices e o Focus",
            "O INPC ao lado do IPCA, e o que o mercado espera.",
            cartoes=["focus-ipca"],
            graficos=["outros-indices", "expectativa-meta"],
        ),
    ],
    "juros": [
        Parte(
            "selic",
            "Selic e juro real",
            "A taxa básica, o que se espera dela e quanto sobra depois da inflação.",
            cartoes=["selic-meta", "juro-real-ex-ante", "focus-selic", "juro-real-ex-post"],
            graficos=["selic-trajetoria", "juro-real", "selic-ipca"],
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
            "curva",
            "Curva e inflação implícita",
            "O juro travado para cada prazo e a inflação que os títulos embutem.",
            cartoes=[
                "prefixado",
                "juro-real-longo",
                "inflacao-implicita",
                "inflacao-implicita-focus",
            ],
            graficos=["curva-prefixada", "prefixado-decomposto", "inflacao-titulos-focus"],
            tabelas=["titulos-por-prazo"],
        ),
        Parte(
            "volume-custo",
            "Crédito: quanto custa",
            "O juro de quem toma emprestado, por modalidade, e quanto atrasa.",
            cartoes=["credito-pib", "credito-taxa", "inadimplencia", "juro-cartao"],
            graficos=["credito-custo", "inadimplencia", "juros-modalidades"],
        ),
        Parte(
            "familias",
            "Dívida das famílias e imóveis",
            "Quanto as famílias devem, quanto da renda vai para parcelas e o crédito da casa.",
            cartoes=["endividamento", "comprometimento", "imobiliario-taxa", "ivgr"],
            graficos=["familias", "familias-juros", "ivgr"],
        ),
    ],
    "externo": [
        Parte(
            "conta-corrente",
            "Contas externas e câmbio",
            "O que entra e sai de dólares, as reservas e o câmbio real.",
            cartoes=["transacoes-correntes", "reservas", "cambio-real"],
            graficos=["conta-corrente", "reservas", "cambio-real"],
            tabelas=["balanco-pagamentos", "servicos-partes"],
        ),
        Parte(
            "comercio",
            "Comércio: o que se vende e se compra",
            "O saldo da balança, o preço das commodities e os produtos e setores.",
            cartoes=["balanca", "commodities-exportacoes", "maior-exportacao"],
            graficos=["balanca", "commodities", "exportacoes-composicao"],
            tabelas=[
                "exportacoes-setores",
                "importacoes-setores",
                "importacoes-uso",
                "exportacoes-produtos",
                "importacoes-produtos",
            ],
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
            "cambio",
            "Câmbio e aplicações",
            "O dólar, o euro e quanto cada aplicação rendeu.",
            cartoes=["dolar", "euro"],
            graficos=["dolar", "retornos-em-reais"],
            tabelas=["variacoes"],
        ),
    ],
    "fiscal": [
        Parte(
            "divida",
            "Dívida pública",
            "Dívida bruta e líquida, o que o mercado projeta, de que ela é feita, quanto "
            "custa e quando vence.",
            cartoes=["dbgg", "dlsp", "divida-selic", "juro-implicito"],
            graficos=["divida", "divida-fatores", "divida-indexador"],
            veja=[
                Elo(
                    endereco="#juros/efeito",
                    titulo="Efeito da Selic",
                    resumo="Quanto a dívida muda com 1 ponto de Selic, nas contas do BC.",
                ),
            ],
        ),
        Parte(
            "resultado",
            "Primário, juros e meta",
            "O resultado do setor público antes e depois dos juros, e o primário do Governo "
            "Central contra a meta da LDO.",
            cartoes=["primario", "juros-divida", "nominal", "meta-primario"],
            graficos=["primario", "nominal", "meta-primario"],
            tabelas=["primario-bc-fmi", "meta-primario"],
        ),
        Parte(
            "gasto",
            "Receita e gasto",
            "Quanto o Governo Central arrecada e gasta, o que é obrigatório e o Brasil contra "
            "os outros países por função.",
            cartoes=["despesa-gc", "previdencia-rgps", "discricionaria-parte", "gasto-acima-pares"],
            graficos=["receita-despesa", "despesa-composicao", "despesa-rigidez"],
            tabelas=["despesa-obrigatoria", "gasto-por-funcao"],
        ),
        # Caio, 19/11/2026: "inclua a distribuição dos gastos por servidores públicos (quem
        # fica com mais) e compare o rendimento e benefícios [...] com o setor privado" e a
        # pergunta das estatais. Para caber no teto de cinco partes, a meta entrou em
        # "Primário, juros e meta" (o primário mês a mês saiu da tela) e "Receita e despesa
        # da União" juntou-se a "Onde está o gasto" (saiu o cartão da obrigatória em % do PIB,
        # que está no gráfico).
        Parte(
            "servidores",
            "Servidores públicos",
            "Quanto custa a folha, quem fica com mais (esfera, poder, ativos e aposentados) e "
            "o contracheque e a aposentadoria contra os do setor privado.",
            cartoes=[
                "folha-ativos-pib",
                "servidor-rendimento",
                "aposentadoria-servidor",
                "folha-inativos",
            ],
            graficos=["rendimento-publico-privado", "folha-por-esfera", "folha-uniao"],
            tabelas=[
                "folha-quem-fica",
                "folha-por-poder",
                "remuneracao-por-poder",
                "folha-uniao",
                "rendimento-por-posicao",
                "aposentadoria-publico-privado",
                "folha-paises",
            ],
        ),
        Parte(
            "estatais",
            "Estatais",
            "O que as estatais federais pagam à União em dividendos, o que recebem em "
            "subvenção e capital, e cada uma por dentro: lucro, receita e balanço.",
            cartoes=["estatais-saldo", "dividendos-12m", "estatais-subvencao", "estatais-primario"],
            graficos=["estatais-conta", "dividendos-por-empresa", "estatais-primario"],
            tabelas=[
                "estatais-conta",
                "dividendos-por-empresa",
                "estatais-subvencoes",
                "estatais-lucro",
            ],
            # Caio, 25/11/2026: "abra por estatal um dashboard". As fichas vêm num arquivo à
            # parte (`Secao.arquivo_estatais`), uma de cada vez, escolhida numa lista.
            extras=["fichas-estatais"],
        ),
    ],
    "impostos": [
        Parte(
            "arrecadacao",
            "Arrecadação",
            "Quanto a Receita arrecada, de que tributos, por estado e por setor.",
            cartoes=["arrecadacao-12m", "arrecadacao-real", "arrecadacao-pib", "fpe-fpm-12m"],
            graficos=["arrecadacao-12m", "arrecadacao-tributos"],
            tabelas=[
                "arrecadacao-tributos",
                "arrecadacao-previsto",
                "arrecadacao-estados",
                "fpe-fpm-estados",
                "arrecadacao-setores",
            ],
        ),
        Parte(
            "carga",
            "Carga tributária e quem paga",
            "Quanto se cobra, sobre o quê, e o Brasil contra os outros países.",
            cartoes=["carga-tributaria", "carga-consumo", "ir-pessoas", "imposto-lucro"],
            graficos=["carga-tributaria", "carga-composicao", "imposto-lucro"],
            tabelas=[
                "carga-paises",
                "carga-bases-paises",
                "quem-paga-irpf",
                "quem-paga-retido",
                "imposto-lucro-paises",
            ],
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
            "gasto-tributario",
            "O que não entra",
            "O que a União deixa de arrecadar com isenções e o que tem a receber de imposto "
            "não pago.",
            cartoes=["gasto-tributario", "divida-ativa"],
            graficos=["gasto-tributario", "divida-ativa"],
            tabelas=["gasto-tributario", "gasto-tributario-regioes", "divida-ativa"],
        ),
        Parte(
            "esferas",
            "União, estados e municípios",
            "Quem arrecada, quanto a União repassa e para onde vai a despesa de cada esfera "
            '(pergunta "Para onde vai o imposto?").',
            cartoes=["carga-uniao", "carga-estados", "carga-municipios", "repasses-uniao"],
            graficos=["carga-esferas"],
            tabelas=["despesa-esferas"],
            veja=[
                Elo(
                    endereco="#estados/m-gasto_saude",
                    titulo="Cada estado, um por um",
                    resumo="Saúde, educação, segurança e previdência na despesa dos 27.",
                ),
            ],
        ),
    ],
    "longo-prazo": [
        Parte(
            "populacao",
            "População",
            "Quantos somos, a pirâmide etária e quando a população em idade de trabalhar para"
            " de crescer.",
            cartoes=["populacao", "populacao-15-64", "fecundidade", "idade-mediana"],
            graficos=["piramide", "crescimento-15-64", "fecundidade"],
            tabelas=["demografia-marcos"],
        ),
        Parte(
            "envelhecimento",
            "Envelhecimento e previdência",
            "Quantos idosos para cada pessoa em idade de trabalhar, e a conta da previdência.",
            cartoes=[
                "idosos-por-100",
                "deficit-inss",
                "deficit-servidores-militares",
                "esperanca-de-vida",
            ],
            graficos=["dependencia", "idosos-paises", "inss"],
            tabelas=["demografia-estados", "previdencia-uniao"],
        ),
        Parte(
            "produtividade",
            "Produtividade e eficiência",
            "Quanto cada trabalhador produz, a eficiência (PTF) e de onde veio o crescimento.",
            cartoes=["produtividade", "produtividade-hora", "ptf-eua", "ptf-desde-o-pico"],
            graficos=["crescimento-decomposto", "ptf-brasil", "ptf-paises"],
            tabelas=["pwt-contabilidade"],
            veja=[
                Elo(
                    endereco="#mundo/m-ptf",
                    titulo="PTF no mundo",
                    resumo=(
                        "O Brasil ao lado de 120 países, e o produto por hora, o capital e o "
                        "estudo de cada um."
                    ),
                ),
            ],
        ),
        Parte(
            "escola",
            "Escola",
            "Os anos de estudo, o analfabetismo e quanto a escola pesa na renda.",
            cartoes=["anos-de-estudo", "analfabetismo"],
            graficos=["renda-escolaridade", "analfabetismo"],
            tabelas=["pobreza-escola-idade"],
        ),
    ],
    "laboratorio": [
        Parte(
            "juro-neutro",
            "Juro neutro, hiato e regra de Taylor",
            "Onde estaria o juro que nem acelera nem freia, e onde a regra de Taylor põe a Selic.",
            cartoes=["juro-neutro", "hiato", "taylor"],
            graficos=["regra-de-taylor", "juro-neutro", "hiato"],
            tabelas=["juro-neutro-metodos"],
        ),
        Parte(
            "pressao",
            "O mercado: de onde vem a pressão",
            "Quanto da alta do dólar é só do Brasil, e o que o juro e o dólar fazem quando o "
            "Copom surpreende.",
            cartoes=["dolar-do-brasil", "dolar-de-fora", "copom-efeito"],
            graficos=["dolar-mundo-brasil"],
            tabelas=["dolar-altas", "copom-surpresas"],
        ),
        Parte(
            "reacao-fiscal",
            "O ajuste fiscal: o que foi feito",
            "A dívida com outro primário, por onde ele já mudou, o que custa esperar e se ele "
            "reage à dívida.",
            cartoes=["divida-sem-deficit"],
            graficos=["divida-outro-primario"],
            tabelas=[
                "primario-episodios",
                "divida-outro-primario",
                "custo-de-esperar",
                "reacao-fiscal-amostras",
            ],
        ),
        Parte(
            "promessa",
            "O prometido e o que veio",
            "A meta de cada ano e o que o mercado esperava, contra o primário e a dívida que "
            "vieram; e a meta do projeto da LDO 2027.",
            cartoes=["ldo-2027", "meta-ldo", "primario-prometido", "divida-esperada"],
            graficos=["meta-ldo", "primario-prometido", "divida-esperada", "ldo-2027-divida"],
            tabelas=[
                "meta-ldo",
                "primario-erro-horizonte",
                "ldo-2027-cenarios",
                "primario-estabiliza-ponte",
                "ldo-2027",
            ],
            extras=["simulador-ldo"],
        ),
        Parte(
            "crescimento",
            "O PIB por habitante desde 1950",
            "De onde veio o crescimento, década a década, e a distância para os EUA.",
            cartoes=["pib-hab-eua"],
            graficos=["convergencia"],
            tabelas=["pib-hab-decadas"],
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
            graficos=["ipca-focus-fmi", "focus-selic", "focus-câmbio"],
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
            "O primário que estabiliza a dívida, o juro contra o crescimento e o leque de "
            "trajetórias.",
            cartoes=[
                "primario-estabiliza",
                "divida-sobe-em-5-anos",
                "juro-menos-crescimento",
                "juro-da-divida",
            ],
            graficos=["divida-leque", "primario-necessario", "juro-crescimento"],
            tabelas=[
                "primario-estabiliza-ponte",
                "primario-conforme-o-juro",
                "elasticidades-da-divida",
            ],
        ),
        Parte(
            "custo",
            "Custo, rolagem e crises",
            "Quanto se paga de juros, quanto vence logo e o que cada crise faria hoje com a "
            "dívida, o PIB, a inflação, o dólar e a Selic.",
            cartoes=[
                "juros-sobre-receita",
                "vence-em-12-meses",
                "juros-em-reais",
                "prazo-da-divida",
            ],
            graficos=["juros-sobre-receita", "vence-em-12-meses", "estresse-divida"],
            tabelas=["estresse-episodios"],
        ),
        Parte(
            "juridico",
            "Justiça, Previdência e estados",
            "Ações na Justiça, precatórios, o INSS até 2100 e os estados perto dos limites da lei.",
            cartoes=[
                "acoes-perda-provavel",
                "sentencas-pagas",
                "inss-deficit-2060",
                "estados-no-limite",
            ],
            graficos=["acoes-judiciais", "sentencas-judiciais", "inss-ate-2100"],
            tabelas=["riscos-fiscais-uniao", "estados-no-limite"],
            veja=[
                Elo(
                    endereco="#estados/limites",
                    titulo="Estados › Perto dos limites",
                    resumo="Os 27 estados contra os limites da lei, com a nota CAPAG.",
                ),
            ],
        ),
        Parte(
            "mercado-externo",
            "Mercado, contas externas e bancos",
            "O juro real contra o dos EUA, a nota de crédito, as reservas e o capital dos bancos.",
            cartoes=["juro-real-brasil-eua", "nota-de-credito", "reservas-cobertura", "basileia"],
            graficos=["juro-real-brasil-eua", "nota-de-credito", "basileia"],
        ),
    ],
}


MAXIMO_DE_PARTES = 5
MAXIMO_DE_CARTOES = 4
MAXIMO_DE_GRAFICOS = 3
"""O orçamento de atenção (Caio, 16/11/2026): por assunto, até cinco partes; por parte, até
quatro números e três gráficos à vista. Tabela não tem teto: fica guardada atrás do clique.
Peça que a seção calcula e não está em `PARTES` sai da tela (o builder avisa)."""


# ------------------------------------------------- peças parecidas, atrás de uma lista
#
# Caio, 19/11/2026: *"vamos usar o artifício de colocar parâmetros para gráficos parecidos,
# assim mudando o parâmetro muda o gráfico ou tabela, podendo acrescentar informações ao site
# sem ter que excluir coisas e sem ficar pesado de informações, mantendo amostra do
# principal. Aplique isso sistematicamente"*. Por parte: {principal: [os de trás]}, para
# gráficos e para tabelas, e o nome curto de cada um na lista. O principal fica na tela; os
# de trás saem da lista da parte sozinhos (abaixo) e não contam no orçamento de atenção.
# Muitos dos de trás tinham saído da tela no corte de 16/11 e voltam assim. O Laboratório
# fica como está (peça dele vai ao ar com o Caio olhando).


@dataclass(frozen=True)
class Agrupar:
    graficos: dict[str, list[str]] = field(default_factory=dict)
    tabelas: dict[str, list[str]] = field(default_factory=dict)
    rotulos: dict[str, str] = field(default_factory=dict)


AGRUPAR: dict[str, dict[str, Agrupar]] = {
    "atividade": {
        "pib": Agrupar(
            graficos={
                "pib-trimestral": [
                    "pib-oferta",
                    "pib-demanda",
                    "demanda-privada",
                    "pib-por-habitante",
                ]
            },
            rotulos={
                "pib-trimestral": "PIB a cada trimestre",
                "pib-oferta": "Pela oferta, em um ano",
                "pib-demanda": "Pela demanda, em um ano",
                "demanda-privada": "Demanda privada",
                "pib-por-habitante": "Por habitante, ano a ano",
            },
        ),
        "mes-a-mes": Agrupar(
            graficos={"setores-mensais": ["confianca"]},
            rotulos={
                "setores-mensais": "Indústria, varejo e serviços",
                "confianca": "Confiança do consumidor",
            },
        ),
        "investimento": Agrupar(
            graficos={"investimento-paises": ["poupanca-paises"]},
            rotulos={"investimento-paises": "Investimento", "poupanca-paises": "Poupança"},
        ),
    },
    "trabalho": {
        "desemprego": Agrupar(
            graficos={
                "subutilizacao": ["desalento", "procura-longa"],
                "desocupacao": ["desocupacao-mais-inflacao"],
                "desocupacao-fatores": ["okun", "phillips"],
            },
            rotulos={
                "desocupacao": "Taxa de desocupação",
                "desocupacao-mais-inflacao": "Somada à inflação",
                "desocupacao-fatores": "Por que mudou",
                "okun": "Contra o PIB (Okun)",
                "phillips": "Contra a inflação (Phillips)",
                "subutilizacao": "Subutilização",
                "desalento": "Desalentados",
                "procura-longa": "Procura há 2 anos ou mais",
            },
        ),
        "quem-trabalha": Agrupar(
            graficos={"emprego-formal": ["emprego-setores"]},
            tabelas={"trabalho-detalhe": ["emprego-setores"]},
            rotulos={
                "emprego-formal": "Vagas no mês",
                "emprego-setores": "Por setor",
                "trabalho-detalhe": "Em detalhe",
            },
        ),
        "renda": Agrupar(
            graficos={"rendimento": ["renda-trabalho-grupos"], "massa": ["massa-fatores"]},
            rotulos={
                "rendimento": "Média",
                "renda-trabalho-grupos": "Por sexo e cor",
                "massa": "Em reais",
                "massa-fatores": "Emprego ou salário",
            },
        ),
        "linha-de-pobreza": Agrupar(
            graficos={
                "pobreza": [
                    "fome-pesquisas",
                    "fome-fao",
                    "programas-sociais",
                    "saneamento",
                    "internet-lenha",
                    "moradia",
                ],
                "fatias": ["gini"],
            },
            tabelas={"pobreza-estados": ["pobreza-sinisa"], "pobreza-fome": ["pobreza-saneamento"]},
            rotulos={
                "pobreza": "Pobreza",
                "fome-pesquisas": "Fome (IBGE)",
                "fome-fao": "Fome (FAO)",
                "programas-sociais": "Programas sociais",
                "saneamento": "Água, esgoto e lixo",
                "internet-lenha": "Internet, luz e lenha",
                "moradia": "Moradia",
                "fatias": "Fatias da renda",
                "gini": "Índice de Gini",
                "pobreza-estados": "Os estados",
                "pobreza-sinisa": "Esgoto por estado",
                "pobreza-fome": "Fome por lugar e idade",
                "pobreza-saneamento": "Cidade e campo",
            },
        ),
        "quem-ganha-mais": Agrupar(
            tabelas={"pobreza-irpf": ["pobreza-centis"]},
            rotulos={"pobreza-irpf": "Por faixa", "pobreza-centis": "Do pé ao topo"},
        ),
    },
    "inflacao": {
        "ipca": Agrupar(
            graficos={"ipca-12m": ["ipca-mensal"]},
            rotulos={"ipca-12m": "Em 12 meses", "ipca-mensal": "Mês a mês"},
        ),
        "nucleos": Agrupar(
            graficos={"nucleos-ritmo": ["ipca-difusao"]},
            rotulos={"nucleos-ritmo": "Núcleos", "ipca-difusao": "Difusão"},
        ),
        "grupos": Agrupar(
            graficos={"ipca-contribuicoes": ["ipca-aberturas", "ipca-itens"]},
            tabelas={"ipca-grupos": ["ipca-itens"]},
            rotulos={
                "ipca-contribuicoes": "Por grupo",
                "ipca-aberturas": "Serviços, livres e administrados",
                "ipca-itens": "Itens",
                "ipca-grupos": "Por grupo",
            },
        ),
    },
    "juros": {
        "selic": Agrupar(
            graficos={"juro-real": ["selic-ipca"]},
            rotulos={"juro-real": "Juro real", "selic-ipca": "Selic e IPCA"},
        ),
        "efeito": Agrupar(
            graficos={"selic-ciclos-alinhados": ["ipca-ciclos-alinhados"]},
            tabelas={"selic-ciclos-corte": ["selic-ciclos-alta"]},
            rotulos={
                "selic-ciclos-alinhados": "Selic",
                "ipca-ciclos-alinhados": "IPCA",
                "selic-ciclos-corte": "Ciclos de corte",
                "selic-ciclos-alta": "Ciclos de alta",
            },
        ),
        "curva": Agrupar(
            graficos={
                "curva-prefixada": ["curva-real", "juro-titulos-focus", "inclinacao"],
                "inflacao-titulos-focus": ["inflacao-implicita"],
            },
            rotulos={
                "curva-prefixada": "Prefixada",
                "curva-real": "Juro real",
                "juro-titulos-focus": "Contra a Selic do Focus",
                "inclinacao": "Inclinação no tempo",
                "inflacao-titulos-focus": "Contra o IPCA do Focus",
                "inflacao-implicita": "No tempo",
            },
        ),
        "volume-custo": Agrupar(
            graficos={"credito-custo": ["credito-pib"]},
            rotulos={"credito-custo": "Custo", "credito-pib": "Crédito sobre o PIB"},
        ),
        "familias": Agrupar(
            graficos={
                "familias": ["familias-juros", "familias-sem-casa"],
                "ivgr": ["imobiliario-taxa", "imobiliario-concessoes"],
            },
            rotulos={
                "familias": "Dívida e parcelas",
                "familias-juros": "Só os juros",
                "familias-sem-casa": "Sem o imobiliário",
                "ivgr": "Preço dos imóveis",
                "imobiliario-taxa": "Juro do financiamento",
                "imobiliario-concessoes": "Financiamento concedido",
            },
        ),
    },
    "externo": {
        "conta-corrente": Agrupar(
            graficos={"conta-corrente": ["conta-corrente-partes", "servicos-partes"]},
            tabelas={"balanco-pagamentos": ["servicos-partes"]},
            rotulos={
                "conta-corrente": "Conta corrente e investimento",
                "conta-corrente-partes": "Em partes",
                "servicos-partes": "Serviços",
                "balanco-pagamentos": "Balanço de pagamentos",
            },
        ),
        "comercio": Agrupar(
            graficos={"exportacoes-composicao": ["importacoes-uso"]},
            tabelas={
                "exportacoes-setores": ["importacoes-setores", "importacoes-uso"],
                "exportacoes-produtos": ["importacoes-produtos"],
            },
            rotulos={
                "exportacoes-composicao": "Exportações",
                "importacoes-uso": "Importações por uso",
                "exportacoes-setores": "Exportações por setor",
                "importacoes-setores": "Importações por setor",
                "exportacoes-produtos": "Exportações",
                "importacoes-produtos": "Importações",
            },
        ),
    },
    "fiscal": {
        "divida": Agrupar(
            graficos={"divida-indexador": ["divida-vencimento"]},
            rotulos={"divida-indexador": "Por indexador", "divida-vencimento": "Por vencimento"},
        ),
        "resultado": Agrupar(
            graficos={"primario": ["primario-mensal"]},
            rotulos={"primario": "Em 12 meses", "primario-mensal": "Mês a mês"},
        ),
        "gasto": Agrupar(
            graficos={"receita-despesa": ["despesa-real"]},
            rotulos={
                "receita-despesa": "Receita e despesa",
                "despesa-real": "Crescimento real da despesa",
            },
        ),
    },
    "impostos": {
        "arrecadacao": Agrupar(
            tabelas={
                "arrecadacao-tributos": ["arrecadacao-setores", "arrecadacao-previsto"],
                "arrecadacao-estados": ["fpe-fpm-estados"],
            },
            rotulos={
                "arrecadacao-tributos": "Por tributo",
                "arrecadacao-setores": "Por setor",
                "arrecadacao-previsto": "Previsto e realizado",
                "arrecadacao-estados": "O que sai de cada estado",
                "fpe-fpm-estados": "O que volta (FPE e FPM)",
            },
        ),
        "carga": Agrupar(
            graficos={"carga-tributaria": ["carga-crescimento"]},
            tabelas={
                "carga-paises": ["carga-bases-paises", "imposto-lucro-paises"],
                "quem-paga-irpf": ["quem-paga-retido"],
            },
            rotulos={
                "carga-tributaria": "No tempo",
                "carga-crescimento": "Contra o crescimento",
                "carga-paises": "Carga e composição",
                "carga-bases-paises": "Por base",
                "imposto-lucro-paises": "Imposto sobre o lucro",
                "quem-paga-irpf": "Por faixa de renda",
                "quem-paga-retido": "Retido e acerto",
            },
        ),
        "reforma": Agrupar(
            tabelas={
                "reforma-linha-do-tempo": ["reforma-seletivo-simples", "reforma-regimes"],
                "reforma-aliquota": ["reforma-descontos"],
            },
            rotulos={
                "reforma-linha-do-tempo": "Ano a ano",
                "reforma-seletivo-simples": "Seletivo e Simples",
                "reforma-regimes": "Regras próprias",
                "reforma-aliquota": "Alíquota cheia",
                "reforma-descontos": "Quem paga menos",
            },
        ),
        "gasto-tributario": Agrupar(
            tabelas={"gasto-tributario": ["gasto-tributario-regioes"]},
            rotulos={"gasto-tributario": "Os maiores", "gasto-tributario-regioes": "Por região"},
        ),
    },
    "longo-prazo": {
        "populacao": Agrupar(
            graficos={
                "crescimento-15-64": ["populacao", "populacao-onu", "nascimentos-obitos"],
                "fecundidade": ["esperanca-de-vida", "mortalidade-infantil"],
            },
            rotulos={
                "crescimento-15-64": "Crescimento de 15 a 64",
                "populacao": "População",
                "populacao-onu": "Projeção da ONU",
                "nascimentos-obitos": "Nascimentos e óbitos",
                "fecundidade": "Filhos por mulher",
                "esperanca-de-vida": "Esperança de vida",
                "mortalidade-infantil": "Mortalidade infantil",
            },
        ),
        "envelhecimento": Agrupar(
            graficos={"dependencia": ["idosos"], "inss": ["previdencia-uniao"]},
            rotulos={
                "dependencia": "Dependentes",
                "idosos": "Idosos na população",
                "inss": "INSS",
                "previdencia-uniao": "INSS, servidores e militares",
            },
        ),
        "produtividade": Agrupar(
            graficos={"crescimento-decomposto": ["produtividade", "rendimento-produtividade"]},
            rotulos={
                "rendimento-produtividade": "Contra o rendimento",
                "crescimento-decomposto": "Gente ou produto",
                "produtividade": "Por pessoa e por hora",
            },
        ),
    },
    "previsoes": {
        "inflacao-juros-dolar": Agrupar(
            graficos={"focus-selic": ["focus-ipca", "focus-câmbio"]},
            rotulos={"focus-selic": "Selic", "focus-ipca": "IPCA", "focus-câmbio": "Dólar"},
        ),
    },
    "laboratorio": {
        "promessa": Agrupar(
            graficos={"divida-esperada": ["ldo-2027-divida"]},
            rotulos={
                "divida-esperada": "O que o Focus esperava, safra a safra",
                "ldo-2027-divida": "Projeto da LDO 2027",
            },
        ),
    },
    "riscos": {
        "mercado-externo": Agrupar(
            graficos={
                "juro-real-brasil-eua": [
                    "cambio-real",
                    "reservas-cobertura",
                    "vol-dolar",
                ],
                "basileia": ["credito-atrasos"],
            },
            rotulos={
                "juro-real-brasil-eua": "Juro real: Brasil e EUA",
                "cambio-real": "Câmbio real",
                "reservas-cobertura": "Reservas e dívida curta",
                "vol-dolar": "Quanto o dólar balança",
                "basileia": "Capital dos bancos",
                "credito-atrasos": "Atrasos do crédito",
            },
        ),
    },
}


def _com_agrupar(assunto: str, p: Parte) -> Parte:
    a = AGRUPAR.get(assunto, {}).get(p.id)
    if a is None:
        return p
    atras_g = {i for v in a.graficos.values() for i in v}
    atras_t = {i for v in a.tabelas.values() for i in v}
    return replace(
        p,
        graficos=[i for i in p.graficos if i not in atras_g],
        tabelas=[i for i in p.tabelas if i not in atras_t],
        juntos={**p.juntos, **a.graficos},
        tabelas_juntas={**p.tabelas_juntas, **a.tabelas},
        rotulos={**p.rotulos, **a.rotulos},
    )


PARTES = {s: [_com_agrupar(s, p) for p in ps] for s, ps in PARTES.items()}


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
    saida = {
        k: {i for p in partes for i in getattr(p, k)} for k in ("cartoes", "graficos", "tabelas")
    }
    # Os que moram atrás da lista de um principal também são esperados.
    saida["graficos"] |= {i for p in partes for v in p.juntos.values() for i in v}
    saida["tabelas"] |= {i for p in partes for v in p.tabelas_juntas.values() for i in v}
    return saida


def _juntar[T: (Grafico, Tabela)](
    na_tela: list[T], todos: dict[str, T], partes: list[Parte], campo: str
) -> list[T]:
    """Tira da lista os que vão atrás de um principal e os põe nas `alternativas` dele."""
    atras: set[str] = set()
    saida: list[T] = []
    juntos = {k: v for p in partes for k, v in getattr(p, campo).items()}
    rotulos = {k: v for p in partes for k, v in p.rotulos.items()}
    for x in na_tela:
        for i in juntos.get(x.id, []):
            atras.add(i)
    for x in na_tela:
        if x.id in atras:
            continue
        outros = [todos[i] for i in juntos.get(x.id, []) if i in todos and i != x.id]
        nome = rotulos.get(x.id, x.rotulo_opcao)
        if outros:
            alternativas = [
                o.model_copy(update={"rotulo_opcao": rotulos.get(o.id, o.rotulo_opcao)})
                for o in outros
            ]
            x = x.model_copy(update={"alternativas": alternativas, "rotulo_opcao": nome})
        saida.append(x)
    return saida


def aplicar(secao: Secao) -> list[str]:
    """Põe as subcategorias na seção e tira dela o que não tem parte; devolve o que saiu.

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
    if secao.simulador_ldo:
        extras_da_secao.append("simulador-ldo")
    if secao.alertas:
        extras_da_secao.append("alertas")
    if secao.salario_minimo:
        extras_da_secao.append("salario-minimo")
    if secao.arquivo_estatais:
        extras_da_secao.append("fichas-estatais")
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
    # O que fica atrás da lista de um principal que está na tela também tem lugar.
    graficos_atras = {g.id: g for g in secao.graficos}
    tabelas_atras = {t.id: t for t in secao.tabelas}
    for p in partes:
        for k, campo in (("graficos", "juntos"), ("tabelas", "tabelas_juntas")):
            for principal, outros in getattr(p, campo).items():
                if principal in usados[k]:
                    usados[k].update(i for i in outros if i in tem[k])
    sobra = {k: [i for i in tem[k] if i not in usados[k]] for k in tem}
    extras_sobrando = [e for e in extras_da_secao if not any(e in s.extras for s in subcategorias)]
    # O que não tem parte sai da tela (orçamento de atenção, 16/11/2026): a seção continua
    # calculando, o builder avisa, e a peça volta quando ganhar lugar numa parte.
    secao.cartoes = [c for c in secao.cartoes if c.id in usados["cartoes"]]
    secao.graficos = _juntar(
        [g for g in secao.graficos if g.id in usados["graficos"]], graficos_atras, partes, "juntos"
    )
    secao.tabelas = _juntar(
        [t for t in secao.tabelas if t.id in usados["tabelas"]],
        tabelas_atras,
        partes,
        "tabelas_juntas",
    )
    if extras_sobrando:
        subcategorias.append(
            Subcategoria(
                id="outros",
                titulo="Outros",
                resumo="O que ainda não ganhou lugar nas outras partes.",
                extras=extras_sobrando,
            )
        )
    secao.subcategorias = subcategorias
    return [f"{k[0]}-{i}" for k, ids in sobra.items() for i in ids] + extras_sobrando
