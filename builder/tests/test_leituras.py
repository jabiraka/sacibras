"""Os prazos de releitura: cada um aponta para um número que existe e tem prazo coerente."""

from __future__ import annotations

import importlib
from datetime import date, timedelta

from sacibras import leituras
from sacibras.cli import _falhas_md
from sacibras.leituras import Leitura, situacao
from sacibras.schema import ItemSecao


def test_cada_leitura_aponta_para_um_numero_que_existe() -> None:
    for x in leituras.LEITURAS:
        modulo, nome = x.onde.split(".")
        assert hasattr(importlib.import_module(f"sacibras.{modulo}"), nome), x.onde


def test_prazo_depois_da_leitura_e_sem_repeticao() -> None:
    for x in leituras.LEITURAS:
        assert x.reler_ate > x.lida_em, x.o_que
        assert x.como.strip(), x.o_que
    assert len({x.onde for x in leituras.LEITURAS}) == len(leituras.LEITURAS)


def test_situacao_pelo_prazo() -> None:
    x = Leitura("teste", "leis.META_CONTINUA", date(2026, 1, 1), date(2026, 6, 30), "lá")
    assert situacao(x, date(2026, 6, 1)) == "em dia"
    assert situacao(x, date(2026, 6, 30) - timedelta(days=leituras.AVISO_DIAS)) == "vence logo"
    assert situacao(x, date(2026, 6, 30)) == "vence logo"
    assert situacao(x, date(2026, 7, 1)) == "vencida"


def test_tabela_mostra_so_as_pendentes() -> None:
    longe = max(x.reler_ate for x in leituras.LEITURAS) + timedelta(days=1)
    assert leituras.tabela(longe).count("| vencida |") == len(leituras.LEITURAS)
    cedo = min(x.lida_em for x in leituras.LEITURAS)
    assert "Nenhuma releitura" in leituras.tabela(cedo - timedelta(days=400))


def test_falhas_em_markdown() -> None:
    assert _falhas_md([]) == ""
    item = ItemSecao(id="juros", titulo="Juros", arquivo="juros.json", ok=False, erro="a | b\nc")
    md = _falhas_md([item])
    assert "| Juros (`juros`) | não | a \\| b c |" in md
