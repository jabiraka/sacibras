"""FRED (Federal Reserve Bank of St. Louis): séries dos EUA em CSV, sem chave.

Só série que o FRED redistribui de fonte oficial, citada pela fonte de origem. Em uso:
`DFII10`, o rendimento do título do Tesouro americano de 10 anos indexado à inflação (TIPS),
prazo constante, % ao ano, diário — a série H.15 do Federal Reserve. Conferido em 15/11/2026:
`fredgraph.csv?id=DFII10` responde da nuvem, com `observation_date,DFII10`, desde 02/01/2003,
e dia sem negócio vem em branco.
"""

from __future__ import annotations

import csv
import io
from datetime import date

from sacibras.rede import baixar
from sacibras.tipos import Ponto

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
TIPS_10_ANOS = "DFII10"
FONTE_TIPS = "Federal Reserve, H.15, TIPS de 10 anos (DFII10, via FRED)"


def ler_csv(texto: str) -> list[Ponto]:
    """Os pontos do CSV do FRED, sem os dias em branco ("" ou ".")."""
    leitor = csv.reader(io.StringIO(texto))
    next(leitor, None)  # o cabeçalho
    pontos: list[Ponto] = []
    for linha in leitor:
        if len(linha) < 2 or linha[1].strip() in ("", "."):
            continue
        pontos.append((date.fromisoformat(linha[0]), float(linha[1])))
    pontos.sort()
    return pontos


def serie(codigo: str, desde: date) -> list[Ponto]:
    corpo = baixar(URL, params={"id": codigo}, validade=12 * 3600, tempo_limite=90)
    return [p for p in ler_csv(corpo.decode("utf-8-sig")) if p[0] >= desde]
