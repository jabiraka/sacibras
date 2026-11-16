"""O que saiu contra o Focus: a diferença, o erro de costume e a ordem."""

from datetime import date

from sacibras import saiu
from sacibras.schema import Divulgado
from sacibras.secoes.base import Contexto


def _medir(realizado: list[tuple[date, float]], esperado: saiu.Esperado) -> Divulgado | None:
    return saiu.medir(
        "ipca",
        "IPCA",
        "inflacao",
        realizado,
        esperado,
        unidade="%",
        casas=2,
        periodicidade="M",
        fonte="teste",
    )


def test_a_ultima_coleta_de_cada_referencia() -> None:
    linhas = [
        ("10/2026", date(2026, 11, 6), 0.27),
        ("10/2026", date(2026, 11, 5), 0.30),
        ("09/2026", date(2026, 10, 8), 0.60),
    ]
    assert saiu.ultimas(linhas, saiu._mes) == {
        date(2026, 10, 1): (date(2026, 11, 6), 0.27),
        date(2026, 9, 1): (date(2026, 10, 8), 0.60),
    }
    assert saiu._trimestre("3/2026") == date(2026, 7, 1)


def test_o_ipca_de_outubro_de_2026_contra_o_focus() -> None:
    """Os números de 16/11/2026: saiu 0,14 %, o Focus esperava 0,27 %."""
    meses = [date(2026, m, 1) for m in range(3, 11)]
    saidos = [0.88, 0.67, 0.58, 0.16, 0.07, -0.32, 0.82, 0.14]
    focus = [0.60, 0.68, 0.49, 0.32, 0.06, -0.23, 0.60, 0.27]
    esperado = {m: (date(2026, m.month, 28), f) for m, f in zip(meses, focus, strict=True)}
    d = _medir(list(zip(meses, saidos, strict=True)), esperado)
    assert d is not None
    assert (d.periodo, d.valor, d.esperado, d.surpresa) == ("out/2026", 0.14, 0.27, -0.13)
    # O erro de costume não conta a divulgação de agora: as 7 anteriores.
    assert d.divulgacoes == 7
    assert d.erro_de_costume == round((0.28 + 0.01 + 0.09 + 0.16 + 0.01 + 0.09 + 0.22) / 7, 3)


def test_sem_focus_o_numero_sai_sem_a_comparacao() -> None:
    d = _medir([(date(2026, 10, 1), 0.14)], {})
    assert d is not None
    assert (d.esperado, d.surpresa, d.erro_de_costume) == (None, None, None)
    assert _medir([], {}) is None


def test_a_diferenca_se_mede_nas_casas_em_que_o_numero_sai() -> None:
    """Desocupação 5,2 contra mediana 5,22: nada a dizer, o número sai com uma casa."""
    d = saiu.medir(
        "desocupacao",
        "Desocupação",
        "trabalho",
        [(date(2026, 9, 1), 5.2)],
        {date(2026, 9, 1): (date(2026, 10, 29), 5.22)},
        unidade="%",
        casas=1,
        periodicidade="M",
        fonte="teste",
    )
    assert d is not None and d.surpresa == 0


def test_o_que_falha_fica_com_o_da_rodada_anterior(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def falha(ctx: Contexto) -> Divulgado | None:
        raise OSError("fora do ar")

    for nome in ("_ipca", "_desocupacao", "_pib", "_selic"):
        monkeypatch.setattr(saiu, nome, falha)
    antes = _medir([(date(2026, 10, 1), 0.14)], {})
    assert antes is not None
    assert saiu.montar(Contexto(hoje=date(2026, 11, 16)), [antes]) == [antes]
