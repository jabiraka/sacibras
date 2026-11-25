"""Ministério do Planejamento e Orçamento: a planilha "quadros de apoio" do Relatório de
Avaliação de Receitas e Despesas Primárias, que sai a cada dois meses.

O Caio pediu (25/11/2026) que o builder leia sozinho a edição mais nova. A página dos
relatórios de avaliação fiscal lista a planilha de cada bimestre, mas o nome e a pasta mudam
sem padrão ("quadros_de_apoio_relatorio_4o_bi_2026-para-envio.xlsx",
"quadros-de-apoio_relatorio-5o-bi-2026-para-envio.xlsx", uma de 2026 numa pasta de
legislação eleitoral). O builder pega todo endereço com "quadros de apoio" e ".xlsx", abre os
que o nome sugere mais novos e decide o ano e o bimestre pelo cabeçalho da aba "Tabela 1"
("LOA 2026", "Avaliação 5º Bimestre"), não pelo nome. A Tabela 1 traz, em R$ milhões, a LOA e
as duas avaliações mais recentes: o resultado primário, a dedução da meta, a receita
administrada pela Receita e a arrecadação líquida do INSS.

Conferido em 25/11/2026: a do 4º bimestre de 2026 dá os números lidos à mão na nota da
Conorf (-80,9; 67,3; 2.065,7; 786,4; LOA 2.041,0 e 793,2); a do 5º, -89,3; 77,0; 2.064,9;
777,6; meta de 34,3.
"""

from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass
from functools import cache

import openpyxl  # type: ignore[import-untyped]

from sacibras.rede import FonteForaDoArError, baixar

SITE = "https://www.gov.br"
PAGINA = SITE + "/planejamento/pt-br/assuntos/orcamento/relatorios-de-avaliacao-fiscal"
FONTE = (
    "Ministério do Planejamento e Orçamento, Relatório de Avaliação de Receitas e Despesas "
    "Primárias"
)
VALIDADE = 12 * 3600
ABRIR = 3
"""Quantas planilhas, das que o nome sugere mais novas, o builder abre (mais as duas primeiras
da página, que lista a mais nova no alto)."""

_PLANILHA = re.compile(r'href="([^"]*?quadros.{0,3}de.{0,3}apoio[^"]*?\.xlsx[^"]*)"', re.I)


@dataclass(frozen=True)
class Avaliacao:
    """Uma coluna de avaliação da Tabela 1, em R$ bilhões."""

    bimestre: int
    resultado: float
    deducao: float
    receita_rfb: float
    arrecadacao_rgps: float

    @property
    def rotulo(self) -> str:
        return f"{self.bimestre}º bimestre"


@dataclass(frozen=True)
class Quadros:
    ano: int
    url: str
    avaliacoes: list[Avaliacao]
    """As colunas de avaliação da planilha, da mais velha para a mais nova."""
    loa: dict[str, float]
    """{'receita_rfb' | 'arrecadacao_rgps': R$ bilhões} na coluna da LOA."""
    meta: float | None
    """O centro da meta de primário, R$ bilhões."""

    @property
    def bimestre(self) -> int:
        return self.avaliacoes[-1].bimestre

    @property
    def ultima(self) -> Avaliacao:
        return self.avaliacoes[-1]

    @property
    def fonte(self) -> str:
        return f"{FONTE}, {self.bimestre}º bimestre de {self.ano} (quadros de apoio, tabela 1)"


def _texto(valor: object) -> str:
    sem_acento = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


def candidatas(html: str) -> list[str]:
    """Os endereços das planilhas, na ordem em que vale abri-las: as que o nome sugere mais
    novas (ano e bimestre no nome) e, junto, as duas primeiras da página."""
    na_pagina: list[str] = []
    for m in _PLANILHA.finditer(html):
        url = m.group(1)
        url = SITE + url if url.startswith("/") else url
        if not url.endswith("/@@download/file"):
            url = url.split(".xlsx")[0] + ".xlsx/@@download/file"
        if url not in na_pagina:
            na_pagina.append(url)

    def palpite(url: str) -> tuple[int, int]:
        nome = url.split("/")[-3] if url.endswith("/@@download/file") else url.split("/")[-1]
        anos = re.findall(r"20\d\d", nome)
        bim = re.search(r"(\d)\s*[oº]?[-_ ]?bi", nome, re.I)
        return (int(anos[-1]) if anos else 0, int(bim.group(1)) if bim else 0)

    escolhidas = sorted(na_pagina, key=palpite, reverse=True)[:ABRIR]
    for url in na_pagina[:2]:
        if url not in escolhidas:
            escolhidas.append(url)
    return escolhidas


def ler(conteudo: bytes, url: str = "") -> Quadros:
    """A Tabela 1 da planilha. O ano sai da coluna da LOA; o bimestre, de cada coluna de
    avaliação."""
    livro = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    if "Tabela 1" not in livro.sheetnames:
        raise FonteForaDoArError("avaliação bimestral: a planilha não tem a aba Tabela 1")
    linhas = [list(x) for x in livro["Tabela 1"].iter_rows(values_only=True)]
    cabeca = next((x for x in linhas if x and _texto(x[0]).startswith("discrimina")), None)
    if cabeca is None:
        raise FonteForaDoArError("avaliação bimestral: Tabela 1 sem o cabeçalho")
    ano = 0
    col_loa = -1
    col_bim: list[tuple[int, int]] = []
    for c, celula in enumerate(cabeca):
        t = _texto(celula or "")
        if m := re.search(r"\bloa\s*(\d{4})", t):
            ano, col_loa = int(m.group(1)), c
        elif m := re.search(r"avaliacao.*?(\d)\s*[oº]?\s*bimestre", t):
            col_bim.append((c, int(m.group(1))))
    if not ano or not col_bim:
        raise FonteForaDoArError("avaliação bimestral: sem o ano da LOA ou sem bimestre")

    def linha(*padroes: str) -> list[object]:
        for x in linhas:
            t = _texto(x[0] or "") if x else ""
            if all(re.search(p, t) for p in padroes):
                return x
        raise FonteForaDoArError(f"avaliação bimestral: sem a linha {padroes}")

    def bi(x: list[object], c: int) -> float:
        valor = x[c] if c < len(x) else None
        if not isinstance(valor, int | float):
            raise FonteForaDoArError("avaliação bimestral: célula sem número")
        return round(float(valor) / 1000, 1)

    resultado = linha(r"^\d+\.\s*resultado primario(?! apos)")
    deducao = linha(r"^\d+\.\s*deducao")
    rfb = linha(r"^receita administrada pela rfb")
    rgps = linha(r"^arrecadacao liquida para o rgps")
    try:
        centro = linha(r"centro da meta")
        meta: float | None = bi(centro, col_bim[-1][0])
    except FonteForaDoArError:
        meta = None
    avaliacoes = sorted(
        (
            Avaliacao(b, bi(resultado, c), bi(deducao, c), bi(rfb, c), bi(rgps, c))
            for c, b in col_bim
        ),
        key=lambda a: a.bimestre,
    )
    loa = (
        {"receita_rfb": bi(rfb, col_loa), "arrecadacao_rgps": bi(rgps, col_loa)}
        if col_loa >= 0
        else {}
    )
    return Quadros(ano, url, avaliacoes, loa, meta)


@cache
def mais_novo() -> Quadros:
    """A planilha do bimestre mais novo que a página lista (uma vez por rodada)."""
    html = baixar(PAGINA, validade=VALIDADE, tempo_limite=60).decode("utf-8", "replace")
    urls = candidatas(html)
    if not urls:
        raise FonteForaDoArError("avaliação bimestral: a página não lista os quadros de apoio")
    lidas: list[Quadros] = []
    for url in urls:
        try:
            lidas.append(ler(baixar(url, validade=VALIDADE, tempo_limite=120), url))
        except Exception as erro:
            print(f"  aviso: avaliação bimestral: {url.split('/')[-3]}: {str(erro)[:100]}")
    if not lidas:
        raise FonteForaDoArError("avaliação bimestral: nenhuma planilha abriu")
    return max(lidas, key=lambda q: (q.ano, q.bimestre))


def do_ano(ano: int, onde: str) -> Quadros | None:
    """A planilha mais nova, se for do ano que a peça espera; senão None (e o aviso), e a peça
    usa os números lidos à mão."""
    try:
        q = mais_novo()
    except Exception as erro:
        print(f"  aviso: {onde}: avaliação bimestral indisponível ({str(erro)[:120]})")
        return None
    if q.ano != ano:
        print(
            f"  aviso: {onde}: a avaliação bimestral mais nova é de {q.ano}, não de {ano}: "
            "ficam os números lidos à mão; troque o ano (leis.py, relatorios.py)"
        )
        return None
    return q
