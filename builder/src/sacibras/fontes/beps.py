"""Ministério da Previdência Social: a planilha do Boletim Estatístico da Previdência Social
(BEPS), mensal, em .xls.

O Caio pediu (25/11/2026) que o builder leia sozinho a edição mais nova. A página dos boletins
lista a edição do mês ("beps092026_final.xls"); a dos anteriores, as outras. O builder junta as
duas e pega a de mês mais alto. Do quadro 15 ("Benefícios emitidos pelo INSS, por clientela,
segundo os grupos de espécies") sai o valor médio das aposentadorias, por idade e por tempo de
contribuição; do quadro 27 ("Outras informações"), o teto do salário de benefício.

Mês com o 13º (o abono anual) fica de fora: o valor médio do quadro 15 vem com a parcela
dentro (abr/2026: R$ 3.207, contra R$ 2.056 em mar/2026). O quadro 14 traz o valor médio de
todos os meses do ano; se o do mês passa de 1,5 % do menor desde janeiro, o builder vai à
edição anterior. Conferido em 25/11/2026 nas edições de jul/2025 a set/2026: separa abr e
mai/2026 e nov/2025 (+2,4 %) e deixa passar jan/2026 (o reajuste) e dez/2025 (+0,6 %).
Conferido também que a de set/2026 dá os números lidos à mão no PDF (2.051,05; 1.617,72;
3.032,35; teto de 8.475,55).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date

import xlrd  # type: ignore[import-untyped]

from sacibras.rede import FonteForaDoArError, baixar

PAGINA = (
    "https://www.gov.br/previdencia/pt-br/assuntos/previdencia-social/"
    "Dados-estatisticos-previdencia-social-e-inss/boletins-da-previdencia-social"
)
ANTERIORES = PAGINA + "/BEPS-anteriores"
FONTE = "Ministério da Previdência Social, Boletim Estatístico da Previdência Social"
VALIDADE = 12 * 3600
TENTATIVAS = 4
"""Quantas edições, da mais nova para trás, o builder abre atrás de um mês sem o 13º."""
FOLGA_DO_13 = 0.015
"""Quanto o valor médio do mês pode passar do menor do ano antes de contar como mês do 13º."""

_PLANILHA = re.compile(r'href="([^"]*?beps(\d\d)(\d{4})_final[^"]*?\.xls)"', re.IGNORECASE)
_MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


@dataclass(frozen=True)
class Boletim:
    mes: date
    url: str
    aposentadorias: int
    media: float
    """Valor médio de todas as aposentadorias, R$ por mês."""
    idade: float
    tempo: float
    teto: float
    teto_em: date
    com_13: bool
    """O mês traz a parcela do 13º no valor (não serve para o valor médio)."""


def edicoes(*paginas: str) -> list[tuple[date, str]]:
    """(mês, endereço) de cada planilha listada, da mais nova para a mais velha, sem repetir."""
    achadas: dict[date, str] = {}
    for html in paginas:
        for m in _PLANILHA.finditer(html):
            mes = date(int(m.group(3)), int(m.group(2)), 1)
            achadas.setdefault(mes, m.group(1))
    return sorted(achadas.items(), reverse=True)


def _texto(valor: object) -> str:
    sem_acento = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


def _data(valor: object, modo: int) -> date | None:
    """Célula de mês: número de série do Excel ou texto 'JUN/18'."""
    if isinstance(valor, float) and valor > 0:
        dia: date = xlrd.xldate.xldate_as_datetime(valor, modo).date()
        return dia.replace(day=1)
    m = re.fullmatch(r"([a-z]{3})/(\d{2})", _texto(valor))
    if m and m.group(1) in _MESES:
        return date(2000 + int(m.group(2)), _MESES.index(m.group(1)) + 1, 1)
    return None


def _coluna(aba: xlrd.sheet.Sheet, titulo: str) -> tuple[int, int]:
    """(linha, coluna) da primeira célula cujo texto começa com `titulo`."""
    for r in range(min(aba.nrows, 15)):
        for c in range(aba.ncols):
            if _texto(aba.cell_value(r, c)).startswith(titulo):
                return r, c
    raise FonteForaDoArError(f"BEPS: quadro {aba.name} sem a coluna '{titulo}'")


def _mes_da_aba(aba: xlrd.sheet.Sheet, modo: int) -> date:
    """O mês de referência: o número de série na primeira linha do quadro."""
    for c in range(aba.ncols):
        mes = _data(aba.cell_value(0, c), modo)
        if mes is not None:
            return mes
    raise FonteForaDoArError(f"BEPS: quadro {aba.name} sem o mês de referência")


def _quadro_15(aba: xlrd.sheet.Sheet) -> tuple[int, float, float, float]:
    _, c_qtd = _coluna(aba, "quantidade")
    _, c_media = _coluna(aba, "valor medio")
    rotulos = [_texto(aba.cell_value(r, 0)) for r in range(aba.nrows)]
    try:
        inicio = rotulos.index("aposentadorias")
    except ValueError as erro:
        raise FonteForaDoArError("BEPS: quadro 15 sem a linha Aposentadorias") from erro

    def depois(rotulo: str) -> int:
        for r in range(inicio + 1, min(inicio + 6, aba.nrows)):
            if rotulos[r] == rotulo:
                return r
        raise FonteForaDoArError(f"BEPS: quadro 15 sem a linha '{rotulo}'")

    def valor(r: int, c: int) -> float:
        v = aba.cell_value(r, c)
        if not isinstance(v, float):
            raise FonteForaDoArError(f"BEPS: quadro 15, linha {r + 1}, sem número")
        return v

    return (
        int(valor(inicio, c_qtd)),
        valor(inicio, c_media),
        valor(depois("idade"), c_media),
        valor(depois("tempo de contribuicao"), c_media),
    )


def _quadro_27(aba: xlrd.sheet.Sheet, modo: int) -> tuple[float, date]:
    """O teto do salário de benefício na última coluna, e o mês dela."""
    cabeca, _ = _coluna(aba, "discriminacao")
    for r in range(aba.nrows):
        if _texto(aba.cell_value(r, 0)).startswith("teto do sal"):
            for c in range(aba.ncols - 1, 0, -1):
                v = aba.cell_value(r, c)
                if isinstance(v, float) and v > 0:
                    mes = _data(aba.cell_value(cabeca, c), modo)
                    if mes is None:
                        break
                    return v, mes
    raise FonteForaDoArError("BEPS: quadro 27 sem o teto do salário de benefício")


def _valores_medios_do_ano(aba: xlrd.sheet.Sheet, ano: int) -> dict[int, float]:
    """Quadro 14: o valor médio de todos os benefícios, mês a mês, no ano pedido.

    As linhas de mês ('Abril(1)') seguem a do ano; a nota (1) nem sempre aparece."""
    _, c_media = _coluna(aba, "valor medio")
    meses = [
        "janeiro",
        "fevereiro",
        "marco",
        "abril",
        "maio",
        "junho",
        "julho",
        "agosto",
        "setembro",
        "outubro",
        "novembro",
        "dezembro",
    ]
    atual: int | None = None
    saida: dict[int, float] = {}
    for r in range(aba.nrows):
        primeira = aba.cell_value(r, 0)
        tem_ano = re.fullmatch(r"(\d{4})(?:\.0)?", str(primeira).strip())
        if tem_ano:
            atual = int(tem_ano.group(1))
        nome = re.sub(r"\s*\(.*\)", "", _texto(aba.cell_value(r, 1)))
        valor = aba.cell_value(r, c_media)
        if atual == ano and nome in meses and isinstance(valor, float):
            saida[meses.index(nome) + 1] = valor
    return saida


def mes_do_13(valores: dict[int, float], mes: int) -> bool:
    """O valor médio do mês passa do menor do ano até ele: veio com o 13º."""
    ate = [v for m, v in valores.items() if m <= mes]
    if mes not in valores or not ate:
        raise FonteForaDoArError("BEPS: quadro 14 sem o mês de referência")
    return valores[mes] > min(ate) * (1 + FOLGA_DO_13)


def ler(conteudo: bytes, url: str) -> Boletim:
    livro = xlrd.open_workbook(file_contents=conteudo)
    q15 = livro.sheet_by_name("15")
    mes = _mes_da_aba(q15, livro.datemode)
    quantidade, media, idade, tempo = _quadro_15(q15)
    teto, teto_em = _quadro_27(livro.sheet_by_name("27"), livro.datemode)
    com_13 = mes_do_13(_valores_medios_do_ano(livro.sheet_by_name("14"), mes.year), mes.month)
    if not (500 < idade < media < tempo < teto):
        raise FonteForaDoArError(f"BEPS {mes:%m/%Y}: valores fora de ordem")
    return Boletim(mes, url, quantidade, media, idade, tempo, teto, teto_em, com_13)


def boletim() -> Boletim:
    """O boletim mais novo cujo mês não traz o 13º."""
    paginas = [baixar(PAGINA, validade=VALIDADE, tempo_limite=60).decode("utf-8", "replace")]
    try:
        anteriores = baixar(ANTERIORES, validade=VALIDADE, tempo_limite=60)
        paginas.append(anteriores.decode("utf-8", "replace"))
    except FonteForaDoArError:
        pass  # a página do mês basta; a dos anteriores só serve para pular o 13º
    lista = edicoes(*paginas)
    if not lista:
        raise FonteForaDoArError("BEPS: a página não lista a planilha do boletim")
    for _, url in lista[:TENTATIVAS]:
        lido = ler(baixar(url, validade=VALIDADE, tempo_limite=120), url)
        if not lido.com_13:
            return lido
    raise FonteForaDoArError(f"BEPS: as {TENTATIVAS} edições mais novas trazem o 13º")
