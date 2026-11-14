"""`sacibras fontes-smoke`: uma chamada mínima a cada fonte, para mapear bloqueios.

Roda localmente e dentro do GitHub Actions (os runners ficam nos EUA, e algumas fontes
brasileiras recusam IP de fora). Sem cache: o que importa é a resposta de agora.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date, timedelta

from sacibras import rede
from sacibras.catalogo import SGS
from sacibras.fontes import b3_indices, bcb_copom, bcb_focus, bcb_sgs, bis, fmi, ibge_sidra


def _sgs() -> str:
    pontos = bcb_sgs.ler(SGS["IPCA_12M"], date.today() - timedelta(days=200))
    return f"IPCA 12m {pontos[-1][1]} em {pontos[-1][0]:%m/%Y}"


def _focus() -> str:
    return f"IPCA {date.today().year}: {bcb_focus.mediana_anual_hoje('IPCA')[date.today().year]}"


def _sidra() -> str:
    pontos = ibge_sidra.serie(6381, 4099, periodos="last 1")
    return f"desocupação {pontos[-1][1]} em {pontos[-1][0]:%m/%Y}"


def _copom() -> str:
    ultima = bcb_copom.reunioes()[-1]
    return f"reunião {ultima.numero} em {ultima.data:%d/%m/%Y}: {ultima.meta}"


def _b3() -> str:
    pontos = b3_indices.ano("IBOV", date.today().year, corrente=True)
    return f"Ibovespa {pontos[-1][1]:.0f} em {pontos[-1][0]:%d/%m/%Y}"


def _fmi() -> str:
    weo = fmi.weo(["BRA"], ["NGDP_RPCH"], date.today().year, date.today().year)
    return f"WEO de {weo.publicado_em:%m/%Y}: PIB {next(iter(weo.valores.values()))}"


def _bis() -> str:
    pontos = bis.juro_basico(["BR"], date.today() - timedelta(days=120))["BR"]
    return f"juro básico BR {pontos[-1][1]} em {pontos[-1][0]:%m/%Y}"


def _texto(url: str, **kw: object) -> Callable[[], str]:
    def chamar() -> str:
        corpo = rede.baixar(url, validade=0, **kw)  # type: ignore[arg-type]
        return f"{len(corpo) / 1024:.0f} KB"

    return chamar


FONTES: list[tuple[str, Callable[[], str]]] = [
    ("BCB SGS", _sgs),
    ("BCB Focus (Olinda)", _focus),
    ("BCB Copom (site)", _copom),
    ("IBGE SIDRA", _sidra),
    ("B3 índices", _b3),
    (
        "B3 derivativos (cotação)",
        _texto("https://cotacao.b3.com.br/mds/api/v1/DerivativeQuotation/DI1"),
    ),
    ("FMI WEO (SDMX)", _fmi),
    ("BIS", _bis),
    (
        "SICONFI",
        _texto("https://apidatalake.tesouro.gov.br/ords/siconfi/tt/entes", tempo_limite=90),
    ),
    (
        "Tesouro Transparente (CKAN)",
        _texto(
            "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_search",
            params={"q": "resultado do tesouro nacional", "rows": "1"},
        ),
    ),
    (
        "IPEADATA",
        _texto("http://www.ipeadata.gov.br/api/odata4/Metadados('GM366_IBVSP366')"),
    ),
    ("Comex Stat", _texto("https://api-comexstat.mdic.gov.br/general/dates/updated")),
    (
        "IBGE calendário (servicodados)",
        _texto("https://servicodados.ibge.gov.br/api/v3/calendario/?qtd=1", tempo_limite=20),
    ),
]


def rodar(*, markdown: bool = False) -> int:
    rede.VALIDADE_PADRAO = 0  # sem cache: é teste de conexão
    rede.TENTATIVAS = 2
    linhas: list[tuple[str, bool, float, str]] = []
    for nome, chamar in FONTES:
        inicio = time.monotonic()
        try:
            detalhe, ok = chamar(), True
        except Exception as erro:
            detalhe, ok = str(erro)[:140].replace("\n", " "), False
        linhas.append((nome, ok, time.monotonic() - inicio, detalhe))
        print(f"  {'ok   ' if ok else 'FALHA'} {nome:32} {linhas[-1][2]:5.1f}s  {detalhe}")
    if markdown:
        print("\n| Fonte | Responde? | Tempo | Detalhe |\n|---|---|---|---|")
        for nome, ok, tempo, detalhe in linhas:
            print(f"| {nome} | {'sim' if ok else '**não**'} | {tempo:.1f} s | {detalhe} |")
    # Falha de fonte não é falha do teste: o resultado é a tabela.
    return 0
