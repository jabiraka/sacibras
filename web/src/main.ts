// A página tem três vistas, trocadas pelo # do endereço:
//   início       → o essencial: seis números e os assuntos, por categoria;
//   um assunto   → a visão geral: quatro números, as partes dele e o gráfico principal;
//   uma parte    → tudo o que a parte tem ("Inflação › Núcleos e o ritmo"), numa tela só.
// O menu lateral (no celular, o botão "Assuntos") leva a qualquer uma, e a busca fica fixa nele.
// Decisões do Caio (14/11/2026): pouca coisa por tela, categorias e subcategorias, a pessoa
// acha as coisas com facilidade.

import "@fontsource-variable/geist";
import "./estilo.css";
import { comUnidade, data, dataHora, numero, periodo } from "./formato";
import { montarAlertas } from "./alertas";
import { pontoMaisNovo } from "./aovivo";
import { abrirBusca, ligarBusca, revelar } from "./busca";
import { agendaDoAssunto } from "./calendario";
import { ligarGlossario } from "./glossario";
import { montarEstados } from "./estados";
import { montarGrafico } from "./grafico";
import { montarMundo } from "./mundo";
import { montarPiramide } from "./piramide";
import { montarRetornos } from "./retornos";
import { el, guardar } from "./pecas";
import { montarSimulador } from "./simulador";
import { montarSimuladorSelic } from "./simulador-selic";
import type {
  Cartao,
  Estados,
  Grafico,
  ItemSecao,
  Mundo,
  Painel,
  Secao,
  SimuladorSelic,
  Subcategoria,
  Tabela,
} from "./tipos";

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
  no.id = `c-${c.id}`;
  no.append(el("span", "cartao-rotulo", c.rotulo));
  const valor = el("span", "cartao-valor");
  valorComUnidade(c, valor);
  no.append(valor, el("span", "cartao-detalhe", c.detalhe));
  if (c.meta) no.append(...medidorDaMeta(c.valor, c.meta, c.casas, c.unidade));
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
  const caixa = guardar(t.titulo, t.subtitulo, () => {
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
  caixa.id = `t-${t.id}`;
  return caixa;
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

/** O gráfico, ou a peça própria quando o gráfico tem uma (o comparador de retornos). */
function montarPeca(g: Grafico): HTMLElement {
  if (g.piramide) return montarPiramide(g, g.piramide);
  return g.id === "retornos-em-reais" ? montarRetornos(g) : montarGrafico(g);
}

/** O simulador da Selic, guardado atrás do título; na parte dele (`#juros/efeito`) já abre. */
function caixaDoSimuladorSelic(sim: SimuladorSelic): HTMLElement {
  const caixa = guardar(
    "E se a Selic mudar?",
    "Corte ou suba a taxa e veja o que o Banco Central estima para a inflação, o dólar e a dívida",
    () => montarSimuladorSelic(sim),
  );
  caixa.id = "simulador-selic";
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
    s.graficos.slice(0, aVista).forEach((g) => grade.append(montarPeca(g)));
    alvo.append(grade);
    const resto = s.graficos.slice(aVista);
    if (resto.length) {
      alvo.append(
        botaoDeAbrir("Mais gráficos", resto.length, () => {
          resto.forEach((g) => grade.append(montarPeca(g)));
        }),
      );
    }
  }
  if (s.alertas?.length) alvo.append(montarAlertas(s.alertas));
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
  const simuladorSelic = s.simulador_selic;
  if (simuladorSelic) alvo.append(caixaDoSimuladorSelic(simuladorSelic));
  for (const t of s.tabelas) alvo.append(montarTabela(t));
}

// ------------------------------------------------------------------ vistas

/** O conteúdo de um dos seis números; `aoVivo` quando o valor veio agora, direto da fonte. */
function preencherEssencial(item: HTMLElement, c: Cartao, aoVivo: boolean): void {
  item.replaceChildren();
  item.title =
    `${c.detalhe && !aoVivo ? `${c.detalhe}. ` : ""}Fonte: ${c.fonte}` +
    (aoVivo ? ". Lido agora, direto da fonte, mais novo que a última rodada do painel." : "");
  const valor = el("strong");
  valorComUnidade(c, valor);
  item.append(valor, el("span", "rotulo", c.rotulo));
  if (c.meta) item.append(...medidorDaMeta(c.valor, c.meta, c.casas, c.unidade));
  const quando = el("span", "quando", periodo(c.referencia, c.periodicidade));
  if (aoVivo) quando.append(el("span", "novo", "novo"));
  item.append(quando);
  item.classList.toggle("ao-vivo", aoVivo);
}

/** O número contra a meta oficial: onde ele está no intervalo, e em palavras. Serve para
 *  meta em % (a de inflação) e em reais (a de resultado primário). */
function medidorDaMeta(
  valor: number,
  meta: NonNullable<Cartao["meta"]>,
  casas: number,
  unidade = "%",
): HTMLElement[] {
  const situacao =
    valor > meta.superior ? "acima" : valor < meta.inferior ? "abaixo" : "dentro";
  const texto = { acima: "acima do teto", abaixo: "abaixo do piso", dentro: "dentro da meta" }[
    situacao
  ];
  const selo = el("span", `situacao ${situacao}`);
  selo.append(el("i", "", situacao === "dentro" ? "✓" : situacao === "acima" ? "▲" : "▼"), document.createTextNode(texto));

  // Régua com folga de meio intervalo de cada lado (ou até o valor, se ele passar disso).
  const folga = (meta.superior - meta.inferior) / 2 || 1;
  const inicio = Math.min(meta.inferior - folga, valor - folga / 3);
  const fim = Math.max(meta.superior + folga, valor + folga / 3);
  const pos = (v: number): string =>
    `${Math.min(100, Math.max(0, ((v - inicio) / (fim - inicio)) * 100))}%`;
  const regua = el("span", "regua");
  regua.setAttribute("aria-hidden", "true");
  const faixa = el("i", "regua-faixa");
  faixa.style.left = pos(meta.inferior);
  faixa.style.width = `calc(${pos(meta.superior)} - ${pos(meta.inferior)})`;
  const centro = el("i", "regua-centro");
  centro.style.left = pos(meta.centro);
  const ponto = el("i", `regua-ponto ${situacao}`);
  ponto.style.left = pos(valor);
  regua.append(faixa, centro, ponto);

  const diferenca = valor - meta.centro;
  const emPorcento = unidade.startsWith("%");
  const curto = (v: number): string => (v === 0 ? "R$ 0" : comUnidade(v, unidade, casas));
  const legenda = el(
    "span",
    "regua-legenda",
    emPorcento
      ? `meta ${numero(meta.centro, 0)} % (${numero(meta.inferior, 1)} a ${numero(meta.superior, 1)})`
      : `meta ${curto(meta.centro)} (piso ${curto(meta.inferior)}, teto ${curto(meta.superior)})`,
  );
  const distancia = emPorcento
    ? `${numero(Math.abs(diferenca), casas)} pp`
    : comUnidade(Math.abs(diferenca), unidade, casas);
  legenda.title = `${distancia} ${diferenca >= 0 ? "acima" : "abaixo"} do centro da meta. ${meta.norma}.`;
  return [selo, regua, legenda];
}

// ------------------------------------------------------------------ categorias e menu

/** As categorias do painel, só com os assuntos que existem; o que sobrar vai em "Outros". */
function categorias(painel: Painel): { titulo: string; secoes: ItemSecao[] }[] {
  const assuntos = painel.secoes.filter((s) => s.id !== "resumo");
  const lista = (painel.categorias ?? [])
    .map((c) => ({
      titulo: c.titulo,
      secoes: c.secoes
        .map((id) => assuntos.find((s) => s.id === id))
        .filter((s): s is ItemSecao => s !== undefined),
    }))
    .filter((c) => c.secoes.length);
  const usados = new Set(lista.flatMap((c) => c.secoes.map((s) => s.id)));
  const resto = assuntos.filter((s) => !usados.has(s.id));
  if (resto.length) lista.push({ titulo: lista.length ? "Outros" : "Assuntos", secoes: resto });
  return lista;
}

function categoriaDe(painel: Painel, id: string): string {
  return categorias(painel).find((c) => c.secoes.some((s) => s.id === id))?.titulo ?? "";
}

/** O menu lateral: as categorias, os assuntos e, no assunto aberto, as partes dele. */
function montarMenu(painel: Painel): void {
  const menu = document.getElementById("menu");
  if (!menu) return;
  const inicio = el("a", "menu-inicio", "Início");
  inicio.href = "#";
  inicio.dataset.assunto = "";
  menu.replaceChildren(inicio);
  for (const c of categorias(painel)) {
    const grupo = el("div", "menu-grupo");
    grupo.append(el("p", "menu-categoria", c.titulo));
    const ul = el("ul");
    for (const s of c.secoes) {
      const li = el("li");
      const a = el("a", "menu-assunto", s.titulo);
      a.href = `#${s.id}`;
      a.dataset.assunto = s.id;
      li.append(a);
      if (s.subcategorias?.length) {
        const partes = el("ul", "menu-partes");
        partes.dataset.assunto = s.id;
        for (const p of s.subcategorias) {
          const item = el("li");
          const elo = el("a", "menu-parte", p.titulo);
          elo.href = `#${s.id}/${p.id}`;
          elo.dataset.parte = `${s.id}/${p.id}`;
          item.append(elo);
          partes.append(item);
        }
        li.append(partes);
      }
      ul.append(li);
    }
    grupo.append(ul);
    menu.append(grupo);
  }
}

/** Marca no menu onde a pessoa está e abre as partes do assunto aberto. */
function marcarMenu(assunto: string, parte: string): void {
  const menu = document.getElementById("menu");
  if (!menu) return;
  for (const a of menu.querySelectorAll<HTMLAnchorElement>("a[data-assunto]")) {
    const aqui = a.dataset.assunto === assunto;
    a.classList.toggle("ativo", aqui);
    if (aqui && !parte) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  }
  for (const ul of menu.querySelectorAll<HTMLElement>(".menu-partes")) {
    ul.classList.toggle("aberto", ul.dataset.assunto === assunto);
  }
  for (const a of menu.querySelectorAll<HTMLAnchorElement>("a[data-parte]")) {
    const aqui = a.dataset.parte === `${assunto}/${parte}`;
    a.classList.toggle("ativo", aqui);
    if (aqui) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  }
}

function abrirMenu(abrir: boolean): void {
  const lateral = document.getElementById("lateral");
  const botao = document.querySelector<HTMLButtonElement>(".menu-botao");
  lateral?.classList.toggle("aberta", abrir);
  botao?.setAttribute("aria-expanded", String(abrir));
}

// ------------------------------------------------------------------ início

function vistaInicio(painel: Painel, conteudo: HTMLElement): void {
  const heroi = el("section", "heroi");
  const selo = el("span", "selo entra");
  selo.append(el("i", "bolinha"), document.createTextNode(`Atualizado em ${dataHora(painel.gerado_em)}`));
  const titulo = el("h1", "entra");
  titulo.style.setProperty("--i", "1");
  titulo.append(
    document.createTextNode("Status da "),
    el("span", "apagado", "economia brasileira"),
  );
  const lema = el(
    "p",
    "lema entra",
    "Cada número com a data e a fonte oficial. Escolha um assunto ou busque pelo nome.",
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
        preencherEssencial(item, c, false);
        essenciais.append(item);
        // O ponto mais novo, direto da fonte: se vier depois do da última rodada, troca.
        void pontoMaisNovo(c).then((novo) => {
          if (!novo || novo[0] <= c.referencia) return;
          preencherEssencial(item, { ...c, referencia: novo[0], valor: novo[1] }, true);
        });
      }
    })
    .catch(() => essenciais.remove());

  const bloco = el("section", "bloco");
  bloco.id = "assuntos";
  bloco.append(el("p", "sobretitulo", "Assuntos"));
  const h2 = el("h2");
  h2.append(document.createTextNode("Abra o que interessa. "), el("span", "apagado", "Toque num."));
  bloco.append(h2);
  for (const c of categorias(painel)) {
    const grupo = el("div", "categoria");
    grupo.append(el("h3", "categoria-titulo", c.titulo));
    const lista = el("ul", "assuntos");
    for (const s of c.secoes) {
      const li = el("li");
      const a = el("a", "vidro assunto");
      a.href = `#${s.id}`;
      const nome = el("span", "assunto-titulo", s.titulo);
      nome.append(el("span", "seta", "→"));
      a.append(
        nome,
        el("span", "assunto-resumo", s.ok ? s.resumo : "Não pôde ser atualizado nesta rodada."),
      );
      if (s.subcategorias?.length) {
        a.append(el("span", "assunto-partes", s.subcategorias.map((p) => p.titulo).join(" · ")));
      }
      li.append(a);
      lista.append(li);
    }
    grupo.append(lista);
    bloco.append(grupo);
  }
  conteudo.replaceChildren(heroi, essenciais, bloco);
}

// ------------------------------------------------------------------ assunto e parte

/** "2 números · 3 gráficos · 1 tabela": o que a parte guarda. */
function contagem(p: Subcategoria): string {
  const plural = (n: number, um: string, varios: string): string =>
    n ? `${n} ${n === 1 ? um : varios}` : "";
  return [
    plural(p.cartoes.length, "número", "números"),
    plural(p.graficos.length, "gráfico", "gráficos"),
    plural(p.tabelas.length, "tabela", "tabelas"),
    p.extras.includes("simulador") || p.extras.includes("simulador-selic") ? "simulador" : "",
    p.extras.includes("alertas") ? "painel" : "",
  ]
    .filter(Boolean)
    .join(" · ");
}

/** A parte em que a peça do endereço ("c-ipca-12m", "t-alertas") mora. */
function parteDaPeca(partes: Subcategoria[], peca: string): Subcategoria | undefined {
  if (peca === "t-alertas" || peca.startsWith("a-")) {
    return partes.find((p) => p.extras.includes("alertas"));
  }
  const campos: Record<string, "cartoes" | "graficos" | "tabelas"> = {
    "c-": "cartoes",
    "g-": "graficos",
    "t-": "tabelas",
  };
  const campo = campos[peca.slice(0, 2)];
  if (!campo) return undefined;
  const id = peca.slice(2);
  return partes.find((p) => p[campo].includes(id));
}

/** O que uma parte mostra, inteiro: números, a peça própria, gráficos e tabelas. */
function montarParte(s: Secao, p: Subcategoria, alvo: HTMLElement): void {
  const pegar = <T extends { id: string }>(lista: T[], ids: string[]): T[] =>
    ids.map((i) => lista.find((x) => x.id === i)).filter((x): x is T => x !== undefined);
  const cartoes = pegar(s.cartoes, p.cartoes);
  if (cartoes.length) {
    const grade = el("div", "cartoes");
    cartoes.forEach((c) => grade.append(montarCartao(c)));
    alvo.append(grade);
  }
  if (p.extras.includes("alertas") && s.alertas?.length) {
    const painel = montarAlertas(s.alertas);
    if (painel instanceof HTMLDetailsElement) painel.open = true;
    alvo.append(painel);
  }
  const simulador = s.simulador;
  if (p.extras.includes("simulador") && simulador) {
    const caixa = guardar(
      "Simule a dívida pública",
      "Mexa no juro, no crescimento e no resultado primário e veja para onde ela vai",
      () => montarSimulador(simulador),
    );
    if (caixa instanceof HTMLDetailsElement) caixa.open = true;
    alvo.append(caixa);
  }
  const simuladorSelic = s.simulador_selic;
  if (p.extras.includes("simulador-selic") && simuladorSelic) {
    const caixa = caixaDoSimuladorSelic(simuladorSelic);
    if (caixa instanceof HTMLDetailsElement) caixa.open = true;
    alvo.append(caixa);
  }
  const graficos = pegar(s.graficos, p.graficos);
  if (graficos.length) {
    const grade = el("div", "graficos");
    graficos.forEach((g) => grade.append(montarPeca(g)));
    alvo.append(grade);
  }
  // Numa parte com uma tabela só, ela é o assunto da tela: já abre aberta.
  for (const t of pegar(s.tabelas, p.tabelas)) {
    const caixa = montarTabela(t);
    if (p.tabelas.length === 1 && caixa instanceof HTMLDetailsElement) caixa.open = true;
    alvo.append(caixa);
  }
}

function vistaAssunto(painel: Painel, id: string, peca: string, conteudo: HTMLElement): void {
  const item = painel.secoes.find((s) => s.id === id && s.id !== "resumo");
  if (!item) return;
  const categoria = categoriaDe(painel, id);

  const secao = el("section", "secao");
  const topo = el("header", "secao-topo");
  const corpo = el("div", "secao-corpo");
  secao.append(topo, corpo);
  conteudo.replaceChildren(secao);

  /** A trilha ("Preços, juros e crédito › Inflação") e o título. */
  const cabecalho = (titulo: string, assuntoComElo: boolean): void => {
    const trilha = el("nav", "trilha");
    trilha.setAttribute("aria-label", "Onde você está");
    if (categoria) trilha.append(el("span", "", categoria));
    if (assuntoComElo) {
      const a = el("a", "", item.titulo);
      a.href = `#${id}`;
      trilha.append(el("span", "trilha-sep", "›"), a);
    }
    topo.replaceChildren(trilha, el("h2", "", titulo));
  };
  const falhou = (erro: unknown): void => {
    corpo.append(el("p", "aviso", `Não foi possível carregar (${String(erro)}).`));
  };

  cabecalho(item.titulo, false);
  marcarMenu(id, "");
  if (!item.ok) {
    corpo.append(el("p", "aviso", "Este assunto não pôde ser atualizado nesta rodada."));
    return;
  }
  if (id === "mundo") {
    topo.append(agendaDoAssunto(id));
    void ler<Mundo>(item.arquivo)
      .then((m) => corpo.append(el("p", "secao-resumo", m.resumo), montarMundo(m)))
      .catch(falhou);
    return;
  }
  if (id === "estados") {
    topo.append(agendaDoAssunto(id));
    void ler<Estados>(item.arquivo)
      .then((e) => corpo.append(el("p", "secao-resumo", e.resumo), montarEstados(e)))
      .catch(falhou);
    return;
  }
  void ler<Secao>(item.arquivo)
    .then((s) => {
      const partes = s.subcategorias ?? [];
      const parte =
        partes.find((p) => p.id === peca) ?? (peca ? parteDaPeca(partes, peca) : undefined);

      if (!partes.length) {
        // Assunto sem partes: abre inteiro, como antes.
        topo.append(agendaDoAssunto(id));
        if (s.resumo) corpo.append(el("p", "secao-resumo", s.resumo));
        montarSecao(s, corpo);
        return;
      }

      if (parte) {
        // Uma parte: tudo o que ela tem, numa tela só, e o caminho para as vizinhas.
        cabecalho(parte.titulo, true);
        marcarMenu(id, parte.id);
        corpo.classList.add("parte-corpo");
        if (parte.resumo) corpo.append(el("p", "secao-resumo", parte.resumo));
        montarParte(s, parte, corpo);
        const outras = el("nav", "outras-partes");
        outras.setAttribute("aria-label", `Outras partes de ${item.titulo}`);
        outras.append(el("span", "outras-titulo", `Mais em ${item.titulo}`));
        const geral = el("a", "pilula", "Visão geral");
        geral.href = `#${id}`;
        outras.append(geral);
        for (const p of partes) {
          const a = el("a", p.id === parte.id ? "pilula atual" : "pilula", p.titulo);
          a.href = `#${id}/${p.id}`;
          if (p.id === parte.id) a.setAttribute("aria-current", "page");
          outras.append(a);
        }
        corpo.append(outras);
        return;
      }

      // A visão geral: o resumo, quatro números, as partes e o gráfico principal.
      topo.append(agendaDoAssunto(id));
      if (s.resumo) corpo.append(el("p", "secao-resumo", s.resumo));
      if (s.cartoes.length) {
        const grade = el("div", "cartoes");
        s.cartoes.slice(0, NUMEROS_A_VISTA).forEach((c) => grade.append(montarCartao(c)));
        corpo.append(grade);
      }
      const bloco = el("section", "partes");
      bloco.append(el("h3", "partes-titulo", `${partes.length} partes de ${item.titulo}`));
      const lista = el("ul", "partes-lista");
      for (const p of partes) {
        const li = el("li");
        const a = el("a", "vidro parte");
        a.href = `#${id}/${p.id}`;
        const nome = el("span", "parte-titulo", p.titulo);
        nome.append(el("span", "seta", "→"));
        a.append(nome, el("span", "parte-resumo", p.resumo), el("span", "parte-conta", contagem(p)));
        li.append(a);
        lista.append(li);
      }
      bloco.append(lista);
      corpo.append(bloco);
      const principal = s.graficos[0];
      if (principal) {
        const grade = el("div", "graficos");
        grade.append(montarPeca(principal));
        corpo.append(grade);
      }
    })
    .catch(falhou);
}

// ------------------------------------------------------------------ partida

async function iniciar(): Promise<void> {
  const conteudo = document.getElementById("conteudo") as HTMLElement;
  ligarBusca();
  ligarGlossario(conteudo);
  document.querySelector(".menu-botao")?.addEventListener("click", () => {
    abrirMenu(!document.getElementById("lateral")?.classList.contains("aberta"));
  });
  document.addEventListener("keydown", (ev) => {
    const alvoDoTeclado = ev.target as HTMLElement;
    if (ev.key === "/" && !/^(INPUT|SELECT|TEXTAREA)$/.test(alvoDoTeclado.tagName)) {
      ev.preventDefault();
      abrirBusca();
    }
    if (ev.key === "Escape") abrirMenu(false);
  });

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
  montarMenu(painel);

  let vistaAtual: string | null = null;
  const desenhar = (): void => {
    // "#juros" abre a visão geral do assunto; "#juros/curva", uma parte; "#juros/g-curva-
    // prefixada" abre a parte em que o gráfico mora e vai até ele (a busca).
    const [alvo = "", bruto = ""] = location.hash.slice(1).split("/");
    const peca = decodeURIComponent(bruto);
    const item = painel.secoes.find((s) => s.id === alvo && s.id !== "resumo");
    const assunto = item ? alvo : "";
    const chave = assunto ? `${assunto}/${peca}` : "";
    abrirMenu(false);
    if (chave !== vistaAtual || !conteudo.firstChild) {
      vistaAtual = chave;
      if (assunto) vistaAssunto(painel, assunto, peca, conteudo);
      else {
        vistaInicio(painel, conteudo);
        marcarMenu("", "");
      }
      window.scrollTo(0, 0);
    }
    // "#assuntos" é uma âncora dentro do início, não um assunto.
    if (!assunto && alvo) document.getElementById(alvo)?.scrollIntoView();
    const ehParte = item?.subcategorias?.some((p) => p.id === peca) ?? false;
    if (assunto && peca && !ehParte) esperarEDepois(() => revelar(peca));
  };
  window.addEventListener("hashchange", desenhar);
  desenhar();
}

/** O assunto monta o conteúdo depois de ler o JSON dele: espera aparecer e então age. */
function esperarEDepois(fazer: () => void, tentativas = 40): void {
  const pronto = document.querySelector(
    "#conteudo .cartoes, #conteudo .graficos, #conteudo .mapa, #conteudo .parte-corpo details",
  );
  if (pronto || tentativas <= 0) window.setTimeout(fazer, 60);
  else window.setTimeout(() => esperarEDepois(fazer, tentativas - 1), 100);
}

void iniciar();
