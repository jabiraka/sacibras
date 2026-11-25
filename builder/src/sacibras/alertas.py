"""O que cada indicador do painel de alerta quer dizer, por que ele é um sinal de alerta e no
que pode dar, em palavras de todo dia.

Pedido do Caio (14/11/2026): *"No painel de alerta [...] o que falta dizer é o que significa,
por que é um alerta, o que isso pode levar"*. A tela mostra os três textos quando a pessoa
abre a linha do indicador. Indicador novo no painel (`secoes/riscos.py`) ganha a explicação
aqui; o teste confere que nenhum fica sem.

Regra do texto: uma ou duas frases por campo, sem prever crise. "Pode levar a" diz o
caminho que a história já mostrou, não o que vai acontecer.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Explicacao:
    significa: str
    por_que: str
    pode_levar: str


NO_PAINEL: tuple[str, ...] = (
    # Contas públicas
    "dbgg",
    "primario-que-falta",
    "juro-menos-crescimento",
    "juros-sobre-receita",
    "vence-em-12-meses",
    # Câmbio e contas externas
    "reservas-cobertura",
    "conta-corrente",
    "cobertura-idp",
    # Inflação
    "ipca",
    "nucleos",
    "expectativa-12m",
    # Crédito e bancos
    "inadimplencia",
    "comprometimento",
    "basileia",
    "hiato-credito",
    # Mercado e longo prazo
    "vol-dolar",
    "deficit-inss",
)
"""Os indicadores que vão ao painel de alerta: um por pergunta (Caio, 16/11/2026: *"a parte
de riscos tem muitos alertas e outras coisas"*; eram 39). Saiu o que repetia outro: o
primário, os juros e o nominal em 12 meses (estão no "primário que falta" e nos juros sobre
a receita), a dívida atrelada à Selic e o prazo médio (a rolagem está no que vence em 12
meses), as reservas em meses de importação, a dívida externa líquida (o setor público é
credor), a dívida cambial e os swaps, a difusão e a implícita longa, a inadimplência de
pessoas e de empresas, os atrasos, o spread, o endividamento, os dois índices de liquidez,
a bolsa (volatilidade e queda), os benefícios do INSS e os reservatórios. O número de cada
um continua no assunto dele; a explicação fica em `EXPLICACOES`, para voltar sem reescrever."""

EXPLICACOES: dict[str, Explicacao] = {
    # ---------------------------------------------------------------- contas públicas
    "dbgg": Explicacao(
        "Quanto União, estados e municípios devem, em proporção do PIB.",
        "Quanto maior a dívida, mais juros e menos espaço para reagir a uma crise.",
        "Juros mais altos para todos, dólar mais caro e, no limite, imposto maior ou corte de "
        "gastos às pressas.",
    ),
    "primario": Explicacao(
        "Receitas menos despesas do setor público em 12 meses, sem contar os juros.",
        "Déficit é gastar mais do que arrecada antes dos juros: a diferença vira dívida nova.",
        "Dívida crescendo mais rápido que a economia e juro maior para financiar o governo.",
    ),
    "juros": Explicacao(
        "O que o setor público pagou de juros sobre a dívida em 12 meses, em % do PIB.",
        "É dinheiro que não vai para saúde, educação ou investimento, e faz a dívida crescer "
        "sozinha sem superávit.",
        "Mais dívida mesmo com as outras contas em ordem e pressão por ajuste fiscal.",
    ),
    "nominal": Explicacao(
        "O primário menos os juros: quanto o governo tomou emprestado em 12 meses.",
        "Déficit nominal grande quer dizer muitos títulos novos a cada ano.",
        "Juro maior para rolar a dívida e dívida subindo em % do PIB.",
    ),
    "juro-menos-crescimento": Explicacao(
        "A diferença entre o juro real que a dívida paga e o crescimento real da economia.",
        "Com o juro acima do crescimento, a dívida sobe em % do PIB sozinha, a menos que haja "
        "superávit primário.",
        "Um superávit maior a cada ano só para a dívida não subir.",
    ),
    "primario-que-falta": Explicacao(
        "A distância entre o primário que deixaria a dívida parada e o de hoje, em pontos do PIB.",
        "É o tamanho do ajuste que falta para a dívida parar de subir.",
        "Quanto maior, mais difícil o ajuste e mais tempo a dívida segue subindo.",
    ),
    "divida-selic": Explicacao(
        "A parte da dívida em títulos cujo juro acompanha a Selic (o Tesouro Selic).",
        "Quando o Banco Central sobe a Selic, o custo dessa parte sobe no mesmo dia.",
        "Conta de juros do governo crescendo rápido justamente quando os juros sobem.",
    ),
    "prazo-da-divida": Explicacao(
        "Quanto tempo, em média, falta para os títulos da dívida vencerem.",
        "Prazo curto é muito a refinanciar em pouco tempo, ao juro do momento.",
        "Numa crise, refinanciar fica caro ou difícil (o risco de rolagem).",
    ),
    "juros-sobre-receita": Explicacao(
        "Quanto da receita líquida da União, em 12 meses, vai para os juros da dívida.",
        "Cada real em juros não paga saúde, educação ou investimento; e essa parte cresce quando a"
        " Selic sobe.",
        "Orçamento preso aos juros, pressão para cortar gastos ou subir impostos e nota de crédito"
        " rebaixada.",
    ),
    "vence-em-12-meses": Explicacao(
        "A parte da dívida bruta que vence nos próximos 12 meses e precisa ser paga ou trocada por"
        " nova.",
        "Quanto mais vence de uma vez, mais o governo depende de quem compre títulos novos, ao "
        "juro do momento.",
        "Numa crise de confiança, refinanciar fica caro ou difícil, como em 2002.",
    ),
    # ---------------------------------------------------------------- câmbio e contas externas
    "reservas-cobertura": Explicacao(
        "Quantas vezes as reservas do Banco Central cobrem a dívida externa que vence em até um "
        "ano.",
        "As reservas são o colchão em dólar se o crédito de fora secar de repente.",
        "Com cobertura baixa, uma fuga de capitais pode fazer faltar dólar, como em 1999 e 2002.",
    ),
    "reservas-importacoes": Explicacao(
        "Por quantos meses as reservas pagariam tudo o que o país importa.",
        "É a medida clássica do tamanho do colchão em moeda forte.",
        "Com reservas curtas, um choque externo obriga a cortar importações ou a deixar o dólar "
        "subir muito.",
    ),
    "conta-corrente": Explicacao(
        "O saldo de tudo o que o país compra, vende, paga e recebe do exterior, em 12 meses.",
        "Déficit grande quer dizer depender de dinheiro de fora para fechar as contas.",
        "Se esse dinheiro parar de entrar, o dólar sobe e a economia se ajusta às pressas.",
    ),
    "cobertura-idp": Explicacao(
        "O investimento direto que entra (estrangeiros abrindo ou comprando empresas aqui) menos o"
        " déficit externo.",
        "É o financiamento mais estável; se não cobre o déficit, o resto é dinheiro que sai fácil.",
        "Mais exposição a uma saída rápida de capitais e a saltos do dólar.",
    ),
    "divida-externa-liquida": Explicacao(
        "O que o setor público deve ao exterior menos o que tem lá fora, as reservas "
        "inclusive. Negativo quer dizer credor.",
        "Um governo devedor em moeda forte vê a dívida subir quando o real se desvaloriza.",
        "Dívida pública subindo junto com o dólar numa crise.",
    ),
    "divida-cambial": Explicacao(
        "A parte da dívida em títulos que acompanha o dólar.",
        "Quando o dólar sobe, essa dívida cresce em reais.",
        "Dívida pública maior justamente nas crises, quando o dólar dispara (como em 2002).",
    ),
    "swaps-cambiais": Explicacao(
        "Contratos em que o Banco Central paga a variação do dólar a quem quer proteção, sem "
        "gastar reservas.",
        "Estoque grande mostra o BC segurando o câmbio, exposto a perdas se o dólar subir.",
        "Prejuízo do Banco Central, que cai nas contas do Tesouro, numa alta forte do dólar.",
    ),
    # ---------------------------------------------------------------- inflação
    "ipca": Explicacao(
        "A inflação oficial dos últimos 12 meses.",
        "Acima do teto da meta, o Banco Central tende a manter ou subir os juros, e o salário "
        "compra menos.",
        "Juros altos por mais tempo, crescimento menor e perda de poder de compra, maior para quem"
        " ganha menos.",
    ),
    "nucleos": Explicacao(
        "A inflação sem os preços que oscilam por motivos passageiros: a média dos núcleos do "
        "Banco Central.",
        "Núcleo alto é inflação enraizada, mais difícil de baixar que um choque de alimento ou "
        "combustível.",
        "Juros altos por mais tempo para trazer a inflação de volta à meta.",
    ),
    "difusao": Explicacao(
        "A parte dos itens do IPCA que ficou mais cara no mês.",
        "Difusão alta quer dizer alta de preços generalizada, não de poucos produtos.",
        "Inflação mais persistente, que custa mais juros para cair.",
    ),
    "expectativa-12m": Explicacao(
        "A inflação que o mercado espera para os próximos 12 meses (mediana do Focus) menos a "
        "meta, em pontos.",
        "Quem espera inflação acima da meta reajusta preços e salários por ela, e a inflação vem "
        "mesmo.",
        "Juros altos por mais tempo para trazer as expectativas de volta à meta.",
    ),
    "implicita-longa": Explicacao(
        "A inflação média dos próximos 8 anos embutida nos títulos do Tesouro (prefixado contra "
        "IPCA+) menos a meta.",
        "Mostra se quem empresta por muitos anos acredita na meta; inclui um prêmio pelo risco de "
        "errar.",
        "Juro longo mais alto para governo, empresas e crédito imobiliário.",
    ),
    # ---------------------------------------------------------------- crédito e bancos
    "inadimplencia": Explicacao(
        "A parte do crédito com parcela atrasada há mais de 90 dias.",
        "Calote em alta mostra famílias e empresas apertadas e deixa os bancos mais cautelosos.",
        "Crédito mais caro e escasso, menos consumo e investimento, e perdas para os bancos.",
    ),
    "inadimplencia-pf": Explicacao(
        "A parte do crédito às pessoas com parcela atrasada há mais de 90 dias.",
        "Mostra famílias sem conseguir pagar as dívidas.",
        "Nome sujo, menos consumo e bancos mais seletivos para emprestar às famílias.",
    ),
    "inadimplencia-pj": Explicacao(
        "A parte do crédito às empresas com parcela atrasada há mais de 90 dias.",
        "Mostra empresas com o caixa apertado.",
        "Demissões, recuperações judiciais e menos crédito para as empresas.",
    ),
    "atrasos": Explicacao(
        "A parte do crédito com atraso entre 15 e 90 dias: o atraso que ainda não virou "
        "inadimplência.",
        "É o termômetro adiantado: costuma subir antes da inadimplência.",
        "Inadimplência maior nos meses seguintes.",
    ),
    "spread": Explicacao(
        "A diferença entre o juro que os bancos cobram e o que pagam para conseguir o dinheiro.",
        "Spread em alta quer dizer, em boa parte, mais risco de calote visto pelos bancos.",
        "Crédito mais caro, o que freia consumo e investimento.",
    ),
    "comprometimento": Explicacao(
        "A parte da renda mensal das famílias que vai para as parcelas das dívidas.",
        "Mais renda em dívida deixa menos para o resto e dificulta pagar se a renda cair.",
        "Consumo mais fraco e mais atrasos.",
    ),
    "endividamento": Explicacao(
        "Tudo o que as famílias devem aos bancos, em proporção da renda de 12 meses.",
        "Dívida alta deixa as famílias frágeis a juros maiores ou a perder o emprego.",
        "Menos consumo por anos, enquanto as famílias pagam o que devem.",
    ),
    "basileia": Explicacao(
        "O capital próprio dos bancos sobre o que emprestaram e aplicaram, pesado pelo risco.",
        "É o colchão que absorve os prejuízos; perto do mínimo, o banco tem pouca folga.",
        "Bancos cortando crédito para se proteger e, no limite, risco de quebra.",
    ),
    "hiato-credito": Explicacao(
        "Quanto o crédito a famílias e empresas, em % do PIB, está acima ou abaixo da tendência, "
        "pela conta do BIS.",
        "Crédito muito acima da tendência é endividamento mais rápido do que a economia aguenta.",
        "No mundo, hiatos altos costumam vir antes de crises bancárias e recessão.",
    ),
    "liquidez": Explicacao(
        "O dinheiro de pronto dos bancos sobre o que poderiam perder em 30 dias de saques, pela "
        "conta do Banco Central. Acima de 1, sobra.",
        "Com pouco dinheiro de pronto, o banco pode não pagar os saques numa desconfiança, mesmo "
        "com capital.",
        "Bancos vendendo ativos às pressas, crédito cortado e, no limite, socorro do Banco "
        "Central.",
    ),
    "liquidez-lcr": Explicacao(
        "A mesma ideia do Índice de Liquidez na regra de Basileia (LCR): ativos líquidos sobre 30 "
        "dias de saídas no estresse, em %.",
        "Abaixo de 100 %, o banco não aguentaria sozinho 30 dias de saques fortes.",
        "Bancos segurando crédito para guardar caixa e mais dependência do Banco Central numa "
        "crise.",
    ),
    # ---------------------------------------------------------------- mercado
    "vol-dolar": Explicacao(
        "Quanto o dólar balança de um dia para o outro, no último mês (21 dias úteis).",
        "Oscilação forte é sinal de incerteza e de investidores mudando de posição às pressas.",
        "Preço de importados e combustíveis instável, empresas adiando decisões e o Banco Central "
        "no mercado.",
    ),
    # ---------------------------------------------------------------- longo prazo e energia
    "deficit-inss": Explicacao(
        "Quanto os benefícios do INSS superam as contribuições, em 12 meses, em % do PIB.",
        "Com a população envelhecendo, mais gente recebe e proporcionalmente menos contribui.",
        "Mais pressão sobre as contas públicas e novas reformas da previdência.",
    ),
    "beneficios-inss": Explicacao(
        "O que o INSS paga em aposentadorias, pensões e outros benefícios em 12 meses, em % do "
        "PIB.",
        "É a maior despesa federal, e cresce com o envelhecimento e com o salário mínimo.",
        "Menos espaço no orçamento para o resto e déficit da previdência maior.",
    ),
    "reservatorios": Explicacao(
        "A água nos reservatórios das hidrelétricas, contra o mesmo mês dos outros anos.",
        "Reservatório baixo obriga a ligar as térmicas, que geram energia mais cara.",
        "Conta de luz mais cara (as bandeiras tarifárias), mais inflação e, num extremo, "
        "racionamento, como em 2001.",
    ),
}
