"""Mercado de trabalho: PNAD Contínua e emprego formal."""

from __future__ import annotations

from datetime import date

from sacibras import contas
from sacibras.fontes import ibge_sidra
from sacibras.schema import Cartao, LinhaTabela, Secao, Tabela
from sacibras.secoes.base import Contexto, br, cartao, grafico, ha_um_ano, periodo, serie
from sacibras.tipos import Periodicidade, Ponto

PNAD = "IBGE, PNAD Contínua"

# Tabelas e variáveis do SIDRA, conferidas pela própria resposta de
# `apisidra.ibge.gov.br/values/t/<tabela>/n1/all/v/all/p/last 1` em 14/11/2026 (a API de
# metadados do IBGE não responde de fora do Brasil). Todas em trimestre móvel, Brasil,
# pessoas de 14 anos ou mais, salvo dito.
PARTICIPACAO = (5944, 4096)
"""Taxa de participação na força de trabalho, na semana de referência (%)."""
NIVEL_OCUPACAO = (6379, 4097)
"""Nível da ocupação, na semana de referência (%): ocupados sobre a população de 14+."""
DESOCUPACAO_SUBOCUPACAO = (6439, 4114)
"""Taxa combinada de desocupação e de subocupação por insuficiência de horas trabalhadas (%)."""
DESOCUPACAO_POTENCIAL = (6440, 4116)
"""Taxa combinada de desocupação e força de trabalho potencial (%)."""
SUBUTILIZACAO = (6441, 4118)
"""Taxa composta de subutilização da força de trabalho (%)."""
INFORMALIDADE = (8513, 12466)
"""Taxa de informalidade das pessoas ocupadas (%)."""
DESALENTO = (6807, 9869)
"""Percentual de pessoas desalentadas na população na força de trabalho ou desalentada (%)."""
DESALENTADOS = (6438, 1641, "c604/46254")
"""Pessoas de 14 anos ou mais (mil pessoas), tipo de medida de subutilização "Desalentado"
(classificação 604, categoria 46254)."""
CONDICAO = (6318, 1641, "c629/32387,32446")
"""Pessoas de 14 anos ou mais (mil pessoas) por condição: 32387 "Força de trabalho -
ocupada", 32446 "Força de trabalho - desocupada" (classificação 629)."""
OCUPADOS, DESOCUPADOS = "32387", "32446"
PROCURA_LONGA = (1616, 4110, "c1965/101227")
"""Trimestre civil, não móvel: distribuição percentual das pessoas desocupadas (%) por tempo
de procura de trabalho, categoria "2 anos ou mais" (classificação 1965, categoria 101227)."""


def _meses_antes(pontos: list[Ponto], meses: int, de: date | None = None) -> float | None:
    """O valor `meses` antes de `de` (ou do último ponto), se a série tiver essa data."""
    if not pontos:
        return None
    base = de or pontos[-1][0]
    total = base.year * 12 + base.month - 1 - meses
    alvo = date(total // 12, total % 12 + 1, 1)
    return dict(pontos).get(alvo)


def _linha(
    rotulo: str,
    pontos: list[Ponto],
    unidade: str,
    *,
    referencia: date,
    casas: int = 1,
    periodicidade: Periodicidade = "M",
    fonte: str = "",
) -> LinhaTabela:
    """Agora, três meses antes e um ano antes. Se o último ponto não for o da `referencia`
    da tabela (trimestre civil, série atrasada), o período dele vai no rótulo."""
    ultimo = pontos[-1][0] if pontos else referencia
    if ultimo != referencia:
        rotulo = f"{rotulo} ({periodo(ultimo, periodicidade)})"
    return LinhaTabela(
        rotulo=rotulo,
        valores=[
            None if v is None else round(v, casas + 2)
            for v in (
                pontos[-1][1] if pontos else None,
                _meses_antes(pontos, 3),
                _meses_antes(pontos, 12),
            )
        ],
        unidade=unidade,
        casas=casas,
        fonte=fonte,
    )


def _cartao_taxa(id: str, rotulo: str, pontos: list[Ponto], tabela: int) -> Cartao:
    um_ano = ha_um_ano(pontos)
    return cartao(
        id,
        rotulo,
        pontos,
        unidade="%",
        periodicidade="M",
        casas=1,
        detalhe=(
            f"trimestre até {periodo(pontos[-1][0], 'M')}"
            + (f"; um ano antes, {br(um_ano)} %" if um_ano is not None else "")
        ),
        fonte=f"{PNAD} (SIDRA {tabela})",
        secao="trabalho",
        mini=60,
    )


def montar(ctx: Contexto) -> Secao:
    desocupacao = ibge_sidra.serie(6381, 4099)
    rendimento = ibge_sidra.serie(6390, 5933)
    massa = contas.escalar(ibge_sidra.serie(6392, 6293), 1 / 1000)  # R$ milhões → bilhões
    formal = ctx.sgs("EMPREGO_FORMAL")
    saldo = contas.escalar(contas.diferenca(formal, 1), 1 / 1000)
    saldo_12m = contas.soma_movel(saldo, 12)
    saldo_3m = contas.media_movel(saldo, 3)

    participacao = ibge_sidra.serie(*PARTICIPACAO)
    nivel = ibge_sidra.serie(*NIVEL_OCUPACAO)
    sub_horas = ibge_sidra.serie(*DESOCUPACAO_SUBOCUPACAO)
    sub_potencial = ibge_sidra.serie(*DESOCUPACAO_POTENCIAL)
    subutilizacao = ibge_sidra.serie(*SUBUTILIZACAO)
    informalidade = ibge_sidra.serie(*INFORMALIDADE)
    desalento = ibge_sidra.serie(*DESALENTO)
    desalentados = contas.escalar(
        ibge_sidra.serie(DESALENTADOS[0], DESALENTADOS[1], classificacao=DESALENTADOS[2]),
        1 / 1000,
    )  # mil pessoas → milhões
    condicao = ibge_sidra.series(
        CONDICAO[0], CONDICAO[1], classificacao=CONDICAO[2], por="Condição"
    )
    ocupados = contas.escalar(condicao.get(OCUPADOS, []), 1 / 1000)
    desocupados = contas.escalar(condicao.get(DESOCUPADOS, []), 1 / 1000)
    procura_longa = ibge_sidra.serie(
        PROCURA_LONGA[0], PROCURA_LONGA[1], classificacao=PROCURA_LONGA[2], trimestral=True
    )

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
            detalhe=(
                f"no mês: {br(saldo[-1][1], 0)} mil; média de 3 meses: {br(saldo_3m[-1][1], 0)} mil"
            ),
            fonte=ctx.fonte_sgs("EMPREGO_FORMAL"),
            procedencia="calculado",
            secao="trabalho",
            mini=48,
        ),
        # Os que vêm daqui ficam atrás de "Mais números".
        _cartao_taxa("subutilizacao", "Subutilização", subutilizacao, SUBUTILIZACAO[0]),
        _cartao_taxa(
            "participacao", "Participação na força de trabalho", participacao, PARTICIPACAO[0]
        ),
        _cartao_taxa("nivel-ocupacao", "Nível de ocupação", nivel, NIVEL_OCUPACAO[0]),
        _cartao_taxa("informalidade", "Informalidade", informalidade, INFORMALIDADE[0]),
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
            [
                serie("saldo", "Variação do estoque", saldo, desde=inicio, casas=1),
                serie("saldo-3m", "Média de 3 meses", saldo_3m, desde=inicio, casas=1),
            ],
            tipo="barras",
            unidade="mil vagas",
            casas=0,
            periodicidade="M",
            janela_anos=5,
            fonte=ctx.fonte_sgs("EMPREGO_FORMAL"),
            nota=(
                "Diferença, mês a mês, do estoque de empregos formais publicado pelo Banco "
                "Central (dados do Novo Caged); a linha é a média dos três últimos meses."
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
        grafico(
            "subutilizacao",
            "Subutilização: da desocupação à taxa composta",
            [
                serie("desocupacao", "Desocupação", desocupacao, desde=inicio),
                serie(
                    "desocupacao-horas",
                    "Desocupação e subocupação por horas",
                    sub_horas,
                    desde=inicio,
                ),
                serie(
                    "desocupacao-potencial",
                    "Desocupação e força de trabalho potencial",
                    sub_potencial,
                    desde=inicio,
                ),
                serie("subutilizacao", "Taxa composta", subutilizacao, desde=inicio),
            ],
            unidade="%",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=(
                f"{PNAD}, trimestre móvel (SIDRA 6381, 6439, 6440 e 6441, variáveis 4099, "
                "4114, 4116 e 4118)"
            ),
            nota=(
                "As quatro medidas do IBGE, da mais estreita à mais larga: a taxa composta "
                "junta aos desocupados quem trabalha menos horas do que queria e quem queria "
                "trabalhar mas não procurou ou não podia começar, sobre a força de trabalho "
                "ampliada."
            ),
        ),
        grafico(
            "participacao",
            "Participação na força de trabalho e nível de ocupação",
            [
                serie("participacao", "Participação", participacao, desde=inicio),
                serie("nivel-ocupacao", "Nível de ocupação", nivel, desde=inicio),
            ],
            unidade="%",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=f"{PNAD}, trimestre móvel (SIDRA 5944, variável 4096; SIDRA 6379, variável 4097)",
            nota=(
                "Participação: quem trabalha ou procura trabalho; nível de ocupação: só quem "
                "trabalha; as duas sobre a população de 14 anos ou mais."
            ),
        ),
        grafico(
            "informalidade",
            "Taxa de informalidade",
            [serie("informalidade", "Informalidade", informalidade, desde=inicio)],
            unidade="%",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=f"{PNAD}, trimestre móvel (SIDRA 8513, variável 12466)",
            nota=(
                "Ocupados sem carteira (empregados do setor privado e domésticos), por conta "
                "própria e empregadores sem CNPJ e quem ajuda a família sem salário, sobre "
                "todos os ocupados (definição do IBGE)."
            ),
        ),
        grafico(
            "desalento",
            "Desalentados",
            [serie("desalento", "Desalentados", desalento, desde=inicio)],
            unidade="%",
            casas=1,
            periodicidade="M",
            janela_anos=10,
            fonte=f"{PNAD}, trimestre móvel (SIDRA 6807, variável 9869)",
            nota=(
                "Quem queria trabalhar e podia começar, mas não procurou por achar que não "
                "encontraria vaga, sobre a força de trabalho mais os desalentados."
            ),
        ),
        grafico(
            "procura-longa",
            "Desocupados que procuram trabalho há 2 anos ou mais",
            [serie("procura-longa", "Há 2 anos ou mais", procura_longa, desde=inicio)],
            unidade="% dos desocupados",
            casas=1,
            periodicidade="T",
            janela_anos=10,
            fonte=(
                f"{PNAD}, trimestre civil (SIDRA 1616, variável 4110, tempo de procura "
                "2 anos ou mais)"
            ),
            nota=(
                "Parcela dos desocupados que procura trabalho há 2 anos ou mais; o IBGE "
                "publica o tempo de procura por trimestre civil, não móvel."
            ),
        ),
    ]

    ref = desocupacao[-1][0]
    linhas = [
        _linha("Desocupação", desocupacao, "%", referencia=ref),
        _linha("Desocupação e subocupação por horas", sub_horas, "%", referencia=ref),
        _linha("Desocupação e força de trabalho potencial", sub_potencial, "%", referencia=ref),
        _linha("Subutilização (taxa composta)", subutilizacao, "%", referencia=ref),
        _linha("Participação na força de trabalho", participacao, "%", referencia=ref),
        _linha("Nível de ocupação", nivel, "%", referencia=ref),
        _linha("Informalidade", informalidade, "%", referencia=ref),
        _linha("Desalentados", desalento, "%", referencia=ref),
        _linha("Desalentados", desalentados, "milhões", referencia=ref, casas=2),
        _linha("Ocupados", ocupados, "milhões", referencia=ref),
        _linha("Desocupados", desocupados, "milhões", referencia=ref),
        _linha(
            "Procuram trabalho há 2 anos ou mais",
            procura_longa,
            "% dos desocupados",
            referencia=ref,
            periodicidade="T",
        ),
    ]
    tabela = Tabela(
        id="trabalho-detalhe",
        titulo="Mercado de trabalho, em detalhe",
        subtitulo=f"PNAD Contínua, trimestre móvel até {periodo(ref, 'M')}",
        colunas=[f"Trimestre até {periodo(ref, 'M')}", "Três meses antes", "Um ano antes"],
        linhas=linhas,
        fonte=(f"{PNAD} (SIDRA 6381, 6439, 6440, 6441, 5944, 6379, 8513, 6807, 6438, 6318 e 1616)"),
        nota=(
            "Taxas em % da força de trabalho, salvo: participação e nível de ocupação sobre a "
            "população de 14 anos ou mais; informalidade sobre os ocupados; desalentados sobre "
            "a força de trabalho mais os desalentados. O tempo de procura sai por trimestre "
            "civil: nas colunas, o trimestre anterior e o do ano anterior."
        ),
    )

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
        tabelas=[tabela],
        gerado_em=ctx.agora(),
    )
