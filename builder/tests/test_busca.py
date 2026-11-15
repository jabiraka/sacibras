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
    assert busca.gravar(tmp_path) == 8  # a seção sem JSON fica de fora; o glossário entra
    itens = {i["h"]: i for i in json.loads((tmp_path / "busca.json").read_text("utf-8"))}
    assert set(itens) == {
        "#juros",
        "#juros/c-selic-meta",
        "#juros/g-curva",
        "#juros/t-acerto",
        "#estados",
        "#estados/m-icms",
        "#estados/uf-RJ",
        "#glossario",
    }
    assert "copom" in itens["#juros/c-selic-meta"]["p"]
    assert itens["#estados/uf-RJ"]["o"] == "Estados · RJ"


def test_palavras_em_ingles_espanhol_e_frances() -> None:
    assert "unemployment" in busca.sinonimos_de("Taxa de desocupação")
    assert "desempleo" in busca.sinonimos_de("Taxa de desocupação")
    assert "chomage" in busca.sinonimos_de("Taxa de desocupação")
    assert "credit rating" in busca.sinonimos_de("Nota de crédito do Brasil")
    assert "exchange rate" in busca.sinonimos_de("Dólar")
    assert "gdp" in busca.sinonimos_de("PIB no trimestre")
    # Tudo sem acento e em minúsculas, como o navegador compara.
    for palavras in busca.OUTRAS_LINGUAS.values():
        assert all(p == busca.normalizar(p) for p in palavras)


def test_titulo_em_outras_linguas_vai_a_parte() -> None:
    item = busca._item("Desocupação", "Trabalho · número", "#trabalho/c-desocupacao")
    assert "unemployment" in item.lt
    assistido = busca._item("Estados", "Assunto", "#estados", "a desocupação vai de 2 a 10 %")
    assert "unemployment" not in assistido.lt and "unemployment" in assistido.p


def test_numero_como_a_busca_compara() -> None:
    assert busca.numero(13.75, 2) == "13,75"
    assert busca.numero(128450.4, 0) == "128450"  # sem o ponto de milhar
    assert busca.numero(-2.14, 1) == "-2,1"
    assert busca.numero(-0.04, 1) == "0,0"  # zero arredondado não leva sinal


def test_indice_guarda_os_numeros_do_cartao_e_da_tabela(tmp_path: Path) -> None:
    painel = {"secoes": [{"id": "juros", "titulo": "Juros e Copom", "arquivo": "juros.json"}]}
    juros = {
        "cartoes": [
            {"id": "selic-meta", "rotulo": "Selic meta", "detalhe": "", "valor": 13.75, "casas": 2},
            {"id": "nota", "rotulo": "Nota", "detalhe": "", "valor": 0, "casas": 0, "texto": "BB"},
        ],
        "tabelas": [
            {
                "id": "ciclos",
                "titulo": "Ciclos",
                "linhas": [
                    {"rotulo": "a", "valores": [13.75, None, 2.0], "casas": 2},
                    {"rotulo": "b", "valores": [13.75, 1234.5], "casas": 1},
                ],
            }
        ],
    }
    (tmp_path / "painel.json").write_text(json.dumps(painel), encoding="utf-8")
    (tmp_path / "juros.json").write_text(json.dumps(juros), encoding="utf-8")
    itens = {i.h: i for i in busca.montar(tmp_path)}
    assert itens["#juros/c-selic-meta"].n == "13,75"
    assert itens["#juros/c-nota"].n == ""  # o resultado é um nome, não um número
    # Cada número uma vez, com as casas da linha: 13,75 com uma casa é "13,8".
    assert itens["#juros/t-ciclos"].n == "13,75 2,00 13,8 1234,5"


def test_assuntos_em_chines_japones_e_arabe() -> None:
    inflacao = busca._item("Inflação", "Assunto", "#inflacao")
    for termo in ("通货膨胀", "通貨膨脹", "インフレ", "التضخم"):
        assert termo in inflacao.lt.split()
    # O árabe vai ao índice sem a hamza ("الأسعار" → "الاسعار"), como o navegador compara.
    assert "الاسعار" in inflacao.lt.split()
    # Japonês com o sinal de sonora ("ド") não perde o sinal ao normalizar.
    assert busca.normalizar("ドル") == "ドル"
    # Árabe sem as vogais curtas, como o navegador compara.
    assert busca.normalizar("التَّضَخُّم") == "التضخم"
    assert "مؤشر أسعار المستهلك" in busca.OUTRAS_ESCRITAS["ipca"]


def test_linhas_das_tabelas_curtas_vao_ao_indice(tmp_path: Path) -> None:
    """15/11/2026: "gasolina", "aluguel" e "alimentos" não achavam a tabela do IPCA por grupo,
    e "Derivados de petróleo (diesel, gasolina)" só existia como linha de tabela."""
    painel = {"secoes": [{"id": "inflacao", "titulo": "Inflação", "arquivo": "inflacao.json"}]}
    grupos = [{"rotulo": r, "valores": [1.0]} for r in ("Alimentação e bebidas", "Transportes")]
    longa = [
        {"rotulo": f"Estado {i}", "valores": [1.0]} for i in range(busca.LINHAS_POR_TABELA + 1)
    ]
    inflacao = {
        "tabelas": [
            {"id": "ipca-grupos", "titulo": "IPCA por grupo em out/2026", "linhas": grupos},
            {"id": "longa", "titulo": "Longa", "linhas": longa},
        ]
    }
    (tmp_path / "painel.json").write_text(json.dumps(painel), encoding="utf-8")
    (tmp_path / "inflacao.json").write_text(json.dumps(inflacao), encoding="utf-8")
    itens = {i.h: i for i in busca.montar(tmp_path)}
    p = itens["#inflacao/t-ipca-grupos"].p
    assert "alimentacao e bebidas transportes" in p
    assert all(w in p for w in ("gasolina", "aluguel", "conta de luz", "alimentos"))
    assert "estado 3" not in itens["#inflacao/t-longa"].p


def test_glossario_entra_na_busca(tmp_path: Path) -> None:
    (tmp_path / "painel.json").write_text(json.dumps({"secoes": []}), encoding="utf-8")
    item = next(i for i in busca.montar(tmp_path) if i.h == "#glossario")
    assert "dicionario" in item.p and "siglas" in item.p


def test_comparador_do_salario_minimo_entra_na_busca(tmp_path: Path) -> None:
    painel = {"secoes": [{"id": "trabalho", "titulo": "Trabalho", "arquivo": "trabalho.json"}]}
    trabalho = {
        "subcategorias": [
            {"id": "renda", "titulo": "Renda", "resumo": "", "extras": ["salario-minimo"]}
        ],
        "salario_minimo": {"meses": [], "prazos": [1], "fonte": "", "nota": ""},
    }
    (tmp_path / "painel.json").write_text(json.dumps(painel), encoding="utf-8")
    (tmp_path / "trabalho.json").write_text(json.dumps(trabalho), encoding="utf-8")
    item = next(i for i in busca.montar(tmp_path) if i.t == "Salário mínimo contra a inflação")
    assert item.h == "#trabalho/renda"
    assert item.o == "Trabalho › Renda · comparador"
