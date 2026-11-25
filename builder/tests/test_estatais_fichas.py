"""Uma estatal por dentro: a planilha da Sest (anexo I) e a ficha de cada empresa."""

import io

import openpyxl  # type: ignore[import-untyped]

from sacibras.fontes import sest
from sacibras.secoes import estatais

FONTE = f"{sest.FONTE} 2026, ano-base 2025, anexo I"

CABECALHO = [
    "ANO",
    "CÓDIGO",
    "ABREVIAÇÃO",
    "NOME",
    "SETOR RELATÓRIO",
    "MINISTÉRIO SUPERVISOR",
    "DEPENDÊNCIA DO TESOURO NACIONAL",
    "ANO DE CRIAÇÃO",
    "ATIVO",
    "PASSIVO EXIGÍVEL",
    "PATRIMÔNIO LÍQUIDO",
    "GASTO COM PESSOAL PRÓPRIO",
    "IMPOSTOS, TAXAS E CONTRIBUIÇÕES",
    "FATURAMENTO",
    "RESULTADO LÍQUIDO",
    "DIVIDENDOS E JCP PAGOS",
    "DIVIDENDOS E JCP PAGOS À UNIÃO",
    "SUBVENÇÃO",
    "AFAC",
    "RECEITA DA INTERMEDIAÇÃO FINANCEIRA",
    "RECEITA DA PRESTAÇÃO DE SERVIÇOS E TARIFAS",
    " ORÇAMENTO INVESTIMENTO APROVADO ",
    " ORÇAMENTO INVESTIMENTO EXECUTADO ",
    "QTD_EMPREGADOS",
]


def _linha(ano: int, sigla: str, dep: str, lucro: float, pessoal: float, **x: float) -> list:
    return [
        ano,
        1,
        sigla,
        f"Empresa {sigla}",
        x.get("setor", "Financeiro" if x.get("banco") else "Energia"),  # type: ignore[arg-type]
        "Ministério da Fazenda",
        dep,
        1950,
        100e9,
        60e9,
        40e9,
        pessoal,
        1e9 if ano < 2025 else 1e6,
        0 if x.get("banco") else 50e9,
        lucro,
        2e9,
        1e9,
        x.get("subvencao", 0),
        0,
        30e9 if x.get("banco") else 0,
        5e9 if x.get("banco") else 0,
        "-",
        "#N/A",
        1000,
    ]


def _planilha() -> bytes:
    livro = openpyxl.Workbook()
    folha = livro.active
    folha.append(CABECALHO)
    siglas = ["A", "B", "C", "D", "E", "PETROBRAS (Grupo)"]
    for ano in (2024, 2025):
        # Em 2025 o pessoal vem em R$ mil, como na edição de 2026.
        pessoal = 2e9 if ano == 2024 else 2.1e6
        for i, s in enumerate(siglas):
            folha.append(_linha(ano, s, "Não dependente", (i + 1) * 1e9, pessoal))
        folha.append(_linha(ano, "BANCO", "Não dependente", 3e9, pessoal, banco=1))
        folha.append(_linha(ano, "HOSP", "Dependente", -0.2e9, pessoal, subvencao=8e9))
    saida = io.BytesIO()
    livro.save(saida)
    return saida.getvalue()


def test_le_a_planilha_e_corrige_a_escala_da_dva() -> None:
    linhas = sest.empresas(_planilha())
    assert len(linhas) == 16
    x = next(x for x in linhas if x.sigla == "A" and x.ano == 2025)
    assert x["pessoal"] == 2.1e9  # vezes mil: a mediana de 2025/2024 deu 0,001
    assert x["impostos"] == 1e9
    assert x["investimento"] is None and x["investimento_aprovado"] is None
    assert not x.dependente
    assert next(x for x in linhas if x.sigla == "HOSP").dependente


def test_ficha_de_cada_estatal() -> None:
    fichas = {f.id: f for f in estatais.fichas(FONTE, sest.empresas(_planilha()))}
    assert len(fichas) == 8
    p = fichas["petrobras"]
    assert p.nome == "Petrobras"
    rotulos = [c.rotulo for c in p.cartoes]
    assert rotulos == ["Lucro", "Receita", "Retorno sobre o patrimônio", "Saldo com a União"]
    lucro, receita, roe, saldo = p.cartoes
    assert receita.valor == 50.0
    assert lucro.valor == 6.0 and lucro.unidade == "R$ bilhões"
    assert lucro.detalhe.startswith("1º lugar em lucro")
    assert roe.valor == 15.0  # 6 bi sobre 40 bi
    assert saldo.valor == 1.0
    assert all(len(c.detalhe) <= 60 for f in fichas.values() for c in f.cartoes)
    # Os outros gráficos atrás da lista; sem investimento na planilha, sem o gráfico dele.
    opcoes = [g.rotulo_opcao for g in p.grafico.alternativas]
    assert "Balanço" in opcoes and "Investimento" not in opcoes
    linhas = {li.rotulo: li.valores for li in p.tabela.linhas}
    assert linhas["Margem líquida"] == [12.0, 12.0]  # 6 bi sobre 50 bi
    assert "Execução do orçamento" not in linhas


def test_banco_e_dependente() -> None:
    fichas = {f.id: f for f in estatais.fichas(FONTE, sest.empresas(_planilha()))}
    banco = fichas["banco"]
    receita = next(c for c in banco.cartoes if c.rotulo == "Receita")
    assert receita.valor == 35.0  # intermediação mais tarifas
    hosp = fichas["hosp"]
    assert hosp.cartoes[0].rotulo == "Prejuízo"
    assert [c.rotulo for c in hosp.cartoes][2] == "Subvenção do Tesouro"
    assert hosp.cartoes[-1].valor == -7.0  # pagou 1 bi, recebeu 8 bi
    assert "Dependente do Tesouro" in hosp.descricao


def test_retorno_contra_o_juro_da_divida() -> None:
    from datetime import date

    taxa = [(date(2024, 12, 1), 10.0), (date(2025, 12, 1), 13.0)]
    _, [desenho], [tabela] = estatais.retorno(FONTE, sest.empresas(_planilha()), taxa, "BC")
    juro = next(s for s in desenho.series if s.id == "juro")
    assert [v for _, v in juro.pontos] == [10.0, 13.0]
    petro = next(s for s in desenho.series if s.id == "petrobras")
    assert [v for _, v in petro.pontos] == [15.0, 15.0]  # 6 bi sobre 40 bi
    assert "acima dele: Petrobras" in desenho.manchete
    # Sete não dependentes; a dependente fica fora da tabela.
    assert len(tabela.linhas) == 7
    assert all("HOSP" not in li.rotulo for li in tabela.linhas)
    primeira = tabela.linhas[0]
    assert primeira.grupo.startswith("Renderam acima do juro em 2025")
    assert primeira.valores[2] == 2.0  # 15 % contra 13 %
