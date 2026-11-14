"""Estados sem rede: o parser do RGF (SICONFI) com trechos reais e a montagem das métricas."""

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


def test_montar_sem_rede(monkeypatch: pytest.MonkeyPatch) -> None:
    deso = {str(c): [(date(2026, 4, 1), 5.0 + c / 100)] for c, *_ in estados.UFS}
    monkeypatch.setattr(estados.ibge_sidra, "series", lambda *a, **k: deso)
    monkeypatch.setattr(estados.ibge_sidra, "serie", lambda *a, **k: [(date(2026, 4, 1), 5.4)])
    monkeypatch.setattr(estados.siconfi, "coletar", lambda *a, **k: _coleta({12}))
    monkeypatch.setattr(estados.siconfi, "entes", lambda: {c: 1000.0 for c, *_ in estados.UFS})
    e = estados.montar(Contexto(hoje=date(2026, 11, 14)))
    assert len(e.ufs) == 27
    assert [m.id for m in e.metricas] == ["desocupacao", "pessoal", "divida", "rcl_per_capita"]
    assert e.metricas[0].referencia == "2º tri/2026" and e.metricas[0].brasil == 5.4
    assert "5,4 %" in e.resumo and "limite de alerta" in e.resumo
