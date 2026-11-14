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
  janela_anos: number | null;
  fonte: string;
  nota: string;
  largura: "meia" | "inteira";
  piramide?: Piramide | null;
  dispersao?: Dispersao | null;
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
  linhas: { rotulo: string; valores: (number | null)[]; unidade: string; casas: number; fonte: string }[];
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

/** Uma parte do assunto: os ids do que abre junto, numa tela só. */
export interface Subcategoria {
  id: string;
  titulo: string;
  resumo: string;
  cartoes: string[];
  graficos: string[];
  tabelas: string[];
  extras: ("simulador" | "alertas")[];
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
}

export interface ContasEstado {
  uf: string;
  nome: string;
  blocos: BlocoDeConta[];
  numeros: Cartao[];
}

export interface EstadosContas {
  id: "estados-contas";
  contas: Record<string, ContasEstado>;
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
  gerado_em: string;
}

export interface ItemSecao {
  id: string;
  titulo: string;
  arquivo: string;
  resumo: string;
  ok: boolean;
  erro: string;
  subcategorias?: { id: string; titulo: string }[];
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
