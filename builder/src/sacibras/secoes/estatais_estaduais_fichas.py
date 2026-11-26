"""Uma estatal estadual por dentro (Caio, 26/11/2026: *"podemos pegar o histórico mas pulando
se tiver um erro muito óbvio"*).

Duas contas daqui sobre o arquivo do Tesouro (`fontes/tesouro_estaduais.py`):

- **A mesma empresa entre os anos.** O nome muda de uma edição para outra; dentro de cada
  estado, casa o par de nomes mais parecido (`casar`). Em 26/11/2026, 271 das 298 empresas de
  2024 tinham os quatro anos, e os pares de nomes diferentes foram olhados um a um.
- **Erro óbvio fica em branco** (`limpar`): patrimônio ou folha em outra unidade, um ano que
  destoa dos dois vizinhos, folha por empregado abaixo do salário mínimo e os casos olhados à
  mão (`A_MAO`). Lucro, dividendos, subvenção, capital e investimento variam muito de um ano
  para outro e só saem quando a linha inteira veio em outra unidade.
"""

from __future__ import annotations

import difflib
import re
import statistics
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date

from sacibras.fontes.tesouro_estaduais import EmpresaEstadual
from sacibras.schema import (
    Cartao,
    FichaEstatal,
    Grafico,
    LinhaTabela,
    Serie,
    Tabela,
    VarianteGrafico,
)
from sacibras.secoes.base import br, com_variantes, grafico
from sacibras.secoes.estatais import Pecas
from sacibras.secoes.estatais_estaduais import custo_ou_ganho, nome_legivel

MESMA = 0.5
"""Semelhança mínima para dois nomes serem a mesma empresa."""
ABREVIADAS = {"cia": "companhia", "companha": "companhia"}
VAZIAS = frozenset(
    ["de", "da", "do", "das", "dos", "e", "em", "sa", "s", "a", "o", "estado", "liquidacao", "ltda"]
)
OUTROS_NOMES = {("DF", "BIOTIC SA"): "Parque Tecnológico de Brasília - BIOTIC"}
"""Nome novo e nome antigo que a semelhança não liga, conferidos à mão."""

OUTRA_UNIDADE = 300.0
"""Patrimônio ou folha tantas vezes menor (ou maior) que o dos outros anos: outra unidade."""
OUTRA_UNIDADE_JUNTO = 100.0
"""Na linha que veio em outra unidade, o resto do dinheiro sai a partir daqui."""
DESTOA = 8.0
VIZINHOS_CONCORDAM = 3.0
FOLHA_MINIMA = 15_000.0
"""Folha anual por empregado abaixo disso não paga um salário mínimo com 13º."""

UNIDADE_PELA_FOLHA = ("patrimonio", "pessoal")
CONFERIDOS = ("patrimonio", "empregados", "pessoal")
"""Os que mudam devagar: um ano isolado muito diferente é erro."""
DINHEIRO = ("lucro", "dividendos", "subvencao", "capital", "investimento")

# Olhados no arquivo em 26/11/2026: em 2021 e 2022 a linha da Cemig mistura o grupo (lucro e
# patrimônio) com a controladora sozinha (folha de R$ 62 mi e 41 mi; 57 empregados em 2022),
# porque as subsidiárias vinham em linhas à parte. Chave: estado, palavras do nome, ano.
A_MAO: dict[tuple[str, frozenset[str], int], tuple[str, ...]] = {
    ("MG", frozenset({"energetica", "minas"}), 2021): ("pessoal",),
    ("MG", frozenset({"energetica", "minas"}), 2022): ("pessoal", "empregados"),
}


def _palavras(nome: str) -> list[str]:
    sem = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    todas = (ABREVIADAS.get(p, p) for p in re.findall(r"[a-z0-9]+", sem))
    return [p for p in todas if p not in VAZIAS]


def semelhanca(a: str, b: str) -> float:
    x, y = _palavras(a), _palavras(b)
    comuns = set(x) & set(y)
    if not comuns:
        return 0.0
    juntas = len(comuns) / len(set(x) | set(y))
    contido = len(comuns) / min(len(set(x)), len(set(y)))
    letras = difflib.SequenceMatcher(None, " ".join(x), " ".join(y)).ratio()
    return 0.4 * juntas + 0.3 * contido + 0.3 * letras


def casar(linhas: list[EmpresaEstadual]) -> list[list[EmpresaEstadual]]:
    """Cada empresa do último ano com os anos anteriores dela, em ordem."""
    ultimo = max(x.ano for x in linhas)
    cadeias = [[x] for x in linhas if x.ano == ultimo]
    for ano in sorted({x.ano for x in linhas if x.ano < ultimo}, reverse=True):
        do_ano = [x for x in linhas if x.ano == ano]
        pares: list[tuple[float, int, int]] = []
        for i, cadeia in enumerate(cadeias):
            uf = cadeia[0].uf
            nomes = [y.nome for y in cadeia]
            nomes += [OUTROS_NOMES[(uf, n)] for n in nomes if (uf, n) in OUTROS_NOMES]
            pares += [
                (max(semelhanca(n, x.nome) for n in nomes), i, j)
                for j, x in enumerate(do_ano)
                if x.uf == uf
            ]
        com_par: set[int] = set()
        usadas: set[int] = set()
        for nota, i, j in sorted(pares, key=lambda p: (-p[0], p[1], p[2])):
            if nota < MESMA or i in com_par or j in usadas:
                continue
            com_par.add(i)
            usadas.add(j)
            cadeias[i].append(do_ano[j])
    return [sorted(c, key=lambda x: x.ano) for c in cadeias]


@dataclass(frozen=True)
class Limpa:
    anos: list[EmpresaEstadual]
    fora: dict[int, set[str]]
    """Os campos que saíram, por ano; a ficha deixa em branco."""


def _destoa(valor: float, antes: float, depois: float) -> bool:
    a, d, v = abs(antes), abs(depois), abs(valor)
    if max(a, d) > VIZINHOS_CONCORDAM * min(a, d):
        return False
    return v * DESTOA < min(a, d) or v > DESTOA * max(a, d)


def limpar(anos: list[EmpresaEstadual]) -> Limpa:
    fora: dict[int, set[str]] = {x.ano: set() for x in anos}

    def vezes_menor(i: int, campo: str) -> float | None:
        """Quantas vezes a mediana dos outros anos é maior que o valor deste."""
        v = getattr(anos[i], campo)
        outros = [abs(o) for k, x in enumerate(anos) if k != i and (o := getattr(x, campo))]
        return statistics.median(outros) / abs(v) if v and len(outros) >= 2 else None

    for i, x in enumerate(anos):
        for campo in UNIDADE_PELA_FOLHA:
            r = vezes_menor(i, campo)
            if r is not None and not 1 / OUTRA_UNIDADE < r < OUTRA_UNIDADE:
                fora[x.ano].add(campo)
        if fora[x.ano]:  # a linha veio em outra unidade: sai o dinheiro que acompanha
            for campo in (*UNIDADE_PELA_FOLHA, *DINHEIRO):
                r = vezes_menor(i, campo)
                if r is not None and r >= OUTRA_UNIDADE_JUNTO:
                    fora[x.ano].add(campo)
        if 0 < i < len(anos) - 1:
            for campo in CONFERIDOS:
                v = getattr(x, campo)
                a, d = getattr(anos[i - 1], campo), getattr(anos[i + 1], campo)
                if v and a and d and _destoa(v, a, d):
                    fora[x.ano].add(campo)
        palavras = set(_palavras(x.nome))
        for (uf, pedidas, ano), campos in A_MAO.items():
            if x.uf == uf and x.ano == ano and pedidas <= palavras:
                fora[x.ano].update(campos)
        if (
            x.pessoal
            and x.empregados
            and not {"pessoal", "empregados"} & fora[x.ano]
            and x.pessoal / x.empregados < FOLHA_MINIMA
        ):
            fora[x.ano].add("pessoal")
    return Limpa(anos, {ano: campos for ano, campos in fora.items() if campos})


def _sem_o_errado(x: EmpresaEstadual, campos: set[str]) -> EmpresaEstadual:
    """Os campos opcionais ficam vazios; os de dinheiro a ficha esconde por `fora`."""
    return replace(
        x,
        patrimonio=None if "patrimonio" in campos else x.patrimonio,
        empregados=None if "empregados" in campos else x.empregados,
        pessoal=None if "pessoal" in campos else x.pessoal,
        investimento=None if "investimento" in campos else x.investimento,
    )


def _id(x: EmpresaEstadual) -> str:
    return f"{x.uf.lower()}-{'-'.join(_palavras(x.nome))[:60].strip('-')}"


Valor = Callable[[EmpresaEstadual], float | None]


def ficha(brutos: list[EmpresaEstadual], fonte: str, ident: str) -> FichaEstatal:
    limpa = limpar(brutos)
    anos = [_sem_o_errado(x, limpa.fora.get(x.ano, set())) for x in limpa.anos]
    u = anos[-1]
    nome = nome_legivel(u.nome)
    datas = [date(x.ano, 1, 1) for x in anos]
    tamanho = max(
        abs(v or 0.0) for x in anos for v in (x.patrimonio, x.lucro, x.subvencao, x.pessoal)
    )
    if tamanho >= 2e9:
        escala, unidade, curta, sufixo = 1e9, "R$ bilhões", "R$ bi", "bi"
    else:
        escala, unidade, curta, sufixo = 1e6, "R$ milhões", "R$ mi", "mi"

    def em(campo: str) -> Valor:
        def valor(x: EmpresaEstadual) -> float | None:
            if campo in limpa.fora.get(x.ano, set()):
                return None
            v: float | None = getattr(x, campo)
            return None if v is None else round(v / escala, 2)

        return valor

    def saldo(x: EmpresaEstadual) -> float | None:
        d, s, c = (em(campo)(x) for campo in ("dividendos", "subvencao", "capital"))
        if d is None or s is None or c is None:
            return None
        return round(d - s - c, 2)

    def empregados(x: EmpresaEstadual) -> float | None:
        return x.empregados

    def pontos(f: Valor) -> list[tuple[date, float | None]]:
        return [(d, f(x)) for d, x in zip(datas, anos, strict=True)]

    periodo = f"{anos[0].ano} a {u.ano}" if len(anos) > 1 else str(u.ano)
    fonte = f"{fonte}; {periodo}"
    nota = "Declarado pelo estado, em valores da época." + (
        " Número com erro óbvio na fonte fica em branco." if limpa.fora else ""
    )

    def cartao(
        chave: str, rotulo: str, f: Valor, detalhe: str, un: str = unidade, casas: int = 1
    ) -> Cartao | None:
        atual = f(u)
        if atual is None:
            return None
        return Cartao(
            id=f"estadual-{ident}-{chave}",
            rotulo=rotulo,
            valor=atual,
            unidade=un,
            casas=casas,
            referencia=datas[-1],
            periodicidade="A",
            detalhe=detalhe,
            fonte=fonte,
            secao="fiscal",
            mini=[(d, v) for d, v in pontos(f) if v is not None],
        )

    lucro = em("lucro")(u)
    quatro = [
        cartao(
            "lucro",
            "Prejuízo" if (lucro or 0.0) < 0 else "Lucro",
            em("lucro"),
            "resultado do ano",
        ),
        cartao("subvencao", "Subvenção do estado", em("subvencao"), "para pessoal e custeio")
        if u.dependente
        else cartao(
            "patrimonio", "Patrimônio líquido", em("patrimonio"), "o que tem menos o que deve"
        ),
        cartao("saldo", "Saldo com o estado", saldo, "dividendos menos subvenção e capital"),
        cartao(
            "empregados",
            "Empregados",
            empregados,
            "como o estado declarou",
            un="pessoas",
            casas=0,
        ),
    ]

    def g(
        chave: str,
        opcao: str,
        series: list[tuple[str, str, Valor]],
        *,
        unidade_dele: str = unidade,
        casas: int = 1,
    ) -> Grafico:
        return grafico(
            f"estadual-{ident}-{chave}",
            f"{nome}: {opcao.lower()}",
            [Serie(id=i, nome=rotulo, pontos=pontos(f)) for i, rotulo, f in series],
            unidade=unidade_dele,
            casas=casas,
            periodicidade="A",
            fonte=fonte,
            rotulo_opcao=opcao,
            largura="inteira",
            nota=nota,
        )

    principal = g("resultado", "Lucro ou prejuízo", [("lucro", "Lucro ou prejuízo", em("lucro"))])
    outros = [
        g(
            "estado",
            "Com o estado",
            [
                ("dividendos", "Dividendos ao estado", em("dividendos")),
                ("subvencao", "Subvenção", em("subvencao")),
                ("capital", "Reforço de capital", em("capital")),
            ],
        ),
        g(
            "patrimonio",
            "Patrimônio líquido",
            [("patrimonio", "Patrimônio líquido", em("patrimonio"))],
        ),
        g(
            "empregados",
            "Empregados",
            [("empregados", "Empregados", empregados)],
            unidade_dele="pessoas",
            casas=0,
        ),
        g("pessoal", "Gasto com pessoal", [("pessoal", "Gasto com pessoal", em("pessoal"))]),
        g("investimento", "Investimento", [("inv", "Investimento", em("investimento"))]),
    ]
    manchete = ""
    if lucro is not None:
        palavra = "lucro" if lucro >= 0 else "prejuízo"
        manchete = f"Em {u.ano}, {palavra} de R$ {br(abs(lucro))} {sufixo}."
    principal = principal.model_copy(
        update={
            "manchete": manchete,
            "alternativas": [o for o in outros if any(v for s in o.series for _, v in s.pontos)],
        }
    )

    def linha(rotulo: str, f: Valor, un: str = curta, casas: int = 1) -> LinhaTabela:
        return LinhaTabela(rotulo=rotulo, valores=[f(x) for x in anos], unidade=un, casas=casas)

    linhas = [
        linha("Lucro ou prejuízo", em("lucro")),
        linha("Patrimônio líquido", em("patrimonio")),
        linha("Dividendos ao estado", em("dividendos")),
        linha("Subvenção", em("subvencao")),
        linha("Reforço de capital", em("capital")),
        linha("Saldo com o estado", saldo),
        linha("Empregados", empregados, "pessoas", 0),
        linha("Gasto com pessoal", em("pessoal")),
        linha("Investimento", em("investimento")),
    ]
    tabela = Tabela(
        id=f"estadual-{ident}",
        titulo=f"{nome}, ano a ano",
        subtitulo=f"{unidade}, valores da época, salvo onde diz outra unidade",
        colunas=[str(x.ano) for x in anos],
        linhas=[li for li in linhas if any(v for v in li.valores)],
        fonte=fonte,
        nota=nota,
    )
    # O arquivo escreve "Espiríto Santo".
    estado = u.estado.replace("Espiríto", "Espírito")
    return FichaEstatal(
        id=ident,
        nome=f"{nome} ({u.uf})",
        nome_completo=nome,
        setor=estado,
        descricao=("Dependente" if u.dependente else "Não dependente") + " do estado",
        cartoes=[c for c in quatro if c is not None],
        grafico=principal,
        tabela=tabela,
    )


def fichas(fonte: str, linhas: list[EmpresaEstadual]) -> list[FichaEstatal]:
    """Uma ficha por empresa do último ano, por estado e nome."""
    saida: list[FichaEstatal] = []
    vistos: set[str] = set()
    for anos in casar(linhas):
        ident = base = _id(anos[-1])
        n = 2
        while ident in vistos:
            ident, n = f"{base}-{n}", n + 1
        vistos.add(ident)
        saida.append(ficha(anos, fonte, ident))
    return sorted(saida, key=lambda f: (f.setor, f.nome))


def primeira(linhas: list[EmpresaEstadual], prontas: list[FichaEstatal]) -> str:
    """Abre na de maior lucro no último ano."""
    ultimo = max(x.ano for x in linhas)
    maior = max((x for x in linhas if x.ano == ultimo), key=lambda x: x.lucro)
    ident = _id(maior)
    return ident if any(f.id == ident for f in prontas) else prontas[0].id


# ------------------------------------------------------------------ quem ganha e quem custa
#
# Caio, 26/11/2026: "dá pra ver o ranking de quais estaduais dão mais lucros ou prejuízos?" e
# "sim, ponha". A mesma conta do das federais: o lucro; nas dependentes, menos a subvenção.

DESTAQUES = 3

APELIDOS: tuple[tuple[str, frozenset[str], str], ...] = (
    ("MG", frozenset({"energetica", "minas"}), "Cemig"),
    ("MG", frozenset({"desenvolvimento", "economico", "minas"}), "Codemig"),
    ("PR", frozenset({"saneamento", "parana"}), "Sanepar"),
    ("DF", frozenset({"urbanizadora", "capital"}), "Novacap"),
    ("SP", frozenset({"paulista", "trens"}), "CPTM"),
    ("SC", frozenset({"santa", "catarina", "participacao"}), "SC Participações"),
)
"""O nome curto, para a legenda, das que estavam nos extremos em 26/11/2026; quem não está
aqui aparece com o nome declarado."""


def apelido(x: EmpresaEstadual) -> str:
    palavras = set(_palavras(x.nome))
    curto = next((a for uf, p, a in APELIDOS if uf == x.uf and p <= palavras), None)
    return f"{curto or nome_legivel(x.nome)} ({x.uf})"


def ranking(fonte: str, linhas: list[EmpresaEstadual]) -> Pecas:
    """As três que mais ganham e as três que mais custam no último ano, ano a ano."""
    ultimo = max(x.ano for x in linhas)
    anos = sorted({x.ano for x in linhas})
    cadeias = casar(linhas)
    ordem = sorted(cadeias, key=lambda c: custo_ou_ganho(c[-1]))
    ganham = [c for c in reversed(ordem) if custo_ou_ganho(c[-1]) > 0][:DESTAQUES]
    custam = [c for c in ordem if custo_ou_ganho(c[-1]) < 0][:DESTAQUES]

    def serie_de(cadeia: list[EmpresaEstadual]) -> Serie:
        fora = limpar(cadeia).fora
        por_ano = {
            x.ano: round(custo_ou_ganho(x) / 1e9, 2)
            for x in cadeia
            if "lucro" not in fora.get(x.ano, set())
        }
        return Serie(
            id=_id(cadeia[-1]),
            nome=apelido(cadeia[-1]),
            pontos=[(date(a, 1, 1), por_ano.get(a)) for a in anos],
        )

    lucros = [serie_de(c) for c in ganham]
    custos = [serie_de(c) for c in custam]
    nota = (
        "Lucro ou prejuízo do ano; nas dependentes do estado, menos a subvenção. Declarado "
        "pelos estados, em valores da época."
    )

    def em_texto(cadeias_: list[list[EmpresaEstadual]]) -> str:
        return ", ".join(f"{apelido(c[-1])} {br(custo_ou_ganho(c[-1]) / 1e9)}" for c in cadeias_)

    desenho = grafico(
        "estatais-estados-ranking",
        "As estaduais que mais lucram e as que mais custam",
        [*lucros, *custos],
        unidade="R$ bilhões",
        casas=1,
        periodicidade="A",
        fonte=fonte,
        rotulo_opcao="Estaduais: quem lucra e quem custa",
        manchete=f"Em {ultimo}, em R$ bi: {em_texto(ganham)}; {em_texto(custam)}.",
        nota=nota,
    )

    # Cada lado na escala dele, como no das federais.
    def lado(id_: str, rotulo: str, series: list[Serie]) -> VarianteGrafico:
        return VarianteGrafico(
            id=id_,
            rotulo=rotulo,
            titulo=desenho.titulo,
            unidade=desenho.unidade,
            casas=1,
            periodicidade="A",
            series=series,
            nota=nota,
            fonte=fonte,
        )

    desenho = com_variantes(
        desenho,
        "Os dois lados",
        lado("lucros", "Os 3 maiores lucros", lucros),
        lado("custos", "Os 3 maiores custos", custos),
        nome_da_lista="Ver",
    )
    return [], [desenho], []
