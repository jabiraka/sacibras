"""As estatais dos estados: a leitura do arquivo do Tesouro e a conta do caixa."""

from sacibras.fontes import tesouro_estaduais
from sacibras.secoes import estatais_estaduais, estatais_estaduais_fichas

CABECA = (
    "Estado;Nome_estado;emp;dep;lucros;Dividendos;Subvenção;Reforço de Capital;"
    "PL;qde_empregados;desp_pessoal;desp_investimento\n"
)


def _ano(ano: int) -> list[tesouro_estaduais.EmpresaEstadual]:
    corpo = (
        "MG;Minas Gerais;COMPANHIA  DE LUZ;Não Dependente;5000000000,5;800000000;0;0;"
        "9e9;100;2e7;NA\n"
        "AC;Acre;Companhia de Armazéns;Dependente;NA;0;2000000000;500000000;0;;;\n"
    )
    return tesouro_estaduais.ler((CABECA + corpo).encode(), ano)


def test_le_o_arquivo_do_tesouro() -> None:
    luz, armazem = _ano(2024)
    assert luz.lucro == 5000000000.5 and not luz.dependente
    assert armazem.dependente and armazem.lucro == 0.0 and armazem.capital == 5e8


def test_conta_do_caixa_dos_estados() -> None:
    _, [desenho], [conta, estados, empresas] = estatais_estaduais.pecas(
        "teste", [*_ano(2023), *_ano(2024)]
    )
    saldo = {s.id: s for s in desenho.series}["saldo"]
    assert [v for _, v in saldo.pontos] == [-1.7, -1.7]
    assert conta.colunas == ["2023", "2024"]
    # De quem mais pôs para quem mais recebeu.
    assert [li.rotulo for li in estados.linhas] == ["Acre (1)", "Minas Gerais (1)"]
    assert estados.linhas[0].valores == [0, 2000, 500, -2500, -5000, 0]
    assert [li.rotulo for li in empresas.linhas] == [
        "Companhia de Luz (MG)",
        "Companhia de Armazéns (AC)",
    ]
    assert empresas.linhas[1].valores[0] == -2000


def _linha(ano: int, nome: str, **campos: float) -> tesouro_estaduais.EmpresaEstadual:
    base = {"lucro": 1e8, "dividendos": 0.0, "subvencao": 0.0, "capital": 0.0}
    extras = {"patrimonio": 2e9, "empregados": 20000.0, "pessoal": 2e9, "investimento": 1e8}
    return tesouro_estaduais.EmpresaEstadual(
        ano=ano,
        uf="MG",
        estado="Minas Gerais",
        nome=nome,
        dependente=False,
        **{**base, **extras, **campos},  # type: ignore[arg-type]
    )


def test_casa_a_empresa_que_mudou_de_nome() -> None:
    anos = [
        _linha(2023, "Companhia de Gás de Minas Gerais"),
        _linha(2024, "COMPANHIA DE GÁS DE MINAS GERAIS  GASMIG"),
        _linha(2023, "Companhia Energética de Minas Gerais"),
        _linha(2024, "COMPANHIA ENERGÉTICA DE MINAS GERAIS  CEMIG"),
    ]
    cadeias = estatais_estaduais_fichas.casar(anos)
    assert sorted([x.nome[:16].lower() for x in c] for c in cadeias) == [
        ["companhia de gás", "companhia de gás"],
        ["companhia energé", "companhia energé"],
    ]


def test_erro_obvio_fica_em_branco() -> None:
    nome = "Companhia de Saneamento"
    anos = [
        # O ano em outra unidade: tudo mil vezes menor.
        _linha(2021, nome, patrimonio=2e6, pessoal=2e6, lucro=1e5),
        _linha(2022, nome, empregados=57.0),  # destoa dos dois vizinhos
        _linha(2023, nome, lucro=-5e8),  # lucro muda muito: fica
        _linha(2024, nome, pessoal=1e8),  # folha de R$ 5 mil por pessoa no ano
    ]
    fora = estatais_estaduais_fichas.limpar(anos).fora
    assert fora == {
        2021: {"patrimonio", "pessoal", "lucro"},
        2022: {"empregados"},
        2024: {"pessoal"},
    }
    ficha = estatais_estaduais_fichas.ficha(anos, "teste", "mg-saneamento")
    linhas = {li.rotulo: li.valores for li in ficha.tabela.linhas}
    assert linhas["Empregados"] == [20000, None, 20000, 20000]
    assert linhas["Lucro ou prejuízo"] == [None, 0.1, -0.5, 0.1]
    assert "em branco" in ficha.tabela.nota


def test_ranking_das_estaduais() -> None:
    linhas = [
        _linha(2023, "Companhia Energética de Minas Gerais", lucro=5e9),
        _linha(2024, "Companhia Energética de Minas Gerais", lucro=7e9),
        _linha(2023, "Companhia de Armazéns", lucro=-1e9),
        _linha(2024, "Companhia de Armazéns", lucro=-2e9),
    ]
    _, [desenho], _ = estatais_estaduais_fichas.ranking("teste", linhas)
    assert [s.nome for s in desenho.series] == ["Cemig (MG)", "Companhia de Armazéns (MG)"]
    assert [v for _, v in desenho.series[0].pontos] == [5.0, 7.0]
    assert [v.rotulo for v in desenho.variantes][1:] == [
        "Os 3 maiores lucros",
        "Os 3 maiores custos",
    ]
