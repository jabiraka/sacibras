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

from datetime import date

from sacibras import contas, relatorios
from sacibras.schema import Cartao, Grafico, LinhaTabela, Tabela
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
            procedencia="calculado",
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
            nota=(
                "O que entrou no caixa do Tesouro, pelo mês do pagamento. A União é dona de "
                "todo o BNDES e de toda a Caixa, e de parte da Petrobras e do Banco do Brasil: "
                "nestas duas, os outros acionistas recebem o resto. O dividendo de um ano "
                "depende do lucro e de quanto a empresa decide distribuir, e por isso oscila "
                "muito."
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
            fonte=f"{fonte}; saldo: conta nossa",
            procedencia="calculado",
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
        fonte=f"{fonte}; saldo: conta nossa",
        nota=(
            "Quem paga e quem recebe não são as mesmas empresas: os dividendos vêm de quatro "
            "(BNDES, Petrobras, Banco do Brasil e Caixa) e a subvenção vai para as dependentes, "
            "que são na maior parte hospitais, pesquisa e obras, e não vendem o que fazem. "
            "Valores da época, sem descontar a inflação."
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
        titulo="As estatais federais e o caixa da União, ano a ano",
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
            linha("Saldo para a União (conta nossa)", saldo, caixa),
            linha("Lucro de todas as estatais somadas", lambda a: por_ano[a].lucro, empresas),
            linha("  só das que tiveram prejuízo", lambda a: por_ano[a].prejuizos, empresas),
        ],
        fonte=f"{fonte}; saldo e soma dos prejuízos: conta nossa",
        nota=(
            "O saldo é a conta que a própria Sest faz no relatório (dividendos menos subvenção "
            "e aporte). Ficam fora dela, porque não passam por essas linhas: os impostos que as "
            "estatais pagam, o lucro que elas guardam e o quanto as ações valem. O prejuízo de uma "
            "estatal que não é dependente (os Correios) não sai do Tesouro no ano; vira dívida "
            "ou perda de patrimônio da empresa, e pode virar aporte depois."
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
            procedencia="calculado",
            secao="fiscal",
            mini=120,
        )
    ]
    graficos = [
        grafico(
            "estatais-primario",
            "Resultado primário das estatais: federais, estaduais e municipais",
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
            nota=(
                "Acima de zero, superávit. É a variação da dívida líquida das empresas, antes "
                "dos juros: déficit quer dizer que elas gastaram e investiram mais do que "
                "arrecadaram, e isso entra no resultado do setor público. O Banco Central não "
                "conta aqui os bancos públicos, a Petrobras nem a Eletrobras; das federais "
                "ficam empresas como os Correios."
            ),
        )
    ]
    return cartoes, graficos, []
