"""Trabalho sem rede: as séries do SIDRA e do SGS trocadas por números de mentira."""

from datetime import date
from typing import Any

import pytest

from sacibras.fontes import ibge_sidra
from sacibras.secoes import trabalho
from sacibras.secoes.base import Contexto
from sacibras.tipos import Ponto


def _mensal(inicio: float, passo: float, n: int = 40) -> list[Ponto]:
    return [(date(2023 + (m + 5) // 12, (m + 5) % 12 + 1, 1), inicio + passo * m) for m in range(n)]


def test_meses_antes() -> None:
    pontos = _mensal(10, 1)  # jun/2023 … set/2026
    assert pontos[-1][0] == date(2026, 9, 1)
    assert trabalho._meses_antes(pontos, 3) == pontos[-4][1]
    assert trabalho._meses_antes(pontos, 12) == pontos[-13][1]
    assert trabalho._meses_antes(pontos, 100) is None
    assert trabalho._meses_antes([], 3) is None


def test_linha_trimestral_leva_o_periodo_no_rotulo() -> None:
    trimestral = [(date(2025, 4, 1), 20.0), (date(2026, 1, 1), 19.0), (date(2026, 4, 1), 18.0)]
    linha = trabalho._linha(
        "Há 2 anos ou mais", trimestral, "%", referencia=date(2026, 9, 1), periodicidade="T"
    )
    assert linha.rotulo == "Há 2 anos ou mais (2º tri/2026)"
    assert linha.valores == [18.0, 19.0, 20.0]


@pytest.fixture
def ctx(monkeypatch: pytest.MonkeyPatch) -> Contexto:
    def series(tabela: int, variavel: int, **kw: Any) -> dict[str, list[Ponto]]:
        if kw.get("por"):
            return {"32387": _mensal(100_000, 10), "32446": _mensal(6_000, -10)}
        if kw.get("trimestral"):
            return {"": [(date(2026, m, 1), 18.0) for m in (1, 4)]}
        return {"": _mensal(float(variavel % 50), 0.1)}

    monkeypatch.setattr(ibge_sidra, "series", series)
    c = Contexto(hoje=date(2026, 11, 14))
    estoque = [(d, 47_000_000 + 100_000 * i) for i, (d, _) in enumerate(_mensal(0, 0))]
    c._sgs[("EMPREGO_FORMAL", 16)] = estoque
    return c


def test_montar(ctx: Contexto) -> None:
    secao = trabalho.montar(ctx)
    ids = [c.id for c in secao.cartoes]
    # Os quatro de sempre na frente; os novos depois, atrás de "Mais números".
    assert ids[:4] == ["desocupacao", "rendimento", "massa", "emprego-formal"]
    assert ids[4:] == ["subutilizacao", "participacao", "nivel-ocupacao", "informalidade"]
    assert "média de 3 meses: 100 mil" in secao.cartoes[3].detalhe
    graficos = [g.id for g in secao.graficos]
    assert graficos[:4] == ["desocupacao", "emprego-formal", "rendimento", "massa"]
    caged = secao.graficos[1]
    assert [s.id for s in caged.series] == ["saldo", "saldo-3m"]
    (tabela,) = secao.tabelas
    assert tabela.colunas[0] == "Trimestre até set/2026"
    rotulos = [linha.rotulo for linha in tabela.linhas]
    assert "Procuram trabalho há 2 anos ou mais (2º tri/2026)" in rotulos
    ocupados = next(linha for linha in tabela.linhas if linha.rotulo == "Ocupados")
    assert ocupados.valores[0] == pytest.approx(100.39)
    assert ocupados.valores[1] == pytest.approx(100.36)
