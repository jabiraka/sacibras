"""O glossário do site (`glossario.json`): cada termo com uma definição curta, em palavras de
todo dia, e as formas como ele aparece no texto.

Pedido do Caio (14/11/2026): *"para as pessoas entenderem ao clicar em um conceito, se elas
não souberem uma palavra ou termo, ela clica ou na palavra ou em um ? que abre a definição
dela, não precisa abrir uma página nova, só um balão"*. O navegador procura as `formas` no
texto da tela (a primeira vez em cada bloco), sublinha a palavra e põe um "?" ao lado do
rótulo dos números e do título dos gráficos; o toque abre o balão.

Regras do texto: até três frases, sem jargão que precise de outro verbete, e número de lei
só de norma já lida (`leis.py`). Forma com duas letras maiúsculas ou mais (IPCA, PIB) só
casa com a mesma caixa; as outras casam com qualquer caixa. A forma mais longa ganha:
"juro real" antes de "juro", "dívida bruta do governo geral" antes de "dívida bruta".
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel


@dataclass(frozen=True)
class Termo:
    id: str
    nome: str
    definicao: str
    formas: tuple[str, ...]
    elo: str = ""
    """Onde ver no painel ("#inflacao/nucleos"); vazio quando não há um lugar só."""


TERMOS: list[Termo] = [
    # ---------------------------------------------------------------- atividade
    Termo(
        "pib",
        "PIB",
        "Produto Interno Bruto: o valor de todos os bens e serviços finais produzidos no país "
        "num período. O crescimento do PIB é a variação sem o efeito dos preços (em volume).",
        ("PIB", "Produto Interno Bruto"),
        "#atividade",
    ),
    Termo(
        "ibc-br",
        "IBC-Br",
        "Índice de Atividade Econômica do Banco Central: um termômetro mensal da economia, "
        "feito com dados de indústria, comércio, serviços e agropecuária. Serve de prévia do "
        "PIB, que só sai por trimestre.",
        ("IBC-Br",),
        "#atividade",
    ),
    Termo(
        "ibc-r",
        "IBC-R",
        "O IBC-Br feito para um estado: a prévia mensal do PIB que o Banco Central publica "
        "para 13 estados. O PIB oficial de cada estado, do IBGE, sai quase dois anos depois.",
        ("IBC-R",),
        "#estados/mapa",
    ),
    Termo(
        "contas-regionais",
        "Contas Regionais",
        "O PIB de cada estado, calculado pelo IBGE com os órgãos de estatística estaduais. "
        "Sai uma vez por ano, com quase dois anos de atraso: o de 2024 saiu em novembro de "
        "2026.",
        ("Contas Regionais",),
        "#estados/mapa",
    ),
    Termo(
        "ajuste-sazonal",
        "Ajuste sazonal",
        "Correção do que se repete todo ano na mesma época (Natal, safra, férias), para "
        "comparar um mês com o anterior. Sem ajuste, compara-se com o mesmo mês do ano "
        "anterior.",
        ("ajuste sazonal", "dessazonalizado", "dessazonalizada", "dessazonalizados"),
    ),
    Termo(
        "investimento-pib",
        "Taxa de investimento",
        "O que o país gasta em máquinas, construções e infraestrutura (a formação bruta de "
        "capital fixo) em proporção do PIB. É o que aumenta a capacidade de produzir no futuro.",
        ("taxa de investimento", "formação bruta de capital", "FBCF"),
        "#atividade/investimento",
    ),
    Termo(
        "demanda-privada",
        "Demanda privada",
        "O consumo das famílias somado ao investimento (FBCF): o que famílias e empresas gastam "
        "dentro do país, sem o governo, os estoques e o exterior. Varia menos que o PIB e "
        "mostra melhor a força da economia.",
        ("demanda privada",),
        "#atividade/pib",
    ),
    Termo(
        "pib-oferta",
        "PIB pela oferta",
        "O PIB visto por quem produz: agropecuária, indústria e serviços. Pela demanda, é o "
        "mesmo PIB visto por quem gasta: famílias, empresas, governo e exterior.",
        ("PIB pela oferta", "pela oferta"),
        "#atividade/pib",
    ),
    Termo(
        "poupanca-pib",
        "Taxa de poupança",
        "A parte da renda do país que não vira consumo, em proporção do PIB. Se o país investe "
        "mais do que poupa, a diferença vem do exterior.",
        ("taxa de poupança",),
        "#atividade/investimento",
    ),
    Termo(
        "produtividade",
        "Produtividade",
        "Quanto cada pessoa que trabalha produz, em média. Aqui, o PIB dividido pelo número de "
        "ocupados ou pelas horas que eles trabalham. No longo prazo, é o que faz a renda subir.",
        ("produtividade", "PIB por ocupado", "PIB por pessoa ocupada", "PIB por hora trabalhada"),
        "#demografia",
    ),
    Termo(
        "ptf",
        "PTF (produtividade total dos fatores)",
        "O quanto o país produz além do que explicam as máquinas, as horas trabalhadas e o "
        "estudo de quem trabalha: tecnologia, organização, gente e capital no lugar certo. É "
        "calculada como o que sobra da conta, por isso também sobe e desce com o ciclo.",
        ("PTF", "produtividade total dos fatores", "eficiência da economia"),
        "#demografia/eficiencia",
    ),
    Termo(
        "capital-humano",
        "Capital humano",
        "O estudo de quem trabalha visto como um fator de produção. Na Penn World Table, um "
        "índice feito dos anos de estudo da população e do quanto cada ano a mais costuma "
        "render no salário.",
        ("capital humano",),
        "#demografia/eficiencia",
    ),
    Termo(
        "parte-do-trabalho",
        "Parte do trabalho na renda",
        "Quanto da renda do país fica com quem trabalha (salários e o ganho dos autônomos com "
        "o próprio trabalho); o resto remunera o capital: lucros, juros e aluguéis.",
        ("parte do trabalho na renda",),
        "#mundo",
    ),
    Termo(
        "pwt",
        "Penn World Table",
        "Base de dados da Universidade de Groningen com PIB, capital, horas, estudo e PTF de "
        "185 países desde 1950, com o mesmo método para todos. Sai a cada dois anos, mais ou "
        "menos, sob licença aberta (CC BY 4.0).",
        ("Penn World Table", "PWT"),
        "#demografia/eficiencia",
    ),
    Termo(
        "ibge",
        "IBGE",
        "O Instituto Brasileiro de Geografia e Estatística, do governo federal: faz o PIB, o "
        "IPCA, a PNAD Contínua, o censo e as projeções da população.",
        ("IBGE",),
    ),
    Termo(
        "pmc-pms-pim",
        "PMC, PMS e PIM",
        "As pesquisas mensais do IBGE com as empresas: a PMC mede as vendas do comércio, a PMS "
        "a receita dos serviços e a PIM-PF a produção da indústria. Saem antes do PIB e "
        "mostram o mês a mês de cada setor.",
        ("PIM-PF", "PMC", "PMS", "PIM"),
        "#atividade/mes-a-mes",
    ),
    # ---------------------------------------------------------------- trabalho
    Termo(
        "desocupacao",
        "Desocupação",
        "A taxa de desemprego oficial: a parte de quem está na força de trabalho que não tem "
        "trabalho e procurou um nos últimos 30 dias. Vem da PNAD Contínua, do IBGE.",
        ("taxa de desocupação", "desocupação", "desocupados"),
        "#trabalho",
    ),
    Termo(
        "forca-de-trabalho",
        "Força de trabalho",
        "As pessoas de 14 anos ou mais que estão trabalhando ou procurando trabalho. A taxa de "
        "participação é essa parte de toda a população de 14 anos ou mais.",
        ("força de trabalho", "taxa de participação"),
    ),
    Termo(
        "nivel-de-ocupacao",
        "Nível de ocupação",
        "A parte da população de 14 anos ou mais que está trabalhando. Diferente da "
        "desocupação, não depende de quem resolve procurar emprego.",
        ("nível de ocupação",),
    ),
    Termo(
        "subutilizacao",
        "Subutilização",
        "Uma medida mais larga do desemprego: os desocupados, quem trabalha menos horas do que "
        "gostaria e quem poderia trabalhar mas não procurou (os desalentados entre eles).",
        ("subutilização", "subutilizados", "subutilizada"),
    ),
    Termo(
        "desalento",
        "Desalento",
        "Quem queria e podia trabalhar mas desistiu de procurar, por achar que não acharia "
        "vaga (pela idade, por falta de experiência, por não haver trabalho na região).",
        ("desalento", "desalentados", "desalentadas"),
    ),
    Termo(
        "informalidade",
        "Informalidade",
        "Quem trabalha sem carteira assinada, sem CNPJ ou sem a proteção da previdência: "
        "empregados sem carteira, quem trabalha por conta própria ou emprega sem CNPJ, e quem "
        "ajuda a família sem receber.",
        ("informalidade", "informais"),
    ),
    Termo(
        "caged",
        "Caged",
        "O cadastro do Ministério do Trabalho com as contratações e demissões com carteira "
        "assinada, mês a mês. O saldo é contratações menos demissões.",
        ("Novo Caged", "Caged"),
    ),
    Termo(
        "pnad",
        "PNAD Contínua",
        "A Pesquisa Nacional por Amostra de Domicílios Contínua, do IBGE: entrevistas em casas "
        "de todo o país, o ano inteiro. Dá o desemprego oficial, a renda e a informalidade.",
        ("PNAD Contínua", "PNAD"),
    ),
    Termo(
        "rendimento-real",
        "Rendimento real",
        "O que as pessoas ganham, descontada a inflação: mostra se o salário compra mais ou "
        "menos do que antes. A massa de rendimentos é a soma do que todos os ocupados recebem.",
        ("rendimento real", "massa de rendimentos", "massa salarial"),
    ),
    # ---------------------------------------------------------------- inflação
    Termo(
        "ipca",
        "IPCA",
        "Índice Nacional de Preços ao Consumidor Amplo, do IBGE: a inflação oficial do Brasil. "
        "Mede os preços do que as famílias com renda de 1 a 40 salários mínimos compram, nas "
        "principais cidades. É o índice da meta de inflação.",
        ("IPCA",),
        "#inflacao",
    ),
    Termo(
        "meta-de-inflacao",
        "Meta de inflação",
        "O alvo que o Conselho Monetário Nacional fixa e o Banco Central persegue: 3 % no IPCA "
        "de 12 meses, com tolerância de 1,5 ponto para cima (o teto, 4,5 %) e para baixo (o "
        "piso, 1,5 %), conferida mês a mês (Resolução CMN nº 5.141/2024).",
        ("meta de inflação", "teto da meta", "centro da meta", "piso da meta"),
        "#inflacao",
    ),
    Termo(
        "nucleo",
        "Núcleo de inflação",
        "Medidas da inflação que tiram ou suavizam os preços que sobem e descem por motivos "
        "passageiros (alimentos, energia, combustíveis). Mostram a tendência, que é o que o "
        "Banco Central olha para decidir os juros.",
        ("núcleos de inflação", "núcleo de inflação", "núcleos", "núcleo"),
        "#inflacao",
    ),
    Termo(
        "administrados",
        "Preços administrados",
        "Preços fixados ou autorizados pelo governo ou por contrato: energia elétrica, ônibus "
        "urbano, planos de saúde, remédios, água e esgoto, parte dos combustíveis. Os outros "
        "são os preços livres, que seguem a oferta e a procura.",
        ("preços administrados", "administrados"),
    ),
    Termo(
        "livres",
        "Preços livres",
        "Os itens do IPCA cujo preço segue a oferta e a procura, sem governo nem contrato "
        "no meio. O Banco Central os divide em alimentação no domicílio, serviços e bens "
        "industriais.",
        ("preços livres", "itens livres"),
        "#inflacao/grupos",
    ),
    Termo(
        "difusao",
        "Difusão",
        "A parte dos itens do IPCA que ficou mais cara no mês. Alta quer dizer inflação "
        "espalhada, não concentrada em poucos produtos.",
        ("difusão",),
    ),
    Termo(
        "anualizado",
        "Anualizado",
        "Uma variação de poucos meses levada ao ano, como se o mesmo ritmo durasse 12 meses. "
        "Mostra a velocidade recente, mas balança muito de um mês para o outro.",
        ("anualizado", "anualizada", "anualizados", "anualizadas"),
    ),
    Termo(
        "ponto-percentual",
        "Ponto percentual (pp)",
        "A diferença entre duas porcentagens. Se a Selic vai de 10 % para 11 %, subiu 1 ponto "
        "percentual (1 pp), o que é um aumento de 10 % na taxa.",
        ("pontos percentuais", "ponto percentual", "pp"),
    ),
    Termo(
        "nucleo-ex0",
        "Núcleo EX0",
        "Núcleo do Banco Central que deixa de fora os preços administrados e a alimentação no "
        "domicílio: sobra o resto dos preços livres, isto é, serviços e bens industriais.",
        ("EX0",),
        "#inflacao/nucleos",
    ),
    Termo(
        "nucleo-ex3",
        "Núcleo EX3",
        "Núcleo do Banco Central feito só com serviços e bens industriais dos preços livres, "
        "já sem os itens mais voláteis ou de reajuste raro. Fica fora toda a alimentação no "
        "domicílio e os preços administrados.",
        ("EX3",),
        "#inflacao/nucleos",
    ),
    Termo(
        "nucleo-ms",
        "Núcleo MS (médias aparadas)",
        "Todo mês, o Banco Central ordena os itens do IPCA pela alta e tira as pontas: os de "
        "menor alta até somar 20 % do peso e os de maior alta até outros 20 %. A média do que "
        "sobra é o núcleo; itens de reajuste raro, como energia e ônibus, entram pela média "
        "de 12 meses (a suavização).",
        ("médias aparadas",),
        "#inflacao/nucleos",
    ),
    Termo(
        "nucleo-dp",
        "Núcleo DP (dupla ponderação)",
        "A média dos itens do IPCA com o peso de cada um diminuído conforme ele oscila: quem "
        "varia muito de um mês para o outro conta menos. Os dois pesos (o do IPCA e o da "
        "volatilidade) dão o nome.",
        ("dupla ponderação",),
        "#inflacao/nucleos",
    ),
    Termo(
        "nucleo-p55",
        "Núcleo P55 (percentil 55)",
        "Ordenados os subitens do IPCA pela alta do mês, com o peso de cada um, o P55 é a alta "
        "do que fica no ponto de 55 %. É um pouco acima da mediana porque a mediana costuma "
        "ficar abaixo da inflação cheia.",
        ("percentil 55", "P55"),
        "#inflacao/nucleos",
    ),
    Termo(
        "bens-industriais",
        "Bens industriais",
        "Na divisão do Banco Central, os produtos de preço livre que se pegam com a mão e não "
        "são comida para casa: roupa, carro, eletrodoméstico, remédio.",
        ("bens industriais",),
        "#inflacao/grupos",
    ),
    Termo(
        "alimentacao-no-domicilio",
        "Alimentação no domicílio",
        "A comida e a bebida compradas para comer em casa (o subgrupo 11 do IPCA). Comer fora "
        "é outro subgrupo. Oscila muito com safra e clima.",
        ("alimentação no domicílio",),
        "#inflacao/grupos",
    ),
    Termo(
        "ipca-15",
        "IPCA-15",
        "O mesmo IPCA, do IBGE, com preços coletados de meados do mês anterior a meados do mês "
        "de referência. Sai umas duas semanas antes e serve de prévia da inflação oficial.",
        ("IPCA-15",),
        "#inflacao",
    ),
    Termo(
        "inpc",
        "INPC",
        "Índice Nacional de Preços ao Consumidor, do IBGE: a inflação das famílias com renda "
        "de 1 a 5 salários mínimos. Pesa mais comida e menos serviços que o IPCA.",
        ("INPC",),
        "#inflacao/outros-indices",
    ),
    Termo(
        "igp",
        "IGP-M e IGP-DI",
        "Índices gerais de preços da FGV: misturam preços no atacado (a maior parte), ao "
        "consumidor e da construção. Sobem e descem com dólar e commodities. O IGP-M corrige "
        "muitos aluguéis e contratos.",
        ("IGP-M", "IGP-DI", "IGP"),
        "#fiscal/divida",
    ),
    Termo(
        "cmn",
        "CMN",
        "O Conselho Monetário Nacional: o ministro da Fazenda, a ministra ou ministro do "
        "Planejamento e o presidente do Banco Central. Fixa a meta de inflação e as regras do "
        "sistema financeiro.",
        ("Conselho Monetário Nacional", "CMN"),
    ),
    # ---------------------------------------------------------------- juros
    Termo(
        "selic",
        "Selic",
        "A taxa básica de juros da economia, decidida pelo Copom. Puxa os juros dos "
        "empréstimos e das aplicações: subir a Selic esfria o crédito e o consumo para segurar "
        "a inflação.",
        ("Selic meta", "taxa Selic", "Selic"),
        "#juros",
    ),
    Termo(
        "copom",
        "Copom",
        "O Comitê de Política Monetária: a diretoria do Banco Central reunida oito vezes por "
        "ano para decidir a Selic.",
        ("Copom",),
        "#juros",
    ),
    Termo(
        "transmissao",
        "Transmissão da Selic",
        "O caminho da Selic até os preços: ela encarece o crédito e esfria o consumo, barateia "
        "o dólar e mexe com a inflação que as pessoas esperam. Leva tempo: pela conta do Banco "
        "Central, o maior efeito na inflação aparece cerca de um ano depois.",
        ("transmissão da política monetária", "transmissão da Selic"),
        "#juros/efeito",
    ),
    Termo(
        "faixa-de-90",
        "Faixa de 90 %",
        "O intervalo em que, pela conta de quem estimou, o número certo cai em 9 de cada 10 "
        "casos. Quanto mais larga a faixa, menos se sabe sobre o tamanho do efeito.",
        ("faixa de 90 %", "faixas de 90 %"),
        "#juros/efeito",
    ),
    Termo(
        "repasse-cambial",
        "Repasse cambial",
        "Quanto da alta do dólar chega aos preços daqui. O Banco Central estima que um dólar "
        "10 % mais caro põe cerca de 1 ponto a mais no IPCA dos 12 meses seguintes.",
        ("repasse cambial",),
        "#juros/efeito",
    ),
    Termo(
        "ciclo-da-selic",
        "Ciclo da Selic",
        "Uma sequência de reuniões em que o Copom mexe na Selic no mesmo sentido: ciclo de "
        "corte quando ela vai caindo, ciclo de alta quando vai subindo.",
        ("ciclo de corte", "ciclo de alta", "ciclos de corte", "ciclos de alta"),
        "#juros/efeito",
    ),
    Termo(
        "juro-real",
        "Juro real",
        "O juro descontada a inflação: quanto o dinheiro rende, ou custa, em poder de compra. "
        "Juro de 14 % com inflação de 4,5 % dá juro real de cerca de 9 %.",
        ("juro real", "juros reais"),
    ),
    Termo(
        "ex-post",
        "Ex-post",
        "Calculado com a inflação que já aconteceu (a dos 12 meses anteriores), e não com a "
        "que se espera para a frente.",
        ("ex-post",),
    ),
    Termo(
        "cdi",
        "CDI",
        "A taxa dos empréstimos de um dia entre bancos. Anda colada na Selic e é a referência "
        'da renda fixa ("rende 100 % do CDI").',
        ("CDI",),
    ),
    Termo(
        "curva-de-juros",
        "Curva de juros",
        "Os juros de hoje para cada prazo: 1 ano, 2 anos, 10 anos. A curva zero é a mesma "
        "conta feita como se cada título pagasse tudo no vencimento, sem cupons, para dar "
        "para comparar os prazos.",
        ("curva de juros", "curva zero", "curva prefixada"),
        "#juros",
    ),
    Termo(
        "prefixado",
        "Prefixado",
        "Título com o juro fixado na compra: quem compra sabe quanto vai receber no "
        "vencimento, mas perde se a inflação vier mais alta que a esperada.",
        ("Tesouro Prefixado", "prefixado", "prefixados", "prefixada"),
    ),
    Termo(
        "ipca-mais",
        "Tesouro IPCA+",
        "Título que paga a inflação (IPCA) mais um juro real fixado na compra, e por isso "
        "protege o poder de compra. NTN-B é o nome técnico dele.",
        ("Tesouro IPCA+", "IPCA+", "NTN-B"),
    ),
    Termo(
        "juro-10-anos",
        "Juro de 10 anos",
        "Quanto o governo paga para tomar emprestado por 10 anos, pela taxa dos títulos desse "
        "prazo no mercado. É a referência de juro longo para comparar países: mostra a "
        "confiança nas contas do governo e a inflação esperada.",
        ("juro de 10 anos", "juros de 10 anos"),
        "#mundo",
    ),
    Termo(
        "tesouro-direto",
        "Tesouro Direto",
        "O programa do Tesouro Nacional para pessoas comprarem títulos públicos pela internet. "
        "As taxas diárias dele são a base das curvas deste painel.",
        ("Tesouro Direto",),
    ),
    Termo(
        "inflacao-implicita",
        "Inflação implícita",
        "A inflação que o mercado embute nos títulos públicos: a diferença entre o juro do "
        "prefixado e o juro real do IPCA+ no mesmo prazo. Mistura a inflação esperada com um "
        "prêmio pelo risco.",
        ("inflação implícita",),
        "#juros",
    ),
    Termo(
        "tips",
        "TIPS",
        "O título do Tesouro americano que paga a inflação dos EUA mais um juro fixo: o "
        "IPCA+ de lá. A taxa dele é o juro real americano.",
        ("TIPS",),
    ),
    Termo(
        "premio-de-prazo",
        "Prêmio de prazo",
        "O juro a mais que se cobra para emprestar por mais tempo, pelo risco de as coisas "
        "mudarem no caminho.",
        ("prêmio de prazo",),
    ),
    # ---------------------------------------------------------------- previsões
    Termo(
        "focus",
        "Focus",
        "A pesquisa semanal do Banco Central com bancos, gestoras e consultorias sobre o que "
        "esperam para inflação, PIB, Selic, câmbio e contas públicas. A mediana das respostas "
        "é o consenso do mercado.",
        ("boletim Focus", "Focus"),
        "#previsoes",
    ),
    Termo(
        "consenso",
        "Consenso",
        "A previsão do meio entre as dos analistas: aqui, a mediana do Focus. Toda previsão "
        "própria deste painel aparece ao lado dele.",
        ("consenso do mercado", "consenso"),
    ),
    Termo(
        "mediana",
        "Mediana",
        "O valor do meio: metade fica acima e metade abaixo. Diferente da média, não se deixa "
        "puxar por um valor muito fora.",
        ("mediana",),
    ),
    Termo(
        "projecao",
        "Projeção",
        "Uma estimativa do que vai acontecer, feita com uma conta e com hipóteses. Não é "
        "certeza: por isso vem com a faixa de erro e ao lado do consenso.",
        ("projeção", "projeções", "projetado", "projetada"),
    ),
    Termo(
        "erro-tipico",
        "Erro típico",
        "Quanto uma previsão costumou errar, para mais ou para menos, medido no passado. A "
        "barra em volta da previsão vai do valor previsto menos esse erro até ele mais o erro.",
        ("erro típico",),
    ),
    Termo(
        "faixa",
        "Barra de erro",
        "Onde o número deve cair. Nos futuros sorteados, 8 em cada 10 ficam entre as pontas "
        "da barra (1 acima e 1 abaixo dela), e metade fica na parte grossa. Nas previsões, a "
        "barra é o tamanho do erro de um ano comum.",
        ("8 em cada 10 sorteios", "faixa de erro", "barra de erro", "parte grossa"),
    ),
    Termo(
        "sorteio",
        "Sorteio",
        "Um futuro possível montado pelo computador: para cada ano à frente, ele tira ao acaso "
        "um pedaço da história (como juro, crescimento, inflação e primário se afastaram do "
        "normal num ano já vivido) e soma ao cenário de hoje. Repetido 4.000 vezes, dá para "
        "contar em quantos a dívida sobe.",
        ("sorteios", "sorteio", "sorteados", "sorteadas"),
        "#riscos/divida",
    ),
    Termo(
        "percentil",
        "Percentil",
        "A posição num conjunto ordenado de 100: o 90º percentil é o valor que só 10 % "
        "superam; o 10º, o que só 10 % ficam abaixo.",
        ("percentil", "percentis"),
    ),
    Termo(
        "leque",
        "Leque",
        "Gráfico com os futuros possíveis: o meio é o caminho mais provável e as pontas, os "
        "cenários bons e ruins, menos prováveis. Abre como um leque porque, quanto mais longe, "
        "maior a incerteza.",
        ("leque",),
        "#riscos/divida",
    ),
    # ---------------------------------------------------------------- crédito
    Termo(
        "inadimplencia",
        "Inadimplência",
        "Crédito com parcela atrasada há mais de 90 dias, em porcentagem de tudo o que está "
        "emprestado.",
        ("inadimplência",),
        "#credito",
    ),
    Termo(
        "spread",
        "Spread",
        "A diferença entre o juro que o banco cobra de quem pega emprestado e o que ele paga "
        "para conseguir o dinheiro. Cobre o risco de calote, impostos, despesas e o lucro.",
        ("spread",),
    ),
    Termo(
        "concessoes",
        "Concessões",
        "Os empréstimos novos feitos no período. O saldo (ou estoque) é tudo o que já está "
        "emprestado.",
        ("concessões",),
    ),
    Termo(
        "comprometimento",
        "Comprometimento da renda",
        "A parte da renda mensal das famílias que vai para as parcelas das dívidas, juros e "
        "amortização somados.",
        ("comprometimento da renda", "renda comprometida", "comprometida com dívidas"),
    ),
    Termo(
        "basileia",
        "Índice de Basileia",
        "O capital próprio dos bancos em proporção do que emprestaram e aplicaram, pesado pelo "
        "risco de cada operação. É o colchão contra prejuízos; o Banco Central fixa um mínimo, "
        "seguindo o acordo internacional de Basileia.",
        ("índice de Basileia", "Basileia"),
    ),
    Termo(
        "ivg-r",
        "IVG-R",
        "Índice de Valores de Garantia de Imóveis Residenciais Financiados, do Banco Central: "
        "o valor dos imóveis dados em garantia nos financiamentos, pelas avaliações dos "
        "bancos. Serve de termômetro do preço das casas.",
        ("IVG-R",),
    ),
    Termo(
        "hiato-de-credito",
        "Hiato de crédito",
        "Quanto o crédito a famílias e empresas, em % do PIB, está acima ou abaixo da "
        "tendência de longo prazo. Muito acima de zero, o crédito cresceu rápido demais, o "
        "que costuma vir antes de crise bancária.",
        ("hiato de crédito",),
    ),
    Termo(
        "indice-de-liquidez",
        "Índice de Liquidez",
        "Conta do Banco Central: o dinheiro de pronto dos bancos (caixa e títulos fáceis de "
        "vender) sobre o que eles poderiam perder em 30 dias de saques fortes. Acima de 1, "
        "sobra.",
        ("Índice de Liquidez",),
    ),
    Termo(
        "lcr",
        "LCR",
        "Indicador de Liquidez de Curto Prazo, a regra internacional de Basileia: ativos "
        "líquidos sobre as saídas de 30 dias de estresse, em %. Abaixo de 100 %, o banco não "
        "aguentaria sozinho.",
        ("LCR",),
    ),
    Termo(
        "servico-da-divida",
        "Serviço da dívida",
        "O que se paga num período para a dívida: juros mais a parte do principal (amortização).",
        ("serviço da dívida",),
    ),
    Termo(
        "fgts",
        "FGTS",
        "O Fundo de Garantia do Tempo de Serviço: todo mês o empregador deposita 8 % do salário "
        "numa conta do trabalhador. O dinheiro parado financia casa própria, saneamento e "
        "obras.",
        ("FGTS",),
    ),
    Termo(
        "sfh",
        "SFH",
        "O Sistema Financeiro da Habitação: o crédito para a casa própria feito com o dinheiro "
        "da poupança, com teto de juros e de valor do imóvel.",
        ("Sistema Financeiro da Habitação", "SFH"),
        "#credito/imoveis",
    ),
    # ---------------------------------------------------------------- mercados
    Termo(
        "ibovespa",
        "Ibovespa",
        "O principal índice da bolsa brasileira: o valor de uma carteira com as ações mais "
        "negociadas.",
        ("Ibovespa",),
        "#mercados",
    ),
    Termo(
        "volatilidade",
        "Volatilidade",
        "Quanto um preço balança, para cima e para baixo. Aqui, o desvio-padrão das variações "
        "diárias dos últimos 21 dias úteis, levado ao ano. Não diz para que lado o preço vai.",
        ("volatilidade",),
    ),
    # ---------------------------------------------------------------- setor externo
    Termo(
        "conta-corrente",
        "Transações correntes",
        "O saldo de tudo o que o Brasil vende e compra do exterior (bens e serviços), mais o "
        "que paga e recebe de juros, lucros e transferências. Déficit quer dizer que o país "
        "precisa de dinheiro de fora para fechar a conta.",
        ("transações correntes", "conta corrente"),
        "#externo",
    ),
    Termo(
        "balanca",
        "Balança comercial",
        "Exportações menos importações de bens.",
        ("balança comercial",),
    ),
    Termo(
        "commodity",
        "Commodities",
        "Produtos vendidos em grande quantidade, quase iguais de um vendedor para outro, com "
        "preço dado no mercado mundial: soja, petróleo, minério, carne, café. Aqui, pelos "
        "grupos da UNCTAD (ONU): alimentos, combustíveis, minérios e metais e matérias-primas "
        "agrícolas.",
        ("commodities", "commodity"),
        "#externo/setores",
    ),
    Termo(
        "cgce",
        "Categoria de uso (CGCE)",
        "Classificação do IBGE que separa o que o país compra pelo destino: bens de capital "
        "(máquinas que viram investimento), intermediários (insumos e peças para produzir), "
        "bens de consumo (para as famílias) e combustíveis.",
        ("categoria de uso", "categorias de uso", "CGCE"),
        "#externo/setores",
    ),
    Termo(
        "bens-de-capital",
        "Bens de capital",
        "Máquinas, equipamentos e veículos de carga que as empresas compram para produzir. A "
        "importação deles sobe quando o investimento sobe.",
        ("bens de capital",),
        "#externo/setores",
    ),
    Termo(
        "bens-intermediarios",
        "Bens intermediários",
        "Insumos e peças que entram na produção de outra coisa: adubo, aço, químicos, chips. "
        "São mais da metade do que o Brasil importa.",
        ("bens intermediários", "intermediários"),
        "#externo/setores",
    ),
    Termo(
        "aluguel-de-equipamentos",
        "Aluguel de equipamentos",
        "O que o país paga para usar máquinas de donos de fora, como plataformas e navios de "
        "petróleo, aviões e contêineres. Conta como serviço no balanço de pagamentos.",
        ("aluguel de equipamentos",),
        "#externo/conta-corrente",
    ),
    Termo(
        "fob",
        "FOB",
        "O valor da mercadoria embarcada no porto, sem o frete e o seguro até o destino. É como "
        "o Brasil registra o que exporta e importa.",
        ("FOB",),
    ),
    Termo(
        "idp",
        "Investimento direto",
        "Dinheiro de estrangeiros para abrir, comprar ou ampliar empresas no Brasil (com 10 % "
        "ou mais do capital). É o financiamento externo mais estável: não sai de um dia para o "
        "outro.",
        ("investimento direto no país", "investimento direto", "IDP"),
    ),
    Termo(
        "reservas",
        "Reservas internacionais",
        "Os dólares e outros ativos em moeda forte que o Banco Central guarda. São o colchão "
        "para pagar compromissos com o exterior e acalmar o câmbio numa crise.",
        ("reservas internacionais", "reservas"),
    ),
    Termo(
        "cambio-real",
        "Câmbio real efetivo",
        "O valor do real contra as moedas dos países com quem o Brasil comercia, descontada a "
        "inflação daqui e de lá. No índice do Banco Central, subir quer dizer real mais barato.",
        ("câmbio real efetivo", "câmbio real"),
    ),
    Termo(
        "swap",
        "Swap cambial",
        "Contrato em que o Banco Central paga a variação do dólar (mais um juro) e recebe a "
        "taxa DI. Dá proteção contra a alta do dólar sem gastar as reservas.",
        ("swaps cambiais", "swap cambial", "swaps"),
    ),
    Termo(
        "nota-de-credito",
        "Nota de crédito",
        "A nota que as agências (S&P, Moody's, Fitch) dão à chance de um país pagar a dívida "
        "em dia. De BBB− (Baa3 na Moody's) para cima é grau de investimento; abaixo, grau "
        "especulativo.",
        ("grau de investimento", "grau especulativo", "nota de crédito", "rating"),
        "#riscos/mercado-externo",
    ),
    Termo(
        "ic-br",
        "IC-Br",
        "O Índice de Commodities do Banco Central: os preços, em reais, das commodities que "
        "mais pesam na inflação do Brasil (agropecuária, metais e energia).",
        ("IC-Br",),
    ),
    Termo(
        "bpm6",
        "BPM6",
        "A sexta edição do manual do FMI de como montar o balanço de pagamentos. É a regra que "
        "o Banco Central segue nas contas externas, igual à dos outros países.",
        ("BPM6",),
    ),
    # ---------------------------------------------------------------- contas públicas
    Termo(
        "primario",
        "Resultado primário",
        "Receitas menos despesas do governo, sem contar os juros da dívida. No superávit, sobra "
        "dinheiro para pagar parte dos juros; no déficit, falta, e a diferença vira dívida nova.",
        (
            "resultado primário",
            "déficit primário",
            "superávit primário",
            "primário",
        ),
        "#fiscal",
    ),
    Termo(
        "nominal",
        "Resultado nominal",
        "O resultado primário menos os juros da dívida: quanto o governo precisa tomar "
        "emprestado no período.",
        ("resultado nominal", "déficit nominal"),
    ),
    Termo(
        "dbgg",
        "Dívida bruta (DBGG)",
        "Dívida Bruta do Governo Geral: tudo o que União, estados e municípios devem, sem "
        "descontar o que têm a receber, em % do PIB. É a medida do Banco Central; o FMI soma "
        "também os títulos do Tesouro na carteira do BC, e por isso o número dele é maior.",
        ("dívida bruta do governo geral", "dívida bruta", "DBGG"),
        "#fiscal",
    ),
    Termo(
        "dlsp",
        "Dívida líquida (DLSP)",
        "Dívida Líquida do Setor Público: a dívida bruta menos o que o setor público tem a "
        "receber (as reservas internacionais, os créditos), somando governos, Banco Central e "
        "parte das estatais.",
        ("dívida líquida do setor público", "dívida líquida", "DLSP"),
    ),
    Termo(
        "governo-central",
        "Governo Central",
        "O Tesouro Nacional, a Previdência Social (INSS) e o Banco Central. É a parte do setor "
        "público que tem a meta de primário da LDO.",
        ("Governo Central",),
    ),
    Termo(
        "setor-publico",
        "Setor público consolidado",
        "O Governo Central, os estados, os municípios e as estatais (fora Petrobras, "
        "Eletrobras e os bancos públicos). É o conceito do Banco Central para as contas "
        "públicas.",
        ("setor público consolidado",),
    ),
    Termo(
        "governo-geral",
        "Governo geral",
        "União, estados e municípios, sem o Banco Central e sem as estatais. É o conceito que "
        "o FMI usa para comparar países.",
        ("governo geral",),
    ),
    Termo(
        "ldo",
        "LDO",
        "Lei de Diretrizes Orçamentárias: a lei votada todo ano com as regras do orçamento do "
        "ano seguinte, a meta de resultado primário entre elas.",
        ("LDO",),
    ),
    Termo(
        "lrf",
        "LRF",
        "Lei de Responsabilidade Fiscal (Lei Complementar 101/2000): limita o gasto com "
        "pessoal e a dívida de União, estados e municípios, e manda publicar as contas a cada "
        "bimestre e quadrimestre.",
        ("Lei de Responsabilidade Fiscal", "LRF"),
    ),
    Termo(
        "rcl",
        "Receita corrente líquida",
        "O que o governo arrecada em 12 meses com impostos, contribuições e transferências, "
        "menos o que repassa por obrigação (aos municípios, por exemplo). É a base dos limites "
        "da LRF.",
        ("receita corrente líquida", "RCL"),
    ),
    Termo(
        "juro-menos-crescimento",
        "Juro menos crescimento",
        "Se o juro real que a dívida paga é maior que o crescimento real do PIB, a dívida "
        "cresce em % do PIB sozinha, a menos que o governo faça superávit primário. É a conta "
        "central da sustentabilidade da dívida.",
        ("juro da dívida menos crescimento", "juro menos crescimento"),
        "#riscos/divida",
    ),
    Termo(
        "primario-que-estabiliza",
        "Primário que estabiliza a dívida",
        "O superávit primário que deixaria a dívida parada em % do PIB, com o juro e o "
        "crescimento de hoje. Abaixo dele, ela sobe.",
        ("primário que estabiliza", "estabilizar a dívida", "estabiliza a dívida"),
        "#riscos/divida",
    ),
    Termo(
        "sustentabilidade",
        "Sustentabilidade da dívida",
        "Se o governo consegue manter a dívida num nível que paga em dia, sem ajuste às "
        "pressas, inflação alta ou calote. Não é sim ou não: é um caminho, que depende de "
        "juro, crescimento e resultado primário.",
        ("sustentabilidade da dívida",),
        "#riscos/divida",
    ),
    Termo(
        "estresse",
        "Teste de estresse",
        'A pergunta "e se uma crise do passado acontecesse de novo hoje?": aplica os choques '
        "de um episódio real (2008, 2015, 2020) aos números de hoje e mostra o resultado.",
        ("testes de estresse", "teste de estresse"),
        "#riscos/divida",
    ),
    Termo(
        "elasticidade",
        "Elasticidade",
        "Quanto um número muda quando outro muda. Aqui, quanto a dívida sobe se a Selic, o "
        "dólar ou a inflação subirem 1 ponto.",
        ("elasticidades", "elasticidade"),
    ),
    Termo(
        "aceso",
        "Aceso",
        "No painel de alerta, o indicador que está pior que 80 % da própria história (no "
        "quinto pior). Não quer dizer crise: quer dizer fora do normal para ele.",
        ("acesos", "aceso", "quinto pior"),
        "#riscos/alerta",
    ),
    Termo(
        "rgps",
        "INSS (Regime Geral)",
        "O Regime Geral de Previdência Social, pago pelo INSS: aposentadorias e pensões dos "
        "trabalhadores do setor privado. O déficit é o que se paga em benefícios menos o que "
        "se recebe de contribuições.",
        ("Regime Geral", "RGPS", "INSS"),
    ),
    Termo(
        "precatorios",
        "Precatórios",
        "Dívidas do governo reconhecidas pela Justiça em decisão final, que entram no "
        "orçamento para ser pagas.",
        ("precatórios", "precatório"),
    ),
    Termo(
        "taxa-implicita",
        "Taxa implícita da dívida",
        "O juro médio que a dívida pagou: os juros do período divididos pelo saldo dela. O "
        "Banco Central publica a da dívida bruta todo mês, somando os últimos 12 meses.",
        ("taxa implícita", "juro médio da dívida bruta"),
        "#riscos/divida",
    ),
    Termo(
        "compromissadas",
        "Operações compromissadas",
        "Empréstimos de curtíssimo prazo que o Banco Central toma dos bancos, dando títulos do "
        "Tesouro em garantia, para tirar dinheiro de circulação. Pagam perto da Selic e o Banco "
        "Central as conta na dívida bruta.",
        ("operações compromissadas", "compromissadas"),
    ),
    Termo(
        "rolagem",
        "Rolagem da dívida",
        "Trocar a dívida que vence por dívida nova. Quanto mais dívida vence no ano, mais o "
        "governo depende do juro do momento para rolá-la.",
        ("rolagem", "rolar a dívida"),
        "#riscos/custo",
    ),
    Termo(
        "receita-liquida",
        "Receita líquida da União",
        "O que o Governo Central arrecada menos o que a lei manda repassar a estados e "
        "municípios. É o que sobra para os gastos da União, os juros inclusive.",
        ("receita líquida",),
    ),
    Termo(
        "perda-provavel",
        "Perda provável e perda possível",
        "Como a AGU classifica as ações contra a União: provável quando o STF, o STJ ou o TST "
        "já decidiu contra o governo; possível quando o caso está para ser julgado nesses "
        "tribunais. O resto é remoto e fica fora da conta.",
        ("perda provável", "perda possível"),
        "#riscos/juridico",
    ),
    Termo(
        "anexo-de-riscos-fiscais",
        "Anexo de Riscos Fiscais",
        "A parte do projeto da LDO em que o governo lista, todo ano, o que pode piorar as "
        "contas: ações na Justiça, garantias dadas, dívidas a receber e o efeito de juros e PIB "
        "diferentes do previsto. A Lei de Responsabilidade Fiscal manda publicar.",
        ("Anexo de Riscos Fiscais", "riscos fiscais"),
        "#riscos/juridico",
    ),
    Termo(
        "projecao-atuarial",
        "Projeção atuarial",
        "A conta de quanto a Previdência vai receber e pagar nas próximas décadas, feita com a "
        "população projetada, as regras de aposentadoria e hipóteses de salário e PIB.",
        ("projeção atuarial", "projeções atuariais", "projeção do governo"),
        "#riscos/bancos",
    ),
    Termo(
        "governanca",
        "Governança (Banco Mundial)",
        "As notas que o Banco Mundial dá a cada país, todo ano, para a qualidade do governo, "
        "das leis, da regulação e o controle da corrupção, juntando dezenas de pesquisas. Vão "
        "de 0 a 100; mais é melhor, e a margem de erro é de alguns pontos.",
        ("governança", "estado de direito", "controle da corrupção"),
        "#riscos/juridico",
    ),
    Termo(
        "tjlp",
        "TJLP",
        "A Taxa de Juros de Longo Prazo, fixada pelo CMN, que corrigia os empréstimos do BNDES. "
        "Os contratos novos passaram a usar a TLP, mais perto dos juros de mercado.",
        ("TJLP",),
    ),
    Termo(
        "adpf",
        "ADPF",
        "Arguição de Descumprimento de Preceito Fundamental: a ação no Supremo para derrubar ato "
        "do governo que fere a Constituição.",
        ("ADPF",),
    ),
    Termo(
        "lei-complementar",
        "Lei complementar (LC)",
        "Lei que a Constituição exige para certos assuntos, como impostos e finanças públicas. "
        "Precisa do voto da maioria absoluta da Câmara e do Senado, não só dos presentes.",
        ("lei complementar", "leis complementares", "LCs", "LC"),
    ),
    Termo(
        "pec",
        "PEC",
        "Proposta de Emenda à Constituição: passa duas vezes em cada Casa do Congresso, com "
        "três quintos dos votos. Aprovada, vira emenda constitucional (EC).",
        ("PEC",),
    ),
    Termo(
        "tcu",
        "TCU",
        "O Tribunal de Contas da União: fiscaliza como o governo federal gasta e arrecada, a "
        "serviço do Congresso. Na reforma do consumo, faz a conta das alíquotas de referência.",
        ("Tribunal de Contas da União", "TCU"),
    ),
    # ---------------------------------------------------------------- impostos
    Termo(
        "carga-tributaria",
        "Carga tributária",
        "Quanto do PIB o governo inteiro (União, estados, municípios e previdência) arrecada "
        "em impostos e contribuições num ano.",
        ("carga tributária",),
        "#impostos/carga",
    ),
    Termo(
        "gasto-tributario",
        "Gasto tributário",
        "O que o governo deixa de arrecadar por isenção, desconto ou regime especial de "
        "imposto (Simples Nacional, Zona Franca de Manaus, deduções do Imposto de Renda). "
        "Funciona como um gasto, só que sem passar pelo orçamento.",
        ("gasto tributário", "gastos tributários"),
        "#impostos/gasto-tributario",
    ),
    Termo(
        "simples-nacional",
        "Simples Nacional",
        "O regime de imposto das empresas pequenas: uma guia só, com alíquota menor que a das "
        "regras gerais. É o maior gasto tributário da União.",
        ("Simples Nacional",),
    ),
    Termo(
        "cofins",
        "Cofins e PIS",
        "Contribuições federais cobradas sobre o faturamento das empresas, que pagam a "
        "seguridade social e o seguro-desemprego.",
        ("Cofins", "PIS/Pasep", "PIS"),
    ),
    Termo(
        "csll",
        "CSLL",
        "Contribuição Social sobre o Lucro Líquido: um segundo imposto sobre o lucro das "
        "empresas, ao lado do Imposto de Renda.",
        ("CSLL",),
    ),
    Termo(
        "ipi",
        "IPI",
        "Imposto sobre Produtos Industrializados: federal, cobrado de fábricas e importadores.",
        ("IPI",),
    ),
    Termo(
        "iof",
        "IOF",
        "Imposto sobre Operações Financeiras: federal, cobrado em crédito, câmbio, seguro e "
        "algumas aplicações.",
        ("IOF",),
    ),
    Termo(
        "cbs",
        "CBS",
        "Contribuição sobre Bens e Serviços: o tributo federal sobre o consumo criado pela "
        "reforma de 2023, que substitui o PIS e a Cofins a partir de 2027.",
        ("CBS",),
        "#impostos/reforma",
    ),
    Termo(
        "ibs",
        "IBS",
        "Imposto sobre Bens e Serviços: o tributo de estados e municípios criado pela reforma "
        "de 2023, que substitui o ICMS e o ISS aos poucos, de 2029 a 2033.",
        ("IBS",),
        "#impostos/reforma",
    ),
    Termo(
        "regime-especifico",
        "Regime específico",
        "Na reforma do consumo, o setor em que o IBS e a CBS têm conta própria: outra base (só "
        "a margem, nos bancos), outra alíquota (em reais por litro, nos combustíveis) ou sem "
        "crédito para quem compra.",
        ("regime específico", "regimes específicos", "regra própria"),
        "#impostos/reforma",
    ),
    Termo(
        "iva",
        "IVA",
        "Imposto sobre Valor Adicionado: o imposto sobre o consumo em que cada empresa paga só "
        "sobre o que acrescentou, abatendo o que já se pagou antes. É o modelo do IBS e da CBS.",
        ("IVA",),
    ),
    Termo(
        "redutor-social",
        "Redutor social",
        "Valor fixo da lei que se tira da base do IBS e da CBS na venda de casa nova ou de lote "
        "e em cada mês de aluguel de moradia, para pesar menos nos imóveis mais baratos.",
        ("redutor social", "redutor de ajuste"),
        "#impostos/reforma",
    ),
    Termo(
        "imposto-seletivo",
        "Imposto Seletivo",
        "Imposto federal criado pela reforma de 2023 sobre produtos que fazem mal à saúde ou "
        "ao meio ambiente. Começa em 2027.",
        ("Imposto Seletivo",),
        "#impostos/reforma",
    ),
    Termo(
        "cobranca-no-destino",
        "Cobrança no destino",
        "O imposto fica com o estado e o município onde a compra é consumida, e não com os de "
        "onde a mercadoria saiu. É a regra do IBS; a troca vai de 2029 a 2077.",
        ("cobrança no destino", "pelo destino"),
        "#impostos/reforma",
    ),
    Termo(
        "retido-na-fonte",
        "Imposto retido na fonte",
        "O Imposto de Renda que a empresa, o INSS ou o banco desconta antes de pagar e repassa "
        "à Receita. Na declaração, conta como já pago: se passou do devido, volta como "
        "restituição.",
        ("retido na fonte", "imposto retido"),
        "#impostos/quem-paga",
    ),
    Termo(
        "iss",
        "ISS",
        "Imposto Sobre Serviços: municipal, cobrado de quem presta serviço.",
        ("ISS",),
    ),
    Termo(
        "irpj",
        "IRPJ",
        "Imposto de Renda da Pessoa Jurídica: o imposto federal sobre o lucro das empresas, "
        "de 25 % para as grandes.",
        ("IRPJ",),
        "#impostos/quem-paga",
    ),
    Termo(
        "aliquota-de-referencia",
        "Alíquota de referência",
        "A alíquota da CBS e do IBS que o Senado fixa para a arrecadação ficar igual à dos "
        "tributos que saem. Cada estado e município pode cobrar acima ou abaixo dela.",
        ("alíquota de referência", "alíquotas de referência"),
        "#impostos/reforma",
    ),
    Termo(
        "correlacao",
        "Correlação",
        "Mede de -1 a 1 o quanto duas coisas andam juntas. Perto de zero, não andam; andar "
        "junto não quer dizer que uma cause a outra.",
        ("correlação",),
    ),
    Termo(
        "aliquota-cheia",
        "Alíquota cheia",
        "O percentual do imposto para o que não tem desconto, cobrado sobre o valor sem o "
        "imposto. Quem tem desconto de 60 % paga 40 % dela; a cesta básica, zero.",
        ("alíquota cheia", "alíquotas cheias"),
        "#impostos/reforma",
    ),
    Termo(
        "cashback",
        "Devolução do imposto (cashback)",
        "Parte do IBS e da CBS pagos volta para a família de baixa renda inscrita no Cadastro "
        "Único: 20 % no geral, e toda a CBS nas contas de luz, água, gás e telefone.",
        ("cashback", "Cadastro Único"),
        "#impostos/reforma",
    ),
    Termo(
        "imposto-de-renda",
        "Imposto de Renda",
        "O imposto federal sobre a renda: o das pessoas (IRPF), descontado no salário e acertado "
        "na declaração anual, e o das empresas (IRPJ), sobre o lucro.",
        ("Imposto de Renda", "IRPF"),
        "#impostos/quem-paga",
    ),
    Termo(
        "iptu-itbi-itr",
        "IPTU, ITBI e ITR",
        "Impostos sobre imóveis. IPTU: o municipal sobre casas e terrenos da cidade, todo ano. "
        "ITBI: o municipal na compra e venda do imóvel. ITR: o federal sobre a terra rural.",
        ("IPTU", "ITBI", "ITR"),
    ),
    Termo(
        "adct",
        "ADCT",
        "O Ato das Disposições Constitucionais Transitórias: a parte do fim da Constituição com "
        "as regras que valem só por um tempo. A transição da reforma do consumo está lá.",
        ("ADCT",),
        "#impostos/reforma",
    ),
    Termo(
        "comite-gestor",
        "Comitê Gestor do IBS",
        "O órgão dos estados e municípios que vai cobrar o IBS e dividir o dinheiro entre eles, "
        "no lugar de cada um cobrar o seu ICMS e ISS.",
        ("Comitê Gestor do IBS", "Comitê Gestor"),
        "#impostos/reforma",
    ),
    Termo(
        "cesta-basica",
        "Cesta básica",
        "Os alimentos essenciais que a lei livra de imposto. Hoje não pagam Cofins e PIS; com a "
        "reforma, os da Cesta Básica Nacional ficam com IBS e CBS zerados.",
        ("Cesta Básica Nacional", "cesta básica"),
        "#impostos/reforma",
    ),
    Termo(
        "divida-ativa",
        "Dívida ativa",
        "Impostos e outras dívidas com o governo que venceram sem pagamento e foram inscritas "
        "para cobrança, na Justiça ou fora dela. Boa parte nunca é recebida.",
        ("dívida ativa",),
        "#impostos/gasto-tributario",
    ),
    Termo(
        "zona-franca",
        "Zona Franca de Manaus",
        "Área de Manaus com descontos e isenções de impostos federais e do ICMS para quem "
        "produz lá, garantidos pela Constituição. É um dos maiores gastos tributários da União.",
        ("Zona Franca de Manaus", "Zona Franca"),
    ),
    Termo(
        "ocde",
        "OCDE",
        "A Organização para a Cooperação e Desenvolvimento Econômico: 38 países, a maioria "
        "ricos (Estados Unidos, Europa, Japão, Chile, México). Publica estatísticas iguais "
        "para todos, como a carga tributária.",
        ("OCDE",),
    ),
    # ---------------------------------------------------------------- estados
    Termo(
        "icms",
        "ICMS",
        "O imposto estadual sobre a circulação de mercadorias e alguns serviços (energia, "
        "combustíveis, telefonia). É a maior receita própria dos estados.",
        ("ICMS",),
    ),
    Termo("ipva", "IPVA", "O imposto estadual sobre a propriedade de veículos.", ("IPVA",)),
    Termo("itcmd", "ITCMD", "O imposto estadual sobre heranças e doações.", ("ITCMD",)),
    Termo(
        "fpe",
        "FPE",
        "Fundo de Participação dos Estados: a parte do Imposto de Renda e do IPI que a União "
        "reparte com os estados, mais para os mais pobres.",
        ("FPE",),
        "#impostos/por-estado",
    ),
    Termo(
        "fpm",
        "FPM",
        "Fundo de Participação dos Municípios: a parte do Imposto de Renda e do IPI que a "
        "União reparte com as prefeituras, com mais peso para as cidades pequenas.",
        ("FPM",),
        "#impostos/por-estado",
    ),
    Termo(
        "fundeb",
        "Fundeb",
        "O fundo da educação básica: estados e municípios põem nele parte dos impostos, e o "
        "dinheiro volta repartido pelo número de alunos de cada rede.",
        ("Fundeb", "FUNDEB"),
    ),
    Termo(
        "transferencias-uniao",
        "Transferências da União",
        "Dinheiro que o governo federal repassa aos estados: o FPE, a parte de outros tributos "
        "federais e os repasses para saúde e educação.",
        ("transferências da União", "repasses da União"),
    ),
    Termo(
        "despesa-pessoal",
        "Despesa com pessoal",
        "Salários, aposentadorias, pensões e encargos dos servidores. A LRF limita esse gasto "
        "a uma parte da receita corrente líquida.",
        ("despesa com pessoal", "gasto com pessoal", "gastam com pessoal", "Pessoal e encargos"),
        "#estados/mapa",
    ),
    Termo(
        "limite-maximo-pessoal",
        "Limite máximo de pessoal",
        "O teto da LRF para o gasto com pessoal do Poder Executivo de um estado: 49 % da "
        "receita corrente líquida (art. 20). Acima dele, o estado tem de cortar o excesso.",
        ("limite máximo",),
        "#estados/mapa",
    ),
    Termo(
        "limite-prudencial",
        "Limite prudencial",
        "95 % do limite máximo de gasto com pessoal (LRF, art. 22). Passou dele, o estado fica "
        "proibido, entre outras coisas, de dar aumento e de criar cargos.",
        ("limite prudencial",),
        "#estados/mapa",
    ),
    Termo(
        "limite-de-alerta",
        "Limite de alerta",
        "90 % do limite da lei (LRF, art. 59). Ao passar dele, o Tribunal de Contas avisa o "
        "estado. Vale para o gasto com pessoal e para a dívida.",
        ("limite de alerta",),
        "#estados/mapa",
    ),
    Termo(
        "dcl",
        "Dívida consolidada líquida",
        "A dívida do estado menos o que ele tem em caixa e em haveres financeiros, em proporção "
        "da receita corrente líquida. O limite para os estados é 200 % da RCL (Resolução do "
        "Senado 40/2001).",
        ("dívida consolidada líquida", "DCL"),
        "#estados/mapa",
    ),
    Termo(
        "divida-consolidada",
        "Dívida consolidada",
        "Tudo o que o estado deve com prazo de mais de um ano (empréstimos, a dívida com a "
        "União, precatórios vencidos), antes de descontar o caixa.",
        ("dívida consolidada",),
    ),
    Termo(
        "divida-com-a-uniao",
        "Dívida com a União",
        "Nos anos 1990 a União assumiu dívidas dos estados e passou a cobrá-las deles em "
        "parcelas de longo prazo. Para vários estados, é a maior parte da dívida.",
        ("Dívida com a União", "renegociação da dívida dos estados"),
    ),
    Termo(
        "haveres",
        "Haveres financeiros",
        "O que outros devem ao estado e que ele pode cobrar, como empréstimos que concedeu. "
        "Junto com o caixa, é descontado da dívida para chegar à dívida líquida.",
        ("haveres financeiros", "haveres"),
    ),
    Termo(
        "disponibilidade-de-caixa",
        "Disponibilidade de caixa",
        "O dinheiro que o estado tem no banco, livre para pagar contas.",
        ("disponibilidade de caixa",),
    ),
    Termo(
        "custeio",
        "Custeio",
        "O gasto para manter a máquina funcionando, fora salários e juros: compras, serviços, "
        'aluguel, contas de luz, repasses. Na contabilidade, "outras despesas correntes".',
        ("outras despesas correntes", "custeio"),
    ),
    Termo(
        "inversoes",
        "Inversões financeiras",
        "Gasto que vira um bem financeiro: comprar participação em empresa, pôr capital numa "
        "estatal ou emprestar dinheiro.",
        ("inversões financeiras", "inversão financeira"),
    ),
    Termo(
        "amortizacao",
        "Amortização",
        "A parte da prestação que paga o principal da dívida, não os juros. Diminui o que se deve.",
        ("amortização da dívida", "amortização"),
    ),
    Termo(
        "encargos-especiais",
        "Encargos especiais",
        "Despesa que não é de uma área de governo: juros e amortização da dívida e o que o "
        "estado repassa aos municípios.",
        ("encargos especiais",),
    ),
    Termo(
        "rpps",
        "RPPS",
        "Regime Próprio de Previdência Social: a previdência dos servidores do estado, "
        "separada do INSS.",
        ("RPPS", "regimes próprios", "regime próprio", "fundos de previdência próprios"),
    ),
    Termo(
        "capitalizacao",
        "Fundo em capitalização",
        "A parte da previdência dos servidores que guarda e aplica o dinheiro para pagar as "
        "aposentadorias de quem entrou mais recentemente. Costuma sobrar; as aposentadorias de "
        "hoje saem do fundo em repartição, que o Tesouro do estado cobre.",
        ("fundo em capitalização", "fundo em repartição"),
    ),
    Termo(
        "capag",
        "CAPAG",
        "Capacidade de pagamento: a nota que o Tesouro Nacional dá a cada estado, de A+ (a "
        "melhor) a D, pela dívida, pela poupança corrente e pelo caixa. É a nota que o "
        "Tesouro olha quando o estado pede empréstimo com garantia da União.",
        ("CAPAG", "Capag", "capacidade de pagamento"),
        "#estados/limites",
    ),
    Termo(
        "rrf",
        "Regime de Recuperação Fiscal",
        "Acordo da Lei Complementar 159/2017 para estado com as contas em crise: a União "
        "suspende parte das parcelas da dívida e o estado segue um plano de ajuste, com teto "
        "de gastos e venda de empresas, vigiado por um conselho.",
        ("Regime de Recuperação Fiscal", "RRF"),
        "#estados/limites",
    ),
    Termo(
        "propag",
        "Propag",
        "Programa de Pleno Pagamento de Dívidas dos Estados (Lei Complementar 212/2025): "
        "refinancia a dívida com a União em até 30 anos, com juro menor para quem entrega "
        "empresas ou imóveis, investe em ensino técnico e aporta num fundo dos estados.",
        ("Propag",),
        "#estados/limites",
    ),
    Termo(
        "valor-adicionado",
        "Valor adicionado",
        "O que cada atividade produz, descontado o que ela comprou de outras: a soma de todas "
        "é o PIB sem os impostos sobre os produtos.",
        ("valor adicionado",),
    ),
    Termo(
        "acima-da-linha",
        "Acima da linha",
        "Resultado apurado pelas receitas e despesas do próprio governo. O outro jeito, "
        '"abaixo da linha", olha quanto a dívida mudou; os dois deviam dar parecido.',
        ("acima da linha", "abaixo da linha"),
    ),
    Termo(
        "rgf",
        "RGF",
        "Relatório de Gestão Fiscal: sai a cada quadrimestre e mostra o gasto com pessoal e a "
        "dívida do estado contra os limites da LRF.",
        ("Relatório de Gestão Fiscal", "RGF"),
    ),
    Termo(
        "rreo",
        "RREO",
        "Relatório Resumido da Execução Orçamentária: sai a cada bimestre com a receita, a "
        "despesa e o resultado primário do estado.",
        ("Relatório Resumido da Execução Orçamentária", "RREO"),
    ),
    Termo(
        "dca",
        "DCA",
        "Declaração de Contas Anuais: o balanço do ano fechado que cada estado manda ao "
        "Tesouro Nacional, com a receita e a despesa abertas por tipo e por área.",
        ("Declaração de Contas Anuais", "DCA"),
    ),
    Termo(
        "siconfi",
        "SICONFI",
        "O sistema do Tesouro Nacional onde estados e municípios entregam as contas (RGF, "
        "RREO e DCA). É de onde vêm os números desta aba.",
        ("SICONFI",),
    ),
    Termo(
        "quadrimestre",
        "Quadrimestre",
        "Um terço do ano: jan–abr, mai–ago ou set–dez. O RGF sai a cada quadrimestre.",
        ("quadrimestre",),
    ),
    # ---------------------------------------------------------------- mundo
    Termo(
        "fmi",
        "FMI",
        "O Fundo Monetário Internacional. Duas vezes por ano publica o World Economic Outlook, "
        "com dados e projeções de quase todos os países.",
        ("FMI", "WEO", "World Economic Outlook"),
        "#mundo",
    ),
    Termo(
        "bis",
        "BIS",
        "O Banco de Compensações Internacionais, em Basileia (Suíça), que os bancos centrais "
        "usam como banco. Reúne dados de juros, câmbio e crédito de dezenas de países.",
        ("BIS",),
    ),
    Termo(
        "ppc",
        "PPC",
        "Paridade do poder de compra: uma conversão que corrige a diferença de preços entre os "
        "países, para que um dólar PPC compre a mesma coisa em qualquer lugar. Serve para "
        "comparar renda.",
        ("paridade do poder de compra", "PPC"),
    ),
    Termo(
        "emergentes",
        "Emergentes",
        "Na lista do FMI, os mercados emergentes e economias em desenvolvimento: países de "
        "renda média ou baixa, como Brasil, México, China, Índia e África do Sul.",
        ("emergentes",),
    ),
    Termo(
        "avancados",
        "Avançados",
        "Na lista do FMI, as economias avançadas: Estados Unidos, zona do euro, Japão, Reino "
        "Unido, Canadá, Austrália, Coreia do Sul e outros países ricos.",
        ("avançados", "economias avançadas"),
    ),
    # ---------------------------------------------------------------- pobreza
    Termo(
        "inseguranca-alimentar",
        "Insegurança alimentar",
        "Medida pela escala do IBGE, com oito perguntas sobre os últimos três meses. Leve: "
        "medo de faltar comida ou comida pior; moderada: menos comida para os adultos; grave: "
        "alguém da casa, até criança, ficou sem comer por falta de dinheiro, a fome.",
        ("insegurança alimentar", "insegurança grave", "EBIA"),
        "#pobreza/fome",
    ),
    Termo(
        "mapa-da-fome",
        "Mapa da Fome",
        "A lista da FAO, a agência da ONU para a alimentação, dos países com mais de 2,5 % da "
        "população sem comer o bastante, na média de três anos.",
        ("Mapa da Fome",),
        "#pobreza/fome",
    ),
    Termo(
        "subalimentacao",
        "Subalimentação",
        "Pela conta da FAO, a parte da população que não come calorias suficientes para as "
        "necessidades mínimas de uma vida normal. É o critério do Mapa da Fome.",
        ("subalimentação", "subalimentada"),
        "#pobreza/fome",
    ),
    Termo(
        "bpc",
        "BPC",
        "Benefício de Prestação Continuada: um salário mínimo por mês para idosos de 65 anos "
        "ou mais e pessoas com deficiência de famílias de baixa renda. Não é aposentadoria: "
        "não exige ter contribuído.",
        ("BPC", "BPC-LOAS"),
        "#pobreza/linha-de-pobreza",
    ),
    Termo(
        "marco-do-saneamento",
        "Marco Legal do Saneamento",
        "A lei de 2020 que mudou as regras do saneamento e fixou a meta de 99 % da população "
        "com água potável e 90 % com coleta e tratamento de esgoto até o fim de 2033.",
        ("Marco Legal do Saneamento", "Marco do Saneamento"),
        "#pobreza/saneamento",
    ),
    Termo(
        "esgoto-na-rede",
        "Esgoto ligado à rede",
        "A casa cujo esgoto vai para a rede geral (ou para a rede de chuva, ou para uma fossa "
        "ligada à rede). Fossa sem ligação, vala, rio ou mar ficam de fora.",
        ("esgoto ligado à rede", "esgoto na rede"),
        "#pobreza/saneamento",
    ),
    Termo(
        "gini",
        "Índice de Gini",
        "Mede a desigualdade numa só conta: 0 é tudo dividido por igual, 1 é tudo nas mãos de "
        "um só (uma pessoa, ou um município, no PIB dos estados). Na renda, o Brasil fica perto "
        "de 0,5; países europeus, perto de 0,3.",
        ("índice de Gini", "coeficiente de Gini", "Gini"),
        "#pobreza/desigualdade",
    ),
    Termo(
        "renda-por-pessoa",
        "Renda domiciliar por pessoa",
        "Toda a renda de quem mora na casa (trabalho, aposentadoria, aluguel, programas "
        "sociais) dividida pelo número de moradores. É a medida que o IBGE usa para a "
        "desigualdade e a pobreza.",
        ("renda domiciliar por pessoa", "renda domiciliar per capita", "renda por pessoa"),
        "#pobreza/desigualdade",
    ),
    Termo(
        "razao-10-40",
        "Razão 10/40",
        "Quantas vezes a fatia da renda dos 10 % mais ricos é maior que a dos 40 % mais pobres "
        "juntos. Também chamada de razão de Palma.",
        ("razão 10/40", "razão de Palma"),
        "#pobreza/desigualdade",
    ),
    Termo(
        "linha-de-pobreza",
        "Linha de pobreza",
        "A renda por pessoa abaixo da qual alguém é contado como pobre. As do Banco Mundial "
        "são em dólares por dia, corrigidos pela diferença de preços entre os países: US$ "
        "8,30 para pobreza num país como o Brasil e US$ 3,00 para extrema pobreza.",
        ("linha de pobreza", "linhas de pobreza", "extrema pobreza"),
        "#pobreza/linha-de-pobreza",
    ),
    Termo(
        "lucros-e-dividendos",
        "Lucros e dividendos",
        "O que a empresa paga aos sócios e acionistas do lucro que teve. No Brasil, quem recebe "
        "não paga Imposto de Renda sobre eles na declaração.",
        ("lucros e dividendos", "dividendos"),
        "#pobreza/quem-ganha-mais",
    ),
    Termo(
        "patrimonio-declarado",
        "Patrimônio declarado",
        "Os bens e direitos que a pessoa lista na declaração do Imposto de Renda: imóveis, "
        "carros, aplicações, parte em empresas. Em geral vão pelo valor de compra, não pelo de "
        "mercado.",
        ("patrimônio declarado", "bens e direitos"),
        "#pobreza/quem-ganha-mais",
    ),
    Termo(
        "analfabetismo",
        "Analfabetismo",
        "A parte das pessoas que não sabem ler e escrever um bilhete simples, pela resposta à "
        "pesquisa do IBGE.",
        ("analfabetismo",),
        "#pobreza/diferencas",
    ),
    Termo(
        "anos-de-estudo",
        "Anos de estudo",
        "Quantos anos de escola a pessoa completou, do primeiro ano do fundamental em diante. "
        "Repetir de ano não conta.",
        ("anos de estudo",),
        "#pobreza/diferencas",
    ),
    Termo(
        "fao",
        "FAO",
        "A agência da ONU para a alimentação e a agricultura. Mede a fome no mundo e faz o "
        "Mapa da Fome.",
        ("FAO",),
    ),
    Termo(
        "pof",
        "POF",
        "A Pesquisa de Orçamentos Familiares, do IBGE: o que as famílias compram e quanto gastam "
        "em cada coisa. Dela saem os pesos de cada item no IPCA.",
        ("POF",),
    ),
    Termo(
        "sinisa",
        "SINISA",
        "O Sistema Nacional de Informações em Saneamento Básico, do Ministério das Cidades: o "
        "que as empresas e prefeituras que cuidam de água, esgoto e lixo informam todo ano. "
        "Substituiu o SNIS em 2024.",
        ("SINISA", "SNIS"),
        "#pobreza/saneamento",
    ),
    Termo(
        "centil",
        "Centil",
        "Cada um dos cem grupos do mesmo tamanho em que se dividem as pessoas, da menor renda "
        "para a maior. O último centil é o 1 % de cima.",
        ("centil", "centis"),
    ),
    Termo(
        "militares-inativos",
        "Militares inativos",
        "Os militares da reserva e os reformados. Continuam recebendo a remuneração, paga pelo "
        "Tesouro; a contribuição dos militares vai só para as pensões.",
        ("militares inativos", "militares da reserva", "reserva e dos reformados"),
        "#demografia/envelhecimento",
    ),
    # ---------------------------------------------------------------- demografia
    Termo(
        "fecundidade",
        "Fecundidade",
        "A média de filhos que uma mulher teria na vida, nas condições de hoje. Abaixo de 2,1 "
        "a população deixa de se repor e, com o tempo, começa a diminuir.",
        ("taxa de fecundidade", "fecundidade", "filhos por mulher"),
        "#demografia",
    ),
    Termo(
        "dependencia",
        "Idosos por 100 em idade de trabalhar",
        "Quantas pessoas de 65 anos ou mais há para cada 100 de 15 a 64 anos. Quanto maior, "
        "menos gente em idade de trabalhar para cada aposentado.",
        ("razão de dependência", "idosos por 100"),
        "#demografia",
    ),
    Termo(
        "esperanca-de-vida",
        "Esperança de vida",
        "Quantos anos, em média, viveria quem nasce hoje, se o risco de morrer em cada idade "
        "continuasse o de hoje.",
        ("esperança de vida", "expectativa de vida"),
        "#demografia",
    ),
    Termo(
        "idade-mediana",
        "Idade mediana",
        "A idade que divide a população ao meio: metade é mais nova, metade mais velha.",
        ("idade mediana",),
        "#demografia",
    ),
    Termo(
        "piramide",
        "Pirâmide etária",
        "O desenho da população por idade, homens de um lado e mulheres do outro. Larga "
        "embaixo, população jovem; larga em cima, população velha.",
        ("pirâmide etária",),
        "#demografia",
    ),
]


class Verbete(BaseModel):
    id: str
    nome: str
    definicao: str
    formas: list[str]
    elo: str = ""


def verbetes() -> list[Verbete]:
    return [
        Verbete(id=t.id, nome=t.nome, definicao=t.definicao, formas=list(t.formas), elo=t.elo)
        for t in TERMOS
    ]


def gravar(saida: Path) -> int:
    lista = verbetes()
    texto = json.dumps([v.model_dump(exclude_defaults=True) for v in lista], ensure_ascii=False)
    (saida / "glossario.json").write_text(texto, encoding="utf-8")
    return len(lista)
