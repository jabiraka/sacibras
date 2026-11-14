// Peças de comparação usadas em "Brasil no mundo" e em "Estados": a lista suspensa, o
// ranking em pontos (cada linha um ponto na régua, em vez de barra) e o gráfico de duas
// métricas, com um ponto por país ou estado.

import * as Plot from "@observablehq/plot";
import { numero } from "./formato";
import { el } from "./pecas";

// ------------------------------------------------------------------ lista suspensa

export interface Opcao {
  valor: string;
  rotulo: string;
  /** Opções com o mesmo `grupo` vêm juntas, sob o título dele (optgroup). */
  grupo?: string;
}

/** Um rótulo e uma lista suspensa nativa (no celular abre o seletor do sistema). */
export function listaSuspensa(
  id: string,
  rotulo: string,
  opcoes: Opcao[],
  escolhido: string,
  aoMudar: (valor: string) => void,
): { caixa: HTMLElement; trocar: (opcoes: Opcao[], escolhido: string) => void } {
  const caixa = el("label", "escolha-campo");
  caixa.htmlFor = id;
  const nome = el("span", "escolha-rotulo", rotulo);
  const lista = el("select", "escolha");
  lista.id = id;
  const trocar = (novas: Opcao[], valor: string): void => {
    const itens: HTMLElement[] = [];
    let titulo: HTMLOptGroupElement | null = null;
    for (const o of novas) {
      const item = el("option", "", o.rotulo);
      item.value = o.valor;
      if (o.grupo && titulo?.label !== o.grupo) {
        titulo = el("optgroup");
        titulo.label = o.grupo;
        itens.push(titulo);
      }
      if (o.grupo && titulo) titulo.append(item);
      else itens.push(item);
    }
    lista.replaceChildren(...itens);
    lista.value = valor;
  };
  trocar(opcoes, escolhido);
  lista.addEventListener("change", () => aoMudar(lista.value));
  caixa.append(nome, lista);
  return { caixa, trocar };
}

// ------------------------------------------------------------------ ranking em pontos

export type Marca = "comum" | "brasil" | "grupo" | "membro";

export interface LinhaDoRanking {
  chave: string;
  nome: string;
  valor: number;
  marca: Marca;
  posicao: number | null;
  /** Cor da série quando o item está escolhido no gráfico ao lado. */
  cor?: string;
  /** Grupo que abre: o texto do botão e o que fazer no clique. */
  abre?: { aberto: boolean; quantos: number };
  /** Texto que aparece ao passar o dedo/mouse. */
  dica?: string;
  /** Previsão: a faixa de erro (de, até), um traço em tinta neutra com as pontas marcadas. */
  faixa?: [number, number];
  /** Valor estimado por regra, não medido: o ponto sai vazado. */
  estimado?: boolean;
}

export interface Regua {
  min: number;
  max: number;
  /** Traços verticais de referência (limites, meta). */
  marcos?: { valor: number; rotulo: string }[];
}

export function reguaDe(valores: number[], marcos: { valor: number; rotulo: string }[] = []): Regua {
  const todos = [...valores, ...marcos.map((m) => m.valor), 0];
  const min = Math.min(...todos);
  const max = Math.max(...todos);
  const folga = (max - min) * 0.04 || 1;
  return { min: min < 0 ? min - folga : 0, max: max + folga, marcos };
}

function posicaoNaRegua(v: number, r: Regua): { pct: number; fora: "" | "esq" | "dir" } {
  if (v < r.min) return { pct: 0, fora: "esq" };
  if (v > r.max) return { pct: 100, fora: "dir" };
  return { pct: ((v - r.min) / (r.max - r.min || 1)) * 100, fora: "" };
}

/** Uma linha do ranking: posição, nome, a régua com o ponto, e o valor. */
export function linhaDoRanking(
  l: LinhaDoRanking,
  r: Regua,
  casas: number,
  aoTocar?: () => void,
): HTMLElement {
  const linha = el(aoTocar ? "button" : "div", `ponto-linha ${l.marca}`);
  if (linha instanceof HTMLButtonElement) {
    linha.type = "button";
    linha.addEventListener("click", aoTocar ?? (() => undefined));
  }
  if (l.cor) {
    linha.classList.add("escolhido");
    linha.style.setProperty("--cor", l.cor);
  }
  const nome = el("span", "ponto-nome");
  if (l.abre) {
    nome.append(el("span", "abre-seta", l.abre.aberto ? "▾" : "▸"), document.createTextNode(l.nome));
    nome.append(el("span", "abre-conta", ` ${l.abre.quantos}`));
    linha.setAttribute("aria-expanded", String(l.abre.aberto));
  } else {
    nome.textContent = l.nome;
  }
  const trilho = el("span", "ponto-trilho");
  const zero = el("i", "ponto-zero");
  zero.style.left = `${posicaoNaRegua(0, r).pct}%`;
  trilho.append(zero);
  for (const m of r.marcos ?? []) {
    const traco = el("i", "ponto-marco");
    traco.style.left = `${posicaoNaRegua(m.valor, r).pct}%`;
    trilho.append(traco);
  }
  if (l.faixa) {
    const de = posicaoNaRegua(l.faixa[0], r).pct;
    const ate = posicaoNaRegua(l.faixa[1], r).pct;
    const faixa = el("i", "ponto-faixa");
    faixa.style.left = `${de}%`;
    faixa.style.width = `${ate - de}%`;
    trilho.append(faixa);
  }
  const lugar = posicaoNaRegua(l.valor, r);
  const ponto = el("i", `ponto ${lugar.fora ? `fora-${lugar.fora}` : ""}${l.estimado ? " estimado" : ""}`);
  ponto.style.left = `${lugar.pct}%`;
  trilho.append(ponto);
  linha.append(
    el("span", "ponto-pos", l.posicao === null ? "" : String(l.posicao)),
    nome,
    trilho,
    el("span", "ponto-valor", numero(l.valor, casas)),
  );
  linha.title =
    l.dica ??
    `${l.nome}: ${numero(l.valor, casas)}` +
      (l.faixa ? ` (de ${numero(l.faixa[0], casas)} a ${numero(l.faixa[1], casas)})` : "") +
      (l.estimado ? ", estimado pela região" : "");
  return linha;
}

// ------------------------------------------------------------------ duas métricas

export interface PontoDisperso {
  chave: string;
  nome: string;
  x: number;
  y: number;
  marca: Marca;
  cor?: string;
  rotulo?: boolean;
}

export interface Eixo {
  nome: string;
  unidade: string;
  casas: number;
}

/** Os pontos muito longe dos outros (fora de 3 intervalos interquartis), num eixo. */
function extremos(valores: number[]): (v: number) => boolean {
  const ordenados = [...valores].sort((a, b) => a - b);
  const q = (p: number): number => ordenados[Math.floor(p * (ordenados.length - 1))] ?? 0;
  const iqr = q(0.75) - q(0.25);
  if (ordenados.length < 8 || iqr <= 0) return () => false;
  return (v) => v > q(0.75) + 3 * iqr || v < q(0.25) - 3 * iqr;
}

/** Um ponto por país (ou estado): uma métrica no eixo horizontal, outra no vertical.
 *  Sem `comExtremos`, quem fica muito longe dos outros sai do desenho (para não esmagar o
 *  resto num canto) e volta na lista devolvida, para a tela avisar. */
export function desenharDispersao(
  alvo: HTMLElement,
  todosOsPontos: PontoDisperso[],
  ex: Eixo,
  ey: Eixo,
  aoTocar?: (chave: string) => void,
  comExtremos = false,
): PontoDisperso[] {
  const longeX = extremos(todosOsPontos.map((p) => p.x));
  const longeY = extremos(todosOsPontos.map((p) => p.y));
  const fora = comExtremos
    ? []
    : todosOsPontos.filter((p) => p.marca !== "brasil" && (longeX(p.x) || longeY(p.y)));
  const pontos = todosOsPontos.filter((p) => !fora.includes(p));
  const largura = Math.max(260, Math.floor(alvo.clientWidth));
  const estreito = largura < 480;
  const css = getComputedStyle(document.documentElement);
  const v = (nome: string): string => css.getPropertyValue(nome).trim();
  const corDe = (p: PontoDisperso): string =>
    p.cor ?? (p.marca === "brasil" ? v("--verde") : p.marca === "grupo" ? v("--azul") : v("--eixo"));
  // Os de fundo primeiro, o Brasil e os escolhidos por cima.
  const ordem: Record<Marca, number> = { membro: 0, comum: 1, grupo: 2, brasil: 3 };
  const ordenados = [...pontos].sort(
    (a, b) => ordem[a.marca] + (a.cor ? 2 : 0) - (ordem[b.marca] + (b.cor ? 2 : 0)),
  );
  const rotulados = ordenados.filter((p) => p.rotulo);
  const zeroX = Math.min(...pontos.map((p) => p.x)) < 0;
  const zeroY = Math.min(...pontos.map((p) => p.y)) < 0;
  const grafico = Plot.plot({
    width: largura,
    height: Math.round(estreito ? largura * 0.95 : Math.min(460, largura * 0.62)),
    marginLeft: 44,
    marginBottom: 40,
    marginRight: 16,
    style: { background: "transparent", color: v("--tinta-2"), fontSize: "11px", fontFamily: "inherit" },
    // Tamanho e opacidade dos pontos são valores em si, não escalas.
    r: { type: "identity" },
    opacity: { type: "identity" },
    x: {
      label: `${ex.nome} (${ex.unidade}) →`,
      labelAnchor: "right",
      grid: true,
      ticks: estreito ? 4 : 7,
      tickFormat: (d: number) => numero(d, Math.abs(d - Math.round(d)) < 1e-9 ? 0 : 1),
      nice: true,
    },
    y: {
      label: `↑ ${ey.nome} (${ey.unidade})`,
      labelAnchor: "top",
      grid: true,
      ticks: 5,
      tickFormat: (d: number) => numero(d, Math.abs(d - Math.round(d)) < 1e-9 ? 0 : 1),
      nice: true,
    },
    marks: [
      zeroX ? Plot.ruleX([0], { stroke: v("--eixo") }) : null,
      zeroY ? Plot.ruleY([0], { stroke: v("--eixo") }) : null,
      Plot.dot(ordenados, {
        x: "x",
        y: "y",
        r: (p: PontoDisperso) => (p.marca === "membro" ? 3.5 : p.marca === "brasil" || p.cor ? 6.5 : 5),
        fill: corDe,
        fillOpacity: (p: PontoDisperso) => (p.marca === "membro" ? 0.55 : 1),
        stroke: v("--superficie"),
        strokeWidth: 1.5,
        symbol: (p: PontoDisperso) => (p.marca === "grupo" ? "diamond" : "circle"),
      }),
      Plot.text(rotulados, {
        x: "x",
        y: "y",
        text: "nome",
        dy: -12,
        fontSize: estreito ? 10 : 11,
        fill: v("--tinta"),
        fontWeight: 600,
        stroke: v("--superficie"),
        strokeWidth: 3,
        paintOrder: "stroke",
      }),
      Plot.tip(
        ordenados,
        Plot.pointer({
          x: "x",
          y: "y",
          title: (p: PontoDisperso) =>
            `${p.nome}\n${ex.nome}: ${numero(p.x, ex.casas)} ${ex.unidade}\n${ey.nome}: ${numero(p.y, ey.casas)} ${ey.unidade}`,
          fontSize: 12,
        }),
      ),
    ],
  });
  if (aoTocar) {
    grafico.addEventListener("click", () => {
      const escolhido = (grafico as unknown as { value?: PontoDisperso }).value;
      if (escolhido) aoTocar(escolhido.chave);
    });
  }
  grafico.setAttribute("role", "img");
  grafico.setAttribute("aria-label", `${ey.nome} contra ${ex.nome}, um ponto por item. A tabela traz os valores.`);
  alvo.replaceChildren(grafico);
  return fora;
}
