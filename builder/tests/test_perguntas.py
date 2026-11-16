"""As perguntas: só apontam para o que os assuntos têm, e cabem no orçamento de atenção."""

from datetime import date

from sacibras import organizacao, perguntas
from sacibras.schema import Cartao, Grafico


def _cartao(id: str) -> Cartao:
    return Cartao(
        id=id,
        rotulo=id,
        valor=1.0,
        unidade="%",
        referencia=date(2026, 10, 1),
        periodicidade="M",
        fonte="teste",
    )


def _grafico(id: str) -> Grafico:
    return Grafico(id=id, titulo=id, series=[], unidade="%", periodicidade="M", fonte="teste")


def test_cada_peca_citada_mora_numa_parte_do_assunto() -> None:
    """Senão a explicação some calada. O "*" do Focus (o ano no id) fica de fora."""
    for d in perguntas.PERGUNTAS:
        refs = [(r, "cartoes") for r in d.numeros]
        for b in d.blocos:
            refs += [(r, "cartoes") for r in b.numeros]
            if b.grafico:
                refs.append((b.grafico, "graficos"))
            if b.tabela:
                refs.append((b.tabela, "tabelas"))
        for (assunto, id), tipo in refs:
            if not id.endswith("*"):
                assert id in organizacao.esperados(assunto)[tipo], (d.id, assunto, id)


def test_o_orcamento_de_atencao() -> None:
    ids = [d.id for d in perguntas.PERGUNTAS]
    assert len(ids) == len(set(ids)) <= 8
    for d in perguntas.PERGUNTAS:
        assert d.titulo.endswith("?")
        assert len(d.numeros) <= perguntas.MAXIMO_DE_NUMEROS, d.id
        assert 3 <= len(d.blocos) <= perguntas.MAXIMO_DE_BLOCOS, d.id
        assert len(d.resposta) <= 260, (d.id, len(d.resposta))
        assert 0 < len(d.conclusao) <= 300, (d.id, len(d.conclusao))
        for b in d.blocos:
            assert len(b.numeros) <= 2 and len(b.texto) <= 170, (d.id, b.titulo)
            assert b.grafico or b.numeros, (d.id, b.titulo)


def test_o_que_falta_na_rodada_nao_aparece() -> None:
    cartoes = {("juros", "selic-meta"): _cartao("selic-meta")}
    graficos = {("inflacao", "ipca-12m"): _grafico("ipca-12m")}
    prontas = perguntas.montar(cartoes, graficos, {"inflacao": "Inflação"})
    juro = next(p for p in prontas if p.id == "juro-alto")
    assert [c.id for c in juro.numeros] == ["selic-meta"]
    # O número da resposta não se repete dentro da explicação.
    cartoes[("inflacao", "ipca-12m")] = _cartao("ipca-12m")
    cartoes[("inflacao", "focus-ipca")] = _cartao("focus-ipca")
    de_novo = next(p for p in perguntas.montar(cartoes, graficos, {}) if p.id == "juro-alto")
    assert [c.id for c in de_novo.blocos[0].numeros] == ["focus-ipca"]
    assert [b.titulo for b in juro.blocos] == ["A inflação está acima da meta"]
    bloco = juro.blocos[0]
    assert (bloco.elo, bloco.assunto_titulo) == ("#inflacao/g-ipca-12m", "Inflação")
    assert bloco.grafico is not None and bloco.grafico.secao == "inflacao"
    # Pergunta sem nenhuma peça não vai ao ar.
    assert all(p.blocos for p in prontas)
    assert perguntas.montar({}, {}, {}) == []


def test_o_asterisco_pega_o_cartao_do_ano() -> None:
    cartoes = {("previsoes", "focus-pib-2027"): _cartao("focus-pib-2027")}
    achado = perguntas._achar(cartoes, ("previsoes", "focus-pib-*"))
    assert achado is not None and achado.id == "focus-pib-2027"


def test_a_tabela_da_explicacao_vem_dos_dados() -> None:
    from sacibras.schema import Tabela

    tabela = Tabela(id="primario-conforme-o-juro", titulo="t", colunas=[], linhas=[], fonte="f")
    prontas = perguntas.montar(
        {("riscos", "primario-estabiliza"): _cartao("primario-estabiliza")},
        {},
        {},
        {("riscos", "primario-conforme-o-juro"): tabela},
    )
    divida = next(p for p in prontas if p.id == "divida")
    assert divida.blocos[0].tabela == tabela
    assert divida.conclusao.startswith("A dívida é em reais")
