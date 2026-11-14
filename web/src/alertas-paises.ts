// O painel de alerta contra outros países (Caio, 14/11/2026: "coloque também a comparação com
// outros países, pra ver como estamos, mas principalmente com países parecidos (emergentes,
// América Latina)").
//
// Os números vêm dos mesmos arquivos de "Brasil no mundo" (FMI e BIS, todos os países): cada
// indicador do painel que tem par internacional é posto, para o Brasil e para os outros, na
// mesma fonte e no mesmo ano. O conceito às vezes difere do número brasileiro do painel (a
// dívida do FMI é maior que a DBGG do Banco Central): a linha diz isso.

import { numero } from "./formato";
import type { Alerta, MetricaMundo, Mundo, MundoPaises } from "./tipos";

export interface Par {
  /** A métrica de Brasil no mundo; "juros" é primário menos nominal (os juros líquidos). */
  metrica: string;
  nome: string;
  pior_quando: "alto" | "baixo";
  unidade?: string;
  /** O que difere do número do painel, numa frase. */
  conceito: string;
}

/** Os indicadores do painel que têm par internacional, pelo id do alerta. */
export const PARES: Record<string, Par> = {
  dbgg: {
    metrica: "divida",
    nome: "Dívida bruta do governo geral",
    pior_quando: "alto",
    conceito:
      "Conceito do FMI, que soma os títulos do Tesouro na carteira do Banco Central: para o " +
      "Brasil dá mais que a DBGG do painel, mas é a mesma régua para todos os países.",
  },
  primario: {
    metrica: "primario",
    nome: "Resultado primário",
    pior_quando: "baixo",
    conceito:
      "Governo geral no conceito do FMI (receitas menos despesas, sem estatais nem o Banco " +
      "Central); o número do painel é o do Banco Central, para o setor público consolidado.",
  },
  juros: {
    metrica: "juros",
    nome: "Juros líquidos do governo",
    pior_quando: "alto",
    unidade: "% do PIB",
    conceito:
      "Primário menos nominal do governo geral, pelo FMI: os juros que o governo paga, " +
      "descontados os que recebe.",
  },
  nominal: {
    metrica: "nominal",
    nome: "Resultado nominal",
    pior_quando: "baixo",
    conceito: "Governo geral no conceito do FMI; o número do painel é o do Banco Central.",
  },
  "conta-corrente": {
    metrica: "conta_corrente",
    nome: "Saldo em conta corrente",
    pior_quando: "baixo",
    conceito: "Pelo FMI, no ano; o número do painel é o do Banco Central em 12 meses.",
  },
  ipca: {
    metrica: "inflacao",
    nome: "Inflação ao consumidor",
    pior_quando: "alto",
    conceito: "Média do ano contra a média do ano anterior (FMI); o painel usa o IPCA em 12 meses.",
  },
};

/** Números que não estão no painel, mas ajudam a ver como o Brasil está entre os parecidos. */
export const EXTRAS: (Par & { id: string; explica: string })[] = [
  {
    id: "juro-real",
    metrica: "juro_real",
    nome: "Juro real básico",
    pior_quando: "alto",
    conceito: "Juro do banco central menos a inflação dos 12 meses anteriores (BIS), no último mês.",
    explica: "Juro real alto encarece a dívida do governo, o crédito e o investimento.",
  },
  {
    id: "crescimento",
    metrica: "pib",
    nome: "Crescimento do PIB",
    pior_quando: "baixo",
    conceito: "Variação real do PIB no ano (FMI).",
    explica: "Crescer pouco torna a dívida mais pesada e o emprego mais difícil.",
  },
  {
    id: "desemprego",
    metrica: "desemprego",
    nome: "Desemprego",
    pior_quando: "alto",
    conceito: "Taxa de desemprego, média do ano (FMI). Nem todo país informa.",
    explica: "Desemprego alto pesa na renda das famílias e no pagamento das dívidas.",
  },
];

export interface Dados {
  m: Mundo;
  todos: MundoPaises;
}

let pedido: Promise<Dados | null> | null = null;

/** Lê "Brasil no mundo" e o arquivo com todos os países (uma vez só). */
export function carregarPaises(): Promise<Dados | null> {
  pedido ??= Promise.all([
    fetch("data/mundo.json", { cache: "no-cache" }).then((r) => (r.ok ? (r.json() as Promise<Mundo>) : null)),
    fetch("data/mundo-paises.json", { cache: "no-cache" }).then((r) =>
      r.ok ? (r.json() as Promise<MundoPaises>) : null,
    ),
  ])
    .then(([m, todos]) => (m && todos ? { m, todos } : null))
    .catch(() => null);
  return pedido;
}

/** Os grupos que se comparam, na ordem da lista: os parecidos primeiro. */
export function opcoesDeGrupo(d: Dados): { valor: string; rotulo: string }[] {
  const nome = (iso: string): string => d.m.grupos.find((g) => g.iso3 === iso)?.nome ?? iso;
  const tamanho = (iso: string): number => d.m.grupos.find((g) => g.iso3 === iso)?.membros.length ?? 0;
  const principais = d.m.paises.filter((p) => p.grupo !== "agregado").length;
  return [
    ...["G200", "G205"].filter((g) => tamanho(g)).map((g) => ({ valor: g, rotulo: `${nome(g)} (${tamanho(g)})` })),
    { valor: "principais", rotulo: `Os ${principais} países de Brasil no mundo` },
    ...["G110", "G001"].filter((g) => tamanho(g)).map((g) => ({ valor: g, rotulo: `${nome(g)} (${tamanho(g)})` })),
  ];
}

/** "dos 153 emergentes", "dos 32 países da América Latina e Caribe". */
export function dosPaises(d: Dados, grupo: string, n: number): string {
  if (grupo === "principais") return `dos ${n} outros países de Brasil no mundo`;
  const nome = d.m.grupos.find((x) => x.iso3 === grupo)?.nome ?? grupo;
  if (grupo === "G200") return `dos ${n} outros emergentes`;
  if (grupo === "G110") return `dos ${n} avançados`;
  if (grupo === "G001") return `dos ${n} outros países do mundo`;
  return `dos ${n} outros países de ${nome}`;
}

function membros(d: Dados, grupo: string): string[] {
  if (grupo === "principais") return d.m.paises.filter((p) => p.grupo !== "agregado").map((p) => p.iso3);
  return d.m.grupos.find((g) => g.iso3 === grupo)?.membros ?? [];
}

function metricaDe(d: Dados, id: string): MetricaMundo | undefined {
  return d.todos.metricas.find((x) => x.id === id);
}

/** O último ano com dado realizado (o FMI traz o ano corrente como projeção). */
function anoDe(mt: MetricaMundo): number {
  const ultimo = Math.max(...mt.anos);
  return mt.primeiro_ano_projetado ? Math.min(ultimo, mt.primeiro_ano_projetado - 1) : ultimo;
}

function valorDe(d: Dados, metrica: string, iso: string, ano: number): number | null {
  if (metrica === "juros") {
    const p = valorDe(d, "primario", iso, ano);
    const n = valorDe(d, "nominal", iso, ano);
    return p === null || n === null ? null : p - n;
  }
  const mt = metricaDe(d, metrica);
  const i = mt ? mt.anos.indexOf(ano) : -1;
  return i < 0 ? null : (mt?.valores[iso]?.[i] ?? null);
}

function mediana(valores: number[]): number {
  const v = [...valores].sort((a, b) => a - b);
  const meio = Math.floor(v.length / 2);
  return v.length % 2 ? (v[meio] ?? 0) : ((v[meio - 1] ?? 0) + (v[meio] ?? 0)) / 2;
}

export interface Comparacao {
  ano: number;
  fonte: string;
  brasil: number;
  /** % dos países do grupo (sem o Brasil) em situação melhor que a do Brasil. */
  pior_que: number;
  n: number;
  mediana: number;
  valores: number[];
  /** Mediana dos dois grupos parecidos, para a frase. */
  latina: number | null;
  emergentes: number | null;
  /** Os vizinhos de "Brasil no mundo" (América Latina e emergentes), com valor. */
  parecidos: { nome: string; valor: number }[];
}

export function comparar(d: Dados, par: Par, grupo: string): Comparacao | null {
  const base = metricaDe(d, par.metrica === "juros" ? "primario" : par.metrica);
  if (!base) return null;
  const ano = anoDe(base);
  const brasil = valorDe(d, par.metrica, "BRA", ano);
  if (brasil === null) return null;
  const dos = (g: string): number[] =>
    membros(d, g)
      .filter((iso) => iso !== "BRA")
      .map((iso) => valorDe(d, par.metrica, iso, ano))
      .filter((v): v is number => v !== null);
  const valores = dos(grupo);
  if (valores.length < 3) return null;
  const melhores = valores.filter((v) => (par.pior_quando === "alto" ? v < brasil : v > brasil)).length;
  const latina = dos("G205");
  const emergentes = dos("G200");
  const parecidos = d.m.paises
    .filter((p) => p.iso3 !== "BRA" && (p.grupo === "america_latina" || p.grupo === "emergentes"))
    .map((p) => ({ nome: p.nome, valor: valorDe(d, par.metrica, p.iso3, ano) }))
    .filter((x): x is { nome: string; valor: number } => x.valor !== null);
  return {
    ano,
    fonte: par.metrica === "juros" ? (metricaDe(d, "primario")?.fonte ?? "") : base.fonte,
    brasil,
    pior_que: (melhores / valores.length) * 100,
    n: valores.length,
    mediana: mediana(valores),
    valores,
    latina: latina.length ? mediana(latina) : null,
    emergentes: emergentes.length ? mediana(emergentes) : null,
    parecidos,
  };
}

/** "México 58,1 · Chile 41,7 · …", para a linha aberta. */
export function listaDeParecidos(c: Comparacao, casas: number): string {
  return c.parecidos.map((p) => `${p.nome} ${numero(p.valor, casas)}`).join(" · ");
}

/** Os alertas sem par internacional, para dizer o que fica de fora. */
export function semPar(alertas: Alerta[]): Alerta[] {
  return alertas.filter((a) => !PARES[a.id]);
}
