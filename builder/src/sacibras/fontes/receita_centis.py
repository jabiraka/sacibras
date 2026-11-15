"""Distribuição da Renda por Centis, da Receita Federal: as declarações do IRPF em cem grupos
do mesmo tamanho, da menor renda para a maior, com o patrimônio declarado de cada grupo.

Uma publicação por ano-calendário, desde 2017 neste formato (o "estudo ampliado"), na página
de estudos da Receita (`…/publicacoes/estudos/distribuicao-da-renda`). Lido em 15/11/2026: a
mais nova é a do ano-calendário 2024 (março de 2026). A pasta tem o nome
"…-estudo-ampliado-2017-a-2023" mas já guarda 2024: acha-se a pasta, depois a subpasta do ano
mais novo, depois o arquivo do Brasil (`centis-br-ac2024.xlsx`); baixa-se com
`/@@download/file` no lugar de `/view`.

O arquivo tem onze abas, uma para cada jeito de pôr as pessoas em fila. Usada a `BRV`
(Tabela V): fila pela RB4, que é a renda tributável mais a isenta mais a de tributação
exclusiva, menos doações e heranças (o metadado diz: "RB4 = Renda Tributável Bruta +
Rendimentos Isentos + Rendimentos Sujeitos à Tributação Exclusiva/Definitiva - Transferências
Patrimoniais"). Linhas 1 a 100: os centis; 101 a 110: o centil 100 aberto em dez (cada um, 0,1
% de quem declara); 111 a 120: o último desses aberto em dez (0,01 %). Cabeçalho em duas
linhas (grupo e coluna): as colunas se acham pelo nome, nunca pela posição. Anos anteriores
(2017 a 2021) vêm em arquivo de outro formato e não são lidos.
"""

from __future__ import annotations

import io
import re
import warnings
from dataclasses import dataclass
from functools import cache
from typing import Any

import openpyxl  # type: ignore[import-untyped]

from sacibras.rede import FonteForaDoArError, baixar

LISTAGEM = (
    "https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/estudos/"
    "distribuicao-da-renda"
)
FONTE = "Receita Federal, Distribuição da Renda por Centis"
PASTA = re.compile(r'href="(?P<url>[^"]*/distribuicao-de-renda-por-centis-estudo-ampliado[^"/]*)"')
ARQUIVO = re.compile(r'href="(?P<url>[^"]*/centis-br[-_]ac(?P<ano>\d{4})[^"/]*\.xlsx)/view"')
ABA = "BRV"
COLUNAS = {
    "declarantes": "Quantidade de Contribuintes",
    "renda": "Soma de RB4 do Centil",
    "dividendos": "Lucros e dividendos",
    "imposto": "Imposto Devido",
    "bens": "Total Bens e Direitos",
    "dividas": "Dívidas e Ônus",
}


@dataclass
class Centil:
    numero: int
    """1 a 100; 101 a 110 abrem o 100 em milésimos; 111 a 120 abrem o 110."""
    declarantes: float = 0.0
    renda: float = 0.0
    dividendos: float = 0.0
    imposto: float = 0.0
    bens: float = 0.0
    dividas: float = 0.0


def _limpo(texto: Any) -> str:
    return re.sub(r"\s+", " ", str(texto or "")).strip().lower()


def anos_da_listagem(html: str) -> dict[int, str]:
    """{ano: endereço da subpasta} na página da pasta do estudo ampliado."""
    achados = re.findall(r'href="([^"]*/(\d{4}))/?"', html)
    return {int(ano): url for url, ano in achados}


def colunas(cabecalho1: tuple[Any, ...], cabecalho2: tuple[Any, ...]) -> dict[str, int]:
    """Onde está cada coluna: o nome pode estar na linha de cima (grupo sem subcoluna, como
    "Imposto Devido") ou na de baixo."""
    onde: dict[str, int] = {}
    for campo, nome in COLUNAS.items():
        alvo = _limpo(nome)
        for i in range(max(len(cabecalho1), len(cabecalho2))):
            em_cima = _limpo(cabecalho1[i] if i < len(cabecalho1) else "")
            embaixo = _limpo(cabecalho2[i] if i < len(cabecalho2) else "")
            if embaixo == alvo or (em_cima.replace(" ", "") == alvo.replace(" ", "")):
                onde[campo] = i
                break
    faltam = [COLUNAS[c] for c in COLUNAS if c not in onde]
    if faltam:
        raise FonteForaDoArError(f"centis do IRPF: colunas que sumiram: {faltam}")
    return onde


def ler_planilha(conteudo: bytes) -> list[Centil]:
    """Os 120 centis da aba BRV, na ordem do arquivo."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        livro = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    try:
        if ABA not in livro.sheetnames:
            raise FonteForaDoArError(f"centis do IRPF: sem a aba {ABA}")
        linhas = list(livro[ABA].iter_rows(values_only=True))
    finally:
        livro.close()
    topo = next(
        (i for i, li in enumerate(linhas[:20]) if any(_limpo(c) == "centil" for c in li)), None
    )
    if topo is None:
        raise FonteForaDoArError("centis do IRPF: sem a linha de cabeçalho")
    onde = colunas(linhas[topo], linhas[topo + 1])
    col_centil = next(i for i, c in enumerate(linhas[topo]) if _limpo(c) == "centil")
    centis: list[Centil] = []
    for linha in linhas[topo + 2 :]:
        numero = linha[col_centil] if col_centil < len(linha) else None
        if not isinstance(numero, (int, float)):
            continue
        c = Centil(int(numero))
        for campo, i in onde.items():
            valor = linha[i] if i < len(linha) else None
            if isinstance(valor, (int, float)):
                setattr(c, campo, float(valor))
        centis.append(c)
    if len(centis) < 120 or {c.numero for c in centis} < set(range(1, 121)):
        raise FonteForaDoArError(f"centis do IRPF: só {len(centis)} linhas")
    return centis


@dataclass(frozen=True)
class Grupo:
    nome: str
    declarantes: float
    renda: float
    dividendos: float
    imposto: float
    bens: float
    dividas: float


GRUPOS = [
    ("Metade de baixo", range(1, 51)),
    ("Do meio (40 %)", range(51, 91)),
    ("10 % de cima", range(91, 101)),
    ("1 % de cima", range(100, 101)),
    ("0,1 % de cima", range(110, 111)),
    ("0,01 % de cima", range(120, 121)),
]
"""Os grupos da tabela. Os três primeiros somam todos; os de baixo estão dentro do 10 %."""


def agrupar(centis: list[Centil]) -> list[Grupo]:
    por_numero = {c.numero: c for c in centis}
    saida = []
    for nome, numeros in GRUPOS:
        partes = [por_numero[n] for n in numeros]
        saida.append(
            Grupo(
                nome,
                *(sum(getattr(p, campo) for p in partes) for campo in COLUNAS),
            )
        )
    return saida


def total(centis: list[Centil]) -> Grupo:
    """Todos os que declaram: os centis 1 a 100 (as linhas 101 a 120 repetem o topo)."""
    so = [c for c in centis if c.numero <= 100]
    return Grupo("Todos", *(sum(getattr(c, campo) for c in so) for campo in COLUNAS))


@cache
def mais_novo() -> tuple[int, list[Centil]]:
    """(ano-calendário, centis) da publicação mais nova."""
    pagina = baixar(LISTAGEM, validade=24 * 3600).decode("utf-8", "replace")
    pasta = PASTA.search(pagina)
    if not pasta:
        raise FonteForaDoArError("centis do IRPF: sem a pasta do estudo ampliado")
    anos = anos_da_listagem(baixar(pasta["url"], validade=24 * 3600).decode("utf-8", "replace"))
    for ano in sorted(anos, reverse=True):
        html = baixar(anos[ano], validade=24 * 3600).decode("utf-8", "replace")
        arquivo = next((m for m in ARQUIVO.finditer(html) if int(m["ano"]) == ano), None)
        if arquivo:
            conteudo = baixar(arquivo["url"] + "/@@download/file", validade=30 * 24 * 3600)
            return ano, ler_planilha(conteudo)
    raise FonteForaDoArError("centis do IRPF: nenhum arquivo do Brasil nas pastas dos anos")
