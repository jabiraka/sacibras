"""SGS do Banco Central: `api.bcb.gov.br/dados/serie/bcdata.sgs.N/dados`.

Só aceita série registrada no catálogo (com unidade) — nunca código solto. Duas manhas da
API, herdadas da experiência do finance_agent: série diária recusa janela maior que dez
anos, e de vez em quando o SGS responde uma página HTML no lugar do JSON.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sacibras.catalogo import SerieSGS
from sacibras.rede import FonteForaDoArError, baixar_json
from sacibras.tipos import Ponto

URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
JANELA_DIARIA = timedelta(days=365 * 9)


def _data(texto: str) -> date:
    return datetime.strptime(texto, "%d/%m/%Y").date()


def _br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _janela(serie: SerieSGS, inicio: date, fim: date) -> list[Ponto]:
    try:
        bruto = baixar_json(
            URL.format(codigo=serie.codigo),
            params={"formato": "json", "dataInicial": _br(inicio), "dataFinal": _br(fim)},
        )
    except FonteForaDoArError as erro:
        # O 404 "Value(s) not found" quer dizer "nada nesta janela", não série errada.
        if "Value(s) not found" in str(erro):
            return []
        raise
    pontos: list[Ponto] = []
    for linha in bruto:
        valor = linha.get("valor")
        if valor in (None, ""):
            continue
        pontos.append((_data(linha["data"]), float(valor)))
    # Alguns códigos voltam em ordem decrescente de data.
    pontos.sort()
    return pontos


def ler(serie: SerieSGS, inicio: date, fim: date | None = None) -> list[Ponto]:
    """Os pontos da série entre `inicio` e `fim` (hoje, se omitido), em ordem de data.

    Séries como a Selic meta (432) vêm preenchidas até a próxima reunião do Copom: o `fim`
    em hoje corta esse futuro.
    """
    fim = fim or date.today()
    if serie.periodicidade != "D":
        return _janela(serie, inicio, fim)
    pontos: list[Ponto] = []
    cursor = inicio
    while cursor <= fim:
        ate = min(cursor + JANELA_DIARIA, fim)
        pontos.extend(_janela(serie, cursor, ate))
        cursor = ate + timedelta(days=1)
    return pontos
