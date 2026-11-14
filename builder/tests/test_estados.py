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
    assert (pessoal.limites[0].valor, pessoal.limites[0].rotulo) == (49, "limite máximo do RGF")
    assert [x.valor for x in divida.limites] == [200, 180]
    assert rcl.valores["SP"] == 35_000.0 and rcl.valores["AC"] is None
    assert "AC" not in alertas and alertas["SP"] == 44.1


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


def test_montar_sem_rede(monkeypatch: pytest.MonkeyPatch) -> None:
    deso = {str(c): [(date(2026, 4, 1), 5.0 + c / 100)] for c, *_ in estados.UFS}
    monkeypatch.setattr(estados.ibge_sidra, "series", lambda *a, **k: deso)
    monkeypatch.setattr(estados.ibge_sidra, "serie", lambda *a, **k: [(date(2026, 4, 1), 5.4)])
    monkeypatch.setattr(estados.siconfi, "coletar", lambda *a, **k: _coleta({12}))
    monkeypatch.setattr(estados.siconfi, "coletar_rreo", lambda *a, **k: _coleta_rreo({12}))
    monkeypatch.setattr(estados.siconfi, "entes", lambda: {c: 1000.0 for c, *_ in estados.UFS})
    e = estados.montar(Contexto(hoje=date(2026, 11, 14)))
    assert len(e.ufs) == 27
    assert [m.id for m in e.metricas] == [
        "desocupacao",
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
    monkeypatch.setattr(estados.siconfi, "coletar", lambda *a, **k: _coleta({12}))
    monkeypatch.setattr(estados.siconfi, "coletar_rreo", cai)
    monkeypatch.setattr(estados.siconfi, "entes", lambda: {c: 1000.0 for c, *_ in estados.UFS})
    e = estados.montar(Contexto(hoje=date(2026, 11, 14)))
    assert [m.id for m in e.metricas] == ["desocupacao", "pessoal", "divida", "rcl_per_capita"]
