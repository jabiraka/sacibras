"""Os números de cada estatal federal, ano a ano: o Anexo I do Relatório Agregado da Sest.

Caio, 25/11/2026: *"Na aba das estatais, abra por estatal um dashboard com informações mais
relevantes, principalmente histórico de performance, receita ou prejuízo e outras métricas
relevantes para analisar empresas"*.

A planilha "Anexo I – Séries históricas" sai uma vez por ano, em junho, com o relatório
(Ministério da Gestão, Sest). Uma linha por empresa e ano, as 44 de controle direto da União,
valores em reais, desde 2021 na edição de 2026 (lida em 25/11/2026). O NOME DO ARQUIVO MUDA
a cada edição (`AnexoISrieshistricasRelatrioAgregado...2026anobase2025.xlsx`), então o
endereço se acha na página do relatório: o link do Anexo I com o ano-base mais novo.

Duas armadilhas da edição de 2026, achadas comparando 2025 com 2024 em todas as empresas:
- as colunas da demonstração do valor adicionado (pessoal, impostos, lucro retido e as do
  fim da planilha) de 2025 vêm em R$ mil, não em reais (mediana de 2025/2024 perto de
  0,001). `_corrigir_escala` acha isso sozinha e multiplica por mil;
- a remuneração média, a idade média e o tempo de serviço de 2024 e 2025 vêm vazios ou com
  outro número no lugar. Ficam de fora.
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

PAGINA = (
    "https://www.gov.br/gestao/pt-br/assuntos/estatais/transparencia/defeso_relatorio%20agregado"
)
# A edição lida em 25/11/2026, para quando a página não abrir.
RESERVA = (
    "https://www.gov.br/gestao/pt-br/assuntos/estatais/transparencia/"
    "AnexoISrieshistricasRelatrioAgregadodasEmpresasEstataisFederais2026anobase2025.xlsx"
)
PDF = (
    "https://www.gov.br/gestao/pt-br/assuntos/estatais/transparencia/"
    "RelatrioAgregadodasEmpresasEstataisFederais2026anobase202506181.pdf"
)
FONTE = "Ministério da Gestão (Sest), Relatório Agregado das Empresas Estatais Federais, anexo I"

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
}
TEXTOS = {"ano", "sigla", "nome", "setor", "ministerio", "dependencia", "criacao"}
NUMEROS = [c for c in COLUNAS.values() if c not in TEXTOS]
# As que vêm da demonstração do valor adicionado: as que já mudaram de escala.
DA_DVA = ("pessoal", "impostos")


def _normal(texto: object) -> str:
    sem = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem).strip().lower()


def _numero(v: Any) -> float | None:
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
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


def ler(conteudo: bytes) -> list[EstatalNoAno]:
    """As linhas da planilha, já com a escala corrigida."""
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
                valores={c: _numero(bruta[onde[c]]) for c in NUMEROS},
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
                if a and b and a > 0 and b > 0:
                    razoes.append(b / a)
            if len(razoes) >= 5 and statistics.median(razoes) < 0.01:
                for x in linhas:
                    v = x[campo]
                    if x.ano == ano and v is not None:
                        x.valores[campo] = v * 1000


def endereco() -> str:
    """O link do Anexo I mais novo na página do relatório; sem a página, o lido em 25/11."""
    try:
        html = baixar(PAGINA).decode("utf-8", "ignore")
    except Exception:
        return RESERVA
    links = re.findall(r'href="([^"]*AnexoI[^"I][^"]*\.xlsx)"', html)
    com_ano = [(int(m.group(1)), u) for u in links if (m := re.search(r"anobase(\d{4})", u))]
    return max(com_ano)[1] if com_ano else RESERVA


def estatais() -> list[EstatalNoAno]:
    url = endereco()
    if url != RESERVA:
        # O link na tela (`links.py`) aponta para RESERVA: edição nova pede trocar os dois.
        print(f"    aviso: edição nova do anexo I da Sest ({url}); atualize RESERVA e PDF")
    return ler(baixar(url))
