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
    # Por setor: cada um dos 17 da lista com 1/20 do total; os serviços valem 14/20 (as 11
    # partes dos serviços e mais 3/20 sem série própria), e os seis outros, 6/20.
    vigesimo = [(d, v / 20) for d, v in estoque]
    for chave, _ in trabalho.SETORES_CAGED:
        c._sgs[(chave, 16)] = vigesimo
    c._sgs[("EMPREGO_SERVICOS", 16)] = [(d, v * 14 / 20) for d, v in estoque]
    anos = 2026 - trabalho.SALARIO_MINIMO_DESDE.year + 1
    c._sgs[("SALARIO_MINIMO", anos)] = _salario()
    c._sgs[("IPCA", anos)] = (
        [(date(2024, m, 1), 0.5) for m in range(1, 13)]
        + [(date(2025, m, 1), 0.5) for m in range(1, 13)]
        + [(date(2026, m, 1), 0.5) for m in range(1, 11)]
    )
    return c


def _salario() -> list[Ponto]:
    """R$ 1.518 em 2025 e R$ 1.621 em 2026, com os meses já decretados até dez/2026."""
    return [(date(2025, m, 1), 1518.0) for m in range(1, 13)] + [
        (date(2026, m, 1), 1621.0) for m in range(1, 13)
    ]


def test_montar(ctx: Contexto) -> None:
    secao = trabalho.montar(ctx)
    ids = [c.id for c in secao.cartoes]
    # Os quatro de sempre na frente; os novos depois, atrás de "Mais números".
    assert ids[:4] == ["desocupacao", "rendimento", "massa", "emprego-formal"]
    assert ids[4:] == [
        "subutilizacao",
        "participacao",
        "nivel-ocupacao",
        "informalidade",
        "salario-minimo",
    ]
    assert "média de 3 meses: 100 mil" in secao.cartoes[3].detalhe
    graficos = [g.id for g in secao.graficos]
    assert graficos[:4] == ["desocupacao", "emprego-formal", "rendimento", "massa"]
    caged = secao.graficos[1]
    assert [s.id for s in caged.series] == ["saldo", "saldo-3m"]
    tabela, setores = secao.tabelas
    assert secao.salario_minimo is not None
    assert setores.id == "emprego-setores"
    assert setores.linhas[-1].rotulo == "Total"
    # 17 setores, os "demais serviços" e o total; a coluna das vagas fecha no total.
    assert len(setores.linhas) == 19
    vagas = [linha.valores[1] or 0.0 for linha in setores.linhas[:-1]]
    assert sum(vagas) == pytest.approx(setores.linhas[-1].valores[1] or 0.0)
    assert setores.linhas[-1].valores[1] == pytest.approx(1200.0)  # 100 mil por mês
    por_setor = next(g for g in secao.graficos if g.id == "emprego-setores")
    assert [s.id for s in por_setor.series] == [
        "agro",
        "industria",
        "construcao",
        "comercio",
        "servicos",
    ]
    assert tabela.colunas[0] == "Trimestre até set/2026"
    rotulos = [linha.rotulo for linha in tabela.linhas]
    assert "Procuram trabalho há 2 anos ou mais (2º tri/2026)" in rotulos
    ocupados = next(linha for linha in tabela.linhas if linha.rotulo == "Ocupados")
    assert ocupados.valores[0] == pytest.approx(100.39)
    assert ocupados.valores[1] == pytest.approx(100.36)


def test_emprego_por_setor_ordena_pelas_vagas() -> None:
    antes, agora = date(2025, 9, 1), date(2026, 9, 1)
    estoques = [
        ("Comércio", [(antes, 10_000_000.0), (agora, 10_100_000.0)]),
        ("Agropecuária", [(antes, 2_000_000.0), (agora, 1_980_000.0)]),
        ("Serviços", [(antes, 20_000_000.0), (agora, 20_500_000.0)]),
    ]
    total = [(antes, 32_000_000.0), (agora, 32_580_000.0)]
    quando, linhas = trabalho.emprego_por_setor(estoques, total)
    assert quando == agora
    assert [linha.rotulo for linha in linhas] == ["Serviços", "Comércio", "Agropecuária", "Total"]
    assert linhas[2].valores == pytest.approx([1980.0, -20.0, -1.0])
    assert linhas[-1].valores[1] == pytest.approx(580.0)


def test_somar_so_nas_datas_comuns() -> None:
    a = [(date(2026, 1, 1), 1.0), (date(2026, 2, 1), 2.0)]
    b = [(date(2026, 2, 1), 10.0)]
    assert trabalho.somar([a, b]) == [(date(2026, 2, 1), 12.0)]


def test_salario_minimo_ate_hoje_e_o_comparador(ctx: Contexto) -> None:
    """Revisão das telas (15/11/2026): quem buscava "salário mínimo" não achava nada."""
    cartao, comparador = trabalho.salario_minimo(ctx)
    # O SGS traz dez/2026 já decretado; o cartão para no mês de hoje (nov/2026).
    assert cartao.valor == 1621.0
    assert cartao.referencia == date(2026, 11, 1)
    assert cartao.detalhe == "2025: R$ 1.518, alta de 6,8 %"
    assert "Decreto nº 12.797" in cartao.fonte
    # O comparador vai até o último mês com IPCA (out/2026), desde 1995 (aqui, jan/2025).
    assert comparador.meses[0][:2] == (date(2025, 1, 1), 1518.0)
    assert comparador.meses[-1][0] == date(2026, 10, 1)
    assert comparador.prazos == [1, 5, 10, 20]


def test_salario_minimo_contra_a_inflacao(ctx: Contexto) -> None:
    """Caio, 15/11/2026: "comparar o salário mínimo contra a inflação acumulada no período",
    com o período à escolha."""
    _, comparador = trabalho.salario_minimo(ctx)
    conta = trabalho.comparar(comparador.meses, date(2025, 10, 1), date(2026, 10, 1))
    assert conta is not None
    alta, ipca, acima = conta
    assert alta == pytest.approx((1621 / 1518 - 1) * 100)
    assert ipca == pytest.approx((1.005**12 - 1) * 100)
    assert acima == pytest.approx((1621 / 1518 / 1.005**12 - 1) * 100)
    # Fora da série ou de trás para a frente: sem conta.
    assert trabalho.comparar(comparador.meses, date(2026, 10, 1), date(2025, 10, 1)) is None
    assert trabalho.comparar(comparador.meses, date(2020, 1, 1), date(2026, 10, 1)) is None
