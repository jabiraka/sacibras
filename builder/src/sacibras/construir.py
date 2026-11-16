"""Monta todas as seções e grava os JSONs do site.

Uma seção que falha não derruba as outras: fica marcada no `painel.json`, e o JSON bom da
rodada anterior, se existir na pasta de saída, continua valendo. Se a seção sai mas uma fonte
dela falhou, o que faltou (cartão, gráfico, tabela, métrica) vem da rodada anterior: o valor
nunca fica em branco (Caio, 14/11/2026: *"se o agendamento falhar, pode manter os dados = ao
dia anterior, nunca deixe em branco os valores"*). No Actions, `sacibras anterior` traz os
JSONs do site no ar para a pasta antes do build.
"""

from __future__ import annotations

import json
import re
import traceback
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from sacibras import licencas, organizacao, rede, saiu
from sacibras.catalogo import SGS
from sacibras.schema import (
    AoVivo,
    Cartao,
    Divulgado,
    EstadoFonte,
    Grafico,
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
    impostos,
    inflacao,
    juros,
    mercados,
    mundo,
    pobreza,
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
    ("impostos", "Impostos", impostos.montar),
    ("estados", "Estados", estados.montar),
    ("demografia", "Demografia", demografia.montar),
    ("pobreza", "Pobreza e condições de vida", pobreza.montar),
    ("mundo", "Brasil no mundo", mundo.montar),
    ("previsoes", "Previsões", previsoes.montar),
    ("riscos", "Riscos", riscos.montar),
]

# Os números da página inicial, na ordem; cada um nasce no assunto que o explica.
# Decisão do Caio (14/11/2026): só o essencial na entrada, o resto abre no clique. Em
# 15/11/2026 a entrada ganhou gráficos (*"coloque também alguns gráficos que achar mais
# importante pra entender o Brasil. Pode eliminar alguns cartões"*): saíram o dólar e a
# dívida bruta, que agora está no gráfico.
RESUMO = ["pib-4t", "ipca-12m", "selic-meta", "desocupacao"]

# Os gráficos da página inicial, na ordem: (assunto, id do gráfico). Crescimento, inflação
# contra a meta, o juro real e a dívida: o que mais explica o Brasil de hoje.
RESUMO_GRAFICOS = [
    ("inflacao", "ipca-12m"),
    ("atividade", "pib-trimestral"),
    ("juros", "juro-real"),
    ("fiscal", "divida"),
]

# Onde o navegador busca o ponto mais novo de cada número da entrada (SGS e SIDRA têm CORS
# aberto, conferido em 14/11/2026). A Selic meta fica de fora: o SGS a preenche dia a dia até
# a próxima reunião, então "data mais nova" não quer dizer decisão nova.
AO_VIVO = {
    "pib-4t": AoVivo(tipo="sidra", caminho="t/5932/n1/all/v/6562/p/last%201/c11255/90707"),
    "ipca-12m": AoVivo(tipo="sgs", codigo=SGS["IPCA_12M"].codigo),
    "desocupacao": AoVivo(tipo="sgs", codigo=SGS["DESOCUPACAO"].codigo),
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
    "mercados": "IPEADATA, Banco Central, Tesouro Nacional e FMI (bolsa, câmbio, títulos e ouro)",
    "externo": "Banco Central (setor externo)",
    "fiscal": "Banco Central (estatísticas fiscais) e Tesouro Nacional (RTN)",
    "impostos": "Receita Federal (arrecadação e gastos tributários), OCDE e FMI (impostos)",
    "estados": (
        "Tesouro Nacional (SICONFI e CAPAG), IBGE (Contas Regionais, PNAD Contínua e IPCA), "
        "Banco Central (IBC-R e crédito por UF) e Comex Stat"
    ),
    "mundo": "FMI (WEO), BIS, OCDE e Tesouro Nacional",
    "previsoes": "Banco Central (Focus)",
    "riscos": "Banco Central, Tesouro Nacional, IBGE, IPEADATA e ONS (riscos)",
    "demografia": "IBGE (Projeções da População e PNAD) e Tesouro Nacional (RTN)",
    "pobreza": "IBGE (PNAD Contínua anual), Ipea, Receita Federal (IRPF), FAO e Banco Mundial",
}


DETALHE_MAXIMO = 60
"""O texto embaixo do número: só o essencial (Caio, 14/11/2026: "se for apresentar o
resultado, escreva só o essencial, sem muitos detalhes e contextos"). O resto vai na nota do
gráfico ou no glossário."""


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


def _juntar[T](novos: Sequence[T], antigos: Sequence[T], chave: Callable[[T], str]) -> list[T]:
    """Os novos, mais os antigos que faltaram, cada um logo depois do vizinho que o precedia."""
    juntos = list(novos)
    tem = {chave(x) for x in juntos}
    for i, velho in enumerate(antigos):
        if chave(velho) in tem:
            continue
        lugar = 0
        for anterior in reversed(antigos[:i]):
            achou = [j for j, x in enumerate(juntos) if chave(x) == chave(anterior)]
            if achou:
                lugar = achou[0] + 1
                break
        juntos.insert(lugar, velho)
        tem.add(chave(velho))
    return juntos


def completar(secao: BaseModel, caminho: Path) -> list[str]:
    """Põe na seção o que a rodada anterior tinha e esta não trouxe; devolve os ids.

    Chamado só quando uma fonte da seção falhou. Num `Secao`, só volta o que as partes de
    `organizacao.PARTES` listam; em Estados e Brasil no mundo, as métricas. Cada peça leva a
    própria data de referência, então a tela diz de quando é o número."""
    if not caminho.exists():
        return []
    try:
        antigo = type(secao).model_validate_json(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # JSON de outra versão do contrato: não dá para aproveitar
        return []
    mantidos: list[str] = []

    def juntar(campo: str, aceitos: set[str] | None = None) -> None:
        novos = getattr(secao, campo)
        velhos = [x for x in getattr(antigo, campo) if aceitos is None or x.id in aceitos]
        ids_novos = {x.id for x in novos}
        juntos = _juntar(novos, velhos, lambda x: x.id)
        mantidos.extend(x.id for x in juntos if x.id not in ids_novos)
        setattr(secao, campo, juntos)

    if isinstance(secao, Secao) and isinstance(antigo, Secao):
        esperados = organizacao.esperados(secao.id)
        for campo in ("cartoes", "graficos", "tabelas"):
            juntar(campo, esperados[campo])
        for campo in ("simulador", "simulador_selic", "simulador_reforma"):
            if getattr(secao, campo) is None and getattr(antigo, campo) is not None:
                setattr(secao, campo, getattr(antigo, campo))
                mantidos.append(campo)
        if not secao.alertas and antigo.alertas:
            secao.alertas = antigo.alertas
            mantidos.append("alertas")
    elif hasattr(secao, "metricas"):
        juntar("metricas")
    return mantidos


def construir(saida: Path, so: list[str] | None = None) -> Painel:
    saida.mkdir(parents=True, exist_ok=True)
    ctx = Contexto()
    itens: list[ItemSecao] = []
    fontes: list[EstadoFonte] = []
    cartoes: dict[str, Cartao] = {}
    graficos: dict[tuple[str, str], Grafico] = {}

    def guardar_graficos(id: str, lista: Sequence[Grafico | dict[str, object]]) -> None:
        """Os gráficos do assunto que a página inicial mostra, marcados com o assunto."""
        for g in lista:
            modelo = g if isinstance(g, Grafico) else Grafico.model_validate(g)
            if (id, modelo.id) in RESUMO_GRAFICOS:
                graficos[(id, modelo.id)] = modelo.model_copy(update={"secao": id})

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
                guardar_graficos(id, antigo.get("graficos", []))
            continue
        try:
            falhas_antes = len(rede.FALHAS)
            secao = montar(ctx)
            mantidos = completar(secao, saida / arquivo) if len(rede.FALHAS) > falhas_antes else []
            if mantidos:
                print(f"  aviso: {id}: da rodada anterior (fonte falhou): {', '.join(mantidos)}")
            tirados = licencas.tirar_o_que_nao_pode(secao)
            if tirados:
                print(f"  aviso: {id}: fora da tela pela licença: {', '.join(tirados)}")
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
                for c in secao.cartoes:
                    if len(c.detalhe) > DETALHE_MAXIMO:
                        print(f"  aviso: {id}: detalhe longo em {c.id} ({len(c.detalhe)} letras)")
            _gravar(saida, arquivo, secao)
            extra = ctx.memo.pop(f"{id}_paises", None)  # o arquivo à parte da seção, se houver
            if extra is not None:
                _gravar(saida, getattr(secao, "arquivo_paises", ""), extra)
            if isinstance(secao, Secao):
                cartoes.update({c.id: c for c in secao.cartoes})
                guardar_graficos(id, secao.graficos)
            itens.append(
                ItemSecao(
                    id=id,
                    titulo=titulo,
                    arquivo=arquivo,
                    resumo=manchete(getattr(secao, "resumo", "")),
                    subcategorias=_partes(secao),
                    ok=True,
                    mantidos=mantidos,
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
                    guardar_graficos(id, antigo.get("graficos", []))
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

    saiu_antes: list[Divulgado] = []
    try:
        antigo = json.loads((saida / "resumo.json").read_text(encoding="utf-8"))
        saiu_antes = [Divulgado.model_validate(d) for d in antigo.get("saiu", [])]
    except (OSError, ValueError):
        pass
    agora = datetime.now(UTC)
    resumo = Secao(
        id="resumo",
        titulo="Resumo",
        resumo="Os números e os gráficos da página inicial.",
        cartoes=[
            cartoes[c].model_copy(update={"ao_vivo": AO_VIVO.get(c)})
            for c in RESUMO
            if c in cartoes
        ],
        graficos=[graficos[g] for g in RESUMO_GRAFICOS if g in graficos],
        saiu=saiu.montar(ctx, saiu_antes),
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
