"""Estados sem rede: os parsers do RGF e do RREO (SICONFI) com trechos reais e a montagem."""

from datetime import date
from typing import Any

import pytest

from sacibras.fontes import siconfi
from sacibras.schema import MetricaEstados
from sacibras.secoes import estados
from sacibras.secoes.base import Contexto


def _linha(conta: str, coluna: str, valor: float) -> dict[str, Any]:
    return {"cod_conta": conta, "coluna": coluna, "valor": valor, "co_poder": "E", "esfera": "E"}


PCT = "% sobre a RCL Ajustada"
# Trecho real do RGF-Anexo 01 de SP, 2º quadrimestre de 2026 (consultado em 14/11/2026).
A1_SP = [
    _linha("DespesaComPessoalBruta", "<MR>", 10519563728.89),
    _linha("ReceitaCorrenteLiquidaAjustada", "Valor", 279170988510.08),
    _linha("DespesaComPessoalTotal", "Valor", 118023183648.21),
    _linha("DespesaComPessoalTotal", PCT, 42.28),
    _linha("LimiteMaximoDespesaComPessoalTotal", "Valor", 136793784369.94),
    _linha("LimiteMaximoDespesaComPessoalTotal", PCT, 49),
    _linha("LimitePrudencialDespesaComPessoalTotal", "Valor", 129954095151.44),
    _linha("LimitePrudencialDespesaComPessoalTotal", PCT, 46.55),
    _linha("LimiteDeAlertaDespesaComPessoalTotal", "Valor", 123114405932.95),
    _linha("LimiteDeAlertaDespesaComPessoalTotal", PCT, 44.1),
]
# Amapá no mesmo demonstrativo: o limite em % vem como fração (0,49), os valores em R$ não.
A1_AP = [
    _linha("ReceitaCorrenteLiquidaAjustada", "Valor", 10832918771.42),
    _linha("DespesaComPessoalTotal", PCT, 41.83),
    _linha("LimiteMaximoDespesaComPessoalTotal", "Valor", 5308130198),
    _linha("LimiteMaximoDespesaComPessoalTotal", PCT, 0.49),
    _linha("LimitePrudencialDespesaComPessoalTotal", "Valor", 5042723688.1),
    _linha("LimitePrudencialDespesaComPessoalTotal", PCT, 0.47),
    _linha("LimiteDeAlertaDespesaComPessoalTotal", "Valor", 4777317178.2),
    _linha("LimiteDeAlertaDespesaComPessoalTotal", PCT, 0.44),
]
# Distrito Federal: o RGF só responde com co_esfera=E. Trecho parcial; a RCL ajustada daqui é
# um valor aproximado escrito para o teste, não o da resposta real (os limites são os reais).
A1_DF = [
    _linha("ReceitaCorrenteLiquidaAjustada", "Valor", 41896610000.0),
    _linha("DespesaComPessoalTotal", PCT, 40.54),
    _linha("LimiteMaximoDespesaComPessoalTotal", "Valor", 20530599680.64),
    _linha("LimiteDeAlertaDespesaComPessoalTotal", "Valor", 18477539712.58),
]
COL2 = "Até o 2º Quadrimestre"
# Trecho real do RGF-Anexo 02 de SP.
A2_SP = [
    _linha("DividaConsolidadaLiquida", COL2, 315908470847.25),
    _linha("RGF2ReceitaCorrenteLiquida", "Até o 1º Quadrimestre", 270767497842.45),
    _linha("RGF2ReceitaCorrenteLiquida", COL2, 279658527567.42),
    _linha(
        "ReceitaCorrenteLiquidaAjustadaParaCalculoDosLimitesDeEndividamento", COL2, 279497399297.08
    ),
    _linha("PercentualDaDCLSobreARCL", COL2, 113.03),
    _linha("LimiteDefinidoPorResolucaoDoSenadoFederal", COL2, 558994798594.16),
    _linha("LimiteDeAlerta", COL2, 503095318734.74),
]


T12 = "TOTAL (ÚLTIMOS 12 MESES)"
# Trechos reais do RREO-Anexo 03 (4º bimestre de 2026, consultado em 14/11/2026).
R3_SP = [
    _linha("ICMSLiquidoExcetoTransferenciasEFUNDEB", "<MR>", 21782488968.33),
    _linha("ICMSLiquidoExcetoTransferenciasEFUNDEB", T12, 250219667943.92),
    _linha("ICMSLiquidoExcetoTransferenciasEFUNDEB", "PREVISÃO ATUALIZADA 2026", 254620847220),
    _linha("RREO3ReceitaCorrenteLiquida", T12, 279658527567.42),
]
# O DF só responde com co_esfera=E.
R3_DF = [
    _linha("ICMSLiquidoExcetoTransferenciasEFUNDEB", T12, 13774849189.55),
    _linha("RREO3ReceitaCorrenteLiquida", T12, 42283586178.36),
]
# Estado que entregou o Anexo 03 sem a linha do ICMS (só a RCL).
R3_SEM_ICMS = [_linha("RREO3ReceitaCorrenteLiquida", T12, 1_000_000_000.0)]
# Trechos reais do RREO-Anexo 06: acima da linha, com e sem RPPS (coluna VALOR).
R6_SP = [
    _linha("ResultadoPrimarioComRPPSAcimaDaLinha", "VALOR", 5341116534.66),
    _linha("ResultadoPrimarioSemRPPSAcimaDaLinha", "VALOR", 5320559240.55),
    _linha("ResultadoPrimarioAbaixoDaLinhaSemRPPS", "VALOR", 5320559240.55),
]
R6_DF = [
    _linha("ResultadoPrimarioComRPPSAcimaDaLinha", "VALOR", 1714434057.5),
    _linha("ResultadoPrimarioSemRPPSAcimaDaLinha", "VALOR", 1824667292.95),
]


def test_receita_do_rreo_de_sp_e_do_df() -> None:
    sp = siconfi.parse_receita(R3_SP)
    assert sp == siconfi.Receita(icms=250219667943.92, rcl=279658527567.42)
    df = siconfi.parse_receita(R3_DF)
    assert df == siconfi.Receita(icms=13774849189.55, rcl=42283586178.36)


def test_receita_sem_a_conta_do_icms_ou_sem_nada() -> None:
    sem = siconfi.parse_receita(R3_SEM_ICMS)
    assert sem is not None and sem.icms is None and sem.rcl == 1_000_000_000.0
    assert siconfi.parse_receita([]) is None


def test_primario_usa_a_conta_sem_rpps_acima_da_linha() -> None:
    assert siconfi.parse_primario(R6_SP) == 5320559240.55
    assert siconfi.parse_primario(R6_DF) == 1824667292.95  # no DF "sem" difere da "com"
    assert siconfi.parse_primario([]) is None
    assert siconfi.parse_primario(R6_SP[:1]) is None  # só a "com RPPS": não troca de conta


def test_bimestres_voltam_no_tempo() -> None:
    assert siconfi.bimestres(date(2026, 11, 14), 3) == [(2026, 6), (2026, 5), (2026, 4)]
    assert siconfi.bimestres(date(2026, 2, 1), 3) == [(2026, 1), (2025, 6), (2025, 5)]


def test_pessoal_de_sp() -> None:
    p = siconfi.parse_pessoal(A1_SP)
    assert p == siconfi.Pessoal(percentual=42.28, maximo=49.0, prudencial=46.55, alerta=44.1)


def test_limite_do_amapa_sai_da_razao_dos_valores_e_nao_da_fracao() -> None:
    p = siconfi.parse_pessoal(A1_AP)
    assert p is not None
    assert (p.maximo, p.prudencial, p.alerta) == (49.0, 46.55, 44.1)


def test_df_sem_a_coluna_de_percentual_do_limite_ainda_acha_pela_razao() -> None:
    p = siconfi.parse_pessoal(A1_DF)
    assert p is not None and p.percentual == 40.54
    assert p.maximo == pytest.approx(49.0, abs=0.01)
    assert p.prudencial is None


def test_uf_sem_dado_devolve_none() -> None:
    assert siconfi.parse_pessoal([]) is None
    assert siconfi.parse_divida([], 2) is None


def test_divida_de_sp_usa_a_coluna_do_quadrimestre() -> None:
    d = siconfi.parse_divida(A2_SP, 2)
    assert d is not None
    assert d.dcl_percentual == 113.03
    assert d.rcl == 279658527567.42
    assert d.limite == 200.0
    assert d.alerta == 180.0
    # No 1º quadrimestre não há o percentual nesse trecho.
    d1 = siconfi.parse_divida(A2_SP, 1)
    assert d1 is not None and d1.dcl_percentual is None


def test_candidatos_voltam_no_tempo() -> None:
    assert siconfi.candidatos(date(2026, 11, 14), 4) == [(2026, 3), (2026, 2), (2026, 1), (2025, 3)]
    assert siconfi.candidatos(date(2026, 2, 1), 2) == [(2026, 1), (2025, 3)]


def test_df_cai_para_esfera_d_so_se_a_e_vier_vazia(monkeypatch: pytest.MonkeyPatch) -> None:
    pedidos: list[str] = []

    def falso(url: str, **kw: Any) -> Any:
        esfera = kw["params"]["co_esfera"]
        pedidos.append(esfera)
        return {"items": A1_DF if esfera == "E" else []}

    monkeypatch.setattr(siconfi, "baixar_json", falso)
    monkeypatch.setattr(siconfi, "PAUSA", 0)
    assert siconfi.rgf(2026, 2, 1, siconfi.DF) == A1_DF
    assert pedidos == ["E"]


def _coleta(sem_dado: set[int]) -> siconfi.ColetaRgf:
    cods = [c for c, *_ in estados.UFS]
    pessoal = {
        c: None if c in sem_dado else siconfi.Pessoal(40.0 + c % 10, 49, 46.55, 44.1) for c in cods
    }
    divida = {
        c: None if c in sem_dado else siconfi.Divida(10.0, 1_000_000.0 * c, 200, 180) for c in cods
    }
    return siconfi.ColetaRgf(2026, 2, pessoal, divida)


def test_montagem_das_metricas_fiscais_deixa_none_para_quem_falta() -> None:
    populacao = {c: 1000.0 for c, *_ in estados.UFS}
    pessoal, divida, rcl, alertas = estados._fiscais(_coleta({12}), populacao)
    assert isinstance(pessoal, MetricaEstados)
    assert pessoal.referencia == "2º quadrimestre de 2026"
    assert len(pessoal.valores) == 27
    assert pessoal.valores["AC"] is None and pessoal.valores["SP"] == 45.0
    assert [(x.valor, x.rotulo) for x in pessoal.limites] == [
        (49, "limite máximo"),
        (46.55, "limite prudencial"),
        (44.1, "limite de alerta"),
    ]
    assert "art. 20, II, c" in pessoal.descricao and "diferente" not in pessoal.descricao
    assert [x.valor for x in divida.limites] == [200, 180]
    assert "Resolução do Senado nº 40/2001" in divida.descricao
    assert rcl.valores["SP"] == 35_000.0 and rcl.valores["AC"] is None
    assert "AC" not in alertas and alertas["SP"] == 44.1


def test_estado_com_limite_proprio_no_rgf_e_nomeado() -> None:
    coleta = _coleta(set())
    coleta.pessoal[35] = siconfi.Pessoal(45.0, 50.0, 47.5, 45.0)  # SP com limite próprio
    pessoal, *_ = estados._fiscais(coleta, {c: 1000.0 for c, *_ in estados.UFS})
    assert pessoal.limites[0].valor == 49  # a linha continua sendo a da lei
    assert "SP (50,0 %)" in pessoal.descricao


def _coleta_rreo(sem_dado: set[int]) -> siconfi.ColetaRreo:
    cods = [c for c, *_ in estados.UFS]
    receita = {
        c: None if c in sem_dado else siconfi.Receita(icms=2_000_000.0 * c, rcl=10_000_000.0 * c)
        for c in cods
    }
    primario = {c: None if c in sem_dado else 500_000.0 * c for c in cods}
    primario[53] = -1_000_000.0 * 53  # DF no vermelho
    return siconfi.ColetaRreo(2026, 4, receita, primario)


def test_montagem_do_rreo_divide_por_populacao_e_por_rcl() -> None:
    populacao = {c: 1000.0 for c, *_ in estados.UFS}
    primario, icms = estados._rreo(_coleta_rreo({12}), populacao)
    assert primario.referencia == "jan–ago/2026" and icms.referencia == "12 meses até ago/2026"
    assert "acumulado do ano" in primario.descricao and "RPPS" in primario.descricao
    assert primario.maior_e_melhor is True
    assert primario.valores["SP"] == pytest.approx(5.0)  # 500 mil / 10 mi = 5 %
    assert primario.valores["DF"] == pytest.approx(-10.0)
    assert primario.valores["AC"] is None and icms.valores["AC"] is None
    assert icms.valores["SP"] == pytest.approx(2_000_000.0 * 35 / 1000.0)
    assert len(icms.valores) == 27 and icms.unidade == "R$ por pessoa"
    assert icms.brasil is not None and primario.brasil is not None


def _sem_economia(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem as fontes de `estados_economia` (cada uma cai e a seção segue sem ela)."""

    def cai(*a: Any, **k: Any) -> Any:
        raise siconfi.FonteForaDoArError("fora")

    for nome in ("pib", "ibcr", "inflacao", "exportacoes", "concentracao", "trabalho", "credito"):
        monkeypatch.setattr(estados.estados_economia, nome, cai)
    monkeypatch.setattr(estados.ibge_contas_regionais, "pib", cai)
    # A ficha: CAPAG, os anos fechados e a economia por atividade (testados à parte).
    monkeypatch.setattr(estados.ibge_contas_regionais, "setores", cai)
    monkeypatch.setattr(estados.tesouro_capag, "capag", cai)
    monkeypatch.setattr(estados.siconfi, "coletar_historico", cai)


def _pobreza_uf() -> dict[str, list[tuple[date, float]]]:
    pobreza = {str(c): [(date(2025, 1, 1), 20.0 + c / 10)] for c, *_ in estados.UFS}
    return pobreza | {"0": [(date(2025, 1, 1), 25.0)], "1": [(date(2025, 1, 1), 40.0)]}


def test_pobreza_por_uf_fica_so_com_os_estados(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(estados.ipeadata, "por_territorio", lambda *a, **k: _pobreza_uf())
    m = estados._pobreza()
    assert len(m.valores) == 27 and m.valores["SP"] == pytest.approx(23.5)
    assert m.brasil == 25.0 and m.referencia == "2025" and m.maior_e_melhor is False


def test_montar_sem_rede(monkeypatch: pytest.MonkeyPatch) -> None:
    deso = {str(c): [(date(2026, 4, 1), 5.0 + c / 100)] for c, *_ in estados.UFS}
    monkeypatch.setattr(estados.ibge_sidra, "series", lambda *a, **k: deso)
    monkeypatch.setattr(estados.ibge_sidra, "serie", lambda *a, **k: [(date(2026, 4, 1), 5.4)])
    monkeypatch.setattr(estados.ipeadata, "por_territorio", lambda *a, **k: _pobreza_uf())
    monkeypatch.setattr(estados.siconfi, "coletar", lambda *a, **k: _coleta({12}))
    monkeypatch.setattr(estados.siconfi, "coletar_rreo", lambda *a, **k: _coleta_rreo({12}))
    monkeypatch.setattr(estados.siconfi, "coletar_anual", lambda *a, **k: None)
    monkeypatch.setattr(estados.siconfi, "entes", lambda: {c: 1000.0 for c, *_ in estados.UFS})
    _sem_economia(monkeypatch)
    e = estados.montar(Contexto(hoje=date(2026, 11, 14)))
    assert len(e.ufs) == 27
    assert [m.id for m in e.metricas] == [
        "desocupacao",
        "pobreza",
        "gini",
        "pessoal",
        "divida",
        "primario",
        "icms_per_capita",
        "rcl_per_capita",
    ]
    assert e.metricas[0].referencia == "2º tri/2026" and e.metricas[0].brasil == 5.4
    assert "5,4 %" in e.resumo and "limite de alerta" in e.resumo


def test_rreo_fora_do_ar_nao_derruba_as_outras_metricas(monkeypatch: pytest.MonkeyPatch) -> None:
    def cai(*a: Any, **k: Any) -> Any:
        raise siconfi.FonteForaDoArError("fora")

    deso = {str(c): [(date(2026, 4, 1), 5.0)] for c, *_ in estados.UFS}
    monkeypatch.setattr(estados.ibge_sidra, "series", lambda *a, **k: deso)
    monkeypatch.setattr(estados.ibge_sidra, "serie", lambda *a, **k: [(date(2026, 4, 1), 5.4)])
    monkeypatch.setattr(estados.ipeadata, "por_territorio", lambda *a, **k: _pobreza_uf())
    monkeypatch.setattr(estados.siconfi, "coletar", lambda *a, **k: _coleta({12}))
    monkeypatch.setattr(estados.siconfi, "coletar_rreo", cai)
    monkeypatch.setattr(estados.siconfi, "coletar_anual", cai)
    monkeypatch.setattr(estados.siconfi, "entes", lambda: {c: 1000.0 for c, *_ in estados.UFS})
    _sem_economia(monkeypatch)
    e = estados.montar(Contexto(hoje=date(2026, 11, 14)))
    assert [m.id for m in e.metricas] == [
        "desocupacao",
        "pobreza",
        "gini",
        "pessoal",
        "divida",
        "rcl_per_capita",
    ]


# ---------------------------------------------------------------- contas de cada estado (DCA)


def _dca(anexo: str, conta: str, coluna: str, valor: float, texto: str = "") -> dict[str, Any]:
    return {
        "anexo": f"DCA-Anexo {anexo}",
        "cod_conta": conta,
        "conta": texto or conta,
        "coluna": coluna,
        "valor": valor,
    }


def _receita(anexo_c: list[tuple[str, float]]) -> list[dict[str, Any]]:
    return [_dca("I-C", c, siconfi.COL_BRUTA, v) for c, v in anexo_c]


# Trechos reais da DCA 2025 (consultada em 14/11/2026): SP, DF e AC (o Acre não tem a conta do
# adicional de ICMS do fundo de pobreza).
C_SP = _receita(
    [
        ("ReceitasExcetoIntraOrcamentarias", 400067309037.12),
        ("RO1.0.0.0.00.0.0", 391843249289.61),
        ("RO2.0.0.0.00.0.0", 8224059747.51),
        ("RO1.1.0.0.00.0.0", 308817766033.1),
        ("RO1.1.1.2.51.0.0", 31876947927.41),
        ("RO1.1.1.2.52.0.0", 7356323453.8),
        ("RO1.1.1.4.50.1.0", 237071553843.02),
        ("RO1.1.1.4.50.2.0", 989671514),
        ("RO1.7.1.0.00.0.0", 16976648259.35),
        ("RO1.7.1.1.50.0.0", 2198843536.87),
        ("RO1.7.5.1.00.0.0", 27628403587.9),
    ]
)
C_DF = _receita(
    [
        ("ReceitasExcetoIntraOrcamentarias", 42812567643.95),
        ("RO1.0.0.0.00.0.0", 42206905726.33),
        ("RO2.0.0.0.00.0.0", 605661917.62),
        ("RO1.1.0.0.00.0.0", 27036709581.04),
        ("RO1.1.1.2.51.0.0", 1980575602.08),
        ("RO1.1.1.2.52.0.0", 397912793.92),
        ("RO1.1.1.4.50.1.0", 12495978651.6),
        ("RO1.1.1.4.50.2.0", 102870659.48),
        ("RO1.7.1.0.00.0.0", 3634462504.54),
        ("RO1.7.1.1.50.0.0", 1401061527.03),
        ("RO1.7.5.1.00.0.0", 3378160052.62),
    ]
)
C_AC = _receita(
    [
        ("ReceitasExcetoIntraOrcamentarias", 14543589194.55),
        ("RO1.1.0.0.00.0.0", 3356381239.02),
        ("RO1.1.1.2.51.0.0", 157312868.39),
        ("RO1.1.1.2.52.0.0", 9550865.61),
        ("RO1.1.1.4.50.1.0", 2220306998.18),
        ("RO1.7.1.0.00.0.0", 8580977171.32),
        ("RO1.7.1.1.50.0.0", 7699187827.42),
        ("RO1.7.5.1.00.0.0", 1365078748.25),
    ]
)
LIQ = siconfi.COL_LIQUIDADA
D_SP = [
    _dca("I-D", "TotalDespesas", LIQ, 369170001590.1),
    _dca("I-D", "DO3.1.00.00.00.00", LIQ, 153744558649.7),
    _dca("I-D", "DO3.2.00.00.00.00", LIQ, 15491578316.02),
    _dca("I-D", "DO3.3.00.00.00.00", LIQ, 164618844359.92),
    _dca("I-D", "DO4.4.00.00.00.00", LIQ, 11939191762.84),
    _dca("I-D", "DO4.5.00.00.00.00", LIQ, 10892702376.33),
    _dca("I-D", "DO4.6.00.00.00.00", LIQ, 12483126125.29),
    # a mesma conta em outra coluna não pode entrar
    _dca("I-D", "DO4.4.00.00.00.00", "Despesas Empenhadas", 17046272275.75),
]
D_DF = [  # o DF não tem amortização lançada neste trecho: grupo ausente vale zero
    _dca("I-D", "TotalDespesas", LIQ, 42370260061.43),
    _dca("I-D", "DO3.1.00.00.00.00", LIQ, 22321759198.82),
    _dca("I-D", "DO3.2.00.00.00.00", LIQ, 445626882.92),
    _dca("I-D", "DO3.3.00.00.00.00", LIQ, 17012252934),
    _dca("I-D", "DO4.4.00.00.00.00", LIQ, 1858202159.79),
    _dca("I-D", "DO4.5.00.00.00.00", LIQ, 76702580.67),
    _dca("I-D", "DO4.6.00.00.00.00", LIQ, 655716305.23),
]


def _funcoes(total: float, linhas: list[tuple[str, float]]) -> list[dict[str, Any]]:
    # Na DCA-Anexo I-E a conta é sempre `TotalDespesas`; a função vem no texto.
    itens = [_dca("I-E", "TotalDespesas", LIQ, total, "Despesas Exceto Intraorçamentárias")]
    itens += [_dca("I-E", "TotalDespesas", LIQ, v, t) for t, v in linhas]
    # subfunção e intraorçamentárias não são função
    itens.append(_dca("I-E", "TotalDespesas", LIQ, 1.0, "10.302 - Assistência Hospitalar"))
    itens.append(_dca("I-E", "TotalDespesas", LIQ, 1.0, "Despesas Intraorçamentárias"))
    return itens


F_SP = _funcoes(
    355439276197.86,
    [
        ("01 - Legislativa", 3495057248.48),
        ("04 - Administração", 7459323154.63),
        ("06 - Segurança Pública", 17697921882.41),
        ("09 - Previdência Social", 30818599756.54),
        ("10 - Saúde", 42153192468.94),
        ("12 - Educação", 69278015667.13),
        ("26 - Transporte", 19088178066.7),
        ("28 - Encargos Especiais", 111822024706.41),
    ],
)


def test_receita_anual_de_sp_soma_o_adicional_do_icms() -> None:
    r = siconfi.parse_receita_anual(C_SP)
    assert r is not None
    assert r.total == 400067309037.12
    assert r.icms == pytest.approx(237071553843.02 + 989671514)
    assert (r.ipva, r.itcmd, r.fpe) == (31876947927.41, 7356323453.8, 2198843536.87)
    assert r.corrente is not None and r.capital is not None
    assert r.corrente + r.capital == pytest.approx(r.total, rel=1e-4)


def test_receita_anual_do_df_e_do_acre_sem_a_conta_do_adicional() -> None:
    df = siconfi.parse_receita_anual(C_DF)
    assert df is not None and df.icms == pytest.approx(12495978651.6 + 102870659.48)
    ac = siconfi.parse_receita_anual(C_AC)
    assert ac is not None and ac.icms == 2220306998.18  # só a conta principal
    assert ac.corrente is None and ac.capital is None  # trecho sem os dois totais
    assert siconfi.parse_receita_anual([]) is None
    assert siconfi.parse_receita_anual(C_SP[1:]) is None  # sem o total, nada


def test_despesa_anual_usa_so_a_coluna_liquidada_e_fecha_no_total() -> None:
    d = siconfi.parse_despesa_anual(D_SP)
    assert d is not None
    assert d.investimentos == 11939191762.84  # e não os 17,0 bi empenhados
    soma = d.pessoal + d.juros + d.outras_correntes + d.investimentos + d.inversoes + d.amortizacao
    assert soma == pytest.approx(d.total, rel=1e-6)
    df = siconfi.parse_despesa_anual(D_DF)
    assert df is not None and df.pessoal == 22321759198.82
    assert siconfi.parse_despesa_anual([]) is None
    sem_grupo = siconfi.parse_despesa_anual(D_SP[:2])
    assert sem_grupo is not None and sem_grupo.juros == 0.0  # grupo ausente vale zero


def test_funcoes_anuais_pegam_so_o_codigo_de_dois_digitos() -> None:
    f = siconfi.parse_funcoes_anuais(F_SP)
    assert f is not None
    assert f.total == 355439276197.86
    assert f.por_funcao["10"] == ("Saúde", 42153192468.94)
    assert "10.302" not in f.por_funcao and len(f.por_funcao) == 8
    assert siconfi.parse_funcoes_anuais([]) is None
    assert siconfi.parse_funcoes_anuais(F_SP[:1]) is None  # só o total, sem função


def test_parse_dca_junta_os_tres_anexos_e_devolve_none_se_nada_veio() -> None:
    c = siconfi.parse_dca(C_SP + D_SP + F_SP)
    assert c is not None and c.receita and c.despesa and c.funcoes
    so_receita = siconfi.parse_dca(C_AC)
    assert so_receita is not None and so_receita.despesa is None and so_receita.funcoes is None
    assert siconfi.parse_dca([]) is None


# Trecho real do RGF-Anexo 02 de SP (2º quadrimestre de 2026) e do AM, que lança os empréstimos em
# "Financiamentos".
def _div(conta: str, valor: float) -> dict[str, Any]:
    return _linha(conta, COL2, valor)


A2_COMP_SP = [
    _div("DividaConsolidada", 390041766345.85),
    _div("DividaContratual", 359521548266.76),
    _div("RGF2EmprestimosInternos", 22800735828.09),
    _div("RGF2EmprestimosExternos", 24926152012.99),
    _div("RGF2ReestruturacaoDaDividaDeEstadosEMunicipios", 311646985702.58),
    _div("RGF2ParcelamentoERenegociacaoDeDividas", 147674723.1),
    _div("PrecatoriosPosterioresA05052000VencidosENaoPagos", 30490337111.85),
    _div("OutrasDividas", 29880967.24),
    _div("DeducoesDaDividaConsolidada", 74133295498.6),
    _div("RGF2DisponibilidadeDeCaixa", 69524884535.06),
    _div("DemaisHaveresFinanceiros", 4608410963.54),
    _div("DividaConsolidadaLiquida", 315908470847.25),
    _div("PercentualDaDCLSobreARCL", 113.03),
    _div("RGF2ReceitaCorrenteLiquida", 279658527567.42),
]
A2_COMP_AM = [
    _div("DividaConsolidada", 10087765866.21),
    _div("RGF2ReestruturacaoDaDividaDeEstadosEMunicipios", 184902303.93),
    _div("RGF2FinanciamentosInternos", 5430200000.0),
    _div("RGF2FinanciamentosExternos", 4450200000.0),
    _div("RGF2ParcelamentoERenegociacaoDeDividas", 22385847.63),
    _div("DeducoesDaDividaConsolidada", 4032200000.0),
    _div("RGF2DisponibilidadeDeCaixa", 4029600000.0),
    _div("DemaisHaveresFinanceiros", 2600000.0),
]


def test_composicao_da_divida_de_sp_fecha_no_total() -> None:
    c = siconfi.parse_composicao_divida(A2_COMP_SP, 2)
    assert c is not None
    soma = c.uniao + c.emprestimos_internos + c.emprestimos_externos + c.parcelamentos
    soma += c.precatorios + c.outras
    assert soma == pytest.approx(c.total, rel=1e-6)
    assert c.caixa is not None and c.haveres is not None and c.deducoes is not None
    assert c.caixa + c.haveres == pytest.approx(c.deducoes, rel=1e-4)
    assert siconfi.parse_composicao_divida(A2_COMP_SP, 1) is None  # outra coluna
    assert siconfi.parse_composicao_divida([], 2) is None
    d = siconfi.parse_divida(A2_COMP_SP, 2)
    assert d is not None and d.composicao == c


def test_composicao_do_am_soma_financiamentos_aos_emprestimos() -> None:
    c = siconfi.parse_composicao_divida(A2_COMP_AM, 2)
    assert c is not None
    assert c.emprestimos_internos == 5430200000.0 and c.emprestimos_externos == 4450200000.0
    assert c.precatorios == 0.0  # conta ausente vale zero


def _contas_de_teste(sem_dca: set[int] | None = None) -> estados.EstadosContas:
    cods = [c for c, *_ in estados.UFS]
    ucs = {
        35: siconfi.parse_dca(C_SP + D_SP + F_SP),
        53: siconfi.parse_dca(C_DF + D_DF),  # DF sem o anexo de funções
        12: siconfi.parse_dca(C_AC),
    }
    dca = {c: (ucs.get(c) if c not in (sem_dca or set()) else None) for c in cods}
    rcl: dict[int, float | None] = {c: 1e9 * c for c in cods}
    rcl[35] = 266.2e9
    anual = siconfi.ColetaAnual(2025, dca, rcl)
    divida = {c: None for c in cods}
    divida[35] = siconfi.parse_divida(A2_COMP_SP, 2)
    rgf = siconfi.ColetaRgf(2026, 2, {}, divida)
    populacao = {c: 1_000_000.0 * (c % 10 + 1) for c in cods}
    populacao[35] = 46_024_937.0
    return estados._contas(anual, rgf, populacao, Contexto().agora())


def test_fatias_de_cada_bloco_somam_o_total_e_vem_da_maior_para_a_menor() -> None:
    contas = _contas_de_teste()
    for uf, ce in contas.contas.items():
        for b in ce.blocos:
            assert b.total is not None
            assert sum(f.valor for f in b.fatias) == pytest.approx(b.total, rel=0.01), (uf, b.id)
            nomes = [f.nome for f in b.fatias]
            corpo = [f.valor for f in b.fatias if f.nome != "Outras"]
            assert corpo == sorted(corpo, reverse=True), (uf, b.id)
            if "Outras" in nomes:
                assert nomes[-1] == "Outras"
            assert b.referencia and b.fonte and b.descricao
    assert [b.id for b in contas.contas["SP"].blocos] == [
        "receita",
        "despesa_grupo",
        "despesa_funcao",
        "divida",
        "deducoes",
    ]


def test_contas_de_sp_numeros_e_posicao() -> None:
    sp = _contas_de_teste().contas["SP"]
    rec = next(b for b in sp.blocos if b.id == "receita")
    assert rec.fatias[0].nome == "ICMS" and rec.total == 400067.3
    uniao = next(n for n in sp.numeros if n.id == "sp_divida_uniao")
    assert uniao.valor == 311.6 and uniao.unidade == "R$ bilhões"
    inv = next(n for n in sp.numeros if n.id == "sp_investimento")
    assert inv.valor == pytest.approx(11.939 / 266.2 * 100, abs=0.05) and inv.unidade == "% da RCL"
    icms = next(n for n in sp.numeros if n.id == "sp_icms_por_habitante")
    assert "º maior de" in icms.detalhe and icms.casas == 0
    assert all(len(n.detalhe) <= 60 for n in sp.numeros)


def test_estado_sem_dca_ou_sem_uma_conta_sai_com_o_que_tem() -> None:
    contas = _contas_de_teste(sem_dca={53})
    assert "DF" not in contas.contas  # nada para mostrar: fora, e não vazio
    ac = contas.contas["AC"]
    assert [b.id for b in ac.blocos] == ["receita"]  # sem despesa, função nem dívida
    assert not any(n.id == "ac_divida_uniao" for n in ac.numeros)
    df = _contas_de_teste().contas["DF"]
    assert [b.id for b in df.blocos] == ["receita", "despesa_grupo"]  # sem o anexo de funções


def test_montar_poe_as_contas_no_memo_e_aponta_o_arquivo(monkeypatch: pytest.MonkeyPatch) -> None:
    deso = {str(c): [(date(2026, 4, 1), 5.0)] for c, *_ in estados.UFS}
    monkeypatch.setattr(estados.ibge_sidra, "series", lambda *a, **k: deso)
    monkeypatch.setattr(estados.ibge_sidra, "serie", lambda *a, **k: [(date(2026, 4, 1), 5.4)])
    monkeypatch.setattr(estados.ipeadata, "por_territorio", lambda *a, **k: _pobreza_uf())
    monkeypatch.setattr(estados.siconfi, "coletar", lambda *a, **k: _coleta({12}))
    monkeypatch.setattr(estados.siconfi, "coletar_rreo", lambda *a, **k: _coleta_rreo({12}))
    monkeypatch.setattr(estados.siconfi, "entes", lambda: {c: 1000.0 for c, *_ in estados.UFS})
    monkeypatch.setattr(estados.siconfi, "coletar_anual", lambda *a, **k: _anual_falso())
    _sem_economia(monkeypatch)
    ctx = Contexto(hoje=date(2026, 11, 14))
    e = estados.montar(ctx)
    assert e.arquivo_contas == "estados-contas.json"
    assert ctx.memo["estados_contas"].id == "estados-contas"


def _anual_falso() -> siconfi.ColetaAnual:
    cods = [c for c, *_ in estados.UFS]
    dca = {c: siconfi.parse_dca(C_SP + D_SP + F_SP) for c in cods}
    return siconfi.ColetaAnual(2025, dca, {c: 266.2e9 for c in cods})


def test_sem_dca_o_estados_json_sai_sem_o_arquivo_de_contas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deso = {str(c): [(date(2026, 4, 1), 5.0)] for c, *_ in estados.UFS}
    monkeypatch.setattr(estados.ibge_sidra, "series", lambda *a, **k: deso)
    monkeypatch.setattr(estados.ibge_sidra, "serie", lambda *a, **k: [(date(2026, 4, 1), 5.4)])
    monkeypatch.setattr(estados.ipeadata, "por_territorio", lambda *a, **k: _pobreza_uf())
    monkeypatch.setattr(estados.siconfi, "coletar", lambda *a, **k: _coleta({12}))
    monkeypatch.setattr(estados.siconfi, "coletar_rreo", lambda *a, **k: _coleta_rreo({12}))
    monkeypatch.setattr(estados.siconfi, "entes", lambda: {c: 1000.0 for c, *_ in estados.UFS})
    monkeypatch.setattr(estados.siconfi, "coletar_anual", lambda *a, **k: None)
    _sem_economia(monkeypatch)
    ctx = Contexto(hoje=date(2026, 11, 14))
    e = estados.montar(ctx)
    assert e.arquivo_contas == "" and "estados_contas" not in ctx.memo


def test_composicao_le_as_demais_dividas_contratuais() -> None:
    """TO e PR lançam parte da dívida em "Demais dívidas contratuais" (achado em 14/11/2026)."""
    col = "Até o 2º Quadrimestre"
    linhas = {
        "DividaConsolidada": 5471.7,
        "RGF2FinanciamentosInternos": 3403.1,
        "RGF2EmprestimosInternos": 0.4,
        "RGF2FinanciamentosExternos": 1031.6,
        "RGF2ParcelamentoERenegociacaoDeDividas": 87.4,
        "RGF2DemaisDividasContratuais": 174.1,
        "PrecatoriosPosterioresA05052000VencidosENaoPagos": 737.7,
        "OutrasDividas": 37.3,
    }
    itens = [{"cod_conta": k, "coluna": col, "valor": v} for k, v in linhas.items()]
    c = siconfi.parse_composicao_divida(itens, 2)
    assert c is not None
    partes = (
        c.uniao
        + c.emprestimos_internos
        + c.emprestimos_externos
        + c.parcelamentos
        + c.demais_contratuais
        + c.precatorios
        + c.outras
    )
    assert partes == pytest.approx(c.total, abs=0.2)  # os valores acima vêm arredondados


@pytest.fixture(autouse=True)
def _sem_a_receita(monkeypatch: pytest.MonkeyPatch) -> None:
    """Os testes de `montar` não chamam a Receita: sem ela, a métrica fica de fora."""

    def fora() -> None:
        raise RuntimeError("sem rede no teste")

    monkeypatch.setattr(estados.receita_arrecadacao, "arrecadacao", fora)


def test_arrecadacao_federal_por_habitante(monkeypatch: pytest.MonkeyPatch) -> None:
    meses = [(date(2026, m, 1), 1000.0) for m in range(1, 10)]
    monkeypatch.setattr(
        estados.receita_arrecadacao,
        "arrecadacao",
        lambda: {"ir": {"SP": meses, "AC": meses[:1], "BR": meses}},
    )
    m = estados._arrecadacao_federal({35: 100.0, 12: 10.0})
    assert m.valores["SP"] == 90.0 and m.valores["AC"] == 100.0 and m.valores["RJ"] is None
    assert m.brasil == pytest.approx(10000.0 / 110.0)
    assert m.referencia == "12 meses até set/2026"
