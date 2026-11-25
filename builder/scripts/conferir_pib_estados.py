"""Confere o PIB trimestral por estado (conta nossa) contra o que cinco estados publicam.

Uso, de dentro de `builder/`:

    uv run python scripts/conferir_pib_estados.py [--mg anexo_pib_trimestral.xlsx]

O script acha sozinho, na página de cada órgão, a planilha mais nova de RS (DEE), PR
(IPARDES), BA (SEI) e ES (IJSN), e a baixa (Caio, 25/11/2026: ler sozinho a edição mais nova
onde a fonte publica em planilha). O nome muda a cada trimestre ("serie-historica-2026-ii.xlsx",
"serie_encadeada_2o_trim_2026.xlsx"): vale o ano e o trimestre do nome; a da Bahia, a da pasta
mais nova; a do ES tem nome fixo. MG (Fundação João Pinheiro) publica numa planilha do Google
que não abre da nuvem: baixe-a à mão e passe com `--mg`; sem ela, a conferência sai com os
quatro e diz isso. Qualquer estado aceita o arquivo à mão (`--rs`, `--pr`, `--ba`, `--es`), para
quando a página recusa (o IPARDES às vezes responde com uma verificação de robô).

Depois chama as mesmas fontes do builder (Contas Regionais, PIB trimestral do Brasil e IBC-R),
refaz a estimativa e imprime, por estado e no conjunto, a diferença do crescimento contra o
mesmo trimestre do ano anterior (nossa conta menos a do órgão estadual). O resultado do
conjunto vai, à mão, para `relatorios.CONFERENCIA_PIB_ESTADOS` (com os estados que entraram),
e a data para `leituras.py`.
"""

from __future__ import annotations

import argparse
import html
import io
import re
from pathlib import Path
from urllib.parse import urljoin

import openpyxl
import xlrd  # type: ignore[import-untyped]

from sacibras.fontes import ibge_contas_regionais, ibge_sidra
from sacibras.rede import baixar
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

# A página de cada órgão e o link da planilha; `ano` e `sub` (trimestre ou mês da pasta)
# escolhem a mais nova. Conferidas em 25/11/2026.
PAGINAS = {
    "RS": (
        "https://dee.rs.gov.br/pib-trimestral",
        r'href="([^"]*serie-historica-(?P<ano>\d{4})-(?P<sub>iv|iii|ii|i)\.xlsx)"',
    ),
    "PR": (
        "https://www.ipardes.pr.gov.br/Pagina/PIB-Trimestral-do-Parana",
        r'href="([^"]*serie_encadeada_(?P<sub>\d)o_trim_(?P<ano>\d{4})\.xlsx)"',
    ),
    "BA": (
        "https://www.ba.gov.br/sei/pib-estadual-trimestral-0",
        r'href="([^"]*/(?P<ano>\d{4})-(?P<sub>\d\d)/pib_trimestral_tabelas_completas\.xlsx?)"',
    ),
    "ES": (
        "https://ijsn.es.gov.br/publicacoes/boletins/pib-trimestral",
        r'href="([^"]*PIB%20Trimestral%20%28dados%20em%20Excel%29[^"]*\.xlsx[^"]*)"',
    ),
}


def planilha_mais_nova(pagina: str, padrao: str, corpo: str) -> str:
    """O endereço da planilha mais nova que a página lista (a primeira, se o nome não tem
    ano)."""
    achados = []
    for m in re.finditer(padrao, corpo, re.IGNORECASE):
        grupos = m.groupdict()
        sub = str(grupos.get("sub") or "0").upper()
        chave = (int(grupos.get("ano") or 0), ROMANOS.get(sub) or int(sub))
        achados.append((chave, urljoin(pagina, html.unescape(m.group(1)))))
    if not achados:
        raise RuntimeError(f"a página {pagina} não lista a planilha")
    return max(achados, key=lambda x: x[0])[1]


def linhas_da_aba(conteudo: bytes, aba: str) -> list[list[object]]:
    """As linhas da aba, em .xlsx ou no .xls antigo (o da Bahia)."""
    if conteudo[:2] == b"PK":
        livro = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
        return [list(x) for x in livro[aba].iter_rows(values_only=True)]
    folha = xlrd.open_workbook(file_contents=conteudo).sheet_by_name(aba)
    return [[c if c != "" else None for c in folha.row_values(r)] for r in range(folha.nrows)]


def ler(linhas: list[list[object]], coluna: int, indice: bool) -> dict[Tri, float]:
    """{(ano, trimestre): crescimento contra o mesmo trimestre do ano anterior, em %}."""
    valores: dict[Tri, float] = {}
    for linha in linhas:
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


def oficial(uf: str, arquivo: Path | None) -> tuple[dict[Tri, float], str]:
    """A série do órgão estadual e de onde veio (o arquivo dado ou o endereço baixado)."""
    aba, coluna, indice = ONDE[uf]
    if arquivo is not None:
        return ler(linhas_da_aba(arquivo.read_bytes(), aba), coluna, indice), str(arquivo)
    pagina, padrao = PAGINAS[uf]
    corpo = baixar(pagina, validade=0, tempo_limite=60).decode("utf-8", "replace")
    url = planilha_mais_nova(pagina, padrao, corpo)
    conteudo = baixar(url, validade=0, tempo_limite=120)
    return ler(linhas_da_aba(conteudo, aba), coluna, indice), url


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
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    for uf in ONDE:
        parser.add_argument(f"--{uf.lower()}", type=Path, help=f"planilha de {uf} já baixada")
    args = parser.parse_args()
    series: dict[str, dict[Tri, float]] = {}
    for uf in ONDE:
        arquivo = getattr(args, uf.lower())
        if uf not in PAGINAS and arquivo is None:
            print(f"{uf}: fica de fora (a planilha não abre da nuvem; passe --{uf.lower()})")
            continue
        try:
            series[uf], origem = oficial(uf, arquivo)
            print(f"{uf}: {origem}")
        except Exception as erro:
            print(f"{uf}: fica de fora ({str(erro)[:160]}; passe --{uf.lower()})")
    estimativa = nossa()
    todas: list[float] = []
    for uf, serie in series.items():
        comuns = sorted(t for t in serie if t in estimativa[uf] and t[0] >= 2011)
        dif = [estimativa[uf][t] - serie[t] for t in comuns]
        todas += dif
        print(
            f"{uf}: {len(dif)} trimestres, de {comuns[0]} a {comuns[-1]}; diferença média "
            f"{sum(abs(d) for d in dif) / len(dif):.2f} pp; viés {sum(dif) / len(dif):+.2f}"
        )
    print(
        f"Os {len(series)} ({', '.join(series)}): {len(todas)} trimestres; diferença média "
        f"{sum(abs(d) for d in todas) / len(todas):.2f} pp; 8 em 10 entre "
        f"{quantil(todas, 0.1):+.2f} e {quantil(todas, 0.9):+.2f}"
    )


if __name__ == "__main__":
    main()
