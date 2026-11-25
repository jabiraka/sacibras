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
from sacibras.schema import (
    Cartao,
    CenarioDaLDO,
    Grafico,
    Intervalo,
    LinhaTabela,
    SimuladorLDO,
    Tabela,
)
from sacibras.secoes import estabiliza
from sacibras.secoes.base import MESES, Contexto, br, grafico, serie
from sacibras.tipos import Ponto

CONTA = "cálculo próprio"
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
            "Dólar em 12 meses: de fora e do Brasil",
            [
                serie(
                    "brasil",
                    "Só do Brasil",
                    [(p.dia, ajuste.composta(p.do_brasil)) for p in semanais],
                ),
                serie(
                    "fora",
                    "De fora",
                    [(p.dia, ajuste.composta(p.de_fora)) for p in semanais],
                ),
                serie(
                    "total",
                    "Dólar no Brasil",
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
                f"{br(abs(total))} %: {_sinal(de_fora)} % de fora e "
                f"{_sinal(do_brasil)} % do Brasil"
            ),
            # De fora: a variação do dólar contra a cesta de emergentes (índice do Federal
            # Reserve) vezes o quanto o real a acompanha, reta por mínimos quadrados sobre as
            # variações diárias dos cinco anos anteriores. As duas partes se multiplicam no
            # total. A faixa do cartão vai do menor ao maior resultado com o real medido em 2, 5
            # e 10 anos, estreita quando o dólar lá fora quase não se mexeu. O real está na
            # cesta com peso pequeno, o que puxa um pouco para "de fora".
            nota=(
                "Cálculo próprio: de fora é o dólar contra os emergentes vezes o quanto o real o "
                "acompanhou em cinco anos; o resto é do Brasil. A parte do Brasil junta contas "
                "públicas, política, juro e exportações, sem separar uma da outra."
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
        titulo="As maiores altas do dólar em 12 meses",
        subtitulo=(
            f"as cinco maiores desde {partes[0].dia.year}, uma por episódio, e os 12 meses até hoje"
        ),
        colunas=["Dólar no Brasil (%)", "De fora (%)", "Só do Brasil (%)"],
        linhas=linhas,
        fonte=fonte,
        nota=(
            "Os 12 meses até cada data, com a conta do gráfico. Parte do Brasil grande: alta "
            "que as outras moedas não explicam."
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
            "Sem déficit primário",
            {a: max(primario[a], 0.0) for a in anos if a in primario and a not in POUPADO},
        ),
        "um": (
            f"Primário de pelo menos {br(PISO, 0)} % do PIB",
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
            f"A dívida bruta com outro primário desde {DESDE}",
            [
                serie("realizada", "Realizada", pontos(dbgg)),
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
                f"Sem os déficits desde {DESDE}, a dívida bruta de {ultimo} seria "
                f"{br(sem)} % do PIB, e não {br(dbgg[ultimo])} %"
            ),
            # Cada real de déficit que não houve deixa de virar dívida e de render a taxa
            # implícita do ano (Banco Central). Dois erros de sinais opostos que os dados não
            # medem: juro menor com dívida menor (abaixo da linha) e PIB menor por um tempo com
            # o ajuste (acima). Vale para o setor público inteiro; não diz como se chegaria lá.
            nota=(
                "Cálculo próprio, não previsão: a dívida refeita trocando só o primário, com "
                f"juro e PIB como foram ({POUPADO[0]} fica como foi). Fica de fora o efeito do "
                "ajuste no juro e no PIB, que os dados daqui não medem."
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
            "Diferença (pp)",
            "Primário médio no período",
        ],
        linhas=linhas,
        fonte=fonte,
        nota=(
            "Diferença: os déficits que não teriam havido, mais o juro sobre eles. O efeito de "
            "um primário maior no juro e no PIB não entra."
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
        f"{ctx.fonte_sgs('NFSP_PRIMARIO_12M')}); erro médio: {CONTA}"
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
            "Realizado",
            [(date(a, 1, 1), v) for a, v in sorted(realizado.items()) if a > PRIMEIRA_SAFRA],
        )
    ]
    for h, nome in ((1, "um ano antes"), (2, "dois anos antes"), (4, "quatro anos antes")):
        previsto = ajuste.previsto_antes(safras, h)
        series.append(
            serie(
                f"antes-{h}",
                f"Focus, {nome}",
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
        series.append(serie("focus-hoje", "Focus hoje", futuros, papel="previsao"))
    lado = "acima" if dois.media > 0 else "abaixo"
    graficos = [
        grafico(
            "primario-prometido",
            "O primário que o Focus esperava e o que veio",
            series,
            unidade="% do PIB",
            casas=1,
            periodicidade="A",
            fonte=fonte,
            manchete=(
                f"Dois anos antes, o Focus esperava em média {br(abs(dois.media))} pp do PIB "
                f"{lado} do que veio ({dois.anos[0]} a {dois.anos[-1]})"
            ),
            # Mediana do Focus para o primário do setor público em dezembro de um, dois ou
            # quatro anos antes. É a expectativa do mercado, que lê o que o governo anuncia.
            nota=(
                "Mediana do Focus em dezembro de um, dois ou quatro anos antes; acima do "
                f"realizado, esperava-se mais. O erro junta choques ({EXCECAO}) e ajuste "
                "esperado que não veio."
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
        titulo="O erro do primário esperado, por antecedência",
        subtitulo=(
            f"Focus menos realizado, pp do PIB, {dois.anos[0]} a {dois.anos[-1]}; "
            "positivo: esperava-se mais"
        ),
        colunas=["Média", "90 %: de", "até", "Anos com o esperado acima (%)"],
        linhas=linhas,
        fonte=fonte,
        # Erro de Newey-West porque os erros de anos vizinhos andam juntos. Realizado: o
        # primário do setor público consolidado em dezembro, como o BC publica hoje.
        nota=(
            "Média com intervalo de 90 %. Poucos anos, e 2015 e 2016 pesam muito: intervalo "
            "que encosta no zero é viés que não se distingue do acaso."
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
            f"Governo Central, % do PIB, {min(primario)} a {max(primario)}; anos seguidos com o "
            f"primário andando {br(MINIMO_DO_EPISODIO, 0)} pp ou mais"
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
        # Receita sobe com imposto novo, mas também com inflação, commodities e receita de
        # uma vez só; despesa em % do PIB cai quando o PIB cresce mais que ela. 2020 e a volta
        # de 2021 são a pandemia.
        nota=(
            "Receita líquida menos despesa total, em % do PIB; as duas últimas colunas somam a "
            "mudança (despesa negativa: subiu). Mostra por onde mudou, não por quê."
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
            "Realizada",
            [(date(a, 1, 1), v) for a, v in sorted(realizada.items()) if a >= primeira],
        )
    ]
    for feita in escolhidas:
        series.append(
            serie(
                f"safra-{feita}",
                f"Focus, dez/{feita}",
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
            "Focus hoje",
            [(date(a, 1, 1), v) for a, v in sorted(futuros.items())],
            papel="previsao",
        )
    )
    alvo = max(futuros)
    antes = safras[max(safras)].get(alvo)
    fonte = (
        f"Banco Central (Focus, mediana de dezembro de cada ano e a de hoje; "
        f"{ctx.fonte_sgs('DBGG')}); erro médio: {CONTA}"
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
            procedencia="mercado",
            secao="laboratorio",
        )
    ]
    graficos = [
        grafico(
            "divida-esperada",
            "A dívida bruta que o Focus esperava, safra a safra",
            series,
            unidade="% do PIB",
            casas=1,
            periodicidade="A",
            fonte=fonte,
            manchete=(
                f"O Focus espera dívida bruta de {br(futuros[alvo])} % do PIB em {alvo}; em "
                f"{ultimo} ela foi de {br(realizada[ultimo])} %"
            ),
            # Linha que sobe sem parar: o mercado não via a dívida estabilizar. A queda de 2021
            # e 2022 veio em boa parte da inflação e da revisão do PIB.
            nota=(
                "Cada linha: a mediana do Focus em dezembro para os cinco anos seguintes. "
                f"Safras só desde {primeira}, e a revisão do PIB muda a dívida depois do fato"
                + (f"; erro médio (esperado − realizado): {'; '.join(feitos)}." if feitos else ".")
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
        titulo="O primário que estabiliza a dívida, por ano de partida",
        subtitulo=(
            "% do PIB; dívida de partida do Focus; juro: as pontas e a mediana do juro neutro"
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
        # Cenário de longo prazo em que a dívida custa o juro neutro (hoje custa mais). Esperar
        # muda pouco o primário necessário, que cresce na proporção da dívida; muda o nível
        # em que ela para e o juro pago daí em diante.
        nota=(
            "Cálculo próprio, não previsão: dívida × (juro − crescimento) ÷ (1 + crescimento), "
            f"real, com o PIB do Focus para {max(pib)} ({br(crescimento)} % ao ano). Não mede "
            "se o juro sobe com a dívida mais alta, o risco de esperar."
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
    ctx.memo["laboratorio_erro_ldo"] = (lo, media, hi, anos[0], anos[-1])
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
                    "Realizado",
                    [(date(a, 1, 1), realizado[a]) for a in anos],
                ),
                serie(
                    "meta",
                    "Meta original da LDO",
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
            # A meta é a da LDO sancionada (orçamentos fiscal e da seguridade), sem as mudanças
            # do ano; até 2010 em % do PIB, depois em reais divididos pelo PIB. O realizado é o
            # do BC, que apura a meta. De 2007 a 2014 a lei deixava descontar PPI e PAC; ficar
            # abaixo junta choque (2020) com meta trocada no caminho.
            nota=(
                "Meta cheia do texto sancionado contra o apurado pelo Banco Central; de 2007 a "
                f"2014 a lei deixava descontar investimentos. Sem {EXCECAO}, a diferença média "
                f"é de {_sinal(media_sem)} pp (90 %: de {_sinal(lo_sem)} a {_sinal(hi_sem)})."
            ),
        )
    ]
    tabela = Tabela(
        id="meta-ldo",
        titulo="A meta de cada LDO e o que veio, ano a ano",
        subtitulo="Governo Central, % do PIB; meta do texto original",
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
            "Meta cheia, em reais sobre o PIB publicado hoje. O que a lei já deixava descontar: "
            + "; ".join(
                f"{a}, {leis.METAS_DAS_LDOS[a].abatimento}"
                for a in anos
                if leis.METAS_DAS_LDOS[a].abatimento
            )
            + "."
        ),
    )
    return cartoes, graficos, [tabela]


# ------------------------------------------------------------------ o projeto da LDO 2027

# Caio, 25/11/2026: *"tem como ver se isso vai estabilizar a dívida"* e *"Pode já colocar,
# dizendo que ainda não virou lei"*. É o que o governo projeta, não cálculo próprio: a peça põe a
# meta e a dívida do projeto ao lado do Focus e do primário que estabilizaria a dívida, e
# diz em que o governo supõe diferente do mercado. Sancionada a lei, a meta de 2027 vai para
# `leis.METAS_DAS_LDOS` e o "ainda não é lei" sai daqui.


ATE_O_FOCUS = 2030
"""O Focus colhe o PIB até este ano; daí em diante vale a última mediana."""


def _cenarios_da_ldo(
    pib_focus: dict[int, float],
    primario_focus: dict[int, float],
    divida_focus: dict[int, float],
) -> tuple[float, dict[int, ajuste.AnoDaDivida], dict[int, ajuste.AnoDaDivida], dict[int, float]]:
    """(dívida de partida, as entradas do governo, as do mercado, a sobra da conta).

    As do mercado: crescimento e primário do Focus, e o juro que faz a conta chegar à dívida
    que o próprio Focus espera, ano a ano."""
    proj = relatorios.PLDO_2027
    inicio = min(proj)
    partida = proj[inicio].divida
    governo = {
        a: ajuste.AnoDaDivida(
            x.implicita, ajuste.nominal(x.pib, x.deflator), x.primario + x.regionais
        )
        for a, x in proj.items()
        if a > inicio
    }
    sobra = ajuste.sobras(partida, governo, {a: proj[a].divida for a in governo})
    mercado: dict[int, ajuste.AnoDaDivida] = {}
    anterior = partida
    ultimo_pib = pib_focus[max(a for a in pib_focus if a <= ATE_O_FOCUS)]
    for a in sorted(governo):
        if a not in primario_focus or a not in divida_focus:
            break
        cresce = ajuste.nominal(pib_focus.get(a, ultimo_pib), proj[a].deflator)
        juro = ajuste.juro_que_fecha(anterior, divida_focus[a], cresce, primario_focus[a], sobra[a])
        mercado[a] = ajuste.AnoDaDivida(juro, cresce, primario_focus[a])
        anterior = divida_focus[a]
    return partida, governo, mercado, sobra


def _conferencia_com_o_tesouro(
    partida: float, governo: dict[int, ajuste.AnoDaDivida], sobra: dict[int, float]
) -> float:
    """A maior distância, em pp do PIB, entre a nossa conta e a tabela de sensibilidade do
    Tesouro (1 pp a menos de PIB ou de primário, todo ano), de 2027 a 2030. O choque do
    Tesouro começa em maio de 2026: compara-se o que cada um soma depois de 2026."""
    proj = relatorios.PLDO_2027
    base = ajuste.caminho(partida, governo, sobra)
    choques = {
        "pib": {
            a: ajuste.AnoDaDivida(
                x.juro, ajuste.nominal(proj[a].pib - 1, proj[a].deflator), x.primario
            )
            for a, x in governo.items()
        },
        "primario": {
            a: ajuste.AnoDaDivida(x.juro, x.nominal, x.primario - 1) for a, x in governo.items()
        },
    }
    pior = 0.0
    for nome, cenario in choques.items():
        nosso = ajuste.caminho(partida, cenario, sobra)
        deles = relatorios.PLDO_2027_SENSIBILIDADE[nome]
        zero = deles[min(deles)]
        for a, v in deles.items():
            if a in nosso:
                pior = max(pior, abs((nosso[a] - base[a]) - (v - zero)))
    return pior


def _simulador_da_ldo(
    partida: float,
    governo: dict[int, ajuste.AnoDaDivida],
    mercado: dict[int, ajuste.AnoDaDivida],
    sobra: dict[int, float],
    focus: dict[int, float],
    realizada: dict[int, float],
    erro: tuple[float, float, float],
    fonte: str,
) -> SimuladorLDO:
    """A linha de base (o projeto, até o último ano dele) e os botões. Os controles somam o
    mesmo tanto em todos os anos: o botão do Focus leva cada um à diferença média entre o
    Focus e o projeto. A tela deixa escolher até que ano simular (Caio, 25/11/2026: *"deixe
    a pessoa escolher até quando quer ir"*); depois do último ano do projeto, ela repete as
    hipóteses dele."""
    proj = relatorios.PLDO_2027
    do_focus = sorted(mercado)
    anos = sorted(governo)

    def media(valores: list[float]) -> float:
        return round(sum(valores) / len(valores), 1)

    cresce = media(
        [
            ((1 + mercado[a].nominal / 100) / (1 + proj[a].deflator / 100) - 1) * 100 - proj[a].pib
            for a in do_focus
        ]
    )
    juro = media([mercado[a].juro - governo[a].juro for a in do_focus])
    primario = media([mercado[a].primario - governo[a].primario for a in do_focus])
    menor, medio, maior = erro
    return SimuladorLDO(
        projeto="projeto da LDO 2027, ainda não é lei",
        ano_inicial=min(proj),
        divida_inicial=partida,
        anos=anos,
        juro=[governo[a].juro for a in anos],
        crescimento=[proj[a].pib for a in anos],
        deflator=[proj[a].deflator for a in anos],
        primario=[round(governo[a].primario, 2) for a in anos],
        sobra=[round(sobra[a], 3) for a in anos],
        meta=[proj[a].meta for a in anos],
        governo_divida=[proj[a].divida for a in anos],
        focus_divida=[focus.get(a) for a in anos],
        realizado=[(date(a, 1, 1), v) for a, v in sorted(realizada.items())][-11:],
        erro_da_historia=(round(menor, 1), round(medio, 1), round(maior, 1)),
        cenarios=[
            CenarioDaLDO(rotulo="Como no projeto", crescimento=0, juro=0, primario=0),
            CenarioDaLDO(
                rotulo="Médias do Focus", crescimento=cresce, juro=juro, primario=primario
            ),
            CenarioDaLDO(
                rotulo="Focus com o erro da história",
                crescimento=cresce,
                juro=juro,
                primario=-round(medio, 1),
            ),
        ],
        fonte=f"{fonte}; {CONTA}",
        nota=(
            "Cálculo próprio, não previsão. Cada controle vale para todos os anos e não mexe nos "
            f"outros. Depois de {max(governo)}, repete as hipóteses do último ano do projeto."
        ),
    )


def ldo_proposta(ctx: Contexto) -> Pecas:
    proj = relatorios.PLDO_2027
    realizada = ajuste.ultimo_de_cada_ano(ctx.sgs("DBGG", 30))
    divida_focus = bcb_focus.mediana_anual_hoje(INDICADOR_DIVIDA)
    pib_focus = bcb_focus.mediana_anual_hoje("PIB Total")
    primario_focus = bcb_focus.mediana_anual_hoje("Resultado primário")
    if not realizada:
        raise ValueError("sem a dívida bruta realizada")
    ultimo = max(realizada)
    futuros = {a: x.divida for a, x in sorted(proj.items()) if a > ultimo}
    focus = {a: v for a, v in sorted(divida_focus.items()) if a > ultimo}
    lido = f"lido em {relatorios.PLDO_2027_LIDO_EM:%d/%m/%Y}"
    fonte = (
        f"{relatorios.FONTE_PLDO_2027} ({lido}); Banco Central (Focus de "
        f"{bcb_focus.data_da_ultima_edicao():%d/%m/%Y}; {ctx.fonte_sgs('DBGG')})"
    )
    meta = proj[2027]
    # Os dois números do primário que estabiliza, lado a lado (a ponte entre eles vai na
    # tabela): o do governo para 2027 e o de Riscos, com o juro e o PIB de hoje.
    detalhe = f"projeto; estabilizar: {br(relatorios.PLDO_2027_ESTABILIZA)} % (governo)"
    tabelas: list[Tabela] = []
    try:
        de_hoje = estabiliza.hoje(ctx).primario
        detalhe = (
            f"estabilizar: {br(relatorios.PLDO_2027_ESTABILIZA)} % (governo); "
            f"{br(de_hoje)} % com o juro de hoje"
        )
        tabelas.append(estabiliza.ponte(ctx))
    except Exception as falha:
        print(f"    laboratório: sem a ponte do primário ({str(falha)[:100]})")
    cartoes = [
        Cartao(
            id="ldo-2027",
            rotulo="Meta de primário para 2027 no projeto da LDO",
            valor=meta.meta or 0.0,
            unidade="% do PIB",
            casas=2,
            referencia=date(2027, 12, 1),
            periodicidade="A",
            detalhe=detalhe,
            fonte=f"{relatorios.FONTE_PLDO_2027} ({lido})",
            procedencia="oficial",
            secao="laboratorio",
        )
    ]
    ponte = [(date(ultimo, 1, 1), realizada[ultimo])]
    series = [
        serie(
            "realizada",
            "Realizado",
            [(date(a, 1, 1), v) for a, v in sorted(realizada.items()) if a >= ultimo - 10],
        ),
        serie(
            "pldo-2027",
            "Governo (projeto da LDO 2027)",
            ponte + [(date(a, 1, 1), v) for a, v in futuros.items()],
            papel="previsao",
        ),
    ]
    if focus:
        series.append(
            serie(
                "focus-hoje",
                "Focus",
                ponte + [(date(a, 1, 1), v) for a, v in focus.items()],
                papel="consenso",
            )
        )

    # O cálculo próprio: as metas do projeto com o erro que as LDOs já tiveram, e o crescimento
    # e o juro que o mercado espera. Só sai se a peça da meta de cada LDO saiu antes.
    erro = ctx.memo.get("laboratorio_erro_ldo")
    intervalos: list[Intervalo] = []
    frase_nossa = ""
    nota_nossa: list[str] = []
    fonte_conta = fonte
    if erro and pib_focus and primario_focus and ultimo < min(proj) + 1:
        menor, medio, maior, de, ate = erro
        partida, governo, mercado, sobra = _cenarios_da_ldo(pib_focus, primario_focus, divida_focus)
        fim = max(mercado)
        meio = min(ATE_O_FOCUS, fim)

        def historia(falta: float) -> dict[int, float]:
            return ajuste.caminho(
                partida,
                {
                    a: ajuste.AnoDaDivida(x.juro, x.nominal, governo[a].primario - falta)
                    for a, x in mercado.items()
                },
                sobra,
            )

        central, baixo, alto = historia(medio), historia(menor), historia(maior)
        ctx.memo["laboratorio_simulador_ldo"] = _simulador_da_ldo(
            partida, governo, mercado, sobra, focus, realizada, (menor, medio, maior), fonte
        )
        inicio = (date(min(proj), 1, 1), partida)
        series.append(
            serie(
                "historia",
                "Cálculo próprio (metas com o erro da história)",
                [inicio] + [(date(a, 1, 1), v) for a, v in central.items()],
                papel="previsao",
            )
        )
        intervalos = [
            Intervalo(
                nome="Faixa de 90 % do erro das metas",
                serie="historia",
                pontos=[(date(a, 1, 1), round(baixo[a], 2), round(alto[a], 2)) for a in central],
            )
        ]
        fonte_conta = f"{fonte}; {CONTA}"
        frase_nossa = f", cálculo próprio {br(central[fim])} % ({br(baixo[fim])} a {br(alto[fim])})"
        sobra_media = sum(sobra.values()) / len(sobra)
        nota_nossa = [
            f"Cálculo próprio, não previsão: as metas do projeto menos {br(medio)} pp, o erro",
            f"médio das LDOs de {de} a {ate} (traços: {br(menor)} a {br(maior)}), com",
            "crescimento e juro do Focus.",
        ]

        def divida_com(quais: tuple[str, ...]) -> dict[int, float]:
            return ajuste.caminho(partida, ajuste.trocar(governo, mercado, quais), sobra)

        partes = {
            a: ajuste.repartir_a_diferenca(partida, governo, mercado, sobra, a) for a in (meio, fim)
        }
        do_governo = ajuste.caminho(partida, ajuste.trocar(governo, mercado, ()), sobra)
        do_mercado = divida_com(ajuste.FATORES)

        def linha(rotulo: str, d: dict[int, float], grupo: str) -> LinhaTabela:
            return LinhaTabela(
                rotulo=rotulo,
                valores=[round(d[meio], 1), round(d[fim], 1)],
                unidade="",
                casas=1,
                grupo=grupo,
            )

        um = "Governo, trocando uma hipótese (% do PIB)"
        nosso = "Metas com o erro da história (% do PIB)"
        de_onde = "Focus menos governo: de onde vem (pp do PIB)"
        nomes = {"crescimento": "Crescimento", "juro": "Juro", "primario": "Primário"}
        tabelas.append(
            Tabela(
                id="ldo-2027-cenarios",
                titulo="A dívida bruta, cenário a cenário",
                subtitulo="Projeto da LDO 2027, ainda não é lei",
                colunas=[str(meio), str(fim)],
                linhas=[
                    linha("Como o governo supõe", do_governo, um),
                    linha("Crescimento do Focus", divida_com(("crescimento",)), um),
                    linha("Juro do Focus", divida_com(("juro",)), um),
                    linha("Primário do Focus", divida_com(("primario",)), um),
                    linha("Os três (é o Focus)", do_mercado, um),
                    linha(f"Erro médio ({br(medio)} pp)", central, nosso),
                    linha(f"Erro menor ({br(menor)} pp)", baixo, nosso),
                    linha(f"Erro maior ({br(maior)} pp)", alto, nosso),
                    *(
                        LinhaTabela(
                            rotulo=nomes[f],
                            valores=[round(partes[meio][f], 1), round(partes[fim][f], 1)],
                            unidade="",
                            casas=1,
                            grupo=de_onde,
                        )
                        for f in ajuste.FATORES
                    ),
                    LinhaTabela(
                        rotulo="Total",
                        valores=[
                            round(do_mercado[meio] - do_governo[meio], 1),
                            round(do_mercado[fim] - do_governo[fim], 1),
                        ],
                        unidade="",
                        casas=1,
                        grupo=de_onde,
                    ),
                ],
                fonte=fonte_conta,
                nota=" ".join(
                    [
                        "Cálculo próprio. Com os números do governo, a conta deixa uma sobra de",
                        f"{br(sobra_media)} pp por ano, mantida em todos os cenários.",
                        f"Depois de {ATE_O_FOCUS}: crescimento na última mediana do Focus e o",
                        "juro que fecha com a dívida do Focus.",
                    ]
                ),
            )
        )

    fim_focus = max(focus) if focus else None
    alvo = fim_focus if fim_focus in futuros else max(futuros)
    manchete = (
        f"Em {alvo}: governo {br(futuros[alvo])} % do PIB"
        + (f", Focus {br(focus[alvo])} %" if alvo in focus else "")
        + frase_nossa
    )
    graficos = [
        grafico(
            "ldo-2027-divida",
            "A dívida bruta: governo, Focus e a conta com a história",
            series,
            unidade="% do PIB",
            casas=1,
            periodicidade="A",
            fonte=fonte_conta,
            intervalos=intervalos,
            manchete=manchete,
            nota=" ".join(
                [
                    f"Projeto, ainda não é lei (em {relatorios.PLDO_2027_LIDO_EM:%d/%m/%Y},",
                    f"{relatorios.PLDO_2027_SITUACAO}).",
                    *nota_nossa,
                ]
            ),
        )
    ]
    linhas = [
        LinhaTabela(
            rotulo=str(a) + ("" if a == 2027 else " (indicativa)"),
            valores=[
                x.meta,
                x.primario,
                x.divida,
                divida_focus.get(a),
                relatorios.PLDO_2027_REQUERIDO.get(a),
                estabiliza.do_focus(a),
                x.pib,
                pib_focus.get(a),
            ],
            unidade="",
            casas=2,
        )
        for a, x in proj.items()
        if x.meta is not None
    ]
    tabelas.append(
        Tabela(
            id="ldo-2027",
            titulo="O projeto da LDO 2027 em números",
            subtitulo="% do PIB; PIB em % ao ano; ainda não é lei",
            colunas=[
                "Meta de primário",
                "Primário antes dos descontos",
                "Dívida bruta (governo)",
                "Dívida bruta (Focus)",
                "Primário que estabiliza (governo)",
                "Primário que estabiliza (Focus)",
                "PIB (governo)",
                "PIB (Focus)",
            ],
            linhas=linhas,
            fonte=f"{fonte}; estabiliza (Focus): {CONTA}",
            nota=" ".join(
                [
                    f"Meta de 2027: R$ {br(relatorios.PLDO_2027_META_BI)} bi (tolerância de",
                    f"R$ {br(relatorios.PLDO_2027_FAIXA_BI[0])} bi a",
                    f"R$ {br(relatorios.PLDO_2027_FAIXA_BI[1])} bi); as de 2028 a 2030 são",
                    "indicativas. A meta se apura sem parte dos precatórios, a defesa e o",
                    "Fundo Social.",
                ]
            ),
        )
    )
    return cartoes, graficos, tabelas
