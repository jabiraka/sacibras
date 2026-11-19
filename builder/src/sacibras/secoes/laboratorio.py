"""O Laboratório: estimativas nossas, cada uma com o método em uma frase e a faixa de erro
(Caio, 16/11/2026: *"pode afrouxar minhas regras"*; 17/11/2026: *"Faça 1) laboratório"*).

Quatro peças, da leva 1 do plano (docs/PLANO-FASE-2.md):
- juro neutro por três métodos, o hiato do produto por dois filtros e a regra de Taylor com
  a faixa que sai de combinar os dois;
- estudo de evento do Copom: a surpresa de cada decisão contra o Focus e o que o juro de dois
  anos e o dólar fizeram no dia seguinte;
- a reação fiscal (o teste de Bohn): quando a dívida sobe, o primário responde?
- o PIB por habitante desde 1950: de onde veio o crescimento e a distância para os EUA.

Em 19/11/2026 entraram três peças sobre pressão e ajuste fiscal, que moram em
`secoes/laboratorio_ajuste.py`: o dólar repartido entre o mundo e o Brasil, a dívida com outro
primário desde 2014 e o primário que o Focus esperava contra o que veio.

Nada aqui é número oficial: a fonte de cada peça diz "conta nossa" e o dado de onde ela sai.
Onde a conta não dá resposta firme (pouca observação, medida ruim), a tela diz isso.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from statistics import median

from sacibras import contas, curvas
from sacibras.calendario import dia_util
from sacibras.fontes import bcb_copom, bcb_focus, ibge_sidra, pwt, tesouro_direto
from sacibras.modelos import estatistica
from sacibras.schema import Cartao, Faixa, Grafico, LinhaTabela, Secao, Tabela
from sacibras.secoes import laboratorio_ajuste
from sacibras.secoes.base import Contexto, br, cartao, grafico, periodo, serie
from sacibras.tipos import Ponto

PIB_SAZONAL = (1621, 584, "c11255/90707")
"""SIDRA 1621: PIB a preços de mercado, índice de volume com ajuste sazonal (1995 = 100),
trimestral desde 1996 (conferido em 17/11/2026)."""
INICIO = date(2006, 1, 1)
CONTA = "conta nossa"


def _trimestre(d: date) -> date:
    return date(d.year, 3 * ((d.month - 1) // 3) + 1, 1)


def _por_trimestre(pontos: list[Ponto]) -> dict[date, float]:
    """O último valor de cada trimestre (a série chega mensal, diária ou trimestral)."""
    saida: dict[date, float] = {}
    for d, v in sorted(pontos):
        saida[_trimestre(d)] = v
    return saida


def _real(nominal: float, inflacao: float) -> float:
    return ((1 + nominal / 100) / (1 + inflacao / 100) - 1) * 100


# ------------------------------------------------------------------ hiato do produto


def hiatos(pib: list[Ponto]) -> dict[str, list[Ponto]]:
    """O hiato em % do PIB potencial por dois filtros: HP (λ = 1600) e Hamilton (2018, dois
    anos à frente). Os dois sobre o log do índice com ajuste sazonal."""
    log = [100 * math.log(v) for _, v in pib]
    tendencia = estatistica.hp(log)
    ciclo = estatistica.hamilton(log)
    return {
        "hp": [(d, y - t) for (d, _), y, t in zip(pib, log, tendencia, strict=True)],
        "hamilton": [(d, c) for (d, _), c in zip(pib, ciclo, strict=True) if c is not None],
    }


# ------------------------------------------------------------------ juro neutro


def datas_de_fim_de_trimestre(desde: date, ate: date) -> list[date]:
    """A quinta e a sexta da última semana cheia de cada trimestre (duas, para o feriado)."""
    saida: list[date] = []
    ano, mes = desde.year, 3
    while date(ano, mes, 1) <= ate:
        d = date(ano, mes, 28)
        while d.weekday() != 4:
            d -= timedelta(days=1)
        saida += [d - timedelta(days=1), d]
        ano, mes = (ano, mes + 3) if mes < 12 else (ano + 1, 3)
    return [d for d in saida if d <= ate]


def neutro_do_focus(
    selic: dict[date, dict[int, float]], ipca: dict[date, dict[int, float]], anos: int = 3
) -> list[Ponto]:
    """O juro real que os analistas esperam daqui a `anos` anos: a Selic do fim daquele ano
    descontada do IPCA do mesmo ano. Longe o bastante para não ser o ciclo de agora."""
    por_trimestre: dict[date, float] = {}
    for dia in sorted(set(selic) & set(ipca)):
        alvo = dia.year + anos
        if alvo in selic[dia] and alvo in ipca[dia]:
            por_trimestre[_trimestre(dia)] = _real(selic[dia][alvo], ipca[dia][alvo])
    return sorted(por_trimestre.items())


def neutro_da_media(
    selic: list[Ponto], inflacao_esperada: list[Ponto], anos: int = 10
) -> list[Ponto]:
    """A média dos últimos `anos` anos do juro real esperado (Selic menos o IPCA esperado
    para 12 meses), por trimestre: o nível em volta do qual o juro real oscilou."""
    s, i = _por_trimestre(selic), _por_trimestre(inflacao_esperada)
    reais = [(t, _real(s[t], i[t])) for t in sorted(set(s) & set(i))]
    janela = 4 * anos
    return [
        (reais[k][0], sum(v for _, v in reais[k - janela + 1 : k + 1]) / janela)
        for k in range(janela - 1, len(reais))
    ]


def neutro_da_curva(td: tesouro_direto.Curvas, trimestres: list[date]) -> list[Ponto]:
    """O juro real a termo de 5 a 10 anos nos títulos IPCA+: o que o mercado cobra acima da
    inflação num prazo em que o ciclo de hoje já passou (inclui o prêmio de prazo)."""
    from sacibras.secoes.juros import _anos_depois, _curvas_no_dia

    saida: list[Ponto] = []
    for t in trimestres:
        fim = date(t.year + (t.month + 2) // 12, (t.month + 2) % 12 + 1, 1) - timedelta(days=1)
        try:
            dia, _, real = _curvas_no_dia(td, fim)
        except (KeyError, ValueError, StopIteration):
            continue
        if (fim - dia).days > 20:
            continue
        a, b = real.du_de(_anos_depois(dia, 5)), real.du_de(_anos_depois(dia, 10))
        if curvas.tem_real(real, a) and b <= real.fim:
            saida.append((t, curvas.termo(real, a, b)))
    return saida


METODOS_NEUTRO = {
    "focus": "Focus: juro real esperado para daqui a 3 anos",
    "curva": "Títulos IPCA+: juro real a termo de 5 a 10 anos",
    "media": "Média de 10 anos do juro real esperado",
}


def regra_de_taylor(
    neutros: dict[str, dict[date, float]],
    hiato: dict[str, dict[date, float]],
    inflacao_esperada: dict[date, float],
    meta: dict[int, float],
) -> list[tuple[date, float, float, float]]:
    """[(trimestre, mediana, mínimo, máximo)] da Selic pela regra de Taylor (1993), com a
    inflação esperada: i = r* + πᵉ + 0,5·(πᵉ − meta) + 0,5·hiato, uma conta para cada juro
    neutro e cada hiato. O hiato de um trimestre que o IBGE ainda não publicou é o último."""
    saida: list[tuple[date, float, float, float]] = []
    for t in sorted(inflacao_esperada):
        if t.year not in meta:
            continue
        pi = inflacao_esperada[t]
        rs = [v[t] for v in neutros.values() if t in v]
        hs = []
        for serie_h in hiato.values():
            antes = [d for d in serie_h if d <= t]
            if antes and (t - max(antes)).days <= 200:
                hs.append(serie_h[max(antes)])
        if not rs or not hs:
            continue
        valores = [r + pi + 0.5 * (pi - meta[t.year]) + 0.5 * h for r in rs for h in hs]
        saida.append((t, median(valores), min(valores), max(valores)))
    return saida


def _juro_neutro(ctx: Contexto) -> tuple[list[Cartao], list[Grafico], list[Tabela]]:
    pib = ibge_sidra.series(
        PIB_SAZONAL[0], PIB_SAZONAL[1], classificacao=PIB_SAZONAL[2], por="Setores", trimestral=True
    )
    pib_sa = pib["90707"]
    gaps = hiatos(pib_sa)
    fonte_pib = f"IBGE, SIDRA {PIB_SAZONAL[0]} (PIB com ajuste sazonal); {CONTA}"

    datas = datas_de_fim_de_trimestre(INICIO, ctx.hoje)
    selic_f = bcb_focus.anuais_nas_datas("Selic", datas)
    ipca_f = bcb_focus.anuais_nas_datas("IPCA", datas)
    selic = ctx.sgs("SELIC_META", 25)
    esperada = bcb_focus.inflacao_12_meses(date(1999, 1, 1))
    neutros: dict[str, list[Ponto]] = {
        "focus": neutro_do_focus(selic_f, ipca_f),
        "media": [p for p in neutro_da_media(selic, esperada) if p[0] >= INICIO],
    }
    try:
        td = tesouro_direto.curvas(INICIO)
        trimestres = sorted({_trimestre(d) for d in datas})
        neutros["curva"] = neutro_da_curva(td, trimestres)
    except Exception as erro:
        print(f"    laboratório: sem o juro neutro da curva ({str(erro)[:100]})")
    neutros = {k: v for k, v in neutros.items() if v}
    fonte_neutro = (
        "Banco Central (Focus e SGS 432), Tesouro Direto (taxas dos títulos IPCA+); " + CONTA
    )
    hoje = {k: v[-1] for k, v in neutros.items()}
    faixa_hoje = (min(v for _, v in hoje.values()), max(v for _, v in hoje.values()))
    central = median(v for _, v in hoje.values())
    quando = max(d for d, _ in hoje.values())

    meta = {d.year: v for d, v in ctx.sgs("META_INFLACAO", 30)}
    taylor = regra_de_taylor(
        {k: dict(v) for k, v in neutros.items()},
        {k: dict(v) for k, v in gaps.items()},
        _por_trimestre(esperada),
        meta,
    )
    selic_tri = sorted(_por_trimestre(selic).items())
    t_hoje = taylor[-1]

    cartoes = [
        Cartao(
            id="juro-neutro",
            rotulo="Juro neutro, a mediana de três métodos",
            valor=round(central, 2),
            unidade="% a.a.",
            casas=1,
            referencia=quando,
            periodicidade="T",
            detalhe=f"de {br(faixa_hoje[0])} % a {br(faixa_hoje[1])} %, conforme o método",
            fonte=fonte_neutro,
            procedencia="calculado",
            secao="laboratorio",
        ),
        cartao(
            "hiato",
            "Hiato do produto (filtro HP)",
            gaps["hp"],
            unidade="% do PIB potencial",
            periodicidade="T",
            casas=1,
            detalhe=f"pelo filtro de Hamilton: {br(gaps['hamilton'][-1][1])} %",
            fonte=fonte_pib,
            procedencia="calculado",
            secao="laboratorio",
            mini=40,
        ),
        Cartao(
            id="taylor",
            rotulo="Selic pela regra de Taylor",
            valor=round(t_hoje[1], 2),
            unidade="% a.a.",
            casas=1,
            referencia=t_hoje[0],
            periodicidade="T",
            detalhe=(
                f"faixa de {br(t_hoje[2])} % a {br(t_hoje[3])} %; Selic: {br(selic[-1][1], 2)} %"
            ),
            fonte=f"{fonte_neutro}; IBGE (PIB); Focus (IPCA de 12 meses); SGS 13521 (meta)",
            procedencia="calculado",
            secao="laboratorio",
        ),
    ]
    cartoes[2].mini = [(d, round(m, 2)) for d, m, _, _ in taylor[-40:]]
    graficos = [
        grafico(
            "juro-neutro",
            "Juro neutro: três formas de medir",
            [serie(k, METODOS_NEUTRO[k], v) for k, v in neutros.items()],
            unidade="% a.a., acima da inflação",
            casas=1,
            periodicidade="T",
            fonte=fonte_neutro,
            nota=(
                "Juro neutro é o juro real que nem acelera nem freia a economia; ninguém o "
                "observa, só estima. Focus: a Selic que os analistas esperam para o fim do "
                "ano daqui a três anos, descontado o IPCA do mesmo ano. Títulos: o juro "
                "acima da inflação que o Tesouro paga entre 5 e 10 anos à frente, a termo, "
                "que inclui um prêmio por prazo. Média: o juro real esperado (Selic menos o "
                "IPCA esperado em 12 meses) na média dos dez anos anteriores. O Banco Central "
                "publica a estimativa dele no Relatório de Política Monetária; ainda não "
                "entrou aqui."
            ),
        ),
        grafico(
            "hiato",
            "Hiato do produto: a economia acima ou abaixo do potencial",
            [
                serie("hp", "Filtro HP", gaps["hp"], desde=INICIO),
                serie("hamilton", "Filtro de Hamilton", gaps["hamilton"], desde=INICIO),
            ],
            unidade="% do PIB potencial",
            casas=1,
            periodicidade="T",
            fonte=fonte_pib,
            nota=(
                "Positivo: a economia produz acima do que conseguiria sem pressionar preços. "
                "HP: a distância do PIB para uma tendência suave (λ = 1600). Hamilton: o erro "
                "de prever o PIB de hoje com o de dois anos antes. Os dois erram mais no fim "
                "da série, justamente no trimestre que interessa: o HP muda quando sai o "
                "dado novo, e os dois podem divergir por pontos, como agora."
            ),
        ),
        grafico(
            "regra-de-taylor",
            "A Selic e a regra de Taylor",
            [
                serie("selic", "Selic meta (fim do trimestre)", selic_tri, desde=INICIO),
                serie("taylor", "Regra de Taylor (mediana)", [(d, m) for d, m, _, _ in taylor]),
            ],
            unidade="% a.a.",
            casas=1,
            periodicidade="T",
            fonte=f"{fonte_neutro}; IBGE (PIB); SGS 13521 (meta de inflação)",
            faixa=Faixa(
                nome="faixa entre os métodos",
                pontos=[(d, round(lo, 2), round(hi, 2)) for d, _, lo, hi in taylor],
            ),
            nota=(
                "Regra de Taylor (1993), com a inflação esperada: juro neutro + IPCA esperado "
                "em 12 meses + metade da distância da expectativa para a meta + metade do "
                "hiato. Uma conta para cada juro neutro (três) e cada hiato (dois); a linha é "
                "a mediana das seis e a faixa vai da menor à maior. Não é o que o Banco "
                "Central faz, e sim uma régua: Selic acima da faixa é aperto maior do que a "
                "regra pede."
            ),
        ),
    ]
    linhas = []
    for k, v in neutros.items():
        d = dict(v)
        ult = v[-1]
        ano_antes = d.get(date(ult[0].year - 1, ult[0].month, 1))
        linhas.append(
            LinhaTabela(
                rotulo=METODOS_NEUTRO[k],
                valores=[
                    round(ult[1], 2),
                    None if ano_antes is None else round(ano_antes, 2),
                    round(min(d.values()), 2),
                    round(max(d.values()), 2),
                ],
                unidade="% a.a.",
                casas=1,
            )
        )
    tabela = Tabela(
        id="juro-neutro-metodos",
        titulo="Juro neutro por método",
        subtitulo=f"% a.a., acima da inflação; o mais novo de cada um, até {periodo(quando, 'T')}",
        colunas=[
            "Hoje",
            "Um ano antes",
            f"Menor desde {INICIO.year}",
            f"Maior desde {INICIO.year}",
        ],
        linhas=linhas,
        fonte=fonte_neutro,
        nota=(
            "A distância entre os métodos é a medida honesta da incerteza: ninguém sabe o juro "
            "neutro com precisão de décimos."
        ),
    )
    ctx.memo["laboratorio_hiato_hp"] = gaps["hp"]
    return cartoes, graficos, [tabela]


# ------------------------------------------------------------------ estudo de evento do Copom


def reunioes_rotuladas(todas: list[bcb_copom.Reuniao]) -> list[tuple[str, bcb_copom.Reuniao]]:
    """[("R7/2026", reunião)]: a ordem da reunião ordinária no ano, como o Focus a chama."""
    saida: list[tuple[str, bcb_copom.Reuniao]] = []
    do_ano: dict[int, int] = {}
    for r in todas:
        do_ano[r.data.year] = do_ano.get(r.data.year, 0) + 1
        saida.append((f"R{do_ano[r.data.year]}/{r.data.year}", r))
    return saida


def _dia_seguinte(d: date) -> date:
    d += timedelta(days=1)
    while not dia_util(d):
        d += timedelta(days=1)
    return d


def _juro_de_2_anos(td: tesouro_direto.Curvas, dia: date) -> float | None:
    from sacibras.secoes.juros import _anos_depois, _curvas_no_dia

    try:
        achado, nominal, _ = _curvas_no_dia(td, dia)
    except (KeyError, ValueError, StopIteration):
        return None
    if achado != dia:
        return None
    du = nominal.du_de(_anos_depois(dia, 2))
    return nominal.taxa(du) * 100 if du <= nominal.fim else None


def _copom(ctx: Contexto) -> tuple[list[Cartao], list[Grafico], list[Tabela]]:
    rotuladas = [
        (k, r)
        for k, r in reunioes_rotuladas(bcb_copom.reunioes())
        if r.meta is not None and INICIO <= r.data <= ctx.hoje
    ]
    esperado = bcb_focus.selic_antes_das_reunioes([(k, r.data) for k, r in rotuladas])
    td = tesouro_direto.curvas(INICIO)
    dolar = dict(ctx.sgs("DOLAR", 25))
    eventos: list[tuple[date, float, float, float, float, float | None]] = []
    calmos: list[float] = []
    for rotulo, r in rotuladas:
        if rotulo not in esperado or r.meta is None:
            continue
        seguinte = _dia_seguinte(r.data)
        antes, depois = _juro_de_2_anos(td, r.data), _juro_de_2_anos(td, seguinte)
        if antes is None or depois is None:
            continue
        surpresa = round(r.meta - esperado[rotulo][1], 2)
        mov_dolar = (
            (dolar[seguinte] / dolar[r.data] - 1) * 100
            if r.data in dolar and seguinte in dolar
            else None
        )
        eventos.append(
            (r.data, r.meta, esperado[rotulo][1], surpresa, (depois - antes) * 100, mov_dolar)
        )
        # O mesmo par de dias uma semana antes: a régua de um dia comum.
        a = r.data - timedelta(days=7)
        b = _dia_seguinte(a)
        x, y = _juro_de_2_anos(td, a), _juro_de_2_anos(td, b)
        if x is not None and y is not None:
            calmos.append(abs(y - x) * 100)
    fora_2020 = [e for e in eventos if e[0].year != 2020]
    reg = estatistica.mqo([e[4] for e in fora_2020], [[e[3] * 100] for e in fora_2020])
    reg_todos = estatistica.mqo([e[4] for e in eventos], [[e[3] * 100] for e in eventos])
    efeito = reg.coef[1] * 25
    lo, hi = (v * 25 for v in reg.intervalo(1))
    media_copom = sum(abs(e[4]) for e in eventos) / len(eventos)
    media_calma = sum(calmos) / len(calmos)
    fonte = (
        "Banco Central (decisões do Copom, Focus por reunião e SGS 1, dólar), Tesouro Direto "
        "(taxas dos títulos prefixados, curva zero); " + CONTA
    )
    ultimo = eventos[-1][0]
    cartoes = [
        Cartao(
            id="copom-efeito",
            rotulo="Juro de 2 anos a cada 0,25 pp de surpresa do Copom",
            valor=round(efeito, 2),
            unidade="pb",
            casas=1,
            referencia=ultimo,
            periodicidade="D",
            detalhe=f"90 %: de {br(lo)} a {br(hi)} pb; sem 2020",
            fonte=fonte,
            procedencia="calculado",
            secao="laboratorio",
        ),
        Cartao(
            id="copom-dias",
            rotulo="Quanto o juro de 2 anos mexe no dia seguinte ao Copom",
            valor=round(media_copom, 2),
            unidade="pb",
            casas=1,
            referencia=ultimo,
            periodicidade="D",
            detalhe=f"num dia comum: {br(media_calma)} pb (média, sem sinal)",
            fonte=fonte,
            procedencia="calculado",
            secao="laboratorio",
        ),
    ]
    com_surpresa = [e for e in eventos if abs(e[3]) >= 0.1]
    tabela = Tabela(
        id="copom-surpresas",
        titulo="As decisões do Copom que o Focus não esperava",
        subtitulo=(
            f"{len(com_surpresa)} de {len(eventos)} reuniões desde {INICIO.year}, surpresa de "
            "0,10 pp ou mais"
        ),
        colunas=[
            "Decisão (% a.a.)",
            "Focus (% a.a.)",
            "Surpresa (pp)",
            "Juro de 2 anos (pb)",
            "Dólar (%)",
        ],
        linhas=[
            LinhaTabela(
                rotulo=d.strftime("%d/%m/%Y"),
                valores=[
                    meta,
                    focus,
                    surpresa,
                    round(mov, 1),
                    None if dol is None else round(dol, 2),
                ],
                unidade="",
                casas=2,
            )
            for d, meta, focus, surpresa, mov, dol in reversed(com_surpresa)
        ],
        fonte=fonte,
        nota=(
            "Estudo de evento: a surpresa é a decisão menos a última mediana do Focus nos sete "
            "dias antes da reunião; o movimento vai do dia da reunião ao dia útil seguinte "
            "(o Copom anuncia depois do fechamento). Juro de 2 anos: a curva zero dos títulos "
            "prefixados do Tesouro Direto. Uma reta pelos pontos (mínimos quadrados, erro de "
            f"Newey-West) dá {br(efeito)} pb a cada 0,25 pp de surpresa, de {br(lo)} a {br(hi)} "
            f"com 90 % de confiança, fora 2020; com 2020, {br(reg_todos.coef[1] * 25)} pb, sem "
            "efeito que se distinga de zero (a pandemia mexeu tudo junto). O efeito é pequeno "
            "porque a medida da surpresa é pobre: a mediana do Focus fica até uma semana velha "
            "e o mercado de juros futuros, que mede melhor, é da B3, fora daqui pela licença."
        ),
    )
    return cartoes, [], [tabela]


# ------------------------------------------------------------------ reação fiscal (Bohn)


def anuais_de_dezembro(pontos: list[Ponto]) -> dict[int, float]:
    return {d.year: v for d, v in pontos if d.month == 12}


def reacao_fiscal(
    primario: dict[int, float], divida: dict[int, float], hiato: dict[int, float], anos: list[int]
) -> estatistica.Regressao:
    """primárioₜ = a + b·dívidaₜ₋₁ + c·hiatoₜ (Bohn, 1998): b > 0 é o governo reagindo."""
    usados = [a for a in anos if a in primario and a - 1 in divida and a in hiato]
    return estatistica.mqo(
        [primario[a] for a in usados], [[divida[a - 1], hiato[a]] for a in usados]
    )


def _reacao(ctx: Contexto) -> tuple[list[Cartao], list[Grafico], list[Tabela]]:
    primario = anuais_de_dezembro(contas.escalar(ctx.sgs("NFSP_PRIMARIO_12M", 30), -1))
    divida = anuais_de_dezembro(ctx.sgs("DLSP", 30))
    gaps: list[Ponto] = (
        ctx.memo.get("laboratorio_hiato_hp")
        or hiatos(
            ibge_sidra.series(
                PIB_SAZONAL[0],
                PIB_SAZONAL[1],
                classificacao=PIB_SAZONAL[2],
                por="Setores",
                trimestral=True,
            )["90707"]
        )["hp"]
    )
    por_ano: dict[int, list[float]] = {}
    for d, v in gaps:
        por_ano.setdefault(d.year, []).append(v)
    hiato = {a: sum(v) / len(v) for a, v in por_ano.items() if len(v) == 4}
    ultimo = max(a for a in primario if a in hiato and a - 1 in divida)
    todos = list(range(min(primario), ultimo + 1))
    reg = reacao_fiscal(primario, divida, hiato, todos)
    partes = [
        (f"{todos[0]} a 2013", [a for a in todos if a <= 2013]),
        (f"2014 a {ultimo}", [a for a in todos if a >= 2014]),
    ]
    fonte = f"{ctx.fonte_sgs('NFSP_PRIMARIO_12M', 'DLSP')}; IBGE, SIDRA 1621 (hiato); {CONTA}"
    b, (lo, hi) = reg.coef[1] * 10, (v * 10 for v in reg.intervalo(1))
    usados = [a for a in todos if a - 1 in divida and a in hiato]
    previsto = [
        (date(a, 1, 1), reg.coef[0] + reg.coef[1] * divida[a - 1] + reg.coef[2] * hiato[a])
        for a in usados
    ]
    cartoes = [
        Cartao(
            id="reacao-fiscal",
            rotulo="Primário a mais para cada 10 pp de dívida a mais",
            valor=round(b, 2),
            unidade="pp do PIB",
            casas=2,
            referencia=date(ultimo, 1, 1),
            periodicidade="A",
            detalhe=f"90 %: de {br(lo, 2)} a {br(hi, 2)} pp; {reg.n} anos",
            fonte=fonte,
            procedencia="calculado",
            secao="laboratorio",
        )
    ]
    graficos = [
        grafico(
            "reacao-fiscal",
            "O primário e o que a reação à dívida previa",
            [
                serie(
                    "primario", "Primário realizado", [(date(a, 1, 1), primario[a]) for a in usados]
                ),
                serie("previsto", "Pela reação estimada", previsto, papel="previsao"),
            ],
            unidade="% do PIB",
            casas=1,
            periodicidade="A",
            fonte=fonte,
            nota=(
                "Teste de Bohn (1998): primário do ano contra a dívida líquida do fim do ano "
                "anterior, descontado o ciclo (o hiato do produto, filtro HP). Se o coeficiente "
                "da dívida é positivo, o governo aperta quando a dívida sobe, e isso basta para "
                "ela não explodir. Com um ponto por ano, são poucos pontos: o intervalo é "
                "largo."
            ),
        )
    ]
    linhas = []
    for nome, anos in [(f"{todos[0]} a {ultimo}", todos), *partes]:
        try:
            r = reacao_fiscal(primario, divida, hiato, anos)
        except ValueError:
            continue
        a, z = r.intervalo(1)
        linhas.append(
            LinhaTabela(
                rotulo=nome,
                valores=[round(r.coef[1] * 10, 2), round(a * 10, 2), round(z * 10, 2), float(r.n)],
                unidade="",
                casas=2,
            )
        )
    tabela = Tabela(
        id="reacao-fiscal-amostras",
        titulo="A reação do primário à dívida, em dois períodos",
        subtitulo="pp de primário a mais para cada 10 pp de dívida líquida a mais no ano anterior",
        colunas=["Reação", "90 %: de", "até", "Anos"],
        linhas=linhas,
        fonte=fonte,
        nota=(
            "Mínimos quadrados com erro de Newey-West. Dividir a amostra deixa cada pedaço com "
            "uma dúzia de anos: a diferença entre os períodos só vale se os intervalos não se "
            "cruzam."
        ),
    )
    return cartoes, graficos, [tabela]


# ------------------------------------------------------------------ crescimento de longo prazo

PARES = {
    "BRA": "Brasil",
    "KOR": "Coreia do Sul",
    "CHL": "Chile",
    "MEX": "México",
    "CHN": "China",
    "TUR": "Turquia",
}
DECADAS = [
    (1950, 1960),
    (1960, 1970),
    (1970, 1980),
    (1980, 1990),
    (1990, 2000),
    (2000, 2010),
    (2010, 2019),
]


def contra_os_eua(dados: pwt.PorPais, pais: str) -> list[Ponto]:
    """O PIB por habitante (PIB pela despesa a PPC ÷ população) em % do dos EUA."""
    eua = dados.get("USA", {})
    saida: list[Ponto] = []
    for ano, v in sorted(dados.get(pais, {}).items()):
        u = eua.get(ano, {})
        if {"rgdpe", "pop"} <= v.keys() and {"rgdpe", "pop"} <= u.keys():
            saida.append((date(ano, 1, 1), v["rgdpe"] / v["pop"] / (u["rgdpe"] / u["pop"]) * 100))
    return saida


def decompor(brasil: dict[int, dict[str, float]], de: int, ate: int) -> tuple[float, float, float]:
    """(PIB por habitante, produto por ocupado, ocupados por habitante), % ao ano em log: os
    dois últimos somam o primeiro."""
    x0, x1 = brasil[de], brasil[ate]
    n = ate - de

    def taxa(a: float, b: float) -> float:
        return math.log(b / a) / n * 100

    return (
        taxa(x0["rgdpna"] / x0["pop"], x1["rgdpna"] / x1["pop"]),
        taxa(x0["rgdpna"] / x0["emp"], x1["rgdpna"] / x1["emp"]),
        taxa(x0["emp"] / x0["pop"], x1["emp"] / x1["pop"]),
    )


def _crescimento(ctx: Contexto) -> tuple[list[Cartao], list[Grafico], list[Tabela]]:
    dados = pwt.dados({*PARES, "USA"})
    brasil = dados["BRA"]
    ultimo = max(a for a, v in brasil.items() if {"rgdpna", "pop", "emp"} <= v.keys())
    periodos = [*DECADAS, (DECADAS[-1][1], ultimo)]
    linhas = []
    for de, ate in periodos:
        if de in brasil and ate in brasil:
            pc, prod, ocup = decompor(brasil, de, ate)
            linhas.append(
                LinhaTabela(
                    rotulo=f"{de} a {ate}",
                    valores=[round(pc, 2), round(prod, 2), round(ocup, 2)],
                    unidade="% a.a.",
                    casas=1,
                )
            )
    relativo = {iso: contra_os_eua(dados, iso) for iso in PARES}
    br_rel = relativo["BRA"]
    pico = max(br_rel, key=lambda p: p[1])
    fonte = f"{pwt.FONTE}; {CONTA}"
    cartoes = [
        cartao(
            "pib-hab-eua",
            "PIB por habitante do Brasil, em % do dos EUA",
            br_rel,
            unidade="%",
            periodicidade="A",
            casas=0,
            detalhe=f"o maior foi {br(pico[1], 0)} %, em {pico[0].year}",
            fonte=fonte,
            procedencia="calculado",
            secao="laboratorio",
            mini=74,
        ),
    ]
    graficos = [
        grafico(
            "convergencia",
            "PIB por habitante, em % do dos EUA",
            [
                serie(iso.lower(), nome, relativo[iso], casas=1)
                for iso, nome in PARES.items()
                if relativo[iso]
            ],
            unidade="% do PIB por habitante dos EUA",
            casas=0,
            periodicidade="A",
            fonte=fonte,
            nota=(
                "PIB pela despesa a paridade de poder de compra (o que a Penn World Table "
                "indica para comparar padrão de vida entre países) dividido pela população, "
                "contra o mesmo número dos EUA no mesmo ano. Subir é encostar nos EUA; ficar "
                "parado é crescer no mesmo ritmo deles."
            ),
        )
    ]
    tabela = Tabela(
        id="pib-hab-decadas",
        titulo="De onde veio o crescimento do PIB por habitante",
        subtitulo="% ao ano; as duas últimas colunas somam a primeira",
        colunas=["PIB por habitante", "Produto por ocupado", "Ocupados por habitante"],
        linhas=linhas,
        fonte=fonte,
        nota=(
            "Conta nossa sobre a Penn World Table: o PIB por habitante cresce porque cada "
            "ocupado produz mais ou porque uma parte maior da população trabalha (mais gente "
            "em idade de trabalhar, mais mulheres no mercado). A segunda fonte tem limite; a "
            "primeira, não. Taxas em logaritmo, por isso somam."
        ),
    )
    return cartoes, graficos, [tabela]


# ------------------------------------------------------------------ a seção


def montar(ctx: Contexto) -> Secao:
    cartoes: list[Cartao] = []
    graficos: list[Grafico] = []
    tabelas: list[Tabela] = []
    feitos = 0
    for nome, peca in (
        ("juro neutro", _juro_neutro),
        ("Copom", _copom),
        ("o dólar entre o mundo e o Brasil", laboratorio_ajuste.dolar),
        ("reação fiscal", _reacao),
        ("a dívida com outro primário", laboratorio_ajuste.divida),
        ("o primário esperado e o que veio", laboratorio_ajuste.promessa),
        ("os ajustes que já houve", laboratorio_ajuste.episodios),
        ("crescimento", _crescimento),
    ):
        try:
            c, g, t = peca(ctx)
        except Exception as erro:
            print(f"    laboratório: {nome} ficou de fora ({str(erro)[:140]})")
            continue
        cartoes += c
        graficos += g
        tabelas += t
        feitos += 1
    if not feitos:
        raise RuntimeError("laboratório: nenhuma peça saiu")
    neutro = next((c for c in cartoes if c.id == "juro-neutro"), None)
    taylor = next((c for c in cartoes if c.id == "taylor"), None)
    resumo = "Estimativas nossas, cada uma com o método e a faixa de erro."
    if neutro and taylor:
        resumo = (
            f"O juro neutro sai em torno de {br(neutro.valor)} % ao ano acima da inflação "
            f"({neutro.detalhe.removesuffix(', conforme o método')}, conforme o método), e a "
            f"regra de Taylor põe a Selic em {br(taylor.valor)} %. Estimativas nossas, cada "
            "uma com o método e a faixa de erro."
        )
    return Secao(
        id="laboratorio",
        titulo="Laboratório",
        resumo=resumo,
        cartoes=cartoes,
        graficos=graficos,
        tabelas=tabelas,
        gerado_em=ctx.agora(),
    )
