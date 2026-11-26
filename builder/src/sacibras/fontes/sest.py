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
import itertools
import re
import statistics
import unicodedata
from dataclasses import dataclass, field
from typing import Any

import openpyxl  # type: ignore[import-untyped]

from sacibras.rede import FonteForaDoArError, baixar
from sacibras.relatorios import EstataisNoAno

PAGINA = (
    "https://www.gov.br/gestao/pt-br/assuntos/estatais/transparencia/defeso_relatorio%20agregado"
)
FONTE = "Ministério da Gestão (Sest), Relatório Agregado das Empresas Estatais Federais"
# A planilha e o PDF da edição de 2026, abertos em 25/11/2026: são os links da tela
# (`links.py`). Edição nova muda os dois nomes; o build avisa (`empresas_da_mais_nova`).
RESERVA = (
    "https://www.gov.br/gestao/pt-br/assuntos/estatais/transparencia/"
    "AnexoISrieshistricasRelatrioAgregadodasEmpresasEstataisFederais2026anobase2025.xlsx"
)
PDF = (
    "https://www.gov.br/gestao/pt-br/assuntos/estatais/transparencia/"
    "RelatrioAgregadodasEmpresasEstataisFederais2026anobase202506181.pdf"
)
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


# ------------------------------------------------------------------ cada empresa, ano a ano
#
# Caio, 25/11/2026: *"Na aba das estatais, abra por estatal um dashboard com informações mais
# relevantes, principalmente histórico de performance, receita ou prejuízo e outras métricas
# relevantes para analisar empresas"*. As mesmas linhas da planilha, empresa por empresa, para
# a ficha de cada uma (`secoes/estatais.fichas`).
#
# Três armadilhas da edição de 2026, achadas comparando 2025 com 2024 em todas as empresas:
# - as colunas da demonstração do valor adicionado (pessoal, impostos e as do fim da planilha)
#   de 2025 vêm em R$ mil, não em reais (mediana de 2025/2024 perto de 0,001).
#   `_corrigir_escala` acha isso sozinha e multiplica por mil;
# - os custos da DVA de 2025 (insumos, despesas financeiras, retenções) vêm negativos, e antes
#   positivos: vão sempre positivos (`CUSTOS_DA_DVA`);
# - a remuneração média, a idade média e o tempo de serviço de 2024 e 2025 vêm vazios ou com
#   outro número no lugar. Ficam de fora.

# Cabeçalho normalizado (sem acento, minúsculas, espaços simples) -> campo.
COLUNAS = {
    "ano": "ano",
    "abreviacao": "sigla",
    "nome": "nome",
    "setor relatorio": "setor",
    "ministerio supervisor": "ministerio",
    "dependencia do tesouro nacional": "dependencia",
    "ano de criacao": "criacao",
    "ativo": "ativo",
    "passivo exigivel": "passivo",
    "patrimonio liquido": "patrimonio",
    "gasto com pessoal proprio": "pessoal",
    "impostos, taxas e contribuicoes": "impostos",
    "faturamento": "faturamento",
    "resultado liquido": "lucro",
    "dividendos e jcp pagos": "dividendos",
    "dividendos e jcp pagos a uniao": "dividendos_uniao",
    "subvencao": "subvencao",
    "afac": "afac",
    "receita da intermediacao financeira": "intermediacao",
    "receita da prestacao de servicos e tarifas": "tarifas",
    "orcamento investimento aprovado": "investimento_aprovado",
    "orcamento investimento executado": "investimento",
    "qtd_empregados": "empregados",
    # A demonstração do valor adicionado (DVA): de onde vem o dinheiro e para onde vai
    # (Caio, 26/11/2026: "Ver quais foram os maiores custos dela"). Fecha, empresa a empresa:
    # receitas + valor recebido = insumos + despesas financeiras + retenções + pessoal +
    # impostos + juros e aluguéis + resultado (conferido nos Correios, Petrobras, Ebserh e
    # Caixa, 2024 e 2025, em 26/11/2026; nos bancos sobra até 1 %).
    "receitas": "receitas_dva",
    "valor adicionado recebido": "recebido",
    "insumos adquiridos": "insumos",
    "despesas": "despesas_financeiras",
    "retencoes": "retencoes",
    "fornecedores e outros": "terceiros",
}
TEXTOS = {"ano", "sigla", "nome", "setor", "ministerio", "dependencia", "criacao"}
NUMEROS = [c for c in COLUNAS.values() if c not in TEXTOS]
# As que vêm da demonstração do valor adicionado: as que já mudaram de escala.
DA_DVA = (
    "pessoal",
    "impostos",
    "receitas_dva",
    "recebido",
    "insumos",
    "despesas_financeiras",
    "retencoes",
    "terceiros",
)
# Custos que a edição de 2026 traz com sinal negativo em 2025 e positivo antes: vão sempre
# positivos (são o que sai).
CUSTOS_DA_DVA = ("insumos", "despesas_financeiras", "retencoes")


def _normal(texto: object) -> str:
    sem = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem).strip().lower()


def _valor(campo: str, bruto: Any) -> float | None:
    v = _numero(bruto)
    return abs(v) if v is not None and campo in CUSTOS_DA_DVA else v


def _numero(v: Any) -> float | None:
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, int | float):
        return float(v)
    return None  # "-", "#N/A", ""


@dataclass
class EstatalNoAno:
    """Uma linha da planilha. Reais; None onde a Sest não traz o número."""

    ano: int
    sigla: str
    nome: str
    setor: str
    ministerio: str
    dependente: bool
    criacao: int | None
    valores: dict[str, float | None] = field(default_factory=dict)

    def __getitem__(self, campo: str) -> float | None:
        return self.valores.get(campo)


def empresas(conteudo: bytes) -> list[EstatalNoAno]:
    """As linhas da planilha, empresa por empresa, já com a escala corrigida."""
    livro = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    linhas = list(livro.worksheets[0].iter_rows(values_only=True))
    if not linhas:
        raise FonteForaDoArError("Sest: planilha vazia")
    cabecalho = [_normal(c) for c in linhas[0]]
    onde = {campo: cabecalho.index(nome) for nome, campo in COLUNAS.items() if nome in cabecalho}
    faltam = set(COLUNAS.values()) - set(onde)
    if faltam:
        raise FonteForaDoArError(f"Sest: colunas que sumiram: {sorted(faltam)}")
    saida: list[EstatalNoAno] = []
    for bruta in linhas[1:]:
        ano = bruta[onde["ano"]]
        if not isinstance(ano, int) or not bruta[onde["sigla"]]:
            continue
        criacao = bruta[onde["criacao"]]
        saida.append(
            EstatalNoAno(
                ano=ano,
                sigla=str(bruta[onde["sigla"]]).strip(),
                nome=str(bruta[onde["nome"]] or "").strip(),
                setor=str(bruta[onde["setor"]] or "").strip(),
                ministerio=str(bruta[onde["ministerio"]] or "").strip(),
                dependente=_normal(bruta[onde["dependencia"]]) == "dependente",
                criacao=criacao if isinstance(criacao, int) else None,
                valores={c: _valor(c, bruta[onde[c]]) for c in NUMEROS},
            )
        )
    _corrigir_escala(saida)
    return saida


def _corrigir_escala(linhas: list[EstatalNoAno]) -> None:
    """Ano em que uma coluna da DVA veio em R$ mil: a mediana do ano contra o anterior, nas
    mesmas empresas, fica perto de 1/1000. Aí o ano inteiro daquela coluna vai vezes mil."""
    por = {(x.ano, x.sigla): x for x in linhas}
    anos = sorted({x.ano for x in linhas})
    for campo in DA_DVA:
        for antes, ano in itertools.pairwise(anos):
            razoes = []
            for x in linhas:
                if x.ano != ano or (antes, x.sigla) not in por:
                    continue
                a, b = por[(antes, x.sigla)][campo], x[campo]
                if a and b:
                    razoes.append(abs(b / a))
            if len(razoes) >= 5 and statistics.median(razoes) < 0.01:
                for x in linhas:
                    v = x[campo]
                    if x.ano == ano and v is not None:
                        x.valores[campo] = v * 1000


def empresas_da_mais_nova() -> tuple[str, list[EstatalNoAno]]:
    """A fonte ("..., anexo I") e as linhas da planilha da edição mais nova."""
    html = baixar(PAGINA, validade=VALIDADE, tempo_limite=60).decode("utf-8", "replace")
    edicao, ano_base, url = planilha_mais_nova(html)
    if url != RESERVA:
        print(f"    aviso: edição nova do anexo I da Sest ({url}); atualize RESERVA e PDF")
    linhas = empresas(baixar(url, validade=VALIDADE, tempo_limite=120))
    return f"{FONTE} {edicao}, ano-base {ano_base}, anexo I", linhas
