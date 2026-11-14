"""Setor externo: comércio, conta corrente, investimento direto, reservas e câmbio."""

from __future__ import annotations

from datetime import date

from sacibras import contas
from sacibras.schema import LinhaRef, Secao
from sacibras.secoes.base import Contexto, br, cartao, grafico, periodo, serie


def montar(ctx: Contexto) -> Secao:
    balanca_12m = contas.escalar(contas.soma_movel(ctx.sgs("BALANCA_COMERCIAL"), 12), 1 / 1000)
    tc_pib = ctx.sgs("TC_12M_PIB")
    idp_pib = ctx.sgs("IDP_12M_PIB")
    reservas = contas.escalar(ctx.sgs("RESERVAS"), 1 / 1000)
    cambio_real = ctx.sgs("CAMBIO_REAL_EFETIVO", anos=25)
    icbr = ctx.sgs("ICBR")
    media_cambio = sum(v for _, v in cambio_real) / len(cambio_real)

    cartoes = [
        cartao(
            "transacoes-correntes",
            "Conta corrente, 12 meses",
            tc_pib,
            unidade="% do PIB",
            periodicidade="M",
            casas=2,
            detalhe=f"investimento direto: {br(idp_pib[-1][1], 2)} % do PIB",
            fonte=ctx.fonte_sgs("TC_12M_PIB", "IDP_12M_PIB"),
            secao="externo",
            mini=60,
        ),
        cartao(
            "balanca",
            "Saldo comercial, 12 meses",
            balanca_12m,
            unidade="US$ bilhões",
            periodicidade="M",
            casas=1,
            fonte=ctx.fonte_sgs("BALANCA_COMERCIAL"),
            procedencia="calculado",
            secao="externo",
            mini=60,
        ),
        cartao(
            "reservas",
            "Reservas internacionais",
            reservas,
            unidade="US$ bilhões",
            periodicidade="M",
            casas=1,
            fonte=ctx.fonte_sgs("RESERVAS"),
            secao="externo",
            mini=60,
        ),
        cartao(
            "cambio-real",
            "Câmbio real efetivo",
            cambio_real,
            unidade="índice",
            periodicidade="M",
            casas=1,
            detalhe=f"média de 25 anos: {br(media_cambio)}; acima, real mais fraco",
            fonte=ctx.fonte_sgs("CAMBIO_REAL_EFETIVO"),
            secao="externo",
            mini=120,
        ),
    ]
    inicio = date(ctx.hoje.year - 15, 1, 1)
    graficos = [
        grafico(
            "conta-corrente",
            "Conta corrente e investimento direto",
            [
                serie("tc", "Transações correntes", tc_pib, desde=inicio),
                serie("idp", "Investimento direto no país", idp_pib, desde=inicio),
            ],
            unidade="% do PIB, em 12 meses",
            casas=2,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs("TC_12M_PIB", "IDP_12M_PIB"),
            nota=(
                "Quando o investimento direto supera o déficit em conta corrente, ele o "
                "financia inteiro."
            ),
        ),
        grafico(
            "balanca",
            "Saldo da balança comercial em 12 meses",
            [serie("balanca", "Saldo comercial", balanca_12m, desde=inicio, casas=1)],
            tipo="area",
            unidade="US$ bilhões",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=f"{ctx.fonte_sgs('BALANCA_COMERCIAL')} (balanço de pagamentos), soma de 12 meses",
        ),
        grafico(
            "reservas",
            "Reservas internacionais",
            [serie("reservas", "Reservas", reservas, desde=inicio, casas=1)],
            unidade="US$ bilhões",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs("RESERVAS"),
        ),
        grafico(
            "cambio-real",
            "Câmbio real efetivo",
            [serie("cre", "Taxa de câmbio real efetiva (IPCA)", cambio_real)],
            unidade="índice, jun/1994 = 100",
            casas=1,
            periodicidade="M",
            janela_anos=20,
            linhas=[LinhaRef(valor=round(media_cambio, 1), rotulo="média de 25 anos")],
            fonte=ctx.fonte_sgs("CAMBIO_REAL_EFETIVO"),
            nota=(
                "Descontada a inflação daqui e dos parceiros comerciais. Para cima: real mais "
                "fraco."
            ),
        ),
        grafico(
            "commodities",
            "Preço das commodities que o Brasil vende (IC-Br)",
            [
                serie("icbr", "IC-Br", icbr, desde=inicio),
                serie("agro", "Agropecuária", ctx.sgs("ICBR_AGRO"), desde=inicio),
                serie("metal", "Metal", ctx.sgs("ICBR_METAL"), desde=inicio),
                serie("energia", "Energia", ctx.sgs("ICBR_ENERGIA"), desde=inicio),
            ],
            unidade="índice, em reais",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs("ICBR", "ICBR_AGRO", "ICBR_METAL", "ICBR_ENERGIA"),
        ),
    ]
    sinal = "déficit" if tc_pib[-1][1] < 0 else "superávit"
    resumo = (
        f"A conta corrente tem {sinal} de {br(abs(tc_pib[-1][1]), 2)} % do PIB em 12 meses até "
        f"{periodo(tc_pib[-1][0], 'M')}; o investimento direto soma {br(idp_pib[-1][1], 2)} % do "
        f"PIB. As reservas estão em US$ {br(reservas[-1][1])} bilhões."
    )
    return Secao(
        id="externo",
        titulo="Setor externo",
        resumo=resumo,
        cartoes=cartoes,
        graficos=graficos,
        gerado_em=ctx.agora(),
    )
