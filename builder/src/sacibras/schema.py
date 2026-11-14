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


class Intervalo(Modelo):
    """Barras de erro: em cada data, de `inferior` a `superior`, na cor da série `serie`."""

    nome: str
    serie: str
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
    intervalos: list[Intervalo] = Field(default_factory=list)
    linhas: list[LinhaRef] = Field(default_factory=list)
    janela_anos: float | None = None
    """Quanto de história abre na tela (o resto fica atrás do botão "máx")."""
    fonte: str
    nota: str = ""
    """O método em uma frase, quando há conta nossa ou previsão."""
    largura: Literal["meia", "inteira"] = "meia"


class Meta(Modelo):
    """A meta oficial com que o número se compara (a de inflação, do CMN)."""

    centro: float
    inferior: float
    superior: float
    norma: str


class AoVivo(Modelo):
    """De onde o navegador busca o ponto mais recente do número (fontes com CORS aberto).

    O JSON do builder é o piso: se a busca falhar ou não trouxer data mais nova, fica o
    número do builder."""

    tipo: Literal["sgs", "sidra"]
    codigo: int | None = None
    """Código da série no SGS."""
    caminho: str = ""
    """Caminho da consulta no SIDRA (`t/5932/n1/all/v/6562/p/last%201/c11255/90707`)."""
    escala: float = 1.0
    """Multiplica o valor da fonte (para pôr na unidade do cartão)."""


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
    meta: Meta | None = None
    ao_vivo: AoVivo | None = None


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


class SimuladorDivida(Modelo):
    """A linha de base da dinâmica da dívida; o navegador refaz a conta com os controles.

    d₊₁ = d · (1 + juro) / ((1 + crescimento) · (1 + inflação)) − primário, tudo em %.
    """

    ano_inicial: int
    divida_inicial: float
    anos: list[int]
    juro: list[float]
    crescimento: list[float]
    inflacao: list[float]
    primario: list[float]
    focus_divida: list[float | None]
    realizado: list[tuple[date, float]]
    fonte: str
    nota: str


class Secao(Modelo):
    id: str
    titulo: str
    resumo: str = ""
    cartoes: list[Cartao] = Field(default_factory=list)
    graficos: list[Grafico] = Field(default_factory=list)
    tabelas: list[Tabela] = Field(default_factory=list)
    simulador: SimuladorDivida | None = None
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


class GrupoMundo(Modelo):
    """Um grupo de países do FMI (hierarquia oficial H_WEO_COUNTRIES), para abrir por país."""

    iso3: str
    """Código do grupo no WEO: G001 Mundo, G110 Avançados, G200 Emergentes, G205 América
    Latina e Caribe, G163 Zona do euro…"""
    nome: str
    membros: list[str]
    """Os países (ISO3), sem os subgrupos, como a hierarquia do FMI os lista."""


class Mundo(Modelo):
    id: Literal["mundo"] = "mundo"
    titulo: str
    resumo: str
    paises: list[Pais]
    metricas: list[MetricaMundo]
    ano_corrente: int
    edicao: str
    """De qual edição vêm as projeções, ex. 'World Economic Outlook, outubro de 2026'."""
    grupos: list[GrupoMundo] = Field(default_factory=list)
    nomes: dict[str, str] = Field(default_factory=dict)
    """{ISO3: nome em português} de todos os países que aparecem em algum grupo."""
    arquivo_paises: str = ""
    """O JSON com as métricas de todos os países (MundoPaises), lido só quando a pessoa abre
    um grupo."""
    gerado_em: datetime


class MundoPaises(Modelo):
    """As mesmas métricas do `Mundo`, para todos os países dos grupos, em menos anos."""

    id: Literal["mundo-paises"] = "mundo-paises"
    metricas: list[MetricaMundo]
    gerado_em: datetime


# ------------------------------------------------------------------ estados


class UF(Modelo):
    sigla: str
    nome: str
    regiao: Literal["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]


class MetricaEstados(Modelo):
    id: str
    nome: str
    descricao: str = ""
    unidade: str
    casas: int = 1
    referencia: str
    """O período do dado, escrito: "2º quadrimestre de 2026", "3º tri/2026", "2023"."""
    maior_e_melhor: bool | None = None
    fonte: str
    valores: dict[str, float | None]
    """{sigla da UF: valor}."""
    brasil: float | None = None
    """O número do país (ou a soma/média dos estados), quando a fonte o dá."""
    limites: list[LinhaRef] = Field(default_factory=list)
    """Linhas de referência que a própria fonte publica (ex.: o limite que consta do RGF)."""


class Fatia(Modelo):
    nome: str
    valor: float
    """Na unidade do bloco (R$ milhões, salvo dito)."""


class BlocoDeConta(Modelo):
    """Uma conta do estado aberta em partes: de onde vem a receita, para onde vai a despesa,
    do que é feita a dívida."""

    id: str
    titulo: str
    descricao: str = ""
    unidade: str = "R$ milhões"
    referencia: str
    """O período escrito: "2025", "jan–ago/2026", "2º quadrimestre de 2026"."""
    fonte: str
    fatias: list[Fatia]
    total: float | None = None
    """O total da conta, quando a soma das fatias não é o total (sobra "outras")."""


class ContasEstado(Modelo):
    uf: str
    nome: str
    blocos: list[BlocoDeConta]
    numeros: list[Cartao] = Field(default_factory=list)
    """Os números soltos do estado (investimento % da RCL, dívida com a União…)."""


class EstadosContas(Modelo):
    """As contas de cada UF, lidas só quando a pessoa abre um estado."""

    id: Literal["estados-contas"] = "estados-contas"
    contas: dict[str, ContasEstado]
    gerado_em: datetime


class Estados(Modelo):
    id: Literal["estados"] = "estados"
    titulo: str
    resumo: str
    ufs: list[UF]
    metricas: list[MetricaEstados]
    arquivo_contas: str = ""
    """O JSON com `EstadosContas`, quando houver."""
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
    resumo: str = ""
    """A manchete do assunto, para o cartão da página inicial (que não baixa a seção)."""
    ok: bool
    erro: str = ""


class Painel(Modelo):
    gerado_em: datetime
    secoes: list[ItemSecao]
    fontes: list[EstadoFonte] = Field(default_factory=list)


def pontos(serie: list[Ponto], casas: int = 4) -> list[tuple[date, float | None]]:
    return [(d, round(v, casas)) for d, v in serie]
