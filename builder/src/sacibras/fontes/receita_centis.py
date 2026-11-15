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
linhas (grupo e coluna): as colunas se acham pelo nome, nunca pela posição.

Os anos de 2017 a 2021 (conferido em 15/11/2026) vêm noutro arquivo
(`distribuicao-de-renda-por-centis-2021.xlsx`, ~22 MB, as 27 UFs no mesmo livro, valores em R$
milhões) com a mesma aba `BRV` e as mesmas colunas, menos o total dos bens: há só as quatro
partes (imóveis, móveis, financeiros, outros), que aqui se somam. Abrem com o openpyxl; o "não
é zip válido" de antes era o download cortado no meio (o `curl` grava o pedaço; o httpx acusa
e tenta de novo). As unidades mudam de um ano para outro (R$ milhões até 2021, R$ depois): só
as fatias se comparam no tempo.
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
ARQUIVO = re.compile(
    r'href="(?P<url>[^"]*/(?:centis-br[-_]ac|distribuicao-de-renda-por-centis-)(?P<ano>\d{4})'
    r'[^"/]*\.xlsx)/view"'
)
ABA = "BRV"
COLUNAS = {
    "declarantes": "Quantidade de Contribuintes",
    "renda": "Soma de RB4 do Centil",
    "dividendos": "Lucros e dividendos",
    "imposto": "Imposto Devido",
    "bens": "Total Bens e Direitos",
    "dividas": "Dívidas e Ônus",
}
PARTES_DOS_BENS = ["Imóveis", "Móveis", "Financeiros", "Outros Bens e Direitos"]
"""Até 2021 o arquivo não traz o total dos bens: ele é a soma destas quatro colunas (as
primeiras com cada nome; as de "- Brasil" e "- Exterior" só existem nos anos novos)."""


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


def _achar(nome: str, cabecalho1: tuple[Any, ...], cabecalho2: tuple[Any, ...]) -> int | None:
    alvo = _limpo(nome)
    for i in range(max(len(cabecalho1), len(cabecalho2))):
        em_cima = _limpo(cabecalho1[i] if i < len(cabecalho1) else "")
        embaixo = _limpo(cabecalho2[i] if i < len(cabecalho2) else "")
        if embaixo == alvo or (em_cima.replace(" ", "") == alvo.replace(" ", "")):
            return i
    return None


def colunas(cabecalho1: tuple[Any, ...], cabecalho2: tuple[Any, ...]) -> dict[str, list[int]]:
    """Onde está cada coluna: o nome pode estar na linha de cima (grupo sem subcoluna, como
    "Imposto Devido") ou na de baixo. Uma lista por campo: os bens, nos arquivos até 2021,
    são a soma das quatro partes."""
    onde: dict[str, list[int]] = {}
    for campo, nome in COLUNAS.items():
        i = _achar(nome, cabecalho1, cabecalho2)
        if i is not None:
            onde[campo] = [i]
    if "bens" not in onde:
        partes = [_achar(p, cabecalho1, cabecalho2) for p in PARTES_DOS_BENS]
        if all(i is not None for i in partes):
            onde["bens"] = [i for i in partes if i is not None]
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
    # Até 2021, o centil 100 aberto não segue a numeração 101 a 120: vem em duas colunas sem
    # cabeçalho ao lado da do centil, de 1 a 10 cada (a primeira, os milésimos; a segunda, os
    # décimos de milésimo do último).
    abertos = all(
        not _limpo(
            linhas[topo + j][col_centil + k] if col_centil + k < len(linhas[topo + j]) else ""
        )
        for j in (0, 1)
        for k in (1, 2)
    )
    for linha in linhas[topo + 2 :]:
        numero = linha[col_centil] if col_centil < len(linha) else None
        if not isinstance(numero, (int, float)) and abertos:
            for k, base in ((1, 100), (2, 110)):
                sub = linha[col_centil + k] if col_centil + k < len(linha) else None
                if isinstance(sub, (int, float)) and 1 <= sub <= 10:
                    numero = base + sub
                    break
        if not isinstance(numero, (int, float)):
            continue
        c = Centil(int(numero))
        for campo, indices in onde.items():
            valores = [linha[i] if i < len(linha) else None for i in indices]
            numeros = [float(v) for v in valores if isinstance(v, (int, float))]
            if numeros:
                setattr(c, campo, sum(numeros))
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


def fatia(centis: list[Centil], numeros: range, campo: str = "renda") -> float:
    """% do total de quem declara (centis 1 a 100) que fica com os centis `numeros`."""
    tot = getattr(total(centis), campo)
    por_numero = {c.numero: c for c in centis}
    parte = sum(getattr(por_numero[n], campo) for n in numeros)
    return parte / tot * 100 if tot else 0.0


@cache
def _pastas_dos_anos() -> dict[int, str]:
    pagina = baixar(LISTAGEM, validade=24 * 3600).decode("utf-8", "replace")
    pasta = PASTA.search(pagina)
    if not pasta:
        raise FonteForaDoArError("centis do IRPF: sem a pasta do estudo ampliado")
    return anos_da_listagem(baixar(pasta["url"], validade=24 * 3600).decode("utf-8", "replace"))


@cache
def do_ano(ano: int) -> list[Centil] | None:
    """Os centis do ano-calendário `ano` (None se a pasta do ano não tem o arquivo do Brasil)."""
    pastas = _pastas_dos_anos()
    if ano not in pastas:
        return None
    html = baixar(pastas[ano], validade=24 * 3600).decode("utf-8", "replace")
    arquivo = next((m for m in ARQUIVO.finditer(html) if int(m["ano"]) == ano), None)
    if not arquivo:
        return None
    # ~22 MB nos anos até 2021; publicação fechada, que só muda em revisão.
    conteudo = baixar(
        arquivo["url"] + "/@@download/file", validade=30 * 24 * 3600, tempo_limite=300
    )
    return ler_planilha(conteudo)


def mais_novo() -> tuple[int, list[Centil]]:
    """(ano-calendário, centis) da publicação mais nova."""
    for ano in sorted(_pastas_dos_anos(), reverse=True):
        centis = do_ano(ano)
        if centis:
            return ano, centis
    raise FonteForaDoArError("centis do IRPF: nenhum arquivo do Brasil nas pastas dos anos")


def todos() -> dict[int, list[Centil]]:
    """{ano-calendário: centis} de todos os anos da pasta (2017 em diante). Ano cujo arquivo
    falha fica de fora; o mais novo tem de vir."""
    saida: dict[int, list[Centil]] = {}
    novo, centis = mais_novo()
    saida[novo] = centis
    for ano in sorted(_pastas_dos_anos()):
        if ano == novo:
            continue
        try:
            achados = do_ano(ano)
        except FonteForaDoArError as erro:
            print(f"    centis do IRPF {ano} ficou de fora: {str(erro)[:120]}")
            continue
        if achados:
            saida[ano] = achados
    return dict(sorted(saida.items()))
