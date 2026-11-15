from datetime import date

import pytest

from sacibras.secoes import atividade
from sacibras.secoes.atividade import demanda_privada
from sacibras.tipos import Ponto


def test_demanda_privada_pesa_pelo_tamanho_em_reais_do_ano_anterior() -> None:
    t0, t1 = date(2025, 4, 1), date(2026, 4, 1)
    consumo = [(t1, 2.0)]
    investimento = [(t1, 6.0)]
    # Um ano antes, consumo valia 3 vezes o investimento: peso 3/4 e 1/4.
    consumo_reais = [(t0, 300.0), (t1, 999.0)]
    investimento_reais = [(t0, 100.0), (t1, 1.0)]
    assert demanda_privada(consumo, investimento, consumo_reais, investimento_reais) == [(t1, 3.0)]


def test_demanda_privada_pula_trimestre_sem_base() -> None:
    t1 = date(2026, 4, 1)
    assert demanda_privada([(t1, 2.0)], [(t1, 6.0)], [(t1, 1.0)], [(t1, 1.0)]) == []


def _trimestres(inicio: int, valores: list[float]) -> list[Ponto]:
    return [(date(inicio + i // 4, 3 * (i % 4) + 1, 1), v) for i, v in enumerate(valores)]


CODIGOS = ["90707", *atividade.DEMANDA, *atividade.OFERTA]


def _contas() -> tuple[dict[str, list[Ponto]], dict[str, list[Ponto]]]:
    """Três anos: tudo cresce 2 % de um ano para o outro; em reais, cada parte vale 100."""
    volume = {c: _trimestres(2024, [100.0] * 4 + [102.0] * 4 + [104.04] * 4) for c in CODIGOS}
    valor = {c: _trimestres(2024, [100.0] * 12) for c in CODIGOS}
    return volume, valor


def test_por_ano_soma_so_os_anos_completos() -> None:
    anual = atividade.por_ano({"x": _trimestres(2025, [1.0, 2.0, 3.0, 4.0, 5.0])})
    assert anual == {"x": [(date(2025, 1, 1), 10.0)]}


def test_tabela_do_pib_abre_no_ultimo_trimestre_e_tem_os_anos_fechados() -> None:
    volume, valor = _contas()
    tri = atividade.contribuicoes(volume, valor)
    ano = atividade.contribuicoes(atividade.por_ano(volume), atividade.por_ano(valor))
    taxa = {c: _trimestres(2025, [2.0] * 8) for c in CODIGOS}
    t = atividade.tabela_componentes(taxa, taxa, taxa, tri, ano)

    trimestres = [v for v in t.visoes if v.grupo == "Trimestres"]
    anos = [v for v in t.visoes if v.grupo == "Anos"]
    assert trimestres[0].rotulo == "4º tri/2026" and t.visoes[0] is trimestres[0]
    assert [v.rotulo for v in anos] == ["2026", "2025"]
    assert t.linhas == trimestres[0].linhas and t.rotulo_visoes == "Período"

    def pontos(visao: atividade.VisaoTabela, grupo: str) -> float:
        return sum(li.valores[-1] or 0.0 for li in visao.linhas if li.grupo == grupo)

    for visao in (trimestres[0], anos[0]):
        pib = visao.linhas[0]
        assert pib.rotulo == "PIB" and pib.valores[-1] == pytest.approx(2.0)
        # Os pontos de quem comprou e os de quem produziu somam, cada um, o PIB.
        assert pontos(visao, "Quem comprou (demanda)") == pytest.approx(2.0)
        assert pontos(visao, "Quem produziu (oferta)") == pytest.approx(2.0)
        importacoes = next(li for li in visao.linhas if li.rotulo == "Importações")
        assert importacoes.valores[-1] == pytest.approx(-2.0)
    assert len(anos[0].colunas) == 2 and len(trimestres[0].colunas) == 3
    # 2025 se compara com 2024, o primeiro ano completo das contas.
    assert anos[1].linhas[0].valores == [2.0, pytest.approx(2.0)]


def test_ano_sem_o_anterior_completo_fica_sem_pontos() -> None:
    volume, valor = _contas()
    sem_2024 = {c: p[4:] for c, p in volume.items()}
    ano = atividade.contribuicoes(atividade.por_ano(sem_2024), atividade.por_ano(valor))
    taxa = {c: _trimestres(2025, [2.0] * 8) for c in CODIGOS}
    t = atividade.tabela_componentes(taxa, taxa, taxa, ({}, {}), ano)
    anos = {v.rotulo: v for v in t.visoes if v.grupo == "Anos"}
    assert anos["2025"].linhas[0].valores == [2.0, None]
    assert anos["2026"].linhas[0].valores == [2.0, pytest.approx(2.0)]
