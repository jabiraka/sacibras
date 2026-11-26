"""As estatais dos estados e o caixa deles (Caio, 26/11/2026: *"Podemos incluir as empresas
estaduais também?"*).

A mesma conta das federais (`estatais.py`): dividendos que o estado recebe menos a subvenção e o
reforço de capital que põe nelas. Dados declarados pelos estados, juntados pelo Tesouro
(`fontes/tesouro_estaduais.py`), em reais da época. Somar por ano e por estado é só soma.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from sacibras.fontes.tesouro_estaduais import EmpresaEstadual
from sacibras.schema import Grafico, LinhaTabela, Tabela
from sacibras.secoes.base import br, grafico, serie
from sacibras.secoes.estatais import Pecas
from sacibras.tipos import Ponto

NA_TABELA = 10
MINUSCULAS = {"de", "da", "do", "das", "dos", "e", "em"}


def saldo(linhas: Iterable[EmpresaEstadual]) -> float:
    return sum(x.dividendos - x.subvencao - x.capital for x in linhas)


def nome_legivel(nome: str) -> str:
    """O nome como o estado declarou, sem os espaços dobrados e sem gritar."""
    nome = " ".join(nome.split())
    if nome != nome.upper():
        return nome
    palavras = [p.lower() for p in nome.split()]
    return " ".join(p if p in MINUSCULAS and i else p.capitalize() for i, p in enumerate(palavras))


def custo_ou_ganho(x: EmpresaEstadual) -> float:
    """Como no ranking das federais: o lucro; nas dependentes, menos a subvenção."""
    return x.lucro - (x.subvencao if x.dependente else 0.0)


def pecas(fonte: str, linhas: list[EmpresaEstadual]) -> Pecas:
    anos = sorted({x.ano for x in linhas})
    ultimo = anos[-1]
    do_ano = {a: [x for x in linhas if x.ano == a] for a in anos}
    ativas = len(do_ano[ultimo])

    def pontos(valores: list[float]) -> list[Ponto]:
        return [(date(a, 1, 1), v / 1e9) for a, v in zip(anos, valores, strict=True)]

    recebidos = [sum(x.dividendos for x in do_ano[a]) for a in anos]
    postos = [sum(x.subvencao + x.capital for x in do_ano[a]) for a in anos]
    saldos = [saldo(do_ano[a]) for a in anos]
    nota = (
        "Soma do que cada estado declarou, em valores da época; o Tesouro não garante os "
        "números. A lista de empresas muda: a Sabesp saiu em 2024."
    )
    desenho: Grafico = grafico(
        "estatais-estados",
        "O que as estatais estaduais pagam aos estados e o que recebem",
        [
            serie("dividendos", "Dividendos aos estados", pontos(recebidos)),
            serie("repasses", "Subvenção e capital recebidos", pontos(postos)),
            serie("saldo", "Saldo para os estados", pontos(saldos)),
        ],
        unidade="R$ bilhões",
        casas=1,
        periodicidade="A",
        fonte=fonte,
        rotulo_opcao="Estaduais",
        nota=nota,
        manchete=(
            f"Em {ultimo}, os estados receberam R$ {br(recebidos[-1] / 1e9)} bi e puseram "
            f"R$ {br(postos[-1] / 1e9)} bi."
        ),
    )

    def linha(rotulo: str, valores: list[float], grupo: str) -> LinhaTabela:
        return LinhaTabela(
            rotulo=rotulo,
            valores=[round(v / 1e9, 1) for v in valores],
            unidade="",
            casas=1,
            grupo=grupo,
        )

    caixa = "O que passou pelo caixa dos estados"
    empresas = "O resultado das empresas (não entra no caixa)"
    conta = Tabela(
        id="estatais-estados",
        titulo="As estatais estaduais e o caixa dos estados",
        subtitulo=f"R$ bilhões, valores da época; {ativas} empresas em {ultimo}",
        colunas=[str(a) for a in anos],
        linhas=[
            linha("Dividendos recebidos pelos estados", recebidos, caixa),
            linha("Subvenção", [-sum(x.subvencao for x in do_ano[a]) for a in anos], caixa),
            linha("Reforço de capital", [-sum(x.capital for x in do_ano[a]) for a in anos], caixa),
            linha("Saldo para os estados", saldos, caixa),
            linha(
                "Lucro de todas somadas", [sum(x.lucro for x in do_ano[a]) for a in anos], empresas
            ),
            linha(
                "  só das que tiveram prejuízo",
                [sum(min(x.lucro, 0.0) for x in do_ano[a]) for a in anos],
                empresas,
            ),
        ],
        fonte=fonte,
        # Em 2021 e 2022 a Cemig vem com o lucro do grupo e as duas maiores subsidiárias em
        # linhas à parte (conferido no arquivo em 26/11/2026). A soma é a que o Tesouro publica.
        nota=(
            "Soma do declarado pelos estados, sem garantia do Tesouro. A Sabesp saiu em 2024; "
            "o lucro de 2021 e 2022 conta em dobro subsidiárias da Cemig."
        ),
        rotulo_opcao="Estaduais, ano a ano",
    )

    def milhoes(valores: Iterable[float]) -> list[float | None]:
        return [float(round(v / 1e6)) for v in valores]

    por_estado = []
    for estado in sorted({x.estado for x in do_ano[ultimo]}):
        deste = [x for x in do_ano[ultimo] if x.estado == estado]
        todos = [x for x in linhas if x.estado == estado]
        por_estado.append((saldo(deste), estado, deste, todos))
    estados = Tabela(
        id="estatais-estados-uf",
        titulo="Estatais estaduais, estado por estado",
        subtitulo=f"R$ milhões em {ultimo}; entre parênteses, quantas empresas",
        colunas=[
            "Dividendos",
            "Subvenção",
            "Capital",
            "Saldo",
            f"Saldo desde {anos[0]}",
            "Lucro das empresas",
        ],
        linhas=[
            LinhaTabela(
                # O arquivo escreve "Espiríto Santo".
                rotulo=f"{estado.replace('Espiríto', 'Espírito')} ({len(deste)})",
                valores=milhoes(
                    (
                        sum(x.dividendos for x in deste),
                        sum(x.subvencao for x in deste),
                        sum(x.capital for x in deste),
                        s,
                        saldo(todos),
                        sum(x.lucro for x in deste),
                    )
                ),
                unidade="",
                casas=0,
            )
            # De quem mais pôs para quem mais recebeu.
            for s, estado, deste, todos in sorted(por_estado, key=lambda e: (e[0], e[1]))
        ],
        fonte=fonte,
        nota="Saldo: dividendos menos subvenção e capital. Negativo, o estado pôs mais.",
        rotulo_opcao="Estaduais, por estado",
    )

    ordem = sorted(do_ano[ultimo], key=custo_ou_ganho)
    lucros = [x for x in reversed(ordem) if custo_ou_ganho(x) > 0][:NA_TABELA]
    custos = [x for x in ordem if custo_ou_ganho(x) < 0][:NA_TABELA]

    def empresa(x: EmpresaEstadual, grupo: str) -> LinhaTabela:
        return LinhaTabela(
            rotulo=f"{nome_legivel(x.nome)} ({x.uf})",
            valores=milhoes((custo_ou_ganho(x), x.lucro, x.dividendos, x.subvencao, x.capital)),
            unidade="",
            casas=0,
            grupo=grupo,
        )

    maiores = Tabela(
        id="estatais-estados-empresas",
        titulo="As estatais estaduais que mais lucram e as que mais custam",
        subtitulo=f"R$ milhões em {ultimo}",
        colunas=["Ganho ou custo", "Lucro ou prejuízo", "Dividendos", "Subvenção", "Capital"],
        linhas=[
            *(empresa(x, "Maiores lucros") for x in lucros),
            *(empresa(x, "Maiores custos") for x in custos),
        ],
        fonte=fonte,
        nota=(
            "Ganho ou custo: o lucro; nas dependentes, menos a subvenção. Dividendos são os "
            "declarados pelo estado."
        ),
        rotulo_opcao="Estaduais, por empresa",
    )
    return [], [desenho], [conta, estados, maiores]
