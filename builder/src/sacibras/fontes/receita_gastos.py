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
from dataclasses import dataclass, field

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
    regioes: dict[str, float]
    """{região: R$} do último ano (aba Q IV, linha TOTAL); vazio se a aba mudou."""
    zona_franca: dict[int, float] = field(default_factory=dict)
    """{ano: R$} da Zona Franca de Manaus, das Áreas de Livre Comércio e da Amazônia Ocidental
    (aba Q XXVI), com os anos de projeção; o último realizado fecha com `principais`."""


@dataclass(frozen=True)
class Previsao:
    """O gasto tributário previsto no projeto de orçamento (PLOA) de um ano."""

    ano: int
    total: float
    pct_pib: float


LISTAGEM_PLOA = LISTAGEM.replace("bases-efetivas", "ploa")
FONTE_PLOA = "Receita Federal, Demonstrativo dos Gastos Tributários do PLOA"
PADRAO_PLOA = re.compile(
    r'href="(?P<url>[^"]*/dgt-(?:previsao-)?ploa-(?P<ano>\d{4})-quadros(?:\.xlsx)?)/view"'
)
REGIOES = {
    "NORTE": "Norte",
    "NORDESTE": "Nordeste",
    "CENTRO-OESTE": "Centro-Oeste",
    "SUDESTE": "Sudeste",
    "SUL": "Sul",
}


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
        por_regiao = list(livro[abas["Q IV"]].iter_rows(values_only=True)) if "Q IV" in abas else []
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
    todas = {
        i: int(v)
        for linha in serie[:12]
        for i, v in enumerate(linha)
        if isinstance(v, (int, float)) and 1990 < v < 2100
    }
    zona_franca: dict[int, float] = {}
    for linha in serie:
        r = _rotulo(linha[0] if linha else None)
        if "ZONA FRANCA" in r or "LIVRE COMÉRCIO" in r or "AMAZÔNIA OCIDENTAL" in r:
            for i, a in todas.items():
                if i < len(linha) and isinstance(linha[i], (int, float)):
                    zona_franca[a] = zona_franca.get(a, 0.0) + float(linha[i])
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
        regioes=ler_regioes(por_regiao),
        zona_franca=zona_franca,
    )


def ler_regioes(linhas: list[tuple[object, ...]]) -> dict[str, float]:
    """A linha TOTAL da aba Q IV, pelas colunas que o cabeçalho nomeia."""
    colunas: dict[int, str] = {}
    for linha in linhas:
        if not colunas:
            achadas = {i: REGIOES[_rotulo(c)] for i, c in enumerate(linha) if _rotulo(c) in REGIOES}
            if len(achadas) == len(REGIOES):
                colunas = achadas
        elif _rotulo(linha[0] if linha else None) == "TOTAL":
            return {
                nome: float(linha[i])  # type: ignore[arg-type]
                for i, nome in colunas.items()
                if i < len(linha) and isinstance(linha[i], (int, float))
            }
    return {}


def ler_previsao(conteudo: bytes, ano: int) -> Previsao:
    """Aba Q VI ("consolidação por tipo de tributo"): na linha TOTAL, o valor em R$ e, na
    coluna seguinte, a participação no PIB, já em %."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        livro = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    try:
        abas = {nome.strip(): nome for nome in livro.sheetnames}
        if "Q VI" not in abas:
            raise FonteForaDoArError(f"DGT PLOA {ano}: sem a aba Q VI")
        linhas = list(livro[abas["Q VI"]].iter_rows(values_only=True))
    finally:
        livro.close()
    for linha in linhas:
        if _rotulo(linha[0] if linha else None) == "TOTAL":
            valor, pib = (*linha[1:3], None, None)[:2]
            if isinstance(valor, (int, float)) and isinstance(pib, (int, float)):
                return Previsao(ano=ano, total=float(valor), pct_pib=float(pib))
    raise FonteForaDoArError(f"DGT PLOA {ano}: sem a linha TOTAL na aba Q VI")


def previsoes(depois_de: int) -> list[Previsao]:
    """O previsto no PLOA dos anos depois do último realizado, do mais velho ao mais novo."""
    html = baixar(LISTAGEM_PLOA, validade=24 * 3600).decode("utf-8", "replace")
    achadas = {int(m["ano"]): m["url"] + "/@@download/file" for m in PADRAO_PLOA.finditer(html)}
    saida: list[Previsao] = []
    for ano in sorted(a for a in achadas if a > depois_de):
        corpo = baixar(achadas[ano], validade=7 * 24 * 3600, tempo_limite=120)
        saida.append(ler_previsao(corpo, ano))
    return saida


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
