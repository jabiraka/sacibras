"""As perguntas: a entrada do site (Caio, 16/11/2026: *"o gancho vai ser problemas e
perguntas que as pessoas buscam algum tipo de resposta, vamos evitar mostrar só o dado pelo
dado [...] mostrar o dado que responde uma pergunta ou problema"*).

Cada pergunta tem uma resposta curta, os números de hoje que a sustentam e de três a seis
explicações. A explicação é uma frase com o que os economistas dizem, sem escolher qual
está certa, e ao lado vai o número e o gráfico do painel que a mede. Nada aqui é dado novo:
os cartões e gráficos são os dos assuntos, copiados com a data e a fonte deles; o que
faltar numa rodada simplesmente não aparece.

Regra do orçamento de atenção: até 3 números na resposta, até 6 explicações, até 2 números
e 1 gráfico por explicação.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sacibras.schema import BlocoPergunta, Cartao, Grafico, ItemPergunta, Pergunta

MAXIMO_DE_NUMEROS = 3
MAXIMO_DE_BLOCOS = 6

Ref = tuple[str, str]
"""(assunto, id do cartão ou do gráfico). O id pode acabar em "*": vale o primeiro que
começa assim (os cartões do Focus levam o ano no id)."""


@dataclass(frozen=True)
class Bloco:
    titulo: str
    texto: str
    grafico: Ref | None = None
    numeros: tuple[Ref, ...] = ()


@dataclass(frozen=True)
class Definicao:
    id: str
    titulo: str
    resposta: str
    numeros: tuple[Ref, ...]
    blocos: tuple[Bloco, ...]
    palavras: tuple[str, ...] = field(default=())
    """Como alguém procuraria a pergunta na busca."""


PERGUNTAS: tuple[Definicao, ...] = (
    Definicao(
        "juro-alto",
        "Por que o juro é tão alto?",
        "Não há uma causa só. Os economistas apontam a inflação acima da meta, a dívida "
        "pública, a pouca poupança e o juro dos outros países; abaixo, o número de cada uma.",
        (("juros", "selic-meta"), ("juros", "juro-real-ex-ante"), ("inflacao", "ipca-12m")),
        (
            Bloco(
                "A inflação está acima da meta",
                "O Banco Central sobe o juro quando a inflação, ou a inflação que se espera, "
                "passa da meta, e só baixa quando as duas voltam.",
                ("inflacao", "ipca-12m"),
                (("inflacao", "ipca-12m"), ("inflacao", "focus-ipca")),
            ),
            Bloco(
                "A dívida pública é alta e cresce",
                "Quem empresta a um governo que deve muito pede juro maior, e o juro maior "
                "faz a dívida crescer mais depressa.",
                ("riscos", "juro-crescimento"),
                (("fiscal", "dbgg"), ("riscos", "juro-menos-crescimento")),
            ),
            Bloco(
                "O país poupa pouco",
                "Com pouca poupança para financiar o investimento, o dinheiro disponível "
                "fica mais caro.",
                ("atividade", "investimento-poupanca"),
                (("atividade", "taxa-poupanca"), ("atividade", "taxa-investimento")),
            ),
            Bloco(
                "O prazo longo cobra a incerteza",
                "No juro de um título longo entram a inflação que o investidor espera e um "
                "prêmio pelo risco de errar essa conta.",
                ("juros", "prefixado-decomposto"),
                (("juros", "juro-real-longo"), ("juros", "inflacao-implicita")),
            ),
            Bloco(
                "O juro dos outros países",
                "Quando o juro dos Estados Unidos sobe, o Brasil paga mais para atrair o "
                "mesmo dinheiro.",
                ("riscos", "juro-real-brasil-eua"),
                (("riscos", "juro-real-brasil-eua"),),
            ),
        ),
        ("selic alta", "juros altos", "taxa de juros", "por que a selic"),
    ),
    Definicao(
        "divida",
        "A dívida pública se sustenta?",
        "A dívida em relação ao PIB para de subir quando o resultado do governo, antes dos "
        "juros, cobre a diferença entre o juro que ele paga e o crescimento da economia. "
        "Hoje ele não cobre.",
        (("fiscal", "dbgg"), ("riscos", "primario-estabiliza"), ("fiscal", "primario")),
        (
            Bloco(
                "Quanto falta para ela parar de subir",
                "O primário que estabiliza a dívida sai do juro e do crescimento de hoje; a "
                "distância até o resultado de fato é o ajuste que falta.",
                ("riscos", "primario-necessario"),
                (("riscos", "primario-estabiliza"), ("fiscal", "primario")),
            ),
            Bloco(
                "O juro corre mais que a economia",
                "Enquanto o juro da dívida passa do crescimento do PIB, a dívida sobe "
                "sozinha, mesmo sem déficit novo.",
                ("riscos", "juro-crescimento"),
                (("riscos", "juro-menos-crescimento"), ("fiscal", "juros-divida")),
            ),
            Bloco(
                "Para onde ela pode ir",
                "O leque sorteia os choques de juro, crescimento e resultado que o Brasil "
                "já viveu e mostra as trajetórias que saem deles.",
                ("riscos", "divida-leque"),
                (("riscos", "divida-sobe-em-5-anos"),),
            ),
            Bloco(
                "Quanto custa carregar",
                "Dívida que vence logo precisa ser trocada pelo juro do dia; quanto mais "
                "da receita vai para juros, menos sobra para o resto.",
                ("riscos", "juros-sobre-receita"),
                (("riscos", "juros-sobre-receita"), ("riscos", "vence-em-12-meses")),
            ),
            Bloco(
                "Se uma crise se repetisse",
                "Cada crise do passado, aplicada à dívida de hoje: quanto ela subiria.",
                ("riscos", "estresse-divida"),
            ),
            Bloco(
                "O que dizem as agências",
                "As três agências dão nota à capacidade do governo de pagar e a revisam todo ano.",
                ("riscos", "nota-de-credito"),
                (("riscos", "nota-de-credito"),),
            ),
        ),
        ("calote", "dívida do governo", "o brasil vai quebrar", "sustentabilidade da dívida"),
    ),
    Definicao(
        "crescimento",
        "Por que o Brasil cresce pouco?",
        "No longo prazo a economia cresce com mais gente trabalhando, mais máquinas e mais "
        "eficiência. No Brasil a eficiência parou há décadas e a população em idade de "
        "trabalhar está perto de parar de crescer.",
        (("atividade", "pib-4t"), ("atividade", "produtividade"), ("atividade", "ptf-eua")),
        (
            Bloco(
                "A eficiência parou",
                "A eficiência (PTF) é o quanto se produz com o mesmo trabalho e as mesmas "
                "máquinas. É ela que separa os países ricos dos outros.",
                ("atividade", "ptf-brasil"),
                (("atividade", "ptf-eua"), ("atividade", "ptf-desde-o-pico")),
            ),
            Bloco(
                "Mais gente, não mais produto por pessoa",
                "O crescimento pode vir de mais gente ocupada ou de cada um produzir mais. "
                "Só o segundo aumenta a renda de cada pessoa.",
                ("atividade", "crescimento-decomposto"),
                (("atividade", "produtividade"),),
            ),
            Bloco(
                "Investe-se pouco",
                "Máquinas, estradas e fábricas novas vêm do investimento, que depende de "
                "poupança daqui ou de fora.",
                ("atividade", "investimento-poupanca"),
                (("atividade", "taxa-investimento"), ("atividade", "taxa-poupanca")),
            ),
            Bloco(
                "A população que trabalha para de crescer",
                "Com menos filhos por mulher, a população de 15 a 64 anos cresce cada vez "
                "menos: daqui para a frente, crescer depende de produtividade.",
                ("demografia", "crescimento-15-64"),
                (("demografia", "populacao-15-64"), ("demografia", "fecundidade")),
            ),
            Bloco(
                "A escola",
                "Mais anos de estudo, e estudo melhor, aumentam o que cada trabalhador "
                "produz e ganha.",
                ("pobreza", "renda-escolaridade"),
                (("pobreza", "anos-de-estudo"),),
            ),
        ),
        ("pib baixo", "crescimento econômico", "produtividade", "renda média"),
    ),
    Definicao(
        "inflacao",
        "A inflação está sob controle?",
        "Vale olhar além do número cheio: o que resta quando se tiram os preços que mais "
        "oscilam, quanto dos itens está subindo e o que se espera para a frente.",
        (("inflacao", "ipca-12m"), ("inflacao", "nucleos-12m"), ("inflacao", "focus-ipca")),
        (
            Bloco(
                "O número cheio contra a meta",
                "A meta e a tolerância são fixadas pelo Conselho Monetário Nacional; o que "
                "vale é o IPCA acumulado em 12 meses.",
                ("inflacao", "ipca-12m"),
                (("inflacao", "ipca-12m"),),
            ),
            Bloco(
                "Sem os preços que mais oscilam",
                "Os núcleos tiram ou diminuem o peso do que sobe e desce muito, como "
                "comida e energia, e mostram a tendência.",
                ("inflacao", "nucleos-ritmo"),
                (("inflacao", "nucleos-12m"), ("inflacao", "nucleos-3m")),
            ),
            Bloco(
                "Serviços",
                "Os serviços seguem os salários e demoram mais a ceder: é onde o Banco "
                "Central olha para saber se a inflação cai de verdade.",
                ("inflacao", "ipca-aberturas"),
                (("inflacao", "servicos-12m"),),
            ),
            Bloco(
                "Espalhada ou concentrada",
                "Inflação de poucos itens passa; quando a maioria dos itens sobe, ela "
                "tende a durar.",
                ("inflacao", "ipca-difusao"),
                (("inflacao", "difusao"),),
            ),
            Bloco(
                "O que se espera para a frente",
                "Preços e salários de hoje são marcados pela inflação que se espera: a "
                "dos analistas (Focus) e a embutida nos títulos públicos.",
                ("juros", "inflacao-titulos-focus"),
                (("inflacao", "focus-ipca"), ("juros", "inflacao-implicita")),
            ),
            Bloco(
                "De onde ela vem",
                "Quanto cada grupo de preços pôs no IPCA de 12 meses.",
                ("inflacao", "ipca-contribuicoes"),
            ),
        ),
        ("preços subindo", "custo de vida", "ipca", "carestia"),
    ),
    Definicao(
        "imposto",
        "Para onde vai o imposto, e quem paga?",
        "O Brasil arrecada perto da média dos países ricos, mas cobra mais sobre o consumo "
        "e menos sobre a renda. No gasto federal, a maior conta é a previdência.",
        (
            ("impostos", "carga-tributaria"),
            ("impostos", "carga-consumo"),
            ("fiscal", "despesa-gc"),
        ),
        (
            Bloco(
                "Paga-se muito ou pouco?",
                "A carga tributária é tudo o que União, estados e municípios arrecadam, em "
                "relação ao PIB.",
                ("impostos", "carga-tributaria"),
                (("impostos", "carga-tributaria"),),
            ),
            Bloco(
                "Sobre o que se cobra",
                "Imposto sobre o consumo pesa mais em quem ganha menos, que gasta quase "
                "tudo o que recebe; imposto sobre a renda pesa mais em quem ganha mais.",
                ("impostos", "carga-composicao"),
                (("impostos", "carga-consumo"),),
            ),
            Bloco(
                "Para onde vai",
                "A despesa do Governo Central por destino: previdência, pessoal, "
                "benefícios sociais, saúde, educação e o resto.",
                ("fiscal", "despesa-composicao"),
                (("fiscal", "previdencia-rgps"), ("fiscal", "juros-divida")),
            ),
            Bloco(
                "O que se deixa de cobrar",
                "Isenções, deduções e regimes especiais: imposto que a lei manda não "
                "cobrar de alguns.",
                ("impostos", "gasto-tributario"),
                (("impostos", "gasto-tributario"),),
            ),
            Bloco(
                "O topo da renda",
                "Quanto da renda e dos dividendos declarados à Receita fica com a faixa "
                "mais alta de quem declara.",
                ("pobreza", "irpf-topo-tempo"),
                (("pobreza", "irpf-topo-renda"), ("pobreza", "irpf-topo-dividendos")),
            ),
            Bloco(
                "O que muda com a reforma",
                "A reforma troca cinco impostos sobre o consumo (PIS, Cofins, IPI, ICMS e "
                "ISS) por dois (CBS e IBS), cobrados onde se consome.",
                ("impostos", "reforma-transicao"),
                (("impostos", "reforma-aliquota-cheia"),),
            ),
        ),
        ("carga tributária", "quem paga imposto", "gasto público", "reforma tributária"),
    ),
    Definicao(
        "emprego",
        "O emprego está bom mesmo?",
        "A taxa de desocupação só conta quem procura trabalho e não acha. Para saber como "
        "vai o emprego, entram também quem desistiu de procurar, quem trabalha menos do "
        "que queria, quem não tem carteira e quanto se ganha.",
        (("trabalho", "desocupacao"), ("trabalho", "subutilizacao"), ("trabalho", "rendimento")),
        (
            Bloco(
                "Quem procura e não acha",
                "A desocupação é a parcela de quem está na força de trabalho e procurou "
                "emprego sem encontrar.",
                ("trabalho", "desocupacao"),
                (("trabalho", "desocupacao"),),
            ),
            Bloco(
                "Quem ficou de fora da conta",
                "A subutilização soma os desocupados, quem trabalha poucas horas e quem "
                "queria trabalhar mas não procurou.",
                ("trabalho", "subutilizacao"),
                (("trabalho", "subutilizacao"),),
            ),
            Bloco(
                "Quanta gente está no mercado",
                "Se muita gente para de procurar, a desocupação cai sem que haja mais "
                "emprego. A participação mostra isso.",
                ("trabalho", "participacao"),
                (("trabalho", "participacao"),),
            ),
            Bloco(
                "Com ou sem carteira",
                "Trabalho informal não tem férias, 13º nem contribuição para a aposentadoria.",
                ("trabalho", "informalidade"),
                (("trabalho", "informalidade"), ("trabalho", "emprego-formal")),
            ),
            Bloco(
                "Quanto se ganha",
                "O rendimento médio, já descontada a inflação.",
                ("trabalho", "rendimento"),
                (("trabalho", "rendimento"), ("trabalho", "salario-minimo")),
            ),
            Bloco(
                "Por que a taxa mudou",
                "A desocupação cai porque há mais gente ocupada ou porque há menos gente "
                "procurando: a conta separa as duas coisas.",
                ("trabalho", "desocupacao-fatores"),
            ),
        ),
        ("desemprego", "mercado de trabalho", "salário", "carteira assinada"),
    ),
    Definicao(
        "desigualdade",
        "Quem ficou com o crescimento?",
        "O Brasil segue entre os países mais desiguais do mundo, mas a renda dos mais "
        "pobres cresceu mais que a dos mais ricos nas pesquisas do IBGE. No topo, os dados "
        "da Receita mostram concentração maior do que as pesquisas captam.",
        (("pobreza", "fatia-10-ricos"), ("pobreza", "fatia-40-pobres"), ("pobreza", "pobreza")),
        (
            Bloco(
                "Quanto cresceu a renda de cada grupo",
                "A renda dos 40 % de menor renda, do meio e dos 10 % de maior renda, desde 2012.",
                ("pobreza", "renda-por-grupo"),
            ),
            Bloco(
                "Quem fica com quanto",
                "A parte da renda total que vai para cada grupo.",
                ("pobreza", "fatias"),
                (("pobreza", "fatia-10-ricos"), ("pobreza", "fatia-40-pobres")),
            ),
            Bloco(
                "O topo que a pesquisa não vê",
                "Pesquisa de domicílio capta mal as rendas mais altas; a declaração do "
                "imposto de renda mostra esse pedaço.",
                ("pobreza", "irpf-topo-tempo"),
                (("pobreza", "irpf-topo-renda"), ("pobreza", "fatia-1-rico")),
            ),
            Bloco(
                "A pobreza",
                "Quantos vivem abaixo da linha de pobreza e da de extrema pobreza do "
                "Banco Mundial.",
                ("pobreza", "pobreza"),
                (("pobreza", "pobreza"), ("pobreza", "extrema-pobreza")),
            ),
            Bloco(
                "Entre homens e mulheres, brancos e negros",
                "Quanto cada grupo ganha para cada R$ 100 do grupo que ganha mais.",
                ("pobreza", "diferencas"),
            ),
            Bloco(
                "O Brasil e os outros países",
                "O Gini vai de 0 (todos com a mesma renda) a 1 (tudo com um só).",
                ("pobreza", "gini-paises"),
                (("pobreza", "gini"),),
            ),
        ),
        ("desigualdade", "distribuição de renda", "pobreza", "ricos e pobres"),
    ),
    Definicao(
        "mercado",
        "O que o mercado espera do Brasil?",
        "Há duas formas de saber: o que os analistas respondem ao Banco Central toda semana "
        "(o Focus) e o que os preços dos títulos públicos embutem. Nenhuma das duas é "
        "promessa: as duas erram, e dá para ver quanto.",
        (
            ("previsoes", "focus-pib-*"),
            ("previsoes", "focus-ipca-*"),
            ("previsoes", "focus-selic-*"),
        ),
        (
            Bloco(
                "A Selic daqui para a frente",
                "A Selic decidida até hoje e a que os analistas esperam para cada reunião "
                "do Copom.",
                ("juros", "selic-trajetoria"),
                (("juros", "selic-meta"), ("juros", "focus-selic")),
            ),
            Bloco(
                "O juro travado em cada prazo",
                "A curva dos títulos prefixados é o juro que o mercado aceita hoje para "
                "emprestar ao governo até cada data.",
                ("juros", "curva-prefixada"),
                (("juros", "prefixado"),),
            ),
            Bloco(
                "A inflação nos títulos e a dos analistas",
                "A diferença entre o título prefixado e o que paga acima da inflação é a "
                "inflação que o mercado embute, prazo a prazo.",
                ("juros", "inflacao-titulos-focus"),
                (("juros", "inflacao-implicita"), ("previsoes", "focus-ipca-*")),
            ),
            Bloco(
                "O crescimento",
                "O PIB que saiu, o que o Focus espera e o que o FMI projeta.",
                ("previsoes", "pib-focus-fmi"),
                (("previsoes", "focus-pib-*"),),
            ),
            Bloco(
                "O dólar",
                "Como a aposta dos analistas para o dólar no fim do ano mudou com o tempo.",
                ("previsoes", "focus-câmbio"),
                (("previsoes", "focus-câmbio-*"), ("mercados", "dolar")),
            ),
            Bloco(
                "A dívida",
                "A dívida bruta e a trajetória que o mercado projeta para ela.",
                ("fiscal", "divida"),
                (("fiscal", "dbgg"),),
            ),
        ),
        ("expectativas", "focus", "previsão", "curva de juros", "o dólar vai subir"),
    ),
)


def _achar[T: (Cartao, Grafico)](pecas: dict[Ref, T], ref: Ref) -> T | None:
    assunto, id = ref
    if not id.endswith("*"):
        return pecas.get(ref)
    prefixo = id[:-1]
    for (a, i), peca in sorted(pecas.items()):
        if a == assunto and i.startswith(prefixo):
            return peca
    return None


def montar(
    cartoes: dict[Ref, Cartao], graficos: dict[Ref, Grafico], titulos: dict[str, str]
) -> list[Pergunta]:
    """As perguntas com as peças de hoje. `titulos`: o nome de cada assunto, para o elo."""
    saida: list[Pergunta] = []
    for d in PERGUNTAS:
        no_topo = [c for r in d.numeros[:MAXIMO_DE_NUMEROS] if (c := _achar(cartoes, r))]
        ja_dito = {c.id for c in no_topo}
        blocos: list[BlocoPergunta] = []
        for b in d.blocos[:MAXIMO_DE_BLOCOS]:
            grafico = _achar(graficos, b.grafico) if b.grafico else None
            achados = [c for r in b.numeros[:2] if (c := _achar(cartoes, r))]
            if not grafico and not achados:
                continue  # sem dado nesta rodada, a explicação não aparece
            # O número que já está em cima, na resposta, não se repete na explicação.
            numeros = [c for c in achados if c.id not in ja_dito]
            assunto = b.grafico[0] if b.grafico else b.numeros[0][0]
            blocos.append(
                BlocoPergunta(
                    titulo=b.titulo,
                    texto=b.texto,
                    numeros=numeros,
                    grafico=grafico.model_copy(update={"secao": assunto}) if grafico else None,
                    assunto=assunto,
                    assunto_titulo=titulos.get(assunto, ""),
                    elo=f"#{assunto}/g-{grafico.id}" if grafico else f"#{assunto}",
                )
            )
        if not blocos:
            continue
        saida.append(
            Pergunta(
                id=d.id,
                titulo=d.titulo,
                resposta=d.resposta,
                numeros=no_topo,
                blocos=blocos,
            )
        )
    return saida


def itens(perguntas: list[Pergunta]) -> list[ItemPergunta]:
    return [ItemPergunta(id=p.id, titulo=p.titulo, resposta=p.resposta) for p in perguntas]
