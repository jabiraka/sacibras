from sacibras import links


def urls(fonte: str) -> list[str]:
    return [e.url for e in links.enderecos(fonte)]


def test_sgs_um_endereco_por_codigo() -> None:
    assert urls("Banco Central, SGS 4189, 4390 e 13521") == [
        f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{n}/dados?formato=json"
        for n in (4189, 4390, 13521)
    ]


def test_sidra_so_pega_a_tabela_e_nao_a_variavel() -> None:
    achados = urls("IBGE, PNAD Contínua, trimestre móvel (SIDRA 6381, variável 4099)")
    assert achados == ["https://sidra.ibge.gov.br/tabela/6381"]
    assert urls("IBGE, PNAD Contínua trimestral (SIDRA, tabela 4099)") == [
        "https://sidra.ibge.gov.br/tabela/4099"
    ]
    assert len(urls("IBGE, SIDRA 8888, 8880, 8881 e 5906 (volume)")) == 4


def test_sem_repetir_e_com_varias_instituicoes() -> None:
    achados = urls("Banco Central, SGS 13522; IBGE, SIDRA tabela 7060 (variável 2265); Focus")
    assert "https://www.bcb.gov.br/publicacoes/focus" in achados
    assert len(achados) == len(set(achados)) == 3


def test_instituicao_sem_regra_propria_cai_na_pagina_geral() -> None:
    assert urls("IBGE, Pesquisa qualquer") == [
        "https://www.ibge.gov.br/estatisticas/todos-os-temas.html"
    ]
    assert links.sem_endereco("Fulano, estudo de 2020")
    assert not links.sem_endereco("")


def test_regras_compilam_e_os_enderecos_sao_https_ou_http() -> None:
    import re

    for r in links.REGRAS + links._GERAIS:
        re.compile(r.padrao)
        assert r.url.startswith(("https://", "http://"))
        assert ("{n}" in r.url) == r.por_numero


def test_projeto_da_ldo_2027_tem_endereco() -> None:
    from sacibras import relatorios

    assert urls(relatorios.FONTE_PLDO_2027) == [
        "https://www.congressonacional.leg.br/materias/materias-bicamerais/-/ver/pln-2-2026"
    ]
