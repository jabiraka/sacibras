"""PIB trimestral por estado: o ajuste no tempo (Denton), o rateio entre os estados, as
contribuições e o teste das revisões, sem rede."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import pytest

from sacibras.modelos import pib_estados as pe
from sacibras.tipos import Ponto


def _trimestres(de: int, ate: int) -> list[date]:
    return [date(a, m, 1) for a in range(de, ate + 1) for m in (1, 4, 7, 10)]


def _media(valores: list[float], tri: list[date], ano: int) -> float:
    do_ano = [v for v, t in zip(valores, tri, strict=True) if t.year == ano]
    return sum(do_ano) / len(do_ano)


def test_trimestral_tira_a_media_e_ignora_trimestre_incompleto() -> None:
    pontos: list[Ponto] = [(date(2026, m, 1), float(m)) for m in range(1, 9)]
    assert pe.trimestral(pontos) == {date(2026, 1, 1): 2.0, date(2026, 4, 1): 5.0}


def test_emendar_anda_para_tras_pelo_crescimento_em_um_ano_da_regiao() -> None:
    tri = _trimestres(2021, 2023)
    # O índice do estado só existe em 2023, com safra no 2º trimestre.
    proprio = dict(zip(tri[8:], [100.0, 140.0, 90.0, 95.0], strict=True))
    regiao = [50.0 * 1.1 ** (i // 4) for i in range(12)]  # cresce 10 % ao ano, sem safra
    x = pe.emendar(proprio, regiao, tri)
    assert x[8:] == [100.0, 140.0, 90.0, 95.0]
    # Para trás, o mesmo desenho dos trimestres, 10 % menor a cada ano.
    assert x[4:8] == pytest.approx([v / 1.1 for v in x[8:]])
    assert x[:4] == pytest.approx([v / 1.21 for v in x[8:]])
    # Índice inteiro passa como veio; com buraco ou curto demais, não serve.
    assert pe.emendar(dict(zip(tri, regiao, strict=True)), regiao, tri) == regiao
    with pytest.raises(ValueError, match="buraco"):
        pe.emendar({tri[8]: 1.0, tri[10]: 1.0, tri[11]: 1.0}, regiao, tri)
    with pytest.raises(ValueError):
        pe.emendar({tri[11]: 1.0}, regiao, tri)


def test_denton_fecha_com_o_ano_e_guarda_o_desenho_do_indicador() -> None:
    tri = _trimestres(2010, 2013)
    anos = [t.year for t in tri]
    # Indicador com sazonalidade forte e nível errado; o oficial só vai até 2012.
    x = [50.0 * (1 + 0.01 * i) * (1.2 if i % 4 == 1 else 0.9) for i in range(16)]
    anual = {2010: 100.0, 2011: 103.0, 2012: 108.0}
    b = pe.denton(x, anos, anual)
    for ano, oficial in anual.items():
        assert _media(b, tri, ano) == pytest.approx(oficial)
    # Depois do último ano oficial, a razão para o indicador fica parada.
    razoes = [bt / xt for bt, xt in zip(b, x, strict=True)]
    assert razoes[12:] == pytest.approx([razoes[11]] * 4)
    # E muda devagar: nenhum degrau entre trimestres vizinhos maior que 2 %.
    assert max(abs(razoes[i] / razoes[i - 1] - 1) for i in range(1, 16)) < 0.02


def test_denton_com_indicador_proporcional_so_muda_a_escala() -> None:
    tri = _trimestres(2010, 2012)
    x = [10.0, 12.0, 11.0, 13.0, 11.0, 13.0, 12.0, 14.0, 12.0, 14.0, 13.0, 15.0]
    anual = {a: 10 * _media(x, tri, a) for a in (2010, 2011, 2012)}
    assert pe.denton(x, [t.year for t in tri], anual) == pytest.approx([10 * v for v in x])


def test_denton_pede_um_ano_inteiro() -> None:
    with pytest.raises(ValueError, match="quatro trimestres"):
        pe.denton([1.0, 2.0], [2010, 2010], {2010: 1.5})


@dataclass
class Economia:
    tri: list[date]
    indice: dict[str, list[float]]
    volume: dict[str, dict[int, float]]
    corrente: dict[str, dict[int, float]]
    brasil: dict[int, float]
    pib: list[float]

    def estimar(
        self, indicador: dict[str, list[float]] | None = None, ultimo: int | None = None
    ) -> pe.Estimativa:
        return pe.estimar(
            self.tri,
            indicador or self.indice,
            self.volume,
            self.corrente,
            self.pib,
            self.brasil,
            ultimo,
        )

    def revisoes(
        self, indicador: dict[str, list[float]], final: pe.Estimativa
    ) -> dict[str, list[float]]:
        return pe.revisoes(
            self.tri, indicador, self.volume, self.corrente, self.pib, self.brasil, final
        )

    def sem_safra(self) -> dict[str, list[float]]:
        """O indicador de B não vê a safra e cresce de menos (2 % por trimestre, não 3 %)."""
        return {"A": self.indice["A"], "B": [100 * 1.02**i for i in range(len(self.tri))]}


def _economia() -> Economia:
    """Dois estados de verdade conhecida: A (peso 3) cresce 1 % por trimestre, B (peso 1)
    cresce 3 % e tem safra no 2º trimestre. Sem mudança de preço relativo, o PIB do país é a
    soma com pesos fixos."""
    tri = _trimestres(2010, 2015)
    bruto = {
        "A": [1.01**i for i in range(len(tri))],
        "B": [1.03**i * (1.3 if i % 4 == 1 else 0.9) for i in range(len(tri))],
    }
    indice = {s: [100 * v / _media(b, tri, 2010) for v in b] for s, b in bruto.items()}
    tamanho = {"A": 3000.0, "B": 1000.0}
    anos = range(2010, 2016)
    volume = {s: {a: _media(indice[s], tri, a) for a in anos} for s in indice}
    corrente = {s: {a: tamanho[s] * volume[s][a] / 100 for a in anos} for s in indice}
    brasil = {a: sum(corrente[s][a] for s in indice) for a in anos}
    pib = [sum(tamanho[s] * indice[s][t] / 100 for s in indice) for t in range(len(tri))]
    return Economia(tri, indice, volume, corrente, brasil, pib)


def test_com_indicador_perfeito_a_estimativa_e_a_verdade() -> None:
    d = _economia()
    e = d.estimar()
    assert e.ultimo_oficial == 2015
    for s in ("A", "B"):
        assert e.indice[s] == pytest.approx(d.indice[s])
    assert [e.pesos["A"][t] + e.pesos["B"][t] for t in range(24)] == pytest.approx([1.0] * 24)


def test_indicador_ruim_ainda_fecha_com_o_ano_do_estado_e_com_o_trimestre_do_pais() -> None:
    d = _economia()
    # O IBGE só publicou até 2013.
    e = d.estimar(d.sem_safra(), ultimo=2013)
    assert e.ultimo_oficial == 2013
    for s in ("A", "B"):
        for ano in range(2010, 2014):
            assert _media(e.indice[s], d.tri, ano) == pytest.approx(d.volume[s][ano])
    # A soma dos estados dá o crescimento do país em todo trimestre, também em 2014 e 2015.
    contrib = pe.contribuicoes(e, d.pib)
    brasil = pe.crescimento(d.pib)
    assert contrib["A"][:4] == [None] * 4 and brasil[:4] == [None] * 4
    for t in range(4, len(d.tri)):
        a, b = contrib["A"][t], contrib["B"][t]
        assert a is not None and b is not None and a + b == pytest.approx(brasil[t])


def test_contribuicao_e_a_fatia_vezes_o_crescimento() -> None:
    d = _economia()
    contrib = pe.contribuicoes(d.estimar(), d.pib)
    t = 9  # 2º tri de 2012
    indice = d.indice["A"]
    fatia_um_ano_antes = 3000 * indice[t - 4] / 100 / d.pib[t - 4]
    esperado = fatia_um_ano_antes * (indice[t] / indice[t - 4] - 1) * 100
    assert contrib["A"][t] == pytest.approx(esperado)


def test_revisoes_medem_o_quanto_o_trimestre_muda_quando_sai_o_oficial() -> None:
    d = _economia()
    r = d.revisoes(d.indice, d.estimar())
    # Y vai de 2012 a 2014; cada um revê os trimestres de Y+1 e Y+2 que já têm oficial.
    assert len(r["A"]) == 4 * (2 + 2 + 1)
    assert max(abs(x) for s in r for _, x in r[s]) < 1e-6
    assert {t.year for t, _ in r["A"]} == {2013, 2014, 2015}
    ruim = d.sem_safra()
    r = d.revisoes(ruim, d.estimar(ruim))
    # B cresce 12,6 % ao ano e o indicador só 8,2 %: a revisão é para cima, e grande.
    assert sum(x for _, x in r["B"]) / len(r["B"]) > 2


# ------------------------------------------------------------------ scripts/conferir_pib_estados.py


def _script() -> Any:
    import importlib.util
    from pathlib import Path

    caminho = Path(__file__).parents[1] / "scripts" / "conferir_pib_estados.py"
    spec = importlib.util.spec_from_file_location("conferir_pib_estados", caminho)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_conferencia_acha_a_planilha_mais_nova_de_cada_estado() -> None:
    s = _script()
    rs, padrao_rs = s.PAGINAS["RS"]
    html_rs = (
        '<a href="https://admin.dee.rs.gov.br/upload/arquivos/202606/1-serie-historica-2026-i.xlsx">'
        '<a href="https://admin.dee.rs.gov.br/upload/arquivos/202609/2-serie-historica-2026-ii.xlsx">'
        '<a href="https://admin.dee.rs.gov.br/upload/arquivos/202512/3-serie-historica-2025-iv.xlsx">'
    )
    assert s.planilha_mais_nova(rs, padrao_rs, html_rs).endswith("2-serie-historica-2026-ii.xlsx")
    pr, padrao_pr = s.PAGINAS["PR"]
    html_pr = (
        '<a href="/sites/ipardes/files/documento/2026-10/serie_encadeada_2o_trim_2026.xlsx">'
        '<a href="/sites/ipardes/files/documento/2026-07/serie_encadeada_1o_trim_2026.xlsx">'
    )
    assert s.planilha_mais_nova(pr, padrao_pr, html_pr) == (
        "https://www.ipardes.pr.gov.br/sites/ipardes/files/documento/2026-10/"
        "serie_encadeada_2o_trim_2026.xlsx"
    )
    ba, padrao_ba = s.PAGINAS["BA"]
    html_ba = (
        '<a href="/sei/sites/site-sei/files/2026-06/pib_trimestral_tabelas_completas.xls">'
        '<a href="/sei/sites/site-sei/files/2026-09/pib_trimestral_tabelas_completas.xls">'
    )
    assert "2026-09" in s.planilha_mais_nova(ba, padrao_ba, html_ba)
    es, padrao_es = s.PAGINAS["ES"]
    html_es = '<a href="/media/x/PIB%20Trimestral%20%28dados%20em%20Excel%29-1.xlsx?v=1&amp;a=2">'
    assert s.planilha_mais_nova(es, padrao_es, html_es) == (
        "https://ijsn.es.gov.br/media/x/PIB%20Trimestral%20%28dados%20em%20Excel%29-1.xlsx?v=1&a=2"
    )
    with pytest.raises(RuntimeError):
        s.planilha_mais_nova(rs, padrao_rs, "<p>verificação de robô</p>")


def test_conferencia_le_o_indice_e_tira_a_taxa_em_um_ano() -> None:
    import io

    import openpyxl  # type: ignore[import-untyped]

    s = _script()
    livro = openpyxl.Workbook()
    folha = livro.active
    folha.title = "Série encadeada"
    folha.append(["Período", "Agro", "PIB"])
    folha.append(["2025.I", 1.0, 100.0])
    folha.append(["2025.II", 1.0, 110.0])
    folha.append(["2026.I", 1.0, 103.0])
    folha.append(["Nota", None, None])
    saida = io.BytesIO()
    livro.save(saida)
    linhas = s.linhas_da_aba(saida.getvalue(), "Série encadeada")
    assert s.ler(linhas, -1, True) == {(2026, 1): pytest.approx(3.0)}
    assert s.ler(linhas, -1, False)[(2025, 2)] == 110.0
