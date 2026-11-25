"""O que o painel mostra de um projeto que ainda não é lei, e o aviso quando ele anda.

Caio, 25/11/2026, sobre o projeto da LDO 2027: *"Pode já colocar, dizendo que ainda não virou
lei, isso vai ser sancionado logo, a gente vai ter que monitorar se algo muda até a
sanção"*. Cada projeto aqui guarda o que foi visto na última leitura (a situação no Senado e
o informe mais recente). O `sacibras tramitacao` pergunta de novo aos dados abertos do Senado
(que servem também as matérias do Congresso, como os PLN) e lista o que mudou; o workflow
"Prazos de releitura" abre a issue `tramitação` com a lista. Ao reler o projeto, atualize o
número em `relatorios.py` e aqui o que foi visto; sancionada a lei, tire o projeto da lista.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sacibras import rede

SENADO = "https://legis.senado.leg.br/dadosabertos/materia/movimentacoes/{codigo}"


@dataclass(frozen=True)
class Projeto:
    nome: str
    codigo: int
    """O código da matéria nos dados abertos do Senado."""
    onde: str
    """O número no painel que depende do projeto."""
    situacao: str
    """A situação vista na última leitura."""
    informe: str
    """A data e hora do informe legislativo mais recente visto ("2026-11-24 22:57:42")."""


PROJETOS = [
    Projeto(
        "Projeto da LDO 2027 (PLN nº 2/2026)",
        173677,
        "relatorios.PLDO_2027",
        "MATÉRIA COM A RELATORIA",
        "2026-11-24 22:57:42",
    ),
]


def _lista(x: Any) -> list[Any]:
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def estado(corpo: dict[str, Any]) -> tuple[str, str, str]:
    """(situação, data do informe mais recente, o que ele diz) da resposta de movimentações."""
    materia = corpo["MovimentacaoMateria"]["Materia"]
    autuacao = _lista(materia["Autuacoes"]["Autuacao"])[0]
    situacoes = _lista((autuacao.get("SituacoesAtuais") or {}).get("SituacaoAtual"))
    situacao = situacoes[0]["DescricaoSituacao"] if situacoes else ""
    informes = _lista((autuacao.get("InformesLegislativos") or {}).get("InformeLegislativo"))
    if not informes:
        return situacao, "", ""
    ultimo = max(informes, key=lambda i: i["Data"])
    return situacao, ultimo["Data"], " ".join(ultimo["Descricao"].split())


def mudancas(p: Projeto, situacao: str, informe: str, texto: str) -> list[str]:
    saida = []
    if situacao != p.situacao:
        saida.append(f"situação passou de “{p.situacao}” para “{situacao}”")
    if informe > p.informe:
        saida.append(f"informe novo em {informe[:10]}: {texto[:240]}")
    return saida


def olhar() -> str:
    """A tabela, em Markdown, dos projetos que andaram (vazia se nenhum andou)."""
    linhas = []
    for p in PROJETOS:
        try:
            corpo = rede.baixar_json(
                SENADO.format(codigo=p.codigo),
                cabecalhos={"Accept": "application/json"},
                validade=0,
            )
            achado = mudancas(p, *estado(corpo))
        except Exception as erro:  # o Senado fora do ar não é andamento: avisa e segue
            achado = [f"não foi possível ler a matéria ({str(erro)[:120]})"]
        for m in achado:
            linhas.append(f"| {p.nome} | `{p.onde}` | {m} |")
    if not linhas:
        return ""
    return "\n".join(["| Projeto | No painel | O que mudou |", "|---|---|---|", *linhas])
