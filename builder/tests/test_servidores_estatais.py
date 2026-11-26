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


def test_sest_pega_a_planilha_da_edicao_mais_nova() -> None:
    from sacibras.fontes import sest

    html = (
        '<a href="https://x/AnexoISrieshistricasRelatrioAgregado2026anobase2025.xlsx">'
        '<a href="https://x/AnexoISrieshistricasRelatrioAgregado2027anobase2026.xlsx">'
        '<a href="https://x/A%20SEST/AnexoISrieshistricas.xlsx">'
    )
    assert sest.planilha_mais_nova(html) == (
        2027,
        2026,
        "https://x/AnexoISrieshistricasRelatrioAgregado2027anobase2026.xlsx",
    )


def test_sest_soma_as_empresas() -> None:
    from sacibras.fontes import sest

    def empresa(
        ano: int, sigla: str, dep: str, lucro: float, uniao: float, sub: float, afac: float
    ):
        return {
            "ANO": ano,
            "ABREVIAÇÃO": sigla,
            "DEPENDÊNCIA DO TESOURO NACIONAL": dep,
            "RESULTADO LÍQUIDO": lucro * 1e6,
            "DIVIDENDOS E JCP PAGOS À UNIÃO": uniao * 1e6,
            "SUBVENÇÃO": sub * 1e6,
            "AFAC": afac * 1e6,
        }

    linhas = [
        empresa(2024, "ECT", "Não dependente", -2447.2, 0, 0, 0),
        empresa(2024, "EBSERH", "Dependente", 10, 0, 12000, 5),
        empresa(2025, "ECT", "Não dependente", -8457.8, 0, 0, 0),
        empresa(2025, "EBSERH", "Dependente", 20, 0, 13678, 1),
        empresa(2025, "PETROBRAS (Grupo)", "Não dependente", 110605, 22326, 0, 0),
    ]
    lido = sest.montar(linhas, 2026, 2025, "u")  # type: ignore[arg-type]
    assert lido.por_ano[2025].lucro == round(-8457.8 + 20 + 110605, 1)
    assert lido.por_ano[2025].prejuizos == -8457.8
    assert lido.por_ano[2025].aporte == 1.0
    assert lido.subvencoes == [("Ebserh (hospitais universitários)", 13678.0)]
    assert lido.lucros == [("Correios", -2447.2, -8457.8)]
    assert (lido.diretas, lido.dependentes) == (3, 1)
    assert lido.fonte.endswith("2026, ano-base 2025, anexo I")


# ------------------------------------------------------------------ boletim da Previdência


class _Aba:
    """Uma aba de .xls de mentira: o que o leitor do boletim usa do xlrd."""

    def __init__(self, nome: str, linhas: list[list[object]]) -> None:
        self.name = nome
        self.nrows = len(linhas)
        self.ncols = max(len(x) for x in linhas)
        self._linhas = [x + [""] * (self.ncols - len(x)) for x in linhas]

    def cell_value(self, r: int, c: int) -> object:
        return self._linhas[r][c]


class _Livro:
    datemode = 0

    def __init__(self, abas: dict[str, _Aba]) -> None:
        self._abas = abas

    def sheet_by_name(self, nome: str) -> _Aba:
        return self._abas[nome]


SET_2026 = 46266.0  # número de série do Excel de 1/9/2026


def _livro_do_boletim(media_de_setembro: float) -> _Livro:
    """Os quadros 14, 15 e 27 no formato do boletim (set/2026), só com o que se lê."""
    q15 = _Aba(
        "15",
        [
            ["Boletim Estatístico da Previdência Social - Vol. 32 Nº 09", "", "", SET_2026],
            ["GRUPOS DE ESPÉCIES", "QUANTIDADE", "VALOR (R$)", "VALOR MÉDIO (R$)"],
            ["", "Total", "Total", "TOTAL"],
            ["Previdenciários", 35260251.0, 1.0, 1971.92],
            ["Aposentadorias", 24727767.0, 1.0, 2051.0502678834687],
            ["Idade", 14180629.0, 1.0, 1617.7198027844884],
            ["Invalidez", 3445182.0, 1.0, 1811.81],
            ["Tempo de Contribuição", 7101956.0, 1.0, 3032.348472612334],
            ["Rendas Mensais Vitalícias", 44357.0, 1.0, 900.0],
            ["Idade", 1748.0, 1.0, 1.0],
        ],
    )
    q14 = _Aba(
        "14",
        [
            ["Boletim", "", ""],
            ["ANOS/MESES", "", "VALOR MÉDIO (R$)"],
            ["2025", "Novembro", 1825.18],
            ["2026", "Janeiro", 1888.79],
            ["", "Março", 1888.14],
            ["", "Abril(1)", 2807.23],
            ["", "Junho", 1883.65],
            ["", "Setembro", media_de_setembro],
            ["", "Subtotal", "–"],
        ],
    )
    q27 = _Aba(
        "27",
        [
            ["Boletim", "", "", ""],
            ["DISCRIMINAÇÃO", "JUN/18", 46235.0, SET_2026],
            ["Piso Previdenciário - R$", 954.0, 1621.0, 1621.0],
            ["Teto do Sal. Benefício e Sal.Contribuição - R$", 5645.8, 8475.55, 8475.55],
        ],
    )
    return _Livro({"14": q14, "15": q15, "27": q27})


def test_boletim_da_previdencia_le_os_quadros(monkeypatch: pytest.MonkeyPatch) -> None:
    from sacibras.fontes import beps

    monkeypatch.setattr(beps.xlrd, "open_workbook", lambda **_: _livro_do_boletim(1884.19))
    lido = beps.ler(b"", "u")
    assert lido.mes == date(2026, 9, 1)
    assert (round(lido.media, 2), round(lido.idade, 2), round(lido.tempo, 2)) == (
        2051.05,
        1617.72,
        3032.35,
    )
    assert lido.aposentadorias == 24_727_767
    assert (lido.teto, lido.teto_em) == (8475.55, date(2026, 9, 1))
    assert not lido.com_13
    # Mês com o 13º: o valor médio passa do menor do ano.
    monkeypatch.setattr(beps.xlrd, "open_workbook", lambda **_: _livro_do_boletim(2807.0))
    assert beps.ler(b"", "u").com_13


def test_mes_do_13_compara_com_o_menor_do_ano() -> None:
    from sacibras.fontes import beps

    ano = {1: 1888.8, 2: 1889.1, 3: 1888.1, 4: 2807.2, 5: 2803.3, 6: 1883.6}
    assert not beps.mes_do_13(ano, 1)  # o reajuste de janeiro não conta
    assert beps.mes_do_13(ano, 4) and beps.mes_do_13(ano, 5)
    assert not beps.mes_do_13(ano, 6)
    assert beps.mes_do_13({1: 1859.5, 11: 1917.3}, 11)  # nov/2025: +3 %
    with pytest.raises(beps.FonteForaDoArError):
        beps.mes_do_13(ano, 9)


def test_edicoes_do_boletim_da_mais_nova_para_tras() -> None:
    from sacibras.fontes import beps

    base = "https://www.gov.br/previdencia/.../boletins-da-previdencia-social"
    pagina = f'<a href="{base}/2026/beps092026_final.xls">xls</a> <a href="x.pdf">pdf</a>'
    anteriores = (
        f'<a href="{base}/2026/beps062026_final-1.xls">jun</a>'
        f'<a href="{base}/2025/beps122025_final.xls">dez</a>'
        f'<a href="{base}/2026/beps092026_final.xls">de novo</a>'
    )
    lista = beps.edicoes(pagina, anteriores)
    assert [m for m, _ in lista] == [date(2026, 9, 1), date(2026, 6, 1), date(2025, 12, 1)]
    assert lista[1][1].endswith("beps062026_final-1.xls")


def test_aposentadoria_com_o_boletim_lido() -> None:
    from sacibras.fontes import beps

    lido = beps.Boletim(
        date(2026, 12, 1),
        "u",
        25_000_000,
        2100.0,
        1650.0,
        3100.0,
        8475.55,
        date(2026, 12, 1),
        False,
    )
    [cartao], [tabela] = servidores.aposentadoria(lido)
    linhas = {li.rotulo: li.valores for li in tabela.linhas}
    assert linhas["INSS: todas as aposentadorias"] == [2100, 25_000]
    assert linhas["INSS: por idade"][0] == 1650
    assert linhas["Teto do INSS em 2026"][0] == 8476
    assert "INSS em dez/2026" in (tabela.subtitulo or "")
    assert "dez/2026, quadros 15 e 27" in tabela.fonte
    assert "Portaria" not in tabela.fonte and "14.520" in tabela.fonte
    assert "INSS: R$ 2.100" in cartao.detalhe and len(cartao.detalhe) <= 60
