"""O que o painel mostra de um projeto que ainda não é lei, e o aviso quando ele anda.

Caio, 25/11/2026, sobre o projeto da LDO 2027: *"Pode já colocar, dizendo que ainda não virou
lei, isso vai ser sancionado logo, a gente vai ter que monitorar se algo muda até a
sanção"*. Cada projeto aqui guarda o que foi visto na última leitura (a situação no Senado e
o informe mais recente). O `sacibras tramitacao` pergunta de novo aos dados abertos do Senado
(que servem também as matérias do Congresso, como os PLN) e lista o que mudou; o workflow
"Prazos de releitura" abre a issue `tramitação` com a lista. Ao reler o projeto, atualize o
número em `relatorios.py` e aqui o que foi visto; sancionada a lei, tire o projeto da lista.

Pelo mesmo caminho vai o cálculo da CBS do TCU (Caio, 25/11/2026: ler sozinho onde a fonte
publica em API): a API de acórdãos do TCU lista os mais novos primeiro, e o aviso sai quando
um sumário traz "alíquota de referência" da CBS para outro ano ou com outro número que o lido
em `relatorios.CBS_REFERENCIA_2027`. O número na tela continua à mão: o que vale em lei é a
resolução do Senado.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sacibras import rede, relatorios

SENADO = "https://legis.senado.leg.br/dadosabertos/materia/movimentacoes/{codigo}"
TCU = "https://dados-abertos.apps.tcu.gov.br/api/acordao/recupera-acordaos"
PAGINAS_DO_TCU = 2
"""Páginas de 500 acórdãos, dos mais novos para trás (em nov/2026, umas duas semanas cada): o
workflow roda todo dia útil, então duas bastam com folga."""
CBS_LIDA = (2027, relatorios.CBS_REFERENCIA_2027)
"""(ano, %) da alíquota de referência da CBS lida no acórdão mais novo."""


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


def cbs_nos_acordaos(acordaos: list[dict[str, Any]]) -> list[tuple[int, float, str, str]]:
    """(ano, alíquota em %, título, data) de cada acórdão cujo sumário traz a alíquota de
    referência da CBS de um ano."""
    saida = []
    for a in acordaos:
        sumario = " ".join(str(a.get("sumario") or "").upper().split())
        aliquota = re.search(r"AL[IÍ]QUOTA DE REFER[EÊ]NCIA DE (\d+(?:,\d+)?) ?%", sumario)
        ano = re.search(r"\bCBS\)? PARA (\d{4})", sumario)
        if aliquota and ano:
            valor = float(aliquota.group(1).replace(",", "."))
            saida.append((int(ano.group(1)), valor, str(a.get("titulo")), str(a.get("dataSessao"))))
    return saida


def cbs_nova(acordaos: list[dict[str, Any]]) -> list[str]:
    """O que mudou contra a CBS lida: ano mais novo, ou o mesmo ano com outro número."""
    ano_lido, lida = CBS_LIDA
    return [
        f"{titulo} ({data}): alíquota de referência da CBS de {ano} de "
        f"{str(valor).replace('.', ',')} %"
        for ano, valor, titulo, data in cbs_nos_acordaos(acordaos)
        if ano > ano_lido or (ano == ano_lido and valor != lida)
    ]


def olhar_tcu() -> list[str]:
    acordaos: list[dict[str, Any]] = []
    for pagina in range(PAGINAS_DO_TCU):
        corpo = rede.baixar_json(
            TCU, params={"inicio": str(pagina * 500), "quantidade": "500"}, validade=0
        )
        acordaos += corpo if isinstance(corpo, list) else []
    return cbs_nova(acordaos)


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
    try:
        novos = olhar_tcu()
    except Exception as erro:
        novos = [f"não foi possível ler a API do TCU ({str(erro)[:120]})"]
    for m in novos:
        linhas.append(f"| Cálculo da CBS (TCU) | `relatorios.CBS_REFERENCIA_2027` | {m} |")
    if not linhas:
        return ""
    return "\n".join(["| Projeto | No painel | O que mudou |", "|---|---|---|", *linhas])
