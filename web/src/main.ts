import "./estilo.css";
import { comUnidade, data, dataHora, numero, periodo } from "./formato";
import { montarGrafico } from "./grafico";
import { montarMundo } from "./mundo";
import type { Cartao, Mundo, Painel, Secao, Tabela } from "./tipos";

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

async function ler<T>(arquivo: string): Promise<T> {
  const resposta = await fetch(`data/${arquivo}`, { cache: "no-cache" });
  if (!resposta.ok) throw new Error(`${arquivo}: HTTP ${resposta.status}`);
  return (await resposta.json()) as T;
}

const NOME_PROCEDENCIA = { oficial: "oficial", mercado: "mercado", calculado: "calculado" } as const;

function miniatura(pontos: [string, number][]): SVGSVGElement {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 120 34");
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("aria-hidden", "true");
  if (pontos.length < 2) return svg;
  const xs = pontos.map((p) => data(p[0]).getTime());
  const ys = pontos.map((p) => p[1]);
  const x0 = Math.min(...xs);
  const x1 = Math.max(...xs);
  const y0 = Math.min(...ys);
  const y1 = Math.max(...ys);
  const px = (t: number) => 2 + ((t - x0) / (x1 - x0 || 1)) * 112;
  const py = (v: number) => 30 - ((v - y0) / (y1 - y0 || 1)) * 26;
  const d = pontos.map((p, i) => `${i ? "L" : "M"}${px(xs[i] ?? 0).toFixed(1)},${py(p[1]).toFixed(1)}`);
  const linha = document.createElementNS(ns, "path");
  linha.setAttribute("d", d.join(""));
  linha.setAttribute("fill", "none");
  linha.setAttribute("stroke", "var(--eixo)");
  linha.setAttribute("stroke-width", "1.6");
  linha.setAttribute("vector-effect", "non-scaling-stroke");
  linha.setAttribute("stroke-linejoin", "round");
  const ultimo = pontos[pontos.length - 1];
  svg.append(linha);
  if (ultimo) {
    // O ponto de hoje na cor da casa; o passado, discreto.
    const ponta = document.createElementNS(ns, "path");
    const cx = px(xs[xs.length - 1] ?? 0);
    const cy = py(ultimo[1]);
    ponta.setAttribute("d", `M${cx.toFixed(1)},${cy.toFixed(1)}h0.01`);
    ponta.setAttribute("stroke", "var(--verde)");
    ponta.setAttribute("stroke-width", "7");
    ponta.setAttribute("stroke-linecap", "round");
    ponta.setAttribute("vector-effect", "non-scaling-stroke");
    svg.append(ponta);
  }
  return svg;
}

function montarCartao(c: Cartao, comLink: boolean): HTMLElement {
  const no = comLink && c.secao ? el("a", "cartao") : el("div", "cartao");
  if (no instanceof HTMLAnchorElement) no.href = `#${c.secao}`;
  no.append(el("span", "cartao-rotulo", c.rotulo));
  const valor = el("span", "cartao-valor");
  const texto = comUnidade(c.valor, c.unidade, c.casas);
  // O número grande e a unidade pequena: "13,75" + "% a.a.", "R$" + "5,42".
  const n = numero(c.valor, c.casas);
  const [antes, depois] = texto.split(n);
  if (antes?.trim()) valor.append(el("small", "", antes.trim()), document.createTextNode(" "));
  valor.append(document.createTextNode(n));
  if (depois?.trim()) valor.append(el("small", "", depois.trim()));
  if (antes === undefined || depois === undefined) valor.textContent = texto;
  no.append(valor);
  no.append(el("span", "cartao-detalhe", c.detalhe));
  if (c.mini.length > 1) no.append(miniatura(c.mini));
  const pe = el("span", "cartao-pe");
  pe.append(el("span", "", periodo(c.referencia, c.periodicidade)));
  const proc = el("span", `procedencia ${c.procedencia}`);
  proc.append(el("i"), document.createTextNode(NOME_PROCEDENCIA[c.procedencia]));
  proc.title = c.fonte;
  pe.append(proc);
  no.append(pe);
  no.title = `Fonte: ${c.fonte}`;
  return no;
}

function montarTabela(t: Tabela): HTMLElement {
  const cartao = el("div", "tabela-cartao inteira");
  cartao.append(el("h3", "", t.titulo));
  if (t.subtitulo) cartao.append(el("p", "sub", t.subtitulo));
  const rolavel = el("div", "tabela-rolavel");
  rolavel.style.maxHeight = "none";
  const tabela = el("table", "dados");
  const cab = tabela.createTHead().insertRow();
  cab.append(el("th", "", ""));
  for (const c of t.colunas) cab.append(el("th", "", c));
  const corpo = tabela.createTBody();
  for (const l of t.linhas) {
    const tr = corpo.insertRow();
    const th = el("th", "", l.rotulo);
    th.append(el("span", "sub", ` ${l.unidade}`));
    if (l.fonte) th.title = l.fonte;
    tr.append(th);
    for (const v of l.valores) tr.append(el("td", "", v === null ? "–" : numero(v, l.casas)));
  }
  rolavel.append(tabela);
  cartao.append(rolavel);
  const pe = el("footer", "grafico-pe");
  pe.append(el("span", "fonte", `Fonte: ${t.fonte}`));
  cartao.append(pe);
  if (t.nota) cartao.append(el("p", "nota", t.nota));
  return cartao;
}

function montarSecao(s: Secao, alvo: HTMLElement): void {
  if (s.resumo) alvo.append(el("p", "secao-resumo", s.resumo));
  if (s.cartoes.length) {
    const grade = el("div", "cartoes");
    for (const c of s.cartoes) grade.append(montarCartao(c, s.id === "resumo"));
    alvo.append(grade);
  }
  if (s.graficos.length || s.tabelas.length) {
    const grade = el("div", "graficos");
    for (const g of s.graficos) grade.append(montarGrafico(g));
    for (const t of s.tabelas) grade.append(montarTabela(t));
    alvo.append(grade);
  }
}

function tema(): void {
  const botao = document.getElementById("tema");
  if (!botao) return;
  const escuroAgora = (): boolean => {
    const fixo = document.documentElement.dataset.theme;
    if (fixo) return fixo === "dark";
    return matchMedia("(prefers-color-scheme: dark)").matches;
  };
  const rotular = (): void => {
    botao.textContent = escuroAgora() ? "Tema claro" : "Tema escuro";
  };
  rotular();
  botao.addEventListener("click", () => {
    const novo = escuroAgora() ? "light" : "dark";
    document.documentElement.dataset.theme = novo;
    try {
      localStorage.setItem("tema", novo);
    } catch {
      // Sem armazenamento (janela anônima): o tema vale só nesta visita.
    }
    rotular();
    document.dispatchEvent(new Event("tema"));
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    rotular();
    document.dispatchEvent(new Event("tema"));
  });
}

function vigiarNav(nav: HTMLElement): void {
  const links = new Map<string, HTMLAnchorElement>();
  nav.querySelectorAll("a").forEach((a) => links.set(a.hash.slice(1), a));
  const visiveis = new Set<string>();
  const observador = new IntersectionObserver(
    (entradas) => {
      for (const e of entradas) {
        if (e.isIntersecting) visiveis.add(e.target.id);
        else visiveis.delete(e.target.id);
      }
      const atual = [...links.keys()].find((id) => visiveis.has(id));
      links.forEach((a, id) => a.setAttribute("aria-current", String(id === atual)));
    },
    { rootMargin: "-80px 0px -55% 0px" },
  );
  document.querySelectorAll("section.secao").forEach((s) => observador.observe(s));
}

async function iniciar(): Promise<void> {
  tema();
  const conteudo = document.getElementById("conteudo") as HTMLElement;
  const nav = document.getElementById("nav") as HTMLElement;
  const atualizado = document.getElementById("atualizado") as HTMLElement;
  let painel: Painel;
  try {
    painel = await ler<Painel>("painel.json");
  } catch (erro) {
    atualizado.textContent = "Sem dados";
    conteudo.append(
      el(
        "p",
        "aviso",
        `Os dados ainda não foram gerados (${String(erro)}). Rode o builder: "sacibras build".`,
      ),
    );
    return;
  }
  atualizado.textContent = `Atualizado em ${dataHora(painel.gerado_em)}`;

  const tarefas: Promise<void>[] = [];
  for (const item of painel.secoes) {
    const link = el("a", "", item.titulo);
    link.href = `#${item.id}`;
    nav.append(link);
    const secao = el("section", "secao");
    secao.id = item.id;
    secao.append(el("h2", "secao-titulo", item.titulo));
    conteudo.append(secao);
    if (!item.ok) {
      secao.append(el("p", "aviso", "Esta seção não pôde ser atualizada nesta rodada."));
      continue;
    }
    tarefas.push(
      (async () => {
        try {
          if (item.id === "mundo") {
            const m = await ler<Mundo>(item.arquivo);
            secao.append(el("p", "secao-resumo", m.resumo), montarMundo(m));
          } else {
            montarSecao(await ler<Secao>(item.arquivo), secao);
          }
        } catch (erro) {
          secao.append(el("p", "aviso", `Não foi possível carregar esta seção (${String(erro)}).`));
        }
      })(),
    );
  }
  vigiarNav(nav);

  const fontes = document.getElementById("fontes") as HTMLElement;
  for (const f of painel.fontes) {
    const li = el("li", f.ok ? "" : "fora", f.fonte);
    if (f.detalhe) li.title = f.detalhe;
    fontes.append(li);
  }
  await Promise.all(tarefas);
  if (location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView();
}

void iniciar();
