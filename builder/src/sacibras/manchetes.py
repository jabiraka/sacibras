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
ESCALAS = ("mil", "milhões", "bilhões", "trilhões", "mi", "bi", "tri")
ANOS_PARA_SER_RECORDE = 3
"""O maior (ou menor) nível só é dito se o anterior ficou a pelo menos tantos anos."""


def _numero(valor: float, casas: int) -> str:
    return br(valor, casas).replace("-", "−")


def _com_unidade(valor: float, unidade: str, casas: int, *, curta: bool = False) -> str:
    """ "83,0 % do PIB", "R$ 5,65", "US$ 74,3 bilhões", "171.324 pontos". A unidade vai sem o
    que vem depois de parêntese, vírgula ou " e "; com `curta`, o percentual fica só "%"."""
    u = unidade.split("(")[0].split(",")[0].split(";")[0].split(" e ")[0].strip()
    n = _numero(valor, casas)
    if u.startswith("%"):
        return f"{n} %" if curta else f"{n} {u}"
    if u in ("R$", "R$/US$"):
        return f"R$ {n}"
    if u.startswith(("R$ ", "US$ ")):
        moeda, resto = u.split(" ", 1)
        escala = resto.split()[0]
        return f"{moeda} {n} {escala}" if escala in ESCALAS else f"{moeda} {n}"
    if u.lower().startswith(("índice", "indice")) or "= 100" in u or not u:
        return n
    return n if curta else f"{n} {u}"


def _contra_a_faixa(
    g: Grafico, quando: date, valor: float, pontos: list[tuple[date, float]]
) -> str:
    """Com a faixa no gráfico (a da meta, ou outra): há quantos pontos seguidos a série está
    fora dela."""
    if not g.faixa or not g.unidade.startswith("%"):
        return ""  # só taxa contra a meta; o acumulado do ano em reais não se lê assim
    faixa = {d: (lo, hi) for d, lo, hi in g.faixa.pontos}
    if quando not in faixa:
        return ""
    lo, hi = faixa[quando]
    nome = g.faixa.nome.split("(")[0].strip().lower()
    e_meta = "meta" in nome
    if lo <= valor <= hi:
        return f"dentro do {nome}" if e_meta else f"dentro da {nome}"
    if e_meta:
        lado = "acima do teto da meta" if valor > hi else "abaixo do piso da meta"
    else:  # a faixa de outra coisa (a da regra de Taylor): diz-se o nome dela
        lado = f"{'acima' if valor > hi else 'abaixo'} da {nome}"
    seguidos = 0
    for d, v in reversed(pontos):
        if d not in faixa or not (v > faixa[d][1] if valor > hi else v < faixa[d][0]):
            break
        seguidos += 1
    unidade = {"M": "meses", "T": "trimestres", "A": "anos"}.get(g.periodicidade, "")
    ha = f" há {seguidos} {unidade}" if unidade and seguidos > 1 else ""
    return f"{lado}{ha}"


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
    anual = g.periodicidade == "A"
    if agora == antes:
        return "o mesmo do ano anterior" if anual else "o mesmo de um ano antes"
    lado = "acima" if agora > antes else "abaixo"
    era = _com_unidade(antes, g.unidade, g.casas, curta=True)
    return f"{lado} de {era} {'no ano anterior' if anual else 'um ano antes'}"


def do_grafico(g: Grafico) -> str:
    """A frase do gráfico, ou "" quando ele não é uma série no tempo com um dado de hoje."""
    if g.tipo not in ("linha", "area", "degrau") or g.eixo != "tempo":
        return ""
    if g.piramide or g.dispersao or g.marcas_y or not g.series:
        return ""
    principal = next((s for s in g.series if s.papel == "realizado"), None)
    if principal is None:
        return ""
    if principal.tracejado_desde:
        return ""  # a série segue em projeção: o "hoje" dela não é o último ponto
    pontos = [(d, v) for d, v in principal.pontos if v is not None]
    if len(pontos) < MINIMO_DE_PONTOS or pontos[-1][0] > date.today():
        return ""  # curta demais, ou um calendário que vai além de hoje (a transição da reforma)
    quando, valor = pontos[-1]
    leitura = (
        _contra_a_faixa(g, quando, valor, pontos) or _recorde(g, pontos) or _um_ano_antes(g, pontos)
    )
    realizadas = [s for s in g.series if s.papel == "realizado"]
    nome = f"{principal.nome}, " if len(realizadas) > 1 and len(principal.nome) <= 42 else ""
    frase = f"{nome}{periodo(quando, g.periodicidade)}: {_com_unidade(valor, g.unidade, g.casas)}"
    frase = frase[0].upper() + frase[1:]
    frase = f"{frase}, {leitura}" if leitura else frase
    return frase if frase.endswith(".") else f"{frase}."
