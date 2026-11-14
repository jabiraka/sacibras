"""Monta todas as seções e grava os JSONs do site.

Uma seção que falha não derruba as outras: fica marcada no `painel.json`, e o JSON bom da
rodada anterior, se existir na pasta de saída, continua valendo.
"""

from __future__ import annotations

import json
import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from sacibras.schema import Cartao, EstadoFonte, ItemSecao, Painel, Secao
from sacibras.secoes import (
    atividade,
    credito,
    externo,
    fiscal,
    inflacao,
    juros,
    mercados,
    mundo,
    previsoes,
    trabalho,
)
from sacibras.secoes.base import Contexto

# A ordem em que as seções aparecem na página.
ORDEM: list[tuple[str, str, Callable[[Contexto], BaseModel]]] = [
    ("atividade", "Atividade", atividade.montar),
    ("trabalho", "Trabalho", trabalho.montar),
    ("inflacao", "Inflação", inflacao.montar),
    ("juros", "Juros e Copom", juros.montar),
    ("credito", "Crédito", credito.montar),
    ("mercados", "Mercados", mercados.montar),
    ("externo", "Setor externo", externo.montar),
    ("fiscal", "Contas públicas e dívida", fiscal.montar),
    ("mundo", "Brasil no mundo", mundo.montar),
    ("previsoes", "Previsões", previsoes.montar),
]

# Os doze cartões do topo, na ordem; cada um nasce na seção que o explica.
RESUMO = [
    "pib-tt",
    "desocupacao",
    "ipca-12m",
    "nucleos-12m",
    "selic-meta",
    "juro-real-ex-ante",
    "inclinacao",
    "ibovespa",
    "dolar",
    "dbgg",
    "primario",
    "transacoes-correntes",
]

FONTES = {
    "atividade": "IBGE (SIDRA)",
    "trabalho": "IBGE (PNAD Contínua)",
    "inflacao": "Banco Central (SGS)",
    "juros": "Banco Central (Copom e Focus)",
    "credito": "Banco Central (crédito)",
    "mercados": "IPEADATA e Banco Central (bolsa e câmbio)",
    "externo": "Banco Central (setor externo)",
    "fiscal": "Banco Central (estatísticas fiscais)",
    "mundo": "FMI (WEO) e BIS",
    "previsoes": "Banco Central (Focus)",
}


def _gravar(pasta: Path, nome: str, modelo: BaseModel) -> None:
    texto = modelo.model_dump_json()
    json.loads(texto)  # o que vai ao site tem de ser JSON válido
    (pasta / nome).write_text(texto, encoding="utf-8")


def construir(saida: Path, so: list[str] | None = None) -> Painel:
    saida.mkdir(parents=True, exist_ok=True)
    ctx = Contexto()
    itens: list[ItemSecao] = []
    fontes: list[EstadoFonte] = []
    cartoes: dict[str, Cartao] = {}
    for id, titulo, montar in ORDEM:
        arquivo = f"{id}.json"
        if so and id not in so:
            if (saida / arquivo).exists():
                itens.append(ItemSecao(id=id, titulo=titulo, arquivo=arquivo, ok=True))
                antigo = json.loads((saida / arquivo).read_text(encoding="utf-8"))
                for c in antigo.get("cartoes", []):
                    cartoes[c["id"]] = Cartao.model_validate(c)
            continue
        try:
            secao = montar(ctx)
            _gravar(saida, arquivo, secao)
            if isinstance(secao, Secao):
                cartoes.update({c.id: c for c in secao.cartoes})
            itens.append(ItemSecao(id=id, titulo=titulo, arquivo=arquivo, ok=True))
            fontes.append(EstadoFonte(fonte=FONTES[id], ok=True))
            print(f"  ok    {id}")
        except Exception as erro:
            traceback.print_exc()
            sobrou = (saida / arquivo).exists()
            itens.append(
                ItemSecao(id=id, titulo=titulo, arquivo=arquivo, ok=sobrou, erro=str(erro)[:300])
            )
            fontes.append(EstadoFonte(fonte=FONTES[id], ok=False, detalhe=str(erro)[:300]))
            print(f"  FALHA {id}: {str(erro)[:160]}")

    agora = datetime.now(UTC)
    resumo = Secao(
        id="resumo",
        titulo="Resumo",
        resumo="Os números que resumem o momento. Toque num cartão para ver a seção dele.",
        cartoes=[cartoes[c] for c in RESUMO if c in cartoes],
        gerado_em=agora,
    )
    _gravar(saida, "resumo.json", resumo)
    painel = Painel(
        gerado_em=agora,
        secoes=[ItemSecao(id="resumo", titulo="Resumo", arquivo="resumo.json", ok=True), *itens],
        fontes=fontes,
    )
    _gravar(saida, "painel.json", painel)
    return painel
