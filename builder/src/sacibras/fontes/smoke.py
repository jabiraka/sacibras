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
from sacibras.config import usar_b3
from sacibras.fontes import (
    b3_indices,
    bcb_copom,
    bcb_focus,
    bcb_secundario,
    bcb_sgs,
    bis,
    fmi,
    ibge_sidra,
    ocde_receita,
    pwt,
    receita_arrecadacao,
    receita_gastos,
    receita_irpf,
    tesouro_direto,
)


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
        _texto("https://www.ipeadata.gov.br/api/odata4/Metadados('GM366_IBVSP366')"),
    ),
    (
        "Penn World Table (Dataverse)",
        _texto(pwt.API, params={"persistentId": pwt.DOI}),
    ),
    (
        "BCB, negócios no mercado secundário (ZIP)",
        _texto(bcb_secundario.url(date.today() - timedelta(days=5))),
    ),
    (
        "Tesouro Direto (CSV)",
        _texto(tesouro_direto.URL, tempo_limite=180),
    ),
    ("Receita, arrecadação por estado (CSV)", _texto(receita_arrecadacao.URL, tempo_limite=120)),
    ("Receita, gastos tributários (lista)", _texto(receita_gastos.LISTAGEM)),
    ("Receita, arrecadação por setor (CSV)", _texto(receita_arrecadacao.URL_SETORES)),
    ("Receita, Grandes Números do IRPF (lista)", _texto(receita_irpf.LISTAGEM)),
    (
        "OCDE, imposto sobre o lucro",
        _texto(
            ocde_receita.LUCRO + "/BRA.A.CIT_C.ST.PT_INC_TAX.S13._Z._Z._Z",
            params={"startPeriod": "2024", "format": "csvfile"},
            tempo_limite=120,
        ),
    ),
    (
        "OCDE, Global Revenue Statistics",
        _texto(
            ocde_receita.BASE + "/BRA.TAX_REV.S13._T._T.PT_B1GQ.A",
            params={"startPeriod": "2022", "format": "csvfile"},
            tempo_limite=120,
        ),
    ),
    ("Comex Stat", _texto("https://api-comexstat.mdic.gov.br/general/dates/updated")),
    (
        "IBGE calendário (servicodados)",
        _texto("https://servicodados.ibge.gov.br/api/v3/calendario/?qtd=1", tempo_limite=20),
    ),
    (
        "IBGE malhas (servicodados)",
        _texto(
            "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?intrarregiao=UF&qualidade=minima",
            tempo_limite=20,
        ),
    ),
    (
        "FMI grupos de países (SDMX)",
        _texto(
            "https://api.imf.org/external/sdmx/2.1/hierarchicalcodelist/all/all/latest",
            cabecalhos={"Accept": "application/json"},
            tempo_limite=90,
        ),
    ),
    (
        "Tesouro RTN (CKAN)",
        _texto(
            "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show",
            params={"id": "resultado-do-tesouro-nacional"},
        ),
    ),
    (
        "IBGE projeção da população (FTP)",
        _texto(
            "https://ftp.ibge.gov.br/Projecao_da_Populacao/Projecao_da_Populacao_2024/"
            "projecoes_2024_tab4_indicadores.xlsx",
            tempo_limite=120,
        ),
    ),
    (
        "SICONFI RREO",
        _texto(
            "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo",
            params={
                "an_exercicio": "2026",
                "nr_periodo": "4",
                "co_tipo_demonstrativo": "RREO",
                "no_anexo": "RREO-Anexo 03",
                "co_esfera": "E",
                "id_ente": "35",
            },
            tempo_limite=90,
        ),
    ),
]


# Só com SB_B3=1: o site da B3 veda coleta automatizada (ver `config.usar_b3`).
FONTES_B3: list[tuple[str, Callable[[], str]]] = [
    ("B3 índices", _b3),
    (
        "B3 derivativos (cotação)",
        _texto("https://cotacao.b3.com.br/mds/api/v1/DerivativeQuotation/DI1"),
    ),
]


def rodar(*, markdown: bool = False) -> int:
    rede.SEM_CACHE = True  # é teste de conexão: nada vem do disco
    rede.TENTATIVAS = 2
    linhas: list[tuple[str, bool, float, str]] = []
    for nome, chamar in [*FONTES, *(FONTES_B3 if usar_b3() else [])]:
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
