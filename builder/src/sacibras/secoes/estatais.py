"""As estatais federais e o caixa da União: o que entra em dividendos, o que sai em subvenção
e em capital, e o resultado das que o Banco Central conta no setor público (Caio, 19/11/2026:
*"adicione uma pergunta de quanto as estatais dão lucro ou prejuízo aos cofres públicos"*).

Três fontes, três recortes, ditos na tela:
- o Resultado do Tesouro (RTN) dá, mês a mês, os dividendos que entram no caixa da União,
  empresa por empresa, e o aumento de capital das não dependentes;
- o Relatório Agregado da Sest (anual, lido à mão em `relatorios.py`) dá o lucro de todas, os
  dividendos pagos à União e a subvenção às dependentes;
- o Banco Central dá o resultado primário das estatais que ele conta no setor público (sem os
  bancos, a Petrobras e a Eletrobras).

A conta do ano (dividendos menos subvenção e aporte) é a que a própria Sest faz; aqui ela
vai ano a ano. Não é o lucro das empresas nem o valor delas: é o que passou pelo caixa.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from datetime import date

from sacibras import contas, relatorios
from sacibras.fontes.sest import FONTE as FONTE_SEST
from sacibras.fontes.sest import EstatalNoAno
from sacibras.schema import Cartao, FichaEstatal, Grafico, LinhaTabela, Serie, Tabela
from sacibras.secoes.base import br, cartao, grafico, periodo, serie
from sacibras.tipos import Ponto

Pecas = tuple[list[Cartao], list[Grafico], list[Tabela]]

EMPRESAS = {
    "div_bndes": "BNDES",
    "div_petrobras": "Petrobras",
    "div_bb": "Banco do Brasil",
    "div_caixa": "Caixa",
}
OUTRAS = ("div_bnb", "div_correios", "div_eletrobras", "div_irb", "div_demais")
ANOS_NA_TABELA = 5


def _por_ano(mensal: list[Ponto]) -> dict[int, float]:
    """A soma de cada ano com os doze meses."""
    soma: dict[int, float] = {}
    meses: dict[int, int] = {}
    for d, v in mensal:
        soma[d.year] = soma.get(d.year, 0.0) + v
        meses[d.year] = meses.get(d.year, 0) + 1
    return {ano: v for ano, v in soma.items() if meses[ano] == 12}


def _somar(series: list[list[Ponto]]) -> list[Ponto]:
    por_mes = [dict(s) for s in series]
    meses = set.intersection(*(set(s) for s in por_mes))
    return [(d, sum(s[d] for s in por_mes)) for d in sorted(meses)]


def dividendos(det: dict[str, list[Ponto]], pib: list[Ponto], fonte: str, inicio: date) -> Pecas:
    """Os dividendos que a União recebe, por empresa (RTN, aba 1.2)."""
    total_12 = contas.soma_movel(det["dividendos"], 12)
    quando, valor = total_12[-1]
    pib_q = dict(pib).get(quando)
    em_12 = {nome: dict(contas.soma_movel(det[nome], 12)).get(quando, 0.0) for nome in EMPRESAS}
    maior = max(em_12, key=lambda nome: em_12[nome])
    outras = _somar([det[nome] for nome in OUTRAS])
    cartoes = [
        cartao(
            "dividendos-12m",
            "Dividendos que a União recebeu, 12 meses",
            [(d, v / 1000) for d, v in total_12],
            unidade="R$ bilhões",
            periodicidade="M",
            casas=1,
            detalhe=(
                f"{'' if pib_q is None else br(valor / pib_q * 100, 2) + ' % do PIB; '}"
                f"quem mais pagou: {EMPRESAS[maior]}"
            ),
            fonte=fonte,
            secao="fiscal",
            mini=120,
        )
    ]
    graficos = [
        grafico(
            "dividendos-por-empresa",
            "Dividendos pagos à União, por empresa",
            [
                *(
                    serie(nome, rotulo, contas.em_pct_do_pib(det[nome], pib), desde=inicio)
                    for nome, rotulo in EMPRESAS.items()
                ),
                serie("outras", "Demais", contas.em_pct_do_pib(outras, pib), desde=inicio),
            ],
            unidade="% do PIB, em 12 meses",
            casas=2,
            periodicidade="M",
            janela_anos=15,
            fonte=fonte,
            # A União é dona de todo o BNDES e de toda a Caixa, e de parte da Petrobras e do
            # Banco do Brasil. O dividendo depende do lucro e de quanto a empresa distribui.
            nota=(
                "O que entrou no caixa do Tesouro, pelo mês do pagamento. Na Petrobras e no "
                "Banco do Brasil, a União recebe só a parte dela."
            ),
        )
    ]
    por_ano = {nome: _por_ano(det[nome]) for nome in (*EMPRESAS, "dividendos")}
    anos = sorted(por_ano["dividendos"])[-ANOS_NA_TABELA:]

    def linha(rotulo: str, valores: list[float]) -> LinhaTabela:
        return LinhaTabela(
            rotulo=rotulo, valores=[round(v / 1000, 1) for v in valores], unidade="", casas=1
        )

    linhas = [
        linha(rotulo, [*(por_ano[nome].get(a, 0.0) for a in anos), em_12[nome]])
        for nome, rotulo in EMPRESAS.items()
    ]
    demais = [
        por_ano["dividendos"][a] - sum(por_ano[n].get(a, 0.0) for n in EMPRESAS) for a in anos
    ]
    linhas.append(linha("Demais", [*demais, valor - sum(em_12.values())]))
    linhas.append(linha("Total", [*(por_ano["dividendos"][a] for a in anos), valor]))
    tabela = Tabela(
        id="dividendos-por-empresa",
        titulo="Dividendos e participações recebidos pela União",
        subtitulo="R$ bilhões, valores da época",
        colunas=[*(str(a) for a in anos), f"12 meses até {periodo(quando, 'M')}"],
        linhas=linhas,
        fonte=fonte,
        nota=(
            "Tabela 1.2 do Tesouro, pelo que entrou no caixa. Demais: Eletrobras, Banco do "
            "Nordeste, IRB, Correios e participações menores."
        ),
    )
    return cartoes, graficos, [tabela]


def conta_do_ano() -> Pecas:
    """Dividendos menos subvenção e aporte, ano a ano (Relatório Agregado da Sest)."""
    por_ano = relatorios.ESTATAIS_POR_ANO
    anos = sorted(por_ano)
    ultimo = anos[-1]

    def saldo(ano: int) -> float:
        x = por_ano[ano]
        return x.dividendos_uniao - x.subvencao - x.aporte

    def pontos(valor: object) -> list[Ponto]:
        return [(date(a, 1, 1), valor(a) / 1000) for a in anos]  # type: ignore[operator]

    x = por_ano[ultimo]
    fonte = relatorios.FONTE_ESTATAIS
    cartoes = [
        Cartao(
            id="estatais-saldo",
            rotulo="Dividendos menos o que a União pôs nas estatais",
            valor=round(saldo(ultimo) / 1000, 2),
            unidade="R$ bilhões",
            casas=1,
            referencia=date(ultimo, 1, 1),
            periodicidade="A",
            detalhe=(
                f"recebeu {br(x.dividendos_uniao / 1000)}; pôs "
                f"{br((x.subvencao + x.aporte) / 1000)} em subvenção e capital"
            ),
            fonte=fonte,
            secao="fiscal",
            mini=[(d, round(v, 2)) for d, v in pontos(saldo)],
        ),
        Cartao(
            id="estatais-subvencao",
            rotulo="Subvenção às estatais dependentes",
            valor=round(x.subvencao / 1000, 2),
            unidade="R$ bilhões",
            casas=1,
            referencia=date(ultimo, 1, 1),
            periodicidade="A",
            detalhe=(
                f"{relatorios.ESTATAIS_DEPENDENTES} das {relatorios.ESTATAIS_DIRETAS} estatais; "
                "mais da metade vai a hospitais"
            ),
            fonte=fonte,
            secao="fiscal",
            mini=[(d, round(v, 2)) for d, v in pontos(lambda a: por_ano[a].subvencao)],
        ),
    ]
    desenho = grafico(
        "estatais-conta",
        "O que as estatais pagam à União e o que recebem dela",
        [
            serie(
                "dividendos",
                "Dividendos pagos à União",
                pontos(lambda a: por_ano[a].dividendos_uniao),
            ),
            serie(
                "repasses",
                "Subvenção e capital recebidos",
                pontos(lambda a: por_ano[a].subvencao + por_ano[a].aporte),
            ),
            serie("saldo", "Saldo para a União", pontos(saldo)),
        ],
        tipo="barras",
        unidade="R$ bilhões",
        casas=1,
        periodicidade="A",
        fonte=fonte,
        # Os dividendos vêm de quatro empresas; a subvenção vai às dependentes (hospitais,
        # pesquisa, obras). Todos os números são do anexo I da Sest; o aporte é a soma das
        # empresas na planilha, o mesmo que dá o retorno de 2025 da p. 17 (R$ 13,1 bi). A
        # tabela-resumo da p. 86 traz aporte maior em todos os anos (2025: 3.418,3 contra
        # 1.709,1). O relatório de 2024 não publica retorno (lido em 25/11/2026).
        nota=(
            "Valores da época, sem descontar a inflação. Aporte pela soma das empresas, como "
            "no retorno de 2025 da Sest; o resumo da p. 86 traz um valor maior."
        ),
        manchete=(
            f"Em {ultimo}, a União recebeu R$ {br(x.dividendos_uniao / 1000)} bi e pôs "
            f"R$ {br((x.subvencao + x.aporte) / 1000)} bi: saldo de "
            f"R$ {br(saldo(ultimo) / 1000)} bi."
        ),
    )

    def linha(rotulo: str, valor: object, grupo: str) -> LinhaTabela:
        return LinhaTabela(
            rotulo=rotulo,
            valores=[round(valor(a) / 1000, 1) for a in anos],  # type: ignore[operator]
            unidade="",
            casas=1,
            grupo=grupo,
        )

    def pagos(ano: int) -> float:
        return por_ano[ano].dividendos_uniao

    caixa = "O que passou pelo caixa da União"
    empresas = "O resultado das empresas (não entra no caixa)"
    conta = Tabela(
        id="estatais-conta",
        titulo="As estatais federais e o caixa da União",
        subtitulo="R$ bilhões, valores da época",
        colunas=[str(a) for a in anos],
        linhas=[
            linha(
                "Dividendos e juros sobre capital pagos à União",
                lambda a: por_ano[a].dividendos_uniao,
                caixa,
            ),
            linha("Subvenção às estatais dependentes", lambda a: -por_ano[a].subvencao, caixa),
            linha("Aporte de capital", lambda a: -por_ano[a].aporte, caixa),
            linha("Saldo para a União", saldo, caixa),
            linha("Lucro de todas as estatais somadas", lambda a: por_ano[a].lucro, empresas),
            linha("  só das que tiveram prejuízo", lambda a: por_ano[a].prejuizos, empresas),
        ],
        fonte=fonte,
        # Ficam fora do saldo os impostos que as estatais pagam, o lucro que guardam e o valor
        # das ações. O prejuízo de uma não dependente (os Correios) não sai do Tesouro no ano:
        # vira dívida ou perda de patrimônio da empresa, e pode virar aporte depois.
        nota=(
            "O saldo é a conta do caixa, a mesma da Sest: não é o lucro nem o valor das "
            "empresas. Aporte pela soma das empresas; o resumo da p. 86 traz um valor maior."
        ),
    )
    subvencoes = Tabela(
        id="estatais-subvencoes",
        titulo="Quem recebe a subvenção do Tesouro",
        subtitulo=f"{ultimo}, as {relatorios.ESTATAIS_DEPENDENTES} estatais dependentes",
        colunas=["R$ bilhões", "% do total"],
        linhas=[
            LinhaTabela(
                rotulo=nome,
                valores=[round(v / 1000, 2), round(v / x.subvencao * 100, 1)],
                unidade="",
                casas=1,
            )
            for nome, v in relatorios.SUBVENCOES_2025
        ],
        fonte=fonte.replace("anexo I", "p. 17"),
        nota=(
            "Estatal dependente é a que recebe do orçamento para pagar pessoal e custeio. O "
            "gasto dela já está dentro da despesa da União (boa parte, na saúde e na "
            "educação): não é uma conta a mais."
        ),
    )
    lucros = Tabela(
        id="estatais-lucro",
        titulo="O lucro ou o prejuízo das maiores estatais",
        subtitulo="R$ bilhões",
        colunas=[str(ultimo - 1), str(ultimo)],
        linhas=[
            LinhaTabela(
                rotulo=nome, valores=[round(a / 1000, 1), round(b / 1000, 1)], unidade="", casas=1
            )
            for nome, a, b in relatorios.LUCRO_DOS_MAIORES
        ],
        fonte=fonte,
        nota=(
            "Resultado líquido do grupo inteiro. Na Petrobras e no Banco do Brasil, a União "
            "é dona de uma parte: o resto do lucro é dos outros acionistas."
        ),
    )
    return cartoes, [desenho], [conta, subvencoes, lucros]


def primario(
    federais: list[Ponto],
    estaduais: list[Ponto],
    municipais: list[Ponto],
    federais_mes: list[Ponto],
    fonte: str,
    inicio: date,
) -> Pecas:
    """O resultado primário das estatais que o BC conta no setor público. As séries vêm como
    necessidade de financiamento (positivo é déficit): aqui o sinal é trocado."""
    em_12 = [(d, -v / 1000) for d, v in contas.soma_movel(federais_mes, 12)]
    estado = "superávit" if em_12[-1][1] >= 0 else "déficit"
    cartoes = [
        cartao(
            "estatais-primario",
            "Resultado das estatais federais, 12 meses",
            em_12,
            unidade="R$ bilhões",
            periodicidade="M",
            casas=1,
            detalhe=f"{estado}; sem os bancos, a Petrobras e a Eletrobras",
            fonte=fonte,
            secao="fiscal",
            mini=120,
        )
    ]
    graficos = [
        grafico(
            "estatais-primario",
            "Primário das estatais, por esfera",
            [
                serie("federais", "Federais", contas.escalar(federais, -1), desde=inicio),
                serie("estaduais", "Estaduais", contas.escalar(estaduais, -1), desde=inicio),
                serie("municipais", "Municipais", contas.escalar(municipais, -1), desde=inicio),
            ],
            unidade="% do PIB, em 12 meses",
            casas=2,
            periodicidade="M",
            janela_anos=15,
            fonte=fonte,
            # Déficit quer dizer que as empresas gastaram e investiram mais do que arrecadaram,
            # e isso entra no resultado do setor público. Das federais ficam os Correios, etc.
            nota=(
                "Acima de zero, superávit: a variação da dívida líquida das empresas, antes dos "
                "juros. Sem os bancos públicos, a Petrobras e a Eletrobras."
            ),
        )
    ]
    return cartoes, graficos, []


# ------------------------------------------------------------------ uma estatal por dentro
#
# Caio, 25/11/2026: "abra por estatal um dashboard com informações mais relevantes,
# principalmente histórico de performance, receita ou prejuízo e outras métricas relevantes
# para analisar empresas". Tudo do Anexo I da Sest (`fontes/sest.py`), em reais da época. A
# margem, o retorno sobre o patrimônio, o saldo com a União e o gasto por empregado são
# divisões e somas dos números dela. Fica de fora o que a Sest não traz: dívida líquida,
# Ebitda, caixa e o valor de mercado (este vem da bolsa, e a B3 saiu do projeto).

# O nome de todo dia, onde a sigla da Sest não diz nada a quem visita.
NOMES = {
    "PETROBRAS (Grupo)": "Petrobras",
    "BB (Grupo)": "Banco do Brasil",
    "BNDES (Grupo)": "BNDES",
    "CAIXA (Grupo)": "Caixa",
    "ENBPar (Grupo)": "ENBPar (Itaipu e Eletronuclear)",
    "ECT": "Correios",
    "BASA": "Banco da Amazônia",
    "BNB": "Banco do Nordeste",
    "EBSERH": "Ebserh (hospitais universitários)",
    "CONCEIÇÃO": "Grupo Hospitalar Conceição",
    "HCPA": "Hospital de Clínicas de Porto Alegre",
    "CMB": "Casa da Moeda",
    "CPRM": "Serviço Geológico (CPRM)",
    "APS": "Porto de Santos (APS)",
    "CDRJ": "Portos do Rio (CDRJ)",
    "CDC": "Portos do Ceará (CDC)",
    "CDP": "Portos do Pará (CDP)",
    "CODEBA": "Portos da Bahia (Codeba)",
    "CODERN": "Portos do RN (Codern)",
    "CODEVASF": "Codevasf",
    "CONAB": "Conab",
    "EMBRAPA": "Embrapa",
    "INFRAERO": "Infraero",
    "SERPRO": "Serpro",
    "DATAPREV": "Dataprev",
    "TELEBRAS": "Telebras",
    "TRENSURB": "Trensurb",
    "FINEP": "Finep",
    "HEMOBRÁS": "Hemobrás",
    "IMBEL": "Imbel",
    "NUCLEP": "Nuclep",
    "AMAZUL": "Amazul",
    "CEITEC": "Ceitec",
    "CEAGESP": "Ceagesp",
    "CEASAMINAS": "CeasaMinas",
    "EMGEA": "Emgea",
    "EMGEPRON": "Emgepron",
}
PRIMEIRA = "Petrobras"


def _id(sigla: str) -> str:
    sem = unicodedata.normalize("NFKD", sigla).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", sem.replace("(grupo)", "")).strip("-")


def _receita(x: EstatalNoAno) -> float | None:
    """Faturamento; nos bancos, a Sest põe a receita na intermediação e nas tarifas."""
    soma = sum(x[c] or 0.0 for c in ("faturamento", "intermediacao", "tarifas"))
    return soma or None


def _razao(a: float | None, b: float | None, positivo: bool = False) -> float | None:
    if a is None or not b or (positivo and b <= 0):
        return None
    return a / b * 100


def _saldo(x: EstatalNoAno) -> float:
    return (x["dividendos_uniao"] or 0.0) - (x["subvencao"] or 0.0) - (x["afac"] or 0.0)


def _por_empregado(x: EstatalNoAno) -> float | None:
    p, n = x["pessoal"], x["empregados"]
    return p / n / 1000 if p and n else None


def ficha(anos: list[EstatalNoAno], todas_do_ano: list[EstatalNoAno]) -> FichaEstatal:
    """A ficha de uma estatal; `anos` em ordem, `todas_do_ano` para a posição no ranking."""
    u = anos[-1]
    nome = NOMES.get(u.sigla, u.sigla.replace(" (Grupo)", ""))
    ident = _id(u.sigla)
    datas = [date(x.ano, 1, 1) for x in anos]
    tamanho = max(abs(v or 0.0) for x in anos for v in (x["ativo"], _receita(x), x["subvencao"]))
    if tamanho >= 2e9:
        escala, unidade, curta = 1e9, "R$ bilhões", "R$ bi"
    else:
        escala, unidade, curta = 1e6, "R$ milhões", "R$ mi"

    def em(v: float | None) -> float | None:
        return None if v is None else round(v / escala, 2)

    def pontos(valor: Callable[[EstatalNoAno], float | None]) -> list[tuple[date, float | None]]:
        return [(d, valor(x)) for d, x in zip(datas, anos, strict=True)]

    def s(id_: str, rotulo: str, valor: Callable[[EstatalNoAno], float | None]) -> Serie:
        return Serie(id=id_, nome=rotulo, pontos=pontos(valor))

    def reais(v: float) -> str:
        return f"{curta.replace('R$ ', 'R$ ' + br(v / escala) + ' ')}"

    fonte = f"{FONTE_SEST}, {anos[0].ano} a {u.ano}"
    ultimo = date(u.ano, 1, 1)
    banco = (u["intermediacao"] or 0.0) > 0

    # --- os quatro números
    lucro, receita = u["lucro"] or 0.0, _receita(u)
    posicao = 1 + sum(1 for o in todas_do_ano if (o["lucro"] or 0.0) > lucro)
    margem = _razao(lucro, receita)
    cartoes = [
        Cartao(
            id=f"estatal-{ident}-lucro",
            rotulo="Lucro" if lucro >= 0 else "Prejuízo",
            valor=round(lucro / escala, 2),
            unidade=unidade,
            referencia=ultimo,
            periodicidade="A",
            detalhe=f"{posicao}º lugar em lucro entre {len(todas_do_ano)} estatais",
            anterior=em(anos[-2]["lucro"]) if len(anos) > 1 else None,
            anterior_rotulo=str(anos[-2].ano) if len(anos) > 1 else "",
            fonte=fonte,
            secao="fiscal",
            mini=[
                (d, round((x["lucro"] or 0.0) / escala, 2))
                for d, x in zip(datas, anos, strict=True)
            ],
        )
    ]
    if receita:
        antes = _receita(anos[-2]) if len(anos) > 1 else None
        detalhe = "" if margem is None or u.dependente else f"margem de {br(margem)} %"
        if antes:
            detalhe += f"{'; ' if detalhe else ''}{br((receita / antes - 1) * 100)} % em um ano"
        cartoes.append(
            Cartao(
                id=f"estatal-{ident}-receita",
                rotulo="Receita própria" if u.dependente else "Receita",
                valor=round(receita / escala, 2),
                unidade=unidade,
                referencia=ultimo,
                periodicidade="A",
                detalhe=detalhe,
                fonte=fonte,
                secao="fiscal",
                mini=[
                    (d, round((_receita(x) or 0.0) / escala, 2))
                    for d, x in zip(datas, anos, strict=True)
                ],
            )
        )
    if u.dependente:
        sub = u["subvencao"] or 0.0
        cartoes.append(
            Cartao(
                id=f"estatal-{ident}-subvencao",
                rotulo="Subvenção do Tesouro",
                valor=round(sub / escala, 2),
                unidade=unidade,
                referencia=ultimo,
                periodicidade="A",
                detalhe=(
                    f"{br(sub / receita, 0)} vezes a receita própria"
                    if receita and sub > receita
                    else "para pessoal e custeio"
                ),
                fonte=fonte,
                secao="fiscal",
                mini=[
                    (d, round((x["subvencao"] or 0.0) / escala, 2))
                    for d, x in zip(datas, anos, strict=True)
                ],
            )
        )
    else:
        roe = _razao(lucro, u["patrimonio"], positivo=True)
        if roe is not None:
            validos = [r for x in anos if (r := _razao(x["lucro"], x["patrimonio"], True))]
            cartoes.append(
                Cartao(
                    id=f"estatal-{ident}-roe",
                    rotulo="Retorno sobre o patrimônio",
                    valor=round(roe, 2),
                    unidade="%",
                    referencia=ultimo,
                    periodicidade="A",
                    detalhe=f"média desde {anos[0].ano}: {br(sum(validos) / len(validos))} %",
                    fonte=fonte,
                    secao="fiscal",
                    mini=[
                        (d, round(r, 2))
                        for d, r in pontos(lambda x: _razao(x["lucro"], x["patrimonio"], True))
                        if r is not None
                    ],
                )
            )
        else:
            cartoes.append(
                Cartao(
                    id=f"estatal-{ident}-patrimonio",
                    rotulo="Patrimônio líquido",
                    valor=round((u["patrimonio"] or 0.0) / escala, 2),
                    unidade=unidade,
                    referencia=ultimo,
                    periodicidade="A",
                    detalhe="negativo: deve mais do que tem",
                    fonte=fonte,
                    secao="fiscal",
                    mini=[
                        (d, round((x["patrimonio"] or 0.0) / escala, 2))
                        for d, x in zip(datas, anos, strict=True)
                    ],
                )
            )
    saldo = _saldo(u)
    cartoes.append(
        Cartao(
            id=f"estatal-{ident}-saldo",
            texto="" if saldo else "zero",
            rotulo="Saldo com a União",
            valor=round(saldo / escala, 2),
            unidade=unidade,
            referencia=ultimo,
            periodicidade="A",
            detalhe=(
                f"pagou {reais(u['dividendos_uniao'] or 0.0)}; recebeu "
                f"{reais((u['subvencao'] or 0.0) + (u['afac'] or 0.0))}"
                if (u["dividendos_uniao"] or u["subvencao"] or u["afac"])
                else "nada pago nem recebido no ano"
            ),
            fonte=fonte,
            secao="fiscal",
            mini=[(d, round(_saldo(x) / escala, 2)) for d, x in zip(datas, anos, strict=True)],
        )
    )

    # --- o gráfico principal e os outros atrás da lista "Gráfico"
    def g(id_: str, opcao: str, titulo: str, series: list[Serie], **extra: object) -> Grafico:
        return grafico(
            f"estatal-{ident}-{id_}",
            titulo,
            series,
            unidade=str(extra.pop("unidade", unidade)),
            periodicidade="A",
            fonte=fonte,
            # Barras só com uma série: com duas, a segunda vira linha e fica fora do lugar.
            tipo=extra.pop("tipo", "barras" if len(series) == 1 else "linha"),
            casas=extra.pop("casas", 1),
            rotulo_opcao=opcao,
            largura="inteira",
            **extra,
        )

    def ok(series: list[Serie]) -> bool:
        return any(v for x in series for _, v in x.pontos)

    principal = g(
        "resultado",
        "Receita e lucro",
        f"{nome}: receita e lucro",
        [
            s("receita", "Receita", lambda x: em(_receita(x))),
            s("lucro", "Lucro ou prejuízo", lambda x: em(x["lucro"])),
        ],
        nota=(
            "Nos bancos, a receita é a de juros mais as tarifas. Grupo consolidado onde a "
            'Sest diz "Grupo"; valores da época.'
            if banco
            else 'Valores da época; nas que têm "Grupo" no nome, o grupo consolidado.'
        ),
        manchete=f"{_resultado(u, reais)}"
        + (
            f"; {_resultado(anos[-2], reais)[0].lower()}{_resultado(anos[-2], reais)[1:]}."
            if len(anos) > 1
            else "."
        ),
    )
    outros: list[Grafico] = []
    rentab = [
        s("margem", "Margem líquida", lambda x: _round(_razao(x["lucro"], _receita(x)))),
        s(
            "roe",
            "Retorno sobre o patrimônio",
            lambda x: _round(_razao(x["lucro"], x["patrimonio"], True)),
        ),
    ]
    if ok(rentab):
        outros.append(
            g(
                "rentabilidade",
                "Margem e retorno",
                f"{nome}: margem e retorno sobre o patrimônio",
                rentab,
                unidade="%",
                tipo="linha",
                nota="Lucro sobre a receita e sobre o patrimônio do ano. Sem retorno quando o "
                "patrimônio é negativo.",
            )
        )
    outros.append(
        g(
            "balanco",
            "Balanço",
            f"{nome}: o que tem, o que deve e o patrimônio",
            [
                s("ativo", "Ativo", lambda x: em(x["ativo"])),
                s("passivo", "Passivo exigível", lambda x: em(x["passivo"])),
                s("patrimonio", "Patrimônio líquido", lambda x: em(x["patrimonio"])),
            ],
            nota="Passivo exigível: o que a empresa deve a terceiros. Patrimônio é o ativo "
            "menos o passivo.",
        )
    )
    uniao = [
        s("dividendos", "Dividendos à União", lambda x: em(x["dividendos_uniao"])),
        s(
            "repasses",
            "Subvenção e capital",
            lambda x: em((x["subvencao"] or 0.0) + (x["afac"] or 0.0)),
        ),
        s("saldo", "Saldo para a União", lambda x: em(_saldo(x))),
    ]
    if ok(uniao):
        outros.append(
            g(
                "uniao",
                "Com a União",
                f"{nome}: o que paga à União e o que recebe dela",
                uniao,
                nota="Dividendos e juros sobre capital pagos à União, menos a subvenção e o "
                "aporte de capital (AFAC). É o caixa, não o lucro.",
            )
        )
    pessoal = [s("empregados", "Empregados", lambda x: _round((x["empregados"] or 0) / 1000))]
    if ok(pessoal):
        outros.append(
            g(
                "pessoal",
                "Empregados",
                f"{nome}: empregados",
                pessoal,
                unidade="mil pessoas",
                casas=1,
                nota="Quadro próprio no fim do ano.",
            )
        )
    por_emp = [s("por-empregado", "Gasto por empregado", lambda x: _round(_por_empregado(x)))]
    if ok(por_emp):
        outros.append(
            g(
                "gasto-pessoal",
                "Gasto por empregado",
                f"{nome}: gasto com pessoal por empregado",
                por_emp,
                unidade="R$ mil por ano",
                casas=0,
                nota="Salário, encargos e benefícios do ano, divididos pelo quadro do fim do "
                "ano. Valores da época.",
            )
        )
    invest = [
        s("aprovado", "Aprovado", lambda x: em(x["investimento_aprovado"])),
        s("executado", "Executado", lambda x: em(x["investimento"])),
    ]
    if ok(invest):
        outros.append(
            g(
                "investimento",
                "Investimento",
                f"{nome}: investimento aprovado e executado",
                invest,
                nota="Orçamento de investimento das não dependentes. As dependentes investem "
                "pelo orçamento da União.",
            )
        )
    principal = principal.model_copy(update={"alternativas": outros})

    # --- a tabela de todos os anos
    def linha(
        rotulo: str, valor: Callable[[EstatalNoAno], float | None], grupo: str, un: str = curta
    ) -> LinhaTabela:
        return LinhaTabela(
            rotulo=rotulo,
            valores=[None if (v := valor(x)) is None else round(v, 1) for x in anos],
            unidade=un,
            casas=1,
            grupo=grupo,
        )

    def din(campo: str) -> Callable[[EstatalNoAno], float | None]:
        return lambda x: em(x[campo])

    linhas = [
        linha("Receita", lambda x: em(_receita(x)), "Resultado"),
        linha("Lucro ou prejuízo", din("lucro"), "Resultado"),
        linha("Margem líquida", lambda x: _razao(x["lucro"], _receita(x)), "Resultado", "%"),
        linha(
            "Retorno sobre o patrimônio",
            lambda x: _razao(x["lucro"], x["patrimonio"], True),
            "Resultado",
            "%",
        ),
        linha("Ativo", din("ativo"), "Balanço"),
        linha("Passivo exigível", din("passivo"), "Balanço"),
        linha("Patrimônio líquido", din("patrimonio"), "Balanço"),
        linha("Passivo sobre o ativo", lambda x: _razao(x["passivo"], x["ativo"]), "Balanço", "%"),
        linha("Dividendos pagos, a todos", din("dividendos"), "Com a União"),
        linha("Dividendos pagos à União", din("dividendos_uniao"), "Com a União"),
        linha("Subvenção do Tesouro", din("subvencao"), "Com a União"),
        linha("Aporte de capital (AFAC)", din("afac"), "Com a União"),
        linha("Saldo para a União", lambda x: em(_saldo(x)), "Com a União"),
        linha("Impostos pagos", din("impostos"), "Com a União"),
        linha("Empregados", lambda x: _round((x["empregados"] or 0) / 1000), "Pessoal", "mil"),
        linha("Gasto com pessoal", din("pessoal"), "Pessoal"),
        linha("Gasto por empregado", _por_empregado, "Pessoal", "R$ mil"),
        linha("Investimento executado", din("investimento"), "Investimento"),
        linha(
            "Execução do orçamento",
            lambda x: _razao(x["investimento"], x["investimento_aprovado"]),
            "Investimento",
            "%",
        ),
    ]
    linhas = [x for x in linhas if any(v for v in x.valores)]
    tabela = Tabela(
        id=f"estatal-{ident}",
        titulo=f"{nome}, ano a ano",
        subtitulo=f"{unidade}, valores da época, salvo onde diz outra unidade",
        colunas=[str(x.ano) for x in anos],
        linhas=linhas,
        fonte=fonte,
        nota="Margem, retorno, saldo e gasto por empregado: divisões e somas dos números da Sest.",
    )
    dependencia = "Dependente do Tesouro" if u.dependente else "Não dependente do Tesouro"
    partes = [dependencia, u.ministerio, f"criada em {u.criacao}" if u.criacao else ""]
    return FichaEstatal(
        id=ident,
        nome=nome,
        nome_completo=u.nome,
        setor=u.setor,
        descricao=" · ".join(p for p in partes if p),
        cartoes=cartoes,
        grafico=principal,
        tabela=tabela,
    )


def _resultado(x: EstatalNoAno, reais: Callable[[float], str]) -> str:
    """'Em 2025, lucro de R$ 110,6 bi'."""
    v = x["lucro"] or 0.0
    return f"Em {x.ano}, {'lucro' if v >= 0 else 'prejuízo'} de {reais(abs(v))}"


def _round(v: float | None) -> float | None:
    return None if v is None else round(v, 2)


def fichas(linhas: list[EstatalNoAno]) -> list[FichaEstatal]:
    """Uma ficha por estatal que está na edição mais nova, por setor e nome."""
    ultimo = max(x.ano for x in linhas)
    do_ultimo = [x for x in linhas if x.ano == ultimo]
    saida = []
    for atual in do_ultimo:
        anos = sorted((x for x in linhas if x.sigla == atual.sigla), key=lambda x: x.ano)
        saida.append(ficha(anos, do_ultimo))
    saida.sort(key=lambda f: (f.setor, f.nome))
    return saida
