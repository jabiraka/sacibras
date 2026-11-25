"""Sest (Ministério da Gestão): a planilha do anexo I do Relatório Agregado das Empresas
Estatais Federais, uma linha por empresa e ano, em reais.

O Caio pediu (25/11/2026) que o builder leia sozinho a edição mais nova quando ela sair. A
página da transparência das estatais lista a planilha de cada edição com o ano no nome
("...EstataisFederais2026anobase2025.xlsx"); o builder pega a de edição mais alta. Conferido em
25/11/2026: a edição 2026 reproduz os números lidos à mão em `relatorios.ESTATAIS_POR_ANO`
(dividendos à União, subvenção, aporte, lucro e prejuízos, de 2021 a 2025), a subvenção de cada
dependente e o lucro das maiores. Sai uma vez por ano, em junho.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

import openpyxl  # type: ignore[import-untyped]

from sacibras.rede import FonteForaDoArError, baixar
from sacibras.relatorios import EstataisNoAno

PAGINA = (
    "https://www.gov.br/gestao/pt-br/assuntos/estatais/transparencia/defeso_relatorio%20agregado"
)
FONTE = "Ministério da Gestão (Sest), Relatório Agregado das Empresas Estatais Federais"
VALIDADE = 24 * 3600

_PLANILHA = re.compile(r'href="([^"]*AnexoI[^"]*?(\d{4})anobase(\d{4})\.xlsx)"')

NOMES = {
    "EBSERH": "Ebserh (hospitais universitários)",
    "EMBRAPA": "Embrapa (pesquisa agropecuária)",
    "CONCEIÇÃO": "Grupo Hospitalar Conceição",
    "HCPA": "Hospital de Clínicas de Porto Alegre",
    "CODEVASF": "Codevasf (obras nos vales do São Francisco e do Parnaíba)",
    "CONAB": "Conab (abastecimento)",
    "CBTU": "CBTU (trens urbanos)",
    "CPRM": "CPRM (Serviço Geológico)",
    "EBC": "EBC (comunicação pública)",
    "AMAZUL": "Amazul (programa nuclear da Marinha)",
    "NUCLEP": "Nuclep (equipamentos pesados)",
    "TELEBRAS": "Telebras",
    "TRENSURB": "Trensurb (trens de Porto Alegre)",
    "INFRA S.A.": "Infra S.A. (ferrovias e projetos)",
    "IMBEL": "Imbel (material bélico)",
    "EPE": "EPE (pesquisa energética)",
    "CEITEC": "Ceitec (semicondutores)",
}
"""A abreviação da planilha e o nome com o que a empresa faz, para a tela."""

MAIORES = {
    "PETROBRAS (Grupo)": "Petrobras",
    "BNDES (Grupo)": "BNDES",
    "BB (Grupo)": "Banco do Brasil",
    "CAIXA (Grupo)": "Caixa",
    "ECT": "Correios",
}
"""As do quadro do lucro: as três que fazem quase todo o lucro, a Caixa e os Correios."""


@dataclass(frozen=True)
class Anexo:
    edicao: int
    ano_base: int
    url: str
    por_ano: dict[int, EstataisNoAno]
    subvencoes: list[tuple[str, float]]
    """(nome, R$ milhões) de cada dependente no ano-base, da maior para a menor."""
    lucros: list[tuple[str, float, float]]
    """(nome, R$ milhões no ano anterior, no ano-base), na ordem de `MAIORES`."""
    diretas: int
    dependentes: int

    @property
    def fonte(self) -> str:
        return f"{FONTE} {self.edicao}, ano-base {self.ano_base}, anexo I"


def planilha_mais_nova(html: str) -> tuple[int, int, str]:
    """(edição, ano-base, endereço) da planilha do anexo I de edição mais alta na página."""
    achadas = [(int(m.group(2)), int(m.group(3)), m.group(1)) for m in _PLANILHA.finditer(html)]
    if not achadas:
        raise FonteForaDoArError("Sest: a página não lista a planilha do anexo I")
    return max(achadas)


def ler(conteudo: bytes) -> list[dict[str, object]]:
    livro = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    linhas = list(livro.worksheets[0].iter_rows(values_only=True))
    cabeca = [str(c).strip() if c is not None else "" for c in linhas[0]]
    return [dict(zip(cabeca, linha, strict=False)) for linha in linhas[1:] if linha[0]]


def _num(linha: dict[str, object], coluna: str) -> float:
    valor = linha.get(coluna)
    return float(valor) / 1e6 if isinstance(valor, int | float) else 0.0


def montar(linhas: list[dict[str, object]], edicao: int, ano_base: int, url: str) -> Anexo:
    anos = sorted({int(str(x["ANO"])) for x in linhas})
    por_ano: dict[int, EstataisNoAno] = {}
    for ano in anos:
        do_ano = [x for x in linhas if int(str(x["ANO"])) == ano]
        resultado = [_num(x, "RESULTADO LÍQUIDO") for x in do_ano]
        por_ano[ano] = EstataisNoAno(
            lucro=round(sum(resultado), 1),
            dividendos_uniao=round(
                sum(_num(x, "DIVIDENDOS E JCP PAGOS À UNIÃO") for x in do_ano), 1
            ),
            subvencao=round(sum(_num(x, "SUBVENÇÃO") for x in do_ano), 1),
            aporte=round(sum(_num(x, "AFAC") for x in do_ano), 1),
            prejuizos=round(sum(v for v in resultado if v < 0), 1),
        )
    base = [x for x in linhas if int(str(x["ANO"])) == ano_base]
    antes = {str(x["ABREVIAÇÃO"]): x for x in linhas if int(str(x["ANO"])) == ano_base - 1}
    agora = {str(x["ABREVIAÇÃO"]): x for x in base}
    subvencoes = sorted(
        (
            (NOMES.get(str(x["ABREVIAÇÃO"]), str(x["ABREVIAÇÃO"])), round(_num(x, "SUBVENÇÃO"), 1))
            for x in base
            if _num(x, "SUBVENÇÃO") > 0
        ),
        key=lambda par: -par[1],
    )
    lucros = [
        (
            nome,
            round(_num(antes[sigla], "RESULTADO LÍQUIDO"), 1),
            round(_num(agora[sigla], "RESULTADO LÍQUIDO"), 1),
        )
        for sigla, nome in MAIORES.items()
        if sigla in antes and sigla in agora
    ]
    dependentes = sum(1 for x in base if x.get("DEPENDÊNCIA DO TESOURO NACIONAL") == "Dependente")
    return Anexo(edicao, ano_base, url, por_ano, subvencoes, lucros, len(base), dependentes)


def anexo() -> Anexo:
    """A planilha da edição mais nova, já somada."""
    html = baixar(PAGINA, validade=VALIDADE, tempo_limite=60).decode("utf-8", "replace")
    edicao, ano_base, url = planilha_mais_nova(html)
    linhas = ler(baixar(url, validade=VALIDADE, tempo_limite=120))
    saida = montar(linhas, edicao, ano_base, url)
    if ano_base not in saida.por_ano:
        raise FonteForaDoArError(f"Sest: a planilha {edicao} não traz o ano-base {ano_base}")
    return saida
