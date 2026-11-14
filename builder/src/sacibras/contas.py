"""As contas que se repetem sobre séries: acumular, variar, somar em janela."""

from __future__ import annotations

from datetime import date

from sacibras.tipos import Ponto


def acumulado(pontos: list[Ponto], n: int = 12) -> list[Ponto]:
    """Taxas em % por período compostas em janelas de `n` períodos (ex.: % a.m. → % em 12 m)."""
    saida: list[Ponto] = []
    for i in range(n - 1, len(pontos)):
        fator = 1.0
        for _, v in pontos[i - n + 1 : i + 1]:
            fator *= 1 + v / 100
        saida.append((pontos[i][0], (fator - 1) * 100))
    return saida


def variacao(pontos: list[Ponto], defasagem: int = 12) -> list[Ponto]:
    """Variação % de um nível contra `defasagem` períodos antes."""
    return [
        (pontos[i][0], (pontos[i][1] / pontos[i - defasagem][1] - 1) * 100)
        for i in range(defasagem, len(pontos))
        if pontos[i - defasagem][1]
    ]


def diferenca(pontos: list[Ponto], defasagem: int = 1) -> list[Ponto]:
    return [
        (pontos[i][0], pontos[i][1] - pontos[i - defasagem][1])
        for i in range(defasagem, len(pontos))
    ]


def soma_movel(pontos: list[Ponto], n: int = 12) -> list[Ponto]:
    return [
        (pontos[i][0], sum(v for _, v in pontos[i - n + 1 : i + 1]))
        for i in range(n - 1, len(pontos))
    ]


def media_movel(pontos: list[Ponto], n: int = 3) -> list[Ponto]:
    return [(d, v / n) for d, v in soma_movel(pontos, n)]


def escalar(pontos: list[Ponto], fator: float) -> list[Ponto]:
    return [(d, v * fator) for d, v in pontos]


def media_das_series(series: list[list[Ponto]]) -> list[Ponto]:
    """A média, data a data, só onde todas as séries têm valor."""
    if not series:
        return []
    mapas = [dict(s) for s in series]
    datas = sorted(set(mapas[0]).intersection(*mapas[1:]))
    return [(d, sum(m[d] for m in mapas) / len(mapas)) for d in datas]


def subtrair(a: list[Ponto], b: list[Ponto]) -> list[Ponto]:
    mb = dict(b)
    return [(d, v - mb[d]) for d, v in a if d in mb]


def base_100(pontos: list[Ponto], em: date | None = None) -> list[Ponto]:
    """O nível reescrito com 100 na primeira data (ou em `em`)."""
    if not pontos:
        return []
    base = next((v for d, v in pontos if em is None or d >= em), pontos[0][1])
    return [(d, v / base * 100) for d, v in pontos]


def no_ano(pontos: list[Ponto]) -> float | None:
    """Variação % do último ponto contra o último ponto do ano anterior."""
    if not pontos:
        return None
    ultimo_dia, ultimo = pontos[-1]
    anteriores = [v for d, v in pontos if d.year < ultimo_dia.year]
    if not anteriores or not anteriores[-1]:
        return None
    return (ultimo / anteriores[-1] - 1) * 100


def em_dias(pontos: list[Ponto], dias: int) -> float | None:
    """Variação % do último ponto contra o ponto de `dias` corridos antes (ou o anterior a ele)."""
    if not pontos:
        return None
    ultimo_dia, ultimo = pontos[-1]
    alvo = ultimo_dia.toordinal() - dias
    antes = [v for d, v in pontos if d.toordinal() <= alvo]
    if not antes or not antes[-1]:
        return None
    return (ultimo / antes[-1] - 1) * 100


def anualizado(pontos: list[Ponto], n: int = 3, por_ano: int = 12) -> list[Ponto]:
    """Taxas em % por período compostas em janelas de `n` e levadas ao ano.

    ((∏(1 + m))^(por_ano / n) − 1): com n = 3 e mensais, o ritmo dos últimos três meses
    como se durasse um ano. Com n = 1, o mês anualizado."""
    return [(d, ((1 + v / 100) ** (por_ano / n) - 1) * 100) for d, v in acumulado(pontos, n)]
