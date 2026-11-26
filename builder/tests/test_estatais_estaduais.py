"""As estatais dos estados: a leitura do arquivo do Tesouro e a conta do caixa."""

from sacibras.fontes import tesouro_estaduais
from sacibras.secoes import estatais_estaduais

CABECA = "Estado;Nome_estado;emp;dep;lucros;Dividendos;Subvenção;Reforço de Capital\n"


def _ano(ano: int) -> list[tesouro_estaduais.EmpresaEstadual]:
    corpo = (
        "MG;Minas Gerais;COMPANHIA  DE LUZ;Não Dependente;5000000000,5;800000000;0;0\n"
        "AC;Acre;Companhia de Armazéns;Dependente;NA;0;2000000000;500000000\n"
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
