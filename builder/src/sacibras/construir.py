"""Monta todas as seções e grava os JSONs do site.

Uma seção que falha não derruba as outras: fica marcada no `painel.json`, e o JSON bom da
rodada anterior, se existir na pasta de saída, continua valendo.
"""

from __future__ import annotations

import json
import re
import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from sacibras import organizacao
from sacibras.catalogo import SGS
from sacibras.schema import (
    AoVivo,
    Cartao,
    EstadoFonte,
    ItemSecao,
    ItemSubcategoria,
    Painel,
    Secao,
)
from sacibras.secoes import (
    atividade,
    credito,
    demografia,
    estados,
    externo,
    fiscal,
    inflacao,
    juros,
    mercados,
    mundo,
    previsoes,
    riscos,
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
    ("estados", "Estados", estados.montar),
    ("demografia", "Demografia", demografia.montar),
    ("mundo", "Brasil no mundo", mundo.montar),
    ("previsoes", "Previsões", previsoes.montar),
    ("riscos", "Riscos", riscos.montar),
]

# Os seis números da página inicial, na ordem; cada um nasce no assunto que o explica.
# Decisão do Caio (14/11/2026): só o essencial na entrada, o resto abre no clique.
RESUMO = ["pib-4t", "ipca-12m", "selic-meta", "desocupacao", "dolar", "dbgg"]

# Onde o navegador busca o ponto mais novo de cada número da entrada (SGS e SIDRA têm CORS
# aberto, conferido em 14/11/2026). A Selic meta fica de fora: o SGS a preenche dia a dia até
# a próxima reunião, então "data mais nova" não quer dizer decisão nova.
AO_VIVO = {
    "pib-4t": AoVivo(tipo="sidra", caminho="t/5932/n1/all/v/6562/p/last%201/c11255/90707"),
    "ipca-12m": AoVivo(tipo="sgs", codigo=SGS["IPCA_12M"].codigo),
    "desocupacao": AoVivo(tipo="sgs", codigo=SGS["DESOCUPACAO"].codigo),
    "dolar": AoVivo(tipo="sgs", codigo=SGS["DOLAR"].codigo),
    "dbgg": AoVivo(tipo="sgs", codigo=SGS["DBGG"].codigo),
}


def manchete(texto: str) -> str:
    """A primeira frase do resumo de um assunto: o que cabe no cartão da página inicial."""
    corte = re.search(r"[.;](\s|$)", texto)
    frase = texto[: corte.start()] if corte else texto
    return frase.strip() + "." if frase.strip() else ""


FONTES = {
    "atividade": "IBGE (SIDRA)",
    "trabalho": "IBGE (PNAD Contínua)",
    "inflacao": "Banco Central (SGS)",
    "juros": "Banco Central (Copom e Focus)",
    "credito": "Banco Central (crédito)",
    "mercados": "IPEADATA e Banco Central (bolsa e câmbio)",
    "externo": "Banco Central (setor externo)",
    "fiscal": "Banco Central (estatísticas fiscais) e Tesouro Nacional (RTN)",
    "estados": "Tesouro Nacional (SICONFI) e IBGE (PNAD Contínua)",
    "mundo": "FMI (WEO) e BIS",
    "previsoes": "Banco Central (Focus)",
    "riscos": "Banco Central, Tesouro Nacional, IBGE, IPEADATA e ONS (riscos)",
    "demografia": "IBGE (Projeções da População e PNAD) e Tesouro Nacional (RTN)",
}


def _partes(dados: object) -> list[ItemSubcategoria]:
    """As subcategorias de uma seção (modelo ou JSON antigo), só id e título, para o menu."""
    lista = (
        dados.get("subcategorias", [])
        if isinstance(dados, dict)
        else getattr(dados, "subcategorias", [])
    )
    return [
        ItemSubcategoria(id=s["id"], titulo=s["titulo"])
        if isinstance(s, dict)
        else ItemSubcategoria(id=s.id, titulo=s.titulo)
        for s in lista
    ]


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
                antigo = json.loads((saida / arquivo).read_text(encoding="utf-8"))
                itens.append(
                    ItemSecao(
                        id=id,
                        titulo=titulo,
                        arquivo=arquivo,
                        resumo=manchete(antigo.get("resumo", "")),
                        subcategorias=_partes(antigo),
                        ok=True,
                    )
                )
                fontes.append(EstadoFonte(fonte=FONTES[id], ok=True))
                for c in antigo.get("cartoes", []):
                    cartoes[c["id"]] = Cartao.model_validate(c)
            continue
        try:
            secao = montar(ctx)
            contas = ctx.memo.pop(f"{id}_contas", None)  # as contas de cada estado, à parte
            if contas is not None:
                try:
                    _gravar(saida, getattr(secao, "arquivo_contas", ""), contas)
                except Exception as erro:  # sem o arquivo, a seção sai sem apontar para ele
                    setattr(secao, "arquivo_contas", "")  # noqa: B010
                    print(f"  aviso: {id}: contas não gravadas ({erro})")
            if isinstance(secao, Secao):
                sem_lugar = organizacao.aplicar(secao)
                if sem_lugar:
                    print(f"  aviso: {id}: sem parte em organizacao.py: {', '.join(sem_lugar)}")
            _gravar(saida, arquivo, secao)
            extra = ctx.memo.pop(f"{id}_paises", None)  # o arquivo à parte da seção, se houver
            if extra is not None:
                _gravar(saida, getattr(secao, "arquivo_paises", ""), extra)
            if isinstance(secao, Secao):
                cartoes.update({c.id: c for c in secao.cartoes})
            itens.append(
                ItemSecao(
                    id=id,
                    titulo=titulo,
                    arquivo=arquivo,
                    resumo=manchete(getattr(secao, "resumo", "")),
                    subcategorias=_partes(secao),
                    ok=True,
                )
            )
            fontes.append(EstadoFonte(fonte=FONTES[id], ok=True))
            print(f"  ok    {id}")
        except Exception as erro:
            traceback.print_exc()
            sobrou = (saida / arquivo).exists()
            partes: list[ItemSubcategoria] = []
            if sobrou:
                # O JSON bom da rodada anterior continua valendo, e os números dele também
                # entram na página inicial.
                try:
                    antigo = json.loads((saida / arquivo).read_text(encoding="utf-8"))
                    for c in antigo.get("cartoes", []):
                        cartoes[c["id"]] = Cartao.model_validate(c)
                    partes = _partes(antigo)
                except (OSError, ValueError):
                    pass
            itens.append(
                ItemSecao(
                    id=id,
                    titulo=titulo,
                    arquivo=arquivo,
                    subcategorias=partes,
                    ok=sobrou,
                    erro=str(erro)[:300],
                )
            )
            fontes.append(EstadoFonte(fonte=FONTES[id], ok=False, detalhe=str(erro)[:300]))
            print(f"  FALHA {id}: {str(erro)[:160]}")

    agora = datetime.now(UTC)
    resumo = Secao(
        id="resumo",
        titulo="Resumo",
        resumo="Os seis números da página inicial.",
        cartoes=[
            cartoes[c].model_copy(update={"ao_vivo": AO_VIVO.get(c)})
            for c in RESUMO
            if c in cartoes
        ],
        gerado_em=agora,
    )
    _gravar(saida, "resumo.json", resumo)
    painel = Painel(
        gerado_em=agora,
        secoes=[ItemSecao(id="resumo", titulo="Resumo", arquivo="resumo.json", ok=True), *itens],
        fontes=fontes,
        categorias=organizacao.CATEGORIAS,
    )
    _gravar(saida, "painel.json", painel)
    return painel
