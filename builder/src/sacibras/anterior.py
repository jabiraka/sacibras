"""`sacibras anterior`: traz os JSONs do site no ar para a pasta de saída antes do build.

No Actions a pasta começa vazia; sem isto, seção cuja fonte falhou sumiria do site. Com os
JSONs da rodada anterior na pasta, o build mantém o que não conseguiu refazer (Caio,
14/11/2026: *"se o agendamento falhar, pode manter os dados = ao dia anterior, nunca deixe em
branco os valores"*).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sacibras import rede

SITE = "https://jabiraka.github.io/sacibras/data/"


def _arquivos_extras(secao: Any) -> list[str]:
    """Os arquivos à parte que uma seção aponta (`arquivo_contas`, `arquivo_paises`...)."""
    if not isinstance(secao, dict):
        return []
    return [v for k, v in secao.items() if k.startswith("arquivo_") and isinstance(v, str) and v]


def _nome_seguro(nome: str) -> bool:
    return bool(nome) and "/" not in nome and "\\" not in nome and not nome.startswith(".")


def trazer(saida: Path, site: str = SITE) -> list[str]:
    """Baixa o `painel.json` do site e cada arquivo que ele aponta; devolve os gravados.

    Não grava por cima de arquivo que já está na pasta (no PC, o JSON local vale mais)."""
    saida.mkdir(parents=True, exist_ok=True)
    painel = json.loads(rede.baixar(site + "painel.json", validade=0))
    nomes = [s["arquivo"] for s in painel.get("secoes", []) if s.get("arquivo")]
    gravados: list[str] = []
    vistos: set[str] = set()
    while nomes:
        nome = nomes.pop(0)
        if nome in vistos or not _nome_seguro(nome):
            continue
        vistos.add(nome)
        destino = saida / nome
        try:
            corpo = rede.baixar(site + nome, validade=0)
            dados = json.loads(corpo)
        except (rede.FonteForaDoArError, ValueError) as erro:
            print(f"  aviso: {nome} não veio do site ({str(erro)[:120]})")
            continue
        nomes.extend(_arquivos_extras(dados))
        if destino.exists():
            continue
        destino.write_bytes(corpo)
        gravados.append(nome)
    rede.FALHAS.clear()  # o site anterior não é fonte: falha aqui não conta para as seções
    return gravados
