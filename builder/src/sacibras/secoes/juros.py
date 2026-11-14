"""Juros e Copom: a Selic realizada, a esperada pelo Focus e o juro real."""

from __future__ import annotations

from datetime import date, timedelta

from sacibras.catalogo import SGS
from sacibras.fontes import bcb_copom, bcb_focus, bcb_sgs
from sacibras.schema import Secao
from sacibras.secoes.base import Contexto, br, cartao, grafico, periodo, serie
from sacibras.tipos import Ponto


def _mensal(diaria: list[Ponto]) -> list[Ponto]:
    """O último valor de cada mês, na data do 1º dia do mês."""
    por_mes: dict[date, float] = {}
    for d, v in diaria:
        por_mes[d.replace(day=1)] = v
    return sorted(por_mes.items())


def _mudancas(diaria: list[Ponto]) -> list[Ponto]:
    """Só os dias em que o valor muda, mais o último: o degrau sem peso."""
    saida: list[Ponto] = []
    for ponto in diaria:
        if not saida or saida[-1][1] != ponto[1]:
            saida.append(ponto)
    if diaria and saida[-1][0] != diaria[-1][0]:
        saida.append(diaria[-1])
    return saida


def montar(ctx: Contexto) -> Secao:
    meta = ctx.sgs("SELIC_META", anos=20)
    efetiva = ctx.sgs("SELIC_ANUAL", anos=3)
    ipca12 = ctx.sgs("IPCA_12M", anos=20)
    ipca = ctx.sgs("IPCA")

    # A série 432 vem preenchida até o dia da próxima decisão do Copom.
    futuro = bcb_sgs.ler(SGS["SELIC_META"], ctx.hoje, ctx.hoje + timedelta(days=120))
    proxima = futuro[-1][0] if futuro and futuro[-1][0] > ctx.hoje else None

    todas = bcb_copom.reunioes()
    ultima = todas[-1]
    edicao, por_reuniao = bcb_focus.selic_por_reuniao()
    esperada: list[Ponto] = [(ctx.hoje.replace(day=1), meta[-1][1])]
    for rotulo, mediana in por_reuniao:
        ordem, ano = rotulo.removeprefix("R").split("/")
        quando = bcb_copom.mes_da_reuniao(todas, int(ordem), int(ano), proxima)
        if quando > esperada[-1][0]:
            esperada.append((quando, mediana))
    ctx.memo["focus_selic_reuniao"] = esperada

    # Juro real ex-post: Selic meta descontada do IPCA dos 12 meses anteriores.
    meta_mensal = _mensal(meta)
    mapa_ipca = dict(ipca12)
    real_ex_post = [
        (d, ((1 + v / 100) / (1 + mapa_ipca[d] / 100) - 1) * 100)
        for d, v in meta_mensal
        if d in mapa_ipca
    ]
    # Ex-ante: Selic meta descontada do IPCA que o Focus espera para os próximos 12 meses.
    _, focus_mensal = bcb_focus.mensais_hoje("IPCA")
    a_frente = [v for d, v in focus_mensal if d > ipca[-1][0]][:12]
    fator = 1.0
    for v in a_frente:
        fator *= 1 + v / 100
    ipca_esperado = (fator - 1) * 100
    real_ex_ante = ((1 + meta[-1][1] / 100) / fator - 1) * 100
    ctx.memo["ipca_esperado_12m"] = ipca_esperado

    desde_quando = _mudancas(meta)[-2][0] if len(_mudancas(meta)) > 1 else meta[0][0]
    fim_do_ano = next((v for r, v in reversed(por_reuniao) if r.endswith(str(ctx.hoje.year))), None)
    cartoes = [
        cartao(
            "selic-meta",
            "Selic meta",
            meta,
            unidade="% a.a.",
            periodicidade="D",
            casas=2,
            detalhe=(
                f"neste nível desde {periodo(desde_quando, 'D')}"
                + (f"; próxima decisão em {periodo(proxima, 'D')}" if proxima else "")
            ),
            fonte=ctx.fonte_sgs("SELIC_META"),
            secao="juros",
            mini=1500,
            referencia=ultima.data,
        ),
        cartao(
            "juro-real-ex-ante",
            "Juro real esperado (ex-ante)",
            [(edicao, real_ex_ante)],
            unidade="% a.a.",
            periodicidade="D",
            casas=2,
            detalhe=f"Selic menos IPCA esperado em 12 meses ({br(ipca_esperado, 2)} %)",
            fonte=f"{ctx.fonte_sgs('SELIC_META')}; Focus (medianas mensais do IPCA)",
            procedencia="calculado",
            secao="juros",
        ),
        cartao(
            "juro-real-ex-post",
            "Juro real (ex-post)",
            real_ex_post,
            unidade="% a.a.",
            periodicidade="M",
            casas=2,
            detalhe="Selic menos IPCA dos últimos 12 meses",
            fonte=ctx.fonte_sgs("SELIC_META", "IPCA_12M"),
            procedencia="calculado",
            secao="juros",
            mini=120,
        ),
        cartao(
            "selic-efetiva",
            "Selic efetiva",
            efetiva,
            unidade="% a.a.",
            periodicidade="D",
            casas=2,
            detalhe="taxa praticada no dia, base 252",
            fonte=ctx.fonte_sgs("SELIC_ANUAL"),
            secao="juros",
            mini=250,
        ),
    ]
    if fim_do_ano is not None and por_reuniao:
        final, ultimo_valor = por_reuniao[-1]
        cartoes.append(
            cartao(
                "focus-selic",
                f"Focus: Selic no fim de {ctx.hoje.year}",
                [(edicao, fim_do_ano)],
                unidade="% a.a.",
                periodicidade="D",
                casas=2,
                detalhe=f"reunião {final.removeprefix('R')}: {br(ultimo_valor, 2)} %",
                fonte="Banco Central, Focus (mediana por reunião do Copom)",
                procedencia="mercado",
                secao="juros",
            )
        )

    inicio = date(ctx.hoje.year - 20, 1, 1)
    graficos = [
        grafico(
            "selic-trajetoria",
            "Selic: a decidida e a que o mercado espera",
            [
                serie("meta", "Selic meta", _mudancas(meta), desde=inicio),
                serie("focus", "Focus, por reunião (mediana)", esperada, papel="consenso"),
            ],
            tipo="degrau",
            unidade="% a.a.",
            casas=2,
            periodicidade="D",
            janela_anos=5,
            fonte=(
                f"{ctx.fonte_sgs('SELIC_META')}; Focus de {periodo(edicao, 'D')} "
                "(ExpectativasMercadoSelic)"
            ),
            nota=(
                "O Focus pergunta a Selic de cada reunião do Copom. As reuniões futuras estão "
                "no mês em que caiu a reunião de mesma ordem no último calendário conhecido."
            ),
            largura="inteira",
        ),
        grafico(
            "juro-real",
            "Juro real: Selic descontada da inflação",
            [serie("ex-post", "Juro real ex-post", real_ex_post, desde=inicio)],
            tipo="area",
            unidade="% a.a.",
            casas=2,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs("SELIC_META", "IPCA_12M"),
            nota=(
                "Ex-post: (1 + Selic meta) / (1 + IPCA dos 12 meses anteriores) − 1. Olha para "
                "trás; o ex-ante do cartão usa a inflação esperada pelo Focus."
            ),
        ),
        grafico(
            "selic-ipca",
            "Selic e IPCA em 12 meses",
            [
                serie("selic", "Selic meta", meta_mensal, desde=inicio),
                serie("ipca", "IPCA em 12 meses", ipca12, desde=inicio),
            ],
            unidade="%",
            casas=2,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs("SELIC_META", "IPCA_12M"),
        ),
    ]
    resumo = (
        f"A Selic está em {br(meta[-1][1], 2)} % ao ano desde {periodo(desde_quando, 'D')} "
        f"(reunião nº {ultima.numero} do Copom, em {periodo(ultima.data, 'D')}). Descontada a "
        f"inflação esperada para os próximos 12 meses, o juro real é de {br(real_ex_ante, 1)} % "
        "ao ano."
    )
    return Secao(
        id="juros",
        titulo="Juros e Copom",
        resumo=resumo,
        cartoes=cartoes,
        graficos=graficos,
        gerado_em=ctx.agora(),
    )
