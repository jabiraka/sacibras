"""Transferências constitucionais da União (Tesouro Transparente): o FPE de cada estado e o FPM
dos municípios de cada estado, mês a mês.

Dois conjuntos no CKAN do Tesouro Transparente, conferidos em 15/11/2026:
`transferencias-constitucionais-para-estados` e `transferencias-constitucionais-para-municipios`.
Um CSV por mês (`Transferencia_Mensal_Estados_AAAAMM.csv`, ~30 KB;
`Transferencia_Mensal_Municipios_AAAAMM.csv`, 5 a 8 MB), latin-1, `;`, ponto decimal. O nome
do arquivo é o mês da publicação; o mês dos valores vem nas colunas ANO e Mês (o arquivo
202610 traz setembro de 2026). Valores em reais, por decêndio. O metadado diz: critério de
caixa, extraído do SIAFI; desde 2009 sai do FPE e do FPM o desconto de 20 % para o Fundeb, e o
que o arquivo chama de FPE e de FPM é o que chega ao ente já sem ele (o Fundeb volta por
outra linha, repartido pelo número de alunos).

Linhas usadas: "Item transferência" FPE com "Transferência" FPE (estados) e, nos municípios,
FPM/FPM e "FPM 1%"/"FPM 1%" (as parcelas extras de 1 % de julho, setembro e dezembro).
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date

from sacibras.rede import FonteForaDoArError, baixar, baixar_json

CKAN = "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show"
ESTADOS = "transferencias-constitucionais-para-estados"
MUNICIPIOS = "transferencias-constitucionais-para-municipios"
FONTE = "Tesouro Nacional, Transferências Constitucionais (Tesouro Transparente)"
NOME = re.compile(r"Transferencia_Mensal_(Estados|Municipios)_(\d{6})\.csv", re.I)
VALIDADE = 7 * 24 * 3600

PorUfMes = dict[str, dict[date, float]]
"""{sigla: {1º dia do mês: R$}}."""


def recursos(conjunto: str, meses: int) -> list[str]:
    """Os endereços dos `meses` arquivos mensais mais novos, do mais velho ao mais novo."""
    bruto = baixar_json(CKAN, params={"id": conjunto}, validade=24 * 3600)
    achados: dict[str, str] = {}
    for r in bruto["result"]["resources"]:
        m = NOME.fullmatch(str(r.get("name", "")).strip())
        if m:
            achados[m[2]] = str(r["url"])
    if not achados:
        raise FonteForaDoArError(f"Tesouro, {conjunto}: nenhum arquivo mensal no CKAN")
    return [achados[k] for k in sorted(achados)[-meses:]]


def _numero(texto: str) -> float:
    texto = texto.strip()
    return float(texto) if texto else 0.0


def ler_csv(conteudo: bytes, itens: set[tuple[str, str]]) -> PorUfMes:
    """Soma, por UF e mês, as linhas cujo (item, transferência) está em `itens`."""
    texto = conteudo.decode("latin-1")
    leitor = csv.reader(io.StringIO(texto), delimiter=";")
    cabecalho = [c.strip() for c in next(leitor)]

    def coluna(nome: str) -> int:
        for i, c in enumerate(cabecalho):
            if c.lower().startswith(nome.lower()):
                return i
        raise FonteForaDoArError(f"Tesouro, transferências: sem a coluna {nome!r}")

    uf, ano, mes = coluna("UF"), coluna("ANO"), coluna("Mês")
    decendios = [coluna(f"{n}º Decêndio") for n in (1, 2, 3)]
    item, transferencia = coluna("Item"), coluna("Transferência")
    saida: PorUfMes = {}
    for linha in leitor:
        if len(linha) <= max(item, transferencia):
            continue
        if (linha[item].strip(), linha[transferencia].strip()) not in itens:
            continue
        quando = date(int(linha[ano]), int(linha[mes]), 1)
        valor = sum(_numero(linha[i]) for i in decendios)
        por_mes = saida.setdefault(linha[uf].strip(), {})
        por_mes[quando] = por_mes.get(quando, 0.0) + valor
    return saida


def _juntar(partes: list[PorUfMes]) -> PorUfMes:
    saida: PorUfMes = {}
    for parte in partes:
        for uf, por_mes in parte.items():
            destino = saida.setdefault(uf, {})
            for d, v in por_mes.items():
                destino[d] = destino.get(d, 0.0) + v
    return saida


def fpe(meses: int = 12) -> PorUfMes:
    return _juntar(
        [
            ler_csv(baixar(url, validade=VALIDADE), {("FPE", "FPE")})
            for url in recursos(ESTADOS, meses)
        ]
    )


def fpm(meses: int = 12) -> PorUfMes:
    """O FPM dos municípios de cada estado (no DF, o de Brasília)."""
    return _juntar(
        [
            ler_csv(
                baixar(url, validade=VALIDADE, tempo_limite=180),
                {("FPM", "FPM"), ("FPM 1%", "FPM 1%")},
            )
            for url in recursos(MUNICIPIOS, meses)
        ]
    )


def doze_meses(por_uf: PorUfMes) -> tuple[dict[str, float], date]:
    """{sigla: soma dos 12 meses até o mês mais novo que todos têm} e esse mês."""
    if not por_uf:
        raise FonteForaDoArError("Tesouro, transferências: sem dados")
    ultimo = min(max(m) for m in por_uf.values() if m)
    inicio = date(ultimo.year - 1, ultimo.month, 1)
    return (
        {uf: sum(v for d, v in m.items() if inicio < d <= ultimo) for uf, m in por_uf.items()},
        ultimo,
    )
