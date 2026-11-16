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
    Categoria(id="laboratorio", titulo="Laboratório", secoes=["previsoes"]),
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
            "Desocupação, subutilização, desalento e quem procura há muito tempo.",
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
            graficos=["rendimento", "massa"],
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
            graficos=["outros-indices"],
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
            "Dólar e bolsa",
            "O dólar, o euro, o Ibovespa e quanto cada aplicação rendeu.",
            cartoes=["dolar", "euro", "ibovespa", "ibovespa-dolar"],
            graficos=["dolar", "ibovespa", "retornos-em-reais"],
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
            tabelas=["primario-conforme-o-juro", "elasticidades-da-divida"],
        ),
        Parte(
            "custo",
            "Custo, rolagem e crises",
            "Quanto se paga de juros, quanto vence logo e a dívida se cada crise se repetisse.",
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
    # O que não tem parte sai da tela (orçamento de atenção, 16/11/2026): a seção continua
    # calculando, o builder avisa, e a peça volta quando ganhar lugar numa parte.
    secao.cartoes = [c for c in secao.cartoes if c.id in usados["cartoes"]]
    secao.graficos = [g for g in secao.graficos if g.id in usados["graficos"]]
    secao.tabelas = [t for t in secao.tabelas if t.id in usados["tabelas"]]
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
