"""Impostos, sem rede: os leitores da Receita e da OCDE e as contas da seção."""

import io
from datetime import date

import openpyxl
import pytest

from sacibras import leis, relatorios
from sacibras.fontes import (
    ocde_receita,
    receita_arrecadacao,
    receita_gastos,
    receita_irpf,
    tesouro_transferencias,
)
from sacibras.rede import FonteForaDoArError
from sacibras.secoes import impostos
from sacibras.secoes.base import Contexto

CABECALHO = (
    "Ano;Mês;UF;IMPOSTO SOBRE IMPORTAÇÃO;IRPF;IRRF - RENDIMENTOS DO TRABALHO;"
    "COFINS - DEMAIS;RECEITA PREVIDENCIÁRIA;IPI - FUMO;CPMF"
)


def test_arrecadacao_le_formatos_e_soma_o_pais() -> None:
    texto = "\n".join(
        [
            CABECALHO,
            # 2002 mistura vírgula de milhar e decimal: fica de fora.
            "2002;Janeiro;SP;1,014,655,323;1;1;1;1;1;1",
            "2026;Setembro;SP;10,5;100;1.000;2.000,25;3000;;",
            "2026;Setembro;RJ;1;10;20;30;40;5;",
            "2026;Outubro;RJ;;;;;;;",
        ]
    )
    dados = receita_arrecadacao.ler_csv(texto)
    setembro = date(2026, 9, 1)
    assert dict(dados["ir"]["SP"])[setembro] == 1100.0  # IRPF + IRRF
    assert dict(dados["cofins_pis"]["SP"])[setembro] == pytest.approx(2000.25)
    assert dict(dados["previdencia"]["BR"])[setembro] == 3040.0
    assert dict(dados["comercio"]["BR"])[setembro] == pytest.approx(11.5)
    assert dict(dados["outros"]["RJ"])[setembro] == 0.0  # a CPMF vazia
    assert all(d.year >= 2003 for g in dados.values() for p in g.values() for d, _ in p)
    assert dict(dados["ipi"]["BR"])[date(2026, 10, 1)] == 0.0


def test_arrecadacao_recusa_arquivo_mudado() -> None:
    with pytest.raises(FonteForaDoArError):
        receita_arrecadacao.ler_csv("Periodo;UF;X\n2026;SP;1")
    with pytest.raises(FonteForaDoArError):
        receita_arrecadacao.ler_csv("Ano;Mês;UF;IPI - FUMO\n2026;Janeiro;SP;1")


def test_grupo_da_coluna() -> None:
    g = receita_arrecadacao.grupo_da_coluna
    assert g("CONTRIBUIÇÃO PARA O PIS/PASEP - FINANCEIRAS") == "cofins_pis"
    assert g("IRPJ - DEMAIS EMPRESAS") == "ir"
    assert g("IMPOSTO S/ OPERAÇÕES FINANCEIRAS") == "iof"
    assert g("CIDE-COMBUSTÍVEIS") == "outros"


def test_ocde_le_csv() -> None:
    texto = (
        "DATAFLOW,REF_AREA,MEASURE,SECTOR,STANDARD_REVENUE,CTRY_SPECIFIC_REVENUE,UNIT_MEASURE,"
        "FREQ,TIME_PERIOD,OBS_VALUE\n"
        "x,BRA,TAX_REV,S13,_T,_T,PT_B1GQ,A,2024,33.68\n"
        "x,BRA,TAX_REV,S13,_T,_T,PT_B1GQ,A,2023,\n"
        "x,OECD_REP,TAX_REV,S13,T_5000,_T,PT_B1GQ,A,2023,10.4\n"
    )
    t = ocde_receita.ler_csv(texto)
    assert t[("BRA", "S13", "_T")] == {2024: 33.68}
    assert t[("OECD_REP", "S13", "T_5000")] == {2023: 10.4}


def _dgt(anos: list[int], total: list[float], pct: list[float], aba_x: str = "Q X") -> bytes:
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = "Q XXVI"
    ws.append(["título"])
    ws.append(["", "EFETIVO", "", "", "PROJEÇÃO"])
    ws.append(["TRIBUTO", *anos])
    ws.append(["COFINS", *[1.0] * len(anos)])
    ws.append(["TOTAL", *total])
    ws.append(["GT / PIB", *pct])
    x = livro.create_sheet(aba_x)
    x.append(["PRINCIPAIS GASTOS TRIBUTÁRIOS"])
    x.append(["GASTO TRIBUTÁRIO", "VALOR (R$)", "%"])
    x.append(["Simples  Nacional", 110e9, 0.2])
    x.append(["Zona Franca de Manaus", 27e9, 0.05])
    x.append(["TOTAL", 534e9, 1.0])
    x.append(["nota de rodapé", 1.0])
    saida = io.BytesIO()
    livro.save(saida)
    return saida.getvalue()


def test_dgt_le_so_os_anos_realizados() -> None:
    corpo = _dgt([2021, 2022, 2023, 2024], [1e9, 2e9, 3e9, 4e9], [0.04, 0.045, 0.0488, 0.05])
    e = receita_gastos.ler_edicao(corpo, 2023)
    assert e.total == {2021: 1e9, 2022: 2e9, 2023: 3e9}
    assert e.pct_pib[2023] == pytest.approx(4.88)
    assert e.principais == [("Simples Nacional", 110e9), ("Zona Franca de Manaus", 27e9)]


def test_dgt_aceita_aba_com_espaco_e_recusa_sem_total() -> None:
    corpo = _dgt([2020, 2021, 2022], [1.0, 2.0, 3.0], [0.1, 0.1, 0.1], aba_x="Q X ")
    assert receita_gastos.ler_edicao(corpo, 2022).principais
    livro = openpyxl.Workbook()
    livro.active.title = "Q XXVI"
    livro.create_sheet("Q X")
    saida = io.BytesIO()
    livro.save(saida)
    with pytest.raises(FonteForaDoArError):
        receita_gastos.ler_edicao(saida.getvalue(), 2022)


def test_dgt_acha_as_edicoes_na_listagem() -> None:
    base = "https://www.gov.br/x/gastos-tributarios-bases-efetivas"
    html = (
        f'<a href="{base}/dgt-bases-efetivas-2016-serie-2014-a-2019-quadros/view">'
        f'<a href="{base}/dgt-bases-efetivas-2023-serie-2021-a-2026-quadros.xlsx/view">'
        f'<a href="{base}/dgt-bases-efetivas-2023-serie-2021-a-2026-base-conceitual.pdf/view">'
    )
    achadas = receita_gastos.edicoes_na_listagem(html)
    assert sorted(achadas) == [2016, 2023]
    assert achadas[2023].endswith("quadros.xlsx/@@download/file")


def test_contas_da_secao() -> None:
    meses = [(date(2026, m, 1), 1.0) for m in (1, 2, 3)]
    indice = impostos.indice_de_precos(meses)
    assert indice[date(2026, 3, 1)] == pytest.approx(1.01**3)
    real = impostos.a_precos_de([(date(2026, 1, 1), 100.0)], indice, date(2026, 3, 1))
    assert real[0][1] == pytest.approx(100 * 1.01**2)
    nivel = {2013: 100.0, 2023: 100.0 * 1.02**10}
    assert impostos.media_geometrica_da_variacao(nivel, list(range(2014, 2024))) == (
        pytest.approx(2.0)
    )
    assert impostos.media_geometrica_da_variacao({2014: 1.0}, [2014, 2015]) is None
    assert impostos.correlacao([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0)
    assert impostos.correlacao([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)
    assert impostos.em_palavras(-0.05) == "praticamente nenhuma relação"


def test_dgt_regioes_e_previsao_do_ploa() -> None:
    livro = openpyxl.Workbook()
    iv = livro.active
    iv.title = "Q IV"
    iv.append(["QUADRO IV"])
    iv.append(
        ["FUNÇÃO / GASTO", "NORTE ", "NORDESTE ", "CENTRO-OESTE ", "SUDESTE ", "SUL ", "TOTAL "]
    )
    iv.append(["Agricultura", 1.0, 1.0, 1.0, 1.0, 1.0, 5.0])
    iv.append(["TOTAL", 10.0, 20.0, 30.0, 40.0, 50.0, 150.0])
    assert receita_gastos.ler_regioes(list(iv.iter_rows(values_only=True))) == {
        "Norte": 10.0,
        "Nordeste": 20.0,
        "Centro-Oeste": 30.0,
        "Sudeste": 40.0,
        "Sul": 50.0,
    }
    assert receita_gastos.ler_regioes([("sem cabeçalho",), ("TOTAL", 1.0)]) == {}
    vi = livro.create_sheet("Q VI")
    vi.append(["TRIBUTO", "VALOR", "PART. %"])
    vi.append(["COFINS", 1e9, 1.0])
    vi.append(["TOTAL", 612e9, 4.43, 20.2, 100])
    saida = io.BytesIO()
    livro.save(saida)
    previsao = receita_gastos.ler_previsao(saida.getvalue(), 2026)
    assert (previsao.total, previsao.pct_pib) == (612e9, 4.43)


def test_doze_meses_por_uf() -> None:
    meses = [(date(2025 + (m > 12), (m - 1) % 12 + 1, 1), 1.0) for m in range(1, 22)]  # 21 meses
    dados = {"ir": {"SP": meses, "BR": meses}, "ipi": {"SP": meses[-1:], "RJ": meses[:3]}}
    por_uf, ultimo = receita_arrecadacao.doze_meses_por_uf(dados)
    assert ultimo == date(2026, 9, 1)
    assert por_uf == {"SP": 13.0, "RJ": 0.0}


def _irpf(linhas: list[list[object]]) -> bytes:
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = "Tab8"
    ws.append(["Tabela 8 - Resumo das declarações"])
    ws.append(["tipo_formulario", "uf", *receita_irpf.COLUNAS.values()])
    for linha in linhas:
        ws.append(linha)
    saida = io.BytesIO()
    livro.save(saida)
    return saida.getvalue()


def test_irpf_soma_por_faixa_e_poe_em_ordem() -> None:
    corpo = _irpf(
        [
            ["Completo", "SP", "Mais de 320", 10, 100.0, 200.0, 700.0, 300.0, 20.0],
            ["Completo", "SP", "De 1/2 a 1", 5, 10.0, 0.0, 0.0, 0.0, 0.0],
            ["Simplificado", "AC", "Mais de 320", "x", 0.0, 0.0, 0.0, 0.0, 0.0],
            ["Completo", "RJ", "De 10 a 15", 1, 80.0, 10.0, 10.0, 0.0, 10.0],
            ["Completo", "RJ", "Até 1/2", 1, 1.0, 0.0, 0.0, 0.0, 0.0],
            ["Completo", "RJ", "De 2 a 3", 1, 1.0, 0.0, 0.0, 0.0, 0.0],
            ["Simplificado", "RJ", "De 10 a 15", 1, 100.0, 0.0, 0.0, 0.0, 10.0],
        ]
    )
    faixas = receita_irpf.ler_planilha(corpo)
    assert [f.nome for f in faixas] == [
        "Até 1/2",
        "De 1/2 a 1",
        "De 2 a 3",
        "De 10 a 15",
        "Mais de 320",
    ]
    topo = faixas[-1]
    assert (topo.declarantes, topo.renda, topo.dividendos) == (10.0, 1000.0, 300.0)
    assert topo.aliquota == pytest.approx(2.0)
    assert faixas[3].aliquota == pytest.approx(10.0)


def test_irpf_acha_a_planilha_mais_nova() -> None:
    base = "https://www.gov.br/x/grandes-numeros-do-IRPF-2008-a-2025"
    html = (
        f'<a href="{base}/grandes-numeros-do-irpf-2024-ano-calendario-2023-tabelas-1/view">'
        f'<a href="{base}/grandes-numeros-do-irpf-2025-ano-calendario-2024-tabelas/view">'
        f'<a href="{base}/grandes-numeros-do-irpf-2025-ano-calendario-2024-metadados/view">'
    )
    ano, url = receita_irpf.mais_nova(html)
    assert ano == 2024 and url.endswith("2024-tabelas/@@download/file")
    with pytest.raises(FonteForaDoArError):
        receita_irpf.mais_nova("<html></html>")


def test_reforma_esta_inteira() -> None:
    assert [p.quando for p in leis.REFORMA_DO_CONSUMO][:2] == ["2026", "2027"]
    assert all(p.muda and p.norma.startswith("ADCT") for p in leis.REFORMA_DO_CONSUMO)


def test_regimes_proprios_tem_o_artigo_de_cada_um() -> None:
    temas = [r.tema for r in leis.REGIMES_PROPRIOS]
    assert len(temas) == len(set(temas))
    assert all(r.norma.startswith("LC 214/2025, art") and r.diz for r in leis.REGIMES_PROPRIOS)
    assert any("10,85 %" in r.diz for r in leis.REGIMES_PROPRIOS)  # art. 233, LC 227/2026


def test_bases_contra_outros_paises_no_ano_comum() -> None:
    """O Brasil vai até 2024; as médias, até 2023: vale 2023. O salário soma contribuições
    sociais e folha."""
    dados: ocde_receita.Tabela = {}
    for pais, anos in (("BRA", (2023, 2024)), ("OECD_REP", (2023,)), ("A9", (2022, 2023))):
        for ano in anos:
            for cat, v in (("T_1100", 3.0), ("T_1200", 3.6), ("T_5110", 10.9), ("T_2000", 8.0)):
                dados.setdefault((pais, "S13", cat), {})[ano] = v
    dados[("BRA", "S13", "T_3000")] = {2023: 0.56}
    dados[("CHL", "S13", "T_1100")] = {2023: 1.5}
    ano, linhas = impostos.tabela_de_bases(dados, ["BRA", "OECD_REP", "A9", "CHL", "XXX"], str)
    assert ano == 2023
    assert [li.rotulo for li in linhas] == ["BRA", "OECD_REP", "A9", "CHL"]  # sem dado, fora
    assert linhas[0].valores == [3.0, 3.6, 10.9, None, 8.6]
    assert linhas[3].valores == [1.5, None, None, None, None]


def test_setores_le_meses_abreviados_e_so_ano_fechado() -> None:
    cab = "Ano;Mês;Seção - Sigla;Seção - Nome;II;IRPJ"
    meses = ["Jan", "Fev ", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    linhas = [f"2025;{m};C;Indústrias  de transformação;1.000,50;9" for m in meses]
    linhas += ["2025;Jan;K;Atividades financeiras;;5", "2026;Jan;C;Indústrias de transformação;1;1"]
    por_ano = receita_arrecadacao.ler_setores("\n".join([cab, *linhas]))
    assert list(por_ano) == [2025]
    assert por_ano[2025]["Indústrias de transformação"] == pytest.approx(12 * 1009.5)
    assert por_ano[2025]["Atividades financeiras"] == 5.0
    with pytest.raises(FonteForaDoArError):
        receita_arrecadacao.ler_setores("Ano;Mês;UF;X\n2025;Jan;SP;1")


def test_previsto_e_divida_ativa_tem_o_que_a_tela_usa() -> None:
    assert {r.rtn for r in relatorios.RECEITA_PREVISTA} == {"receita_rfb", "arrecadacao_rgps"}
    assert all(r.loa > 0 and r.avaliacao > 0 for r in relatorios.RECEITA_PREVISTA)
    assert set(relatorios.DIVIDA_ATIVA_RECUPERADO) <= set(relatorios.DIVIDA_ATIVA_ESTOQUE)


# ------------------------------------------------------------------ FPE, FPM, retido, reforma


def _csv_transferencias(linhas: list[str], municipio: bool = False) -> bytes:
    cab = "UF;ANO;Mês;1º Decêndio;2º Decêndio;3º Decêndio;Item transferência;Transferência;"
    if municipio:
        cab = "Município;" + cab
    return "\r\n".join([cab, *linhas]).encode("latin-1")


def test_transferencias_somam_os_decendios_so_das_linhas_pedidas() -> None:
    corpo = _csv_transferencias(
        [
            "AC;2026;09;10.5;20;30;FPE;FPE;",
            "AC;2026;09;1;1;1;FPE;FUNDEB;",
            "AC;2026;08;5;0;0;FPE;FPE;",
            "AL;2026;09;0;0;;FPE;FPE;",
        ]
    )
    lido = tesouro_transferencias.ler_csv(corpo, {("FPE", "FPE")})
    assert lido == {
        "AC": {date(2026, 9, 1): 60.5, date(2026, 8, 1): 5.0},
        "AL": {date(2026, 9, 1): 0.0},
    }
    municipios = _csv_transferencias(
        [
            "Acrelândia;AC;2026;09;1;2;3;FPM;FPM;",
            "Bujari;AC;2026;09;4;0;0;FPM 1%;FPM 1%;",
            "Bujari;AC;2026;09;9;9;9;ITR;ITR;",
        ],
        municipio=True,
    )
    fpm = tesouro_transferencias.ler_csv(municipios, {("FPM", "FPM"), ("FPM 1%", "FPM 1%")})
    assert fpm == {"AC": {date(2026, 9, 1): 10.0}}


def test_transferencias_doze_meses_ate_o_mes_que_todos_tem() -> None:
    por_uf = {
        "AC": {date(2025, m, 1): 1.0 for m in range(1, 13)} | {date(2026, 1, 1): 1.0},
        "AL": {date(2025, m, 1): 2.0 for m in range(1, 13)},
    }
    soma, ate = tesouro_transferencias.doze_meses(por_uf)
    assert ate == date(2025, 12, 1)
    assert soma == {"AC": 12.0, "AL": 24.0}


def test_irpf_le_o_imposto_pago_antes_e_o_acerto() -> None:
    faixa = receita_irpf.Faixa("De 5 a 7", tributavel=100.0, imposto=8.0, pago=10.0)
    faixa.a_restituir = 2.0
    assert faixa.aliquota == pytest.approx(8.0)
    assert {"pago", "a_pagar", "a_restituir"} <= set(receita_irpf.COLUNAS)


def test_ibs_vai_para_o_destino_pela_conta_do_adct() -> None:
    retido = leis.IBS_PELA_RECEITA_ANTIGA
    assert [retido[a] for a in (2029, 2032, 2033, 2034)] == [80.0, 80.0, 90.0, 88.0]
    assert retido[2077] == pytest.approx(2.0)
    assert min(retido) == 2029 and max(retido) == 2077
    _, graficos, tabelas, _ = impostos._reforma_regras(Contexto())
    destino = next(g for g in graficos if g.id == "reforma-destino")
    for k in range(len(destino.series[0].pontos)):
        total = sum(s.pontos[k][1] or 0 for s in destino.series)
        assert total == pytest.approx(100.0, abs=0.2)  # cada parte arredondada em uma casa
    seguro = next(s for s in destino.series if s.id == "seguro")
    assert seguro.pontos[0][1] == pytest.approx(1.0)  # 5 % dos 20 % que sobram em 2029
    regras = tabelas[0]
    assert all(len(li.textos) == 2 and li.textos[1] for li in regras.linhas)
    assert any("0,25 %" in li.textos[0] for li in regras.linhas)


def test_dgt_le_funcao_beneficio_e_tributo() -> None:
    livro = openpyxl.Workbook()
    v = livro.active
    v.title = "Q V"
    v.append(["FUNÇÃO ORÇAMENTÁRIA", "VALOR", "%"])
    v.append(["Saúde", 30.0, 0.3])
    v.append(["Indústria", 70.0, 0.7])
    v.append(["TOTAL", 100.0, 1])
    iii = livro.create_sheet("Q III")
    iii.append(["FUNÇÃO ORÇAMENTÁRIA / GASTO TRIBUTÁRIO", "VALOR", "%"])
    iii.append(["Indústria", 70.0, 0.7])
    iii.append(["Zona Franca de Manaus", 60.0, 0.6])
    iii.append(["Rota 2030", 10.0, 0.1])
    iii.append(["Saúde", 30.0, 0.3])
    iii.append(["Medicamentos", 30.0, 0.3])
    iii.append(["TOTAL", 100.0, 1])
    vi = livro.create_sheet("Q VI")
    vi.append(["TRIBUTO", "VALOR", "PART. %"])
    vi.append(["PIB", "ARRECADAÇÃO", "GASTOS TRIBUTÁRIOS"])
    vi.append(["Imposto sobre a Renda Pessoa Física - IRPF", 40.0, 0.4, 3.0])
    vi.append(["Contribuição Social para o PIS-PASEP", 60.0, 0.6, 5.0])
    vi.append(["TOTAL", 100.0, 1.0, 8.0])
    vi.append(["ARRECADAÇÃO*", 2000.0, 20.0, 100])
    aba = lambda n: list(livro[n].iter_rows(values_only=True))  # noqa: E731
    funcoes = receita_gastos.ler_funcoes(aba("Q V"))
    assert funcoes == [("Indústria", 70.0), ("Saúde", 30.0)]
    assert receita_gastos.ler_beneficios(aba("Q III"), {n for n, _ in funcoes}) == {
        "Indústria": [("Zona Franca de Manaus", 60.0), ("Rota 2030", 10.0)],
        "Saúde": [("Medicamentos", 30.0)],
    }
    assert receita_gastos.ler_tributos(aba("Q VI")) == [
        ("Contribuição Social para o PIS-PASEP", 60.0),
        ("Imposto sobre a Renda Pessoa Física - IRPF", 40.0),
    ]
    assert receita_gastos.ler_funcoes([("sem cabeçalho",)]) == []
