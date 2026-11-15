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
    """Barras de erro: em cada data, de `inferior` a `superior`, em volta da série `serie`.

    Desenho (Caio, 14/11/2026, "não gostei da barra azul"): traço fino em tinta neutra com
    as pontas marcadas; `meio`, quando há, é a parte grossa (a faixa de 50 %)."""

    nome: str
    serie: str
    pontos: list[tuple[date, float, float]]
    meio: list[tuple[date, float, float]] = []
    nome_meio: str = ""


class LinhaRef(Modelo):
    valor: float
    rotulo: str


class Piramide(Modelo):
    """A pirâmide etária: pessoas por sexo e grupo de idade, um ano escolhido em lista.

    `homens[i][k]` é o grupo `grupos[k]` no ano `anos[i]`, em mil pessoas."""

    grupos: list[str]
    """Do mais novo ao mais velho: "0 a 4", "5 a 9"… "90 ou mais"."""
    anos: list[int]
    homens: list[list[float]]
    mulheres: list[list[float]]
    ano_inicial: int
    """O ano que abre escolhido (o corrente)."""
    ano_contorno: int
    """O ano desenhado só em contorno, para comparar (o primeiro da série)."""
    primeiro_ano_projetado: int
    """Do ano em diante é projeção da fonte."""


class EixoDispersao(Modelo):
    nome: str
    unidade: str
    casas: int = 1


class PontoDispersao(Modelo):
    chave: str
    """ISO3 do país (ou sigla da UF)."""
    nome: str
    x: float
    y: float


class Dispersao(Modelo):
    """Um ponto por país: uma métrica em cada eixo. O Brasil (BRA) sai em destaque."""

    eixo_x: EixoDispersao
    eixo_y: EixoDispersao
    pontos: list[PontoDispersao]
    correlacao: float | None = None


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
    marcas_y: list[LinhaRef] = Field(default_factory=list)
    """Eixo vertical com nome em vez de número (a nota de crédito: 0 = "BBB−/Baa3")."""
    eixo: Literal["tempo", "meses"] = "tempo"
    """"meses": o eixo horizontal conta meses de uma marca (o primeiro corte da Selic), não
    datas. As datas dos pontos vêm de `modelos.selic.mes_relativo` (jan/2000 é o mês 0) e o
    site escreve "mês k"; não há janela de anos."""
    marco: str = ""
    """No eixo "meses", o nome do mês zero ("mês do primeiro corte")."""
    janela_anos: float | None = None
    """Quanto de história abre na tela (o resto fica atrás do botão "máx")."""
    fonte: str
    nota: str = ""
    """O método em uma frase, quando há conta nossa ou previsão."""
    largura: Literal["meia", "inteira"] = "meia"
    piramide: Piramide | None = None
    """Com ela, o site desenha a pirâmide etária no lugar das séries."""
    dispersao: Dispersao | None = None
    """Com ela, o site desenha um ponto por país no lugar das séries."""
    secao: str = ""
    """O assunto de onde o gráfico veio: só na página inicial, para o elo "abrir"."""


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
    texto: str = ""
    """Mostrado no lugar do número quando o resultado é um nome (a nota de crédito: "BB")."""
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
    textos: list[str] = Field(default_factory=list)
    """Quando há, as células da linha são estes textos (uma linha do tempo, um quadro de
    regras) e `valores` fica vazio."""


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


class SimuladorSelic(Modelo):
    """O que o Banco Central estima que muda quando a Selic fica diferente por um ano.

    Tudo aqui é número publicado pelo BC para 1 pp de Selic (`relatorios.py`); o navegador
    só multiplica pelo tamanho da mudança escolhida e põe ao lado do que o Focus espera."""

    ano: int
    """O ano do exercício: a Selic diferente durante os quatro trimestres dele."""
    focus_selic: float | None
    focus_ipca: float | None
    focus_dolar: float | None
    focus_divida: float | None
    meta: Meta | None
    trimestres: list[date]
    """O trimestre zero (o último antes do ano) e os 16 seguintes."""
    selic_caminho: list[float]
    """O desvio da Selic em cada trimestre, para 1 pp: um ano inteiro e a volta."""
    ipca_agregado: list[float]
    """pp no IPCA acumulado em quatro trimestres, por 1 pp de Selic: modelo agregado."""
    ipca_desagregado: list[float]
    ipca_faixa_menor: list[float]
    """A ponta de menos efeito da faixa de 90 % do BC, por trimestre e por 1 pp."""
    ipca_faixa_maior: list[float]
    faixa_do_ipca: str
    """De onde é a faixa, numa frase curta ("faixa de 90 % do BC, versão de dez/2021")."""
    dolar_por_pp: float
    """% no dólar por 1 pp de Selic."""
    dolar_por_pp_faixa: tuple[float, float]
    divida_por_pp_de_selic: float
    """pp do PIB na dívida bruta por 1 pp de Selic mantido por 12 meses."""
    divida_por_1_de_dolar: float
    divida_por_pp_de_precos: float
    pib_em_reais: float | None
    """PIB de 12 meses, em R$ bilhões: para dizer os pontos do PIB em reais."""
    erro_focus_ipca: float | None = None
    """Quanto o Focus desta época costuma errar o IPCA do ano seguinte, em pp."""
    erro_focus_dolar: float | None = None
    """O mesmo para o dólar do fim do ano seguinte, em %."""
    erro_focus_divida: float | None = None
    """O mesmo para a dívida bruta, em pp do PIB."""
    erro_focus_desde: int | None = None
    fonte: str
    nota: str
    como_ler: str


class TipoDeCompra(Modelo):
    """Um tipo de compra na reforma do consumo: quanto da alíquota cheia paga e quanto volta."""

    id: str
    rotulo: str
    """Curto, para caber na lista suspensa do celular."""
    descricao: str
    paga: float
    """% da alíquota cheia que este tipo de compra paga (100, 70, 40 ou 0)."""
    volta_cbs: float
    """% da CBS devolvida à família de baixa renda."""
    volta_ibs: float
    norma: str


class EtapaDaReforma(Modelo):
    """Um trecho da transição: as alíquotas cheias que valem nele."""

    id: str
    rotulo: str
    cbs: float | None
    """% sobre o valor; None quando ainda não há número (o controle da alíquota decide)."""
    ibs: float | None
    devolve_ibs: bool
    """Se a devolução do IBS à baixa renda já vale nesta etapa."""
    aviso: str
    """O que mais se paga nesta etapa e fica fora da conta."""


class MarcaDeAliquota(Modelo):
    valor: float
    rotulo: str


class SimuladorReforma(Modelo):
    """Quanto de IBS e CBS vai numa compra. Tudo aqui é lei lida ou conta oficial; o navegador
    multiplica o valor da compra pela alíquota e pela fração que o tipo de compra paga."""

    tipos: list[TipoDeCompra]
    etapas: list[EtapaDaReforma]
    etapa_inicial: str
    aliquota: float
    """A alíquota cheia (IBS + CBS) em que o controle abre: a conta oficial mais recente."""
    aliquota_minima: float
    """A ponta de baixo da faixa: o teto que a lei manda perseguir."""
    aliquota_maxima: float
    parte_do_ibs: float
    """A parte da alíquota cheia que é IBS (0 a 1), pela conta do Comitê Gestor."""
    marcas: list[MarcaDeAliquota]
    fonte: str
    nota: str
    como_ler: str


class Alerta(Modelo):
    """Um indicador do painel de alerta: o valor de hoje na régua da própria história.

    Não é previsão de crise: diz só em que parte da história o indicador esteve melhor."""

    id: str
    grupo: str
    """O título do grupo em que aparece: "Contas públicas", "Câmbio e contas externas"…"""
    nome: str
    valor: float
    unidade: str
    casas: int = 1
    referencia: date
    periodicidade: Periodicidade
    pior_quando: Literal["alto", "baixo"]
    pior_que: float
    """% das observações desde `desde` em que o indicador esteve em situação melhor."""
    minimo: float
    maximo: float
    mediana: float
    desde: date
    limite: LinhaRef | None = None
    """O limite oficial, quando existe (o teto da meta de inflação)."""
    fonte: str
    procedencia: Procedencia = "oficial"
    significa: str = ""
    """O que o indicador mede, em palavras de todo dia (`alertas.EXPLICACOES`)."""
    por_que: str = ""
    """Por que ele é um sinal de alerta."""
    pode_levar: str = ""
    """No que costuma dar quando piora (o caminho que a história mostrou, não previsão)."""
    ha_um_ano: float | None = None
    """O valor de um ano antes, para a vista "o que mudou em um ano"."""
    ha_um_ano_em: date | None = None
    pior_que_ha_um_ano: float | None = None
    """Onde o valor de um ano antes fica na régua de toda a história (mesmo corte de hoje)."""


class Elo(Modelo):
    """Um atalho para outra tela do painel ("#juros/efeito"), com o nome e uma frase."""

    endereco: str
    titulo: str
    resumo: str = ""


class Subcategoria(Modelo):
    """Uma parte do assunto ("Núcleos e o ritmo", na Inflação): o que abre junto, numa tela só.

    As listas guardam os ids dos cartões, gráficos e tabelas do próprio assunto, na ordem em
    que aparecem. `extras` são as peças próprias que o assunto traz fora dessas listas."""

    id: str
    titulo: str
    resumo: str = ""
    """Uma frase: o que a pessoa acha aqui dentro."""
    cartoes: list[str] = Field(default_factory=list)
    graficos: list[str] = Field(default_factory=list)
    tabelas: list[str] = Field(default_factory=list)
    extras: list[Literal["simulador", "simulador-selic", "simulador-reforma", "alertas"]] = Field(
        default_factory=list
    )
    veja: list[Elo] = Field(default_factory=list)
    """Atalhos para partes de outros assuntos que tratam do mesmo ("Veja também")."""


class Secao(Modelo):
    id: str
    titulo: str
    resumo: str = ""
    subcategorias: list[Subcategoria] = Field(default_factory=list)
    """Vazia: o assunto abre inteiro, numa tela só (como antes)."""
    cartoes: list[Cartao] = Field(default_factory=list)
    graficos: list[Grafico] = Field(default_factory=list)
    tabelas: list[Tabela] = Field(default_factory=list)
    simulador: SimuladorDivida | None = None
    simulador_selic: SimuladorSelic | None = None
    simulador_reforma: SimuladorReforma | None = None
    alertas: list[Alerta] = Field(default_factory=list)
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


class PeriodoDaMetrica(Modelo):
    """Uma métrica dos estados em outro período (um trimestre anterior)."""

    referencia: str
    valores: dict[str, float | None]
    brasil: float | None = None
    intervalos: dict[str, tuple[float, float]] = Field(default_factory=dict)
    nota: str = ""
    """A frase do período, que a tela põe antes da descrição da métrica."""


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
    grupo: str = ""
    """O assunto da métrica ("Economia", "Trabalho e renda"…): junta as opções na lista e as
    colunas na tabela completa."""
    intervalos: dict[str, tuple[float, float]] = Field(default_factory=dict)
    """Só em previsão: {sigla: (de, até)}, a faixa onde o número oficial costuma cair."""
    estimados: list[str] = Field(default_factory=list)
    """UFs cujo valor é estimativa por regra nossa (a tela marca o ponto e diz no mapa)."""
    como_ler: str = ""
    """A faixa de erro em palavras de todo dia, quando há `intervalos`."""
    anuais: dict[str, dict[int, float]] = Field(default_factory=dict)
    """Só no crescimento do PIB: {sigla ou "BR": {ano: índice de volume}}. A tela calcula o
    crescimento na janela que a pessoa escolhe (Caio, 14/11/2026: "deixe a pessoa escolher a
    janela")."""
    ano_previsto: int | None = None
    """O primeiro ano de `anuais` que é prévia nossa (o IBC-R encadeado), não número do IBGE."""
    marcas: list[LinhaRef] = Field(default_factory=list)
    """Quando o resultado é um nome (a nota CAPAG): o nome de cada valor. A tela escreve o
    nome no lugar do número."""
    periodos: list[PeriodoDaMetrica] = Field(default_factory=list)
    """Só no PIB trimestral dos estados: a mesma métrica em cada trimestre, do mais novo ao
    mais antigo (o primeiro repete `valores`). A tela põe a lista "Trimestre"."""


class HistoricoEstado(Modelo):
    """Uma conta do estado no fim de cada ano (RGF do 3º quadrimestre, RREO do 6º bimestre)."""

    id: str
    titulo: str
    unidade: str
    casas: int = 1
    pontos: dict[int, float]
    """{ano: valor}."""
    fonte: str
    nota: str = ""
    linhas: list[LinhaRef] = Field(default_factory=list)
    """Os limites da lei, quando há."""


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
    compara: bool = True
    """Com a média dos estados ao lado. Não quando as partes mudam de um estado para o outro
    (os produtos e os países das exportações)."""


class ContasEstado(Modelo):
    uf: str
    nome: str
    blocos: list[BlocoDeConta]
    numeros: list[Cartao] = Field(default_factory=list)
    """Os números soltos do estado (investimento % da RCL, dívida com a União…)."""
    historico: list[HistoricoEstado] = Field(default_factory=list)
    """Pessoal, dívida, primário e previdência no fim de cada ano."""
    piramide: Piramide | None = None
    """A pirâmide etária do estado (projeção do IBGE), alguns anos de 2000 a 2070."""
    fonte_piramide: str = ""


class EstadosContas(Modelo):
    """As contas de cada UF, lidas só quando a pessoa abre um estado."""

    id: Literal["estados-contas"] = "estados-contas"
    contas: dict[str, ContasEstado]
    historico_brasil: dict[str, dict[int, float]] = Field(default_factory=dict)
    """{id do histórico: {ano: a soma dos estados}}: a linha "Todos os estados" ao lado."""
    gerado_em: datetime


class Capitais(Modelo):
    """As contas das capitais contra os limites da lei, em Estados › Perto dos limites."""

    nomes: dict[str, str]
    """{sigla da UF: nome da capital}. Brasília fica de fora: o DF não tem relatório municipal."""
    metricas: list[MetricaEstados]
    """Pessoal, dívida e primário, com os valores pela sigla da UF da capital."""


class Estados(Modelo):
    id: Literal["estados"] = "estados"
    titulo: str
    resumo: str
    ufs: list[UF]
    metricas: list[MetricaEstados]
    arquivo_contas: str = ""
    """O JSON com `EstadosContas`, quando houver."""
    subcategorias: list[Subcategoria] = Field(default_factory=list)
    """As partes da tela (`organizacao.PARTES_ESTADOS`): o site monta cada uma sozinha."""
    capitais: Capitais | None = None
    gerado_em: datetime


# ------------------------------------------------------------------ índice


class EstadoFonte(Modelo):
    fonte: str
    ok: bool
    detalhe: str = ""


class ItemSubcategoria(Modelo):
    id: str
    titulo: str


class ItemSecao(Modelo):
    id: str
    titulo: str
    arquivo: str
    subcategorias: list[ItemSubcategoria] = Field(default_factory=list)
    """Para o menu lateral, que não baixa a seção."""
    resumo: str = ""
    """A manchete do assunto, para o cartão da página inicial (que não baixa a seção)."""
    ok: bool
    erro: str = ""
    mantidos: list[str] = Field(default_factory=list)
    """O que veio da rodada anterior porque uma fonte da seção falhou nesta (ids)."""


class Categoria(Modelo):
    """Um grupo de assuntos no menu e na entrada ("Preços, juros e crédito")."""

    id: str
    titulo: str
    secoes: list[str]


class Painel(Modelo):
    gerado_em: datetime
    secoes: list[ItemSecao]
    categorias: list[Categoria] = Field(default_factory=list)
    fontes: list[EstadoFonte] = Field(default_factory=list)


def pontos(serie: list[Ponto], casas: int = 4) -> list[tuple[date, float | None]]:
    return [(d, round(v, casas)) for d, v in serie]
