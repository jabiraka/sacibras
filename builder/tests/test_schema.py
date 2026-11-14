from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from sacibras.schema import Grafico, Secao
from sacibras.secoes.base import br, cartao, grafico, periodo, serie


def test_formato_brasileiro_nas_frases() -> None:
    assert br(4.5) == "4,5"
    assert br(172457.76, 0) == "172.458"
    assert periodo(date(2026, 10, 1), "M") == "out/2026"
    assert periodo(date(2026, 7, 1), "T") == "3º tri/2026"
    assert periodo(date(2026, 11, 13), "D") == "13/11/2026"


def test_cartao_leva_o_ultimo_ponto_e_a_data_dele() -> None:
    pontos = [(date(2026, 9, 1), 4.58), (date(2026, 10, 1), 4.63)]
    c = cartao("ipca", "IPCA", pontos, unidade="%", periodicidade="M", fonte="BCB", casas=2)
    assert (c.valor, c.referencia) == (4.63, date(2026, 10, 1))
    assert c.mini == pontos


def test_grafico_sem_unidade_ou_fonte_nao_passa() -> None:
    with pytest.raises(ValidationError):
        Grafico.model_validate({"id": "x", "titulo": "X", "periodicidade": "M", "series": []})


def test_secao_vira_json_com_datas_iso() -> None:
    g = grafico(
        "g",
        "Título",
        [serie("s", "Série", [(date(2026, 10, 1), 1.23456)])],
        unidade="%",
        periodicidade="M",
        fonte="BCB",
    )
    secao = Secao(id="s", titulo="S", graficos=[g], gerado_em=datetime(2026, 11, 14, tzinfo=UTC))
    texto = secao.model_dump_json()
    assert '"pontos":[["2026-10-01",1.23]]' in texto


def test_manchete_e_a_primeira_frase_do_resumo() -> None:
    from sacibras.construir import manchete

    # Vírgula decimal, "nº" e parênteses não cortam a frase; ponto e ponto e vírgula, sim.
    resumo = (
        "A Selic está em 13,75 % ao ano desde 17/09/2026 (reunião nº 282 do Copom, em "
        "04/11/2026). Descontada a inflação, o juro real é de 8,4 % ao ano."
    )
    assert manchete(resumo) == (
        "A Selic está em 13,75 % ao ano desde 17/09/2026 (reunião nº 282 do Copom, em 04/11/2026)."
    )
    assert manchete("O PIB cresceu 0,5 %; em quatro trimestres acumula 1,9 %.") == (
        "O PIB cresceu 0,5 %."
    )
    assert manchete("") == ""
