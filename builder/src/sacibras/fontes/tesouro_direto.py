"""Tesouro Direto: taxa e preço diários de cada título (Tesouro Transparente, dado aberto).

Um CSV só, com tudo desde 2004 (~15 MB): `Tipo Titulo;Data Vencimento;Data Base;Taxa Compra
Manha;…`, datas em dd/mm/aaaa e decimal com vírgula. Daqui saem a curva prefixada, a curva de
juro real (IPCA+) e a inflação implícita entre as duas. Licença ODbL.
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime

from sacibras.rede import baixar
from sacibras.tipos import Ponto

URL = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/"
    "df56aa42-484a-4a59-8184-7676580c81e3/resource/"
    "796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv"
)

# Sem cupom: a taxa do título é a taxa do prazo, sem ajuste.
PREFIXADO = "Tesouro Prefixado"
IPCA = "Tesouro IPCA+"
# Com cupom semestral: alonga a curva, com a taxa interna de retorno do título.
PREFIXADO_JUROS = "Tesouro Prefixado com Juros Semestrais"
IPCA_JUROS = "Tesouro IPCA+ com Juros Semestrais"

Curvas = dict[str, dict[date, list[Ponto]]]
"""{tipo do título: {data-base: [(vencimento, taxa média entre compra e venda, % a.a.)]}}."""


def _data(texto: str) -> date:
    return datetime.strptime(texto, "%d/%m/%Y").date()


def curvas(desde: date) -> Curvas:
    corpo = baixar(URL, validade=12 * 3600, tempo_limite=180)
    leitor = csv.DictReader(io.StringIO(corpo.decode("latin-1")), delimiter=";")
    saida: Curvas = {}
    for linha in leitor:
        base = _data(linha["Data Base"])
        compra = linha["Taxa Compra Manha"].replace(",", ".")
        venda = linha["Taxa Venda Manha"].replace(",", ".")
        # Linha sem preço é linha sem dado (em 29/01/2010 a NTN-F 2021 veio com taxa 0,06 e
        # preço 0,00, conferido em 15/11/2026); taxa 0,00 é o lado que o Tesouro não negociou
        # naquele dia (só o Tesouro Selic tem taxa zero de verdade, e ele não entra em curva).
        if base < desde or linha.get("PU Base Manha", "").strip() in ("0,00", "0"):
            continue
        # A taxa média entre compra e venda (o "mid", como no finance_agent): usar só um lado
        # embute metade do spread do Tesouro Direto (~12 bps) como viés.
        taxas = [float(t) for t in (compra, venda) if t and float(t) != 0]
        if not taxas:
            continue
        saida.setdefault(linha["Tipo Titulo"].strip(), {}).setdefault(base, []).append(
            (_data(linha["Data Vencimento"]), sum(taxas) / len(taxas))
        )
    for por_data in saida.values():
        for pontos in por_data.values():
            pontos.sort()
    return saida


Precos = dict[date, list[Ponto]]
"""{vencimento: [(data-base, preço unitário de venda, R$)]}, de um tipo de título."""


def precos(tipo: str, desde: date) -> Precos:
    """O preço unitário de cada título de um tipo, dia a dia: o "PU Venda Manhã", o que o
    Tesouro paga a quem vende antes do vencimento (o mesmo que o "PU Base"). Sem ele, o dia
    fica de fora."""
    corpo = baixar(URL, validade=12 * 3600, tempo_limite=180)
    leitor = csv.DictReader(io.StringIO(corpo.decode("latin-1")), delimiter=";")
    saida: Precos = {}
    for linha in leitor:
        if linha["Tipo Titulo"].strip() != tipo:
            continue
        base = _data(linha["Data Base"])
        pu = (linha["PU Venda Manha"] or linha["PU Base Manha"]).replace(",", ".")
        if base < desde or not pu or float(pu) <= 0:
            continue
        saida.setdefault(_data(linha["Data Vencimento"]), []).append((base, float(pu)))
    for pontos in saida.values():
        pontos.sort()
    return saida


def no_dia(por_data: dict[date, list[Ponto]], alvo: date) -> tuple[date, list[Ponto]]:
    """A curva da data-base mais recente que não passa de `alvo`."""
    datas = [d for d in por_data if d <= alvo]
    if not datas:
        raise ValueError(f"sem curva até {alvo}")
    dia = max(datas)
    return dia, por_data[dia]
