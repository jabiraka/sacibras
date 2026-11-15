// Espelho de builder/src/sacibras/schema.py. Datas vêm como "AAAA-MM-DD".

export type Periodicidade = "D" | "M" | "T" | "A";
export type Papel = "realizado" | "consenso" | "previsao" | "referencia";
export type Procedencia = "oficial" | "mercado" | "calculado";

export interface Serie {
  id: string;
  nome: string;
  pontos: [string, number | null][];
  papel: Papel;
  tracejado_desde: string | null;
  /** Só no navegador: a casa da paleta (0–5), para a cor seguir o país e não a ordem. */
  cor?: number;
}

export interface Grafico {
  id: string;
  titulo: string;
  subtitulo: string;
  tipo: "linha" | "area" | "barras" | "empilhado" | "degrau" | "curva";
  /** No empilhado: o id da série que é a soma das barras, desenhada como linha por cima. */
  total?: string;
  unidade: string;
  casas: number;
  periodicidade: Periodicidade;
  series: Serie[];
  faixa: { nome: string; pontos: [string, number, number][] } | null;
  intervalos: {
    nome: string;
    serie: string;
    pontos: [string, number, number][];
    /** A parte grossa da barra (a faixa de 50 %), quando há. */
    meio?: [string, number, number][];
    nome_meio?: string;
  }[];
  linhas: { valor: number; rotulo: string }[];
  marcas_y?: { valor: number; rotulo: string }[];
  /** "meses": o eixo conta meses de uma marca (jan/2000 é o mês 0), não datas. */
  eixo?: "tempo" | "meses";
  /** No eixo "meses", o nome do mês zero. */
  marco?: string;
  janela_anos: number | null;
  fonte: string;
  nota: string;
  largura: "meia" | "inteira";
  piramide?: Piramide | null;
  dispersao?: Dispersao | null;
  /** Só na página inicial: o assunto de onde o gráfico veio. */
  secao?: string;
}

/** Um ponto por país: uma métrica em cada eixo (`chave` é o ISO3; o Brasil é BRA). */
export interface Dispersao {
  eixo_x: { nome: string; unidade: string; casas: number };
  eixo_y: { nome: string; unidade: string; casas: number };
  pontos: { chave: string; nome: string; x: number; y: number }[];
  correlacao: number | null;
}

/** Pessoas por sexo e grupo de idade (mil), um ano por linha de `homens`/`mulheres`. */
export interface Piramide {
  grupos: string[];
  anos: number[];
  homens: number[][];
  mulheres: number[][];
  ano_inicial: number;
  ano_contorno: number;
  primeiro_ano_projetado: number;
}

export interface Cartao {
  id: string;
  rotulo: string;
  valor: number;
  unidade: string;
  casas: number;
  referencia: string;
  periodicidade: Periodicidade;
  detalhe: string;
  texto?: string;
  anterior: number | null;
  anterior_rotulo: string;
  fonte: string;
  procedencia: Procedencia;
  mini: [string, number][];
  secao: string;
  meta: { centro: number; inferior: number; superior: number; norma: string } | null;
  ao_vivo: { tipo: "sgs" | "sidra"; codigo: number | null; caminho: string; escala: number } | null;
}

export interface Tabela {
  id: string;
  titulo: string;
  subtitulo: string;
  colunas: string[];
  linhas: { rotulo: string; valores: (number | null)[]; unidade: string; casas: number; fonte: string; textos?: string[] }[];
  fonte: string;
  nota: string;
}

export interface SimuladorDivida {
  ano_inicial: number;
  divida_inicial: number;
  anos: number[];
  juro: number[];
  crescimento: number[];
  inflacao: number[];
  primario: number[];
  focus_divida: (number | null)[];
  realizado: [string, number][];
  fonte: string;
  nota: string;
}

/** Um tipo de compra na reforma do consumo: quanto da alíquota cheia paga e quanto volta. */
export interface TipoDeCompra {
  id: string;
  rotulo: string;
  /** O que entra neste tipo, por extenso (o rótulo é curto, para caber na lista). */
  descricao: string;
  /** % da alíquota cheia (100, 70, 40 ou 0). */
  paga: number;
  /** % devolvido à família de baixa renda. */
  volta_cbs: number;
  volta_ibs: number;
  norma: string;
}

export interface EtapaDaReforma {
  id: string;
  rotulo: string;
  /** Alíquotas cheias, em %; null quando o controle da alíquota decide. */
  cbs: number | null;
  ibs: number | null;
  devolve_ibs: boolean;
  aviso: string;
}

/** Quanto de IBS e CBS vai numa compra: lei lida e contas oficiais; o navegador multiplica. */
export interface SimuladorReforma {
  tipos: TipoDeCompra[];
  etapas: EtapaDaReforma[];
  etapa_inicial: string;
  aliquota: number;
  aliquota_minima: number;
  aliquota_maxima: number;
  /** A parte da alíquota cheia que é IBS, de 0 a 1. */
  parte_do_ibs: number;
  marcas: { valor: number; rotulo: string }[];
  fonte: string;
  nota: string;
  como_ler: string;
}

/** O que o BC estima para 1 pp de Selic; o navegador multiplica pela mudança escolhida. */
export interface SimuladorSelic {
  ano: number;
  focus_selic: number | null;
  focus_ipca: number | null;
  focus_dolar: number | null;
  focus_divida: number | null;
  meta: { centro: number; inferior: number; superior: number; norma: string } | null;
  /** O trimestre zero e os 16 seguintes. */
  trimestres: string[];
  selic_caminho: number[];
  ipca_agregado: number[];
  ipca_desagregado: number[];
  /** As pontas da faixa de 90 % do BC, por trimestre e por 1 pp: menos e mais efeito. */
  ipca_faixa_menor: number[];
  ipca_faixa_maior: number[];
  faixa_do_ipca: string;
  dolar_por_pp: number;
  dolar_por_pp_faixa: [number, number];
  divida_por_pp_de_selic: number;
  divida_por_1_de_dolar: number;
  divida_por_pp_de_precos: number;
  /** PIB de 12 meses, em R$ bilhões. */
  pib_em_reais: number | null;
  /** Quanto o Focus desta época costuma errar o ano seguinte: pp, % e pp do PIB. */
  erro_focus_ipca: number | null;
  erro_focus_dolar: number | null;
  erro_focus_divida: number | null;
  erro_focus_desde: number | null;
  fonte: string;
  nota: string;
  como_ler: string;
}

/** Uma parte do assunto: os ids do que abre junto, numa tela só. */
export interface Subcategoria {
  id: string;
  titulo: string;
  resumo: string;
  cartoes: string[];
  graficos: string[];
  tabelas: string[];
  extras: ("simulador" | "simulador-selic" | "simulador-reforma" | "alertas")[];
  /** Atalhos para partes de outros assuntos ("Veja também"). */
  veja?: Elo[];
}

export interface Elo {
  endereco: string;
  titulo: string;
  resumo: string;
}

export interface Secao {
  id: string;
  titulo: string;
  resumo: string;
  /** Vazia (ou ausente, num JSON antigo): o assunto abre inteiro. */
  subcategorias?: Subcategoria[];
  cartoes: Cartao[];
  graficos: Grafico[];
  tabelas: Tabela[];
  simulador: SimuladorDivida | null;
  simulador_selic?: SimuladorSelic | null;
  simulador_reforma?: SimuladorReforma | null;
  alertas?: Alerta[];
  gerado_em: string;
}

/** Um indicador do painel de alerta: o valor de hoje na régua da própria história. */
export interface Alerta {
  id: string;
  grupo: string;
  nome: string;
  valor: number;
  unidade: string;
  casas: number;
  referencia: string;
  periodicidade: Periodicidade;
  pior_quando: "alto" | "baixo";
  pior_que: number;
  minimo: number;
  maximo: number;
  mediana: number;
  desde: string;
  limite: { valor: number; rotulo: string } | null;
  fonte: string;
  procedencia: Procedencia;
  significa?: string;
  por_que?: string;
  pode_levar?: string;
  ha_um_ano?: number | null;
  ha_um_ano_em?: string | null;
  pior_que_ha_um_ano?: number | null;
}

export interface Pais {
  iso3: string;
  nome: string;
  grupo: "america_latina" | "avancados" | "emergentes" | "agregado";
}

export interface MetricaMundo {
  id: string;
  nome: string;
  descricao: string;
  unidade: string;
  casas: number;
  maior_e_melhor: boolean | null;
  fonte: string;
  anos: number[];
  primeiro_ano_projetado: number | null;
  valores: Record<string, (number | null)[]>;
}

export interface GrupoMundo {
  iso3: string;
  nome: string;
  membros: string[];
}

export interface Mundo {
  id: "mundo";
  titulo: string;
  resumo: string;
  paises: Pais[];
  metricas: MetricaMundo[];
  ano_corrente: number;
  edicao: string;
  grupos: GrupoMundo[];
  nomes: Record<string, string>;
  arquivo_paises: string;
  gerado_em: string;
}

export interface MundoPaises {
  id: "mundo-paises";
  metricas: MetricaMundo[];
  gerado_em: string;
}

export interface UF {
  sigla: string;
  nome: string;
  regiao: "Norte" | "Nordeste" | "Centro-Oeste" | "Sudeste" | "Sul";
}

export interface MetricaEstados {
  id: string;
  nome: string;
  descricao: string;
  unidade: string;
  casas: number;
  referencia: string;
  maior_e_melhor: boolean | null;
  fonte: string;
  valores: Record<string, number | null>;
  brasil: number | null;
  limites: { valor: number; rotulo: string }[];
  /** O assunto da métrica: junta as opções na lista e as colunas na tabela completa. */
  grupo?: string;
  /** Só em previsão: a faixa onde o número oficial costuma cair, por UF. */
  intervalos?: Record<string, [number, number]>;
  /** UFs cujo valor é estimativa por regra nossa. */
  estimados?: string[];
  /** A faixa de erro em palavras. */
  como_ler?: string;
  /** Só no crescimento do PIB: {sigla ou "BR": {ano: índice de volume}}, para escolher a janela. */
  anuais?: Record<string, Record<string, number>>;
  /** O primeiro ano de `anuais` que é prévia (IBC-R), não número do IBGE. */
  ano_previsto?: number | null;
  /** Quando o resultado é um nome (a nota CAPAG): o nome de cada valor. */
  marcas?: { valor: number; rotulo: string }[];
  /** Só no PIB trimestral dos estados: a métrica em cada trimestre, do mais novo ao mais antigo. */
  periodos?: PeriodoDaMetrica[];
}

export interface PeriodoDaMetrica {
  referencia: string;
  valores: Record<string, number | null>;
  brasil: number | null;
  intervalos?: Record<string, [number, number]>;
  /** A frase do período, que vai antes da descrição ("No 2º tri/2026, o PIB do Brasil…"). */
  nota?: string;
}

/** Uma conta do estado no fim de cada ano: {ano: valor}. */
export interface HistoricoEstado {
  id: string;
  titulo: string;
  unidade: string;
  casas: number;
  pontos: Record<string, number>;
  fonte: string;
  nota: string;
  linhas: { valor: number; rotulo: string }[];
}

export interface BlocoDeConta {
  id: string;
  titulo: string;
  descricao: string;
  unidade: string;
  referencia: string;
  fonte: string;
  fatias: { nome: string; valor: number }[];
  total: number | null;
  /** Falso quando as partes mudam de estado para estado (produtos, países): sem médias. */
  compara?: boolean;
}

export interface ContasEstado {
  uf: string;
  nome: string;
  blocos: BlocoDeConta[];
  numeros: Cartao[];
  historico?: HistoricoEstado[];
  piramide?: Piramide | null;
  fonte_piramide?: string;
}

export interface EstadosContas {
  id: "estados-contas";
  contas: Record<string, ContasEstado>;
  /** {id do histórico: {ano: a soma dos estados}}. */
  historico_brasil?: Record<string, Record<string, number>>;
  gerado_em: string;
}

export interface Estados {
  id: "estados";
  titulo: string;
  resumo: string;
  ufs: UF[];
  metricas: MetricaEstados[];
  arquivo_contas: string;
  subcategorias?: Subcategoria[];
  /** As capitais contra os limites da lei (Perto dos limites). */
  capitais?: Capitais | null;
  gerado_em: string;
}

export interface Capitais {
  /** {sigla da UF: nome da capital}. */
  nomes: Record<string, string>;
  metricas: MetricaEstados[];
}

export interface ItemSecao {
  id: string;
  titulo: string;
  arquivo: string;
  resumo: string;
  ok: boolean;
  erro: string;
  subcategorias?: { id: string; titulo: string }[];
  /** O que veio da rodada anterior porque uma fonte da seção falhou nesta (ids). */
  mantidos?: string[];
}

export interface Categoria {
  id: string;
  titulo: string;
  secoes: string[];
}

export interface Painel {
  gerado_em: string;
  secoes: ItemSecao[];
  categorias?: Categoria[];
  fontes: { fonte: string; ok: boolean; detalhe: string }[];
}
