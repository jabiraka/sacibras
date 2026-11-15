"""Banco Central (Demab): os negócios com títulos federais no mercado secundário, registrados
no Selic. Um ZIP por mês com um CSV, uma linha por título e por dia:
`DATA MOV;SIGLA;CODIGO;CODIGO ISIN;EMISSAO;VENCIMENTO;NUM DE OPER;…;PU MED;…;VALOR PAR;…`.

Daqui sai a NTN-B curta, que o Tesouro Direto não vende (o IPCA+ sem cupom mais curto vence
em 2029). Conferido em 15/11/2026, com o arquivo de nov/2026:

- o arquivo do mês já trazia o dia 13/11 na noite do mesmo dia;
- a NTN-B inteira é o código 760199 (760197 e 760198 são os cupons e o principal destacados);
- a coluna da taxa vem em branco para a NTN-B: a taxa sai do preço médio (`PU MED`);
- `VALOR PAR` é o valor nominal atualizado (VNA) do último dia 15, sem projeção: 4.766,34 em
  novembro até o dia 13, o mesmo que 1.000 × o IPCA acumulado de jul/2000 a set/2026
  (SGS 433). Para chegar à cotação, projeta-se o VNA até a data do negócio com o IPCA do mês
  (`curvas.vna_projetado`).
"""

from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sacibras.rede import FonteForaDoArError, baixar

NTNB = "760199"
MINIMO_DE_NEGOCIOS = 10
"""Abaixo disso o preço médio do dia é de poucos negócios e fica de fora."""


def url(mes: date) -> str:
    return f"https://www4.bcb.gov.br/pom/demab/negociacoes/download/NegT{mes:%Y%m}.ZIP"


@dataclass(frozen=True)
class Negocio:
    vencimento: date
    pu_medio: float
    valor_par: float
    operacoes: int


def _numero(texto: str) -> float:
    return float(texto.replace(".", "").replace(",", "."))


def _data(texto: str) -> date:
    return datetime.strptime(texto, "%d/%m/%Y").date()


def ler(corpo: bytes) -> dict[date, list[Negocio]]:
    """{dia: [NTN-B negociada, por vencimento]} de um arquivo do mês."""
    with zipfile.ZipFile(io.BytesIO(corpo)) as pacote:
        texto = pacote.read(pacote.namelist()[0]).decode("latin-1")
    saida: dict[date, list[Negocio]] = {}
    for linha in csv.DictReader(io.StringIO(texto), delimiter=";"):
        if linha["SIGLA"].strip() != "NTN-B" or linha["CODIGO"].strip() != NTNB:
            continue
        if not linha["PU MED"].strip() or not linha["VALOR PAR"].strip():
            continue
        operacoes = int(linha["NUM DE OPER"])
        if operacoes < MINIMO_DE_NEGOCIOS:
            continue
        saida.setdefault(_data(linha["DATA MOV"]), []).append(
            Negocio(
                _data(linha["VENCIMENTO"]),
                _numero(linha["PU MED"]),
                _numero(linha["VALOR PAR"]),
                operacoes,
            )
        )
    for negocios in saida.values():
        negocios.sort(key=lambda n: n.vencimento)
    return saida


def ntnb_recentes(alvo: date) -> list[tuple[date, Negocio]]:
    """O negócio mais recente de cada NTN-B, até `alvo`: [(dia, negócio)], por vencimento.
    Título sem negócio bastante no dia fica com o do último dia em que teve (Caio,
    15/11/2026: "se não tiver negociação tem que ser igual a de ontem"). Olha o arquivo do
    mês de `alvo` e o do mês anterior."""
    achados: dict[date, tuple[date, Negocio]] = {}
    leu = False
    for mes in (alvo, alvo.replace(day=1) - timedelta(days=1)):
        try:
            por_dia = ler(baixar(url(mes), validade=6 * 3600, tempo_limite=60))
        except (FonteForaDoArError, zipfile.BadZipFile, KeyError, IndexError):
            continue
        leu = True
        for dia in sorted((d for d in por_dia if d <= alvo), reverse=True):
            for negocio in por_dia[dia]:
                achados.setdefault(negocio.vencimento, (dia, negocio))
    if not leu:
        raise ValueError(f"sem arquivo de negócios até {alvo}")
    return [achados[v] for v in sorted(achados)]
