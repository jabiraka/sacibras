"""Contas Regionais do IBGE: o PIB oficial das 27 UFs, ano a ano, desde 2010.

Planilhas no FTP do IBGE (`ftp.ibge.gov.br/Contas_Regionais/<ano>/xls/`), que responde de fora
do Brasil (testado em 14/11/2026). A edição de 2024 saiu em 13/11/2026; cada edição traz um
ano a mais, com dois anos de atraso. Lido o `Especiais_2010_<ano>_xls.zip` (~290 KB):

- `tab01.xls`: PIB a preços correntes, em R$ milhões ("1 000 000 R$").
- `tab03.xls`: série encadeada do volume do PIB (2010 = 100); a razão entre dois anos é o
  crescimento real, o mesmo que o IBGE divulga.

Uma linha por local (Brasil, as cinco regiões, recuadas com espaços, e as UFs), uma coluna por
ano. Os anos se acham na linha de cabeçalho e os locais pelo nome, nunca pela posição.
"""

from __future__ import annotations

import io
import re
import zipfile
from typing import Any

import xlrd  # type: ignore[import-untyped]

from sacibras.rede import FonteForaDoArError, baixar

PASTA = "https://ftp.ibge.gov.br/Contas_Regionais"
FONTE = "IBGE, Contas Regionais"

PorAno = dict[int, float]


class PlanilhaMudouError(FonteForaDoArError):
    """O IBGE trocou o formato: os anos ou os locais não estão onde se espera."""


def ler_tabela(conteudo: bytes) -> dict[str, PorAno]:
    """{nome do local, sem espaços nas pontas: {ano: valor}}."""
    livro = xlrd.open_workbook(file_contents=conteudo)
    folha = livro.sheet_by_index(0)
    anos: list[tuple[int, int]] = []
    for i in range(min(folha.nrows, 15)):
        linha = folha.row_values(i)
        candidatos = [
            (j, int(v))
            for j, v in enumerate(linha)
            if isinstance(v, float) and v.is_integer() and 2000 <= v <= 2100
        ]
        if len(candidatos) >= 5:
            anos, inicio = candidatos, i + 1
            break
    if not anos:
        raise PlanilhaMudouError("Contas Regionais: sem a linha dos anos")
    saida: dict[str, PorAno] = {}
    for i in range(inicio, folha.nrows):
        linha = folha.row_values(i)
        nome = linha[0]
        if not isinstance(nome, str) or not nome.strip() or nome.startswith("Fonte"):
            continue
        valores = {a: float(linha[j]) for j, a in anos if isinstance(linha[j], float)}
        if valores:
            saida[nome.strip()] = valores
    if "Brasil" not in saida or len(saida) < 30:
        raise PlanilhaMudouError(f"Contas Regionais: só {len(saida)} locais, sem o Brasil?")
    return saida


def _ultima_edicao() -> int:
    """O ano mais novo com pasta no FTP (a pasta só aparece com a edição publicada)."""
    pagina = baixar(f"{PASTA}/", validade=24 * 3600).decode("latin-1")
    anos = [int(a) for a in re.findall(r'href="(20\d\d)/"', pagina)]
    if not anos:
        raise PlanilhaMudouError("Contas Regionais: sem pastas de ano no FTP")
    return max(anos)


def ler_zip(conteudo: bytes) -> tuple[dict[str, PorAno], dict[str, PorAno]]:
    """(PIB corrente em R$ milhões, volume encadeado 2010 = 100) do zip das Especiais."""
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        nomes = {n.lower().rsplit("/", 1)[-1]: n for n in z.namelist()}
        if "tab01.xls" not in nomes or "tab03.xls" not in nomes:
            raise PlanilhaMudouError(f"Contas Regionais: o zip traz {sorted(nomes)}")
        return ler_tabela(z.read(nomes["tab01.xls"])), ler_tabela(z.read(nomes["tab03.xls"]))


def _zip() -> tuple[int, bytes]:
    """(ano da edição, o zip das Especiais) da edição mais nova que já tem o arquivo."""
    ano = _ultima_edicao()
    for edicao in (ano, ano - 1):
        try:
            # Uma edição por ano: uma semana de cache basta.
            return edicao, baixar(
                f"{PASTA}/{edicao}/xls/Especiais_2010_{edicao}_xls.zip",
                validade=7 * 24 * 3600,
                tempo_limite=120,
            )
        except FonteForaDoArError:
            continue  # a pasta pode aparecer antes do arquivo
    raise FonteForaDoArError(f"Contas Regionais: sem o zip das Especiais de {ano} nem {ano - 1}")


def pib() -> tuple[int, dict[str, PorAno], dict[str, PorAno]]:
    """(ano da edição, PIB corrente em R$ milhões, volume encadeado 2010 = 100)."""
    edicao, zipado = _zip()
    corrente, volume = ler_zip(zipado)
    return edicao, corrente, volume


# ---- Setores (lido em 15/11/2026, edição de 2024): no mesmo zip, a `tab04.xls` traz o valor
# adicionado bruto (VAB) a preços correntes, em R$ milhões, no mesmo desenho da `tab01`; a
# `tab07.xls` traz a participação de cada atividade no VAB, em %, uma aba por local ("Tabela7.1"
# é o Brasil, depois cada região seguida das suas UFs). Em cada aba: a linha dos anos, a linha
# com o nome do local (a de Santa Catarina vem "Santa catarina") e uma linha por atividade
# ("Agropecuária", "Indústria" e as quatro dela, "Serviços" e as sete dele), que somam 100.

Setores = dict[str, float]
"""{atividade: % do valor adicionado} de um ano."""


def ler_folha_de_participacao(linhas: list[list[Any]]) -> tuple[str, dict[int, Setores]]:
    """(nome do local, {ano: {atividade: %}}) de uma aba da `tab07`; ("", {}) se não é uma."""
    anos: list[tuple[int, int]] = []
    local = ""
    por_ano: dict[int, Setores] = {}
    for linha in linhas:
        if not anos:
            candidatos = [
                (j, int(v))
                for j, v in enumerate(linha)
                if isinstance(v, float) and v.is_integer() and 2000 <= v <= 2100
            ]
            if len(candidatos) >= 5:
                anos = candidatos
            continue
        nome = linha[0].strip() if isinstance(linha[0], str) else ""
        if not nome or nome.startswith("Fonte"):
            continue
        valores = {a: float(linha[j]) for j, a in anos if isinstance(linha[j], float)}
        if not valores and not local:
            local = nome
        elif valores:
            for a, v in valores.items():
                por_ano.setdefault(a, {})[nome] = v
    return (local, por_ano) if local and por_ano else ("", {})


def ler_participacoes(conteudo: bytes) -> dict[str, dict[int, Setores]]:
    """{nome do local: {ano: {atividade: %}}} da `tab07`, todas as abas."""
    livro = xlrd.open_workbook(file_contents=conteudo)
    saida: dict[str, dict[int, Setores]] = {}
    for folha in livro.sheets():
        local, por_ano = ler_folha_de_participacao(
            [folha.row_values(i) for i in range(folha.nrows)]
        )
        if local:
            saida[local] = por_ano
    if "Brasil" not in saida or len(saida) < 30:
        raise PlanilhaMudouError(f"Contas Regionais, tab07: só {len(saida)} locais")
    return saida


def setores() -> tuple[int, dict[str, PorAno], dict[str, dict[int, Setores]]]:
    """(ano da edição, VAB corrente em R$ milhões, participação de cada atividade no VAB)."""
    edicao, zipado = _zip()
    with zipfile.ZipFile(io.BytesIO(zipado)) as z:
        nomes = {n.lower().rsplit("/", 1)[-1]: n for n in z.namelist()}
        if "tab04.xls" not in nomes or "tab07.xls" not in nomes:
            raise PlanilhaMudouError(f"Contas Regionais: o zip traz {sorted(nomes)}")
        return (
            edicao,
            ler_tabela(z.read(nomes["tab04.xls"])),
            ler_participacoes(z.read(nomes["tab07.xls"])),
        )
