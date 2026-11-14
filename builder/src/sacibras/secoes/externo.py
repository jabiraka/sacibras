"""Setor externo: comércio, conta corrente, investimento direto, reservas e câmbio."""

from __future__ import annotations

from datetime import date

from sacibras import contas
from sacibras.catalogo import SGS
from sacibras.schema import LinhaRef, LinhaTabela, Secao, Tabela
from sacibras.secoes.base import Contexto, br, cartao, grafico, periodo, serie
from sacibras.tipos import Ponto

# O balanço de pagamentos em partes: (chave do catálogo, rótulo, sinal). Na conta financeira o
# BPM6 lança ativos menos passivos (positivo é saída); a tabela troca o sinal para ler como
# entrada líquida de dinheiro, que é o que financia o déficit em conta corrente. O IDP já vem
# como entrada (é passivo); o IDE e o resto entram com o sinal trocado.
CONTA_CORRENTE = [
    ("BALANCA_COMERCIAL", "Balança comercial de bens", 1.0),
    ("BP_SERVICOS", "Serviços", 1.0),
    ("BP_RENDA_PRIMARIA", "Renda primária (juros, lucros e dividendos)", 1.0),
    ("BP_RENDA_SECUNDARIA", "Renda secundária (transferências)", 1.0),
    ("TRANSACOES_CORRENTES", "Conta corrente", 1.0),
]
CONTA_FINANCEIRA = [
    ("IDP", "Investimento direto no país", 1.0),
    ("BP_IDE", "Investimento direto de brasileiros no exterior", -1.0),
    ("BP_CARTEIRA", "Investimento em carteira (ações e títulos)", -1.0),
    ("BP_DERIVATIVOS", "Derivativos", -1.0),
    ("BP_OUTROS_INVESTIMENTOS", "Outros investimentos (empréstimos, depósitos)", -1.0),
    ("BP_ATIVOS_RESERVA", "Ativos de reserva (negativo: o BC comprou reservas)", -1.0),
    ("BP_CONTA_FINANCEIRA", "Conta financeira: entrada líquida", -1.0),
]


def em_12m_bi(mensal: list[Ponto], sinal: float = 1.0) -> list[Ponto]:
    """Fluxo mensal em US$ milhões → soma de 12 meses em US$ bilhões."""
    return contas.escalar(contas.soma_movel(mensal, 12), sinal / 1000)


def pib_dolares_12m(tc_12m: list[Ponto], tc_pib: list[Ponto]) -> list[Ponto]:
    """O PIB de 12 meses em US$ bilhões que o próprio BCB usa no denominador.

    Sai de duas séries dele: a conta corrente em 12 meses (US$ milhões) dividida pela mesma
    conta em % do PIB. Como o percentual vem com duas casas, só vale quando passa de 1 % em
    módulo (o erro fica abaixo de 0,5 %); fora disso a data fica de fora.
    """
    pct = dict(tc_pib)
    return [(d, v / pct[d] * 100 / 1000) for d, v in tc_12m if d in pct and abs(pct[d]) >= 1]


def tabela_balanco(
    linhas: list[tuple[str, list[Ponto], str]],
    pib: list[Ponto],
    fonte: str,
) -> Tabela:
    """Cada linha (rótulo, soma de 12 meses em US$ bi, código) no último mês e 12 meses antes,
    em US$ bilhões e em % do PIB."""
    quando = min(p[-1][0] for _, p, _ in linhas)
    antes = date(quando.year - 1, quando.month, 1)
    pib_d = dict(pib)

    def valor(pontos: list[Ponto], d: date) -> float | None:
        return dict(pontos).get(d)

    def pct(v: float | None, d: date) -> float | None:
        base = pib_d.get(d)
        return None if v is None or not base else v / base * 100

    saida: list[LinhaTabela] = []
    for rotulo, pontos, codigo in linhas:
        agora, ha_um_ano = valor(pontos, quando), valor(pontos, antes)
        saida.append(
            LinhaTabela(
                rotulo=rotulo,
                valores=[agora, ha_um_ano, pct(agora, quando), pct(ha_um_ano, antes)],
                unidade="",
                casas=1,
                fonte=f"SGS {codigo}",
            )
        )
    agora_txt, antes_txt = periodo(quando, "M"), periodo(antes, "M")
    return Tabela(
        id="balanco-pagamentos",
        titulo="Balanço de pagamentos em 12 meses",
        subtitulo=(
            f"Soma de 12 meses até {agora_txt} e até {antes_txt}. Na conta financeira, "
            "positivo é dinheiro que entrou no país; negativo, que saiu"
        ),
        colunas=[
            f"Até {agora_txt} (US$ bi)",
            f"Até {antes_txt} (US$ bi)",
            f"Até {agora_txt} (% do PIB)",
            f"Até {antes_txt} (% do PIB)",
        ],
        linhas=saida,
        fonte=fonte,
        nota=(
            "Somas de 12 meses dos fluxos mensais (BPM6) feitas por nós. Na conta financeira o "
            "BCB lança ativos menos passivos; aqui o sinal vem trocado, para ler como entrada. "
            "O % do PIB usa o PIB em dólares do próprio BCB, tirado da conta corrente em 12 "
            "meses dividida pela mesma conta em % do PIB (SGS 24419 e 23079). A diferença "
            "entre conta corrente e conta financeira são a conta capital e os erros e omissões."
        ),
    )


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
    # ---- o balanço de pagamentos em partes (guardado: gráfico no fim e tabela)
    chaves_bp = [c for c, _, _ in CONTA_CORRENTE + CONTA_FINANCEIRA]
    partes = {
        chave: (rotulo, em_12m_bi(ctx.sgs(chave), sinal), str(SGS[chave].codigo))
        for chave, rotulo, sinal in CONTA_CORRENTE + CONTA_FINANCEIRA
    }
    pib_usd = pib_dolares_12m(ctx.sgs("TC_12M"), tc_pib)
    graficos.append(
        grafico(
            "conta-corrente-partes",
            "Conta corrente em partes, em 12 meses",
            [
                serie(id_, nome, partes[chave][1], desde=inicio, casas=1)
                for id_, nome, chave in [
                    ("bens", "Bens", "BALANCA_COMERCIAL"),
                    ("servicos", "Serviços", "BP_SERVICOS"),
                    ("renda1", "Renda primária", "BP_RENDA_PRIMARIA"),
                    ("renda2", "Renda secundária", "BP_RENDA_SECUNDARIA"),
                ]
            ],
            tipo="empilhado",
            unidade="US$ bilhões, soma de 12 meses",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=ctx.fonte_sgs(
                "BALANCA_COMERCIAL", "BP_SERVICOS", "BP_RENDA_PRIMARIA", "BP_RENDA_SECUNDARIA"
            ),
            nota=(
                "Somas de 12 meses dos saldos mensais do balanço de pagamentos (BPM6), feitas "
                "por nós. As barras somadas dão o saldo em conta corrente; renda primária é o "
                "que se paga e recebe de juros, lucros e dividendos."
            ),
        )
    )
    tabelas = [
        tabela_balanco(
            [partes[c] for c in chaves_bp],
            pib_usd,
            fonte=ctx.fonte_sgs(*chaves_bp, "TC_12M", "TC_12M_PIB"),
        )
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
        tabelas=tabelas,
        gerado_em=ctx.agora(),
    )
