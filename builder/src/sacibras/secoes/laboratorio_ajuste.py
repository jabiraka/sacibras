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

from datetime import date

from sacibras import contas
from sacibras.fontes import bcb_fiscal, bcb_focus, fred, tesouro_rtn
from sacibras.modelos import ajuste
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
                    rotulo=f"{h} ano{'s' if h > 1 else ''} antes",
                    valores=[
                        round(e.media, 2),
                        round(e.de, 2),
                        round(e.ate, 2),
                        float(e.otimistas),
                        float(len(e.anos)),
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
        colunas=["Média", "90 %: de", "até", "Anos com o esperado acima", "Anos na conta"],
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
