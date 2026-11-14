"""Mercado de trabalho: PNAD Contínua e emprego formal."""

from __future__ import annotations

from datetime import date

from sacibras import contas
from sacibras.fontes import ibge_sidra
from sacibras.schema import Secao
from sacibras.secoes.base import Contexto, br, cartao, grafico, ha_um_ano, periodo, serie


def montar(ctx: Contexto) -> Secao:
    desocupacao = ibge_sidra.serie(6381, 4099)
    rendimento = ibge_sidra.serie(6390, 5933)
    massa = contas.escalar(ibge_sidra.serie(6392, 6293), 1 / 1000)  # R$ milhões → bilhões
    formal = ctx.sgs("EMPREGO_FORMAL")
    saldo = contas.escalar(contas.diferenca(formal, 1), 1 / 1000)
    saldo_12m = contas.soma_movel(saldo, 12)

    um_ano = ha_um_ano(desocupacao)
    cartoes = [
        cartao(
            "desocupacao",
            "Desocupação",
            desocupacao,
            unidade="%",
            periodicidade="M",
            casas=1,
            detalhe=(
                f"trimestre até {periodo(desocupacao[-1][0], 'M')}"
                + (f"; um ano antes, {br(um_ano)} %" if um_ano is not None else "")
            ),
            fonte="IBGE, PNAD Contínua (SIDRA 6381)",
            secao="trabalho",
            mini=60,
        ),
        cartao(
            "rendimento",
            "Rendimento médio real",
            rendimento,
            unidade="R$",
            periodicidade="M",
            casas=0,
            detalhe=f"em um ano: {br(contas.variacao(rendimento, 12)[-1][1])} %",
            fonte="IBGE, PNAD Contínua (SIDRA 6390)",
            secao="trabalho",
            mini=60,
        ),
        cartao(
            "massa",
            "Massa de rendimento real",
            massa,
            unidade="R$ bilhões",
            periodicidade="M",
            casas=1,
            detalhe=f"em um ano: {br(contas.variacao(massa, 12)[-1][1])} %",
            fonte="IBGE, PNAD Contínua (SIDRA 6392)",
            secao="trabalho",
            mini=60,
        ),
        cartao(
            "emprego-formal",
            "Empregos formais criados em 12 meses",
            saldo_12m,
            unidade="mil",
            periodicidade="M",
            casas=0,
            detalhe=f"no mês: {br(saldo[-1][1], 0)} mil",
            fonte=ctx.fonte_sgs("EMPREGO_FORMAL"),
            procedencia="calculado",
            secao="trabalho",
            mini=48,
        ),
    ]
    inicio = date(ctx.hoje.year - 12, 1, 1)
    graficos = [
        grafico(
            "desocupacao",
            "Taxa de desocupação",
            [serie("desocupacao", "Desocupação", desocupacao, desde=inicio)],
            unidade="%",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte="IBGE, PNAD Contínua, trimestre móvel (SIDRA 6381, variável 4099)",
        ),
        grafico(
            "emprego-formal",
            "Emprego com carteira: vagas criadas no mês",
            [serie("saldo", "Variação do estoque", saldo, desde=inicio, casas=1)],
            tipo="barras",
            unidade="mil vagas",
            casas=0,
            periodicidade="M",
            janela_anos=5,
            fonte=ctx.fonte_sgs("EMPREGO_FORMAL"),
            nota=(
                "Diferença, mês a mês, do estoque de empregos formais publicado pelo Banco "
                "Central (dados do Novo Caged)."
            ),
        ),
        grafico(
            "rendimento",
            "Rendimento médio real do trabalho",
            [serie("rendimento", "Rendimento habitual", rendimento, desde=inicio, casas=0)],
            unidade="R$",
            casas=0,
            periodicidade="M",
            janela_anos=10,
            fonte="IBGE, PNAD Contínua (SIDRA 6390, variável 5933), a preços do último mês",
        ),
        grafico(
            "massa",
            "Massa de rendimento real",
            [serie("massa", "Massa de rendimento", massa, desde=inicio, casas=1)],
            unidade="R$ bilhões",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte="IBGE, PNAD Contínua (SIDRA 6392, variável 6293), a preços do último mês",
        ),
    ]
    resumo = (
        f"A desocupação está em {br(desocupacao[-1][1])} % no trimestre encerrado em "
        f"{periodo(desocupacao[-1][0], 'M')}. O rendimento médio real é de "
        f"R$ {br(rendimento[-1][1], 0)} e o emprego formal criou {br(saldo_12m[-1][1], 0)} mil "
        "vagas em 12 meses."
    )
    return Secao(
        id="trabalho",
        titulo="Trabalho",
        resumo=resumo,
        cartoes=cartoes,
        graficos=graficos,
        gerado_em=ctx.agora(),
    )
