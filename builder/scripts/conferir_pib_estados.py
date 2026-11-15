"""Confere o PIB trimestral por estado (conta nossa) contra o que cinco estados publicam.

Uso, de dentro de `builder/` (baixe antes as cinco planilhas; os endereços estão no comentário
de `relatorios.CONFERENCIA_PIB_ESTADOS` e mudam de nome a cada trimestre):

    uv run python scripts/conferir_pib_estados.py \\
        --rs serie-historica-2026-ii.xlsx --pr serie_encadeada_2o_trim_2026.xlsx \\
        --mg anexo_pib_trimestral.xlsx --ba pib_trimestral_tabelas_completas.xlsx \\
        --es pib_trimestral_dados_em_excel.xlsx

A planilha da Bahia vem em `.xls` antigo: salve como `.xlsx` antes. O script chama as mesmas
fontes do builder (Contas Regionais, PIB trimestral do Brasil e IBC-R), refaz a estimativa e
imprime, por estado e no conjunto, a diferença do crescimento contra o mesmo trimestre do ano
anterior (nossa conta menos a do órgão estadual). O resultado do conjunto vai, à mão, para
`relatorios.CONFERENCIA_PIB_ESTADOS`, e a data para `leituras.py`.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import openpyxl

from sacibras.fontes import ibge_contas_regionais, ibge_sidra
from sacibras.secoes import estados, estados_economia
from sacibras.secoes.base import Contexto

ROMANOS = {"I": 1, "II": 2, "III": 3, "IV": 4}
Tri = tuple[int, int]

# (aba, coluna do PIB entre os números da linha, se é índice ou já é a taxa em um ano)
ONDE = {
    "RS": ("Série encadeada", -1, True),
    "PR": ("Série Encadeada", -1, True),
    "MG": ("Série Encadeada", -1, True),
    "BA": ("Base Móvel", -1, True),
    "ES": ("Planilha4", 3, False),
}


def ler(arquivo: Path, aba: str, coluna: int, indice: bool) -> dict[Tri, float]:
    """{(ano, trimestre): crescimento contra o mesmo trimestre do ano anterior, em %}."""
    folha = openpyxl.load_workbook(arquivo, read_only=True, data_only=True)[aba]
    valores: dict[Tri, float] = {}
    for linha in folha.iter_rows(values_only=True):
        celulas = [c for c in linha if c is not None]
        if not celulas or not isinstance(celulas[0], str):
            continue
        achado = re.match(r"\s*(\d{4})\.(IV|III|II|I)\b", celulas[0])
        numeros = [c for c in celulas[1:] if isinstance(c, int | float)]
        if achado and len(numeros) > abs(coluna):
            valores[(int(achado.group(1)), ROMANOS[achado.group(2)])] = float(numeros[coluna])
    if not indice:
        return valores
    return {
        (a, q): (v / valores[(a - 1, q)] - 1) * 100
        for (a, q), v in valores.items()
        if (a - 1, q) in valores
    }


def nossa() -> dict[str, dict[Tri, float]]:
    """{UF: {(ano, trimestre): crescimento estimado}}, com as fontes de agora."""
    ctx = Contexto()
    edicao, corrente, volume = ibge_contas_regionais.pib()
    tabela, variavel, classificacao = estados_economia.PIB_TRIMESTRAL
    pib = ibge_sidra.serie(tabela, variavel, classificacao=classificacao, trimestral=True)
    metrica = estados_economia.pib_trimestral(
        estados.UFS, lambda k: ctx.sgs(k, 24), pib, edicao, corrente, volume
    )[0]
    saida: dict[str, dict[Tri, float]] = {}
    for p in metrica.periodos:
        achado = re.match(r"(\d)º tri/(\d{4})", p.referencia)
        assert achado, p.referencia
        for uf, v in p.valores.items():
            if v is not None:
                saida.setdefault(uf, {})[(int(achado.group(2)), int(achado.group(1)))] = v
    return saida


def quantil(valores: list[float], p: float) -> float:
    ordenados = sorted(valores)
    i = p * (len(ordenados) - 1)
    baixo, alto = int(i), min(int(i) + 1, len(ordenados) - 1)
    return ordenados[baixo] + (ordenados[alto] - ordenados[baixo]) * (i - baixo)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for uf in ONDE:
        parser.add_argument(f"--{uf.lower()}", type=Path, required=True)
    args = parser.parse_args()
    estimativa = nossa()
    todas: list[float] = []
    for uf, (aba, coluna, indice) in ONDE.items():
        oficial = ler(getattr(args, uf.lower()), aba, coluna, indice)
        comuns = sorted(t for t in oficial if t in estimativa[uf])
        dif = [estimativa[uf][t] - oficial[t] for t in comuns]
        todas += dif
        print(
            f"{uf}: {len(dif)} trimestres, de {comuns[0]} a {comuns[-1]}; diferença média "
            f"{sum(abs(d) for d in dif) / len(dif):.2f} pp; viés {sum(dif) / len(dif):+.2f}"
        )
    print(
        f"Os cinco: {len(todas)} trimestres; diferença média "
        f"{sum(abs(d) for d in todas) / len(todas):.2f} pp; 8 em 10 entre "
        f"{quantil(todas, 0.1):+.2f} e {quantil(todas, 0.9):+.2f}"
    )


if __name__ == "__main__":
    main()
