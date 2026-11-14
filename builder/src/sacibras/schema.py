"""O contrato entre o builder e o site: os JSONs de `web/public/data/`.

O site não sabe nada de economia: ele desenha o que estes modelos declaram. Todo número leva
unidade, casas decimais, data de referência e fonte. `web/src/tipos.ts` espelha este arquivo.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from sacibras.tipos import Periodicidade, Ponto

Procedencia = Literal["oficial", "mercado", "calculado"]
"""oficial: publicado pelo órgão; mercado: preço ou consenso (Focus); calculado: conta nossa
sobre dados oficiais, com o método na nota."""

Papel = Literal["realizado", "consenso", "previsao", "referencia"]


class Modelo(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Serie(Modelo):
    id: str
    nome: str
    pontos: list[tuple[date, float | None]]
    papel: Papel = "realizado"
    tracejado_desde: date | None = None
    """Daqui em diante a própria fonte chama de projeção (o WEO do FMI): a linha segue,
    tracejada."""


class Faixa(Modelo):
    """Uma banda (intervalo da meta, faixa de erro) entre `inferior` e `superior`."""

    nome: str
    pontos: list[tuple[date, float, float]]


class LinhaRef(Modelo):
    valor: float
    rotulo: str


class Grafico(Modelo):
    id: str
    titulo: str
    subtitulo: str = ""
    tipo: Literal["linha", "area", "barras", "empilhado", "degrau", "curva"] = "linha"
    unidade: str
    casas: int = 1
    periodicidade: Periodicidade
    series: list[Serie]
    faixa: Faixa | None = None
    linhas: list[LinhaRef] = Field(default_factory=list)
    janela_anos: float | None = None
    """Quanto de história abre na tela (o resto fica atrás do botão "máx")."""
    fonte: str
    nota: str = ""
    """O método em uma frase, quando há conta nossa ou previsão."""
    largura: Literal["meia", "inteira"] = "meia"


class Cartao(Modelo):
    id: str
    rotulo: str
    valor: float
    unidade: str
    casas: int = 1
    referencia: date
    periodicidade: Periodicidade
    detalhe: str = ""
    anterior: float | None = None
    anterior_rotulo: str = ""
    fonte: str
    procedencia: Procedencia = "oficial"
    mini: list[tuple[date, float]] = Field(default_factory=list)
    secao: str = ""
    """Âncora da seção em que o número é explicado."""


class LinhaTabela(Modelo):
    rotulo: str
    valores: list[float | None]
    unidade: str
    casas: int = 1
    fonte: str = ""


class Tabela(Modelo):
    id: str
    titulo: str
    subtitulo: str = ""
    colunas: list[str]
    linhas: list[LinhaTabela]
    fonte: str
    nota: str = ""


class Secao(Modelo):
    id: str
    titulo: str
    resumo: str = ""
    cartoes: list[Cartao] = Field(default_factory=list)
    graficos: list[Grafico] = Field(default_factory=list)
    tabelas: list[Tabela] = Field(default_factory=list)
    gerado_em: datetime


# ------------------------------------------------------------------ Brasil no mundo


class Pais(Modelo):
    iso3: str
    nome: str
    grupo: Literal["america_latina", "avancados", "emergentes", "agregado"]


class MetricaMundo(Modelo):
    id: str
    nome: str
    descricao: str = ""
    unidade: str
    casas: int = 1
    maior_e_melhor: bool | None = None
    fonte: str
    anos: list[int]
    primeiro_ano_projetado: int | None = None
    """Do ano em diante os números são projeção da fonte (o FMI marca por país; aqui vai o
    primeiro ano em que algum país é projeção)."""
    valores: dict[str, list[float | None]]
    """{iso3: um valor por ano de `anos`}."""


class Mundo(Modelo):
    id: Literal["mundo"] = "mundo"
    titulo: str
    resumo: str
    paises: list[Pais]
    metricas: list[MetricaMundo]
    ano_corrente: int
    edicao: str
    """De qual edição vêm as projeções, ex. 'World Economic Outlook, outubro de 2026'."""
    gerado_em: datetime


# ------------------------------------------------------------------ índice


class EstadoFonte(Modelo):
    fonte: str
    ok: bool
    detalhe: str = ""


class ItemSecao(Modelo):
    id: str
    titulo: str
    arquivo: str
    ok: bool
    erro: str = ""


class Painel(Modelo):
    gerado_em: datetime
    secoes: list[ItemSecao]
    fontes: list[EstadoFonte] = Field(default_factory=list)


def pontos(serie: list[Ponto], casas: int = 4) -> list[tuple[date, float | None]]:
    return [(d, round(v, casas)) for d, v in serie]
