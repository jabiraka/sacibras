"""Dado privado na tela, sem CSV nem PNG (Caio, 15/11/2026)."""

from datetime import date

import pytest

from sacibras import licencas
from sacibras.catalogo import SGS
from sacibras.fontes import ipeadata
from sacibras.schema import Grafico, Secao, Serie
from sacibras.secoes.base import Contexto


def _grafico(fonte: str) -> Grafico:
    return Grafico(
        id="x",
        titulo="x",
        unidade="%",
        periodicidade="M",
        series=[Serie(id="a", nome="a", pontos=[(date(2026, 1, 1), 1.0)])],
        fonte=fonte,
    )


def test_fonte_privada_tira_o_download_e_a_publica_nao() -> None:
    ctx = Contexto(hoje=date(2026, 11, 15))
    igpm = _grafico(ctx.fonte_sgs("IPCA_12M", "INPC", "IGPM"))
    assert "FGV IBRE" in igpm.fonte and igpm.sem_download.startswith("Sem download:")
    assert "Fecomercio" in _grafico(ctx.fonte_sgs("CONFIANCA_CONSUMIDOR")).sem_download
    assert "B3" in _grafico(f"{ipeadata.FONTE_IBOVESPA}; cálculo próprio").sem_download
    assert _grafico(ctx.fonte_sgs("IPCA_12M", "INPC")).sem_download == ""
    assert _grafico("Penn World Table 11.0 (licença CC BY 4.0)").sem_download == ""


def test_o_json_antigo_relido_tambem_perde_o_download() -> None:
    """O que volta da rodada anterior (`completar`, `anterior`) passa pela mesma regra."""
    bruto = _grafico("Banco Central, SGS 189; IGP-M: FGV IBRE").model_dump(mode="json")
    bruto["sem_download"] = ""
    assert Grafico.model_validate(bruto).sem_download


def test_toda_serie_com_origem_privada_tem_licenca_registrada() -> None:
    for chave, s in SGS.items():
        if s.origem:
            assert licencas.sem_download(s.origem), chave


def test_cada_licenca_tem_o_trecho_lido_e_a_data() -> None:
    for x in licencas.LICENCAS:
        assert x.trecho and x.termos and x.lida_em <= date(2026, 11, 15)
        assert x.exporta or x.motivo


def test_o_que_a_licenca_nao_deixa_mostrar_nem_vai_a_tela() -> None:
    """FGV: os termos vedam também a divulgação (Caio, 15/11/2026: "só mostrar se for
    permitido"). Fecomercio (catálogo do BC, ODbL) e B3 (decisão do Caio) vão, sem download."""
    ctx = Contexto(hoje=date(2026, 11, 15))
    with pytest.raises(ValueError, match="não pode ir à tela"):
        ctx.sgs("IGPM")
    with pytest.raises(ValueError, match="FGV"):
        ctx.sgs("UCI_INDUSTRIA")
    secao = Secao(
        id="x",
        titulo="x",
        resumo="",
        graficos=[
            _grafico("Banco Central, SGS 28561 (FGV)"),  # como estava no JSON antigo
            _grafico(ctx.fonte_sgs("CONFIANCA_CONSUMIDOR")).model_copy(update={"id": "icc"}),
            _grafico(ipeadata.FONTE_IBOVESPA).model_copy(update={"id": "ibov"}),
        ],
        gerado_em="2026-11-15T00:00:00Z",
    )
    assert licencas.tirar_o_que_nao_pode(secao) == ["x"]
    assert [g.id for g in secao.graficos] == ["icc", "ibov"]
    assert licencas.B3.mostra and licencas.B3.decisao.startswith("Caio, 15/11/2026")
