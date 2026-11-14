"""Futuros da B3, do serviço de cotações do site (`cotacao.b3.com.br`), sem chave.

Uma chamada por mercadoria traz todos os vencimentos, com o último negócio, o ajuste do
pregão anterior e os contratos em aberto. Os dados têm atraso de 15 minutos durante o pregão;
depois do fechamento, o último negócio é o do dia.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sacibras.rede import baixar_json

URL = "https://cotacao.b3.com.br/mds/api/v1/DerivativeQuotation/{codigo}"


@dataclass(frozen=True)
class Contrato:
    simbolo: str
    vencimento: date
    ultimo: float | None
    ajuste_anterior: float | None
    em_aberto: int
    negociados: int

    @property
    def preco(self) -> float | None:
        """O último negócio; sem negócio no dia, o ajuste anterior."""
        return self.ultimo if self.ultimo is not None else self.ajuste_anterior


def futuros(codigo: str) -> list[Contrato]:
    """Os vencimentos futuros de `codigo` (DI1, DOL, IND, DAP, BGI…), do mais curto ao mais
    longo."""
    bruto = baixar_json(URL.format(codigo=codigo), validade=1800)
    saida: list[Contrato] = []
    for papel in bruto.get("Scty") or []:
        if (papel.get("mkt") or {}).get("cd") != "FUT":
            continue
        resumo = (papel.get("asset") or {}).get("AsstSummry") or {}
        cotacao = papel.get("SctyQtn") or {}
        if not resumo.get("mtrtyCode"):
            continue
        saida.append(
            Contrato(
                simbolo=papel["symb"],
                vencimento=date.fromisoformat(resumo["mtrtyCode"]),
                ultimo=cotacao.get("curPrc"),
                ajuste_anterior=cotacao.get("prvsDayAdjstmntPric"),
                em_aberto=int(resumo.get("opnCtrcts") or 0),
                negociados=int(resumo.get("traddCtrctsQty") or 0),
            )
        )
    return sorted(saida, key=lambda c: c.vencimento)
