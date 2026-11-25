"""O primário que estabiliza a dívida, do número de hoje ao que o governo projeta.

Caio, 25/11/2026: *"Temos uma diferença mto grande, entre 4,7% do PIB e 2,2%. Temos que achar
um jeito de conciliar esses dois, ou as pessoas ficarão confusas"*. Os dois são a mesma
conta, dívida × (juro − crescimento) ÷ (1 + crescimento), com hipóteses diferentes: a de
Riscos usa o juro que a dívida pagou e o PIB dos últimos 12 meses; a do projeto da LDO, o
juro e o PIB que o governo supõe para o ano, mais as emissões que não passam pelo déficit.
A ponte troca uma hipótese por vez e vai às duas telas (Riscos e Laboratório).

Fica a fórmula de livro em Riscos: na história, o que a dívida andou além dela (o "resto")
foi de −3,8 a +4,5 pp do PIB por ano, sem sinal fixo; em 12 meses até set/2026, −0,1.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import pairwise

from sacibras import contas, relatorios
from sacibras.fontes import bcb_fiscal, bcb_focus
from sacibras.modelos import ajuste, risco
from sacibras.schema import LinhaTabela, Tabela
from sacibras.secoes.base import Contexto, br, periodo
from sacibras.tipos import Ponto

ANO = 2027
"""O ano do projeto da LDO a que a ponte chega."""


def juro_que_a_divida_paga(
    ctx: Contexto, dbgg: list[Ponto], juros_pib: list[Ponto]
) -> tuple[list[Ponto], bool]:
    """(a taxa implícita da DBGG em 12 meses, True); sem a planilha do BC, (juros de 12 meses
    do setor público ÷ dívida bruta, False). Fica no memo para quem mais usar."""
    if "taxa_implicita_dbgg" in ctx.memo:
        return ctx.memo["taxa_implicita_dbgg"], True
    try:
        oficial = bcb_fiscal.taxa_implicita_dbgg()
        ctx.memo["taxa_implicita_dbgg"] = oficial
        return oficial, True
    except Exception as erro:
        print(f"    riscos: sem a taxa implícita do BC, fica a conta nossa ({str(erro)[:100]})")
    estoque = dict(dbgg)
    return [(d, j / estoque[d] * 100) for d, j in juros_pib if estoque.get(d)], False


@dataclass(frozen=True)
class Hoje:
    quando: date
    divida: float
    juro: float
    crescimento: float
    primario: float
    """O primário que estabiliza, com os três acima."""


def hoje(ctx: Contexto) -> Hoje:
    """A conta de Riscos no último mês em que as três séries têm valor."""
    dbgg = ctx.sgs("DBGG", 25)
    juro, _ = juro_que_a_divida_paga(ctx, dbgg, ctx.sgs("NFSP_JUROS_12M", 25))
    cresce = contas.variacao(ctx.sgs("PIB_12M", 25), 12)
    d, j, g = dict(dbgg), dict(juro), dict(cresce)
    quando = max(x for x in d if x in j and x in g)
    return Hoje(
        quando,
        d[quando],
        j[quando],
        g[quando],
        risco.primario_que_estabiliza(d[quando], j[quando], g[quando]),
    )


def do_focus(ano: int = ANO) -> float | None:
    """O primário com que a dívida que o Focus espera para `ano` ficaria igual à do ano
    anterior: o primário esperado mais o quanto a dívida esperada sobe."""
    divida = bcb_focus.mediana_anual_hoje("Dívida bruta do governo geral")
    primario = bcb_focus.mediana_anual_hoje("Resultado primário")
    if ano not in divida or ano - 1 not in divida or ano not in primario:
        return None
    return round(primario[ano] + divida[ano] - divida[ano - 1], 2)


def ponte(ctx: Contexto) -> Tabela:
    h = hoje(ctx)
    proj = relatorios.PLDO_2027
    x, antes = proj[ANO], proj[ANO - 1]
    cresce = ajuste.nominal(x.pib, x.deflator)
    passos = [
        h.primario,
        risco.primario_que_estabiliza(h.divida, x.implicita, h.crescimento),
        risco.primario_que_estabiliza(h.divida, x.implicita, cresce),
        risco.primario_que_estabiliza(antes.divida, x.implicita, cresce),
    ]
    # Chega ao número que o governo publica (o gráfico do anexo). Pela tabela do mesmo
    # anexo, o primário do ano mais o quanto a dívida sobe daria 0,2 pp a mais: a diferença
    # fica na última linha, com as emissões que não são déficit.
    governo = relatorios.PLDO_2027_ESTABILIZA
    degraus = [round(passos[0], 1)] + [round(b - a, 1) for a, b in pairwise(passos)]
    resto = governo - sum(degraus)
    focus = do_focus()

    def linha(rotulo: str, valor: float, grupo: str = "") -> LinhaTabela:
        return LinhaTabela(
            rotulo=rotulo, valores=[round(valor, 1)], unidade="", casas=1, grupo=grupo
        )

    muda = "O que muda até a conta do governo (pp do PIB)"
    linhas = [
        linha(f"Com o juro e o PIB de hoje ({periodo(h.quando, 'M')})", degraus[0]),
        linha(
            f"Juro da dívida: de {br(h.juro)} % para {br(x.implicita)} %",
            degraus[1],
            muda,
        ),
        linha(
            f"PIB em reais: de {br(h.crescimento)} % para {br(cresce)} %",
            degraus[2],
            muda,
        ),
        linha(
            f"Dívida de partida: de {br(h.divida)} % para {br(antes.divida)} %",
            degraus[3],
            muda,
        ),
        linha("Emissões que não são déficit e outros ajustes", resto, muda),
        linha(f"Governo, para {ANO} (projeto da LDO)", governo, f"Para {ANO} (% do PIB)"),
    ]
    if focus is not None:
        linhas.append(linha(f"Focus, para {ANO}", focus, f"Para {ANO} (% do PIB)"))
    return Tabela(
        id="primario-estabiliza-ponte",
        titulo="Primário que estabiliza a dívida: de hoje ao que o governo supõe",
        subtitulo="% do PIB; a mesma conta, trocando uma hipótese por vez",
        colunas=["% ou pp do PIB"],
        linhas=linhas,
        fonte=(
            f"{bcb_fiscal.FONTE_TAXA}; {ctx.fonte_sgs('DBGG', 'PIB_12M')}; "
            f"{relatorios.FONTE_PLDO_2027}; Banco Central (Focus); conta nossa"
        ),
        nota="O projeto da LDO ainda não é lei.",
    )
