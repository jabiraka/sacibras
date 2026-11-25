"""A planilha "quadros de apoio" do relatório bimestral: qual abrir e o que ler, sem rede."""

from __future__ import annotations

import io

import openpyxl  # type: ignore[import-untyped]
import pytest

from sacibras import relatorios, tramitacao
from sacibras.fontes import avaliacao_bimestral as aval
from sacibras.rede import FonteForaDoArError
from sacibras.secoes import fiscal, impostos


def _planilha(ano: int = 2026, bimestres: tuple[int, int] = (4, 5)) -> bytes:
    """A Tabela 1 com a forma da do 5º bimestre de 2026 (R$ milhões)."""
    livro = openpyxl.Workbook()
    folha = livro.active
    folha.title = "Tabela 1"
    a, b = bimestres
    folha.append([None, None, None, None, "R$ milhões"])
    folha.append(
        [
            "Discriminação",
            f"LOA {ano}\n\n(a)",
            f"Avaliação \n{a}º Bimestre\n(b)",
            f"Avaliação \n{b}º Bimestre\n(c)",
            "Diferença",
        ]
    )
    folha.append(["1. Receita Primária Total", 3198061.3, 3221516.5, 3249244.5, 0])
    folha.append(
        [
            "Receita Administrada pela RFB/MF, exceto RGPS e líquida de incentivos fiscais",
            2040990.09,
            2065688.34,
            2064945.97,
            0,
        ]
    )
    folha.append(["Arrecadação Líquida para o RGPS", 793153.47, 786426.49, 777560.04, 0])
    folha.append(["5. Resultado Primário (3) - (4)", -22915.9, -80936.8, -89306.48, 0])
    folha.append(
        ["6.  Dedução EC 136,  ADPF 1236 e LCs 221, 223 e 235", 57836.1, 67291.41, 76984.69, 0]
    )
    folha.append(["7. Resultado Primário após Dedução (5) + (6)", 34920.1, -13645.4, -12321.8, 0])
    folha.append(["8. Centro da Meta de Resultado Primário OFS", 34264.6, 34264.6, 34264.6, 0])
    livro.create_sheet("Tabela 2")
    saida = io.BytesIO()
    livro.save(saida)
    return saida.getvalue()


def test_le_a_tabela_1_pelo_cabecalho() -> None:
    q = aval.ler(_planilha(), "u")
    assert (q.ano, q.bimestre) == (2026, 5)
    assert [a.bimestre for a in q.avaliacoes] == [4, 5]
    assert q.avaliacoes[0] == aval.Avaliacao(4, -80.9, 67.3, 2065.7, 786.4)
    assert q.ultima == aval.Avaliacao(5, -89.3, 77.0, 2064.9, 777.6)
    assert q.loa == {"receita_rfb": 2041.0, "arrecadacao_rgps": 793.2}
    assert q.meta == 34.3
    assert "5º bimestre de 2026" in q.fonte


def test_planilha_sem_a_tabela_1_nao_passa() -> None:
    livro = openpyxl.Workbook()
    saida = io.BytesIO()
    livro.save(saida)
    with pytest.raises(FonteForaDoArError):
        aval.ler(saida.getvalue())


def test_candidatas_pelo_nome_e_pelo_alto_da_pagina() -> None:
    html = (
        '<a href="/p/2026/quadros-de-apoio_relatorio-5o-bi-2026-para-envio.xlsx/@@download/file">'
        '<a href="/p/2026/quadros_de_apoio_relatorio_4o_bi_2026-para-envio.xlsx">'
        '<a href="/eleitoral/quadros_de_apoio_relatorio_3o_bi_2026.xlsx/@@download/file">'
        '<a href="/p/2025/quadros-de-apoio_relatorio-2obi-2025_para_envio.xlsx/@@download/file">'
        '<a href="/p/2023/tabelas-relatorio-5o-bim-2023.xlsx/@@download/file">'
    )
    urls = aval.candidatas(html)
    assert len(urls) == aval.ABRIR
    assert all(u.startswith("https://www.gov.br/p") or "eleitoral" in u for u in urls)
    assert all(u.endswith(".xlsx/@@download/file") for u in urls)
    assert "5o-bi-2026" in urls[0] and "4o_bi_2026" in urls[1] and "3o_bi_2026" in urls[2]


def test_fica_com_a_mais_nova_pelo_cabecalho(monkeypatch: pytest.MonkeyPatch) -> None:
    # o nome diz 5º, mas a planilha é a do 4º; a outra, de nome sem número, é a do 5º
    html = (
        '<a href="/a/quadros_de_apoio_5o_bi_2026.xlsx">'
        '<a href="/a/quadros_de_apoio_final.xlsx">'
        '<a href="/a/quadros_de_apoio_quebrada.xlsx">'
    )
    corpos = {
        aval.PAGINA: html.encode(),
        "https://www.gov.br/a/quadros_de_apoio_5o_bi_2026.xlsx/@@download/file": _planilha(
            bimestres=(3, 4)
        ),
        "https://www.gov.br/a/quadros_de_apoio_final.xlsx/@@download/file": _planilha(),
        "https://www.gov.br/a/quadros_de_apoio_quebrada.xlsx/@@download/file": b"nada",
    }
    monkeypatch.setattr(aval, "baixar", lambda url, **_: corpos[url])
    aval.mais_novo.cache_clear()
    try:
        q = aval.mais_novo()
    finally:
        aval.mais_novo.cache_clear()
    assert q.bimestre == 5 and q.url.endswith("final.xlsx/@@download/file")


def test_ano_diferente_fica_com_a_reserva(monkeypatch: pytest.MonkeyPatch) -> None:
    q = aval.ler(_planilha(ano=2027, bimestres=(1, 2)))
    monkeypatch.setattr(aval, "mais_novo", lambda: q)
    assert aval.do_ano(2027, "teste") is q
    assert aval.do_ano(2026, "teste") is None


def test_a_meta_usa_o_bimestre_lido() -> None:
    lido = aval.ler(_planilha(bimestres=(5, 6)))  # um 6º que a reserva não tem
    lista, fonte = fiscal.avaliacoes_do_ano(lido, 2026)
    assert [a.bimestre for a in lista] == ["4º bimestre", "5º bimestre", "6º bimestre"]
    assert lista[-1].resultado == -89.3 and lista[-1].deducao == 77.0
    assert fonte == lido.fonte and "6º bimestre de 2026" in fonte
    reserva, fonte_reserva = fiscal.avaliacoes_do_ano(None, 2026)
    assert reserva[-1].bimestre == "5º bimestre" and "5º bimestre de 2026" in fonte_reserva


def test_receita_prevista_usa_o_bimestre_lido() -> None:
    lido = aval.ler(_planilha())
    lista, bimestre, fonte = impostos.previsto_do_ano(lido)
    assert bimestre == "5º bimestre" and fonte == lido.fonte
    assert [(r.rtn, r.loa, r.avaliacao) for r in lista] == [
        ("receita_rfb", 2041.0, 2064.9),
        ("arrecadacao_rgps", 793.2, 777.6),
    ]
    reserva, bim_reserva, _ = impostos.previsto_do_ano(None)
    assert reserva == relatorios.RECEITA_PREVISTA
    assert bim_reserva == relatorios.AVALIACAO_DA_RECEITA


# ------------------------------------------------------------------ CBS no TCU


def _acordao(sumario: str | None, titulo: str = "ACÓRDÃO 1/2027") -> dict[str, object]:
    return {"titulo": titulo, "dataSessao": "28/10/2027", "sumario": sumario}


def test_cbs_do_tcu_so_avisa_o_que_mudou() -> None:
    lido = _acordao(
        "REFORMA TRIBUTÁRIA. CÁLCULO DA ALÍQUOTA DE REFERÊNCIA DA CONTRIBUIÇÃO SOCIAL SOBRE BENS "
        "E SERVIÇOS (CBS) PARA 2027 E DO REDUTOR. ALÍQUOTA DE REFERÊNCIA DE 11,3%. REDUTOR DE "
        "44,2%."
    )
    recurso = _acordao("RECURSO. CÁLCULO DA ALÍQUOTA DE REFERÊNCIA DA CBS. PROVIMENTO.")
    novo = _acordao(
        "CÁLCULO DA ALÍQUOTA DE REFERÊNCIA DA CONTRIBUIÇÃO SOCIAL SOBRE BENS E SERVIÇOS (CBS) "
        "PARA 2028. ALÍQUOTA DE REFERÊNCIA DE 8,9%.",
        "ACÓRDÃO 2900/2027",
    )
    assert tramitacao.cbs_nos_acordaos([lido, recurso, _acordao(None)]) == [
        (2027, relatorios.CBS_REFERENCIA_2027, "ACÓRDÃO 1/2027", "28/10/2027")
    ]
    assert tramitacao.cbs_nova([lido, recurso]) == []
    aviso = tramitacao.cbs_nova([novo, lido])
    assert len(aviso) == 1 and "2028" in aviso[0] and "8,9 %" in aviso[0]
    assert tramitacao.CBS_LIDA == (2027, relatorios.CBS_REFERENCIA_2027)
