"""A conta do simulador da reforma do consumo: quanto de IBS e CBS vai numa compra.

Só aritmética sobre a lei lida (`leis.py`): o imposto é cobrado "por fora", sobre o valor sem
ele; o tipo da compra diz que fração da alíquota cheia se paga; e a família de baixa renda
recebe de volta parte do que pagou. O navegador refaz a mesma conta
(`web/src/simulador-reforma.ts`).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Compra:
    cbs: float
    """CBS paga, em reais."""
    ibs: float
    devolucao: float
    """O que volta para a família de baixa renda, em reais (zero para as outras)."""

    @property
    def imposto(self) -> float:
        return self.cbs + self.ibs

    @property
    def liquido(self) -> float:
        return self.imposto - self.devolucao


def compra(
    valor: float,
    *,
    cbs: float,
    ibs: float,
    paga: float = 100.0,
    volta_cbs: float = 0.0,
    volta_ibs: float = 0.0,
) -> Compra:
    """`valor` é o preço sem IBS nem CBS; `cbs` e `ibs`, as alíquotas cheias em %; `paga`, o
    quanto da alíquota cheia o tipo de compra paga (100, 70, 40 ou 0); `volta_*`, o percentual
    do imposto devolvido à família de baixa renda."""
    pago_cbs = valor * cbs / 100 * paga / 100
    pago_ibs = valor * ibs / 100 * paga / 100
    return Compra(
        cbs=pago_cbs,
        ibs=pago_ibs,
        devolucao=pago_cbs * volta_cbs / 100 + pago_ibs * volta_ibs / 100,
    )


def repartir(total: float, parte_do_ibs: float) -> tuple[float, float]:
    """A alíquota cheia dividida em (CBS, IBS), com o IBS levando `parte_do_ibs` (0 a 1)."""
    ibs = total * parte_do_ibs
    return total - ibs, ibs


def no_preco(aliquota: float) -> float:
    """Quanto do preço final é imposto, em %, quando ele é cobrado por fora a `aliquota` %."""
    return aliquota / (100 + aliquota) * 100
