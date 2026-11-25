"""Servidores (folha por esfera, por tipo e por poder; rendimento contra o privado) e
estatais (dividendos, a conta do ano, o primário)."""

from datetime import date

import pytest

from sacibras import relatorios
from sacibras.fontes import fmi_pessoal, siconfi
from sacibras.secoes import estatais, servidores

MESES = [date(2024 + i // 12, i % 12 + 1, 1) for i in range(24)]


def fixo(v: float) -> list[tuple[date, float]]:
    return [(d, v) for d in MESES]


PIB = [(d, 12 * 10_000.0) for d in MESES]


def test_rendimento_do_servidor_contra_o_privado() -> None:
    por_posicao = {
        servidores.ESTATUTARIO: fixo(6000.0),
        servidores.PRIVADO_COM_CARTEIRA: fixo(3000.0),
        "31723": fixo(2400.0),
    }
    pessoas = {servidores.ESTATUTARIO: [(MESES[-1], 8000.0)]}
    instrucao = {"11632": [(date(2025, 10, 1), 7500.0)]}
    [cartao], [grafico], [tabela] = servidores.rendimento(
        por_posicao, pessoas, instrucao, date(2020, 1, 1)
    )
    assert cartao.valor == 6000.0 and "2,0 vezes" in cartao.detalhe
    assert len(cartao.detalhe) <= 60
    assert grafico.series[0].nome == "Servidor estatutário ou militar"
    linhas = {li.rotulo: li.valores for li in tabela.linhas}
    assert linhas["Servidor estatutário ou militar"] == [6000.0, 8000, 200]
    assert linhas["Setor privado, sem carteira"] == [2400.0, None, 80]
    assert linhas["Com ensino superior completo (4º tri/2025)"] == [7500.0, None, 250]


def test_folha_da_uniao_soma_a_folha() -> None:
    det = {
        "pessoal_pago": fixo(100.0),
        "ativo_civil": fixo(45.0),
        "ativo_militar": fixo(10.0),
        "inativo_civil": fixo(25.0),
        "inativo_militar": fixo(15.0),
    }
    [cartao], [grafico], [tabela] = servidores.folha_da_uniao(det, PIB, "teste", date(2020, 1, 1))
    assert cartao.valor == pytest.approx(40.0)
    assert len(grafico.series) == 4
    assert sum(li.valores[1] for li in tabela.linhas) == pytest.approx(100.0)  # type: ignore[misc]
    assert tabela.linhas[-1].valores[0] == pytest.approx(0.1)


def test_por_esfera_fecha_com_o_governo_geral() -> None:
    valores: fmi_pessoal.Valores = {}
    partes = {"S1311B": (200.0, 100.0), "S1312MIXED": (500.0, 300.0), "S1313MIXED": (300.0, 100.0)}
    for setor, (ativos, inativos) in {**partes, "S13": (1000.0, 500.0)}.items():
        for indicador, v in ((fmi_pessoal.ATIVOS, ativos), (fmi_pessoal.INATIVOS, inativos)):
            valores[("BRA", setor, indicador, "XDC")] = {2025: v * 1e9}
            valores[("BRA", setor, indicador, "POGDP_PT")] = {2024: v / 110, 2025: v / 100}
    [grafico], [tabela] = servidores.por_esfera(valores)
    assert sum(li.valores[1] for li in tabela.linhas[:-1]) == pytest.approx(100.0, abs=0.2)  # type: ignore[misc]
    assert tabela.linhas[-1].valores == [1500.0, 100.0, 15.0]
    assert grafico.series[1].pontos[-1] == (date(2025, 1, 1), 8.0)


def test_folha_contra_a_mediana_dos_grupos() -> None:
    a, i = fmi_pessoal.ATIVOS, fmi_pessoal.INATIVOS
    paises = {
        "BRA": {a: {2025: 11.0}, i: {2025: 4.5}},
        "TUR": {a: {2025: 9.0}, i: {2025: 0.0}},
        "ZAF": {a: {2024: 13.0}, i: {2024: 0.4}},
        "DEU": {a: {2024: 8.0}},
    }
    grupos = {"G200": ["BRA", "TUR", "ZAF"], "G205": ["BRA"], "G110": ["DEU"]}
    [cartao], [tabela] = servidores.contra_os_paises(paises, grupos)
    assert tabela.colunas == ["Brasil", "Emergentes (2)", "América Latina (0)", "Avançados (1)"]
    assert tabela.linhas[0].valores == [11.0, 11.0, None, 8.0]
    assert tabela.linhas[1].valores[:2] == [4.5, 0.4]  # o zero da Turquia fica fora
    assert cartao.valor == 11.0 and "emergentes: 11,0 %" in cartao.detalhe


def test_por_poder_e_aposentadoria_usam_as_leituras() -> None:
    gasto, remuneracao = servidores.por_poder(2025, {"E": (300e9, 1), "J": (60e9, 90)})
    assert [li.rotulo for li in gasto.linhas] == ["Executivo", "Judiciário"]
    assert gasto.linhas[0].valores == [300.0, 83.3]
    civis = relatorios.SERVIDORES_POR_PODER
    # As quantidades por poder somam os totais que o relatório escreve por extenso.
    assert sum(p.ativos for p in civis) == 792_702
    assert sum(p.aposentados for p in civis) == 467_837
    assert sum(p.pensionistas for p in civis) == 296_641
    assert remuneracao.linhas[0].rotulo == "Legislativo (com o TCU)"
    [cartao], [tabela] = servidores.aposentadoria()
    assert cartao.valor == pytest.approx(13_344.99, abs=0.01)
    assert len(cartao.detalhe) <= 60
    assert any(li.rotulo.startswith("Teto do INSS") for li in tabela.linhas)


def test_pessoal_do_poder_soma_os_orgaos() -> None:
    def item(orgao: str, conta: str, valor: float, coluna: str = "TOTAL (ÚLTIMOS 12 MESES) (a)"):  # type: ignore[no-untyped-def]
        return {
            "instituicao": orgao,
            "rotulo": "Padrão",
            "cod_conta": conta,
            "coluna": coluna,
            "valor": valor,
        }

    itens = [
        item("TRT 1", siconfi.CONTA_BRUTA, 10.0),
        item("TRT 1", siconfi.CONTA_LIQUIDA, 8.0),
        item("TRT 2", siconfi.CONTA_BRUTA, 5.0, "TOTAL (ÚLTIMOS 12 MESES)  (a)"),
        item("TRT 2", siconfi.CONTA_BRUTA, 99.0, "<MR>"),
        item("DPU", siconfi.CONTA_LIQUIDA, 1.0),
    ]
    assert siconfi.pessoal_do_poder(itens) == (16.0, 3)
    assert siconfi.pessoal_do_poder([]) is None


def test_dividendos_por_empresa() -> None:
    det = {nome: fixo(0.0) for nome in (*estatais.EMPRESAS, *estatais.OUTRAS)}
    det |= {"div_bndes": fixo(1000.0), "div_petrobras": fixo(500.0), "div_demais": fixo(100.0)}
    det["dividendos"] = fixo(1600.0)
    [cartao], [grafico], [tabela] = estatais.dividendos(det, PIB, "teste", date(2020, 1, 1))
    assert cartao.valor == pytest.approx(19.2) and "BNDES" in cartao.detalhe
    assert len(cartao.detalhe) <= 60
    assert [s.nome for s in grafico.series][-1] == "Demais"
    assert tabela.colunas == ["2024", "2025", "12 meses até dez/2025"]
    linhas = {li.rotulo: li.valores for li in tabela.linhas}
    assert linhas["Total"] == [19.2, 19.2, 19.2] and linhas["Demais"] == [1.2, 1.2, 1.2]


def test_a_conta_do_ano_fecha_com_a_da_sest() -> None:
    cartoes, [grafico], tabelas = estatais.conta_do_ano()
    saldo = {c.id: c for c in cartoes}["estatais-saldo"]
    # "o retorno financeiro das estatais federais em 2025 [...] foi de R$ 13,1 bilhões" (p. 17).
    assert saldo.valor == pytest.approx(13.12, abs=0.01)
    assert all(len(c.detalhe) <= 60 for c in cartoes)
    conta = tabelas[0]
    por_linha = {li.rotulo: li.valores for li in conta.linhas}
    for i in range(len(conta.colunas)):
        soma = sum(v[i] for nome, v in por_linha.items() if nome.startswith(("Div", "Sub", "Apo")))  # type: ignore[misc]
        assert soma == pytest.approx(por_linha["Saldo para a União"][i], abs=0.11)  # type: ignore[arg-type]
    assert sum(v for _, v in relatorios.SUBVENCOES_2025) == pytest.approx(
        relatorios.ESTATAIS_POR_ANO[2025].subvencao, abs=1.0
    )
    assert grafico.tipo == "barras"
    # A resposta da pergunta diz que os dividendos superam os repasses todo ano e que o saldo
    # de 2025 foi o menor: se a leitura nova mudar isso, o texto muda junto.
    saldos = {
        a: x.dividendos_uniao - x.subvencao - x.aporte
        for a, x in relatorios.ESTATAIS_POR_ANO.items()
    }
    assert min(saldos.values()) > 0 and min(saldos, key=lambda a: saldos[a]) == max(saldos)


def test_primario_das_estatais_troca_o_sinal() -> None:
    [cartao], [grafico], _ = estatais.primario(
        fixo(0.05), fixo(0.02), fixo(0.0), fixo(600.0), "teste", date(2020, 1, 1)
    )
    assert cartao.valor == pytest.approx(-7.2) and cartao.detalhe.startswith("déficit")
    assert grafico.series[0].pontos[-1][1] == -0.05
