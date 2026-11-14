"""Grandes Números do IRPF, da Receita Federal: as declarações por faixa de renda.

Uma planilha por ano-calendário (~20 MB), na página de estudos do Imposto de Renda. O nome
muda a cada ano (e já veio com "-1" no fim), então o endereço se acha na listagem; baixa-se
com `/@@download/file` no lugar de `/view`. Lido em 14/11/2026: a mais nova é a do
ano-calendário 2024 (declarações entregues em 2025).

Aba `Tab8`: "Resumo das declarações por tipo de formulário, UF e faixa de rendimentos totais
em salários mínimos", em reais. Título na linha 1, cabeçalho na linha 2, uma linha por tipo
de formulário × UF × faixa: soma-se tudo por faixa. Célula com "x" é sigilo fiscal (poucas
declarações): conta como zero. As colunas se acham pelo nome, nunca pela posição.

O que o arquivo NÃO traz: o imposto retido na fonte sobre os rendimentos de tributação
exclusiva (13º, aplicações, ganho de capital, participação nos lucros). O "imposto devido
total" é só o da tabela progressiva mais o de rendimentos recebidos acumuladamente; a renda,
no denominador, inclui tudo. No topo, onde a tributação exclusiva pesa, a alíquota sai
menor do que a pessoa de fato pagou.
"""

from __future__ import annotations

import io
import re
import warnings
from dataclasses import dataclass

import openpyxl  # type: ignore[import-untyped]

from sacibras.rede import FonteForaDoArError, baixar

LISTAGEM = (
    "https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/estudos/"
    "imposto-de-renda/estudos-por-ano/grandes-numeros-do-IRPF-2008-a-2025"
)
FONTE = "Receita Federal, Grandes Números do IRPF"
PADRAO = re.compile(
    r'href="(?P<url>[^"]*/grandes-numeros-do-irpf-\d{4}-ano-calendario-(?P<ac>\d{4})-tabelas'
    r'[^"/]*)/view"'
)
ABA = "Tab8"
COLUNAS = {
    "faixa": "faixa_de_rendim_tributavel_mais_trib_exclusiva_mais_isentos_em_sal_minimos",
    "declarantes": "qtde_contribuintes",
    "tributavel": "rendimento_tributavel_total",
    "exclusiva": "rend_sujeitos_a_tribut_exclusiva",
    "isentos": "rend_isentos_e_nao_tributaveis",
    "dividendos": "rend_isentos_lucros_dividendos",
    "imposto": "imposto_devido_total",
}


@dataclass
class Faixa:
    nome: str
    """Como a Receita escreve: "De 3 a 5", "Mais de 320" (em salários mínimos)."""
    declarantes: float = 0.0
    tributavel: float = 0.0
    exclusiva: float = 0.0
    isentos: float = 0.0
    dividendos: float = 0.0
    imposto: float = 0.0

    @property
    def renda(self) -> float:
        return self.tributavel + self.exclusiva + self.isentos

    @property
    def aliquota(self) -> float:
        """Imposto devido na declaração em % da renda total."""
        return self.imposto / self.renda * 100 if self.renda else 0.0


def mais_nova(html: str) -> tuple[int, str]:
    """(ano-calendário, endereço de download) da planilha mais nova da listagem."""
    achadas = {int(m["ac"]): m["url"] + "/@@download/file" for m in PADRAO.finditer(html)}
    if not achadas:
        raise FonteForaDoArError("IRPF: nenhuma planilha de Grandes Números na listagem")
    ano = max(achadas)
    return ano, achadas[ano]


def ler_planilha(conteudo: bytes) -> list[Faixa]:
    """As faixas, da menor renda para a maior (o arquivo vem em ordem alfabética)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        livro = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    try:
        if ABA not in livro.sheetnames:
            raise FonteForaDoArError(f"IRPF: sem a aba {ABA}")
        linhas = livro[ABA].iter_rows(values_only=True)
        next(linhas, None)  # o título
        cabecalho = [str(c).strip() if c is not None else "" for c in next(linhas, ())]
        faltam = [n for n in COLUNAS.values() if n not in cabecalho]
        if faltam:
            raise FonteForaDoArError(f"IRPF, aba {ABA}: colunas que sumiram: {faltam}")
        onde = {campo: cabecalho.index(nome) for campo, nome in COLUNAS.items()}
        faixas: dict[str, Faixa] = {}
        for linha in linhas:
            nome = linha[onde["faixa"]] if len(linha) > onde["faixa"] else None
            if not isinstance(nome, str) or not nome.strip():
                continue
            faixa = faixas.setdefault(nome.strip(), Faixa(nome.strip()))
            for campo, i in onde.items():
                if campo == "faixa":
                    continue
                valor = linha[i] if i < len(linha) else None
                if isinstance(valor, (int, float)):
                    setattr(faixa, campo, getattr(faixa, campo) + float(valor))
    finally:
        livro.close()
    if len(faixas) < 5:
        raise FonteForaDoArError(f"IRPF, aba {ABA}: só {len(faixas)} faixas")
    return sorted(faixas.values(), key=lambda f: piso(f.nome))


def piso(nome: str) -> float:
    """Onde a faixa começa, em salários mínimos, para pôr em ordem: "De 1/2 a 1" -> 0,5;
    "Até 1/2" -> 0; "Mais de 320" -> 320,5."""
    achado = re.search(r"(\d+)(?:/(\d+))?", nome)
    if not achado or nome.lower().startswith("até"):
        return 0.0
    valor = int(achado[1]) / int(achado[2] or 1)
    return valor + 0.5 if nome.lower().startswith("mais") else valor


def grandes_numeros() -> tuple[int, list[Faixa]]:
    """(ano-calendário, faixas) da planilha mais nova."""
    html = baixar(LISTAGEM, validade=24 * 3600).decode("utf-8", "replace")
    ano, url = mais_nova(html)
    return ano, ler_planilha(baixar(url, validade=30 * 24 * 3600, tempo_limite=300))
