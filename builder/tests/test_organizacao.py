"""Categorias, subcategorias e o que a busca diz sobre onde cada coisa mora."""

import json
import re
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from sacibras import busca, construir, leis, organizacao
from sacibras.schema import Cartao, Grafico, Secao, Serie, SimuladorDivida, Tabela
from sacibras.secoes import fiscal

AGORA = datetime(2026, 11, 14, tzinfo=UTC)


def test_cada_assunto_esta_em_uma_categoria_so() -> None:
    nas_categorias = [s for c in organizacao.CATEGORIAS for s in c.secoes]
    assert sorted(nas_categorias) == sorted(id for id, *_ in construir.ORDEM)


def test_partes_com_id_unico_que_nao_parece_peca_e_sem_peca_repetida() -> None:
    for secao, partes in organizacao.PARTES.items():
        ids = [p.id for p in partes]
        assert len(ids) == len(set(ids)), secao
        assert all(not re.match(r"^(c|g|t|m|p|uf)-", i) for i in ids), secao
        for tipo in ("cartoes", "graficos", "tabelas"):
            todos = [i for p in partes for i in getattr(p, tipo)]
            assert len(todos) == len(set(todos)), (secao, tipo)


def _cartao(id: str) -> Cartao:
    return Cartao(
        id=id,
        rotulo=id,
        valor=1.0,
        unidade="%",
        referencia=date(2026, 10, 1),
        periodicidade="M",
        fonte="x",
    )


def _grafico(id: str) -> Grafico:
    return Grafico(
        id=id,
        titulo=id,
        unidade="%",
        periodicidade="M",
        series=[Serie(id="s", nome="s", pontos=[(date(2026, 1, 1), 1.0)])],
        fonte="x",
    )


def test_aplicar_poe_cada_peca_numa_parte_e_tira_o_resto_da_tela() -> None:
    secao = Secao(
        id="inflacao",
        titulo="Inflação",
        cartoes=[_cartao("ipca-12m"), _cartao("nucleos-12m"), _cartao("novo")],
        graficos=[_grafico("ipca-12m")],
        tabelas=[Tabela(id="ipca-grupos", titulo="t", colunas=[], linhas=[], fonte="x")],
        gerado_em=AGORA,
    )
    sem_lugar = organizacao.aplicar(secao)
    partes = {s.id: s for s in secao.subcategorias}
    assert list(partes) == ["ipca", "nucleos", "grupos"]  # "outros-indices" vazia some
    assert partes["ipca"].cartoes == ["ipca-12m"] and partes["ipca"].graficos == ["ipca-12m"]
    assert partes["grupos"].tabelas == ["ipca-grupos"] and partes["grupos"].cartoes == []
    # O que não tem parte sai da tela, e o builder avisa.
    assert sem_lugar == ["c-novo"]
    assert [c.id for c in secao.cartoes] == ["ipca-12m", "nucleos-12m"]


def test_aplicar_leva_o_simulador_para_a_parte_dele() -> None:
    simulador = SimuladorDivida(
        ano_inicial=2026,
        divida_inicial=80.0,
        anos=[2027],
        juro=[10.0],
        crescimento=[2.0],
        inflacao=[4.0],
        primario=[0.0],
        focus_divida=[None],
        realizado=[],
        fonte="x",
        nota="",
    )
    secao = Secao(id="previsoes", titulo="P", simulador=simulador, gerado_em=AGORA)
    assert organizacao.aplicar(secao) == []
    assert [(s.id, s.extras) for s in secao.subcategorias] == [("simulador", ["simulador"])]


def test_assunto_sem_partes_fica_inteiro() -> None:
    secao = Secao(id="nao-listado", titulo="X", cartoes=[_cartao("a")], gerado_em=AGORA)
    assert organizacao.aplicar(secao) == [] and secao.subcategorias == []


def test_busca_ganha_as_partes_e_diz_onde_a_peca_mora(tmp_path: Path) -> None:
    painel = {"secoes": [{"id": "inflacao", "titulo": "Inflação", "arquivo": "inflacao.json"}]}
    inflacao = {
        "cartoes": [{"id": "nucleos-12m", "rotulo": "Média dos núcleos", "detalhe": ""}],
        "graficos": [],
        "tabelas": [],
        "subcategorias": [
            {
                "id": "nucleos",
                "titulo": "Núcleos e o ritmo",
                "resumo": "sem os voláteis",
                "cartoes": ["nucleos-12m"],
            }
        ],
    }
    for nome, dados in [("painel", painel), ("inflacao", inflacao)]:
        (tmp_path / f"{nome}.json").write_text(json.dumps(dados), encoding="utf-8")
    busca.gravar(tmp_path)
    itens = {i["h"]: i for i in json.loads((tmp_path / "busca.json").read_text("utf-8"))}
    assert itens["#inflacao/nucleos"]["o"] == "Inflação · parte"
    assert itens["#inflacao/c-nucleos-12m"]["o"] == "Inflação › Núcleos e o ritmo · número"


class _Ctx:
    """O mínimo do Contexto para a meta: a série mensal do BC, sem rede."""

    hoje = date(2026, 11, 14)

    def sgs(self, chave: str, anos: int = 16) -> list[tuple[date, float]]:
        assert chave == "NFSP_PRIMARIO_GC_MES"
        # NFSP: positivo é déficit. 24 meses de déficit de R$ 5 bi por mês.
        return [(date(2024 + (m // 12), m % 12 + 1, 1), 5000.0) for m in range(24)]

    def fonte_sgs(self, *chaves: str) -> str:
        return "Banco Central, SGS 4639"


def test_meta_do_primario_em_reais_com_o_desconto_ao_lado() -> None:
    cartao, grafico, tabela = fiscal.meta_do_primario(_Ctx())  # type: ignore[arg-type]
    assert cartao.valor == -60.0  # 12 × R$ 5 bi de déficit
    assert cartao.unidade == "R$ bilhões"
    assert cartao.meta is not None
    assert (round(cartao.meta.inferior, 1), round(cartao.meta.superior, 1)) == (0.0, 68.5)
    assert "R$ 77,0 bi" in cartao.detalhe
    assert grafico.faixa is not None and len(grafico.faixa.pontos) == 12
    ultima = leis.AVALIACOES_2026[-1]
    assert tabela.linhas[2].valores[-1] == round(ultima.resultado + ultima.deducao, 1) == -12.3
    assert "abaixo do piso" in tabela.nota


def test_partes_dos_estados_sem_a_ficha_quando_nao_ha_contas() -> None:
    com = [p.id for p in organizacao.partes_dos_estados(True)]
    sem = [p.id for p in organizacao.partes_dos_estados(False)]
    assert com == ["mapa", "estado", "limites", "duas-metricas", "tabela"]
    assert "estado" not in sem
    assert all(not re.match(r"^(c|g|t|m|p|uf)-", i) for i in com)


def test_a_pagina_inicial_so_aponta_para_pecas_que_existem() -> None:
    """Os números e gráficos da entrada moram numa parte do assunto (senão somem calados)."""
    cartoes = {c for s in organizacao.PARTES for c in organizacao.esperados(s)["cartoes"]}
    assert set(construir.RESUMO) <= cartoes


def test_o_orcamento_de_atencao_das_partes() -> None:
    for assunto, partes in organizacao.PARTES.items():
        assert len(partes) <= organizacao.MAXIMO_DE_PARTES, assunto
        for p in partes:
            assert len(p.cartoes) <= organizacao.MAXIMO_DE_CARTOES, (assunto, p.id)
            assert len(p.graficos) <= organizacao.MAXIMO_DE_GRAFICOS, (assunto, p.id)


def test_os_assuntos_juntos_levam_as_pecas_das_secoes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Trabalho e renda = trabalho + pobreza; se uma falha, a outra sai e a falha é anotada."""
    from sacibras import rede
    from sacibras.secoes import juntos
    from sacibras.secoes.base import Contexto

    def secao(id: str, cartao: str) -> Secao:
        return Secao(
            id=id, titulo=id, resumo=f"Resumo de {id}.", cartoes=[_cartao(cartao)], gerado_em=AGORA
        )

    monkeypatch.setattr(
        juntos.secao_trabalho, "montar", lambda ctx: secao("trabalho", "desocupacao")
    )
    monkeypatch.setattr(juntos.pobreza, "montar", lambda ctx: secao("pobreza", "gini"))
    ctx = Contexto()
    junta = juntos.trabalho(ctx)
    assert (junta.id, junta.titulo) == ("trabalho", "Trabalho e renda")
    assert [(c.id, c.secao) for c in junta.cartoes] == [
        ("desocupacao", "trabalho"),
        ("gini", "trabalho"),
    ]
    assert junta.resumo == "Resumo de trabalho. Resumo de pobreza."
    assert organizacao.aplicar(junta) == []

    def falha(ctx: Contexto) -> Secao:
        raise OSError("fora do ar")

    monkeypatch.setattr(juntos.pobreza, "montar", falha)
    antes = len(rede.FALHAS)
    so_trabalho = juntos.trabalho(Contexto())
    assert [c.id for c in so_trabalho.cartoes] == ["desocupacao"] and len(rede.FALHAS) == antes + 1
    del rede.FALHAS[antes:]
    monkeypatch.setattr(juntos.secao_trabalho, "montar", falha)
    with pytest.raises(RuntimeError):
        juntos.trabalho(Contexto())
    del rede.FALHAS[antes:]


def test_endereco_antigo_aponta_para_assunto_que_existe() -> None:
    from sacibras.secoes import juntos

    assuntos = {id for id, _, _ in construir.ORDEM}
    assert set(juntos.ANTIGOS.values()) <= assuntos and not set(juntos.ANTIGOS) & assuntos
    assert {s for c in organizacao.CATEGORIAS for s in c.secoes} == assuntos


def test_juntos_apontam_para_peca_da_parte_e_nao_repetem() -> None:
    """O principal está na parte; o de trás não está em parte nenhuma nem atrás de outro."""
    for secao, partes in organizacao.PARTES.items():
        for tipo, campo in (("graficos", "juntos"), ("tabelas", "tabelas_juntas")):
            nas_partes = {i for p in partes for i in getattr(p, tipo)}
            atras = [i for p in partes for v in getattr(p, campo).values() for i in v]
            assert len(atras) == len(set(atras)), (secao, tipo)
            for p in partes:
                for principal, outros in getattr(p, campo).items():
                    assert principal in getattr(p, tipo), (secao, principal)
                    assert not set(outros) & nas_partes, (secao, principal)


def test_aplicar_poe_os_parecidos_atras_da_lista(monkeypatch: pytest.MonkeyPatch) -> None:
    parte = organizacao.Parte(
        "ipca",
        "IPCA",
        "r",
        graficos=["ipca-12m"],
        tabelas=["t1"],
        juntos={"ipca-12m": ["ipca-mensal", "nao-veio"]},
        tabelas_juntas={"t1": ["t2"]},
        rotulos={"ipca-12m": "12 meses", "ipca-mensal": "No mês"},
    )
    monkeypatch.setitem(organizacao.PARTES, "inflacao", [parte])

    def tabela(id: str) -> Tabela:
        return Tabela(id=id, titulo=id, colunas=[], linhas=[], fonte="x")

    secao = Secao(
        id="inflacao",
        titulo="Inflação",
        graficos=[_grafico("ipca-12m"), _grafico("ipca-mensal"), _grafico("solto")],
        tabelas=[tabela("t1"), tabela("t2")],
        gerado_em=AGORA,
    )
    sem_lugar = organizacao.aplicar(secao)
    assert sem_lugar == ["g-solto"]  # o de trás não conta como fora da tela
    [g] = secao.graficos
    assert (g.id, g.rotulo_opcao) == ("ipca-12m", "12 meses")
    assert [(a.id, a.rotulo_opcao) for a in g.alternativas] == [("ipca-mensal", "No mês")]
    [t] = secao.tabelas
    assert [a.id for a in t.alternativas] == ["t2"]
    assert secao.subcategorias[0].graficos == ["ipca-12m"]


def test_agrupar_aponta_para_partes_que_existem() -> None:
    for assunto, por_parte in organizacao.AGRUPAR.items():
        ids = {p.id for p in organizacao.PARTES[assunto]}
        assert set(por_parte) <= ids, assunto
        for a in por_parte.values():
            nomeados = {*a.graficos, *a.tabelas, *(i for v in a.graficos.values() for i in v)}
            nomeados |= {i for v in a.tabelas.values() for i in v}
            assert set(a.rotulos) <= nomeados, (assunto, set(a.rotulos) - nomeados)
