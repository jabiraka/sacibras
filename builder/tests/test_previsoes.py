"""O juro de hoje do simulador da dívida: a taxa oficial do BC, e a conta antiga se ela falhar."""

from datetime import date

import pytest

from sacibras.secoes import previsoes
from sacibras.secoes.base import Contexto


def test_simulador_usa_a_taxa_implicita_oficial() -> None:
    ctx = Contexto(hoje=date(2026, 11, 15))
    ctx.memo["taxa_implicita_dbgg"] = [(date(2026, 8, 1), 12.9), (date(2026, 9, 1), 13.03)]
    assert previsoes._juro_de_hoje(ctx, [(date(2026, 9, 1), 78.0)]) == (13.03, True)


def test_sem_a_planilha_volta_a_conta_dos_juros_sobre_o_estoque(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def falha() -> list[tuple[date, float]]:
        raise OSError("fora do ar")

    monkeypatch.setattr(previsoes.bcb_fiscal, "taxa_implicita_dbgg", falha)
    ctx = Contexto(hoje=date(2026, 11, 15))
    ctx._sgs[("NFSP_JUROS_12M", 20)] = [(date(2026, 9, 1), 8.0)]
    juro, oficial = previsoes._juro_de_hoje(ctx, [(date(2026, 9, 1), 80.0)])
    assert (juro, oficial) == (pytest.approx(10.0), False)
