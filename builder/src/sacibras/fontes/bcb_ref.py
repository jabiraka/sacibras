"""Banco Central: o anexo estatístico (planilha) do Relatório de Estabilidade Financeira, com os
dados do teste de estresse de capital dos bancos.

O Caio pediu (25/11/2026) que o builder leia sozinho a edição mais nova. A planilha mora em
`content/publicacoes/ref/AAAAMM/RELESTAB{AAAAMM}-refAnexoEstatistico.xlsx`, mas a pasta não
segue sempre o mês de publicação (há 202504, 202510, 202605 e 202610), e a página da lista só
abre com JavaScript. Então o builder pergunta pelas pastas dos últimos 18 meses, da mais nova
para a mais velha, e fica com a primeira que existe. Conferido em 25/11/2026:
- Gráfico 1.2.5.6 (situação de capital no cenário de crise de confiança, no fim da simulação):
  as faixas de 10,5 % para cima somam 81,893 % dos ativos na edição de out/2026 (o texto da p. 50
  diz 81,9 %);
- Gráfico 1.2.5.7 (necessidade de capital, % do PR): o pico da crise de confiança é 3,38 e o da
  recessão aguda, 1,656, na edição de out/2026. O texto dessa edição diz 3,5 % para a crise de
  confiança (p. 50); na de mai/2026, planilha e texto batem. Por isso a seção usa o texto lido à
  mão quando a edição achada é a mesma lida (`relatorios.ESTRESSE_EDICAO`).
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date

import httpx
import openpyxl  # type: ignore[import-untyped]

from sacibras import rede
from sacibras.rede import FonteForaDoArError, baixar

ENDERECO = "https://www.bcb.gov.br/content/publicacoes/ref/{m}/RELESTAB{m}-refAnexoEstatistico.xlsx"
FONTE = "Banco Central, Relatório de Estabilidade Financeira"
VALIDADE = 24 * 3600
MESES_PARA_TRAS = 18
ACIMA_DO_MINIMO = ("10,5 - 14", "14 - 16", "16 - 18", "> 18")
"""As faixas do gráfico 1.2.5.6 que ficam no mínimo regulamentar de 10,5 % ou acima dele."""


@dataclass(frozen=True)
class Estresse:
    edicao: date
    """O mês da pasta da edição (out/2026 = 202610)."""
    url: str
    acima_do_minimo: float
    """% dos ativos do sistema em bancos que seguem acima do mínimo, na crise de confiança."""
    crise: float
    """Maior necessidade de capital na crise de confiança, % do PR."""
    recessao: float
    """Maior necessidade de capital na recessão aguda, % do PR."""


def pastas(hoje: date, meses: int = MESES_PARA_TRAS) -> list[str]:
    """As pastas 'AAAAMM' do mês de hoje para trás."""
    saida = []
    ano, mes = hoje.year, hoje.month
    for _ in range(meses):
        saida.append(f"{ano}{mes:02d}")
        ano, mes = (ano, mes - 1) if mes > 1 else (ano - 1, 12)
    return saida


def _existe(url: str) -> bool:
    """Pergunta sem baixar. O 404 é o esperado nas pastas sem edição: não entra em
    `rede.FALHAS` (não é fonte fora do ar)."""
    ultimo: Exception | None = None
    for _ in range(rede.TENTATIVAS):
        try:
            resposta = rede.cliente().head(url, timeout=30)
        except httpx.HTTPError as erro:
            ultimo = erro
            continue
        if resposta.status_code == 404:
            return False
        if resposta.status_code == 200:
            return True
        ultimo = RuntimeError(f"HTTP {resposta.status_code}")
    rede.FALHAS.append(url)
    raise FonteForaDoArError(f"REF: sem resposta de {url}: {ultimo!r}")


def achar(hoje: date) -> tuple[date, str]:
    for pasta in pastas(hoje):
        url = ENDERECO.format(m=pasta)
        if _existe(url):
            return date(int(pasta[:4]), int(pasta[4:]), 1), url
    raise FonteForaDoArError(f"REF: nenhuma planilha nos últimos {MESES_PARA_TRAS} meses")


def _linhas(livro: openpyxl.Workbook, aba: str) -> list[tuple[object, ...]]:
    if aba not in livro.sheetnames:
        raise FonteForaDoArError(f"REF: a planilha não tem a aba '{aba}'")
    return [r for r in livro[aba].iter_rows(values_only=True) if any(v is not None for v in r)]


def _acima_do_minimo(linhas: list[tuple[object, ...]]) -> float:
    """Soma das faixas acima do mínimo, na coluna '% de ativos' da data final da simulação."""
    cabeca = next(r for r in linhas if any(isinstance(v, int) and v > 190000 for v in r))
    datas = [(v, i) for i, v in enumerate(cabeca) if isinstance(v, int) and v > 190000]
    coluna = max(datas)[1] + 1
    faixas = {str(r[0]).strip(): r[coluna] for r in linhas if r[0] is not None}
    valores = [faixas.get(f) for f in ACIMA_DO_MINIMO]
    if not all(isinstance(v, int | float) for v in valores):
        raise FonteForaDoArError("REF: gráfico 1.2.5.6 sem as faixas de capital")
    return float(sum(valores))  # type: ignore[arg-type]


def _pico(linhas: list[tuple[object, ...]], nome: str) -> float:
    for r in linhas:
        if str(r[0]).strip().lower() == nome.lower():
            numeros = [float(v) for v in r[1:] if isinstance(v, int | float)]
            if numeros:
                return max(numeros)
    raise FonteForaDoArError(f"REF: gráfico 1.2.5.7 sem a linha '{nome}'")


def ler(conteudo: bytes, edicao: date, url: str) -> Estresse:
    livro = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    acima = _acima_do_minimo(_linhas(livro, "Graf 1.2.5.6"))
    necessidade = _linhas(livro, "Graf 1.2.5.7")
    crise = _pico(necessidade, "NC Crise de confiança")
    recessao = _pico(necessidade, "NC Recessão aguda")
    if not (0 < acima <= 100):
        raise FonteForaDoArError(f"REF {edicao:%m/%Y}: {acima} % dos ativos")
    return Estresse(edicao, url, acima, crise, recessao)


def estresse(hoje: date) -> Estresse:
    """O teste de estresse da edição mais nova."""
    edicao, url = achar(hoje)
    return ler(baixar(url, validade=VALIDADE, tempo_limite=120), edicao, url)
