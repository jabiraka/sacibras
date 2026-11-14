// A página tem duas vistas, trocadas pelo # do endereço:
//   início      → o essencial: seis números e a lista de assuntos;
//   um assunto  → os números dele, os dois primeiros gráficos, e o resto atrás de um clique.
// Decisão do Caio (14/11/2026): pouca coisa na entrada, e a pessoa abre o que quiser.

import "@fontsource-variable/geist";
import "./estilo.css";
import { comUnidade, data, dataHora, numero, periodo } from "./formato";
import { montarEstados } from "./estados";
import { montarGrafico } from "./grafico";
import { montarMundo } from "./mundo";
import { el, guardar } from "./pecas";
import { montarSimulador } from "./simulador";
import type { Cartao, Estados, Mundo, Painel, Secao, Tabela } from "./tipos";

const NUMEROS_A_VISTA = 4;
const GRAFICOS_A_VISTA = 2;

const lidos = new Map<string, Promise<unknown>>();

function ler<T>(arquivo: string): Promise<T> {
  let pedido = lidos.get(arquivo);
  if (!pedido) {
    pedido = fetch(`data/${arquivo}`, { cache: "no-cache" }).then((r) => {
      if (!r.ok) throw new Error(`${arquivo}: HTTP ${r.status}`);
      return r.json();
    });
    lidos.set(arquivo, pedido);
  }
  return pedido as Promise<T>;
}

/** O número grande e a unidade pequena: "13,75" + "% a.a.", "R$" + "5,65". */
function valorComUnidade(c: Cartao, alvo: HTMLElement): void {
  const texto = comUnidade(c.valor, c.unidade, c.casas);
  const n = numero(c.valor, c.casas);
  const [antes, depois] = texto.split(n);
  if (antes === undefined || depois === undefined) {
    alvo.textContent = texto;
    return;
  }
  if (antes.trim()) alvo.append(el("small", "", antes.trim()), document.createTextNode(" "));
  alvo.append(document.createTextNode(n));
  if (depois.trim()) alvo.append(el("small", "", depois.trim()));
}

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
  linha.setAttribute("stroke-width", "1.5");
  linha.setAttribute("vector-effect", "non-scaling-stroke");
  linha.setAttribute("stroke-linejoin", "round");
  svg.append(linha);
  const ultimo = pontos[pontos.length - 1];
  if (ultimo) {
    // O ponto de hoje na cor da casa; o passado, discreto.
    const ponta = document.createElementNS(ns, "path");
    ponta.setAttribute("d", `M${px(xs[xs.length - 1] ?? 0).toFixed(1)},${py(ultimo[1]).toFixed(1)}h0.01`);
    ponta.setAttribute("stroke", "var(--verde)");
    ponta.setAttribute("stroke-width", "6");
    ponta.setAttribute("stroke-linecap", "round");
    ponta.setAttribute("vector-effect", "non-scaling-stroke");
    svg.append(ponta);
  }
  return svg;
}

function montarCartao(c: Cartao): HTMLElement {
  const no = el("div", "cartao");
  no.append(el("span", "cartao-rotulo", c.rotulo));
  const valor = el("span", "cartao-valor");
  valorComUnidade(c, valor);
  no.append(valor, el("span", "cartao-detalhe", c.detalhe));
  if (c.mini.length > 1) no.append(miniatura(c.mini));
  const pe = el("span", "cartao-pe");
  pe.append(el("span", "", periodo(c.referencia, c.periodicidade)));
  const proc = el("span", `procedencia ${c.procedencia}`);
  proc.append(el("i"), document.createTextNode(c.procedencia));
  pe.append(proc);
  no.append(pe);
  no.title = `Fonte: ${c.fonte}`;
  return no;
}

function montarTabela(t: Tabela): HTMLElement {
  return guardar(t.titulo, t.subtitulo, () => {
    const rolavel = el("div", "tabela-rolavel");
    const tabela = el("table", "dados");
    const cab = tabela.createTHead().insertRow();
    cab.append(el("th", "", ""));
    for (const c of t.colunas) cab.append(el("th", "", c));
    const corpo = tabela.createTBody();
    for (const l of t.linhas) {
      const tr = corpo.insertRow();
      const th = el("th", "", l.rotulo);
      if (l.unidade) th.append(el("span", "sub", ` ${l.unidade}`));
      tr.append(th);
      for (const v of l.valores) tr.append(el("td", "", v === null ? "–" : numero(v, l.casas)));
    }
    rolavel.append(tabela);
    const pe = el("footer", "grafico-pe");
    pe.append(el("span", "fonte", `Fonte: ${t.fonte}`));
    const partes: HTMLElement[] = [rolavel, pe];
    if (t.nota) partes.push(el("p", "nota", t.nota));
    return partes;
  });
}

/** O botão que revela o que ficou guardado, e some. */
function botaoDeAbrir(rotulo: string, quantos: number, abrir: () => void): HTMLElement {
  const caixa = el("div", "abrir");
  const botao = el("button", "", rotulo);
  botao.type = "button";
  botao.append(el("span", "", `+${quantos}`));
  botao.addEventListener("click", () => {
    abrir();
    caixa.remove();
  });
  caixa.append(botao);
  return caixa;
}

function montarSecao(s: Secao, alvo: HTMLElement): void {
  if (s.cartoes.length) {
    const grade = el("div", "cartoes");
    s.cartoes.slice(0, NUMEROS_A_VISTA).forEach((c) => grade.append(montarCartao(c)));
    alvo.append(grade);
    const resto = s.cartoes.slice(NUMEROS_A_VISTA);
    if (resto.length) {
      alvo.append(
        botaoDeAbrir("Mais números", resto.length, () => {
          resto.forEach((c) => grade.append(montarCartao(c)));
        }),
      );
    }
  }
  if (s.graficos.length) {
    const grade = el("div", "graficos");
    // Um gráfico de largura inteira já enche a tela: abre só ele.
    const aVista = s.graficos[0]?.largura === "inteira" ? 1 : GRAFICOS_A_VISTA;
    s.graficos.slice(0, aVista).forEach((g) => grade.append(montarGrafico(g)));
    alvo.append(grade);
    const resto = s.graficos.slice(aVista);
    if (resto.length) {
      alvo.append(
        botaoDeAbrir("Mais gráficos", resto.length, () => {
          resto.forEach((g) => grade.append(montarGrafico(g)));
        }),
      );
    }
  }
  const simulador = s.simulador;
  if (simulador) {
    alvo.append(
      guardar(
        "Simule a dívida pública",
        "Mexa no juro, no crescimento e no resultado primário e veja para onde ela vai",
        () => montarSimulador(simulador),
      ),
    );
  }
  for (const t of s.tabelas) alvo.append(montarTabela(t));
}

// ------------------------------------------------------------------ vistas

function vistaInicio(painel: Painel, conteudo: HTMLElement): void {
  const assuntos = painel.secoes.filter((s) => s.id !== "resumo");

  const heroi = el("section", "heroi");
  const selo = el("span", "selo entra");
  selo.append(el("i", "bolinha"), document.createTextNode(`Atualizado em ${dataHora(painel.gerado_em)}`));
  const titulo = el("h1", "entra");
  titulo.style.setProperty("--i", "1");
  titulo.append(
    document.createTextNode("A economia brasileira "),
    el("span", "apagado", "em seis números."),
  );
  const lema = el(
    "p",
    "lema entra",
    "Cada número com a data e a fonte oficial. O resto está guardado por assunto: abra o que interessa.",
  );
  lema.style.setProperty("--i", "2");
  heroi.append(selo, titulo, lema);

  const essenciais = el("section", "essenciais entra");
  essenciais.style.setProperty("--i", "3");
  essenciais.setAttribute("aria-label", "Os seis números");
  void ler<Secao>("resumo.json")
    .then((resumo) => {
      for (const c of resumo.cartoes) {
        const item = el("a", "essencial");
        item.href = `#${c.secao}`;
        item.title = `${c.detalhe ? `${c.detalhe}. ` : ""}Fonte: ${c.fonte}`;
        const valor = el("strong");
        valorComUnidade(c, valor);
        item.append(
          valor,
          el("span", "rotulo", c.rotulo),
          el("span", "quando", periodo(c.referencia, c.periodicidade)),
        );
        essenciais.append(item);
      }
    })
    .catch(() => essenciais.remove());

  const bloco = el("section", "bloco");
  bloco.id = "assuntos";
  bloco.append(el("p", "sobretitulo", "Assuntos"));
  const h2 = el("h2");
  h2.append(document.createTextNode("Abra o que interessa. "), el("span", "apagado", "Toque num."));
  bloco.append(h2);
  const lista = el("ul", "assuntos");
  for (const s of assuntos) {
    const li = el("li");
    const a = el("a", "vidro assunto");
    a.href = `#${s.id}`;
    const nome = el("span", "assunto-titulo", s.titulo);
    nome.append(el("span", "seta", "→"));
    a.append(nome);
    a.append(
      el("span", "assunto-resumo", s.ok ? s.resumo : "Não pôde ser atualizado nesta rodada."),
    );
    li.append(a);
    lista.append(li);
  }
  bloco.append(lista);
  conteudo.replaceChildren(heroi, essenciais, bloco);
}

function vistaAssunto(painel: Painel, id: string, conteudo: HTMLElement): void {
  const assuntos = painel.secoes.filter((s) => s.id !== "resumo");
  const indice = assuntos.findIndex((s) => s.id === id);
  const item = assuntos[indice];
  if (!item) return;

  const secao = el("section", "secao");
  const voltar = el("a", "voltar", "← Início");
  voltar.href = "#";
  secao.append(voltar, el("p", "sobretitulo", "Assunto"), el("h2", "", item.titulo));
  const corpo = el("div");
  secao.append(corpo);

  if (!item.ok) {
    corpo.append(el("p", "aviso", "Este assunto não pôde ser atualizado nesta rodada."));
  } else if (id === "mundo") {
    void ler<Mundo>(item.arquivo)
      .then((m) => corpo.append(el("p", "secao-resumo", m.resumo), montarMundo(m)))
      .catch((erro) => corpo.append(el("p", "aviso", `Não foi possível carregar (${String(erro)}).`)));
  } else if (id === "estados") {
    void ler<Estados>(item.arquivo)
      .then((e) => corpo.append(el("p", "secao-resumo", e.resumo), montarEstados(e)))
      .catch((erro) => corpo.append(el("p", "aviso", `Não foi possível carregar (${String(erro)}).`)));
  } else {
    void ler<Secao>(item.arquivo)
      .then((s) => {
        if (s.resumo) corpo.append(el("p", "secao-resumo", s.resumo));
        montarSecao(s, corpo);
      })
      .catch((erro) => corpo.append(el("p", "aviso", `Não foi possível carregar (${String(erro)}).`)));
  }

  const vizinhos = el("nav", "vizinhos");
  vizinhos.setAttribute("aria-label", "Outros assuntos");
  const anterior = assuntos[indice - 1];
  const proximo = assuntos[indice + 1];
  if (anterior) {
    const a = el("a", "vidro vizinho");
    a.href = `#${anterior.id}`;
    a.append(el("small", "", "← Anterior"), el("span", "", anterior.titulo));
    vizinhos.append(a);
  }
  if (proximo) {
    const a = el("a", "vidro vizinho proximo");
    a.href = `#${proximo.id}`;
    a.append(el("small", "", "Próximo →"), el("span", "", proximo.titulo));
    vizinhos.append(a);
  }
  secao.append(vizinhos);
  conteudo.replaceChildren(secao);
}

// ------------------------------------------------------------------ tema e partida

function tema(): void {
  const botao = document.getElementById("tema");
  if (!botao) return;
  const claro = (): boolean => document.documentElement.dataset.theme === "light";
  const rotular = (): void => {
    botao.textContent = claro() ? "Tema escuro" : "Tema claro";
  };
  rotular();
  botao.addEventListener("click", () => {
    const novo = claro() ? "dark" : "light";
    if (novo === "light") document.documentElement.dataset.theme = "light";
    else delete document.documentElement.dataset.theme;
    try {
      localStorage.setItem("tema", novo);
    } catch {
      // Sem armazenamento (janela anônima): o tema vale só nesta visita.
    }
    rotular();
    document.dispatchEvent(new Event("tema"));
  });
}

async function iniciar(): Promise<void> {
  tema();
  const conteudo = document.getElementById("conteudo") as HTMLElement;
  let painel: Painel;
  try {
    painel = await ler<Painel>("painel.json");
  } catch (erro) {
    conteudo.append(
      el(
        "p",
        "aviso",
        `Os dados ainda não foram gerados (${String(erro)}). Rode o builder: "sacibras build".`,
      ),
    );
    return;
  }

  const fontes = document.getElementById("fontes") as HTMLElement;
  for (const f of painel.fontes) {
    const li = el("li", f.ok ? "" : "fora", f.fonte);
    if (f.detalhe) li.title = f.detalhe;
    fontes.append(li);
  }

  let vistaAtual = "";
  const desenhar = (): void => {
    const alvo = location.hash.slice(1);
    const assunto = painel.secoes.some((s) => s.id === alvo && s.id !== "resumo") ? alvo : "";
    if (assunto !== vistaAtual || !conteudo.firstChild) {
      vistaAtual = assunto;
      if (assunto) vistaAssunto(painel, assunto, conteudo);
      else vistaInicio(painel, conteudo);
      window.scrollTo(0, 0);
    }
    // "#assuntos" é uma âncora dentro do início, não um assunto.
    if (!assunto && alvo) document.getElementById(alvo)?.scrollIntoView();
  };
  window.addEventListener("hashchange", desenhar);
  desenhar();
}

void iniciar();
