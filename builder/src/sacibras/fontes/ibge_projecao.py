"""Projeções da População do IBGE, revisão 2024: Brasil e UFs, ano a ano de 2000 a 2070.

Planilhas no FTP do IBGE (`ftp.ibge.gov.br/Projecao_da_Populacao/Projecao_da_Populacao_2024/`),
que responde de fora do Brasil (testado em 14/11/2026; a API `servicodados` não responde).
Lidas três, de 1 a 2 MB cada:

- `tab2_grupo_quinquenal`: população por sexo e grupo de cinco anos (a pirâmide). Uma linha por
  grupo × sexo × local, uma coluna por ano.
- `tab3_grupos_etarios_especificos`: população de 0-14, 15-64, 65+, 80+… Uma linha por ano ×
  local, uma coluna por indicador.
- `tab4_indicadores`: fecundidade (TFT), esperança de vida (e0, e60), nascimentos, óbitos,
  razões de dependência, idade mediana. Mesmo formato da tab3.

O relatório metodológico (3ª edição, lido em 14/11/2026) diz: cada ano tem referência em 1º de
julho; de 2000 a 2022 são dados ajustados pela conciliação com os Censos; daí em diante,
projeção com hipóteses de fecundidade, mortalidade e migração. As colunas se acham pelo nome
do cabeçalho, nunca pela posição.
"""

from __future__ import annotations

import io
from typing import Any

import openpyxl  # type: ignore[import-untyped]

from sacibras.rede import FonteForaDoArError, baixar

PASTA = "https://ftp.ibge.gov.br/Projecao_da_Populacao/Projecao_da_Populacao_2024"
ARQUIVOS = {
    "quinquenal": "projecoes_2024_tab2_grupo_quinquenal.xlsx",
    "grupos": "projecoes_2024_tab3_grupos_etarios_especificos.xlsx",
    "indicadores": "projecoes_2024_tab4_indicadores.xlsx",
}
ULTIMO_ANO_AJUSTADO = 2022
"""Até aqui, dado ajustado aos Censos; depois, projeção (relatório metodológico, cap. 1)."""
FONTE = "IBGE, Projeções da População, revisão 2024"

PorAno = dict[int, float]


class PlanilhaMudouError(FonteForaDoArError):
    """O IBGE trocou o formato da planilha: o cabeçalho esperado não está lá."""


def _linhas(conteudo: bytes) -> list[tuple[Any, ...]]:
    livro = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    try:
        return list(livro[livro.sheetnames[0]].iter_rows(values_only=True))
    finally:
        livro.close()


def _achar_cabecalho(linhas: list[tuple[Any, ...]], primeira: str) -> int:
    for i, linha in enumerate(linhas[:30]):
        if linha and isinstance(linha[0], str) and linha[0].strip().upper() == primeira:
            return i
    raise PlanilhaMudouError(f"projeção do IBGE: sem a linha de cabeçalho {primeira!r}")


def ler_por_ano(conteudo: bytes) -> dict[str, dict[str, PorAno]]:
    """tab3 e tab4: {sigla do local: {coluna: {ano: valor}}}. "BR" é o Brasil."""
    linhas = _linhas(conteudo)
    i = _achar_cabecalho(linhas, "ANO")
    cabecalho = [str(c).strip() if c is not None else "" for c in linhas[i]]
    if "SIGLA" not in cabecalho:
        raise PlanilhaMudouError("projeção do IBGE: sem a coluna SIGLA")
    col_sigla = cabecalho.index("SIGLA")
    saida: dict[str, dict[str, PorAno]] = {}
    for linha in linhas[i + 1 :]:
        if not linha or not isinstance(linha[0], (int, float)):
            continue
        ano, sigla = int(linha[0]), linha[col_sigla]
        if not isinstance(sigla, str):
            continue
        local = saida.setdefault(sigla.strip(), {})
        for j, nome in enumerate(cabecalho):
            if j <= col_sigla or not nome or j >= len(linha):
                continue
            valor = linha[j]
            if isinstance(valor, (int, float)):
                local.setdefault(nome, {})[ano] = float(valor)
    if "BR" not in saida:
        raise PlanilhaMudouError("projeção do IBGE: sem as linhas do Brasil (BR)")
    return saida


def ler_quinquenal_todos(conteudo: bytes) -> dict[str, dict[str, dict[str, PorAno]]]:
    """tab2 de todos os locais de uma vez: {sigla: {sexo: {grupo: {ano: pessoas}}}}. A planilha
    tem 1 a 2 MB; ler uma vez e separar por local é bem mais rápido que ler 28 vezes."""
    linhas = _linhas(conteudo)
    i = _achar_cabecalho(linhas, "GRUPO ETÁRIO")
    cabecalho = linhas[i]
    anos = [(j, int(c)) for j, c in enumerate(cabecalho) if isinstance(c, (int, float))]
    if not anos:
        raise PlanilhaMudouError("projeção do IBGE: sem os anos no cabeçalho da tab2")
    nomes = [str(c).strip().upper() if c is not None else "" for c in cabecalho]
    col_sexo, col_sigla = nomes.index("SEXO"), nomes.index("SIGLA")
    saida: dict[str, dict[str, dict[str, PorAno]]] = {}
    for linha in linhas[i + 1 :]:
        if not linha or not isinstance(linha[0], str) or not isinstance(linha[col_sigla], str):
            continue
        local = saida.setdefault(linha[col_sigla].strip(), {})
        grupo = linha[0].strip()
        sexo = str(linha[col_sexo]).strip()
        local.setdefault(sexo, {})[grupo] = {
            ano: float(linha[j]) for j, ano in anos if isinstance(linha[j], (int, float))
        }
    return saida


def ler_quinquenal(conteudo: bytes, sigla: str = "BR") -> dict[str, dict[str, PorAno]]:
    """tab2: {sexo ("Homens", "Mulheres", "Ambos"): {grupo ("00-04"… "90+"): {ano: pessoas}}},
    os grupos na ordem da planilha (do mais novo ao mais velho)."""
    saida = ler_quinquenal_todos(conteudo).get(sigla, {})
    if not {"Homens", "Mulheres"} <= set(saida):
        raise PlanilhaMudouError(f"projeção do IBGE: sem homens e mulheres de {sigla} na tab2")
    return saida


def _baixar(qual: str) -> bytes:
    # A projeção só muda com revisão nova (a anterior é de 2018): um mês de cache basta.
    return baixar(f"{PASTA}/{ARQUIVOS[qual]}", validade=30 * 24 * 3600, tempo_limite=120)


def indicadores() -> dict[str, dict[str, PorAno]]:
    return ler_por_ano(_baixar("indicadores"))


def grupos() -> dict[str, dict[str, PorAno]]:
    return ler_por_ano(_baixar("grupos"))


def quinquenal() -> dict[str, dict[str, PorAno]]:
    return ler_quinquenal(_baixar("quinquenal"))


def quinquenal_por_uf() -> dict[str, dict[str, dict[str, PorAno]]]:
    """A pirâmide de cada local ("BR" e as 27 siglas), lida da mesma planilha."""
    return ler_quinquenal_todos(_baixar("quinquenal"))
