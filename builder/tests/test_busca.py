"""O índice da busca: o que entra e os sinônimos."""

import json
from pathlib import Path

from sacibras import busca


def test_sinonimos_sem_acento_e_sem_repetir_o_que_ja_esta_no_texto() -> None:
    extras = busca.sinonimos_de("Taxa de desocupação")
    assert "desemprego" in extras
    assert "desocupacao" not in extras.split()
    assert "calote" in busca.sinonimos_de("Inadimplência da carteira")


def test_indice_le_os_json_gravados(tmp_path: Path) -> None:
    painel = {
        "secoes": [
            {"id": "resumo", "titulo": "Resumo", "arquivo": "resumo.json"},
            {"id": "juros", "titulo": "Juros e Copom", "arquivo": "juros.json", "resumo": ""},
            {"id": "estados", "titulo": "Estados", "arquivo": "estados.json", "resumo": ""},
            {"id": "sumiu", "titulo": "Sumiu", "arquivo": "sumiu.json", "resumo": ""},
        ]
    }
    juros = {
        "cartoes": [{"id": "selic-meta", "rotulo": "Selic meta", "detalhe": ""}],
        "graficos": [{"id": "curva", "titulo": "Curva prefixada"}],
        "tabelas": [{"id": "acerto", "titulo": "Acerto do Focus"}],
    }
    estados = {
        "metricas": [{"id": "icms", "nome": "ICMS por habitante"}],
        "ufs": [{"sigla": "RJ", "nome": "Rio de Janeiro"}],
    }
    for nome, dados in [("painel", painel), ("juros", juros), ("estados", estados)]:
        (tmp_path / f"{nome}.json").write_text(json.dumps(dados), encoding="utf-8")
    assert busca.gravar(tmp_path) == 7  # a seção sem JSON fica de fora
    itens = {i["h"]: i for i in json.loads((tmp_path / "busca.json").read_text("utf-8"))}
    assert set(itens) == {
        "#juros",
        "#juros/c-selic-meta",
        "#juros/g-curva",
        "#juros/t-acerto",
        "#estados",
        "#estados/m-icms",
        "#estados/uf-RJ",
    }
    assert "copom" in itens["#juros/c-selic-meta"]["p"]
    assert itens["#estados/uf-RJ"]["o"] == "Estados · RJ"
