// O glossário: quem não conhece uma palavra toca nela (ou no "?" ao lado do nome do número ou
// do gráfico) e a definição abre num balão, sem sair da tela (Caio, 14/11/2026).
//
// Os termos vêm do builder (`glossario.json`, de `glossario.py`). Aqui se procura cada forma
// no texto que a tela mostra, também no que abre depois ("Mais números", tabelas guardadas):
//   - no texto corrido (resumos, notas, subtítulos), a palavra ganha sublinhado pontilhado;
//   - no nome de um número, gráfico ou alerta, o termo ganha um "?" ao lado.
// Cada termo é marcado uma vez só por peça (cartão, gráfico, caixa, tabela), para a tela não
// virar um mar de sublinhados; a tabela conta como peça própria, então o termo do título do
// gráfico ganha o "?" de novo na linha da tabela.

import "./glossario.css";
import { el } from "./pecas";

interface Verbete {
  id: string;
  nome: string;
  definicao: string;
  formas: string[];
  elo?: string;
}

/** Onde a palavra é sublinhada. */
const TEXTO = [
  ".secao-resumo",
  ".parte-resumo",
  ".assunto-resumo",
  ".cartao-detalhe",
  ".grafico-cabeca .sub",
  ".painel-mundo .sub",
  "p.nota",
  "p.posicao",
  ".alerta-texto p",
  ".guardado summary small",
  ".ficha-bloco .sub",
  ".ficha-numero .detalhe",
  "table.dados td.texto",
  "table.dados caption",
].join(",");

/** Onde o termo ganha um "?" ao lado (rótulos curtos, em que sublinhar atrapalha a leitura). */
const ROTULO = [
  ".cartao-rotulo",
  ".grafico-cabeca h3",
  ".essencial .rotulo",
  ".alerta-nome > span:first-child",
  ".painel-mundo > h3",
  ".ficha-numero .rotulo",
  ".ficha-bloco h4",
  // Tabelas e legendas também (Caio, 14/11/2026: "coloque glossário mesmo que o nome esteja
  // na tabela ou num cartão"): o nome da coluna, o da linha e o da série.
  "table.dados thead th",
  "table.dados tbody th",
  ".ficha-partes tbody th",
  ".legenda-item",
].join(",");

/** A peça dentro da qual um termo só se marca uma vez. */
const PECA =
  "table.dados, .cartao, .grafico, .guardado, .alerta, .essencial, .ficha-numero, .ficha-bloco, .painel-mundo";

/** Elementos em que não se mexe: o que já é clicável, campos e o próprio glossário. */
const NAO_MEXER = "a:not(.essencial), button, select, option, input, textarea, .termo, .balao";

let padrao: RegExp | null = null;
const exatas = new Map<string, Verbete>();
const soltas = new Map<string, Verbete>();
const marcadosPorPeca = new WeakMap<Element, Set<string>>();

function escapar(texto: string): string {
  return texto.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Forma com duas maiúsculas ou mais (IPCA, PIB, IBC-Br) só casa com a mesma caixa. */
function exigeCaixa(forma: string): boolean {
  return (forma.match(/\p{Lu}/gu) ?? []).length >= 2;
}

function preparar(lista: Verbete[]): void {
  const formas: string[] = [];
  for (const v of lista) {
    for (const f of v.formas) {
      if (exigeCaixa(f)) exatas.set(f, v);
      else soltas.set(f.toLocaleLowerCase("pt-BR"), v);
      formas.push(f);
    }
  }
  // A forma mais longa primeiro: "juro real" antes de "juro", "IPCA+" antes de "IPCA".
  formas.sort((a, b) => b.length - a.length);
  padrao = new RegExp(
    `(?<![\\p{L}\\p{N}])(${formas.map(escapar).join("|")})(?![\\p{L}\\p{N}+])`,
    "giu",
  );
}

/** O verbete de um trecho achado pelo padrão, respeitando a caixa das siglas. */
function verbeteDe(trecho: string): Verbete | undefined {
  return exatas.get(trecho) ?? soltas.get(trecho.toLocaleLowerCase("pt-BR"));
}

function marcadosEm(no: Element): Set<string> {
  const peca = no.closest(PECA) ?? no;
  let conjunto = marcadosPorPeca.get(peca);
  if (!conjunto) {
    conjunto = new Set();
    marcadosPorPeca.set(peca, conjunto);
  }
  return conjunto;
}

// ------------------------------------------------------------------ o balão

let balao: HTMLElement | null = null;
let origem: HTMLElement | null = null;

function fecharBalao(devolverFoco = false): void {
  if (!balao) return;
  balao.hidden = true;
  origem?.setAttribute("aria-expanded", "false");
  if (devolverFoco) origem?.focus();
  origem = null;
}

function criarBalao(): HTMLElement {
  const caixa = el("div", "balao");
  caixa.id = "balao";
  caixa.setAttribute("role", "dialog");
  caixa.hidden = true;
  document.body.append(caixa);
  document.addEventListener("click", (ev) => {
    const alvo = ev.target as Node;
    if (caixa.hidden || caixa.contains(alvo) || origem?.contains(alvo)) return;
    fecharBalao();
  });
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && !caixa.hidden) fecharBalao(true);
  });
  window.addEventListener("hashchange", () => fecharBalao());
  window.addEventListener("resize", () => fecharBalao());
  return caixa;
}

function abrirBalao(v: Verbete, junto: HTMLElement): void {
  balao ??= criarBalao();
  if (origem === junto && !balao.hidden) {
    fecharBalao();
    return;
  }
  origem?.setAttribute("aria-expanded", "false");
  origem = junto;
  junto.setAttribute("aria-expanded", "true");

  const fechar = el("button", "balao-fechar", "×");
  fechar.type = "button";
  fechar.setAttribute("aria-label", "Fechar");
  fechar.addEventListener("click", () => fecharBalao(true));
  const titulo = el("p", "balao-titulo", v.nome);
  titulo.id = "balao-titulo";
  balao.setAttribute("aria-labelledby", titulo.id);
  const partes: HTMLElement[] = [fechar, titulo, el("p", "balao-texto", v.definicao)];
  // "Ver no painel" só quando leva a outro lugar.
  const aqui = location.hash || "#";
  if (v.elo && !aqui.startsWith(v.elo)) {
    const ir = el("a", "balao-elo", "Ver no painel →");
    ir.href = v.elo;
    partes.push(ir);
  }
  balao.replaceChildren(...partes);
  balao.hidden = false;

  // Embaixo da palavra; em cima, se embaixo não couber. Nunca fora da tela.
  const r = junto.getBoundingClientRect();
  const margem = 12;
  const largura = balao.offsetWidth;
  const altura = balao.offsetHeight;
  const centro = r.left + r.width / 2;
  const esquerda = Math.min(
    Math.max(margem, centro - largura / 2),
    document.documentElement.clientWidth - largura - margem,
  );
  const embaixo = r.bottom + 10 + altura <= window.innerHeight || r.top - 10 - altura < 0;
  const topo = embaixo ? r.bottom + 10 : r.top - 10 - altura;
  balao.classList.toggle("em-cima", !embaixo);
  balao.style.left = `${esquerda + window.scrollX}px`;
  balao.style.top = `${topo + window.scrollY}px`;
  balao.style.setProperty("--seta", `${Math.min(largura - 18, Math.max(18, centro - esquerda))}px`);
}

/** O que abre o balão: a palavra sublinhada ou o "?". A palavra é um <span role="button">,
 *  porque um <button> não quebra linha no meio de "dívida bruta do governo geral". */
function gatilho(v: Verbete, texto: string, classe: string): HTMLElement {
  const ajuda = classe.includes("ajuda");
  const b = ajuda ? el("button", classe, texto) : el("span", classe, texto);
  if (b instanceof HTMLButtonElement) b.type = "button";
  // O "?" não se traduz (o tradutor fazia dele "¿" em espanhol).
  if (ajuda) {
    b.classList.add("notranslate");
    b.setAttribute("translate", "no");
  }
  else {
    b.setAttribute("role", "button");
    b.tabIndex = 0;
  }
  b.setAttribute("aria-expanded", "false");
  b.setAttribute("aria-controls", "balao");
  if (ajuda) b.setAttribute("aria-label", `O que é ${v.nome}?`);
  const abrir = (ev: Event): void => {
    // Dentro de um link (os seis números da entrada) ou de um <summary>, o toque é só do balão.
    ev.preventDefault();
    ev.stopPropagation();
    abrirBalao(v, b);
  };
  b.addEventListener("click", abrir);
  b.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" || ev.key === " ") abrir(ev);
  });
  return b;
}

// ------------------------------------------------------------------ marcar o texto

function marcarTexto(bloco: Element): void {
  if (!padrao) return;
  const usados = marcadosEm(bloco);
  const andar = document.createTreeWalker(bloco, NodeFilter.SHOW_TEXT, {
    acceptNode: (n) =>
      n.parentElement?.closest(NAO_MEXER) && n.parentElement.closest(NAO_MEXER) !== bloco
        ? NodeFilter.FILTER_REJECT
        : NodeFilter.FILTER_ACCEPT,
  });
  const nos: Text[] = [];
  for (let n = andar.nextNode(); n; n = andar.nextNode()) nos.push(n as Text);
  for (const no of nos) {
    const texto = no.data;
    padrao.lastIndex = 0;
    const pedacos: (string | HTMLElement)[] = [];
    let desde = 0;
    for (let m = padrao.exec(texto); m; m = padrao.exec(texto)) {
      const achado = m[1] ?? "";
      const v = verbeteDe(achado);
      if (!v || usados.has(v.id)) continue;
      usados.add(v.id);
      pedacos.push(texto.slice(desde, m.index), gatilho(v, achado, "termo"));
      desde = m.index + achado.length;
    }
    if (!pedacos.length) continue;
    pedacos.push(texto.slice(desde));
    no.replaceWith(...pedacos);
  }
}

function marcarRotulo(rotulo: Element): void {
  if (!padrao) return;
  const texto = rotulo.textContent ?? "";
  padrao.lastIndex = 0;
  const usados = marcadosEm(rotulo);
  for (let m = padrao.exec(texto); m; m = padrao.exec(texto)) {
    const v = verbeteDe(m[1] ?? "");
    if (!v || usados.has(v.id)) continue;
    usados.add(v.id);
    rotulo.append(gatilho(v, "?", "termo-ajuda"));
    return;
  }
}

function marcar(raiz: ParentNode): void {
  for (const r of raiz.querySelectorAll<HTMLElement>(ROTULO)) {
    if (r.dataset.gl) continue;
    r.dataset.gl = "1";
    marcarRotulo(r);
  }
  for (const b of raiz.querySelectorAll<HTMLElement>(TEXTO)) {
    if (b.dataset.gl) continue;
    b.dataset.gl = "1";
    marcarTexto(b);
  }
}

/** O texto de `no` foi trocado (outra métrica na lista): marca de novo, do zero. */
export function remarcar(no: Element): void {
  marcadosPorPeca.delete(no.closest(PECA) ?? no);
  marcadosPorPeca.delete(no);
  for (const n of [no, ...no.querySelectorAll("[data-gl]")]) {
    if (n instanceof HTMLElement) delete n.dataset.gl;
  }
}

/** Lê o glossário e passa a marcar tudo o que aparecer dentro de `raiz`. */
export function ligarGlossario(raiz: HTMLElement): void {
  void fetch("data/glossario.json", { cache: "no-cache" })
    .then((r) => (r.ok ? (r.json() as Promise<Verbete[]>) : []))
    .then((lista) => {
      if (!lista.length) return;
      preparar(lista);
      marcar(raiz);
      let pendente = 0;
      new MutationObserver(() => {
        cancelAnimationFrame(pendente);
        pendente = requestAnimationFrame(() => marcar(raiz));
      }).observe(raiz, { childList: true, subtree: true });
    })
    .catch(() => undefined);
}
