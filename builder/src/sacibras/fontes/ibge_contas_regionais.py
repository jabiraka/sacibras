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


def pib() -> tuple[int, dict[str, PorAno], dict[str, PorAno]]:
    """(ano da edição, PIB corrente em R$ milhões, volume encadeado 2010 = 100)."""
    ano = _ultima_edicao()
    for edicao in (ano, ano - 1):
        try:
            # Uma edição por ano: uma semana de cache basta.
            zipado = baixar(
                f"{PASTA}/{edicao}/xls/Especiais_2010_{edicao}_xls.zip",
                validade=7 * 24 * 3600,
                tempo_limite=120,
            )
        except FonteForaDoArError:
            continue  # a pasta pode aparecer antes do arquivo
        corrente, volume = ler_zip(zipado)
        return edicao, corrente, volume
    raise FonteForaDoArError(f"Contas Regionais: sem o zip das Especiais de {ano} nem {ano - 1}")
