"""Tesouro Nacional, "Raio-X das empresas dos Estados brasileiros": uma linha por estatal
estadual, em reais, o que os estados declararam no Siconfi.

O Tesouro publica a história em tesouro.github.io/empresas-estados e os dados no repositório
oficial dele (github.com/tesouro/empresas-estados), uma pasta por edição: a edição N traz o ano
N-1. O Tesouro diz que a correção dos números é de quem declarou. Conferido em 26/11/2026: as
somas das edições 2023 a 2025 repetem os aportes, as subvenções e os dividendos que a página
publica (2024: 11,3, 12,4 e 5,3 R$ bi) e as da edição 2022, o lucro de 2021 (22,1). A série
começa na edição 2022: antes dela a base mudou de método, o que a própria página avisa. A coluna
"Subvenção (anterior)" da edição 2025 soma R$ 81 bi contra 12 do ano: fora.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date

import httpx

from sacibras.rede import FonteForaDoArError, baixar, cliente

PAGINA = "https://www.tesourotransparente.gov.br/historias/empresas-estatais-do-governo"
ARQUIVO = (
    "https://raw.githubusercontent.com/tesouro/empresas-estados/master/v{edicao}/dados/dados.csv"
)
FONTE = "Tesouro Nacional, Raio-X das empresas dos Estados"
PRIMEIRA = 2022
ULTIMA_CONHECIDA = 2025
VALIDADE = 24 * 3600


@dataclass(frozen=True)
class EmpresaEstadual:
    ano: int
    uf: str
    estado: str
    nome: str
    dependente: bool
    lucro: float
    dividendos: float
    subvencao: float
    capital: float
    """Reforço de capital que o estado pôs na empresa no ano."""


def _numero(texto: str | None) -> float:
    """Lê "-88773662,59"; "NA" (não informado) a página soma como zero."""
    try:
        return float((texto or "").strip().replace(",", "."))
    except ValueError:
        return 0.0


def ler(conteudo: bytes, ano: int) -> list[EmpresaEstadual]:
    texto = conteudo.decode("utf-8-sig", "replace")
    linhas = list(csv.DictReader(io.StringIO(texto), delimiter=";"))
    pedidas = {"Estado", "Nome_estado", "emp", "dep", "lucros", "Dividendos", "Subvenção"}
    pedidas.add("Reforço de Capital")
    if not linhas or not pedidas <= set(linhas[0]):
        raise FonteForaDoArError(f"Tesouro, estatais dos estados: o arquivo de {ano} mudou")
    return [
        EmpresaEstadual(
            ano=ano,
            uf=li["Estado"].strip(),
            estado=li["Nome_estado"].strip(),
            nome=li["emp"].strip(),
            # "Dependente" ou "Não Dependente".
            dependente=li["dep"].strip().lower() == "dependente",
            lucro=_numero(li["lucros"]),
            dividendos=_numero(li["Dividendos"]),
            subvencao=_numero(li["Subvenção"]),
            capital=_numero(li["Reforço de Capital"]),
        )
        for li in linhas
    ]


def edicao_mais_nova(hoje: date) -> int:
    """Procura edição depois da última conhecida. Edição que ainda não saiu dá 404, o que não
    é fonte fora do ar: por isso a pergunta vai direto ao cliente, sem passar por `baixar`."""
    for edicao in range(hoje.year + 1, ULTIMA_CONHECIDA, -1):
        try:
            if cliente().head(ARQUIVO.format(edicao=edicao)).status_code == 200:
                return edicao
        except httpx.HTTPError:
            break
    return ULTIMA_CONHECIDA


def empresas(hoje: date) -> tuple[str, list[EmpresaEstadual]]:
    """A fonte e as linhas de todos os anos."""
    nova = edicao_mais_nova(hoje)
    saida: list[EmpresaEstadual] = []
    for edicao in range(PRIMEIRA, nova + 1):
        conteudo = baixar(ARQUIVO.format(edicao=edicao), validade=VALIDADE, tempo_limite=60)
        saida += ler(conteudo, edicao - 1)
    return f"{FONTE}, edições {PRIMEIRA} a {nova} (declarado ao Siconfi)", saida
