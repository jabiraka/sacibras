"""Reuniões do Copom: data, número e meta decidida, do serviço do site do BCB.

Não há API com o calendário das reuniões futuras. Para pôr o Focus "por reunião" no tempo,
a reunião N de um ano futuro vai no mesmo mês da reunião N do último ano completo conhecido.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sacibras.rede import baixar_json

URL = "https://www.bcb.gov.br/api/servico/sitebcb/historicotaxasjuros"


@dataclass(frozen=True)
class Reuniao:
    numero: int
    data: date
    meta: float | None


def reunioes() -> list[Reuniao]:
    """Reuniões ordinárias, da mais antiga à mais nova."""
    bruto = baixar_json(URL, validade=12 * 3600)
    saida = [
        Reuniao(
            numero=int(item["NumeroReuniaoCopom"]),
            data=date.fromisoformat(item["DataReuniaoCopom"][:10]),
            meta=item.get("MetaSelic"),
        )
        for item in bruto["conteudo"]
        if not item.get("ReuniaoExtraordinaria") and item.get("DataReuniaoCopom")
    ]
    return sorted(saida, key=lambda r: r.data)


def mes_da_reuniao(todas: list[Reuniao], ordem: int, ano: int, proxima: date | None) -> date:
    """O 1º dia do mês em que cai a reunião `ordem` (1 a 8) de `ano`.

    Reunião já realizada: a data dela. A próxima: `proxima` (a Selic meta do SGS vai até
    ela). As demais: o mês da reunião de mesma ordem no último ano com as oito conhecidas.
    """
    do_ano = [r for r in todas if r.data.year == ano]
    if len(do_ano) >= ordem:
        return do_ano[ordem - 1].data.replace(day=1)
    if proxima and proxima.year == ano and len(do_ano) == ordem - 1:
        return proxima.replace(day=1)
    for base in range(ano - 1, ano - 6, -1):
        completo = [r for r in todas if r.data.year == base]
        if len(completo) >= 8:
            return date(ano, completo[ordem - 1].data.month, 1)
    return date(ano, min(12, round(ordem * 1.5)), 1)
