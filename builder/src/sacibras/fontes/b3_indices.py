"""Índices da B3 (Ibovespa, IBrX, SMLL, IFIX, setoriais): fechamento diário, sem chave.

É o serviço que alimenta a página "Estatísticas históricas" de cada índice no site da B3:
uma chamada por índice e por ano, com o pedido em JSON codificado em base64 no caminho. A
resposta é uma grade dia × mês com o número no formato brasileiro ("171.324,31").
"""

from __future__ import annotations

import base64
import json
import time
from datetime import date

from sacibras.rede import baixar_json
from sacibras.tipos import Ponto

URL = "https://sistemaswebb3-listados.b3.com.br/indexStatisticsProxy/IndexCall/GetPortfolioDay/"

# Código na B3 → nome para a tela. Conferidos na B3 em 14/11/2026.
INDICES = {
    "IBOV": "Ibovespa",
    "IBXX": "IBrX-100",
    "SMLL": "Small caps (SMLL)",
    "IDIV": "Dividendos (IDIV)",
    "IFIX": "Fundos imobiliários (IFIX)",
    "IFNC": "Financeiro (IFNC)",
    "IMAT": "Materiais básicos (IMAT)",
    "ICON": "Consumo (ICON)",
    "UTIL": "Utilidade pública (UTIL)",
    "IMOB": "Imobiliário (IMOB)",
    "IEEX": "Energia elétrica (IEEX)",
    "INDX": "Industrial (INDX)",
}


def _numero(texto: str) -> float:
    return float(texto.replace(".", "").replace(",", "."))


def ano(indice: str, ano: int, *, corrente: bool) -> list[Ponto]:
    pedido = json.dumps(
        {"language": "pt-br", "index": indice, "year": str(ano)}, separators=(",", ":")
    )
    caminho = base64.b64encode(pedido.encode()).decode()
    # Ano fechado não muda mais: fica um mês no cache.
    bruto = baixar_json(URL + caminho, validade=None if corrente else 30 * 86400)
    pontos: list[Ponto] = []
    for linha in bruto.get("results") or []:
        for mes in range(1, 13):
            valor = linha.get(f"rateValue{mes}")
            if valor:
                pontos.append((date(ano, mes, int(linha["day"])), _numero(valor)))
    return sorted(pontos)


def fechamentos(indice: str, desde_ano: int, hoje: date | None = None) -> list[Ponto]:
    """Fechamentos diários de `desde_ano` até hoje."""
    hoje = hoje or date.today()
    pontos: list[Ponto] = []
    for a in range(desde_ano, hoje.year + 1):
        pontos.extend(ano(indice, a, corrente=a == hoje.year))
        time.sleep(0.4)  # o serviço é do site da B3: sem pressa
    return pontos
