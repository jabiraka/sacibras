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
        ("taxa de investimento", "formação bruta de capital"),
        "#atividade/investimento",
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
        "ocupados. No longo prazo, é o que faz a renda subir.",
        ("produtividade", "PIB por ocupado", "PIB por pessoa ocupada"),
        "#demografia",
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
        ("preços administrados", "administrados", "preços livres"),
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
        "servico-da-divida",
        "Serviço da dívida",
        "O que se paga num período para a dívida: juros mais a parte do principal (amortização).",
        ("serviço da dívida",),
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
        "#riscos/estresse",
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
        ("FMI",),
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
