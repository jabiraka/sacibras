"""Um lugar só para falar com as fontes: tentativas, espera e cache em arquivo.

O cache (`.cache/`, fora do git) existe para iterar sem martelar as APIs: a mesma URL
pedida de novo dentro da validade vem do disco. No GitHub Actions a pasta começa vazia a
cada rodada, então produção sempre lê a fonte.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

# Navegador genérico: várias fontes (B3, Tesouro) recusam o agente padrão do httpx.
AGENTE = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
TEMPO_LIMITE = float(os.environ.get("SB_HTTP_TIMEOUT", "40"))
TENTATIVAS = int(os.environ.get("SB_HTTP_TENTATIVAS", "3"))
PASTA_CACHE = Path(os.environ.get("SB_CACHE_DIR", ".cache"))
VALIDADE_PADRAO = float(os.environ.get("SB_CACHE_HORAS", "6")) * 3600
SEM_CACHE = os.environ.get("SB_SEM_CACHE", "") == "1"
"""Ignora o cache em arquivo (o teste de fumaça liga: o que importa é a resposta de agora)."""


class FonteForaDoArError(RuntimeError):
    """A fonte não respondeu (ou respondeu outra coisa) depois de todas as tentativas."""


_cliente: httpx.Client | None = None


def cliente() -> httpx.Client:
    global _cliente
    if _cliente is None:
        _cliente = httpx.Client(
            headers={"User-Agent": AGENTE, "Accept-Language": "pt-BR,pt;q=0.9"},
            timeout=TEMPO_LIMITE,
            follow_redirects=True,
        )
    return _cliente


def _chave(metodo: str, url: str, params: Any, dados: Any, corpo_json: Any) -> str:
    """A chave do cache. Sem corpo JSON, a mesma de antes (o cache já gravado continua valendo)."""
    partes = [metodo, url, params, dados] + ([corpo_json] if corpo_json is not None else [])
    return json.dumps(partes, sort_keys=True, ensure_ascii=False)


def _arquivo(chave: str) -> Path:
    return PASTA_CACHE / (hashlib.sha256(chave.encode()).hexdigest()[:32] + ".bin")


def baixar(
    url: str,
    *,
    params: dict[str, str] | None = None,
    metodo: str = "GET",
    dados: dict[str, str] | None = None,
    corpo_json: Any = None,
    cabecalhos: dict[str, str] | None = None,
    validade: float | None = None,
    tempo_limite: float | None = None,
) -> bytes:
    """O corpo da resposta, com cache em arquivo. `validade` em segundos (0 = sem cache).

    `dados` vai como formulário; `corpo_json`, como JSON (o Comex Stat)."""
    validade = 0 if SEM_CACHE else VALIDADE_PADRAO if validade is None else validade
    chave = _chave(metodo, url, params, dados, corpo_json)
    arquivo = _arquivo(chave)
    if validade > 0 and arquivo.exists() and time.time() - arquivo.stat().st_mtime < validade:
        return arquivo.read_bytes()

    ultimo: Exception | None = None
    for tentativa in range(TENTATIVAS):
        try:
            resposta = cliente().request(
                metodo,
                url,
                params=params,
                data=dados,
                json=corpo_json,
                headers=cabecalhos,
                timeout=tempo_limite or TEMPO_LIMITE,
            )
            # 4xx que não é "tente depois" não melhora com insistência. (O 403 fica de
            # fora: há porteiro de site que recusa ao acaso e aceita na tentativa seguinte.)
            if resposta.status_code in (400, 401, 404, 451):
                raise FonteForaDoArError(
                    f"HTTP {resposta.status_code} em {resposta.request.url}: "
                    f"{resposta.text[:200]!r}"
                )
            resposta.raise_for_status()
            corpo = resposta.content
            if validade > 0:
                PASTA_CACHE.mkdir(parents=True, exist_ok=True)
                arquivo.write_bytes(corpo)
            return corpo
        except FonteForaDoArError:
            raise
        except (httpx.HTTPError, OSError) as erro:
            ultimo = erro
            if tentativa + 1 < TENTATIVAS:
                time.sleep(1.5 * (tentativa + 1))
    raise FonteForaDoArError(f"sem resposta de {url}: {ultimo!r}") from ultimo


def baixar_json(url: str, **kw: Any) -> Any:
    """O JSON da resposta. O SGS às vezes devolve uma página HTML no lugar (visto em
    14/11/2026, no meio de uma rodada que funcionava): pede de novo, sem cache, antes de
    desistir."""
    chave = _chave(
        kw.get("metodo", "GET"), url, kw.get("params"), kw.get("dados"), kw.get("corpo_json")
    )
    corpo = b""
    for tentativa in range(TENTATIVAS):
        corpo = baixar(url, **kw)
        try:
            return json.loads(corpo)
        except json.JSONDecodeError:
            # Não deixar a resposta ruim no cache, e esperar um pouco antes de pedir de novo.
            _arquivo(chave).unlink(missing_ok=True)
            if tentativa + 1 < TENTATIVAS:
                time.sleep(2.0 * (tentativa + 1))
    raise FonteForaDoArError(f"{url} não devolveu JSON: {corpo[:120]!r}")
