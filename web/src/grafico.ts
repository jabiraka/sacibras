// Um renderizador só para todos os gráficos: desenha o que o builder declarou.
// Regras da casa: um eixo só, linha de 2 px, grade discreta, legenda quando há duas séries
// ou mais, tabela, CSV e PNG sempre à mão, consenso e previsão tracejados.

import { fonteComEnderecos } from "./fontes";
import * as Plot from "@observablehq/plot";
import { comUnidade, data, eixo, mesCurto, numero, periodo, unidadeCurta } from "./formato";
import type { Grafico, Serie } from "./tipos";

interface Linha {
  t: Date;
  iso: string;
  v: number;
  serie: string;
}

interface Tema {
  series: string[];
  tinta: string;
  tinta2: string;
  tinta3: string;
  fio: string;
  eixo: string;
  superficie: string;
  faixa: string;
}

const DIA = 86400000;

/** No eixo "meses", o mês k desde a marca (jan/2000 é o 0; o builder escreve assim). */
function mesRelativo(iso: string): number {
  const d = data(iso);
  return (d.getUTCFullYear() - 2000) * 12 + d.getUTCMonth();
}

/** O rótulo de um ponto: o período, ou "mês k" quando o eixo conta meses de uma marca. */
function rotuloX(g: Grafico, iso: string): string {
  if (g.eixo !== "meses") return periodo(iso, g.periodicidade);
  const k = mesRelativo(iso);
  if (k === 0) return g.marco || "mês 0";
  return k > 0 ? `${k} ${k === 1 ? "mês" : "meses"} depois` : `${-k} ${k === -1 ? "mês" : "meses"} antes`;
}

/** Marcas do eixo "meses": de 6 em 6 ou de 12 em 12, sempre com o zero. */
function marcasDeMeses(xMin: number, xMax: number, quantas: number): Date[] {
  const k0 = mesRelativo(new Date(xMin).toISOString().slice(0, 10));
  const k1 = mesRelativo(new Date(xMax).toISOString().slice(0, 10));
  const passo = [3, 6, 12, 24].find((p) => (k1 - k0) / p <= quantas) ?? 24;
  const marcas: Date[] = [];
  for (let k = Math.ceil(k0 / passo) * passo; k <= k1; k += passo) {
    marcas.push(new Date(Date.UTC(2000 + Math.floor(k / 12), ((k % 12) + 12) % 12, 1)));
  }
  return marcas;
}

export function tema(): Tema {
  const css = getComputedStyle(document.documentElement);
  const v = (nome: string) => css.getPropertyValue(nome).trim();
  return {
    series: [1, 2, 3, 4, 5, 6].map((i) => v(`--serie-${i}`)),
    tinta: v("--tinta"),
    tinta2: v("--tinta-2"),
    tinta3: v("--tinta-3"),
    fio: v("--fio"),
    eixo: v("--eixo"),
    superficie: v("--superficie"),
    faixa: v("--faixa"),
  };
}

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  classe = "",
  texto = "",
): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (classe) e.className = classe;
  if (texto) e.textContent = texto;
  return e;
}

/** Séries com `tracejado_desde` viram duas: a realizada e a projetada (mesma cor). */
interface Traco {
  serie: Serie;
  indice: number;
  linhas: Linha[];
  tracejado: boolean;
}

function tracos(g: Grafico, desde: number): Traco[] {
  const saida: Traco[] = [];
  g.series.forEach((serie, indice) => {
    const linhas: Linha[] = [];
    for (const [iso, v] of serie.pontos) {
      if (v === null) continue;
      const t = data(iso);
      if (t.getTime() < desde) continue;
      linhas.push({ t, iso, v, serie: serie.id });
    }
    const corte = serie.tracejado_desde ? data(serie.tracejado_desde).getTime() : null;
    if (corte === null) {
      saida.push({ serie, indice, linhas, tracejado: serie.papel !== "realizado" });
      return;
    }
    const antes = linhas.filter((l) => l.t.getTime() < corte);
    const depois = linhas.filter((l) => l.t.getTime() >= corte);
    const ponte = antes[antes.length - 1];
    if (antes.length) saida.push({ serie, indice, linhas: antes, tracejado: false });
    if (depois.length) {
      saida.push({ serie, indice, linhas: ponte ? [ponte, ...depois] : depois, tracejado: true });
    }
  });
  return saida;
}

/** Anos de projeção à frente do último ponto realizado (o trecho tracejado mais longo). */
function anosProjetados(g: Grafico): number {
  let maior = 0;
  for (const s of g.series) {
    if (!s.tracejado_desde) continue;
    const corte = data(s.tracejado_desde).getTime();
    const fim = Math.max(...s.pontos.filter((p) => p[1] !== null).map(([iso]) => data(iso).getTime()));
    maior = Math.max(maior, (fim - corte) / (365.25 * DIA));
  }
  return maior;
}

function janelas(g: Grafico): { rotulo: string; anos: number | null }[] {
  if (g.tipo === "curva" || g.eixo === "meses") return [];
  // Projeção longa (a da população vai até 2070): o gráfico é a trajetória inteira, e uma
  // janela contada do fim mostraria só o futuro.
  if (anosProjetados(g) > 10) return [];
  let min = Infinity;
  let max = -Infinity;
  for (const s of g.series) {
    for (const [iso, v] of s.pontos) {
      if (v === null) continue;
      const t = data(iso).getTime();
      if (t < min) min = t;
      if (t > max) max = t;
    }
  }
  const anos = (max - min) / (365.25 * DIA);
  const candidatas: [string, number][] =
    g.periodicidade === "D"
      ? [
          ["3m", 0.25],
          ["1a", 1],
          ["5a", 5],
          ["10a", 10],
        ]
      : [
          ["2a", 2],
          ["5a", 5],
          ["10a", 10],
          ["20a", 20],
        ];
  const opcoes: { rotulo: string; anos: number | null }[] = candidatas
    .filter(([, a]) => a < anos * 0.9)
    .map(([rotulo, a]) => ({ rotulo, anos: a }));
  if (opcoes.length) opcoes.push({ rotulo: "máx", anos: null });
  return opcoes;
}

function fimDosDados(g: Grafico): number {
  let max = -Infinity;
  for (const s of g.series) {
    if (s.papel !== "realizado") continue;
    for (const [iso, v] of s.pontos) if (v !== null) max = Math.max(max, data(iso).getTime());
  }
  if (max === -Infinity) max = Date.now();
  return max;
}

/** As datas rotuladas no eixo do tempo: anos cheios, meses cheios ou dias, conforme o vão. */
function marcasDoEixo(xMin: number, xMax: number, quantas: number): Date[] {
  const dias = (xMax - xMin) / DIA;
  const inicio = new Date(xMin);
  const marcas: Date[] = [];
  if (dias > 800) {
    const anos = dias / 365.25;
    const passo = [1, 2, 5, 10, 20].find((p) => anos / p <= quantas) ?? 20;
    const primeiro = Math.ceil((inicio.getUTCFullYear() + (xMin > Date.UTC(inicio.getUTCFullYear(), 0, 1) ? 1 : 0)) / passo) * passo;
    for (let a = primeiro; Date.UTC(a, 0, 1) <= xMax; a += passo) marcas.push(new Date(Date.UTC(a, 0, 1)));
    return marcas;
  }
  if (dias > 100) {
    const meses = dias / 30.44;
    const passo = [1, 2, 3, 4, 6, 12].find((p) => meses / p <= quantas) ?? 12;
    let ano = inicio.getUTCFullYear();
    let mes = Math.ceil((inicio.getUTCMonth() + (inicio.getUTCDate() > 1 ? 1 : 0)) / passo) * passo;
    for (;;) {
      const t = Date.UTC(ano, mes, 1);
      if (t > xMax) break;
      if (t >= xMin) marcas.push(new Date(t));
      mes += passo;
      if (mes >= 12) {
        ano += Math.floor(mes / 12);
        mes %= 12;
      }
    }
    return marcas;
  }
  const passo = Math.max(1, Math.ceil(dias / quantas));
  for (let t = Math.ceil(xMin / DIA) * DIA; t <= xMax; t += passo * DIA) marcas.push(new Date(t));
  return marcas;
}

function passoDaBarra(p: Grafico["periodicidade"]): "day" | "month" | "quarter" | "year" {
  return p === "A" ? "year" : p === "T" ? "quarter" : p === "M" ? "month" : "day";
}

export function montarGrafico(g: Grafico): HTMLElement {
  const artigo = el("article", `grafico ${g.largura === "inteira" ? "inteira" : ""}`);
  artigo.id = `g-${g.id}`;

  const cabeca = el("header", "grafico-cabeca");
  const titulos = el("div");
  titulos.append(el("h3", "", g.titulo));
  if (g.manchete) titulos.append(el("p", "grafico-manchete", g.manchete));
  const sub = [g.subtitulo, g.unidade].filter(Boolean).join(" · ");
  titulos.append(el("p", "sub", sub));
  cabeca.append(titulos);

  const opcoes = janelas(g);
  let anosAbertos: number | null = g.janela_anos;
  if (anosAbertos !== null && !opcoes.some((o) => o.anos === anosAbertos)) {
    // A janela pedida pelo builder não está entre os botões: abre a mais próxima, por cima.
    const maior = opcoes.find((o) => o.anos !== null && o.anos >= (anosAbertos ?? 0));
    anosAbertos = maior ? maior.anos : null;
  }
  const grupo = el("div", "janelas");
  grupo.setAttribute("role", "group");
  grupo.setAttribute("aria-label", "Período do gráfico");
  const botoes: HTMLButtonElement[] = [];
  for (const o of opcoes) {
    const b = el("button", "", o.rotulo);
    b.type = "button";
    b.setAttribute("aria-pressed", String(o.anos === anosAbertos));
    b.addEventListener("click", () => {
      anosAbertos = o.anos;
      botoes.forEach((x, i) => x.setAttribute("aria-pressed", String(opcoes[i]?.anos === o.anos)));
      desenhar();
    });
    botoes.push(b);
    grupo.append(b);
  }
  if (opcoes.length) cabeca.append(grupo);
  artigo.append(cabeca);

  const legenda = el("div", "legenda");
  artigo.append(legenda);

  const tela = el("div", "tela");
  const dica = el("div", "dica");
  dica.hidden = true;
  artigo.append(tela);

  const pe = el("footer", "grafico-pe");
  pe.append(el("span", "fonte", `Fonte: ${g.fonte}`));
  const acoes = el("span", "acoes");
  const verTabela = el("button", "", "Tabela");
  verTabela.type = "button";
  verTabela.setAttribute("aria-expanded", "false");
  const csv = el("button", "", "CSV");
  csv.type = "button";
  // A imagem do gráfico, com título, unidade, legenda e fonte escritos nela (15/11/2026),
  // para baixar em PNG ou copiar e colar (16/11/2026).
  const imagem = botoesDaImagem(() => {
    const t = tema();
    const cor = (i: number) => t.series[(g.series[i]?.cor ?? i) % t.series.length] ?? t.tinta;
    return {
      id: g.id,
      titulo: g.titulo,
      sub: [g.subtitulo, g.unidade].filter(Boolean).join(" · "),
      fonte: fonteComEnderecos(`Fonte: ${g.fonte}`),
      legenda: itensDaLegenda(g, cor),
      svg: tela.querySelector("svg"),
    };
  });
  // Dado privado cujos termos vedam reproduzir (licencas.py): fica na tela, sem download.
  if (g.sem_download) acoes.append(verTabela);
  else acoes.append(verTabela, csv, ...imagem);
  pe.append(acoes);
  artigo.append(pe);
  if (g.nota) artigo.append(el("p", "nota", g.nota));
  if (g.sem_download) artigo.append(el("p", "nota", g.sem_download));

  const caixaTabela = el("div", "tabela-rolavel");
  caixaTabela.hidden = true;
  artigo.append(caixaTabela);
  verTabela.addEventListener("click", () => {
    if (!caixaTabela.firstChild) caixaTabela.append(tabelaDoGrafico(g));
    caixaTabela.hidden = !caixaTabela.hidden;
    verTabela.setAttribute("aria-expanded", String(!caixaTabela.hidden));
  });
  csv.addEventListener("click", () => baixarCsv(g));

  let jaEntrou = false;

  function desenhar(): void {
    if (jaEntrou && !artigo.isConnected) {
      // O gráfico saiu da página (o comparador de países troca o dele): soltar o ouvinte.
      document.removeEventListener("tema", desenhar);
      return;
    }
    jaEntrou ||= artigo.isConnected;
    const largura = Math.max(280, Math.floor(tela.clientWidth || artigo.clientWidth || 600));
    const t = tema();
    const fim = fimDosDados(g);
    const desde = anosAbertos === null ? -Infinity : fim - anosAbertos * 365.25 * DIA;
    const ts = tracos(g, desde);
    const todas = ts.flatMap((x) => x.linhas);
    if (!todas.length) {
      tela.replaceChildren(el("p", "vazio", "Sem dados nesta janela."));
      return;
    }
    // A cor segue a entidade: quem monta o gráfico pode fixar a casa da paleta (`cor`).
    // No empilhado, a série `total` (a soma das barras) é uma linha em tinta neutra, por cima.
    const cor = (i: number) =>
      g.total && g.series[i]?.id === g.total
        ? t.tinta
        : (t.series[(g.series[i]?.cor ?? i) % t.series.length] ?? t.tinta);
    const marcas: Plot.Markish[] = [];
    const empilhado = g.tipo === "empilhado";
    const barras = g.tipo === "barras" || empilhado;

    if (g.faixa) {
      const faixa = g.faixa.pontos
        .map(([iso, a, b]) => ({ t: data(iso), a, b }))
        .filter((p) => p.t.getTime() >= desde);
      marcas.push(
        Plot.areaY(faixa, { x: "t", y1: "a", y2: "b", fill: t.faixa, fillOpacity: 0.22 }),
      );
    }
    const xMin = Math.min(...todas.map((l) => l.t.getTime()));
    const xMax = Math.max(...todas.map((l) => l.t.getTime()));
    // Barras de erro (Caio, 14/11/2026: "não gostei da barra azul"): um traço fino em tinta
    // neutra, com as pontas marcadas, e a parte do meio (50 %) mais grossa quando há.
    const msPorPx = (xMax - xMin) / Math.max(1, largura - 60);
    for (const intervalo of g.intervalos ?? []) {
      const pontos = intervalo.pontos
        .map(([iso, a, b]) => ({ t: data(iso), a, b }))
        .filter((p) => p.t.getTime() >= desde);
      const ponta = (campo: "a" | "b") =>
        Plot.ruleY(pontos, {
          y: campo,
          x1: (p: { t: Date }) => new Date(p.t.getTime() - 5 * msPorPx),
          x2: (p: { t: Date }) => new Date(p.t.getTime() + 5 * msPorPx),
          stroke: t.tinta2,
          strokeWidth: 1.5,
        });
      const meio = (intervalo.meio ?? [])
        .map(([iso, a, b]) => ({ t: data(iso), a, b }))
        .filter((p) => p.t.getTime() >= desde);
      if (meio.length) {
        marcas.push(
          Plot.ruleX(meio, {
            x: "t",
            y1: "a",
            y2: "b",
            stroke: t.tinta,
            strokeOpacity: 0.16,
            strokeWidth: 9,
            strokeLinecap: "round",
          }),
        );
      }
      marcas.push(
        Plot.ruleX(pontos, { x: "t", y1: "a", y2: "b", stroke: t.tinta2, strokeWidth: 1.5 }),
        ponta("a"),
        ponta("b"),
      );
    }
    // A linha de referência (meta, média, limite) vai pontilhada e o nome dela fica na
    // legenda: escrito no desenho, ele se misturava com as séries e cortava no celular
    // (Caio, 14/11/2026).
    if (g.eixo === "meses") {
      // O zero (o mês do primeiro corte) marcado como a linha de referência.
      marcas.push(
        Plot.ruleX([new Date(Date.UTC(2000, 0, 1))], {
          stroke: t.tinta2,
          strokeDasharray: "2,4",
          strokeWidth: 1.2,
        }),
      );
    }
    for (const linha of g.linhas) {
      marcas.push(
        Plot.ruleY([linha.valor], { stroke: t.tinta2, strokeDasharray: "2,4", strokeWidth: 1.2 }),
      );
    }

    if (barras) {
      const passo = passoDaBarra(g.periodicidade);
      const quantas = new Set(todas.map((l) => l.iso)).size;
      const faixaPx = (largura - 60) / Math.max(1, quantas);
      const folga = Math.max(0.5, (faixaPx - 24) / 2);
      const dados = empilhado
        ? todas.filter((l) => l.serie !== g.total)
        : (ts[0]?.linhas ?? []);
      marcas.push(
        Plot.rectY(dados, {
          x: "t",
          y: "v",
          interval: passo,
          fill: (d: Linha) => cor(g.series.findIndex((s) => s.id === d.serie)),
          insetLeft: folga,
          insetRight: folga,
          rx: faixaPx > 8 ? 2 : 0,
        }),
      );
      // Uma segunda série num gráfico de barras simples entra como linha (ex.: a taxa em
      // 12 meses por cima da variação mensal).
      if (!empilhado) {
        for (const x of ts.slice(1)) {
          marcas.push(
            Plot.lineY(x.linhas, {
              x: "t",
              y: "v",
              stroke: cor(x.indice),
              strokeWidth: 2,
              strokeDasharray: x.tracejado ? "5,4" : undefined,
            }),
          );
        }
      }
      marcas.push(Plot.ruleY([0], { stroke: t.eixo }));
      if (empilhado && g.total) {
        for (const x of ts.filter((x) => x.serie.id === g.total)) {
          marcas.push(
            Plot.lineY(x.linhas, {
              x: "t",
              y: "v",
              stroke: t.tinta,
              strokeWidth: 2,
              strokeLinejoin: "round",
              strokeLinecap: "round",
            }),
          );
        }
      }
    } else {
      const vMin = Math.min(...todas.map((l) => l.v));
      const vMax = Math.max(...todas.map((l) => l.v));
      if (vMin < 0 && vMax > 0) marcas.push(Plot.ruleY([0], { stroke: t.eixo }));
      for (const x of ts) {
        const opc = {
          x: "t",
          y: "v",
          stroke: cor(x.indice),
          strokeWidth: 2,
          strokeLinejoin: "round" as const,
          strokeLinecap: "round" as const,
          strokeDasharray: x.tracejado ? "5,4" : undefined,
          curve: g.tipo === "degrau" ? ("step-after" as const) : ("linear" as const),
        };
        if (g.tipo === "area" && !x.tracejado) {
          marcas.push(
            Plot.areaY(x.linhas, { x: "t", y: "v", fill: cor(x.indice), fillOpacity: 0.1 }),
          );
        }
        marcas.push(Plot.lineY(x.linhas, opc));
        if (g.tipo === "curva") {
          marcas.push(
            Plot.dot(x.linhas, {
              x: "t",
              y: "v",
              r: 3,
              fill: cor(x.indice),
              stroke: t.superficie,
              strokeWidth: 1.5,
            }),
          );
        }
      }
      // O último ponto de cada série, com um anel na cor do fundo.
      const pontas = g.series
        .map((s, i) => {
          const linhas = ts.filter((x) => x.indice === i).flatMap((x) => x.linhas);
          const u = linhas[linhas.length - 1];
          return u ? { ...u, cor: cor(i), nome: s.nome } : null;
        })
        .filter((p): p is Linha & { cor: string; nome: string } => p !== null);
      marcas.push(
        Plot.dot(pontas, {
          x: "t",
          y: "v",
          r: 4,
          fill: "cor",
          stroke: t.superficie,
          strokeWidth: 2,
        }),
      );
      if (pontas.length === 1) {
        marcas.push(
          Plot.text(pontas, {
            x: "t",
            y: "v",
            text: (d: Linha) => valorNoEixo(g, d.v, numero(d.v, g.casas)),
            dx: 8,
            textAnchor: "start",
            fill: t.tinta,
            fontSize: 12,
            fontWeight: 600,
          }),
        );
      }
    }

    const dias = (xMax - xMin) / DIA;
    const estreito = largura < 480;
    const marcasY = (g.marcas_y ?? []).map((m) => m.valor);
    const dominioY = dominioDasMarcas(todas);
    const rotuloLongo = Math.max(0, ...(g.marcas_y ?? []).map((m) => m.rotulo.length));
    const umaSerie = !barras && g.series.length === 1;
    const grafico = Plot.plot({
      width: largura,
      // No celular o gráfico fica mais alto que largo em proporção: a linha precisa de altura
      // para mostrar o movimento, e a largura é pouca.
      height: Math.round(
        estreito ? Math.min(300, Math.max(240, largura * 0.72)) : Math.min(340, Math.max(220, largura * 0.5)),
      ),
      marginLeft: Math.max(estreito ? 38 : 46, rotuloLongo * 6.4 + 8),
      marginRight: umaSerie ? 52 : 18,
      marginTop: 14,
      marginBottom: 28,
      style: { background: "transparent", color: t.tinta2, fontSize: "11px", overflow: "visible" },
      x: {
        type: "utc",
        label: null,
        // Quantos rótulos cabem: um ano ("2024") pede uns 52 px; um mês ("out/26"), uns 66.
        ticks:
          g.eixo === "meses"
            ? marcasDeMeses(xMin, xMax, Math.max(3, Math.floor((largura - 60) / 40)))
            : marcasDoEixo(
                xMin,
                xMax,
                Math.max(3, Math.floor((largura - 60) / ((xMax - xMin) / DIA > 800 ? 52 : 66))),
              ),
        tickSize: 0,
        tickPadding: 8,
        line: false,
        tickFormat: (d: Date) => {
          if (g.eixo === "meses") {
            const k = (d.getUTCFullYear() - 2000) * 12 + d.getUTCMonth();
            return k > 0 ? `+${k}` : String(k).replace("-", "−");
          }
          if (dias > 800) return String(d.getUTCFullYear());
          if (dias > 100) {
            return d.getUTCMonth() === 0
              ? String(d.getUTCFullYear())
              : `${mesCurto(d)}/${String(d.getUTCFullYear()).slice(2)}`;
          }
          return `${String(d.getUTCDate()).padStart(2, "0")}/${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
        },
      },
      y: {
        label: null,
        grid: true,
        ticks: marcasY.length ? marcasY.filter((m) => m >= dominioY[0] && m <= dominioY[1]) : 5,
        tickSize: 0,
        tickPadding: 6,
        nice: !marcasY.length,
        zero: barras ? true : undefined,
        domain: marcasY.length ? dominioY : undefined,
        tickFormat: (v: number) => valorNoEixo(g, v, eixo(v, g.unidade, g.casas)),
      },
      marks: marcas,
    });
    grafico.querySelectorAll('[aria-label="y-grid"] line, [aria-label="y-grid"] path').forEach((n) => {
      (n as SVGElement).setAttribute("stroke", t.fio);
      (n as SVGElement).setAttribute("stroke-opacity", "1");
    });
    grafico.setAttribute("role", "img");
    grafico.setAttribute("aria-label", descricao(g));
    tela.replaceChildren(grafico, dica);
    pairar(g, grafico as SVGSVGElement & Plot.Plot, tela, dica, ts, cor, t);
    pintarLegenda(g, legenda, cor);
  }

  let pendente = 0;

  new ResizeObserver(() => {
    cancelAnimationFrame(pendente);
    pendente = requestAnimationFrame(desenhar);
  }).observe(tela);
  document.addEventListener("tema", desenhar);
  return artigo;
}

/** O nome do valor quando o eixo tem nomes (a nota de crédito); senão, o número. */
function valorNoEixo(g: Grafico, v: number, numeral: string): string {
  return g.marcas_y?.find((m) => Math.abs(m.valor - v) < 1e-9)?.rotulo ?? numeral;
}

/** O vão dos dados com meio degrau de folga, para a escada não colar na borda. */
function dominioDasMarcas(todas: Linha[]): [number, number] {
  const vs = todas.map((l) => l.v);
  return [Math.min(...vs) - 0.5, Math.max(...vs) + 0.5];
}

type Chave = "linha" | "tracejada" | "banda" | "intervalo" | "intervalo-meio" | "referencia" | "ponto" | "barra" | "contorno";

export interface ItemDaLegenda {
  nome: string;
  chave: Chave;
  cor?: string;
}

/** O que a legenda mostra: as séries (quando há duas ou mais), a projeção, a faixa, as
 *  barras de erro e as linhas de referência. A mesma lista vai para a tela e para o PNG. */
function itensDaLegenda(g: Grafico, cor: (i: number) => string): ItemDaLegenda[] {
  const itens: ItemDaLegenda[] = [];
  if (g.series.length >= 2) {
    g.series.forEach((s, i) => {
      itens.push({ nome: s.nome, chave: s.papel === "realizado" ? "linha" : "tracejada", cor: cor(i) });
    });
  }
  if (g.series.some((s) => s.tracejado_desde)) itens.push({ nome: "projeção", chave: "tracejada" });
  if (g.faixa) itens.push({ nome: g.faixa.nome, chave: "banda" });
  for (const intervalo of g.intervalos ?? []) {
    itens.push({ nome: intervalo.nome, chave: "intervalo" });
    if (intervalo.meio?.length && intervalo.nome_meio) {
      itens.push({ nome: intervalo.nome_meio, chave: "intervalo-meio" });
    }
  }
  for (const linha of g.linhas) itens.push({ nome: linha.rotulo, chave: "referencia" });
  return itens;
}

function pintarLegenda(g: Grafico, legenda: HTMLElement, cor: (i: number) => string): void {
  const classe: Record<Chave, string> = {
    linha: "chave",
    tracejada: "chave tracejada",
    banda: "chave banda",
    intervalo: "chave intervalo",
    "intervalo-meio": "chave intervalo-meio",
    referencia: "chave referencia",
    ponto: "chave redonda",
    barra: "chave",
    contorno: "chave chave-contorno",
  };
  const itens = itensDaLegenda(g, cor).map((x) => {
    const item = el("span", "legenda-item");
    const chave = el("i", classe[x.chave]);
    chave.style.setProperty("--cor", x.cor ?? "var(--tinta-3)");
    item.append(chave, document.createTextNode(x.nome));
    return item;
  });
  legenda.replaceChildren(...itens);
  legenda.hidden = itens.length === 0;
}

function pairar(
  g: Grafico,
  grafico: SVGSVGElement & Plot.Plot,
  tela: HTMLElement,
  dica: HTMLElement,
  ts: Traco[],
  cor: (i: number) => string,
  t: Tema,
): void {
  const x = grafico.scale("x");
  const y = grafico.scale("y");
  if (!x || !y || !x.apply || !y.apply) return;
  const porSerie = g.series.map((_, i) => {
    const mapa = new Map<number, Linha>();
    for (const tr of ts) if (tr.indice === i) for (const l of tr.linhas) mapa.set(l.t.getTime(), l);
    return mapa;
  });
  const instantes = [...new Set(porSerie.flatMap((m) => [...m.keys()]))].sort((a, b) => a - b);
  if (!instantes.length) return;
  const px = instantes.map((i) => Number(x.apply(new Date(i))));

  const ns = "http://www.w3.org/2000/svg";
  const camada = document.createElementNS(ns, "g");
  camada.setAttribute("pointer-events", "none");
  const [yBaixo, yCima] = y.range as [number, number];
  const regua = document.createElementNS(ns, "line");
  regua.setAttribute("stroke", t.eixo);
  regua.setAttribute("y1", String(yCima));
  regua.setAttribute("y2", String(yBaixo));
  camada.append(regua);
  const bolinhas = g.series.map((_, i) => {
    const c = document.createElementNS(ns, "circle");
    c.setAttribute("r", "4.5");
    c.setAttribute("fill", cor(i));
    c.setAttribute("stroke", t.superficie);
    c.setAttribute("stroke-width", "2");
    camada.append(c);
    return c;
  });
  camada.style.display = "none";
  grafico.append(camada);

  const mover = (ev: PointerEvent): void => {
    const caixa = grafico.getBoundingClientRect();
    const escala = caixa.width / (grafico.width.baseVal.value || caixa.width);
    const alvo = (ev.clientX - caixa.left) / escala;
    // Busca binária do instante mais próximo.
    let a = 0;
    let b = px.length - 1;
    while (b - a > 1) {
      const m = (a + b) >> 1;
      if ((px[m] ?? 0) < alvo) a = m;
      else b = m;
    }
    const i = Math.abs((px[a] ?? 0) - alvo) <= Math.abs((px[b] ?? 0) - alvo) ? a : b;
    const instante = instantes[i];
    const xi = px[i];
    if (instante === undefined || xi === undefined) return;
    regua.setAttribute("x1", String(xi));
    regua.setAttribute("x2", String(xi));
    const linhas: HTMLElement[] = [];
    const curta = unidadeCurta(g.unidade);
    let iso = "";
    g.series.forEach((s, k) => {
      const ponto = porSerie[k]?.get(instante);
      const c = bolinhas[k];
      if (!c) return;
      if (!ponto) {
        c.style.display = "none";
        return;
      }
      iso = ponto.iso;
      c.style.display = "";
      c.setAttribute("cx", String(xi));
      c.setAttribute("cy", String(y.apply(g.tipo === "empilhado" ? 0 : ponto.v)));
      if (g.tipo === "empilhado" || (g.tipo === "barras" && k === 0)) c.style.display = "none";
      const linha = el("div", "dica-linha");
      const chave = el("i", "chave");
      chave.style.setProperty("--cor", cor(k));
      const valor = el("b", "", valorNoEixo(g, ponto.v, comUnidade(ponto.v, curta, g.casas)));
      linha.append(chave, el("span", "", s.nome), valor);
      linhas.push(linha);
      // Se a série tem barra de erro nesta data, a faixa vai escrita logo abaixo.
      for (const intervalo of g.intervalos ?? []) {
        if (intervalo.serie !== s.id) continue;
        const faixa = intervalo.pontos.find(([d]) => d === ponto.iso);
        const meio = intervalo.meio?.find(([d]) => d === ponto.iso);
        const de = (f: [string, number, number]): string =>
          `de ${numero(f[1], g.casas)} a ${comUnidade(f[2], curta, g.casas)}`;
        if (faixa) {
          linhas.push(el("div", "dica-faixa", meio ? `8 em 10: ${de(faixa)}` : de(faixa)));
        }
        if (meio) linhas.push(el("div", "dica-faixa", `metade: ${de(meio)}`));
      }
    });
    if (!linhas.length) return;
    dica.replaceChildren(el("div", "dica-data", rotuloX(g, iso)), ...linhas);
    dica.hidden = false;
    camada.style.display = "";
    const larguraTela = tela.clientWidth;
    const xTela = xi * escala;
    if (larguraTela < 480) {
      // No celular a dica fica no alto, do lado oposto ao dedo, e nunca sai do quadro.
      const doLadoDireito = xTela < larguraTela / 2;
      dica.style.left = doLadoDireito ? "" : "0px";
      dica.style.right = doLadoDireito ? "0px" : "";
      dica.style.top = "0px";
    } else {
      const aDireita = xTela < larguraTela * 0.6;
      dica.style.left = aDireita ? `${xTela + 14}px` : "";
      dica.style.right = aDireita ? "" : `${larguraTela - xTela + 14}px`;
      dica.style.top = `${Math.max(0, ev.clientY - caixa.top - 20)}px`;
    }
  };
  const sair = (): void => {
    dica.hidden = true;
    camada.style.display = "none";
  };
  grafico.addEventListener("pointermove", mover);
  grafico.addEventListener("pointerdown", mover);
  // Com mouse, a dica some quando o ponteiro sai. Com o dedo, o "sair" vem no fim de todo
  // toque: a dica fica até a pessoa tocar fora do gráfico.
  grafico.addEventListener("pointerleave", (ev) => {
    if (ev.pointerType === "mouse") sair();
  });
  const foraDoGrafico = (ev: PointerEvent): void => {
    if (!grafico.isConnected) {
      document.removeEventListener("pointerdown", foraDoGrafico);
      return;
    }
    if (!grafico.contains(ev.target as Node)) sair();
  };
  document.addEventListener("pointerdown", foraDoGrafico);
}

function descricao(g: Grafico): string {
  const partes = g.series.map((s) => {
    const validos = s.pontos.filter((p) => p[1] !== null);
    const u = validos[validos.length - 1];
    if (!u || u[1] === null) return s.nome;
    return `${s.nome}: ${comUnidade(u[1], g.unidade, g.casas)} em ${rotuloX(g, u[0])}`;
  });
  return `${g.titulo}. ${partes.join("; ")}. Fonte: ${g.fonte}.`;
}

function matriz(g: Grafico): { isos: string[]; colunas: Map<string, number | null>[] } {
  const colunas = g.series.map((s) => new Map(s.pontos));
  const isos = [...new Set(g.series.flatMap((s) => s.pontos.map((p) => p[0])))].sort();
  if (g.eixo !== "meses") isos.reverse();
  return { isos, colunas };
}

function tabelaDoGrafico(g: Grafico): HTMLTableElement {
  const { isos, colunas } = matriz(g);
  const tabela = el("table", "dados");
  const cab = tabela.createTHead().insertRow();
  cab.append(el("th", "", "Período"));
  for (const s of g.series) cab.append(el("th", "", s.nome));
  const corpo = tabela.createTBody();
  for (const iso of isos) {
    const linha = corpo.insertRow();
    linha.append(el("th", "", rotuloX(g, iso)));
    for (const c of colunas) {
      const v = c.get(iso);
      linha.append(el("td", "", v === null || v === undefined ? "–" : numero(v, g.casas)));
    }
  }
  tabela.createCaption().textContent = `${g.titulo} (${g.unidade})`;
  return tabela;
}

function baixarCsv(g: Grafico): void {
  if (g.sem_download) return;
  const { isos, colunas } = matriz(g);
  const aspas = (s: string) => `"${s.replaceAll('"', '""')}"`;
  const meses = g.eixo === "meses";
  const cabeca = meses ? "meses desde o primeiro corte" : "data";
  const linhas = [[cabeca, ...g.series.map((s) => s.nome)].map(aspas).join(";")];
  for (const iso of isos) {
    const valores = colunas.map((c) => {
      const v = c.get(iso);
      return v === null || v === undefined ? "" : String(v).replace(".", ",");
    });
    linhas.push([meses ? String(mesRelativo(iso)) : iso, ...valores].join(";"));
  }
  linhas.push("", aspas(`Unidade: ${g.unidade}`), aspas(fonteComEnderecos(`Fonte: ${g.fonte}`)));
  const blob = new Blob(["﻿" + linhas.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${g.id}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ------------------------------------------------------------------ PNG

/** Quebra o texto em linhas que caibam em `largura` (medidas na fonte já posta no `ctx`). */
function linhasDoTexto(ctx: CanvasRenderingContext2D, texto: string, largura: number): string[] {
  const linhas: string[] = [];
  let atual = "";
  for (const palavra of texto.split(/\s+/).filter(Boolean)) {
    const tentativa = atual ? `${atual} ${palavra}` : palavra;
    if (atual && ctx.measureText(tentativa).width > largura) {
      linhas.push(atual);
      atual = palavra;
    } else atual = tentativa;
  }
  if (atual) linhas.push(atual);
  return linhas;
}

/** O desenho do gráfico como imagem: o SVG da tela, sem a camada do toque. */
function imagemDoSvg(svg: SVGSVGElement): Promise<{ img: HTMLImageElement; w: number; h: number }> {
  const w = Math.round(svg.width.baseVal.value || svg.getBoundingClientRect().width);
  const h = Math.round(svg.height.baseVal.value || svg.getBoundingClientRect().height);
  const copia = svg.cloneNode(true) as SVGSVGElement;
  copia.querySelectorAll('g[pointer-events="none"], g[aria-label="tip"]').forEach((n) => n.remove());
  copia.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  copia.setAttribute("width", String(w));
  copia.setAttribute("height", String(h));
  // A fonte da página (a Geist não vai junto: no arquivo fica a do sistema, parecida).
  copia.style.fontFamily = getComputedStyle(svg).fontFamily;
  const texto = new XMLSerializer().serializeToString(copia);
  const img = new Image();
  img.width = w;
  img.height = h;
  return new Promise((resolve, reject) => {
    img.onload = () => resolve({ img, w, h });
    img.onerror = () => reject(new Error("o desenho não virou imagem"));
    img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(texto)}`;
  });
}

/** O que vai escrito na imagem em volta do desenho. `nota` (quem ficou fora do desenho,
 *  o ano) sai antes da fonte. */
export interface Figura {
  id: string;
  titulo: string;
  sub: string;
  fonte: string;
  nota?: string;
  legenda: ItemDaLegenda[];
  /** O desenho: o SVG da tela ou, para o que a tela monta em HTML (ranking, pirâmide), um
   *  desenho próprio no canvas, com a largura e a altura dele. */
  svg?: SVGSVGElement | null;
  desenho?: Desenho | null;
}

export interface Desenho {
  w: number;
  h: number;
  pintar: (ctx: CanvasRenderingContext2D, x: number, y: number) => void;
}

/** O texto de uma nota da tela sem os botões e os links dela ("Mostrar todos", "Ver as
 *  contas de…"), para ir na imagem. */
export function textoSemBotoes(no: HTMLElement): string {
  const copia = no.cloneNode(true) as HTMLElement;
  copia.querySelectorAll("button, a, br").forEach((n) => n.remove());
  return (copia.textContent ?? "").replace(/\s+/g, " ").trim();
}

declare const __ENDERECO__: string;

/** Os botões "PNG" e "Copiar" de um gráfico: a mesma imagem, baixada ou posta na área de
 *  transferência. O "Copiar" só aparece onde o navegador sabe copiar imagem. Quem chama
 *  decide se pode exportar (dado privado não pode: licencas.py). */
export function botoesDaImagem(figura: () => Figura | null): HTMLButtonElement[] {
  const png = el("button", "", "PNG");
  png.type = "button";
  png.title = "Baixar a imagem do gráfico, com o título e a fonte";
  png.addEventListener("click", () => {
    const f = figura();
    if (!f?.svg && !f?.desenho) return;
    void pngDaFigura(f, tema()).then((blob) => {
      if (!blob) return;
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${f.id}.png`;
      a.click();
      window.setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    });
  });
  if (typeof ClipboardItem === "undefined" || !navigator.clipboard?.write) return [png];
  const copiar = el("button", "", "Copiar");
  copiar.type = "button";
  copiar.title = "Copiar a imagem do gráfico, com o título e a fonte, para colar em outro lugar";
  let volta = 0;
  const avisar = (texto: string): void => {
    copiar.textContent = texto;
    window.clearTimeout(volta);
    volta = window.setTimeout(() => (copiar.textContent = "Copiar"), 1800);
  };
  copiar.addEventListener("click", () => {
    const f = figura();
    if (!f?.svg && !f?.desenho) return;
    // A promessa vai direto ao ClipboardItem, ainda dentro do toque (o Safari exige).
    const blob = pngDaFigura(f, tema()).then((b) => {
      if (!b) throw new Error("a imagem não saiu");
      return b;
    });
    navigator.clipboard
      .write([new ClipboardItem({ "image/png": blob })])
      .then(() => avisar("Copiada ✓"))
      .catch(() => avisar("Não copiou: use o PNG"));
  });
  return [png, copiar];
}

/** O gráfico em PNG, em fundo claro, com o título, a unidade, a legenda e a fonte escritos
 *  na imagem: quem recebe a figura sabe o que é e de onde veio. */
async function pngDaFigura(f: Figura, t: Tema): Promise<Blob | null> {
  let desenho = f.desenho ?? null;
  if (f.svg) {
    const { img, w, h } = await imagemDoSvg(f.svg);
    desenho = { w, h, pintar: (c, x, y) => c.drawImage(img, x, y, w, h) };
  }
  if (!desenho) return null;
  const { w, h } = desenho;
  const legenda = f.legenda;
  const escala = 2;
  const margem = 28;
  const largura = Math.max(w + 2 * margem, 560);
  const util = largura - 2 * margem;
  const familia = getComputedStyle(document.body).fontFamily;
  const fonte = (peso: number, px: number): string => `${peso} ${px}px ${familia}`;

  // Primeiro mede (a altura depende das quebras de linha), depois desenha.
  const medidor = document.createElement("canvas").getContext("2d");
  if (!medidor) return null;
  medidor.font = fonte(600, 20);
  const titulo = linhasDoTexto(medidor, f.titulo, util);
  medidor.font = fonte(400, 13);
  const sub = linhasDoTexto(medidor, f.sub, util);
  medidor.font = fonte(400, 12);
  const nota = f.nota ? linhasDoTexto(medidor, f.nota, util) : [];
  const pe = linhasDoTexto(medidor, f.fonte, util - 90);
  // A legenda em fileiras: cada item é a chave (22 px) e o nome.
  const fileiras: { item: ItemDaLegenda; x: number }[][] = [];
  let fileira: { item: ItemDaLegenda; x: number }[] = [];
  let x = 0;
  for (const item of legenda) {
    const larguraItem = 22 + medidor.measureText(item.nome).width + 16;
    if (fileira.length && x + larguraItem > util) {
      fileiras.push(fileira);
      fileira = [];
      x = 0;
    }
    fileira.push({ item, x });
    x += larguraItem;
  }
  if (fileira.length) fileiras.push(fileira);

  const alturaTitulo = titulo.length * 26 + (sub.length ? 4 + sub.length * 18 : 0);
  const alturaLegenda = fileiras.length ? 10 + fileiras.length * 20 : 0;
  const alturaNota = nota.length ? nota.length * 17 + 6 : 0;
  const altura = margem + alturaTitulo + alturaLegenda + 12 + h + 14 + alturaNota + pe.length * 17 + 10 + 16 + margem;

  const canvas = document.createElement("canvas");
  canvas.width = Math.round(largura * escala);
  canvas.height = Math.round(altura * escala);
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  ctx.scale(escala, escala);
  ctx.fillStyle = t.superficie || "#fdfcf7";
  ctx.fillRect(0, 0, largura, altura);
  ctx.textBaseline = "top";

  let y = margem;
  ctx.fillStyle = t.tinta;
  ctx.font = fonte(600, 20);
  for (const l of titulo) {
    ctx.fillText(l, margem, y);
    y += 26;
  }
  if (sub.length) {
    y += 4;
    ctx.fillStyle = t.tinta2;
    ctx.font = fonte(400, 13);
    for (const l of sub) {
      ctx.fillText(l, margem, y);
      y += 18;
    }
  }

  if (fileiras.length) {
    y += 10;
    ctx.font = fonte(400, 12);
    for (const f of fileiras) {
      for (const { item, x: dx } of f) {
        const x0 = margem + dx;
        const meio = y + 8;
        ctx.save();
        ctx.strokeStyle = item.cor ?? t.tinta2;
        ctx.fillStyle = item.cor ?? t.tinta2;
        if (item.chave === "linha" || item.chave === "tracejada" || item.chave === "referencia") {
          ctx.lineWidth = item.chave === "linha" ? 3 : item.chave === "tracejada" ? 2 : 1.5;
          if (item.chave === "tracejada") ctx.setLineDash([5, 4]);
          if (item.chave === "referencia") {
            ctx.strokeStyle = t.tinta2;
            ctx.setLineDash([2, 3]);
          }
          if (item.chave === "tracejada" && !item.cor) ctx.strokeStyle = t.tinta3;
          ctx.beginPath();
          ctx.moveTo(x0, meio);
          ctx.lineTo(x0 + 16, meio);
          ctx.stroke();
        } else if (item.chave === "barra") {
          ctx.fillRect(x0 + 2, meio - 5, 12, 10);
        } else if (item.chave === "contorno") {
          ctx.strokeStyle = t.tinta2;
          ctx.lineWidth = 1.5;
          ctx.strokeRect(x0 + 2, meio - 5, 12, 10);
        } else if (item.chave === "ponto") {
          ctx.beginPath();
          ctx.arc(x0 + 8, meio, 5, 0, Math.PI * 2);
          ctx.fill();
        } else if (item.chave === "banda") {
          ctx.globalAlpha = 0.3;
          ctx.fillStyle = t.faixa;
          ctx.fillRect(x0, meio - 5, 16, 10);
        } else if (item.chave === "intervalo") {
          ctx.strokeStyle = t.tinta2;
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.moveTo(x0 + 4, meio - 7);
          ctx.lineTo(x0 + 12, meio - 7);
          ctx.moveTo(x0 + 8, meio - 7);
          ctx.lineTo(x0 + 8, meio + 7);
          ctx.moveTo(x0 + 4, meio + 7);
          ctx.lineTo(x0 + 12, meio + 7);
          ctx.stroke();
        } else {
          ctx.fillStyle = "rgb(20 38 28 / 16%)";
          ctx.fillRect(x0 + 4, meio - 6, 8, 12);
        }
        ctx.restore();
        ctx.fillStyle = t.tinta2;
        ctx.fillText(item.nome, x0 + 22, y + 1);
      }
      y += 20;
    }
  }

  y += 12;
  ctx.save();
  desenho.pintar(ctx, margem + Math.max(0, (util - w) / 2), y);
  ctx.restore();
  y += h + 14;

  ctx.font = fonte(400, 12);
  if (nota.length) {
    ctx.fillStyle = t.tinta2;
    for (const l of nota) {
      ctx.fillText(l, margem, y);
      y += 17;
    }
    y += 6;
  }
  ctx.fillStyle = t.tinta3;
  for (const l of pe) {
    ctx.fillText(l, margem, y);
    y += 17;
  }
  // O crédito, numa linha própria: a marca, o nome e o endereço do site.
  y += 10;
  ctx.strokeStyle = t.tinta3;
  ctx.globalAlpha = 0.35;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(margem, y - 5);
  ctx.lineTo(largura - margem, y - 5);
  ctx.stroke();
  ctx.globalAlpha = 1;
  const xMarca = margem;
  const yMarca = y;
  ctx.fillStyle = "#ffd400";
  ctx.beginPath();
  ctx.moveTo(xMarca + 7, yMarca);
  ctx.lineTo(xMarca + 14, yMarca + 7);
  ctx.lineTo(xMarca + 7, yMarca + 14);
  ctx.lineTo(xMarca, yMarca + 7);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "#0b2a6f";
  ctx.beginPath();
  ctx.arc(xMarca + 7, yMarca + 7, 3.5, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = t.tinta;
  ctx.font = fonte(600, 12);
  ctx.fillText("sacibras", xMarca + 20, yMarca + 1);
  const nomeLargura = ctx.measureText("sacibras").width;
  ctx.fillStyle = t.tinta2;
  ctx.font = fonte(400, 12);
  ctx.fillText(`· painel da economia brasileira · ${__ENDERECO__}`, xMarca + 26 + nomeLargura, yMarca + 1);

  return new Promise<Blob | null>((ok) => canvas.toBlob(ok, "image/png"));
}
