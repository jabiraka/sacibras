"""ONS (Operador Nacional do Sistema Elétrico), dados abertos: energia armazenada nos
reservatórios das hidrelétricas, por subsistema, dia a dia.

Conjunto "EAR Diário por Subsistema" (`dados.ons.org.br/dataset/ear-diario-por-subsistema`,
licença Creative Commons Atribuição), um CSV por ano desde 2000, ~60 KB cada, separado por
`;`. Conferido em 14/11/2026: responde de primeira, último dia 12/11/2026. Colunas:
`id_subsistema;nom_subsistema;ear_data;ear_max_subsistema;ear_verif_subsistema_mwmes;
ear_verif_subsistema_percentual`. O percentual do país (SIN) não vem pronto: é a soma da
energia armazenada dos quatro subsistemas sobre a soma das capacidades.
"""

from __future__ import annotations

from datetime import date

from sacibras.rede import FonteForaDoArError, baixar
from sacibras.tipos import Ponto

URL = (
    "https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/ear_subsistema_di/"
    "EAR_DIARIO_SUBSISTEMA_{ano}.csv"
)
PRIMEIRO_ANO = 2000
FONTE = "ONS, dados abertos (EAR diário por subsistema)"


def ler_csv(texto: str) -> list[Ponto]:
    """[(dia, % da capacidade do SIN)]: só os dias em que os quatro subsistemas informaram."""
    linhas = texto.strip().splitlines()
    if not linhas:
        return []
    cabecalho = [c.strip() for c in linhas[0].split(";")]
    try:
        col_dia = cabecalho.index("ear_data")
        col_max = cabecalho.index("ear_max_subsistema")
        col_ear = cabecalho.index("ear_verif_subsistema_mwmes")
    except ValueError as erro:
        raise FonteForaDoArError(f"ONS: o CSV mudou de colunas ({cabecalho})") from erro
    somas: dict[date, list[float]] = {}
    for linha in linhas[1:]:
        campos = linha.split(";")
        try:
            dia = date.fromisoformat(campos[col_dia].strip()[:10])
            maximo, armazenado = float(campos[col_max]), float(campos[col_ear])
        except (ValueError, IndexError):
            continue
        soma = somas.setdefault(dia, [0.0, 0.0, 0.0])
        soma[0] += armazenado
        soma[1] += maximo
        soma[2] += 1
    return [
        (dia, armazenado / maximo * 100)
        for dia, (armazenado, maximo, quantos) in sorted(somas.items())
        if quantos == 4 and maximo > 0
    ]


def reservatorios(hoje: date, desde: int = PRIMEIRO_ANO) -> list[Ponto]:
    """Energia armazenada no SIN, em % da capacidade, dia a dia desde `desde`."""
    pontos: list[Ponto] = []
    for ano in range(max(desde, PRIMEIRO_ANO), hoje.year + 1):
        # Ano fechado não muda: um mês de cache. O corrente segue a validade padrão.
        validade = None if ano == hoje.year else 30 * 24 * 3600
        corpo = baixar(URL.format(ano=ano), validade=validade, tempo_limite=60)
        pontos.extend(ler_csv(corpo.decode("utf-8", errors="replace")))
    return pontos


def media_mensal(pontos: list[Ponto]) -> list[Ponto]:
    """A média de cada mês (datada no dia 1º)."""
    meses: dict[date, list[float]] = {}
    for d, v in pontos:
        meses.setdefault(date(d.year, d.month, 1), []).append(v)
    return [(m, sum(vs) / len(vs)) for m, vs in sorted(meses.items())]
