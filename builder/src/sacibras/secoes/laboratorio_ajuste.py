"""Laboratório, as peças de pressão e de ajuste fiscal (Caio, 19/11/2026: *"essas métricas
vão nos ajudar a ver o desenrolar e de onde está vindo se tiver uma crise, bem como oq
poderíamos ter feito pra prevenir, o foco principal hj está no ajuste fiscal"*).

Três peças, com as contas em `modelos/ajuste.py`:
- o dólar: quanto da alta (ou da queda) veio de fora e quanto é só do Brasil;
- a dívida se o primário tivesse sido outro desde 2014 (contabilidade, não previsão);
- o primário que o Focus esperava anos antes contra o que veio.

Nada aqui é número oficial nem previsão: são contas nossas sobre o que já aconteceu.
"""

from __future__ import annotations

from datetime import date, timedelta

from sacibras import contas, leis, relatorios
from sacibras.calendario import dia_util
from sacibras.fontes import bcb_fiscal, bcb_focus, fred, tesouro_direto, tesouro_rtn
from sacibras.modelos import ajuste, estatistica
from sacibras.schema import Cartao, Grafico, LinhaTabela, Tabela
from sacibras.secoes.base import MESES, Contexto, br, grafico, serie
from sacibras.tipos import Ponto

CONTA = "conta nossa"
Pecas = tuple[list[Cartao], list[Grafico], list[Tabela]]


def _sinal(v: float, casas: int = 1) -> str:
    return ("+" if v > 0 else "") + br(v, casas).replace("-", "−")


# ------------------------------------------------------------------ o dólar: mundo ou Brasil

INICIO_DOLAR = date(2006, 1, 1)
"""O índice do dólar contra os emergentes começa em 02/01/2006."""
JANELA = 252
JANELA_BETA = 1260


def _mes(d: date) -> str:
    return f"{MESES[d.month - 1]}/{d.year}"


def dolar(ctx: Contexto) -> Pecas:
    brl = dict(fred.serie(fred.REAL_POR_DOLAR, INICIO_DOLAR))
    eme = dict(fred.serie(fred.DOLAR_EMERGENTES, INICIO_DOLAR))
    dias = sorted(set(brl) & set(eme))
    y, x = ajuste.variacoes(brl, dias), ajuste.variacoes(eme, dias)
    partes = ajuste.repartir_dolar(dias[1:], y, x, janela=JANELA, janela_beta=JANELA_BETA)
    hoje = partes[-1]
    ctx.memo["laboratorio_dolar_diario"] = {
        p.dia: p.do_brasil
        for p in ajuste.repartir_dolar(dias[1:], y, x, janela=1, janela_beta=JANELA_BETA)
    }
    beta, b_lo, b_hi = ajuste.beta_com_intervalo(y, x, JANELA_BETA)
    fora_log = sum(x[-JANELA:])
    lo, hi = ajuste.faixa_do_brasil(y, x, janela=JANELA)
    pontas = (ajuste.composta(lo), ajuste.composta(hi))
    total, de_fora, do_brasil = (
        ajuste.composta(hoje.total),
        ajuste.composta(hoje.de_fora),
        ajuste.composta(hoje.do_brasil),
    )
    fonte = f"{fred.FONTE_CAMBIO}; {CONTA}"
    cartoes = [
        Cartao(
            id="dolar-do-brasil",
            rotulo="Dólar em 12 meses: a parte que é só do Brasil",
            valor=round(do_brasil, 2),
            unidade="%",
            casas=1,
            referencia=hoje.dia,
            periodicidade="D",
            detalhe=f"de {_sinal(pontas[0])} a {_sinal(pontas[1])} %; dólar: {_sinal(total)} %",
            fonte=fonte,
            procedencia="calculado",
            secao="laboratorio",
            mini=[(p.dia, round(ajuste.composta(p.do_brasil), 2)) for p in partes[-756::13]],
        ),
        Cartao(
            id="dolar-de-fora",
            rotulo="Dólar em 12 meses: a parte que veio de fora",
            valor=round(de_fora, 2),
            unidade="%",
            casas=1,
            referencia=hoje.dia,
            periodicidade="D",
            detalhe=f"dólar contra os emergentes: {_sinal(ajuste.composta(fora_log))} %",
            fonte=fonte,
            procedencia="calculado",
            secao="laboratorio",
            mini=[(p.dia, round(ajuste.composta(p.de_fora), 2)) for p in partes[-756::13]],
        ),
        Cartao(
            id="dolar-beta",
            rotulo="O dólar no Brasil a cada 1 % do dólar contra os emergentes",
            valor=round(beta, 3),
            unidade="%",
            casas=1,
            referencia=hoje.dia,
            periodicidade="D",
            detalhe=f"90 %: de {br(b_lo)} a {br(b_hi)} %; últimos 5 anos",
            fonte=fonte,
            procedencia="calculado",
            secao="laboratorio",
            mini=[(p.dia, round(p.beta, 3)) for p in partes[::63]],
        ),
    ]
    # Um ponto por semana no gráfico (a conta é diária), e sempre o último dia.
    semanais = [*partes[:-1][::5], hoje]
    lado = "subiu" if total >= 0 else "caiu"
    graficos = [
        grafico(
            "dolar-mundo-brasil",
            "O dólar em 12 meses: o que veio de fora e o que é do Brasil",
            [
                serie(
                    "brasil",
                    "Só do Brasil",
                    [(p.dia, ajuste.composta(p.do_brasil)) for p in semanais],
                ),
                serie(
                    "fora",
                    "De fora (o dólar contra os emergentes)",
                    [(p.dia, ajuste.composta(p.de_fora)) for p in semanais],
                ),
                serie(
                    "total",
                    "Dólar no Brasil, variação em 12 meses",
                    [(p.dia, ajuste.composta(p.total)) for p in semanais],
                ),
            ],
            unidade="% em 12 meses",
            casas=1,
            periodicidade="D",
            fonte=fonte,
            janela_anos=10,
            manchete=(
                f"Em 12 meses até {hoje.dia:%d/%m/%Y}, o dólar {lado} "
                f"{br(abs(total))} % no Brasil: {_sinal(de_fora)} % de fora e "
                f"{_sinal(do_brasil)} % só do Brasil"
            ),
            nota=(
                "O dólar sobe no Brasil por dois caminhos: porque sobe contra todo mundo, ou "
                "por algo daqui. De fora: a variação do dólar contra uma cesta de moedas de "
                "países emergentes (índice do Federal Reserve) vezes o quanto o real costuma "
                "acompanhá-la, medido nos cinco anos anteriores (uma reta por mínimos "
                "quadrados sobre as variações de cada dia). Só do Brasil: o resto, que junta "
                "contas públicas, política, juro e preço do que o país exporta; esta conta não "
                "separa um do outro. As duas partes se compõem (multiplicam) no total. A faixa do "
                "número de hoje vai do menor ao maior resultado com o real medido em 2, 5 e 10 "
                "anos; ela é estreita quando o dólar lá fora quase não se mexeu. O real "
                'está na cesta com peso pequeno, o que puxa um pouco para "de fora".'
            ),
            largura="inteira",
        )
    ]
    altas = ajuste.maiores_altas(partes, quantas=5, afastamento=JANELA)
    linhas = [
        LinhaTabela(
            rotulo=f"até {_mes(p.dia)}" if p is not hoje else f"até {p.dia:%d/%m/%Y} (hoje)",
            valores=[
                round(ajuste.composta(p.total), 1),
                round(ajuste.composta(p.de_fora), 1),
                round(ajuste.composta(p.do_brasil), 1),
            ],
            unidade="",
            casas=1,
        )
        for p in ([hoje, *altas] if hoje not in altas else altas)
    ]
    tabela = Tabela(
        id="dolar-altas",
        titulo="As maiores altas do dólar em 12 meses: de onde vieram",
        subtitulo=(
            f"as cinco maiores desde {partes[0].dia.year}, uma por episódio, e os 12 meses até "
            "hoje; variação do dólar no Brasil"
        ),
        colunas=["Dólar no Brasil (%)", "De fora (%)", "Só do Brasil (%)"],
        linhas=linhas,
        fonte=fonte,
        nota=(
            "Cada linha são os 12 meses que terminam na data. A mesma conta do gráfico: de "
            "fora é o dólar contra os emergentes vezes o quanto o real costumava acompanhá-lo "
            "nos cinco anos até a data. Alta com a parte do Brasil grande é a que não se "
            "explica pelo que aconteceu com as outras moedas."
        ),
    )
    return cartoes, graficos, [tabela]


# ------------------------------------------------------------------ a dívida com outro primário

DESDE = 2014
"""O primeiro ano de déficit primário do setor público desde o início da série."""
POUPADO = (2020,)
"""O déficit da pandemia fica como foi nos dois cenários: nenhuma regra o teria evitado."""
PISO = 1.0
"""O segundo cenário: primário de pelo menos 1 % do PIB em todo ano (de 2003 a 2013 a média
foi perto de 3 %; um piso mais alto que isso levaria a conta longe demais do que ela mede)."""


def _taxa_implicita(ctx: Contexto) -> list[Ponto]:
    if "taxa_implicita_dbgg" not in ctx.memo:
        ctx.memo["taxa_implicita_dbgg"] = bcb_fiscal.taxa_implicita_dbgg()
    taxa: list[Ponto] = ctx.memo["taxa_implicita_dbgg"]
    return taxa


def divida(ctx: Contexto) -> Pecas:
    dbgg = ajuste.ultimo_de_cada_ano(ctx.sgs("DBGG", 30))
    primario = ajuste.ultimo_de_cada_ano(contas.escalar(ctx.sgs("NFSP_PRIMARIO_12M", 30), -1))
    juro = ajuste.ultimo_de_cada_ano(_taxa_implicita(ctx))
    pib = ajuste.ultimo_de_cada_ano(ctx.sgs("PIB_12M", 30))
    crescimento = {a: (pib[a] / pib[a - 1] - 1) * 100 for a in pib if a - 1 in pib}
    anos = [a for a in sorted(dbgg) if a >= DESDE]
    cenarios = {
        "sem-deficit": (
            "Sem déficit primário (zero nos anos de déficit)",
            {a: max(primario[a], 0.0) for a in anos if a in primario and a not in POUPADO},
        ),
        "um": (
            f"Com primário de pelo menos {br(PISO, 0)} % do PIB em todo ano",
            {a: max(primario[a], PISO) for a in anos if a in primario and a not in POUPADO},
        ),
    }
    contas_ = {
        k: ajuste.divida_com_outro_primario(dbgg, juro, crescimento, primario, outro, DESDE)
        for k, (_, outro) in cenarios.items()
    }
    ultimo = max(contas_["sem-deficit"])
    usados = [a for a in anos if a <= ultimo]
    base = DESDE - 1
    fonte = (
        f"{ctx.fonte_sgs('DBGG', 'NFSP_PRIMARIO_12M', 'PIB_12M')}; {bcb_fiscal.FONTE_TAXA}; {CONTA}"
    )

    def pontos(valores: dict[int, float]) -> list[Ponto]:
        return [(date(base, 1, 1), dbgg[base]), *((date(a, 1, 1), valores[a]) for a in usados)]

    sem = contas_["sem-deficit"][ultimo]
    cartoes = [
        Cartao(
            id="divida-sem-deficit",
            rotulo=f"Dívida bruta em {ultimo} sem os déficits primários desde {DESDE}",
            valor=round(sem, 2),
            unidade="% do PIB",
            casas=1,
            referencia=date(ultimo, 12, 1),
            periodicidade="A",
            detalhe=f"foi {br(dbgg[ultimo])} %; conta sem efeito no juro e no PIB",
            fonte=fonte,
            procedencia="calculado",
            secao="laboratorio",
        )
    ]
    graficos = [
        grafico(
            "divida-outro-primario",
            f"A dívida bruta se o primário tivesse sido outro desde {DESDE}",
            [
                serie("realizada", "Dívida bruta (o que aconteceu)", pontos(dbgg)),
                *(
                    serie(k, nome, pontos(contas_[k]), papel="previsao")
                    for k, (nome, _) in cenarios.items()
                ),
            ],
            unidade="% do PIB",
            casas=1,
            periodicidade="A",
            fonte=fonte,
            manchete=(
                f"Sem os déficits primários desde {DESDE}, a dívida bruta de {ultimo} seria de "
                f"{br(sem)} % do PIB, e não de {br(dbgg[ultimo])} % (conta de contabilidade)"
            ),
            nota=(
                "Não é previsão: é a dívida refeita para trás, trocando só o primário. Cada "
                "real de déficit que não houve deixa de virar dívida e deixa de render o juro "
                "que a dívida pagou em cada ano (a taxa implícita, do Banco Central), com o "
                f"PIB como foi. O déficit de {POUPADO[0]}, o da pandemia, fica como foi. A "
                "conta tem dois erros conhecidos, de sinais opostos, que os dados daqui não "
                "medem: com dívida menor o juro provavelmente teria sido menor (a dívida "
                "ficaria abaixo da linha), e com gasto menor ou imposto maior o PIB poderia "
                "ter crescido menos por um tempo (ficaria acima). Vale para o resultado do "
                "setor público inteiro; não diz como se chegaria a ele."
            ),
        )
    ]
    linhas = [
        LinhaTabela(
            rotulo="O que aconteceu",
            valores=[
                round(dbgg[ultimo], 1),
                None,
                round(sum(primario[a] for a in usados) / len(usados), 2),
            ],
            unidade="",
            casas=1,
        )
    ]
    for k, (nome, outro) in cenarios.items():
        feito = [outro.get(a, primario[a]) for a in usados]
        linhas.append(
            LinhaTabela(
                rotulo=nome,
                valores=[
                    round(contas_[k][ultimo], 1),
                    round(contas_[k][ultimo] - dbgg[ultimo], 1),
                    round(sum(feito) / len(feito), 2),
                ],
                unidade="",
                casas=1,
            )
        )
    tabela = Tabela(
        id="divida-outro-primario",
        titulo=f"A dívida bruta de {ultimo} com outro primário desde {DESDE}",
        subtitulo=(
            f"% do PIB; o primário médio é o de {DESDE} a {ultimo}, com {POUPADO[0]} como foi"
        ),
        colunas=[
            f"Dívida em {ultimo}",
            "Diferença para o que aconteceu (pp)",
            "Primário médio no período",
        ],
        linhas=linhas,
        fonte=fonte,
        nota=(
            "A diferença é a soma dos déficits que não teriam havido, mais o juro sobre eles, "
            "com o juro e o crescimento de cada ano como foram. O efeito de um primário maior "
            "sobre o juro e sobre o PIB não entra: os dados daqui não o medem."
        ),
    )
    return cartoes, graficos, [tabela]


# ------------------------------------------------------------------ o prometido e o que veio

HORIZONTES = (1, 2, 3, 4)
PRIMEIRA_SAFRA = 2001
EXCECAO = 2020


def _safras(indicador: str, ate: int) -> dict[int, dict[int, float]]:
    """{ano: {ano-alvo: mediana}} do Focus de meados de dezembro de cada ano (a última coleta
    entre os dias 10 e 16)."""
    datas = [date(a, 12, d) for a in range(PRIMEIRA_SAFRA, ate + 1) for d in range(10, 17)]
    coletas: dict[date, dict[int, float]] = {}
    for i in range(0, len(datas), 84):  # o endereço não aguenta todas as datas de uma vez
        coletas |= bcb_focus.anuais_nas_datas(indicador, datas[i : i + 84])
    saida: dict[int, dict[int, float]] = {}
    for dia in sorted(coletas):
        saida[dia.year] = coletas[dia]
    return saida


def promessa(ctx: Contexto) -> Pecas:
    realizado = ajuste.ultimo_de_cada_ano(contas.escalar(ctx.sgs("NFSP_PRIMARIO_12M", 30), -1))
    safras = _safras("Resultado primário", ctx.hoje.year - 1)
    erros = {h: ajuste.erro_por_horizonte(safras, realizado, h) for h in HORIZONTES}
    sem = {h: ajuste.erro_por_horizonte(safras, realizado, h, sem=[EXCECAO]) for h in HORIZONTES}
    dois = erros[2]
    if dois is None:
        raise ValueError("poucas safras do Focus para o primário")
    ultimo = max(realizado)
    fonte = (
        "Banco Central (Focus, mediana de dezembro de cada ano; "
        f"{ctx.fonte_sgs('NFSP_PRIMARIO_12M')}); {CONTA}"
    )
    cartoes = [
        Cartao(
            id="primario-prometido",
            rotulo="Primário: o esperado dois anos antes menos o que veio",
            valor=round(dois.media, 2),
            unidade="pp do PIB",
            casas=1,
            referencia=date(ultimo, 12, 1),
            periodicidade="A",
            detalhe=(
                f"90 %: de {_sinal(dois.de)} a {_sinal(dois.ate)} pp; "
                f"acima em {dois.otimistas} de {len(dois.anos)} anos"
            ),
            fonte=fonte,
            procedencia="calculado",
            secao="laboratorio",
        )
    ]
    series = [
        serie(
            "realizado",
            "Primário realizado",
            [(date(a, 1, 1), v) for a, v in sorted(realizado.items()) if a > PRIMEIRA_SAFRA],
        )
    ]
    for h, nome in ((1, "um ano antes"), (2, "dois anos antes"), (4, "quatro anos antes")):
        previsto = ajuste.previsto_antes(safras, h)
        series.append(
            serie(
                f"antes-{h}",
                f"O que o Focus esperava {nome}",
                [(date(a, 1, 1), v) for a, v in sorted(previsto.items()) if a <= ultimo],
            )
        )
    try:
        agora = bcb_focus.mediana_anual_hoje("Resultado primário")
    except Exception as erro:
        print(f"    laboratório: sem o Focus de hoje para o primário ({str(erro)[:100]})")
        agora = {}
    futuros = [(date(a, 1, 1), v) for a, v in sorted(agora.items()) if ultimo < a <= ultimo + 5]
    if futuros:
        series.append(serie("focus-hoje", "O que o Focus espera hoje", futuros, papel="previsao"))
    lado = "acima" if dois.media > 0 else "abaixo"
    graficos = [
        grafico(
            "primario-prometido",
            "O primário que o mercado esperava e o que veio",
            series,
            unidade="% do PIB",
            casas=1,
            periodicidade="A",
            fonte=fonte,
            manchete=(
                f"Dois anos antes, o Focus esperava em média {br(abs(dois.media))} pp do PIB "
                f"de primário {lado} do que veio ({dois.anos[0]} a {dois.anos[-1]})"
            ),
            nota=(
                "Cada linha de expectativa mostra, no ano a que se refere, a mediana que os "
                "analistas do Focus davam para o resultado primário do setor público em "
                "dezembro de um, dois ou quatro anos antes. Linha de expectativa acima do "
                "realizado: esperava-se um resultado melhor do que o que veio. É a "
                "expectativa do mercado, que lê o que o governo anuncia; a meta de cada "
                "orçamento contra o realizado ainda não está aqui. O erro junta choques que "
                f"ninguém previa ({EXCECAO}) e ajuste que se esperava e não veio; a tabela "
                f"refaz a conta sem {EXCECAO}."
            ),
        )
    ]
    linhas = []
    for nome, conjunto in (("Todos os anos", erros), (f"Sem {EXCECAO}", sem)):
        for h in HORIZONTES:
            e = conjunto[h]
            if e is None:
                continue
            linhas.append(
                LinhaTabela(
                    rotulo=f"{h} ano{'s' if h > 1 else ''} antes ({len(e.anos)} anos)",
                    valores=[
                        round(e.media, 2),
                        round(e.de, 2),
                        round(e.ate, 2),
                        round(e.otimistas / len(e.anos) * 100, 0),
                    ],
                    unidade="",
                    casas=1,
                    grupo=nome,
                )
            )
    tabela = Tabela(
        id="primario-erro-horizonte",
        titulo="Quanto o primário esperado passou do que veio, conforme a antecedência",
        subtitulo=(
            f"esperado pelo Focus menos realizado, pp do PIB, anos de {dois.anos[0]} a "
            f"{dois.anos[-1]}; positivo: esperava-se mais"
        ),
        colunas=["Média", "90 %: de", "até", "Anos com o esperado acima (%)"],
        linhas=linhas,
        fonte=fonte,
        nota=(
            "Média do erro com o intervalo de 90 % (erro de Newey-West, porque os erros de "
            "anos vizinhos andam juntos). São duas dezenas de anos e uns poucos, como 2015 e "
            "2016, pesam muito: intervalo que encosta no zero quer dizer que o viés não se "
            "distingue do acaso. Realizado: o resultado primário do setor público consolidado "
            "em dezembro, como o Banco Central publica hoje."
        ),
    )
    return cartoes, graficos, [tabela]


# ------------------------------------------------------------------ os ajustes que já houve

MINIMO_DO_EPISODIO = 1.0
"""Só entra a sequência de anos em que o primário andou pelo menos 1 pp do PIB."""


def episodios(ctx: Contexto) -> Pecas:
    rtn = tesouro_rtn.serie_historica()
    pib = ctx.sgs("PIB_12M", 32)
    receita = ajuste.ultimo_de_cada_ano(contas.em_pct_do_pib(rtn["receita_liquida"], pib))
    despesa = ajuste.ultimo_de_cada_ano(contas.em_pct_do_pib(rtn["despesa_total"], pib))
    primario = {a: receita[a] - despesa[a] for a in receita if a in despesa}
    linhas: list[LinhaTabela] = []
    for melhora, grupo in ((True, "Quando o primário melhorou"), (False, "Quando piorou")):
        for de, ate in ajuste.corridas(primario, MINIMO_DO_EPISODIO):
            mudanca = primario[ate] - primario[de]
            if (mudanca > 0) != melhora:
                continue
            linhas.append(
                LinhaTabela(
                    rotulo=f"{de} a {ate}",
                    valores=[
                        round(primario[de], 1),
                        round(primario[ate], 1),
                        round(mudanca, 1),
                        round(receita[ate] - receita[de], 1),
                        round(-(despesa[ate] - despesa[de]), 1),
                    ],
                    unidade="",
                    casas=1,
                    grupo=grupo,
                )
            )
    if not linhas:
        raise ValueError("RTN: nenhum episódio de mudança do primário")
    tabela = Tabela(
        id="primario-episodios",
        titulo="Quando o primário mudou: veio da receita ou da despesa?",
        subtitulo=(
            f"Governo Central, % do PIB, de {min(primario)} a {max(primario)}; sequências de "
            f"anos em que o primário andou {br(MINIMO_DO_EPISODIO, 0)} pp ou mais para o mesmo lado"
        ),
        colunas=[
            "Primário no ano de partida",
            "No ano de chegada",
            "Mudança (pp)",
            "Pela receita (pp)",
            "Pela despesa (pp)",
        ],
        linhas=linhas,
        fonte=(
            "Tesouro Nacional, Resultado do Tesouro Nacional (série histórica, tabela 1.1); "
            f"PIB: {ctx.fonte_sgs('PIB_12M')}; {CONTA}"
        ),
        nota=(
            "Primário = receita líquida menos despesa total, as duas em % do PIB de cada ano; "
            "as duas últimas colunas somam a mudança. Pela receita: quanto a receita subiu. "
            "Pela despesa: quanto a despesa caiu (negativo: ela subiu). A conta mostra por "
            "onde o resultado mudou, não por quê: receita sobe com imposto novo, mas também "
            "com inflação, commodities e receita de uma vez só; despesa em % do PIB cai "
            "quando o PIB cresce mais que ela. 2020 e a volta de 2021 são a pandemia."
        ),
    )
    return [], [], [tabela]


# ------------------------------------------------------------------ a dívida que se espera

SAFRAS_NO_GRAFICO = 4
"""Quantas safras antigas do Focus cabem no gráfico (uma a cada dois anos), além da de hoje."""
INDICADOR_DIVIDA = "Dívida bruta do governo geral"


def divida_esperada(ctx: Contexto) -> Pecas:
    realizada = ajuste.ultimo_de_cada_ano(ctx.sgs("DBGG", 30))
    safras = _safras(INDICADOR_DIVIDA, ctx.hoje.year - 1)
    agora = bcb_focus.mediana_anual_hoje(INDICADOR_DIVIDA)
    if not safras or not agora:
        raise ValueError("Focus sem a dívida bruta esperada")
    ultimo = max(realizada)
    primeira = min(safras)
    escolhidas = sorted(safras)[::-1][::2][:SAFRAS_NO_GRAFICO][::-1]
    series = [
        serie(
            "realizada",
            "Dívida bruta (o que aconteceu)",
            [(date(a, 1, 1), v) for a, v in sorted(realizada.items()) if a >= primeira],
        )
    ]
    for feita in escolhidas:
        series.append(
            serie(
                f"safra-{feita}",
                f"O que o Focus esperava em dez/{feita}",
                [
                    (date(a, 1, 1), v)
                    for a, v in sorted(safras[feita].items())
                    if feita <= a <= feita + 5
                ],
            )
        )
    futuros = {a: v for a, v in agora.items() if ultimo < a <= ultimo + 6}
    series.append(
        serie(
            "focus-hoje",
            "O que o Focus espera hoje",
            [(date(a, 1, 1), v) for a, v in sorted(futuros.items())],
            papel="previsao",
        )
    )
    alvo = max(futuros)
    antes = safras[max(safras)].get(alvo)
    fonte = (
        f"Banco Central (Focus, mediana de dezembro de cada ano e a de hoje; "
        f"{ctx.fonte_sgs('DBGG')}); {CONTA}"
    )
    erros = {h: ajuste.erro_por_horizonte(safras, realizada, h) for h in HORIZONTES}
    feitos = [
        f"{h} ano{'s' if h > 1 else ''} antes, {_sinal(e.media)} pp" for h, e in erros.items() if e
    ]
    cartoes = [
        Cartao(
            id="divida-esperada",
            rotulo=f"Dívida bruta que o Focus espera para {alvo}",
            valor=round(futuros[alvo], 2),
            unidade="% do PIB",
            casas=1,
            referencia=ctx.hoje,
            periodicidade="D",
            detalhe=(
                f"em dez/{max(safras)}, esperava {br(antes)} % para o mesmo ano"
                if antes is not None
                else f"em {ultimo} ela era de {br(realizada[ultimo])} %"
            ),
            fonte=fonte,
            procedencia="calculado",
            secao="laboratorio",
        )
    ]
    graficos = [
        grafico(
            "divida-esperada",
            "A dívida bruta que o mercado esperava, safra a safra",
            series,
            unidade="% do PIB",
            casas=1,
            periodicidade="A",
            fonte=fonte,
            manchete=(
                f"O Focus espera dívida bruta de {br(futuros[alvo])} % do PIB em {alvo}; em "
                f"{ultimo} ela foi de {br(realizada[ultimo])} %"
            ),
            nota=(
                "Cada linha de expectativa é uma safra: a mediana que os analistas do Focus "
                "davam, em dezembro daquele ano, para a dívida bruta do governo geral nos "
                "cinco anos seguintes. Linha que sobe sem parar: o mercado não via a dívida "
                "estabilizar naquele horizonte. O Focus coleta esta expectativa desde "
                f"{primeira}; são poucas safras, e o PIB revisado muda o nível da dívida em % "
                "do PIB depois do fato (a queda de 2021 e 2022 veio em boa parte da inflação e "
                "da revisão do PIB)."
                + (
                    f" Erro médio da expectativa (esperado menos realizado): {'; '.join(feitos)}."
                    if feitos
                    else ""
                )
            ),
        )
    ]
    return cartoes, graficos, []


# ------------------------------------------------------------------ o custo de esperar

ESPERAS = (0, 2, 4)
"""Começar a estabilizar no fim deste ano, ou dois e quatro anos depois."""


def esperar(ctx: Contexto) -> Pecas:
    from sacibras.modelos import risco

    neutro = ctx.memo.get("laboratorio_neutro")
    if neutro is None:
        raise ValueError("sem o juro neutro desta rodada")
    divida = bcb_focus.mediana_anual_hoje(INDICADOR_DIVIDA)
    pib = bcb_focus.mediana_anual_hoje("PIB Total")
    if not divida or not pib:
        raise ValueError("Focus sem a dívida ou o PIB esperados")
    crescimento = pib[max(pib)]
    partida = ctx.hoje.year
    linhas = []
    for espera in ESPERAS:
        ano = partida + espera
        if ano not in divida:
            continue
        linhas.append(
            LinhaTabela(
                rotulo=f"A partir do fim de {ano}",
                valores=[
                    round(divida[ano], 1),
                    *(
                        round(risco.primario_que_estabiliza(divida[ano], r, crescimento), 2)
                        for r in neutro
                    ),
                ],
                unidade="",
                casas=1,
            )
        )
    if len(linhas) < 2:
        raise ValueError("Focus sem a dívida dos próximos anos")
    tabela = Tabela(
        id="custo-de-esperar",
        titulo="O primário que estabiliza a dívida, conforme o ano em que ela para de subir",
        subtitulo=(
            "% do PIB; a dívida de partida é a que o Focus espera para o fim de cada ano, e o "
            "juro, cada ponta e a mediana do juro neutro estimado aqui"
        ),
        colunas=[
            "Dívida de partida (Focus)",
            f"Com juro real de {br(neutro[0])} %",
            f"Com juro real de {br(neutro[1])} %",
            f"Com juro real de {br(neutro[2])} %",
        ],
        linhas=linhas,
        fonte=(
            f"Banco Central (Focus de {bcb_focus.data_da_ultima_edicao():%d/%m/%Y}: dívida bruta "
            f"e PIB); juro neutro: estimativa do Laboratório; {CONTA}"
        ),
        nota=(
            "A conta de sempre, dívida × (juro − crescimento) ÷ (1 + crescimento), em termos "
            f"reais, com o crescimento do PIB que o Focus espera para {max(pib)} "
            f"({br(crescimento)} % ao ano) e três juros reais: a menor, a mediana e a maior "
            "estimativa do juro neutro. Não é previsão: é um cenário de longo prazo em que a "
            "dívida custa o juro neutro (hoje ela custa mais). Esperar muda pouco o primário "
            "necessário, porque ele cresce na proporção da dívida; o que muda é o nível em que "
            "a dívida para, e quanto juro se paga sobre ela daí em diante. A conta não mede se "
            "o juro sobe com a dívida mais alta, que é o risco de esperar."
        ),
    )
    return [], [], [tabela]


# ------------------------------------------------------------------ os anúncios fiscais

# Fora da tela (Caio, 19/11/2026: resultado fraco não precisa entrar): a conta fica aqui,
# sem ser chamada, com a lista em `relatorios.ANUNCIOS_FISCAIS`.

PRAZO_DO_JURO = 5
PASSO_DOS_DIAS_COMUNS = 10
"""A régua de um par de dias qualquer: uma janela a cada dez dias úteis."""
SENTIDOS = {"mais": "mais aperto", "menos": "menos aperto", "ambiguo": "ambíguo"}


def _util(d: date, passo: int) -> date:
    d += timedelta(days=passo)
    while not dia_util(d):
        d += timedelta(days=passo)
    return d


def _juro_longo(td: tesouro_direto.Curvas, dia: date) -> float | None:
    from sacibras.secoes.juros import _anos_depois, _curvas_no_dia

    try:
        achado, nominal, _ = _curvas_no_dia(td, dia)
    except (KeyError, ValueError, StopIteration):
        return None
    if achado != dia:
        return None
    du = nominal.du_de(_anos_depois(dia, PRAZO_DO_JURO))
    return nominal.taxa(du) * 100 if du <= nominal.fim else None


def janela_do_anuncio(dia: date, depois_do_fechamento: bool) -> tuple[date, date]:
    """(véspera, dia útil seguinte ao primeiro pregão que viu o anúncio): dois pregões, para
    pegar tanto o anúncio de manhã quanto o do meio do dia (as taxas do Tesouro Direto são
    as da manhã)."""
    visto = _util(dia, 1) if depois_do_fechamento or not dia_util(dia) else dia
    return _util(visto, -1), _util(visto, 1)


def anuncios(ctx: Contexto) -> Pecas:
    eventos = [e for e in relatorios.ANUNCIOS_FISCAIS if e.dia <= ctx.hoje]
    inicio = min(e.dia for e in eventos) - timedelta(days=30)
    td = ctx.memo.get("laboratorio_td") or tesouro_direto.curvas(date(inicio.year, 1, 1))
    do_brasil: dict[date, float] = ctx.memo.get("laboratorio_dolar_diario", {})

    def movimento(de: date, ate: date) -> tuple[float, float | None] | None:
        a, b = _juro_longo(td, de), _juro_longo(td, ate)
        if a is None or b is None:
            return None
        dias_dolar = [d for d in do_brasil if de < d <= ate]
        dolar = ajuste.composta(sum(do_brasil[d] for d in dias_dolar)) if dias_dolar else None
        return (b - a) * 100, dolar

    medidos = []
    for e in eventos:
        m = movimento(*janela_do_anuncio(e.dia, e.depois_do_fechamento))
        if m is not None:
            medidos.append((e, *m))
    if len(medidos) < 5:
        raise ValueError("poucos anúncios fiscais com taxa nos dois dias")
    comuns: list[float] = []
    dia = _util(medidos[0][0].dia, -1)
    while dia < ctx.hoje - timedelta(days=5):
        m = movimento(_util(dia, -1), _util(dia, 1))
        if m is not None:
            comuns.append(abs(m[0]))
        for _ in range(PASSO_DOS_DIAS_COMUNS):
            dia = _util(dia, 1)
    comum = sum(comuns) / len(comuns)
    media = sum(abs(j) for _, j, _ in medidos) / len(medidos)
    maiores = sum(abs(j) > comum for _, j, _ in medidos)
    menos = [j for e, j, _ in medidos if e.sentido == "menos"]
    mais = [j for e, j, _ in medidos if e.sentido == "mais"]
    fonte = (
        "Datas: anúncios oficiais do governo federal (lista lida à mão, cada uma com a "
        "fonte); Tesouro Direto (títulos prefixados, curva zero); "
        f"{fred.FONTE_CAMBIO}; {CONTA}"
    )
    cartoes = [
        Cartao(
            id="anuncio-fiscal",
            rotulo=f"Juro de {PRAZO_DO_JURO} anos em dois dias de anúncio fiscal: quanto mexe",
            valor=round(media, 2),
            unidade="pb",
            casas=0,
            referencia=medidos[-1][0].dia,
            periodicidade="D",
            detalhe=f"em dois dias comuns: {br(comum, 0)} pb; {len(medidos)} anúncios, sem sinal",
            fonte=fonte,
            procedencia="calculado",
            secao="laboratorio",
        )
    ]

    def sobe(valores: list[float]) -> str:
        return f"subiu em {sum(v > 0 for v in valores)} de {len(valores)}"

    tabela = Tabela(
        id="anuncios-fiscais",
        titulo="O juro longo e o dólar nos anúncios fiscais",
        subtitulo=(
            f"{len(medidos)} anúncios desde {medidos[0][0].dia.year}; da véspera ao dia "
            "seguinte ao anúncio"
        ),
        colunas=[
            "O que foi anunciado",
            "Sentido",
            f"Juro de {PRAZO_DO_JURO} anos (pb)",
            "Dólar, só do Brasil (%)",
        ],
        linhas=[
            LinhaTabela(
                rotulo=e.dia.strftime("%d/%m/%Y"),
                valores=[],
                textos=[
                    e.o_que,
                    SENTIDOS[e.sentido],
                    _sinal(j, 0),
                    "s/d" if d is None else _sinal(d),
                ],
                unidade="",
                fonte=e.fonte,
            )
            for e, j, d in reversed(medidos)
        ],
        fonte=fonte,
        nota=(
            "Estudo de evento: o movimento do juro prefixado de "
            f"{PRAZO_DO_JURO} anos (curva zero do Tesouro Direto) e da parte do dólar que é só "
            "do Brasil entre a véspera do anúncio e o dia seguinte a ele. Entram os dias em "
            "que o governo federal anunciou regra fiscal nova, mudança de meta de primário ou "
            "pacote de ajuste; o sentido (mais ou menos aperto que o que valia) é leitura "
            f"nossa do anúncio. Em {maiores} dos {len(medidos)} o juro mexeu mais que num par "
            f"de dias comum ({br(comum, 0)} pb, média sem sinal). Nos anúncios de menos "
            f"aperto, o juro {sobe(menos) if menos else 'não tem caso'}; nos de mais aperto, "
            f"{sobe(mais) if mais else 'não tem caso'}. São poucos casos, o mercado costuma "
            "saber antes (o vazamento fica fora da janela) e outras notícias caem nos mesmos "
            "dias: a tabela mostra o que aconteceu, não o que o anúncio causou."
        ),
    )
    return cartoes, [], [tabela]


# ------------------------------------------------------------------ a meta da LDO e o que veio


def meta_em_pct(meta: leis.MetaDaLDO, pib_bi: float | None) -> float | None:
    """A meta em % do PIB: a que a lei escreveu assim, ou a em reais sobre o PIB do ano."""
    if meta.pct_do_pib is not None:
        return meta.pct_do_pib
    if meta.reais_bi is None or not pib_bi:
        return None
    return meta.reais_bi / pib_bi * 100


def _media_com_intervalo(erros: list[float]) -> tuple[float, float, float]:
    r = estatistica.mqo(erros, [[] for _ in erros])
    lo, hi = r.intervalo(0)
    return r.coef[0], lo, hi


def meta_da_ldo(ctx: Contexto) -> Pecas:
    realizado = ajuste.ultimo_de_cada_ano(contas.escalar(ctx.sgs("NFSP_PRIMARIO_GC_12M", 30), -1))
    pib = {a: v / 1000 for a, v in ajuste.ultimo_de_cada_ano(ctx.sgs("PIB_12M", 30)).items()}
    metas = {
        a: m
        for a, x in sorted(leis.METAS_DAS_LDOS.items())
        if a in realizado and (m := meta_em_pct(x, pib.get(a))) is not None
    }
    if len(metas) < 10:
        raise ValueError("poucos anos com meta e realizado")
    anos = sorted(metas)
    erros = [metas[a] - realizado[a] for a in anos]
    media, lo, hi = _media_com_intervalo(erros)
    sem = [e for a, e in zip(anos, erros, strict=True) if a != EXCECAO]
    media_sem, lo_sem, hi_sem = _media_com_intervalo(sem)
    abaixo = sum(e > 0 for e in erros)
    fonte = (
        "Meta: texto original da LDO de cada ano (Senado), para os orçamentos fiscal e da "
        f"seguridade social; realizado e PIB: {ctx.fonte_sgs('NFSP_PRIMARIO_GC_12M', 'PIB_12M')}; "
        f"{CONTA}"
    )
    cartoes = [
        Cartao(
            id="meta-ldo",
            rotulo="Primário do Governo Central: a meta da LDO menos o que veio",
            valor=round(media, 2),
            unidade="pp do PIB",
            casas=1,
            referencia=date(anos[-1], 12, 1),
            periodicidade="A",
            detalhe=(
                f"90 %: de {_sinal(lo)} a {_sinal(hi)} pp; abaixo da meta em {abaixo} de "
                f"{len(anos)} anos"
            ),
            fonte=fonte,
            procedencia="calculado",
            secao="laboratorio",
        )
    ]
    graficos = [
        grafico(
            "meta-ldo",
            "A meta de primário de cada LDO e o que veio",
            [
                serie(
                    "realizado",
                    "Primário do Governo Central",
                    [(date(a, 1, 1), realizado[a]) for a in anos],
                ),
                serie(
                    "meta",
                    "Meta no texto original da LDO",
                    [(date(a, 1, 1), metas[a]) for a in anos],
                ),
            ],
            unidade="% do PIB",
            casas=1,
            periodicidade="A",
            fonte=fonte,
            manchete=(
                f"De {anos[0]} a {anos[-1]}, o primário do Governo Central ficou abaixo da meta "
                f"original da LDO em {abaixo} de {len(anos)} anos"
            ),
            nota=(
                "A meta é a que a LDO fixou quando foi sancionada, para os orçamentos fiscal e "
                "da seguridade social, sem as mudanças feitas depois, durante o ano. Até 2010 a "
                "lei a escrevia em % do PIB; de 2011 em diante, em reais, aqui divididos pelo "
                "PIB do ano. O realizado é o do Banco Central, que apura a meta. Duas ressalvas: "
                "de 2007 a 2014 a própria lei deixava descontar investimentos (PPI, PAC) e a "
                "comparação aqui é com a meta cheia; e ficar abaixo junta choque que ninguém "
                f"previa ({EXCECAO}) com meta que foi trocada no caminho. Sem {EXCECAO}, a "
                f"diferença média é de {_sinal(media_sem)} pp (90 %: de {_sinal(lo_sem)} a "
                f"{_sinal(hi_sem)})."
            ),
        )
    ]
    tabela = Tabela(
        id="meta-ldo",
        titulo="A meta de primário de cada LDO e o que veio, ano a ano",
        subtitulo="Governo Central, % do PIB; a meta é a do texto original da lei",
        colunas=["Meta", "Realizado", "Realizado menos meta (pp)"],
        linhas=[
            LinhaTabela(
                rotulo=str(a),
                valores=[
                    round(metas[a], 2),
                    round(realizado[a], 2),
                    round(realizado[a] - metas[a], 2),
                ],
                unidade="",
                casas=2,
                fonte=leis.METAS_DAS_LDOS[a].lei,
            )
            for a in reversed(anos)
        ],
        fonte=fonte,
        nota=(
            "Meta em reais dividida pelo PIB do ano como o Banco Central o publica hoje. A "
            "meta é a cheia; o que o texto original já deixava descontar ou tolerar: "
            + "; ".join(
                f"{a}, {leis.METAS_DAS_LDOS[a].abatimento}"
                for a in anos
                if leis.METAS_DAS_LDOS[a].abatimento
            )
            + "."
        ),
    )
    return cartoes, graficos, [tabela]
