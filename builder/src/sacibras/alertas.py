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


EXPLICACOES: dict[str, Explicacao] = {
    # ---------------------------------------------------------------- contas públicas
    "dbgg": Explicacao(
        "Quanto União, estados e municípios devem, somando tudo, em proporção de tudo o que o "
        "país produz num ano.",
        "Quanto maior a dívida, mais o governo gasta com juros e menos espaço tem para reagir "
        "a uma crise.",
        "Juros mais altos para todos (quem empresta a um devedor grande cobra mais), dólar "
        "mais caro e, no limite, aumento de impostos ou corte de gastos às pressas.",
    ),
    "primario": Explicacao(
        "Receitas menos despesas do setor público nos últimos 12 meses, sem contar os juros.",
        "Déficit quer dizer que o governo gasta mais do que arrecada mesmo antes de pagar os "
        "juros: a diferença vira dívida nova.",
        "Dívida crescendo mais rápido que a economia e o mercado cobrando juro maior para "
        "financiar o governo.",
    ),
    "juros": Explicacao(
        "O que o setor público pagou de juros sobre a dívida em 12 meses, em proporção do PIB.",
        "É dinheiro que não vai para saúde, educação ou investimento, e que faz a dívida "
        "crescer sozinha quando não há superávit para cobri-lo.",
        "Mais dívida mesmo com as outras contas em ordem e pressão por ajuste fiscal.",
    ),
    "nominal": Explicacao(
        "O resultado primário menos os juros: quanto o governo precisou tomar emprestado em "
        "12 meses.",
        "Um déficit nominal grande quer dizer muitos títulos novos para o mercado comprar a "
        "cada ano.",
        "Juros mais altos para o governo rolar a dívida e dívida subindo em proporção do PIB.",
    ),
    "juro-menos-crescimento": Explicacao(
        "A diferença entre o juro real que a dívida paga e o crescimento real da economia.",
        "Quando o juro passa do crescimento, a dívida sobe em proporção do PIB sozinha, a "
        "menos que o governo faça superávit primário.",
        "A necessidade de um superávit maior a cada ano só para a dívida não subir.",
    ),
    "primario-que-falta": Explicacao(
        "A distância entre o resultado primário que deixaria a dívida parada e o resultado de "
        "hoje, em pontos do PIB.",
        "Mostra o tamanho do ajuste que faltaria nas contas para a dívida parar de subir.",
        "Quanto maior a distância, mais difícil o ajuste e mais tempo a dívida segue subindo.",
    ),
    "divida-selic": Explicacao(
        "A parte da dívida em títulos cujo juro acompanha a Selic (o Tesouro Selic).",
        "Quando o Banco Central sobe a Selic para conter a inflação, o custo dessa parte da "
        "dívida sobe no mesmo dia.",
        "Conta de juros do governo crescendo rápido justamente quando os juros sobem.",
    ),
    "prazo-da-divida": Explicacao(
        "Quanto tempo, em média, falta para os títulos da dívida vencerem.",
        "Prazo curto quer dizer que o governo precisa refinanciar muito em pouco tempo, aos "
        "juros do momento.",
        "Numa crise, refinanciar fica caro ou difícil (o chamado risco de rolagem).",
    ),
    # ---------------------------------------------------------------- câmbio e contas externas
    "reservas-cobertura": Explicacao(
        "Quantas vezes as reservas internacionais do Banco Central cobrem a dívida externa "
        "que vence em até um ano.",
        "As reservas são o colchão para pagar compromissos em dólar se o crédito de fora "
        "secar de repente.",
        "Com cobertura baixa, uma fuga de capitais pode fazer faltar dólar e o câmbio "
        "disparar, como nas crises de 1999 e 2002.",
    ),
    "reservas-importacoes": Explicacao(
        "Por quantos meses as reservas pagariam tudo o que o país importa.",
        "É a medida clássica do tamanho do colchão em moeda forte.",
        "Com reservas curtas, um choque externo obriga a cortar importações ou a deixar o "
        "dólar subir muito.",
    ),
    "conta-corrente": Explicacao(
        "O saldo de tudo o que o país compra, vende, paga e recebe do exterior em bens, "
        "serviços, lucros e juros, em 12 meses.",
        "Déficit grande quer dizer que o país depende de dinheiro de fora para fechar as contas.",
        "Se o dinheiro de fora parar de entrar, o dólar sobe e a economia precisa se ajustar "
        "às pressas.",
    ),
    "cobertura-idp": Explicacao(
        "O investimento direto que entra (estrangeiros abrindo ou comprando empresas aqui) "
        "menos o déficit externo.",
        "O investimento direto é o financiamento mais estável; se ele não cobre o déficit, o "
        "resto vem de dinheiro que sai com facilidade.",
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
        "gastar as reservas.",
        "Um estoque grande mostra que o BC precisou segurar o câmbio, e o expõe a perdas se o "
        "dólar subir.",
        "Prejuízo do Banco Central, que acaba nas contas do Tesouro, numa alta forte do dólar.",
    ),
    # ---------------------------------------------------------------- inflação
    "ipca": Explicacao(
        "A inflação oficial dos últimos 12 meses.",
        "Acima do teto da meta, o Banco Central tende a manter ou subir os juros, e o salário "
        "compra menos.",
        "Juros altos por mais tempo, crescimento menor e perda de poder de compra, mais forte "
        "para quem ganha menos.",
    ),
    "nucleos": Explicacao(
        "A inflação sem os preços que sobem e descem por motivos passageiros: a média das "
        "medidas de núcleo do Banco Central.",
        "Núcleo alto quer dizer inflação enraizada, mais difícil de baixar que um choque de "
        "alimento ou combustível.",
        "Juros altos por mais tempo para trazer a inflação de volta à meta.",
    ),
    "difusao": Explicacao(
        "A parte dos itens do IPCA que ficou mais cara no mês.",
        "Difusão alta quer dizer alta de preços generalizada, não de poucos produtos.",
        "Inflação mais persistente, que custa mais juros para cair.",
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
        "A diferença entre o juro que os bancos cobram nos empréstimos e o que pagam para "
        "conseguir o dinheiro.",
        "Spread em alta quer dizer, em boa parte, que os bancos veem mais risco de calote.",
        "Crédito mais caro para quem pega emprestado, o que freia consumo e investimento.",
    ),
    "comprometimento": Explicacao(
        "A parte da renda mensal das famílias que vai para as parcelas das dívidas.",
        "Quanto mais da renda vai para dívida, menos sobra para o resto, e mais difícil fica "
        "pagar se a renda cair.",
        "Consumo mais fraco e mais atrasos.",
    ),
    "endividamento": Explicacao(
        "Tudo o que as famílias devem aos bancos, em proporção da renda de 12 meses.",
        "Dívida alta deixa as famílias frágeis a juros maiores ou a perder o emprego.",
        "Menos consumo por anos, enquanto as famílias pagam o que devem.",
    ),
    "basileia": Explicacao(
        "O capital próprio dos bancos em proporção do que emprestaram e aplicaram, pesado "
        "pelo risco.",
        "É o colchão que absorve os prejuízos; perto do mínimo, o banco tem pouca folga.",
        "Bancos cortando crédito para se proteger e, no limite, risco de quebra.",
    ),
    # ---------------------------------------------------------------- mercado
    "vol-dolar": Explicacao(
        "Quanto o dólar balança de um dia para o outro, no último mês (21 dias úteis).",
        "Oscilação forte é sinal de incerteza e de investidores mudando de posição às pressas.",
        "Preços de importados e combustíveis mais instáveis, empresas adiando decisões e o "
        "Banco Central entrando no mercado.",
    ),
    "vol-ibovespa": Explicacao(
        "Quanto a bolsa balança de um dia para o outro, no último mês (21 dias úteis).",
        "Bolsa nervosa mostra investidores sem saber o que esperar de lucros e da economia.",
        "Empresas adiando investimentos e emissões de ações, e o patrimônio das pessoas oscilando.",
    ),
    "queda-ibovespa": Explicacao(
        "Quanto a bolsa está abaixo do maior valor que já atingiu, em porcentagem.",
        "Quedas grandes e longas costumam vir junto com expectativas piores para os lucros e "
        "a economia.",
        "Menos investimento e famílias se sentindo mais pobres.",
    ),
    # ---------------------------------------------------------------- longo prazo e energia
    "deficit-inss": Explicacao(
        "Quanto os benefícios do INSS superam as contribuições, em 12 meses, em proporção do PIB.",
        "Com a população envelhecendo, mais gente recebe e proporcionalmente menos contribui.",
        "Mais pressão sobre as contas públicas e novas reformas da previdência.",
    ),
    "beneficios-inss": Explicacao(
        "Quanto o INSS paga em aposentadorias, pensões e outros benefícios em 12 meses, em "
        "proporção do PIB.",
        "É a maior despesa do governo federal, e cresce com o envelhecimento e com o salário "
        "mínimo.",
        "Menos espaço no orçamento para o resto e déficit da previdência maior.",
    ),
    "reservatorios": Explicacao(
        "Quanta água há nos reservatórios das hidrelétricas, comparada com o mesmo mês dos "
        "outros anos.",
        "Reservatório baixo obriga a ligar as térmicas, que geram energia mais cara.",
        "Conta de luz mais cara (as bandeiras tarifárias), mais inflação e, num caso extremo, "
        "racionamento, como em 2001.",
    ),
}
