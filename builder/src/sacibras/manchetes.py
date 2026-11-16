"""O que o gráfico mostra hoje, em uma frase, escrita a partir do dado (Caio, 16/11/2026,
plano da fase 2: o título diz a conclusão, não só o nome da série).

Sem opinião e sem causa: o último valor, o período, e a comparação que o dado dá sozinho
(contra a meta, se há faixa; o maior ou o menor em anos; ou um ano antes). Vale para a
primeira série realizada dos gráficos de linha no tempo; nos outros (barras, curvas, um
ponto por país) fica em branco e a tela mostra só o título.
"""

from __future__ import annotations

from datetime import date, timedelta

from sacibras.schema import Grafico
from sacibras.secoes.base import br, periodo

MINIMO_DE_PONTOS = 8
ANOS_PARA_SER_RECORDE = 3
"""O maior (ou menor) nível só é dito se o anterior ficou a pelo menos tantos anos."""


def _com_unidade(valor: float, unidade: str, casas: int) -> str:
    """ "83,0 % do PIB", "R$ 5,65", "171.324 pontos"; a unidade sem o que vem entre parênteses."""
    curta = unidade.split("(")[0].split(",")[0].split(";")[0].strip()
    n = br(valor, casas)
    if curta.startswith("%"):
        return f"{n} {curta}"
    if curta in ("R$", "R$/US$"):
        return f"R$ {n}"
    if curta.startswith(("R$ ", "US$ ")):
        moeda, resto = curta.split(" ", 1)
        return f"{moeda} {n} {resto}"
    if curta.lower().startswith(("índice", "indice")) or not curta:
        return n
    return f"{n} {curta}"


def _contra_a_faixa(
    g: Grafico, quando: date, valor: float, pontos: list[tuple[date, float]]
) -> str:
    """Com a faixa da meta no gráfico: há quantos pontos seguidos a série está fora dela."""
    if not g.faixa:
        return ""
    faixa = {d: (lo, hi) for d, lo, hi in g.faixa.pontos}
    if quando not in faixa:
        return ""
    lo, hi = faixa[quando]
    lado = "acima do teto" if valor > hi else "abaixo do piso" if valor < lo else ""
    if not lado:
        return f"dentro do {g.faixa.nome.split('(')[0].strip().lower()}"
    seguidos = 0
    for d, v in reversed(pontos):
        if d not in faixa or not (v > faixa[d][1] if valor > hi else v < faixa[d][0]):
            break
        seguidos += 1
    unidade = {"M": "meses", "T": "trimestres", "A": "anos"}.get(g.periodicidade, "")
    ha = f" há {seguidos} {unidade}" if unidade and seguidos > 1 else ""
    return f"{lado} da meta{ha}"


def _recorde(g: Grafico, pontos: list[tuple[date, float]]) -> str:
    quando, valor = pontos[-1]
    antes = pontos[:-1]
    v = round(valor, g.casas)
    prazo = 365 * ANOS_PARA_SER_RECORDE
    for palavra in ("maior", "menor"):
        alem = [
            d
            for d, x in antes
            if (round(x, g.casas) >= v if palavra == "maior" else round(x, g.casas) <= v)
        ]
        if not alem:
            if (quando - antes[0][0]).days >= prazo:
                inicio = periodo(antes[0][0], g.periodicidade)
                return f"o {palavra} nível desde {inicio}, o início da série"
            continue
        if (quando - alem[-1]).days >= prazo:
            return f"o {palavra} nível desde {periodo(alem[-1], g.periodicidade)}"
    return ""


def _um_ano_antes(g: Grafico, pontos: list[tuple[date, float]]) -> str:
    quando, valor = pontos[-1]
    if g.periodicidade == "A":
        passados = pontos[:-1]
    else:
        alvo = quando - timedelta(days=350)
        passados = [(d, x) for d, x in pontos[:-1] if d <= alvo]
        if not passados or (alvo - passados[-1][0]).days > 100:
            return ""
    if not passados:
        return ""
    antes = round(passados[-1][1], g.casas)
    agora = round(valor, g.casas)
    quando_foi = "do ano anterior" if g.periodicidade == "A" else "de um ano antes"
    if agora == antes:
        return f"o mesmo {quando_foi}"
    lado = "acima" if agora > antes else "abaixo"
    return f"{lado} de {_com_unidade(antes, g.unidade, g.casas)}, o {quando_foi}"


def do_grafico(g: Grafico) -> str:
    """A frase do gráfico, ou "" quando ele não é uma série no tempo com um dado de hoje."""
    if g.tipo not in ("linha", "area", "degrau") or g.eixo != "tempo":
        return ""
    if g.piramide or g.dispersao or g.marcas_y or not g.series:
        return ""
    principal = next((s for s in g.series if s.papel == "realizado"), None)
    if principal is None:
        return ""
    limite = principal.tracejado_desde
    pontos = [
        (d, v) for d, v in principal.pontos if v is not None and (limite is None or d < limite)
    ]
    if len(pontos) < MINIMO_DE_PONTOS:
        return ""
    quando, valor = pontos[-1]
    leitura = (
        _contra_a_faixa(g, quando, valor, pontos) or _recorde(g, pontos) or _um_ano_antes(g, pontos)
    )
    realizadas = [s for s in g.series if s.papel == "realizado"]
    nome = f"{principal.nome}, " if len(realizadas) > 1 and len(principal.nome) <= 42 else ""
    frase = f"{nome}{periodo(quando, g.periodicidade)}: {_com_unidade(valor, g.unidade, g.casas)}"
    frase = frase[0].upper() + frase[1:]
    return f"{frase}, {leitura}." if leitura else f"{frase}."
