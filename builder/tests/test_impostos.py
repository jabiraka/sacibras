"""Impostos, sem rede: os leitores da Receita e da OCDE e as contas da seção."""

import io
from datetime import date

import openpyxl
import pytest

from sacibras import relatorios
from sacibras.fontes import ocde_receita, receita_arrecadacao, receita_gastos
from sacibras.rede import FonteForaDoArError
from sacibras.secoes import impostos

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


def test_estudos_tem_fonte_e_trecho_lido() -> None:
    for e in relatorios.EFEITOS_DE_IMPOSTO:
        assert e.fonte and e.leitura and e.unidade
        assert '"' in e.leitura or "“" in e.leitura  # o trecho original, entre aspas
