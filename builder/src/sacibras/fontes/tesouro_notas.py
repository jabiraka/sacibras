"""Tesouro Nacional: a consulta "Histórico da classificação de risco da dívida" (sisweb), em
CSV.

O Caio pediu (25/11/2026) que o builder leia sozinho os atos novos das agências. O endereço do
CSV redireciona e pede o cookie da sessão; o cliente de `rede` segue o redirecionamento e guarda
o cookie. O arquivo vem em latin-1, com as colunas "Última Alteração" (dd-MMM-aa, mês em
português), "Agência", "Moeda Estrangeira", "Moeda Local" e "Ação" ("Manutenção da nota e
revisão da perspectiva para estável").

O histórico antigo do CSV é sujo (datas e notas que não batem com o PDF do Tesouro e os
comunicados): fica o lido à mão em `relatorios.NOTAS`, e daqui só se acrescentam os atos de S&P,
Fitch e Moody's posteriores a `relatorios.ULTIMO_ATO_LIDO`. Conferido em 25/11/2026: os atos
depois de 30/05/2025 são Fitch em 25/06/2025 e 16/06/2026 e S&P em 25/06/2026, todos mantendo
a nota e a perspectiva estável.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import date

from sacibras.rede import FonteForaDoArError, baixar

URL = "https://sisweb.tesouro.gov.br/apex/f?p=2810:2:0:CSV::::"
FONTE = "Tesouro Nacional, histórico da classificação de risco (consulta em CSV)"
VALIDADE = 12 * 3600

AGENCIAS = {"Standard & Poor's": "S&P", "Fitch": "Fitch", "Moody's": "Moody's"}
"""O nome no CSV e o de `relatorios.NOTAS`. As outras agências do CSV ficam de fora."""

_MESES = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
_PERSPECTIVA = re.compile(r"perspectiva (?:para )?(estável|positiva|negativa)")


@dataclass(frozen=True)
class Ato:
    data: date
    agencia: str
    nota: str
    """Dívida de longo prazo em moeda estrangeira."""
    perspectiva: str | None
    acao: str


def _data(texto: str) -> date:
    m = re.fullmatch(r"(\d{2})-([A-Z]{3})-(\d{2})", texto.strip().upper())
    if not m or m.group(2) not in _MESES:
        raise FonteForaDoArError(f"classificação de risco: data '{texto}' fora do padrão")
    ano = int(m.group(3))
    return date(
        2000 + ano if ano < 70 else 1900 + ano, _MESES.index(m.group(2)) + 1, int(m.group(1))
    )


def ler(conteudo: bytes) -> list[Ato]:
    """Os atos de S&P, Fitch e Moody's, do mais velho para o mais novo."""
    linhas = list(csv.reader(io.StringIO(conteudo.decode("latin-1")), delimiter=";"))
    if not linhas or len(linhas[0]) < 5 or "Ag" not in linhas[0][1]:
        raise FonteForaDoArError("classificação de risco: o CSV veio sem o cabeçalho esperado")
    atos = []
    for linha in linhas[1:]:
        if len(linha) < 5 or linha[1].strip() not in AGENCIAS:
            continue
        acao = linha[4].strip()
        achada = _PERSPECTIVA.search(acao.lower())
        atos.append(
            Ato(
                data=_data(linha[0]),
                agencia=AGENCIAS[linha[1].strip()],
                nota=linha[2].strip().replace("−", "-"),
                perspectiva=achada.group(1) if achada else None,
                acao=acao,
            )
        )
    if not atos:
        raise FonteForaDoArError("classificação de risco: o CSV veio sem as três agências")
    return sorted(atos, key=lambda a: a.data)


@dataclass(frozen=True)
class Notas:
    historia: dict[str, list[tuple[date, str]]]
    perspectiva: dict[str, str]
    ultimo: date
    novos: list[Ato]
    """Os atos acrescentados ao que foi lido à mão (vazio: nada novo)."""


def juntar(
    historia: dict[str, list[tuple[date, str]]],
    perspectiva: dict[str, str],
    ultimo_lido: date,
    atos: list[Ato],
    escala: dict[str, int],
) -> Notas:
    """O histórico lido à mão com os atos posteriores a `ultimo_lido`: a nota entra só se
    mudou; a perspectiva vale a do último ato. Nota fora da `escala` é erro (o gráfico não teria
    onde pô-la)."""
    novos = [a for a in atos if a.data > ultimo_lido]
    saida = {agencia: list(linhas) for agencia, linhas in historia.items()}
    vista = dict(perspectiva)
    for ato in novos:
        if ato.nota not in escala:
            raise FonteForaDoArError(f"classificação de risco: nota '{ato.nota}' fora da escala")
        linhas = saida.setdefault(ato.agencia, [])
        if not linhas or linhas[-1][1] != ato.nota:
            linhas.append((ato.data, ato.nota))
        if ato.perspectiva:
            vista[ato.agencia] = ato.perspectiva
    ultimo = max([ultimo_lido, *(a.data for a in novos)])
    return Notas(saida, vista, ultimo, novos)


def atos() -> list[Ato]:
    return ler(baixar(URL, validade=VALIDADE, tempo_limite=60))
