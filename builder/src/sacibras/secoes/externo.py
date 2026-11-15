"""Setor externo: comércio, conta corrente, investimento direto, reservas e câmbio."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from sacibras import contas
from sacibras.catalogo import SGS
from sacibras.fontes import comexstat
from sacibras.fontes.comexstat import Item
from sacibras.schema import Cartao, Grafico, LinhaRef, LinhaTabela, Secao, Tabela
from sacibras.secoes.base import MESES, Contexto, br, cartao, grafico, periodo, serie
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


# ---------------------------------------------------------------- serviços em partes
# (chave do catálogo, nome de todo dia). As treze somam o saldo de serviços (BP_SERVICOS); as
# seis primeiras são as que mais pesam (de 2023 a 2026, cada uma passa de US$ 3 bi em 12 meses).
SERVICOS: list[tuple[str, str]] = [
    ("BP_SERV_TRANSPORTES", "Transportes (fretes e passagens)"),
    ("BP_SERV_ALUGUEL", "Aluguel de equipamentos"),
    ("BP_SERV_TELECOM", "Telecomunicação e informática"),
    ("BP_SERV_VIAGENS", "Viagens"),
    ("BP_SERV_PROPRIEDADE", "Marcas, patentes e direitos autorais"),
    ("BP_SERV_NEGOCIOS", "Serviços técnicos e de negócios"),
    ("BP_SERV_FINANCEIROS", "Serviços financeiros"),
    ("BP_SERV_SEGUROS", "Seguros"),
    ("BP_SERV_GOVERNO", "Serviços de governo (embaixadas)"),
    ("BP_SERV_CULTURAIS", "Culturais, pessoais e de lazer"),
    ("BP_SERV_MANUTENCAO", "Manutenção e reparo"),
    ("BP_SERV_CONSTRUCAO", "Construção"),
    ("BP_SERV_MANUFATURA", "Industrialização por encomenda"),
]
SERVICOS_NO_GRAFICO = 6


def tabela_servicos(
    partes: list[tuple[str, list[Ponto]]], total: list[Ponto], fonte: str
) -> Tabela:
    """Cada parte dos serviços (rótulo, soma de 12 meses em US$ bi) no último mês e 12 meses
    antes, da que mais tira dólares do país à que mais traz, e o total, que fecha a coluna."""
    quando = min(min(p[-1][0] for _, p in partes), total[-1][0])
    antes = date(quando.year - 1, quando.month, 1)

    def linha(rotulo: str, pontos: list[Ponto]) -> LinhaTabela:
        mapa = dict(pontos)
        return LinhaTabela(rotulo=rotulo, valores=[mapa.get(quando), mapa.get(antes)], unidade="")

    ordem = sorted(partes, key=lambda x: dict(x[1]).get(quando, 0.0))
    agora_txt, antes_txt = periodo(quando, "M"), periodo(antes, "M")
    return Tabela(
        id="servicos-partes",
        titulo="Serviços com o exterior, parte a parte",
        subtitulo=f"Saldo em 12 meses até {agora_txt} e até {antes_txt}; negativo é déficit",
        colunas=[f"Até {agora_txt} (US$ bi)", f"Até {antes_txt} (US$ bi)"],
        linhas=[linha(r, p) for r, p in ordem] + [linha("Serviços, total", total)],
        fonte=fonte,
        nota=(
            "Receita menos despesa de cada tipo de serviço no balanço de pagamentos (BPM6), "
            "somas de 12 meses feitas por nós. Aluguel de equipamentos inclui o de "
            "plataformas e navios de petróleo; transportes, o frete das importações e as "
            "passagens; viagens, o que brasileiros gastam fora menos o que estrangeiros "
            "gastam aqui."
        ),
    )


# ---------------------------------------------------------------- comércio por setor e produto
FONTE_COMEX = f"{comexstat.FONTE}, valores em US$ FOB"
NOTA_FOB = (
    "Valores FOB: o preço da mercadoria embarcada, sem frete nem seguro. O Comex Stat registra "
    "a mercadoria quando passa pela alfândega; o balanço de pagamentos do Banco Central (o "
    "saldo das outras partes) segue outro critério, e os totais não batem exatamente."
)


def _faixa(mes: int, ano: int) -> str:
    """'jan–out/2026'."""
    return f"jan–{MESES[mes - 1]}/{ano}"


def _pct(parte: float, total: float) -> float:
    return round(parte / total * 100, 1) if total else 0.0


def tabela_ranking(
    id: str,
    titulo: str,
    fechado: dict[Item, float],
    ano_fechado: int,
    *,
    nome: Callable[[Item], str],
    demais: str,
    fonte: str,
    nota: str,
    acumulado: tuple[dict[Item, float], dict[Item, float], int, int] | None = None,
    n: int = 10,
) -> Tabela:
    """Os `n` maiores do ano fechado, o resto somado e o total, que fecha a coluna.

    Com `acumulado` (este ano e o passado, de janeiro ao mesmo mês; o mês e o ano de agora),
    duas colunas a mais: quanto vai no ano e quanto mudou contra o mesmo período do ano
    passado."""
    total = sum(fechado.values())
    agora, antes = (acumulado[0], acumulado[1]) if acumulado else ({}, {})
    todos = set(fechado) | set(agora) | set(antes)
    maiores = sorted(fechado, key=lambda i: -fechado[i])[:n]

    def linha(rotulo: str, itens: list[Item] | set[Item]) -> LinhaTabela:
        v = sum(fechado.get(i, 0.0) for i in itens)
        valores: list[float | None] = [round(v / 1e9, 1), _pct(v, total)]
        if acumulado:
            a = sum(agora.get(i, 0.0) for i in itens)
            b = sum(antes.get(i, 0.0) for i in itens)
            valores += [round(a / 1e9, 1), round((a / b - 1) * 100, 1) if b > 0 else None]
        return LinhaTabela(rotulo=rotulo, valores=valores, unidade="", casas=1)

    linhas = [linha(nome(i), [i]) for i in maiores]
    if todos - set(maiores):
        linhas.append(linha(demais, todos - set(maiores)))
    linhas.append(linha("Total", todos))
    colunas = [f"{ano_fechado} (US$ bi)", f"% em {ano_fechado}"]
    subtitulo = f"{ano_fechado}, do maior ao menor"
    if acumulado:
        _, _, mes, ano = acumulado
        colunas += [f"{_faixa(mes, ano)} (US$ bi)", f"Contra {_faixa(mes, ano - 1)} (%)"]
        subtitulo += f"; e {ano} até {MESES[mes - 1]}"
    return Tabela(
        id=id,
        titulo=titulo,
        subtitulo=subtitulo,
        colunas=colunas,
        linhas=linhas,
        fonte=fonte,
        nota=nota,
    )


def tabela_parceiros(
    exportacoes: dict[Item, float], importacoes: dict[Item, float], ano: int, n: int = 10
) -> Tabela:
    """Os `n` países com mais comércio (exportação + importação) e o saldo com cada um."""
    paises = set(exportacoes) | set(importacoes)
    total_x, total_m = sum(exportacoes.values()), sum(importacoes.values())

    def corrente(i: Item) -> float:
        return exportacoes.get(i, 0.0) + importacoes.get(i, 0.0)

    maiores = sorted(paises, key=lambda i: -corrente(i))[:n]

    def linha(rotulo: str, itens: list[Item] | set[Item]) -> LinhaTabela:
        x = sum(exportacoes.get(i, 0.0) for i in itens)
        m = sum(importacoes.get(i, 0.0) for i in itens)
        return LinhaTabela(
            rotulo=rotulo,
            valores=[
                round(x / 1e9, 1),
                _pct(x, total_x),
                round(m / 1e9, 1),
                _pct(m, total_m),
                round((x - m) / 1e9, 1),
            ],
            unidade="",
            casas=1,
        )

    linhas = [linha(i.nome, [i]) for i in maiores]
    linhas.append(linha("Demais países", paises - set(maiores)))
    linhas.append(linha("Total", paises))
    return Tabela(
        id="parceiros",
        titulo="Com quem o Brasil mais negocia",
        subtitulo=f"{ano}, pela soma do que vende e do que compra de cada país",
        colunas=[
            "Vendeu (US$ bi)",
            "% das vendas",
            "Comprou (US$ bi)",
            "% das compras",
            "Saldo (US$ bi)",
        ],
        linhas=linhas,
        fonte=FONTE_COMEX,
        nota=(
            "Saldo positivo: o Brasil vendeu ao país mais do que comprou dele. O país de "
            "destino é o declarado no embarque; o de origem, o de onde a mercadoria veio. "
            + NOTA_FOB
        ),
    )


def composicao(sitc: comexstat.Valores) -> dict[str, list[Ponto]]:
    """A parte de cada grupo da UNCTAD nas exportações, ano a ano, em %."""
    por_ano: dict[int, dict[str, float]] = {}
    for item, anos in sitc.items():
        grupo = comexstat.grupo_unctad(item.codigo)
        for ano, v in anos.items():
            por_ano.setdefault(ano, {}).setdefault(grupo, 0.0)
            por_ano[ano][grupo] += v
    saida: dict[str, list[Ponto]] = {g: [] for g, _ in comexstat.GRUPOS_UNCTAD}
    for ano in sorted(por_ano):
        total = sum(por_ano[ano].values())
        for g, _ in comexstat.GRUPOS_UNCTAD:
            saida[g].append((date(ano, 1, 1), por_ano[ano].get(g, 0.0) / total * 100))
    return saida


def importacoes_por_uso(valores: comexstat.Valores, codigo: str) -> list[Ponto]:
    """Os US$ bilhões de uma categoria de uso (CGCE nível 1) em cada ano."""
    anos = next((a for item, a in valores.items() if item.codigo == codigo), {})
    return [(date(a, 1, 1), v / 1e9) for a, v in sorted(anos.items())]


def participacao(valores: comexstat.Valores, nome: str) -> list[Ponto]:
    """A parte de um item (um país, um bloco) no total de cada ano, em %."""
    totais: dict[int, float] = {}
    for anos in valores.values():
        for ano, v in anos.items():
            totais[ano] = totais.get(ano, 0.0) + v
    alvo = next((anos for item, anos in valores.items() if item.nome == nome), {})
    return [(date(a, 1, 1), alvo.get(a, 0.0) / totais[a] * 100) for a in sorted(totais)]


Pecas = tuple[list[Cartao], list[Grafico], list[Tabela], str]


def comercio_detalhado(ctx: Contexto) -> Pecas:
    """Setores, produtos e parceiros do Comex Stat."""
    ultimo = comexstat.ultimo_mes()
    fechado = ultimo.year if ultimo.month == 12 else ultimo.year - 1
    mes = ultimo.month

    def consulta(
        fluxo: comexstat.Fluxo, detalhe: str
    ) -> tuple[dict[Item, float], tuple[dict[Item, float], dict[Item, float], int, int] | None]:
        ano = comexstat.no_ano(comexstat.consultar(fluxo, detalhe, fechado, fechado), fechado)
        if ultimo.month == 12:
            return ano, None
        corrente = comexstat.consultar(fluxo, detalhe, ultimo.year - 1, ultimo.year, mes)
        return ano, (
            comexstat.no_ano(corrente, ultimo.year),
            comexstat.no_ano(corrente, ultimo.year - 1),
            mes,
            ultimo.year,
        )

    nota_setor = (
        "Setor pela divisão da ISIC, a classificação de atividades da ONU (a mesma base da "
        "CNAE): o setor é o que produz a mercadoria, não a empresa que exporta. A soja em grão "
        "conta na agropecuária; o farelo, a carne e o açúcar, na fabricação de alimentos. "
        + NOTA_FOB
    )
    tabelas: list[Tabela] = []
    produtos: dict[str, dict[Item, float]] = {}
    fluxos: list[tuple[comexstat.Fluxo, str]] = [("export", "exporta"), ("import", "importa")]
    for fluxo, palavra in fluxos:
        ano, acumulado = consulta(fluxo, "ISICDivision")
        tabelas.append(
            tabela_ranking(
                f"{fluxo}acoes-setores",
                f"O que o Brasil {palavra}, por setor",
                ano,
                fechado,
                nome=comexstat.setor_curto,
                demais="Demais setores",
                fonte=FONTE_COMEX,
                nota=nota_setor,
                acumulado=acumulado,
            )
        )
        ano, acumulado = consulta(fluxo, "heading")
        produtos[fluxo] = ano
        tabelas.append(
            tabela_ranking(
                f"{fluxo}acoes-produtos",
                f"Os produtos que o Brasil mais {palavra}",
                ano,
                fechado,
                nome=comexstat.nome_curto,
                demais="Demais produtos",
                fonte=FONTE_COMEX,
                nota=(
                    "Produto pela posição do Sistema Harmonizado (os quatro primeiros dígitos "
                    "da NCM), com nome de todo dia no lugar do oficial. " + NOTA_FOB
                ),
                acumulado=acumulado,
            )
        )
    # As tabelas de setor e de produto em ordem: setores (vende, compra), produtos (vende, compra).
    tabelas = [tabelas[0], tabelas[2], tabelas[1], tabelas[3]]

    # ---- as importações por categoria de uso (CGCE): máquinas, insumos, consumo, combustível
    graficos: list[Grafico] = []
    try:
        ano, acumulado = consulta("import", "BECLevel1")
        nota_uso = (
            "Categoria de uso pela CGCE, a classificação do IBGE e do MDIC que separa o que "
            "vira investimento (bens de capital), o que entra na produção (intermediários), o "
            "que vai às famílias (consumo) e os combustíveis. " + NOTA_FOB
        )
        tabelas.append(
            tabela_ranking(
                "importacoes-uso",
                "O que o Brasil importa, por uso",
                ano,
                fechado,
                nome=comexstat.uso_curto,
                demais="Demais",
                fonte=FONTE_COMEX,
                nota=nota_uso,
                acumulado=acumulado,
                n=5,
            )
        )
        historia = comexstat.consultar("import", "BECLevel1", comexstat.PRIMEIRO_ANO, fechado)
        graficos.append(
            grafico(
                "importacoes-uso",
                "Importações por uso",
                [
                    serie(
                        f"uso-{codigo}",
                        nome,
                        importacoes_por_uso(historia, codigo),
                        casas=1,
                    )
                    for codigo, nome in comexstat.USOS.items()
                    if codigo != "9"
                ],
                tipo="empilhado",
                unidade="US$ bilhões por ano",
                casas=1,
                periodicidade="A",
                fonte=FONTE_COMEX,
                nota=(
                    "Bens de capital sobem quando as empresas investem; intermediários, com a "
                    "produção; combustíveis, com o preço do petróleo. Pela CGCE, a "
                    "classificação por uso do IBGE; valores FOB, sem frete nem seguro."
                ),
                largura="inteira",
            )
        )
    except Exception as erro:
        print(f"    externo: importações por uso (CGCE) ficaram de fora: {str(erro)[:160]}")

    # ---- o que pesa nas exportações, desde 1997
    sitc = comexstat.consultar("export", "SITCGroup", comexstat.PRIMEIRO_ANO, fechado)
    grupos = composicao(sitc)
    commodities = [
        (d, sum(grupos[g][k][1] for g in comexstat.COMMODITIES))
        for k, (d, _) in enumerate(grupos["alimentos"])
    ]
    nomes_grupo = dict(comexstat.GRUPOS_UNCTAD)
    graficos.insert(
        0,
        grafico(
            "exportacoes-composicao",
            "Do que são feitas as exportações",
            [serie(g, nomes_grupo[g], grupos[g], casas=1) for g, _ in comexstat.GRUPOS_UNCTAD],
            tipo="empilhado",
            unidade="% das exportações",
            casas=1,
            periodicidade="A",
            fonte=f"{FONTE_COMEX}; grupos da UNCTAD (ONU)",
            nota=(
                "Grupos de produtos da UNCTAD, a agência da ONU para comércio: commodities são "
                "alimentos, combustíveis, minérios e metais e matérias-primas agrícolas, "
                "processados ou não (o farelo e a carne contam como alimento; o aço, como "
                "manufaturado). Classificação aplicada por nós aos grupos da CUCI do Comex Stat."
            ),
            largura="inteira",
        ),
    )
    # ---- para onde vendem
    paises_x = comexstat.consultar("export", "country", comexstat.PRIMEIRO_ANO, fechado)
    blocos_x = comexstat.consultar("export", "economicBlock", comexstat.PRIMEIRO_ANO, fechado)
    destinos = {
        "china": ("China", participacao(paises_x, "China")),
        "eua": ("Estados Unidos", participacao(paises_x, "Estados Unidos")),
        "ue": ("União Europeia", participacao(blocos_x, "União Europeia - UE")),
        "argentina": ("Argentina", participacao(paises_x, "Argentina")),
    }
    graficos.append(
        grafico(
            "exportacoes-destinos",
            "Para onde vão as exportações",
            [serie(k, nome, pontos, casas=1) for k, (nome, pontos) in destinos.items()],
            unidade="% das exportações",
            casas=1,
            periodicidade="A",
            fonte=FONTE_COMEX,
            nota=(
                "A União Europeia na composição que o Comex Stat usa para toda a série. "
                "Valores FOB, pelo país de destino declarado no embarque."
            ),
        )
    )
    paises_m = comexstat.consultar("import", "country", fechado, fechado)
    tabelas.append(
        tabela_parceiros(
            comexstat.no_ano(paises_x, fechado), comexstat.no_ano(paises_m, fechado), fechado
        )
    )

    # ---- os cartões, do ano fechado
    total_x = sum(produtos["export"].values())
    ordem = sorted(produtos["export"], key=lambda i: -produtos["export"][i])
    primeiro, segundo, terceiro = ordem[:3]
    referencia = date(fechado, 1, 1)
    nome_1 = comexstat.nome_curto(primeiro)
    china, ue = destinos["china"][1], destinos["ue"][1]
    eua = destinos["eua"][1]
    cartoes = [
        cartao(
            "commodities-exportacoes",
            "Commodities nas exportações",
            commodities,
            unidade="% do total",
            periodicidade="A",
            casas=1,
            detalhe=f"em {commodities[0][0].year}: {br(commodities[0][1])} %",
            fonte=f"{FONTE_COMEX}; grupos da UNCTAD",
            procedencia="calculado",
            secao="externo",
            mini=40,
        ),
        Cartao(
            id="maior-exportacao",
            rotulo="Maior exportação",
            valor=_pct(produtos["export"][primeiro], total_x),
            unidade="% das exportações",
            casas=1,
            texto=nome_1,
            referencia=referencia,
            periodicidade="A",
            detalhe=(
                f"{br(_pct(produtos['export'][primeiro], total_x))} %; depois, "
                f"{comexstat.nome_curto(segundo).lower()} e "
                f"{comexstat.nome_curto(terceiro).lower()}"
            ),
            fonte=FONTE_COMEX,
            secao="externo",
        ),
        cartao(
            "china-exportacoes",
            "China nas exportações",
            china,
            unidade="% do total",
            periodicidade="A",
            casas=1,
            detalhe=f"EUA: {br(eua[-1][1])} %; União Europeia: {br(ue[-1][1])} %",
            fonte=FONTE_COMEX,
            secao="externo",
            mini=40,
        ),
    ]
    frase = (
        f"Em {fechado}, commodities foram {br(commodities[-1][1], 0)} % das exportações; o "
        f"produto mais vendido foi {nome_1.lower()} ({br(cartoes[1].valor)} %), e a China "
        f"comprou {br(china[-1][1], 0)} % do total."
    )
    return cartoes, graficos, tabelas, frase


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
    # ---- os serviços em partes (viagens, fretes, aluguel de equipamentos…)
    try:
        servicos = [(nome, em_12m_bi(ctx.sgs(chave))) for chave, nome in SERVICOS]
        fonte_servicos = ctx.fonte_sgs(*(c for c, _ in SERVICOS), "BP_SERVICOS")
        graficos.append(
            grafico(
                "servicos-partes",
                "Serviços: onde o país gasta e ganha dólares",
                [
                    serie(
                        chave.removeprefix("BP_SERV_").lower(), nome, pontos, desde=inicio, casas=1
                    )
                    for (chave, _), (nome, pontos) in zip(
                        SERVICOS[:SERVICOS_NO_GRAFICO], servicos, strict=False
                    )
                ],
                unidade="US$ bilhões, saldo em 12 meses",
                casas=1,
                periodicidade="M",
                janela_anos=10,
                fonte=fonte_servicos,
                nota=(
                    "Receita menos despesa de cada tipo de serviço, em 12 meses; abaixo de zero, "
                    "o país paga mais do que recebe. As seis maiores partes; todas estão na "
                    "tabela."
                ),
            )
        )
        tabelas.append(tabela_servicos(servicos, partes["BP_SERVICOS"][1], fonte=fonte_servicos))
    except Exception as erro:
        print(f"    externo: serviços em partes ficaram de fora: {str(erro)[:160]}")

    try:
        c, g, t, frase = comercio_detalhado(ctx)
        cartoes += c
        graficos += g
        tabelas += t
    except Exception as erro:
        frase = ""
        print(f"    externo: comércio por setor (Comex Stat) ficou de fora: {str(erro)[:160]}")

    sinal = "déficit" if tc_pib[-1][1] < 0 else "superávit"
    resumo = (
        f"A conta corrente tem {sinal} de {br(abs(tc_pib[-1][1]), 2)} % do PIB em 12 meses até "
        f"{periodo(tc_pib[-1][0], 'M')}; o investimento direto soma {br(idp_pib[-1][1], 2)} % do "
        f"PIB. As reservas estão em US$ {br(reservas[-1][1])} bilhões."
    )
    if frase:
        resumo += " " + frase
    return Secao(
        id="externo",
        titulo="Setor externo",
        resumo=resumo,
        cartoes=cartoes,
        graficos=graficos,
        tabelas=tabelas,
        gerado_em=ctx.agora(),
    )
