from datetime import date

import pytest

from sacibras import contas
from sacibras.secoes import inflacao
from sacibras.secoes.inflacao import MEDIDAS, NUCLEOS, ritmo, tabela_medidas


def _mensal(valores: list[float], ano: int = 2025) -> list[tuple[date, float]]:
    return [(date(ano + i // 12, i % 12 + 1, 1), v) for i, v in enumerate(valores)]


def test_anualizado_de_3_meses_compoe_e_leva_a_12() -> None:
    # 1 % ao mês por 3 meses: 1,01³ − 1 = 3,0301 %; levado ao ano, 1,01¹² − 1 = 12,6825 %.
    serie = _mensal([1.0, 1.0, 1.0])
    assert contas.anualizado(serie, 3) == [(date(2025, 3, 1), pytest.approx(12.6825, abs=1e-4))]


def test_anualizado_de_12_meses_e_o_acumulado() -> None:
    serie = _mensal([0.3, 0.5, -0.1, 0.4] * 4)
    a12 = contas.anualizado(serie, 12)
    ac = contas.acumulado(serie, 12)
    assert [d for d, _ in a12] == [d for d, _ in ac]
    assert [v for _, v in a12] == pytest.approx([v for _, v in ac])


def test_anualizado_de_1_mes() -> None:
    assert contas.anualizado(_mensal([0.5]), 1)[0][1] == pytest.approx((1.005**12 - 1) * 100)


def test_ritmo_faz_a_media_das_series_depois_de_anualizar() -> None:
    a = _mensal([1.0, 1.0, 1.0])
    b = _mensal([0.0, 0.0, 0.0])
    assert ritmo([a, b], 3) == [(date(2025, 3, 1), pytest.approx(12.6825 / 2, abs=1e-4))]


def test_tabela_traz_mes_tres_meses_um_ano_antes_e_doze() -> None:
    ipca = _mensal([0.5] * 24)  # jan/2025 a dez/2026
    atrasada = _mensal([0.2] * 23)  # sem o último mês
    tabela = tabela_medidas(
        [("IPCA", [ipca], "SGS 433"), ("Atrasada", [atrasada], "SGS 1")], "Banco Central"
    )
    assert tabela is not None
    assert tabela.subtitulo.startswith("Até dez/2026. Um ano antes: os 3 meses até dez/2025")
    assert tabela.colunas == [
        "No mês (%)",
        "3 meses, anualizado (%)",
        "Um ano antes (%)",
        "12 meses (%)",
    ]
    mes, tres, antes, doze = tabela.linhas[0].valores
    assert mes == pytest.approx(0.5)
    assert tres == pytest.approx((1.005**12 - 1) * 100)
    assert antes == pytest.approx((1.005**12 - 1) * 100)
    assert doze == pytest.approx((1.005**12 - 1) * 100)
    # Quem não tem o mês do IPCA fica em branco, e não com o número do mês anterior.
    assert tabela.linhas[1].valores[0] is None
    assert tabela.linhas[1].valores[2] == pytest.approx((1.002**12 - 1) * 100)
    assert "sem ajuste sazonal" in tabela.nota


def test_tabela_sem_dados() -> None:
    assert tabela_medidas([], "x") is None
    assert tabela_medidas([("IPCA", [[]], "SGS 433")], "x") is None


def test_medidas_comecam_pelo_ipca_e_usam_os_cinco_nucleos() -> None:
    assert MEDIDAS[0] == ("IPCA", ["IPCA"])
    assert MEDIDAS[1] == ("Média dos núcleos", NUCLEOS)


def test_subitens_do_ipca_so_os_de_sete_digitos_do_maior_peso_ao_menor() -> None:
    """Revisão das telas (15/11/2026): "gasolina" e "aluguel" não achavam nada."""

    def linha(codigo: str, nome: str, variavel: str, valor: str) -> dict[str, str]:
        return {"D4C": codigo, "D4N": nome, "D2C": variavel, "V": valor}

    linhas = [
        linha("7625", "5.Transportes", "66", "20.17"),  # grupo: fica de fora
        linha("7656", "5104.Combustíveis (veículos)", "66", "6.08"),  # item: fora
        linha("7657", "5104001.Gasolina", "63", "-0.56"),
        linha("7657", "5104001.Gasolina", "2265", "3.10"),
        linha("7657", "5104001.Gasolina", "66", "5.1485"),
        linha("7448", "2101001.Aluguel residencial", "63", "0.27"),
        linha("7448", "2101001.Aluguel residencial", "66", "3.6407"),
        linha("7448", "2101001.Aluguel residencial", "2265", "..."),  # sem dado: vazio
        linha("9999", "9999999.Sem peso", "63", "1.0"),  # sem peso: fora
    ]
    assert inflacao.subitens(linhas) == [
        ("Gasolina", [-0.56, 3.10, 5.1485]),
        ("Aluguel residencial", [0.27, None, 3.6407]),
    ]
