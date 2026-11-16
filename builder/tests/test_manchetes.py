"""A frase do gráfico: o último valor e a comparação que o dado dá sozinho."""

from datetime import date

from sacibras import manchetes
from sacibras.schema import Faixa, Grafico, Serie


def _meses(valores: list[float], ate: date = date(2026, 10, 1)) -> list[tuple[date, float | None]]:
    pontos: list[tuple[date, float | None]] = []
    ano, mes = ate.year, ate.month
    for v in reversed(valores):
        pontos.append((date(ano, mes, 1), v))
        ano, mes = (ano, mes - 1) if mes > 1 else (ano - 1, 12)
    return pontos[::-1]


def _grafico(valores: list[float], unidade: str = "%", casas: int = 2, **extra: object) -> Grafico:
    return Grafico(
        id="g",
        titulo="t",
        series=[Serie(id="a", nome="IPCA", pontos=_meses(valores))],
        unidade=unidade,
        casas=casas,
        periodicidade="M",
        fonte="teste",
        **extra,  # type: ignore[arg-type]
    )


def test_contra_um_ano_antes() -> None:
    valores = [4.68, 4.5, 4.4, 4.9, 5.1, 5.0, 4.8, 4.7, 4.6, 4.7, 4.9, 4.8, 4.63]
    assert manchetes.do_grafico(_grafico(valores)) == (
        "Out/2026: 4,63 %, abaixo de 4,68 % um ano antes."
    )


def test_o_maior_nivel_em_anos_e_o_inicio_da_serie() -> None:
    subindo = [5.0 + i * 0.1 for i in range(60)]
    frase = manchetes.do_grafico(_grafico(subindo, "% do PIB", 1))
    assert frase == "Out/2026: 10,9 % do PIB, o maior nível desde nov/2021, o início da série."
    # Passou de um pico antigo, mas o pico ficou a menos de três anos: vale a comparação do ano.
    recente = [5.0] * 30 + [9.0] + [5.0] * 20 + [6.0, 7.0]
    assert "um ano antes" in manchetes.do_grafico(_grafico(recente))
    antigo = [9.0] + [5.0] * 50 + [6.0, 7.0]
    assert manchetes.do_grafico(_grafico(antigo)).endswith("o maior nível desde jun/2022.")


def test_contra_a_meta_quando_o_grafico_tem_a_faixa() -> None:
    valores = [4.0] * 20 + [4.6, 4.7, 4.63]
    faixa = Faixa(nome="intervalo da meta", pontos=[(d, 1.5, 4.5) for d, _ in _meses(valores)])
    frase = manchetes.do_grafico(_grafico(valores, faixa=faixa))
    assert frase == "Out/2026: 4,63 %, acima do teto da meta há 3 meses."
    dentro = manchetes.do_grafico(_grafico([4.0] * 23, faixa=faixa))
    assert dentro == "Out/2026: 4,00 %, dentro do intervalo da meta."


def test_onde_nao_ha_serie_no_tempo_fica_em_branco() -> None:
    assert manchetes.do_grafico(_grafico([1.0] * 5)) == ""
    assert manchetes.do_grafico(_grafico([1.0] * 20, tipo="empilhado")) == ""
    assert manchetes.do_grafico(_grafico([1.0] * 20, eixo="meses")) == ""


def test_a_unidade_sem_o_parentese_e_o_nome_com_mais_de_uma_serie() -> None:
    g = _grafico([1.0 + i * 0.1 for i in range(14)], "% do PIB (superávit +, déficit −)", 1)
    g.series.append(Serie(id="b", nome="Outra", pontos=_meses([0.0] * 14)))
    assert manchetes.do_grafico(g).startswith("IPCA, out/2026: 2,3 % do PIB,")
    assert manchetes._com_unidade(5.65, "R$", 2) == "R$ 5,65"
    assert manchetes._com_unidade(123.2, "índice, 2012 = 100", 1) == "123,2"


def test_a_comparacao_usa_a_unidade_curta_e_o_menos_tipografico() -> None:
    g = _grafico([-3.57] + [-3.0] * 11 + [-2.33], "% do PIB", 2)
    assert manchetes.do_grafico(g) == "Out/2026: −2,33 % do PIB, acima de −3,57 % um ano antes."
    assert manchetes._com_unidade(3135.3, "R$ bilhões de set/2026", 0) == "R$ 3.135 bilhões"
    assert manchetes._com_unidade(142.5, "2012 = 100", 1) == "142,5"
    assert manchetes._com_unidade(6947, "R$ por mês", 0) == "R$ 6.947"
    assert manchetes.do_grafico(_grafico([13.75] * 14, "% a.a.")) == (
        "Out/2026: 13,75 % a.a., o mesmo de um ano antes."
    )


def test_serie_que_segue_em_projecao_ou_passa_de_hoje_fica_sem_frase() -> None:
    g = _grafico([1.0] * 20)
    g.series[0].tracejado_desde = date(2026, 1, 1)
    assert manchetes.do_grafico(g) == ""
    futuro = _grafico([1.0] * 20)
    futuro.series[0].pontos = [(date(2099, 1, 1), 1.0)] * 20
    assert manchetes.do_grafico(futuro) == ""
