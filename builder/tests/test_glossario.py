"""O glossário e as explicações do painel de alerta: nada sem texto, nada repetido."""

import re

from sacibras import alertas, glossario

# Os indicadores do painel de alerta (secoes/riscos.py). Indicador novo entra aqui e ganha a
# explicação em alertas.EXPLICACOES.
INDICADORES = {
    *("dbgg", "primario", "juros", "nominal", "juro-menos-crescimento", "primario-que-falta"),
    *("divida-selic", "prazo-da-divida", "reservas-cobertura", "reservas-importacoes"),
    *("conta-corrente", "cobertura-idp", "divida-externa-liquida", "divida-cambial"),
    *("swaps-cambiais", "ipca", "nucleos", "difusao", "inadimplencia", "inadimplencia-pf"),
    *("inadimplencia-pj", "atrasos", "spread", "comprometimento", "endividamento", "basileia"),
    *("vol-dolar", "deficit-inss", "beneficios-inss"),
    *("reservatorios", "expectativa-12m", "implicita-longa", "hiato-credito", "liquidez"),
    *("liquidez-lcr", "juros-sobre-receita", "vence-em-12-meses"),
}


def test_cada_indicador_do_painel_tem_explicacao() -> None:
    assert set(alertas.EXPLICACOES) == INDICADORES
    for id, e in alertas.EXPLICACOES.items():
        for campo in (e.significa, e.por_que, e.pode_levar):
            assert campo.strip().endswith("."), id


def test_termos_sem_id_nem_forma_repetidos() -> None:
    ids = [t.id for t in glossario.TERMOS]
    assert len(ids) == len(set(ids))
    vistas: dict[str, str] = {}
    for t in glossario.TERMOS:
        assert t.formas and t.definicao.endswith("."), t.id
        for f in t.formas:
            chave = f if len(re.findall(r"[A-ZÀ-Ý]", f)) >= 2 else f.lower()
            assert chave not in vistas, f"{f}: em {vistas.get(chave)} e {t.id}"
            vistas[chave] = t.id


def test_definicoes_curtas() -> None:
    for t in glossario.TERMOS:
        assert len(t.definicao) <= 420, t.id
        assert t.elo == "" or t.elo.startswith("#"), t.id
