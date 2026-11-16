"""Os assuntos que juntam mais de uma seção (Caio, 16/11/2026: de 13 assuntos para 9).

Cada seção antiga continua com a sua conta e as suas fontes, no módulo dela; aqui elas viram
um assunto só, com um arquivo e um endereço (`#trabalho` traz o que era `#pobreza`). O que
vai à tela é o que `organizacao.PARTES` lista para o assunto novo; o resto sai no `aplicar`.

Se uma das seções falha, o assunto sai com as outras e a falha entra em `rede.FALHAS`: o
`completar` do `construir.py` devolve da rodada anterior as peças que faltaram (valor nunca
em branco). Se todas falham, o assunto falha e fica o arquivo anterior.
"""

from __future__ import annotations

from collections.abc import Callable

from sacibras import rede
from sacibras.schema import Cartao, Grafico, Secao, Tabela
from sacibras.secoes import credito, demografia, externo, juros, mercados, pobreza, produtividade
from sacibras.secoes import trabalho as secao_trabalho
from sacibras.secoes.base import Contexto

Pecas = tuple[list[Cartao], list[Grafico], list[Tabela]]

ESCOLA = {
    "cartoes": {"anos-de-estudo", "analfabetismo"},
    "graficos": {"renda-escolaridade", "analfabetismo"},
    "tabelas": {"pobreza-escola-idade"},
}
"""O que sai da seção da pobreza para a parte "Escola" do Longo prazo."""

ANTIGOS = {
    "pobreza": "trabalho",
    "credito": "juros",
    "mercados": "externo",
    "demografia": "longo-prazo",
}
"""Endereço antigo → assunto novo: o site redireciona (`#pobreza/desigualdade` →
`#trabalho/desigualdade`)."""


def _juntar(
    ctx: Contexto,
    id: str,
    titulo: str,
    fontes: list[tuple[str, Callable[[], Secao | Pecas]]],
) -> Secao:
    """A primeira fonte é a principal: dá o resumo. As peças levam o assunto novo em `secao`."""
    junta: Secao | None = None
    cartoes: list[Cartao] = []
    graficos: list[Grafico] = []
    tabelas: list[Tabela] = []
    resumos: list[str] = []
    erros: list[str] = []
    for nome, montar in fontes:
        try:
            parte = montar()
        except Exception as erro:
            erros.append(f"{nome}: {str(erro)[:120]}")
            rede.FALHAS.append(f"seção {nome} (em {id})")
            print(f"  aviso: {id}: sem {nome} nesta rodada ({str(erro)[:120]})")
            continue
        if isinstance(parte, Secao):
            ctx.memo[f"{nome}_secao"] = parte
            c, g, t = parte.cartoes, parte.graficos, parte.tabelas
            if parte.resumo:
                resumos.append(parte.resumo)
            if junta is None:
                junta = parte.model_copy(deep=True)
            else:
                # O que só uma das seções tem (o simulador da Selic, o salário mínimo) vem junto.
                for campo in (
                    "simulador",
                    "simulador_selic",
                    "simulador_reforma",
                    "salario_minimo",
                ):
                    if getattr(junta, campo) is None and getattr(parte, campo) is not None:
                        setattr(junta, campo, getattr(parte, campo))
        else:
            c, g, t = parte
        cartoes += c
        graficos += g
        tabelas += t
    if junta is None:
        raise RuntimeError(f"{id}: nenhuma seção respondeu ({'; '.join(erros)})")
    junta.id, junta.titulo = id, titulo
    junta.resumo = " ".join(resumos[:2])
    junta.cartoes = [c.model_copy(update={"secao": id}) for c in cartoes]
    junta.graficos = graficos
    junta.tabelas = tabelas
    return junta


def trabalho(ctx: Contexto) -> Secao:
    return _juntar(
        ctx,
        "trabalho",
        "Trabalho e renda",
        [
            ("trabalho", lambda: secao_trabalho.montar(ctx)),
            ("pobreza", lambda: pobreza.montar(ctx)),
        ],
    )


def juros_e_credito(ctx: Contexto) -> Secao:
    return _juntar(
        ctx,
        "juros",
        "Juros e crédito",
        [("juros", lambda: juros.montar(ctx)), ("credito", lambda: credito.montar(ctx))],
    )


def exterior(ctx: Contexto) -> Secao:
    return _juntar(
        ctx,
        "externo",
        "Exterior e mercados",
        [("externo", lambda: externo.montar(ctx)), ("mercados", lambda: mercados.montar(ctx))],
    )


def _escola(ctx: Contexto) -> Pecas:
    """Os anos de estudo, o analfabetismo e a renda por escolaridade, da seção da pobreza."""
    secao: Secao = ctx.memo.get("pobreza_secao") or pobreza.montar(ctx)
    return (
        [c for c in secao.cartoes if c.id in ESCOLA["cartoes"]],
        [g for g in secao.graficos if g.id in ESCOLA["graficos"]],
        [t for t in secao.tabelas if t.id in ESCOLA["tabelas"]],
    )


def longo_prazo(ctx: Contexto) -> Secao:
    return _juntar(
        ctx,
        "longo-prazo",
        "Longo prazo",
        [
            ("demografia", lambda: demografia.montar(ctx)),
            ("produtividade", produtividade.pecas),
            ("escola", lambda: _escola(ctx)),
        ],
    )
