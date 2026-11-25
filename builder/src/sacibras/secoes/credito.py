"""Crédito: saldo, custo, calote e o bolso das famílias."""

from __future__ import annotations

from datetime import date

from sacibras import contas
from sacibras.schema import Secao
from sacibras.secoes.base import Contexto, br, cartao, grafico, periodo, serie
from sacibras.tipos import Ponto


def real_em_12m(nominal: list[Ponto], ipca_12m: list[Ponto]) -> list[Ponto]:
    """Variação em 12 meses descontada a inflação do mesmo período: (1 + n) / (1 + ipca) − 1."""
    ipca = dict(ipca_12m)
    return [(d, ((1 + v / 100) / (1 + ipca[d] / 100) - 1) * 100) for d, v in nominal if d in ipca]


# Os juros das pessoas físicas no gráfico por modalidade, do mais caro ao mais barato.
MODALIDADES_PF: list[tuple[str, str, str]] = [
    ("rotativo", "Cartão rotativo", "PF_CARTAO_ROTATIVO"),
    ("parcelado", "Cartão parcelado", "PF_CARTAO_PARCELADO"),
    ("cheque", "Cheque especial", "PF_CHEQUE_ESPECIAL"),
    ("pessoal", "Crédito pessoal", "PF_PESSOAL"),
    ("consignado", "Consignado", "PF_CONSIGNADO"),
]


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

    # ---- os juros das pessoas físicas por modalidade (revisão das telas, 15/11/2026: quem
    # busca "juros do cartão" ou "cheque especial" não achava nada)
    rotativo = ctx.sgs("PF_CARTAO_ROTATIVO")
    cheque = ctx.sgs("PF_CHEQUE_ESPECIAL")
    cartoes.append(
        cartao(
            "juro-cartao",
            "Juro do cartão rotativo",
            rotativo,
            unidade="% a.a.",
            periodicidade="M",
            casas=1,
            detalhe=f"cheque especial: {br(cheque[-1][1])} % a.a.",
            fonte=ctx.fonte_sgs("PF_CARTAO_ROTATIVO", "PF_CHEQUE_ESPECIAL"),
            secao="credito",
            mini=60,
        )
    )

    # ---- casa própria e bolso das famílias (entra guardado: depois dos números de antes)
    taxa_mercado = ctx.sgs("IMOB_TAXA_MERCADO")
    taxa_regulada = ctx.sgs("IMOB_TAXA_REGULADA")
    concessoes_12m = contas.escalar(contas.soma_movel(ctx.sgs("IMOB_CONCESSOES"), 12), 1 / 1000)
    concessoes_var = contas.variacao(concessoes_12m, 12)
    ivgr_12m = contas.variacao(ctx.sgs("IVGR"), 12)
    ipca_12m = ctx.sgs("IPCA_12M")
    ivgr_real = real_em_12m(ivgr_12m, ipca_12m)
    juros_familias = ctx.sgs("FAMILIAS_COMPROMETIMENTO_JUROS")
    sem_casa = ctx.sgs("FAMILIAS_ENDIVIDAMENTO_SEM_HABITACAO")
    ipca_no_mes = dict(ipca_12m).get(ivgr_12m[-1][0])
    real_no_mes = dict(ivgr_real).get(ivgr_12m[-1][0])
    cartoes += [
        c(
            "imobiliario-taxa",
            "Juro do financiamento imobiliário",
            "IMOB_TAXA_MERCADO",
            "% a.a.",
            1,
            f"mercado; regulada (SFH): {br(taxa_regulada[-1][1])} % a.a.",
        ),
        cartao(
            "imobiliario-concessoes",
            "Financiamento imobiliário concedido, 12 meses",
            concessoes_12m,
            unidade="R$ bilhões",
            periodicidade="M",
            casas=1,
            detalhe=f"{br(concessoes_var[-1][1])} % contra os 12 meses anteriores",
            fonte=ctx.fonte_sgs("IMOB_CONCESSOES"),
            secao="credito",
            mini=60,
        ),
        cartao(
            "ivgr",
            "Preço dos imóveis (IVG-R), 12 meses",
            ivgr_12m,
            unidade="% em 12 meses",
            periodicidade="M",
            casas=1,
            detalhe=(
                f"IPCA no mesmo período: {br(ipca_no_mes)} %; descontado ele, {br(real_no_mes)} %"
                if ipca_no_mes is not None and real_no_mes is not None
                else "valor de avaliação dos imóveis financiados"
            ),
            fonte=ctx.fonte_sgs("IVGR", "IPCA_12M"),
            procedencia="calculado",
            secao="credito",
            mini=60,
        ),
        c(
            "comprometimento-juros",
            "Renda comprometida só com juros",
            "FAMILIAS_COMPROMETIMENTO_JUROS",
            "%",
            1,
            f"parcela inteira (juros e amortização): {br(comprometimento[-1][1])} %",
        ),
        c(
            "endividamento-sem-casa",
            "Endividamento sem o financiamento imobiliário",
            "FAMILIAS_ENDIVIDAMENTO_SEM_HABITACAO",
            "%",
            1,
            f"com ele: {br(endividamento[-1][1])} % da renda de 12 meses",
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
                serie("spread", "Spread", spread, desde=inicio),
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
                serie("endividamento", "Dívida / renda de 12 meses", endividamento, desde=inicio),
                serie(
                    "comprometimento",
                    "Parcelas / renda do mês",
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
        grafico(
            "imobiliario-taxa",
            "Juro do financiamento imobiliário",
            [
                serie("mercado", "Taxa de mercado", taxa_mercado, desde=inicio),
                serie("regulada", "Taxa regulada (SFH)", taxa_regulada, desde=inicio),
            ],
            unidade="% a.a.",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs("IMOB_TAXA_MERCADO", "IMOB_TAXA_REGULADA"),
            nota=(
                "Média das novas operações com pessoas físicas. A regulada é a do SFH, com "
                "dinheiro da poupança e do FGTS."
            ),
        ),
        grafico(
            "imobiliario-concessoes",
            "Financiamento imobiliário concedido em 12 meses",
            [serie("concessoes", "Pessoas físicas", concessoes_12m, desde=inicio, casas=1)],
            tipo="area",
            unidade="R$ bilhões, soma de 12 meses",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs("IMOB_CONCESSOES"),
            nota="Soma de 12 meses, em reais correntes.",
        ),
        grafico(
            "ivgr",
            "Preço dos imóveis contra a inflação",
            [
                serie("ivgr", "Imóveis (IVG-R)", ivgr_12m, desde=inicio),
                serie("ipca", "IPCA", ipca_12m, desde=inicio),
            ],
            unidade="% em 12 meses",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs("IVGR", "IPCA_12M"),
            nota=(
                "IVG-R: avaliação dos imóveis financiados em 13 regiões metropolitanas. A "
                "variação em 12 meses é cálculo próprio."
            ),
        ),
        grafico(
            "familias-juros",
            "Quanto da renda vai para juros",
            [
                serie("servico", "Parcela inteira", comprometimento, desde=inicio),
                serie("juros", "Só os juros", juros_familias, desde=inicio),
            ],
            unidade="% da renda do mês",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs("FAMILIAS_COMPROMETIMENTO", "FAMILIAS_COMPROMETIMENTO_JUROS"),
            nota="A diferença entre as linhas é a amortização, o que abate da dívida.",
        ),
        grafico(
            "familias-sem-casa",
            "Dívida das famílias, com e sem a casa própria",
            [
                serie("total", "Toda a dívida", endividamento, desde=inicio),
                serie("sem-casa", "Sem o imobiliário", sem_casa, desde=inicio),
            ],
            unidade="% da renda de 12 meses",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs("FAMILIAS_ENDIVIDAMENTO", "FAMILIAS_ENDIVIDAMENTO_SEM_HABITACAO"),
        ),
        grafico(
            "juros-modalidades",
            "Juros das pessoas físicas, por modalidade",
            [serie(id, nome, ctx.sgs(chave), desde=inicio) for id, nome, chave in MODALIDADES_PF],
            unidade="% a.a.",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs(*(chave for _, _, chave in MODALIDADES_PF)),
            nota=(
                "Recursos livres. Rotativo: quem paga só parte da fatura; parcelado: quem divide "
                "a fatura ou a compra com juros."
            ),
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
