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
from sacibras.fontes import sest
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


def sest_mais_nova() -> sest.Anexo | None:
    """A planilha da Sest da edição mais nova, ou None se a Sest falhar."""
    try:
        return sest.anexo()
    except Exception as erro:
        print(f"  aviso: estatais: planilha da Sest indisponível ({str(erro)[:120]})")
        return None


def conta_do_ano(lido: sest.Anexo | None = None) -> Pecas:
    """Dividendos menos subvenção e aporte, ano a ano (Relatório Agregado da Sest): da
    planilha da edição mais nova (`lido`) ou, sem ela, dos números lidos à mão."""
    if lido is not None:
        por_ano, fonte = lido.por_ano, lido.fonte
        subvencoes_lista, lucros_lista = lido.subvencoes, lido.lucros
        diretas, dependentes = lido.diretas, lido.dependentes
    else:
        por_ano, fonte = relatorios.ESTATAIS_POR_ANO, relatorios.FONTE_ESTATAIS
        subvencoes_lista, lucros_lista = relatorios.SUBVENCOES_2025, relatorios.LUCRO_DOS_MAIORES
        diretas, dependentes = relatorios.ESTATAIS_DIRETAS, relatorios.ESTATAIS_DEPENDENTES
    anos = sorted(por_ano)
    ultimo = anos[-1]

    def saldo(ano: int) -> float:
        x = por_ano[ano]
        return x.dividendos_uniao - x.subvencao - x.aporte

    def pontos(valor: object) -> list[Ponto]:
        return [(date(a, 1, 1), valor(a) / 1000) for a in anos]  # type: ignore[operator]

    x = por_ano[ultimo]
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
            detalhe=(f"{dependentes} das {diretas} estatais; mais da metade vai a hospitais"),
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
        subtitulo=f"{ultimo}, as {dependentes} estatais dependentes",
        colunas=["R$ bilhões", "% do total"],
        linhas=[
            LinhaTabela(
                rotulo=nome,
                valores=[round(v / 1000, 2), round(v / x.subvencao * 100, 1)],
                unidade="",
                casas=1,
            )
            for nome, v in subvencoes_lista
        ],
        fonte=fonte,
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
            for nome, a, b in lucros_lista
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


def ficha(
    anos: list[EstatalNoAno], todas_do_ano: list[EstatalNoAno], fonte_sest: str
) -> FichaEstatal:
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

    fonte = f"{fonte_sest}, {anos[0].ano} a {u.ano}"
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


def fichas(fonte: str, linhas: list[EstatalNoAno]) -> list[FichaEstatal]:
    """Uma ficha por estatal que está na edição mais nova, por setor e nome."""
    ultimo = max(x.ano for x in linhas)
    do_ultimo = [x for x in linhas if x.ano == ultimo]
    saida = []
    for atual in do_ultimo:
        anos = sorted((x for x in linhas if x.sigla == atual.sigla), key=lambda x: x.ano)
        saida.append(ficha(anos, do_ultimo, fonte))
    saida.sort(key=lambda f: (f.setor, f.nome))
    return saida


# ------------------------------------------------------------------ rendem mais que o juro?
#
# Caio, 25/11/2026: "Vale manter as estatais? Bem provocativo mesmo, mostrando os dados que
# podem sustentar uma conclusão ou outra". A régua é a do custo de oportunidade: se a União
# vendesse a parte dela e abatesse dívida, deixaria de pagar o juro médio da dívida bruta. O
# retorno é o lucro sobre o patrimônio do ano (contábil, da Sest); o juro, a taxa implícita
# de 12 meses em dezembro (BC). Fica de fora o preço de venda: ele vem da bolsa, e a B3 saiu.

GRANDES = {
    "PETROBRAS (Grupo)": "Petrobras",
    "BNDES (Grupo)": "BNDES",
    "BB (Grupo)": "Banco do Brasil",
    "CAIXA (Grupo)": "Caixa",
}


def _roe(x: EstatalNoAno) -> float | None:
    return _razao(x["lucro"], x["patrimonio"], positivo=True)


def retorno(
    fonte_sest: str, linhas: list[EstatalNoAno], taxa: list[Ponto], fonte_taxa: str
) -> Pecas:
    """O retorno das estatais que vivem do que vendem contra o juro da dívida."""
    juro = {d.year: v for d, v in taxa if d.month == 12}
    anos = sorted({x.ano for x in linhas if x.ano in juro})
    ultimo = anos[-1]
    por = {(x.sigla, x.ano): x for x in linhas}
    fonte = f"{fonte_sest}; juro: {fonte_taxa}"

    series = [
        Serie(
            id=_id(sigla),
            nome=nome,
            pontos=[
                (date(a, 1, 1), _round(_roe(por[(sigla, a)])) if (sigla, a) in por else None)
                for a in anos
            ],
        )
        for sigla, nome in GRANDES.items()
    ]
    series.append(
        Serie(
            id="juro",
            nome="Juro da dívida",
            pontos=[(date(a, 1, 1), round(juro[a], 2)) for a in anos],
            papel="referencia",
        )
    )
    acima = [
        n
        for s, n in GRANDES.items()
        if (x := por.get((s, ultimo))) and (r := _roe(x)) and r > juro[ultimo]
    ]
    desenho = grafico(
        "estatais-retorno",
        "As maiores estatais rendem mais que o juro da dívida?",
        series,
        unidade="% ao ano",
        casas=1,
        periodicidade="A",
        fonte=fonte,
        rotulo_opcao="Retorno contra o juro",
        manchete=(
            f"Em {ultimo}, juro da dívida de {br(juro[ultimo])} %; acima dele: "
            f"{', '.join(acima) if acima else 'nenhuma das quatro'}."
        ),
        nota=(
            "Retorno é o lucro sobre o patrimônio do ano. Vender e abater dívida pouparia o "
            "juro, mas o ganho depende do preço de venda, que estes dados não têm."
        ),
    )

    def linha(x: EstatalNoAno, grupo: str) -> LinhaTabela:
        da_empresa = [por[(x.sigla, a)] for a in anos if (x.sigla, a) in por]
        roes = [r for y in da_empresa if (r := _roe(y)) is not None]
        r = _roe(x)
        return LinhaTabela(
            rotulo=NOMES.get(x.sigla, x.sigla.replace(" (Grupo)", "")),
            valores=[
                None if r is None else round(r, 1),
                # Com patrimônio negativo hoje, a média de anos de patrimônio quase zero engana.
                round(sum(roes) / len(roes), 1) if roes and r is not None else None,
                None if r is None else round(r - juro[ultimo], 1),
                round(sum(_saldo(y) for y in da_empresa) / 1e9, 2),
            ],
            unidade="",
            casas=1,
            grupo=grupo,
        )

    vendem = sorted(
        (x for x in linhas if x.ano == ultimo and not x.dependente),
        key=lambda x: -(x["patrimonio"] or 0.0),
    )
    grupos = (
        (f"Renderam acima do juro em {ultimo}", lambda r: r is not None and r > juro[ultimo]),
        (f"Renderam abaixo do juro em {ultimo}", lambda r: r is not None and r <= juro[ultimo]),
        ("Patrimônio negativo ou zero", lambda r: r is None),
    )
    linhas_tabela = [
        linha(x, f"{nome} ({sum(1 for y in vendem if cabe(_roe(y)))})")
        for nome, cabe in grupos
        for x in vendem
        if cabe(_roe(x))
    ]
    tabela = Tabela(
        id="estatais-retorno",
        titulo="As estatais que vivem do que vendem, contra o juro da dívida",
        subtitulo=(
            f"Retorno sobre o patrimônio, em %; juro médio da dívida bruta em {ultimo}: "
            f"{br(juro[ultimo])} %"
        ),
        colunas=[
            str(ultimo),
            f"Média desde {anos[0]}",
            "Contra o juro, pp",
            f"Saldo com a União desde {anos[0]}, R$ bi",
        ],
        linhas=linhas_tabela,
        fonte=fonte,
        nota=(
            "As não dependentes, da maior para a menor em patrimônio. Saldo: dividendos à "
            "União menos subvenção e aporte."
        ),
    )
    return [], [desenho], [tabela]


# ------------------------------------------------------------------ ou aplicar no lugar?
#
# Caio, 25/11/2026: "Compare com oq poderia ser investido ao invés delas". O retorno de cada
# ano das estatais (lucro sobre o patrimônio, contábil) contra o que o mesmo dinheiro rendeu
# no ano civil em CDI, Tesouro Prefixado e Tesouro IPCA+ (os de "Quanto rendeu R$ 100", em
# Mercados, títulos de uns cinco anos rolados) e abatendo dívida (o juro médio da dívida
# bruta em dezembro), com o IPCA de referência. Sem bolsa: a B3 saiu do projeto.

Alternativa = tuple[str, dict[int, float], str]
"""(nome, retorno % em cada ano, papel da série)."""


def _somadas(linhas: list[EstatalNoAno], ano: int, sem: str = "") -> float | None:
    """Lucro sobre patrimônio das não dependentes, todas juntas (sem a `sem`, se dada)."""
    x = [y for y in linhas if y.ano == ano and not y.dependente and y.sigla != sem]
    return _razao(sum(y["lucro"] or 0.0 for y in x), sum(y["patrimonio"] or 0.0 for y in x), True)


def alternativas(
    fonte_sest: str,
    linhas: list[EstatalNoAno],
    opcoes: dict[str, Alternativa],
    fonte_opcoes: str,
) -> Pecas:
    """R$ 100 nas estatais ou numa aplicação, de ano a ano e acumulado."""
    anos_comuns = {x.ano for x in linhas}
    for _, retornos, _ in opcoes.values():
        anos_comuns &= set(retornos)
    anos = sorted(anos_comuns)
    por = {(x.sigla, x.ano): x for x in linhas}
    estatais: dict[str, Alternativa] = {
        "somadas": (
            "Estatais não dependentes",
            {a: v for a in anos if (v := _somadas(linhas, a)) is not None},
            "realizado",
        ),
        # A Petrobras faz a maior parte do lucro: sem ela, o resto conta outra história.
        "sem-petrobras": (
            "Sem a Petrobras",
            {a: v for a in anos if (v := _somadas(linhas, a, sem="PETROBRAS (Grupo)")) is not None},
            "realizado",
        ),
    }
    for sigla, nome in GRANDES.items():
        rs = {a: r for a in anos if (x := por.get((sigla, a))) and (r := _roe(x)) is not None}
        if len(rs) == len(anos):
            estatais[_id(sigla)] = (nome, rs, "realizado")
    todas = {**estatais, **opcoes}

    def acumulado(r: dict[int, float]) -> float:
        nivel = 100.0
        for a in anos:
            nivel *= 1 + r[a] / 100
        return nivel

    def nivel(r: dict[int, float]) -> list[tuple[date, float | None]]:
        saida: list[tuple[date, float | None]] = [(date(anos[0] - 1, 1, 1), 100.0)]
        v = 100.0
        for a in anos:
            v *= 1 + r[a] / 100
            saida.append((date(a, 1, 1), round(v, 1)))
        return saida

    no_grafico = ("somadas", "sem-petrobras", "petrobras", "cdi", "divida", "ipca")
    series = [
        Serie(id=k, nome=todas[k][0], pontos=nivel(todas[k][1]), papel=todas[k][2])  # type: ignore[arg-type]
        for k in no_grafico
        if k in todas
    ]
    fonte = f"{fonte_sest}; {fonte_opcoes}"
    s, sem, cdi = (acumulado(todas[k][1]) for k in ("somadas", "sem-petrobras", "cdi"))
    desenho = grafico(
        "estatais-alternativas",
        f"R$ 100 nas estatais ou aplicados, de {anos[0]} a {anos[-1]}",
        series,
        unidade="R$",
        casas=0,
        periodicidade="A",
        fonte=fonte,
        rotulo_opcao="Ou aplicar no lugar",
        manchete=(
            f"Viraram R$ {br(s, 0)} nas não dependentes, R$ {br(sem, 0)} sem a Petrobras e "
            f"R$ {br(cdi, 0)} no CDI."
        ),
        nota=(
            "Estatal: lucro sobre o patrimônio, como se ficasse na empresa (contábil). "
            "Aplicação: preço de mercado, antes de imposto; não é a mesma régua."
        ),
    )

    def linha(chave: str, grupo: str) -> LinhaTabela:
        nome, r, _ = todas[chave]
        return LinhaTabela(
            rotulo=nome,
            valores=[*(round(r[a], 1) for a in anos), round(acumulado(r) - 100, 1)],
            unidade="%",
            casas=1,
            grupo=grupo,
        )

    tabela = Tabela(
        id="estatais-alternativas",
        titulo="O retorno das estatais e o das aplicações, ano a ano",
        subtitulo="% no ano; acumulado de todos os anos",
        colunas=[*(str(a) for a in anos), "Acumulado"],
        linhas=[
            *(linha(k, "Estatais: lucro sobre o patrimônio") for k in estatais),
            *(
                linha(k, "No lugar delas")
                for k, (_, _, papel) in opcoes.items()
                if papel != "referencia"
            ),
            *(linha(k, "Referência") for k, (_, _, p) in opcoes.items() if p == "referencia"),
        ],
        fonte=fonte,
        nota=(
            "Abater dívida: o juro médio da dívida bruta em dezembro. Tesouro: o título de uns "
            "cinco anos, trocado no vencimento."
        ),
    )
    return [], [desenho], [tabela]
