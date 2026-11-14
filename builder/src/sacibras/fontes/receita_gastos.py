"""Gastos tributários da União, realizados ("bases efetivas"): o DGT da Receita Federal.

Gasto tributário é o que a União deixa de arrecadar por isenção, redução de alíquota ou
regime especial (Simples Nacional, Zona Franca de Manaus, deduções do IRPF…). A Receita
publica uma edição por ano, cada uma com três anos realizados e três de projeção, em XLSX
desde a edição de 2016 (as anteriores são PDF). Lido em 14/11/2026: a edição mais nova é a de
2023 (série 2021 a 2026, publicada em 07/04/2026); 2023 é o último ano realizado.

As planilhas se acham pela página de listagem (o nome muda a cada edição) e se baixam com
`/@@download/file` no lugar do `/view`. Dentro:
- aba `Q XXVI`: a série por tributo e gasto, com os anos na linha do cabeçalho; no rodapé, as
  linhas `TOTAL` (R$) e `GT / PIB` (fração). Linhas pelo rótulo, nunca pela posição;
- aba `Q X`: os principais gastos do último ano realizado, do maior ao menor, em R$.
"""

from __future__ import annotations

import io
import re
import warnings
from dataclasses import dataclass

import openpyxl  # type: ignore[import-untyped]

from sacibras.rede import FonteForaDoArError, baixar

LISTAGEM = (
    "https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/relatorios/"
    "renuncia/gastos-tributarios-bases-efetivas"
)
FONTE = "Receita Federal, Demonstrativo dos Gastos Tributários, bases efetivas"
PADRAO = re.compile(
    r'href="(?P<url>[^"]*/dgt-bases-efetivas-(?P<ed>\d{4})-serie-\d{4}-a-\d{4}-quadros'
    r'(?:\.xlsx)?)/view"'
)


@dataclass(frozen=True)
class Edicao:
    ano: int
    """O último ano realizado (o ano da edição)."""
    total: dict[int, float]
    """{ano realizado: R$}."""
    pct_pib: dict[int, float]
    """{ano realizado: % do PIB}."""
    principais: list[tuple[str, float]]
    """Os gastos do último ano, do maior ao menor: (nome, R$)."""


def edicoes_na_listagem(html: str) -> dict[int, str]:
    """{ano da edição: endereço de download}."""
    return {int(m["ed"]): m["url"] + "/@@download/file" for m in PADRAO.finditer(html)}


def _rotulo(celula: object) -> str:
    return " ".join(str(celula).split()).upper() if isinstance(celula, str) else ""


def ler_edicao(conteudo: bytes, ano: int) -> Edicao:
    with warnings.catch_warnings():  # "Print area cannot be set": área de impressão da Receita
        warnings.simplefilter("ignore", UserWarning)
        livro = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    try:
        # O nome da aba às vezes vem com espaço no fim ("Q X " na edição de 2022).
        abas = {nome.strip(): nome for nome in livro.sheetnames}
        if "Q XXVI" not in abas or "Q X" not in abas:
            raise FonteForaDoArError(f"DGT {ano}: sem as abas Q XXVI e Q X")
        serie = list(livro[abas["Q XXVI"]].iter_rows(values_only=True))
        principais_brutos = list(livro[abas["Q X"]].iter_rows(values_only=True))
    finally:
        livro.close()

    colunas: dict[int, int] = {}
    for linha in serie[:12]:
        anos = {
            i: int(v)
            for i, v in enumerate(linha)
            if isinstance(v, (int, float)) and 1990 < v < 2100
        }
        if len(anos) >= 3:
            colunas = {i: a for i, a in anos.items() if a <= ano}  # só os realizados
            break
    if not colunas:
        raise FonteForaDoArError(f"DGT {ano}: sem a linha dos anos na aba Q XXVI")
    achadas: dict[str, tuple[object, ...]] = {}
    for linha in serie:
        r = _rotulo(linha[0] if linha else None)
        if r in ("TOTAL", "GT / PIB") and r not in achadas:
            achadas[r] = linha
    if len(achadas) < 2:
        raise FonteForaDoArError(f"DGT {ano}: sem TOTAL ou GT / PIB na aba Q XXVI")

    def valores(linha: tuple[object, ...], escala: float) -> dict[int, float]:
        return {
            a: float(linha[i]) * escala  # type: ignore[arg-type]
            for i, a in colunas.items()
            if i < len(linha) and isinstance(linha[i], (int, float))
        }

    principais: list[tuple[str, float]] = []
    for linha in principais_brutos:
        nome, valor = (*linha, None, None)[:2]
        r = _rotulo(nome)
        if not r or not isinstance(valor, (int, float)) or r.startswith("GASTO"):
            continue
        if r == "TOTAL":
            break
        principais.append((" ".join(str(nome).split()), float(valor)))
    return Edicao(
        ano=ano,
        total=valores(achadas["TOTAL"], 1.0),
        pct_pib=valores(achadas["GT / PIB"], 100.0),
        principais=principais,
    )


def edicoes(quantas: int = 4) -> list[Edicao]:
    """As edições mais novas, da mais nova para a mais velha. Juntas, com 3 anos realizados
    em cada, as de 2016, 2019, 2022 e 2023 cobrem de 2014 em diante."""
    paginas = "".join(
        baixar(LISTAGEM, params={"b_start:int": str(b)}, validade=24 * 3600).decode(
            "utf-8", "replace"
        )
        for b in (0, 20)
    )
    achadas = edicoes_na_listagem(paginas)
    if not achadas:
        raise FonteForaDoArError("DGT: nenhuma planilha na página de listagem")
    anos = sorted(achadas, reverse=True)
    # A mais nova e, de três em três anos para trás, as que cobrem o que falta.
    escolhidas = [anos[0], *[a for a in anos[1:] if (anos[0] - 1 - a) % 3 == 0]][:quantas]
    return [
        ler_edicao(baixar(achadas[a], validade=7 * 24 * 3600, tempo_limite=120), a)
        for a in escolhidas
    ]
