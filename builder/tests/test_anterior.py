"""Fonte que falha não deixa número em branco: o que faltou vem da rodada anterior."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from sacibras import construir, rede
from sacibras.cli import _falhas_md
from sacibras.schema import Cartao, ItemSecao, Secao, SimuladorDivida
from sacibras.secoes.base import Contexto

AGORA = datetime(2026, 11, 14, tzinfo=UTC)


def _cartao(id: str, valor: float = 1.0) -> Cartao:
    return Cartao(
        id=id,
        rotulo=id,
        valor=valor,
        unidade="%",
        referencia=date(2026, 10, 1),
        periodicidade="M",
        fonte="x",
    )


def _atividade(*ids: str, valor: float = 1.0) -> Secao:
    return Secao(
        id="atividade",
        titulo="Atividade",
        cartoes=[_cartao(i, valor) for i in ids],
        gerado_em=AGORA,
    )


def test_juntar_poe_o_que_faltou_depois_do_vizinho() -> None:
    def chave(x: str) -> str:
        return x

    assert construir._juntar(["a", "c"], ["a", "b", "c"], chave) == ["a", "b", "c"]
    assert construir._juntar(["c"], ["a", "b", "c"], chave) == ["a", "b", "c"]
    assert construir._juntar(["a", "b"], ["a"], chave) == ["a", "b"]


def test_completar_traz_so_o_que_as_partes_listam(tmp_path: Path) -> None:
    antigo = _atividade("pib-tt", "pib-4t", "peca-que-saiu-do-codigo", valor=9.0)
    (tmp_path / "atividade.json").write_text(antigo.model_dump_json(), encoding="utf-8")
    novo = _atividade("pib-4t", valor=2.0)
    mantidos = construir.completar(novo, tmp_path / "atividade.json")
    assert mantidos == ["pib-tt"]
    assert [c.id for c in novo.cartoes] == ["pib-tt", "pib-4t"]
    assert novo.cartoes[1].valor == 2.0  # o número novo não é trocado pelo antigo


def test_completar_traz_simulador(tmp_path: Path) -> None:
    sim = SimuladorDivida(
        ano_inicial=2026,
        divida_inicial=78.0,
        anos=[2026],
        juro=[1.0],
        crescimento=[1.0],
        inflacao=[1.0],
        primario=[0.0],
        focus_divida=[None],
        realizado=[],
        fonte="x",
        nota="",
    )
    antigo = Secao(id="fiscal", titulo="F", simulador=sim, gerado_em=AGORA)
    (tmp_path / "fiscal.json").write_text(antigo.model_dump_json(), encoding="utf-8")
    novo = Secao(id="fiscal", titulo="F", gerado_em=AGORA)
    assert construir.completar(novo, tmp_path / "fiscal.json") == ["simulador"]
    assert novo.simulador == sim


def test_completar_sem_rodada_anterior_ou_de_outra_versao(tmp_path: Path) -> None:
    novo = _atividade("pib-4t")
    assert construir.completar(novo, tmp_path / "nada.json") == []
    (tmp_path / "velho.json").write_text('{"campo_que_nao_existe": 1}', encoding="utf-8")
    assert construir.completar(novo, tmp_path / "velho.json") == []


def _uma_secao(monkeypatch: pytest.MonkeyPatch, montar: object) -> None:
    monkeypatch.setattr(construir, "ORDEM", [("atividade", "Atividade", montar)])
    monkeypatch.setattr(construir, "Contexto", Contexto)


def test_build_so_completa_quando_a_fonte_falhou(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    antigo = _atividade("pib-tt", "pib-4t")
    (tmp_path / "atividade.json").write_text(antigo.model_dump_json(), encoding="utf-8")

    # Sem falha de fonte: a peça que a seção não trouxe é decisão do código, não volta.
    _uma_secao(monkeypatch, lambda ctx: _atividade("pib-4t"))
    painel = construir.construir(tmp_path)
    gravado = json.loads((tmp_path / "atividade.json").read_text(encoding="utf-8"))
    assert [c["id"] for c in gravado["cartoes"]] == ["pib-4t"]
    assert painel.secoes[1].mantidos == []

    # Com falha: volta da rodada anterior, e a página inicial também a recebe.
    (tmp_path / "atividade.json").write_text(antigo.model_dump_json(), encoding="utf-8")

    def montar_com_falha(ctx: Contexto) -> Secao:
        rede.FALHAS.append("https://fonte.fora/do/ar")
        return _atividade("pib-4t")

    _uma_secao(monkeypatch, montar_com_falha)
    painel = construir.construir(tmp_path)
    gravado = json.loads((tmp_path / "atividade.json").read_text(encoding="utf-8"))
    assert [c["id"] for c in gravado["cartoes"]] == ["pib-tt", "pib-4t"]
    assert painel.secoes[1].mantidos == ["pib-tt"]


def test_falhas_md_lista_o_que_veio_da_rodada_anterior() -> None:
    item = ItemSecao(
        id="externo", titulo="Setor externo", arquivo="externo.json", ok=True, mantidos=["a"]
    )
    md = _falhas_md([item])
    assert "- Setor externo (`externo`): a" in md
    assert "| Seção" not in md
