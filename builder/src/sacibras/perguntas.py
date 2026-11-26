"""As perguntas: a entrada do site (Caio, 16/11/2026: *"o gancho vai ser problemas e
perguntas que as pessoas buscam algum tipo de resposta, vamos evitar mostrar só o dado pelo
dado [...] mostrar o dado que responde uma pergunta ou problema"*).

Cada pergunta tem uma resposta curta, os números de hoje que a sustentam e de três a seis
explicações, na ordem em que contam a história, e fecha com a conclusão. **Claro onde a
evidência é clara, em aberto onde ela é fraca** (Caio, 16/11/2026: *"não precisa ser
completamente neutro [...] é melhor ser mais claro do que deixar implícito pra
interpretação"*; e, no mesmo dia: *"também não podemos afirmar oq não se sustenta, se a
evidência for fraca, melhor deixar mais em aberto mesmo [...] vamos ser claros quando a
evidência é clara"*). Três degraus, e o texto diz em qual está: o que o dado do painel
mostra (afirma-se); o que é conta ou regra (afirma-se); e o que é causa, peso de cada causa
ou efeito de política (diz-se que é plausível, disputado ou que os dados daqui não decidem).
Sem adjetivo de torcida e sem número que o painel não tem. Ao lado de cada explicação vai o
número e o gráfico do painel que a sustenta.

**As respostas falam do momento** ("ainda não", "do jeito que está, não"): valem enquanto o
dado disser o mesmo. `LIDAS_EM` e a linha em `leituras.py` marcam quando reler.

Nada aqui é dado novo: os cartões e gráficos são os dos assuntos, copiados com a data e a
fonte deles; o que faltar numa rodada simplesmente não aparece.

Regra do orçamento de atenção: até 3 números na resposta, até 6 explicações, até 2 números
e 1 gráfico por explicação.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sacibras.schema import BlocoPergunta, Cartao, Grafico, ItemPergunta, Pergunta, Tabela

LIDAS_EM = "19/11/2026"
"""Quando as respostas e conclusões foram escritas contra o dado (ver `leituras.py`)."""

MAXIMO_DE_NUMEROS = 3
MAXIMO_DE_BLOCOS = 6

Ref = tuple[str, str]
"""(assunto, id do cartão ou do gráfico). O assunto pode ser o Laboratório (Caio, 19/11/2026:
*"Faz tudo, eu aprovo"*, sobre a pergunta da crise copiar peça de lá): o texto do bloco diz
então "estimativa nossa". O id pode acabar em "*": vale o primeiro que
começa assim (os cartões do Focus levam o ano no id)."""


@dataclass(frozen=True)
class Bloco:
    titulo: str
    texto: str
    grafico: Ref | None = None
    numeros: tuple[Ref, ...] = ()
    tabela: Ref | None = None


@dataclass(frozen=True)
class Definicao:
    id: str
    titulo: str
    resposta: str
    numeros: tuple[Ref, ...]
    blocos: tuple[Bloco, ...]
    palavras: tuple[str, ...] = field(default=())
    """Como alguém procuraria a pergunta na busca."""
    conclusao: str = ""
    """Juntando as peças: o que a história contada torna mais provável."""


TEMAS: tuple[tuple[str, str], ...] = (
    ("precos-juros", "Preços e juros"),
    ("crescimento-renda", "Crescimento, emprego e renda"),
    ("contas-publicas", "Governo: dívida e gasto"),
    ("impostos", "Impostos"),
    ("mercado-riscos", "Mercado e riscos"),
)
"""As perguntas se agrupam por tema na entrada, no menu e no pé de cada pergunta (Caio,
19/11/2026: *"podemos incluir mais perguntas com o tempo, entao é bom ter uma sessão própria
ou organizar melhor as perguntas dentro dos temas"*). Não há mais teto para o total: o teto é
por tema (`MAXIMO_POR_TEMA`). Tema cheio pede tema novo ou juntar duas perguntas: com a do
Simples (26/11/2026), Governo estava cheio e os Impostos viraram tema próprio."""
MAXIMO_POR_TEMA = 6
TEMA_DE: dict[str, str] = {
    "juro-alto": "precos-juros",
    "inflacao": "precos-juros",
    "crescimento": "crescimento-renda",
    "emprego": "crescimento-renda",
    "desigualdade": "crescimento-renda",
    "divida": "contas-publicas",
    "imposto": "impostos",
    "simples": "impostos",
    "cortar-gasto": "contas-publicas",
    "servidores": "contas-publicas",
    "estatais": "contas-publicas",
    "manter-estatais": "contas-publicas",
    "mercado": "mercado-riscos",
    "crise": "mercado-riscos",
}
"""O tema de cada pergunta (o teste confere que toda pergunta tem um)."""

PERGUNTAS: tuple[Definicao, ...] = (
    Definicao(
        "juro-alto",
        "Por que o juro é tão alto?",
        "Duas causas têm apoio claro nos dados: a inflação acima da meta, que segura a Selic,"
        " e a dívida alta e crescente, que encarece o juro longo. Pouca poupança e o juro de "
        "fora também contam, com evidência menos direta.",
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
                "O Brasil poupa menos que a América Latina, os emergentes e os países "
                "ricos. Com pouco dinheiro para emprestar, ele fica mais caro.",
                ("atividade", "poupanca-paises"),
                (("atividade", "poupanca-brasil-fmi"),),
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
        conclusao=(
            "Enquanto a dívida subir e a inflação esperada ficar acima da meta, o mais provável é"
            " o juro seguir alto. Quanto cada causa pesa, ninguém mede com precisão: o que os "
            "dados mostram é que as duas primeiras estão presentes hoje."
        ),
    ),
    Definicao(
        "divida",
        "A dívida pública se sustenta?",
        "Do jeito que está, não: com o juro e o crescimento de hoje, a dívida sobe todo ano. "
        "Se o juro cair, o esforço para estabilizá-la fica bem menor.",
        (("fiscal", "dbgg"), ("riscos", "primario-estabiliza"), ("fiscal", "primario")),
        (
            Bloco(
                "Quanto falta para ela parar de subir",
                "Com o juro de hoje, pediria um superávit acima de qualquer um desde 2006. "
                "A tabela refaz a conta com juro menor e mais crescimento.",
                ("riscos", "primario-necessario"),
                (("riscos", "primario-estabiliza"), ("fiscal", "primario")),
                ("riscos", "primario-conforme-o-juro"),
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
        conclusao=(
            "A dívida é em reais, e deixar de pagá-la é o desfecho menos provável. A conta diz "
            "que ela sobe até haver ajuste. Se o ajuste baixaria o juro, a história brasileira "
            "sugere que sim, mas isso não se mede de antemão."
        ),
    ),
    Definicao(
        "crescimento",
        "Por que o Brasil cresce pouco?",
        "Porque cada trabalhador produz quase o mesmo que há décadas. O país cresceu pondo "
        "mais gente para trabalhar, o que está acabando, e investe menos que os parecidos: "
        "isso os dados mostram com clareza.",
        (("atividade", "pib-4t"), ("longo-prazo", "produtividade"), ("longo-prazo", "ptf-eua")),
        (
            Bloco(
                "A eficiência parou",
                "A eficiência (PTF) é o quanto se produz com o mesmo trabalho e as mesmas "
                "máquinas. É ela que separa os países ricos dos outros.",
                ("longo-prazo", "ptf-brasil"),
                (("longo-prazo", "ptf-eua"), ("longo-prazo", "ptf-desde-o-pico")),
            ),
            Bloco(
                "Mais gente, não mais produto por pessoa",
                "O crescimento pode vir de mais gente ocupada ou de cada um produzir mais. "
                "Só o segundo aumenta a renda de cada pessoa.",
                ("longo-prazo", "crescimento-decomposto"),
                (("longo-prazo", "produtividade"),),
            ),
            Bloco(
                "Investe-se pouco",
                "O Brasil investe menos que a América Latina, os emergentes e os países "
                "ricos. Sem máquinas, estradas e fábricas novas, ninguém produz mais.",
                ("atividade", "investimento-paises"),
                (("atividade", "investimento-brasil-fmi"),),
            ),
            Bloco(
                "A população que trabalha para de crescer",
                "Com menos filhos por mulher, a população de 15 a 64 anos cresce cada vez "
                "menos: daqui para a frente, crescer depende de produtividade.",
                ("longo-prazo", "crescimento-15-64"),
                (("longo-prazo", "populacao-15-64"), ("longo-prazo", "fecundidade")),
            ),
            Bloco(
                "A escola",
                "Mais anos de estudo, e estudo melhor, aumentam o que cada trabalhador "
                "produz e ganha.",
                ("longo-prazo", "renda-escolaridade"),
                (("longo-prazo", "anos-de-estudo"),),
            ),
        ),
        ("pib baixo", "crescimento econômico", "produtividade", "renda média"),
        conclusao=(
            "Com a população em idade de trabalhar parando de crescer, o Brasil só cresce mais se"
            " cada trabalhador produzir mais: isso é conta. O que faz a produtividade subir é "
            "disputado, e os dados daqui não decidem."
        ),
    ),
    Definicao(
        "inflacao",
        "A inflação está sob controle?",
        "Ainda não: o IPCA está acima do teto da meta, os serviços correm mais que o resto e "
        "analistas e títulos esperam inflação acima da meta. O sinal bom é o ritmo recente "
        "dos núcleos, mais baixo que o de 12 meses.",
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
        conclusao=(
            "Com a inflação e as expectativas acima da meta, o mais provável é o Banco Central "
            "manter o juro alto: é o que ele diz e o que fez no passado. Se o ritmo mais baixo "
            "dos núcleos vai durar, três meses de dado não bastam para dizer."
        ),
    ),
    Definicao(
        "imposto",
        "Para onde vai o imposto, e quem paga?",
        "O Brasil arrecada como país rico, mas cobra sobretudo no consumo, que pesa mais em "
        "quem ganha menos. O dinheiro vai principalmente para a previdência e os juros.",
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
                "A União arrecada sete em cada dez reais e gasta mais com previdência e juros; "
                "estados e municípios, com saúde, educação e, nos estados, segurança.",
                ("fiscal", "despesa-composicao"),
                (("impostos", "carga-uniao"), ("fiscal", "previdencia-rgps")),
                ("impostos", "despesa-esferas"),
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
                ("trabalho", "irpf-topo-tempo"),
                (("trabalho", "irpf-topo-renda"), ("trabalho", "irpf-topo-dividendos")),
            ),
            Bloco(
                "O que muda com a reforma",
                "A reforma troca cinco impostos sobre o consumo (PIS, Cofins, IPI, ICMS e "
                "ISS) por dois (CBS e IBS), cobrados onde se consome.",
                ("impostos", "reforma-transicao"),
                (("impostos", "reforma-aliquota-cheia"),),
            ),
        ),
        (
            "carga tributária",
            "quem paga imposto",
            "gasto público",
            "reforma tributária",
            "imposto da União, dos estados e dos municípios",
        ),
        conclusao=(
            "A reforma do consumo simplifica a cobrança, mas não muda o peso entre consumo e "
            "renda: isso está na lei. Cobrar mais da renda ou rever isenções mudaria quem paga; o"
            " efeito sobre investimento e emprego é disputado."
        ),
    ),
    Definicao(
        "cortar-gasto",
        "Onde dá para cortar gasto?",
        "Sem mudar lei, em pouco: só cerca de um real em cada dez da despesa federal é "
        "discricionário. Contra os outros países, o Brasil gasta mais em proteção social e "
        "juros, e menos em infraestrutura.",
        (
            ("fiscal", "discricionaria-parte"),
            ("fiscal", "previdencia-rgps"),
            ("fiscal", "gasto-acima-pares"),
        ),
        (
            Bloco(
                "Quase tudo já tem destino",
                "A despesa obrigatória sobe há anos e espreme a discricionária, que é a única "
                "que o governo corta no orçamento.",
                ("fiscal", "despesa-rigidez"),
                (("fiscal", "discricionaria-parte"),),
                ("fiscal", "despesa-obrigatoria"),
            ),
            Bloco(
                "A previdência é a maior conta",
                "Os benefícios do INSS levam mais de quatro em cada dez reais da despesa "
                "federal, e crescem com o número de idosos.",
                ("fiscal", "despesa-composicao"),
                (("fiscal", "previdencia-rgps"), ("longo-prazo", "idosos-por-100")),
            ),
            Bloco(
                "Contra os outros países",
                "No governo todo (União, estados e municípios), o Brasil gasta em proteção "
                "social como país rico, e em pensão por morte e juros bem acima de todos.",
                None,
                (("fiscal", "gasto-acima-pares"),),
                ("fiscal", "gasto-por-funcao"),
            ),
            Bloco(
                "A folha dos servidores",
                "A folha de quem está na ativa pesa mais no Brasil que na mediana dos "
                "emergentes, e a maior parte dela é de estados e municípios.",
                ("fiscal", "folha-por-esfera"),
                (("fiscal", "folha-ativos-pib"), ("fiscal", "folha-inativos")),
                ("fiscal", "folha-paises"),
            ),
            Bloco(
                "O que se deixa de arrecadar também é gasto",
                "Isenções e regimes especiais custam como despesa, mas não passam pelo "
                "orçamento de cada ano.",
                ("impostos", "gasto-tributario"),
                (("impostos", "gasto-tributario"),),
            ),
            Bloco(
                "Os juros",
                "Os juros não são despesa primária e não se cortam por decisão: caem com a "
                "Selic e com a confiança de quem empresta.",
                ("riscos", "juros-sobre-receita"),
                (("riscos", "juros-sobre-receita"), ("fiscal", "juros-divida")),
            ),
        ),
        (
            "cortar gastos",
            "corte de gastos",
            "gasto público",
            "despesa obrigatória",
            "ajuste fiscal",
        ),
        conclusao=(
            "Os dados mostram que a margem do orçamento é estreita e que o gasto acima dos "
            "outros países está na proteção social e nos juros. Onde cortar é escolha política;"
            " se cada real é bem gasto, estes números não medem."
        ),
    ),
    Definicao(
        "servidores",
        "Servidor público ganha mais que quem trabalha no setor privado?",
        "Na média, sim: o estatutário ganha cerca do dobro do empregado com carteira, e o "
        "federal se aposenta com várias vezes a média do INSS. Quanto disso vem de mais "
        "escola, estes dados não separam.",
        (
            ("fiscal", "servidor-rendimento"),
            ("fiscal", "aposentadoria-servidor"),
            ("fiscal", "folha-ativos-pib"),
        ),
        (
            Bloco(
                "O contracheque",
                "O rendimento médio de quem trabalha para o governo e de quem trabalha para "
                "empresa, com e sem carteira, já descontada a inflação.",
                ("fiscal", "rendimento-publico-privado"),
                (("fiscal", "servidor-rendimento"),),
                ("fiscal", "rendimento-por-posicao"),
            ),
            Bloco(
                "A aposentadoria",
                "O servidor federal aposentado recebe, em média, bem acima do teto do INSS; "
                "no INSS, a maioria das aposentadorias fica perto do salário mínimo.",
                None,
                (("fiscal", "aposentadoria-servidor"), ("fiscal", "folha-inativos")),
                ("fiscal", "aposentadoria-publico-privado"),
            ),
            Bloco(
                "Quem fica com mais: os poderes",
                "Na União, o Executivo leva a maior parte da folha porque tem mais gente; "
                "as médias mais altas são do Legislativo, do Ministério Público e do Judiciário.",
                ("fiscal", "folha-uniao"),
                (),
                ("fiscal", "remuneracao-por-poder"),
            ),
            Bloco(
                "Quem fica com mais: as esferas",
                "Mais da metade do gasto com servidores é de estados e municípios, onde "
                "estão os professores, os policiais e a maior parte da saúde.",
                ("fiscal", "folha-por-esfera"),
                (),
                ("fiscal", "folha-quem-fica"),
            ),
            Bloco(
                "O Brasil e os outros países",
                "A folha da ativa do governo todo, em relação ao PIB, contra a mediana dos "
                "emergentes, da América Latina e dos países ricos.",
                None,
                (("fiscal", "folha-ativos-pib"),),
                ("fiscal", "folha-paises"),
            ),
        ),
        (
            "salário de servidor",
            "funcionário público",
            "funcionalismo",
            "supersalários",
            "aposentadoria de servidor",
            "folha de pagamento do governo",
        ),
        conclusao=(
            "O servidor ganha mais na média e se aposenta com mais: isso os dados mostram. Se "
            "ganha mais que alguém com a mesma formação no setor privado, eles não decidem. As "
            "médias mais altas são do Legislativo, do Ministério Público e do Judiciário."
        ),
    ),
    Definicao(
        "estatais",
        "As estatais dão lucro ou prejuízo aos cofres públicos?",
        "As federais dão à União mais do que recebem desde 2021, por causa de quatro "
        "empresas; o saldo de 2025 foi o menor em cinco anos. Nas estaduais é o contrário: "
        "de 2021 a 2024, os estados puseram mais do que receberam.",
        (
            ("fiscal", "estatais-saldo"),
            ("fiscal", "dividendos-12m"),
            ("fiscal", "estatais-primario"),
        ),
        (
            Bloco(
                "O que entra e o que sai",
                "De um lado, os dividendos que a União recebe; do outro, a subvenção e o "
                "capital que ela põe nas estatais. A diferença é o saldo do ano.",
                ("fiscal", "estatais-conta"),
                (("fiscal", "estatais-saldo"),),
                ("fiscal", "estatais-conta"),
            ),
            Bloco(
                "Quatro empresas pagam quase tudo",
                "BNDES, Petrobras, Banco do Brasil e Caixa. O dividendo acompanha o lucro "
                "delas, que sobe e desce com o petróleo e com o crédito.",
                ("fiscal", "dividendos-por-empresa"),
                (("fiscal", "dividendos-12m"),),
                ("fiscal", "estatais-lucro"),
            ),
            Bloco(
                "As que vivem do orçamento",
                "As estatais dependentes recebem do Tesouro para pagar pessoal e custeio. "
                "São na maior parte hospitais, pesquisa e obras: não vendem o que fazem.",
                None,
                (("fiscal", "estatais-subvencao"),),
                ("fiscal", "estatais-subvencoes"),
            ),
            Bloco(
                "As que gastam mais do que arrecadam",
                "Sem os bancos, a Petrobras e a Eletrobras, as estatais federais fecham no "
                "vermelho, e esse déficit entra na conta do setor público.",
                ("fiscal", "estatais-primario"),
                (("fiscal", "estatais-primario"),),
            ),
            Bloco(
                "E as dos estados",
                "Somadas, receberam dos estados mais do que pagaram em dividendos em todos os "
                "anos desde 2021. São números declarados pelos próprios estados.",
                ("fiscal", "estatais-estados"),
                (),
                ("fiscal", "estatais-estados-uf"),
            ),
        ),
        (
            "estatais dão prejuízo",
            "estatais estaduais",
            "lucro das estatais",
            "dividendos da Petrobras",
            "prejuízo dos Correios",
            "privatização",
            "empresas públicas",
        ),
        conclusao=(
            "Como caixa, as federais ajudam a União, apoiadas em poucas empresas, e as "
            "estaduais custam aos estados. Se vale a pena ser dono delas, estes dados não medem."
        ),
    ),
    # Caio, 25/11/2026: "Adicione agora uma pergunta no painel: Vale manter as estatais? Bem
    # provocativo mesmo, mostrando os dados que podem sustentar uma conclusão ou outra, pode
    # avaliar vc pelos dados, eu acho que não". A régua é o juro da dívida: vender e abater
    # dívida pouparia esse juro. Lido em 25/11/2026 contra a Sest (edição 2026) e o BC: em
    # 2025, 11 das 27 não dependentes renderam acima de 12,7 % (Petrobras, BNDES, BNB, Basa,
    # Finep, Porto de Santos, Serpro, Dataprev, Infraero, NAV, PPSA), cerca de 60 % do
    # patrimônio delas; BB (9,3 %) e Caixa (10,7 %) ficaram abaixo; a Petrobras ficou abaixo
    # em 2024 (10,1 % contra 10,7 %). O preço de venda não está no painel (viria da bolsa).
    # Depois (mesmo dia: "Compare com oq poderia ser investido ao invés delas"): de 2021 a
    # 2025, R$ 100 viraram R$ 260 nas não dependentes somadas (R$ 199 sem a Petrobras),
    # R$ 168 no CDI, R$ 166 abatendo dívida e R$ 146 no Tesouro IPCA+; em 2025, sem a
    # Petrobras, 10,3 % contra 14,3 % do CDI. Em 26/11/2026 (Caio: "a média não faz
    # sentido"), empresa a empresa: em 2025, os três maiores lucros (Petrobras 110,6, BNDES
    # 25,6, BB 17,8: R$ 154 bi) e os três maiores custos, com a subvenção (Ebserh 13,8,
    # Correios 8,5, Embrapa 4,8: R$ 27 bi). De 2021 a 2025: Petrobras R$ 358, BNDES R$ 256,
    # BB R$ 209, Caixa R$ 165, CDI R$ 168, abater dívida R$ 166. E por dentro (mesmo dia: "Ver
    # quais foram os maiores custos dela"), pela DVA da Sest, em 2025: a folha levou 81 % dos
    # recursos nos Correios (54 % em 2024), 75 % na Embrapa, 72 % na Ebserh; 6 % na
    # Petrobras (compras 38 %, impostos 27 %), 4 % no BNDES e 9 % no BB (juros 58 % e 76 %).
    Definicao(
        "manter-estatais",
        "Vale manter as estatais?",
        "Não todas. Em 2025, Petrobras, BNDES e Banco do Brasil lucraram R$ 154 bi; Ebserh, "
        "Correios e Embrapa custaram R$ 27 bi. Só 11 das 27 que vivem do que vendem renderam "
        "mais que o juro da dívida.",
        (
            ("fiscal", "estatais-saldo"),
            ("fiscal", "estatais-subvencao"),
            ("fiscal", "dividendos-12m"),
        ),
        (
            Bloco(
                "Uma a uma: quem lucra e quem custa",
                "Três lucram muito e três custam muito. Nas dependentes, o custo é a subvenção "
                "do Tesouro; nos Correios, o prejuízo, que pode virar aporte da União.",
                ("fiscal", "estatais-ranking"),
                (),
                ("fiscal", "estatais-ranking"),
            ),
            Bloco(
                "Por dentro: o que mais pesa",
                "Nas três que mais custam, a folha leva de 72 % a 81 % do dinheiro; nas que "
                "mais lucram, menos de 10 %. Lá pesam compras e impostos (Petrobras) e juros "
                "(bancos).",
                ("fiscal", "estatais-custos"),
                (),
                ("fiscal", "estatais-custos"),
            ),
            Bloco(
                "Vender e pagar dívida compensaria?",
                "Depende do preço. Pelos números de 2025, cada R$ 100 de patrimônio teria de "
                "sair por mais de R$ 73 (Banco do Brasil), R$ 84 (Caixa), R$ 117 (BNDES) ou "
                "R$ 209 (Petrobras).",
                ("fiscal", "estatais-retorno"),
                (),
                ("fiscal", "estatais-retorno"),
            ),
            Bloco(
                "E se o dinheiro fosse aplicado?",
                "Pelo lucro contábil, Petrobras, BNDES e Banco do Brasil renderam mais que CDI, "
                "Tesouro ou abater dívida de 2021 a 2025; a Caixa empatou com a dívida.",
                ("fiscal", "estatais-alternativas"),
                (),
                ("fiscal", "estatais-alternativas"),
            ),
            Bloco(
                "A favor de manter: poucas pagam a conta",
                "Desde 2021, os dividendos superam o que a União põe nas estatais. Quase tudo "
                "vem de quatro empresas; vendê-las acaba com essa renda.",
                ("fiscal", "dividendos-por-empresa"),
                (("fiscal", "dividendos-12m"),),
                ("fiscal", "estatais-lucro"),
            ),
            Bloco(
                "Contra: as que vivem do orçamento",
                "Hospitais, pesquisa e obras, pagos pelo Tesouro. Vender não acaba com o gasto: "
                "o serviço iria ao orçamento ou acabaria. Estes dados não decidem.",
                None,
                (("fiscal", "estatais-subvencao"),),
                ("fiscal", "estatais-subvencoes"),
            ),
        ),
        (
            "privatização",
            "privatizar",
            "vender as estatais",
            "vale manter estatais",
            "Petrobras privatizar",
            "Correios privatização",
            "estatal dá lucro",
        ),
        conclusao=(
            "Manter as 44 não se sustenta: muitas rendem menos que o juro da dívida, dão "
            "prejuízo ou vivem do orçamento. Três grandes renderam mais do que o dinheiro "
            "aplicado, pelo lucro contábil; vendê-las só compensa se o preço pagar mais que "
            "isso, e estes dados não o medem."
        ),
    ),
    Definicao(
        "emprego",
        "O emprego está bom mesmo?",
        "Está, pelos números: a desocupação está entre as menores da série e a renda sobe. O "
        "ponto fraco é a qualidade, com quase quatro em cada dez trabalhando sem carteira.",
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
        conclusao=(
            "O emprego vai bem em quantidade e em renda, e segue fraco em proteção: isso os dados"
            " mostram. Se o desemprego baixo está segurando a inflação dos serviços, como o Banco"
            " Central costuma dizer, é plausível, mas a ligação entre os dois é incerta."
        ),
    ),
    Definicao(
        "desigualdade",
        "Quem ficou com o crescimento?",
        "Os mais pobres, pelas pesquisas do IBGE: desde 2012 a renda deles cresceu mais que a"
        " dos mais ricos. Mas pelos dados da Receita a concentração no topo segue muito alta.",
        (("trabalho", "fatia-10-ricos"), ("trabalho", "fatia-40-pobres"), ("trabalho", "pobreza")),
        (
            Bloco(
                "Quanto cresceu a renda de cada grupo",
                "A renda dos 40 % de menor renda, do meio e dos 10 % de maior renda, desde 2012.",
                ("trabalho", "renda-por-grupo"),
            ),
            Bloco(
                "Quem fica com quanto",
                "A parte da renda total que vai para cada grupo.",
                ("trabalho", "fatias"),
                (("trabalho", "fatia-10-ricos"), ("trabalho", "fatia-40-pobres")),
            ),
            Bloco(
                "O topo que a pesquisa não vê",
                "Pesquisa de domicílio capta mal as rendas mais altas; a declaração do "
                "imposto de renda mostra esse pedaço.",
                ("trabalho", "irpf-topo-tempo"),
                (("trabalho", "irpf-topo-renda"), ("trabalho", "fatia-1-rico")),
            ),
            Bloco(
                "A pobreza",
                "Quantos vivem abaixo da linha de pobreza e da de extrema pobreza do "
                "Banco Mundial.",
                ("trabalho", "pobreza"),
                (("trabalho", "pobreza"), ("trabalho", "extrema-pobreza")),
            ),
            Bloco(
                "Entre homens e mulheres, brancos e negros",
                "Quanto cada grupo ganha para cada R$ 100 do grupo que ganha mais.",
                ("trabalho", "diferencas"),
            ),
            Bloco(
                "O Brasil e os outros países",
                "O Gini vai de 0 (todos com a mesma renda) a 1 (tudo com um só).",
                ("trabalho", "gini-paises"),
                (("trabalho", "gini"),),
            ),
        ),
        ("desigualdade", "distribuição de renda", "pobreza", "ricos e pobres"),
        conclusao=(
            "A desigualdade caiu na base e pouco mudou no topo, e o Brasil segue entre os países "
            "mais desiguais do mundo: isso é claro. Quanto da melhora veio do emprego, do salário"
            " mínimo ou das transferências, os dados daqui não separam."
        ),
    ),
    # Caio, 26/11/2026: "Temos uma discussão de quanto custa o simples, se vale a pena ou não
    # manter". O custo se mede (gasto tributário da Receita); o retorno em emprego e
    # formalização, nenhuma fonte oficial publica com regularidade, e o texto diz isso.
    Definicao(
        "simples",
        "Quanto custa o Simples, e vale manter?",
        "Custa à União mais de R$ 100 bi por ano, o maior dos gastos tributários. Se vale, "
        "estes dados não decidem: ninguém publica com regularidade quanto emprego e "
        "formalização ele traz.",
        (
            ("impostos", "simples-custo"),
            ("impostos", "simples-optantes"),
            ("impostos", "gasto-tributario"),
        ),
        (
            Bloco(
                "Quanto custa",
                "É o imposto federal que as empresas do Simples e o MEI pagariam a mais nas "
                "regras gerais. Cresce com a economia: perto de 1 % do PIB.",
                ("impostos", "simples-custo"),
                (("impostos", "simples-custo"),),
                ("impostos", "simples-ano"),
            ),
            Bloco(
                "O maior da lista",
                "Nenhuma outra isenção federal custa tanto: o Simples, sozinho, é cerca de um "
                "quinto de tudo o que a União deixa de cobrar.",
                ("impostos", "gasto-tributario"),
                (("impostos", "gasto-tributario"),),
                ("impostos", "gasto-tributario"),
            ),
            Bloco(
                "Para quem, e lá fora",
                "Dois em cada três optantes são MEI. O teto dele, R$ 140 mil em 2028, fica perto "
                "da isenção mediana da OCDE; o do Simples, R$ 4,8 mi, não isenta e não tem par lá.",
                None,
                (("impostos", "simples-optantes"),),
                ("impostos", "reforma-isencao-paises"),
            ),
            Bloco(
                "O que se ganha em troca",
                "A defesa é que ele tira empresas da informalidade e poupa burocracia. É "
                "plausível, mas a informalidade mexe com muita coisa e estes dados não separam "
                "o efeito dele.",
                ("trabalho", "informalidade"),
                (("trabalho", "informalidade"),),
            ),
            Bloco(
                "O que muda com a reforma",
                "O Simples continua, mas quem compra dele abate menos imposto. Por isso a "
                "empresa pode pagar o IBS e a CBS pelas regras gerais e ficar no Simples no "
                "resto.",
                ("impostos", "reforma-transicao"),
                (),
                ("impostos", "reforma-seletivo-simples"),
            ),
        ),
        (
            "simples nacional",
            "mei",
            "microempreendedor individual",
            "pequenas empresas",
            "custo do simples",
            "renúncia fiscal",
            "teto do mei",
        ),
        conclusao=(
            "O custo é claro: mais de R$ 100 bi por ano, perto de 1 % do PIB, a maior isenção "
            "da União. Para o MEI, o limite é parecido com o de fora; a disputa está na faixa "
            "de cima. O ganho em emprego e formalização é plausível, mas sem número oficial "
            'regular: "vale a pena" fica em aberto.'
        ),
    ),
    Definicao(
        "mercado",
        "O que o mercado espera do Brasil?",
        "Juro alto por bastante tempo, inflação acima da meta e crescimento baixo. Os títulos"
        " embutem mais inflação que os analistas, em parte por prêmio de risco.",
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
                (("previsoes", "focus-câmbio-*"), ("externo", "dolar")),
            ),
            Bloco(
                "A dívida",
                "A dívida bruta e a trajetória que o mercado projeta para ela.",
                ("fiscal", "divida"),
                (("fiscal", "dbgg"),),
            ),
        ),
        ("expectativas", "focus", "previsão", "curva de juros", "o dólar vai subir"),
        conclusao=(
            "Analistas e títulos apontam para o mesmo lado. Mas as duas medidas erram: o erro "
            "do Focus está na entrada do site, e quanto do juro dos títulos é risco não se "
            "separa com precisão."
        ),
    ),
    Definicao(
        "crise",
        "De onde viria uma crise?",
        "Pelos dados daqui, o ponto fraco são as contas públicas, não as externas nem os "
        "bancos: a dívida sobe e não se espera que pare. Os dados mostram onde está a pressão,"
        " não se nem quando ela vira crise.",
        (
            ("fiscal", "dbgg"),
            ("riscos", "juro-real-brasil-eua"),
            ("laboratorio", "dolar-do-brasil"),
        ),
        (
            Bloco(
                "A dívida sobe e não se espera que pare",
                "A cada dezembro, a aposta dos analistas para a dívida dos anos seguintes. "
                "Hoje, ela sobe até onde a coleta vai.",
                ("laboratorio", "divida-esperada"),
                (("laboratorio", "divida-esperada"), ("riscos", "primario-estabiliza")),
            ),
            Bloco(
                "O ajuste esperado costuma ficar maior que o entregue",
                "Desde 2003, o primário esperado dois anos antes foi, na média, maior que o que"
                " veio, em parte por choques como 2020. Estimativa nossa, com faixa de erro.",
                ("laboratorio", "primario-prometido"),
                (("laboratorio", "primario-prometido"), ("fiscal", "primario")),
            ),
            Bloco(
                "O Brasil paga mais que os outros para dever",
                "A distância para o juro real dos EUA é o que se cobra a mais do Brasil. O "
                "número não diz por quê.",
                ("riscos", "juro-real-brasil-eua"),
                (("riscos", "juros-sobre-receita"),),
            ),
            Bloco(
                "No dólar, quanto é daqui",
                "Dólar que sobe contra todas as moedas é problema de fora; o resto é do Brasil,"
                " sem dizer de qual causa. Estimativa nossa.",
                ("laboratorio", "dolar-mundo-brasil"),
                (("laboratorio", "dolar-de-fora"),),
            ),
            Bloco(
                "Dólar para pagar as contas de fora, há",
                "As reservas cobrem com sobra a dívida externa de um ano, e o investimento "
                "direto supera o déficit externo.",
                ("externo", "reservas"),
                (("riscos", "reservas-cobertura"), ("externo", "transacoes-correntes")),
            ),
            Bloco(
                "O que o painel de alerta mostra",
                "Cada indicador na régua da própria história, e quantos estão no quinto pior. "
                "Não é nota única nem previsão de crise.",
                ("riscos", "basileia"),
                (("riscos", "alertas-acesos"), ("riscos", "basileia")),
            ),
        ),
        ("crise", "risco de crise", "o brasil vai quebrar", "crise fiscal", "crise cambial"),
        conclusao=(
            "Se a pressão crescer, o caminho mais provável pelos dados é o das contas "
            "públicas, não falta de dólares nem bancos frágeis. Se o ajuste será feito, e até "
            "quando o mercado espera, os dados daqui não decidem."
        ),
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
    cartoes: dict[Ref, Cartao],
    graficos: dict[Ref, Grafico],
    titulos: dict[str, str],
    tabelas: dict[Ref, Tabela] | None = None,
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
                    # Na pergunta, só a peça escolhida: a lista das parecidas fica nos Dados.
                    grafico=(
                        grafico.model_copy(update={"secao": assunto, "alternativas": []})
                        if grafico
                        else None
                    ),
                    tabela=(
                        tabela.model_copy(update={"alternativas": []})
                        if b.tabela and (tabela := (tabelas or {}).get(b.tabela))
                        else None
                    ),
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
                conclusao=d.conclusao,
            )
        )
    return saida


def itens(perguntas: list[Pergunta]) -> list[ItemPergunta]:
    """As perguntas para a entrada e o menu, na ordem dos temas."""
    nomes = dict(TEMAS)
    ordem = {tema: i for i, tema in enumerate(nomes)}
    saida = [
        ItemPergunta(
            id=p.id,
            titulo=p.titulo,
            resposta=p.resposta,
            tema=nomes.get(TEMA_DE.get(p.id, ""), ""),
        )
        for p in perguntas
    ]
    posicao = {p.id: ordem.get(TEMA_DE.get(p.id, ""), len(ordem)) for p in perguntas}
    return sorted(saida, key=lambda q: posicao[q.id])
