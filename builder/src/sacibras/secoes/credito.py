"""Crédito: saldo, custo, calote e o bolso das famílias."""

from __future__ import annotations

from datetime import date

from sacibras import contas
from sacibras.schema import Secao
from sacibras.secoes.base import Contexto, br, cartao, grafico, periodo, serie


def montar(ctx: Contexto) -> Secao:
    credito_pib = ctx.sgs("CREDITO_PIB")
    saldo = ctx.sgs("CREDITO_SALDO")
    taxa = ctx.sgs("CREDITO_TAXA")
    spread = ctx.sgs("CREDITO_SPREAD")
    calote = ctx.sgs("CREDITO_INADIMPLENCIA")
    endividamento = ctx.sgs("FAMILIAS_ENDIVIDAMENTO")
    comprometimento = ctx.sgs("FAMILIAS_COMPROMETIMENTO")
    crescimento = contas.variacao(saldo, 12)

    def c(id: str, rotulo: str, chave: str, unidade: str, casas: int, detalhe: str = ""):  # type: ignore[no-untyped-def]
        return cartao(
            id,
            rotulo,
            ctx.sgs(chave),
            unidade=unidade,
            periodicidade="M",
            casas=casas,
            detalhe=detalhe,
            fonte=ctx.fonte_sgs(chave),
            secao="credito",
            mini=60,
        )

    cartoes = [
        c(
            "credito-pib",
            "Crédito total",
            "CREDITO_PIB",
            "% do PIB",
            1,
            f"cresce {br(crescimento[-1][1])} % em 12 meses",
        ),
        c("credito-taxa", "Juro médio do crédito", "CREDITO_TAXA", "% a.a.", 1),
        c("credito-spread", "Spread médio", "CREDITO_SPREAD", "pp", 1),
        c(
            "inadimplencia",
            "Inadimplência",
            "CREDITO_INADIMPLENCIA",
            "%",
            2,
            "atrasos acima de 90 dias",
        ),
        c(
            "endividamento",
            "Endividamento das famílias",
            "FAMILIAS_ENDIVIDAMENTO",
            "%",
            1,
            "dívida sobre a renda de 12 meses",
        ),
        c(
            "comprometimento",
            "Renda comprometida com dívida",
            "FAMILIAS_COMPROMETIMENTO",
            "%",
            1,
            "parcelas sobre a renda do mês",
        ),
    ]
    inicio = date(ctx.hoje.year - 12, 1, 1)
    graficos = [
        grafico(
            "credito-pib",
            "Crédito em relação ao PIB",
            [serie("credito", "Saldo de crédito", credito_pib, desde=inicio)],
            unidade="% do PIB",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs("CREDITO_PIB"),
        ),
        grafico(
            "credito-custo",
            "Quanto custa o crédito",
            [
                serie("taxa", "Juro médio", taxa, desde=inicio),
                serie("spread", "Spread (juro menos custo de captação)", spread, desde=inicio),
            ],
            unidade="% a.a. e pontos percentuais",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs("CREDITO_TAXA", "CREDITO_SPREAD"),
        ),
        grafico(
            "inadimplencia",
            "Inadimplência da carteira de crédito",
            [serie("inadimplencia", "Atrasos acima de 90 dias", calote, desde=inicio)],
            unidade="% da carteira",
            casas=2,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs("CREDITO_INADIMPLENCIA"),
        ),
        grafico(
            "familias",
            "O peso da dívida nas famílias",
            [
                serie(
                    "endividamento", "Dívida sobre a renda de 12 meses", endividamento, desde=inicio
                ),
                serie(
                    "comprometimento",
                    "Parcelas sobre a renda do mês",
                    comprometimento,
                    desde=inicio,
                ),
            ],
            unidade="% da renda",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs("FAMILIAS_ENDIVIDAMENTO", "FAMILIAS_COMPROMETIMENTO"),
        ),
    ]
    resumo = (
        f"O crédito soma {br(credito_pib[-1][1])} % do PIB em {periodo(credito_pib[-1][0], 'M')}, "
        f"a um juro médio de {br(taxa[-1][1])} % ao ano. As famílias devem "
        f"{br(endividamento[-1][1])} % da renda de um ano e gastam {br(comprometimento[-1][1])} % "
        "da renda do mês com parcelas."
    )
    return Secao(
        id="credito",
        titulo="Crédito",
        resumo=resumo,
        cartoes=cartoes,
        graficos=graficos,
        gerado_em=ctx.agora(),
    )
