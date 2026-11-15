"""Estados: PIB (Contas Regionais), prévia pelo IBC-R, IPCA por área e crédito, sem rede."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from sacibras.catalogo import CREDITO_INADIMPLENCIA_UF, CREDITO_SALDO_UF, IBCR_UF, SGS
from sacibras.fontes import ibge_contas_regionais
from sacibras.secoes import estados, estados_economia
from sacibras.secoes.base import Contexto
from sacibras.tipos import Ponto

UFS = estados.UFS
NOMES = [nome for _, _, nome, _ in UFS]


def _meses(inicio: date, valores: list[float]) -> list[Ponto]:
    saida = []
    for i, v in enumerate(valores):
        t = inicio.year * 12 + inicio.month - 1 + i
        saida.append((date(t // 12, t % 12 + 1, 1), v))
    return saida


def test_crescimento_de_12_meses_compara_medias_e_pede_os_24_meses() -> None:
    pontos = _meses(date(2024, 9, 1), [100.0] * 12 + [110.0] * 12)
    assert estados_economia.crescimento_12_meses(pontos, date(2026, 8, 1)) == pytest.approx(10.0)
    assert estados_economia.crescimento_12_meses(pontos[1:], date(2026, 8, 1)) is None


def test_os_codigos_por_uf_cobrem_as_27_e_estao_no_catalogo() -> None:
    siglas = {s for _, s, _, _ in UFS}
    assert set(CREDITO_SALDO_UF) == siglas == set(CREDITO_INADIMPLENCIA_UF)
    assert set(IBCR_UF) < siglas and len(IBCR_UF) == 13
    assert SGS["CREDITO_SALDO_SP"].codigo == 14080 and SGS["IBCR_SP"].codigo == 25392
    assert SGS["CREDITO_INADIMPLENCIA_ES"].codigo == 15932


def _contas_regionais(monkeypatch: pytest.MonkeyPatch) -> None:
    anos = range(2010, 2025)
    corrente = {n: {a: 1000.0 for a in anos} for n in NOMES}
    corrente["Brasil"] = {a: 27_000.0 for a in anos}
    volume = {n: {a: 100.0 * 1.02 ** (a - 2010) for a in anos} for n in ["Brasil", *NOMES]}
    volume["Paraíba"][2024] = volume["Paraíba"][2023] * 1.065
    monkeypatch.setattr(
        estados_economia.ibge_contas_regionais, "pib", lambda: (2024, corrente, volume)
    )
    pop = {s: {"POP_T": {2024: 1_000_000.0}} for _, s, _, _ in UFS}
    pop["BR"] = {"POP_T": {2024: 27_000_000.0}}
    monkeypatch.setattr(estados_economia.ibge_projecao, "grupos", lambda: pop)


def test_pib_por_uf_cresce_pelo_volume_e_divide_pela_populacao_do_mesmo_ano(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _contas_regionais(monkeypatch)
    m = {x.id: x for x in estados_economia.pib(UFS)}
    assert set(m) == {
        "pib_crescimento",
        "pib_per_capita",
        "pib_participacao",
    }
    assert m["pib_crescimento"].valores["PB"] == pytest.approx(6.5)
    assert m["pib_crescimento"].valores["SP"] == pytest.approx(2.0)
    # A série vai junto, para a tela escolher a janela.
    assert m["pib_crescimento"].anuais["PB"][2024] / m["pib_crescimento"].anuais["PB"][
        2023
    ] == pytest.approx(1.065)
    assert set(m["pib_crescimento"].anuais["BR"]) == set(range(2010, 2025))
    # R$ milhões × 1e6 ÷ pessoas
    assert m["pib_per_capita"].valores["AC"] == pytest.approx(1000.0)
    assert m["pib_per_capita"].brasil == pytest.approx(1000.0)
    assert m["pib_participacao"].valores["AC"] == pytest.approx(1000 / 27_000 * 100)
    assert all(x.grupo == "Economia" for x in m.values())


def test_pib_recusa_planilha_sem_um_estado(monkeypatch: pytest.MonkeyPatch) -> None:
    _contas_regionais(monkeypatch)
    _, corrente, volume = ibge_contas_regionais.pib()  # o falso
    del volume["Acre"]
    monkeypatch.setattr(
        estados_economia.ibge_contas_regionais, "pib", lambda: (2024, corrente, volume)
    )
    with pytest.raises(ibge_contas_regionais.PlanilhaMudouError):
        estados_economia.pib(UFS)


def test_sem_o_pib_oficial_a_previa_fica_so_com_os_13_estados_e_sem_faixa() -> None:
    serie = _meses(date(2023, 1, 1), [100.0] * 12 + [100.0] * 12 + [103.0] * 12 + [104.0] * 8)

    def sgs(chave: str) -> list[Ponto]:
        return serie

    doze, ano = estados_economia.ibcr(UFS, sgs)
    assert ano.nome == "Prévia do PIB de 2025" and ano.referencia == "2025"
    assert ano.valores["SP"] == pytest.approx(3.0) and ano.brasil == pytest.approx(3.0)
    assert ano.valores["MT"] is None and "MT" in ano.descricao
    assert not ano.intervalos and not ano.estimados and ano.como_ler == ""
    assert doze.referencia == "12 meses até ago/2026"
    assert sum(v is not None for v in doze.valores.values()) == 13


def test_estado_sem_ibcr_cresce_como_a_regiao_com_a_faixa_do_teste() -> None:
    # Índices que crescem 2 % ao ano (estados) e 3 % (regiões), de 2010 a ago/2026.
    def indice(taxa: float) -> list[Ponto]:
        valores = [100.0 * (1 + taxa) ** (i // 12) for i in range(12 * 16 + 8)]
        return _meses(date(2010, 1, 1), valores)

    def sgs(chave: str) -> list[Ponto]:
        return indice(0.03 if chave.startswith("IBCR_REGIAO_") else 0.02)

    # O PIB oficial: 2,5 % ao ano em quem tem IBC-R; 4 % em quem não tem, 5 % nos anos pares.
    volume: dict[str, dict[int, float]] = {}
    for _, sigla, nome, _ in UFS:
        nivel, serie = 100.0, {2010: 100.0}
        for a in range(2011, 2025):
            taxa = 0.025 if sigla in IBCR_UF else (0.05 if a % 2 == 0 else 0.04)
            nivel *= 1 + taxa
            serie[a] = nivel
        volume[nome] = serie

    _, previa = estados_economia.ibcr(UFS, sgs, volume)
    assert all(v is not None for v in previa.valores.values())
    assert len(previa.estimados) == 14 and "MT" in previa.estimados and "SP" not in previa.estimados
    assert previa.valores["MT"] == pytest.approx(3.0) and previa.valores["SP"] == pytest.approx(2.0)
    # Erro = oficial − prévia: +0,5 em quem tem índice; de +1 a +2 em quem não tem.
    de, ate = previa.intervalos["SP"]
    assert de == pytest.approx(2.5) and ate == pytest.approx(2.5)
    de, ate = previa.intervalos["MT"]
    assert de == pytest.approx(4.0) and ate == pytest.approx(5.0)
    assert "8 de cada 10" in previa.como_ler and "2011 a 2024" in previa.como_ler
    assert "cresce como a região" in previa.descricao


def test_pib_trimestral_reparte_o_pib_do_brasil_e_so_poe_faixa_depois_do_oficial() -> None:
    # IBC-R: 0,5 % por trimestre nos estados e 1 % nas regiões, de 2010 a jun/2026.
    def sgs(chave: str) -> list[Ponto]:
        taxa = 0.01 if chave.startswith("IBCR_REGIAO_") else 0.005
        return _meses(date(2010, 1, 1), [100.0 * (1 + taxa) ** (i // 3) for i in range(198)])

    # O oficial (até 2024): 2 % ao ano em quem tem IBC-R; 4 %, e 6 % nos anos pares, nos outros.
    anos = range(2010, 2025)
    volume: dict[str, dict[int, float]] = {}
    for _, sigla, nome, _ in UFS:
        nivel, serie = 100.0, {2010: 100.0}
        for a in range(2011, 2025):
            nivel *= 1.02 if sigla in IBCR_UF else (1.06 if a % 2 == 0 else 1.04)
            serie[a] = nivel
        volume[nome] = serie
    corrente = {n: {a: 1000.0 * volume[n][a] / 100 for a in anos} for n in NOMES}
    corrente["Brasil"] = {a: sum(corrente[n][a] for n in NOMES) for a in anos}
    volume["Brasil"] = {a: 100 * corrente["Brasil"][a] / corrente["Brasil"][2010] for a in anos}
    # O PIB trimestral do Brasil: 0,7 % por trimestre, até o 2º tri/2026.
    pib_brasil = [(date(2010 + i // 4, 3 * (i % 4) + 1, 1), 170.0 * 1.007**i) for i in range(66)]

    cresc, contrib = estados_economia.pib_trimestral(UFS, sgs, pib_brasil, 2024, corrente, volume)
    assert (cresc.id, contrib.id) == ("pib_trimestre", "pib_trimestre_contribuicao")
    assert cresc.referencia == "2º tri/2026 (estimativa)" and cresc.grupo == "Economia"
    assert len(cresc.estimados) == 14 and "MT" in cresc.estimados and "SP" not in cresc.estimados
    assert all(v is not None for v in cresc.valores.values())
    assert cresc.brasil == pytest.approx((1.007**4 - 1) * 100, abs=0.01)
    # Quem não tem IBC-R anda pela região, que cresce mais.
    assert cresc.valores["MT"] > cresc.valores["SP"]  # type: ignore[operator]
    # Um período por trimestre desde 2011, do mais novo ao mais antigo; o primeiro é o de cima.
    assert len(cresc.periodos) == 62 and cresc.periodos[0].valores == cresc.valores
    assert cresc.periodos[-1].referencia == "1º tri/2011"
    # A faixa de erro só existe depois do último ano oficial (2025 e 2026: seis trimestres).
    assert [bool(p.intervalos) for p in cresc.periodos] == [True] * 6 + [False] * 56
    de, ate = cresc.intervalos["SP"]
    assert de <= cresc.valores["SP"] <= ate  # type: ignore[operator]
    assert "8 de cada 10" in cresc.como_ler and "IBC-R" in cresc.descricao
    # As contribuições somam o crescimento do Brasil em todo trimestre.
    for p_contrib, p_cresc in zip(contrib.periodos, cresc.periodos, strict=True):
        soma = sum(v for v in p_contrib.valores.values() if v is not None)
        assert soma == pytest.approx(p_cresc.brasil, abs=0.02)
        assert p_contrib.brasil is None and "é a soma dos 27 estados" in p_contrib.nota
    # A faixa da contribuição é a do crescimento vezes o peso: mais estreita que a do estado.
    c_de, c_ate = contrib.intervalos["SP"]
    assert 0 < c_ate - c_de < ate - de


def test_crescimento_anual_ignora_ano_incompleto() -> None:
    pontos = _meses(date(2024, 1, 1), [100.0] * 12 + [105.0] * 12 + [110.0] * 8)
    assert estados_economia.crescimento_anual(pontos) == {2025: pytest.approx(5.0)}


def test_ipca_de_cada_area_vai_ao_estado_dela(monkeypatch: pytest.MonkeyPatch) -> None:
    out = date(2026, 10, 1)

    def series(tabela: int, variavel: int, **k: Any) -> dict[str, list[Ponto]]:
        if k["nivel"] == "n7/all":
            return {"3501": [(out, 4.94)], "4101": [(out, 2.05)]}
        return {"5300108": [(out, 4.83)], "1200401": [(out, 4.13)]}

    monkeypatch.setattr(estados_economia.ibge_sidra, "series", series)
    monkeypatch.setattr(estados_economia.ibge_sidra, "serie", lambda *a, **k: [(out, 4.63)])
    m = estados_economia.inflacao(UFS)
    assert m.valores["SP"] == 4.94 and m.valores["DF"] == 4.83 and m.valores["AC"] == 4.13
    assert m.valores["MT"] is None and m.brasil == 4.63 and m.referencia == "out/2026"


def test_credito_por_habitante_e_inadimplencia_pesada_pelo_saldo() -> None:
    setembro = date(2026, 9, 1)

    def sgs(chave: str) -> list[Ponto]:
        if chave == "CREDITO_SALDO_SP":
            return [(setembro, 3000.0)]
        if chave.startswith("CREDITO_SALDO_"):
            return [(setembro, 1000.0)]
        return [(setembro, 2.0 if chave.endswith("_SP") else 6.0)]

    pop = {c: 1_000_000.0 for c, *_ in UFS}
    por_hab, inad = estados_economia.credito(UFS, sgs, pop)
    assert por_hab.valores["SP"] == pytest.approx(3000.0) and por_hab.referencia == "set/2026"
    # (2 × 3000 + 6 × 26 × 1000) ÷ (3000 + 26 000)
    assert inad.brasil == pytest.approx((2 * 3000 + 6 * 26_000) / 29_000)


def test_metricas_saem_na_ordem_dos_grupos(monkeypatch: pytest.MonkeyPatch) -> None:
    _contas_regionais(monkeypatch)

    def cai(*a: Any, **k: Any) -> Any:
        raise estados.siconfi.FonteForaDoArError("fora")

    for nome in (
        "ibcr",
        "pib_trimestral",
        "inflacao",
        "exportacoes",
        "concentracao",
        "trabalho",
        "credito",
    ):
        monkeypatch.setattr(estados_economia, nome, cai)
    deso = {str(c): [(date(2026, 4, 1), 5.0)] for c, *_ in UFS}
    monkeypatch.setattr(estados.ibge_sidra, "series", lambda *a, **k: deso)
    monkeypatch.setattr(estados.ibge_sidra, "serie", lambda *a, **k: [(date(2026, 4, 1), 5.4)])
    for nome in ("coletar", "coletar_rreo", "coletar_anual", "coletar_historico"):
        monkeypatch.setattr(estados.siconfi, nome, cai)
    monkeypatch.setattr(estados.receita_arrecadacao, "arrecadacao", cai)
    monkeypatch.setattr(estados.ipeadata, "por_territorio", cai)
    monkeypatch.setattr(estados.tesouro_capag, "capag", cai)
    monkeypatch.setattr(estados.ibge_contas_regionais, "setores", cai)
    monkeypatch.setattr(estados.comexstat, "exportacoes_por_estado_e", cai)
    monkeypatch.setattr(estados.comexstat, "exportacoes_por_mes", cai)
    monkeypatch.setattr(estados.ibge_projecao, "quinquenal_por_uf", cai)
    monkeypatch.setattr(estados.siconfi, "capitais", cai)
    e = estados.montar(Contexto(hoje=date(2026, 11, 14)))
    assert e.metricas[0].id == "pib_crescimento"
    # Depois do trabalho, só o acordo da dívida (lido à mão, sempre presente), das contas.
    assert [m.grupo for m in e.metricas][-2:] == ["Trabalho e renda", estados.CONTAS]
    assert e.resumo.startswith("Em 2024, o PIB cresceu de")


def test_previa_entra_na_serie_do_pib_so_no_ano_seguinte(monkeypatch: pytest.MonkeyPatch) -> None:
    _contas_regionais(monkeypatch)
    pib = next(x for x in estados_economia.pib(UFS) if x.id == "pib_crescimento")
    previa = pib.model_copy(
        update={
            "id": "ibcr_ano",
            "referencia": "2025",
            "valores": {"PB": 3.0, "SP": None},
            "brasil": 2.5,
            "anuais": {},
        }
    )
    estados_economia.encadear_previa(pib, previa)
    assert pib.ano_previsto == 2025
    assert pib.anuais["PB"][2025] == pytest.approx(pib.anuais["PB"][2024] * 1.03, rel=1e-5)
    assert pib.anuais["BR"][2025] == pytest.approx(pib.anuais["BR"][2024] * 1.025, rel=1e-5)
    assert 2025 not in pib.anuais["SP"]
    # Prévia de outro ano não se encadeia.
    outro = next(x for x in estados_economia.pib(UFS) if x.id == "pib_crescimento")
    estados_economia.encadear_previa(outro, previa.model_copy(update={"referencia": "2026"}))
    assert outro.ano_previsto is None
