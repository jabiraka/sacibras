// Um renderizador só para todos os gráficos: desenha o que o builder declarou.
// Regras da casa: um eixo só, linha de 2 px, grade discreta, legenda quando há duas séries
// ou mais, tabela e CSV sempre à mão, consenso e previsão tracejados.

import * as Plot from "@observablehq/plot";
import { comUnidade, data, eixo, mesCurto, numero, periodo } from "./formato";
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
  if (g.tipo === "curva") return [];
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
  acoes.append(verTabela, csv);
  pe.append(acoes);
  artigo.append(pe);
  if (g.nota) artigo.append(el("p", "nota", g.nota));

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
    const cor = (i: number) => t.series[(g.series[i]?.cor ?? i) % t.series.length] ?? t.tinta;
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
      const dados = empilhado ? todas : (ts[0]?.linhas ?? []);
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
        ticks: marcasDoEixo(
          xMin,
          xMax,
          Math.max(3, Math.floor((largura - 60) / ((xMax - xMin) / DIA > 800 ? 52 : 66))),
        ),
        tickSize: 0,
        tickPadding: 8,
        line: false,
        tickFormat: (d: Date) => {
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

function pintarLegenda(g: Grafico, legenda: HTMLElement, cor: (i: number) => string): void {
  legenda.replaceChildren();
  const itens: HTMLElement[] = [];
  if (g.series.length >= 2) {
    g.series.forEach((s, i) => {
      const item = el("span", "legenda-item");
      const chave = el("i", s.papel === "realizado" ? "chave" : "chave tracejada");
      chave.style.setProperty("--cor", cor(i));
      item.append(chave, document.createTextNode(s.nome));
      itens.push(item);
    });
  }
  if (g.series.some((s) => s.tracejado_desde)) {
    const item = el("span", "legenda-item");
    const chave = el("i", "chave tracejada");
    chave.style.setProperty("--cor", "var(--tinta-3)");
    item.append(chave, document.createTextNode("projeção"));
    itens.push(item);
  }
  if (g.faixa) {
    const item = el("span", "legenda-item");
    item.append(el("i", "chave banda"), document.createTextNode(g.faixa.nome));
    itens.push(item);
  }
  for (const intervalo of g.intervalos ?? []) {
    const item = el("span", "legenda-item");
    item.append(el("i", "chave intervalo"), document.createTextNode(intervalo.nome));
    itens.push(item);
    if (intervalo.meio?.length && intervalo.nome_meio) {
      const meio = el("span", "legenda-item");
      meio.append(el("i", "chave intervalo-meio"), document.createTextNode(intervalo.nome_meio));
      itens.push(meio);
    }
  }
  for (const linha of g.linhas) {
    const item = el("span", "legenda-item");
    item.append(el("i", "chave referencia"), document.createTextNode(linha.rotulo));
    itens.push(item);
  }
  legenda.append(...itens);
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
      const valor = el("b", "", valorNoEixo(g, ponto.v, comUnidade(ponto.v, g.unidade, g.casas)));
      linha.append(chave, el("span", "", s.nome), valor);
      linhas.push(linha);
      // Se a série tem barra de erro nesta data, a faixa vai escrita logo abaixo.
      for (const intervalo of g.intervalos ?? []) {
        if (intervalo.serie !== s.id) continue;
        const faixa = intervalo.pontos.find(([d]) => d === ponto.iso);
        const meio = intervalo.meio?.find(([d]) => d === ponto.iso);
        const de = (f: [string, number, number]): string =>
          `de ${numero(f[1], g.casas)} a ${comUnidade(f[2], g.unidade, g.casas)}`;
        if (faixa) {
          linhas.push(el("div", "dica-faixa", meio ? `8 em 10: ${de(faixa)}` : de(faixa)));
        }
        if (meio) linhas.push(el("div", "dica-faixa", `metade: ${de(meio)}`));
      }
    });
    if (!linhas.length) return;
    dica.replaceChildren(el("div", "dica-data", periodo(iso, g.periodicidade)), ...linhas);
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
    return `${s.nome}: ${comUnidade(u[1], g.unidade, g.casas)} em ${periodo(u[0], g.periodicidade)}`;
  });
  return `${g.titulo}. ${partes.join("; ")}. Fonte: ${g.fonte}.`;
}

function matriz(g: Grafico): { isos: string[]; colunas: Map<string, number | null>[] } {
  const colunas = g.series.map((s) => new Map(s.pontos));
  const isos = [...new Set(g.series.flatMap((s) => s.pontos.map((p) => p[0])))].sort().reverse();
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
    linha.append(el("th", "", periodo(iso, g.periodicidade)));
    for (const c of colunas) {
      const v = c.get(iso);
      linha.append(el("td", "", v === null || v === undefined ? "–" : numero(v, g.casas)));
    }
  }
  tabela.createCaption().textContent = `${g.titulo} (${g.unidade})`;
  return tabela;
}

function baixarCsv(g: Grafico): void {
  const { isos, colunas } = matriz(g);
  const aspas = (s: string) => `"${s.replaceAll('"', '""')}"`;
  const linhas = [["data", ...g.series.map((s) => s.nome)].map(aspas).join(";")];
  for (const iso of isos) {
    const valores = colunas.map((c) => {
      const v = c.get(iso);
      return v === null || v === undefined ? "" : String(v).replace(".", ",");
    });
    linhas.push([iso, ...valores].join(";"));
  }
  linhas.push("", aspas(`Unidade: ${g.unidade}`), aspas(`Fonte: ${g.fonte}`));
  const blob = new Blob(["﻿" + linhas.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${g.id}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}
