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
import { agendaDaSemana, agendaDoAssunto } from "./calendario";
import { saiuPorUltimo } from "./saiu";
import { ligarGlossario } from "./glossario";
import { vistaGlossario } from "./glossario-pagina";
import { ligarNomesProprios, ligarTraducao, protegerNomeDeEstado } from "./traducao";
import { novoDesdeAUltimaVisita, seloNovo } from "./novidades";
import { montarEstados } from "./estados";
import { montarGrafico } from "./grafico";
import { montarMundo } from "./mundo";
import { montarDispersao } from "./dispersao";
import { montarPiramide } from "./piramide";
import { montarRetornos } from "./retornos";
import { comAlternativas } from "./alternativas";
import { montarComEscolha } from "./variantes";
import { el, guardar } from "./pecas";
import { listaSuspensa } from "./pontos";
import { montarSimulador } from "./simulador";
import { montarSimuladorReforma } from "./simulador-reforma";
import { montarSimuladorSelic } from "./simulador-selic";
import { montarComparadorSalario } from "./salario-minimo";
import type {
  Cartao,
  Estados,
  Grafico,
  ItemSecao,
  Mundo,
  Painel,
  ItemPergunta,
  Pergunta,
  Perguntas,
  Secao,
  SimuladorReforma,
  ComparadorSalario,
  SimuladorSelic,
  Subcategoria,
  LinhaTabela,
  Tabela,
} from "./tipos";

const NUMEROS_A_VISTA = 4;
const GRAFICOS_A_VISTA = 2;

const lidos = new Map<string, Promise<unknown>>();

/** As perguntas por tema, na ordem em que vêm (Caio, 19/11/2026: "organizar melhor as
 * perguntas dentro dos temas"). Sem tema no dado, um grupo só, sem nome. */
function porTema(perguntas: ItemPergunta[]): [string, ItemPergunta[]][] {
  const grupos = new Map<string, ItemPergunta[]>();
  for (const q of perguntas) {
    const tema = q.tema ?? "";
    grupos.set(tema, [...(grupos.get(tema) ?? []), q]);
  }
  return [...grupos.entries()];
}

/** As listas de perguntas, um título por tema; `primeiro` põe um tema na frente. */
function listasDePerguntas(perguntas: ItemPergunta[], primeiro = ""): HTMLElement[] {
  const grupos = porTema(perguntas).sort(
    (a, b) => Number(b[0] === primeiro) - Number(a[0] === primeiro),
  );
  const saida: HTMLElement[] = [];
  for (const [tema, lista] of grupos) {
    if (tema) saida.push(el("h3", "tema-perguntas", tema));
    const ul = el("ul", "perguntas");
    for (const q of lista) {
      const li = el("li");
      const a = el("a", "vidro pergunta");
      a.href = `#pergunta/${q.id}`;
      a.append(el("span", "pergunta-titulo", q.titulo), el("span", "seta", "→"));
      li.append(a);
      ul.append(li);
    }
    saida.push(ul);
  }
  return saida;
}

const PARTES_ANTIGAS: Record<string, string> = {
  "fiscal/meta": "resultado",
  "fiscal/receita-despesa": "gasto",
};

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
  if (c.texto) {
    // O resultado é um nome (a nota de crédito: "BB"), não um número.
    alvo.textContent = c.texto;
    return;
  }
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
  const quando = el("span", "", periodo(c.referencia, c.periodicidade));
  if (novoDesdeAUltimaVisita(c.secao, c.id, c.referencia)) quando.append(seloNovo());
  pe.append(quando);
  const proc = el("span", `procedencia ${c.procedencia}`);
  proc.append(el("i"), document.createTextNode(c.procedencia));
  pe.append(proc);
  no.append(pe);
  no.title = `Fonte: ${c.fonte}`;
  return no;
}

/** As linhas e colunas de uma tabela; linha com `grupo` novo ganha antes uma linha de título. */
function corpoDaTabela(colunas: string[], linhas: LinhaTabela[]): HTMLTableElement {
  const tabela = el("table", "dados");
  const cab = tabela.createTHead().insertRow();
  cab.append(el("th", "", ""));
  for (const c of colunas) cab.append(el("th", "", c));
  const corpo = tabela.createTBody();
  let grupo = "";
  for (const l of linhas) {
    if (l.grupo && l.grupo !== grupo) {
      const titulo = corpo.insertRow();
      titulo.className = "grupo";
      const th = el("th", "", l.grupo);
      th.colSpan = colunas.length + 1;
      titulo.append(th);
    }
    grupo = l.grupo ?? "";
    const tr = corpo.insertRow();
    if (l.grupo) tr.className = "no-grupo";
    const th = el("th", "", l.rotulo);
    protegerNomeDeEstado(th, l.rotulo);
    if (l.unidade) th.append(el("span", "sub", ` ${l.unidade}`));
    tr.append(th);
    if (l.textos?.length) {
      // Tabela de textos: o título da coluna alinha à esquerda, como o texto embaixo dele
      // (Caio, 15/11/2026, "Estados perto dos limites": "pode arrumar o lugar das colunas?").
      tabela.classList.add("de-textos");
      for (const x of l.textos) tr.append(el("td", x.length > 40 ? "texto longo" : "texto", x));
    } else for (const v of l.valores) tr.append(el("td", "", v === null ? "–" : numero(v, l.casas)));
  }
  return tabela;
}

function montarTabela(t: Tabela): HTMLElement {
  if (t.alternativas?.length) return comAlternativas(t, montarTabela, "t");
  const caixa = guardar(t.titulo, t.subtitulo, () => {
    const rolavel = el("div", "tabela-rolavel");
    const partes: HTMLElement[] = [];
    const visoes = t.visoes ?? [];
    if (visoes.length > 1) {
      // O período numa lista suspensa (Caio, 15/11/2026: "com parâmetro pra indicar se quer
      // ver qual trimestre ou qual ano"); o subtítulo diz o que está aberto.
      const legenda = el("p", "tabela-visao", visoes[0]?.subtitulo ?? "");
      const mostrar = (i: number): void => {
        const v = visoes[i];
        if (!v) return;
        rolavel.replaceChildren(corpoDaTabela(v.colunas, v.linhas));
        legenda.textContent = v.subtitulo;
      };
      const { caixa: lista } = listaSuspensa(
        `visao-${t.id}`,
        t.rotulo_visoes || "Período",
        visoes.map((v, i) => ({ valor: String(i), rotulo: v.rotulo, grupo: v.grupo || undefined })),
        "0",
        (valor) => mostrar(Number(valor)),
      );
      const barra = el("div", "tabela-controles");
      barra.append(lista, legenda);
      partes.push(barra);
      mostrar(0);
    } else {
      rolavel.append(corpoDaTabela(t.colunas, t.linhas));
    }
    const pe = el("footer", "grafico-pe");
    pe.append(el("span", "fonte", `Fonte: ${t.fonte}`));
    partes.push(rolavel, pe);
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
  if (g.alternativas?.length) return comAlternativas(g, montarPeca, "g");
  if (g.piramide) return montarPiramide(g, g.piramide);
  if (g.dispersao) return montarDispersao(g, g.dispersao);
  if (g.variantes?.length || g.escolher_series) return montarComEscolha(g);
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

/** O salário mínimo contra a inflação, no período que a pessoa escolhe (Trabalho › Renda). */
function caixaDoSalarioMinimo(c: ComparadorSalario): HTMLElement {
  const caixa = guardar(
    "Salário mínimo contra a inflação",
    "Escolha o período e compare o reajuste do mínimo com o IPCA",
    () => montarComparadorSalario(c),
  );
  caixa.id = "salario-minimo-comparador";
  return caixa;
}

/** O simulador da reforma do consumo; na parte dele (`#impostos/reforma`) já abre. */
function caixaDoSimuladorReforma(sim: SimuladorReforma): HTMLElement {
  const caixa = guardar(
    "Quanto de imposto vai numa compra?",
    "Escolha o valor, o tipo de compra e o ano, e veja o IBS e a CBS da reforma",
    () => montarSimuladorReforma(sim),
  );
  caixa.id = "simulador-reforma";
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
        "Mexa no juro, no crescimento, na inflação e no primário e veja para onde ela vai",
        () => montarSimulador(simulador),
      ),
    );
  }
  const simuladorSelic = s.simulador_selic;
  if (simuladorSelic) alvo.append(caixaDoSimuladorSelic(simuladorSelic));
  const simuladorReforma = s.simulador_reforma;
  if (simuladorReforma) alvo.append(caixaDoSimuladorReforma(simuladorReforma));
  const comparador = s.salario_minimo;
  if (comparador) alvo.append(caixaDoSalarioMinimo(comparador));
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
  const desdeAVisita = novoDesdeAUltimaVisita(c.secao, c.id, c.referencia);
  if (aoVivo) quando.append(el("span", "novo", "novo"));
  else if (desdeAVisita) quando.append(seloNovo());
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
  // Os andares: as perguntas primeiro, os dados depois (16/11/2026).
  if (painel.perguntas?.length) {
    // Recolhido: oito títulos longos ocupavam o menu inteiro (Caio, 19/11/2026: "recolha as
    // perguntas pra não ocupar tanto espaço e a pessoa poder escolher outras perguntas").
    // Abre sozinho quando a pessoa está numa pergunta e no toque de "Perguntas".
    const grupo = el("details", "menu-grupo menu-perguntas");
    const resumo = el("summary", "menu-andar");
    resumo.append(
      el("span", "", "Perguntas"),
      el("small", "", `${painel.perguntas.length}`),
    );
    grupo.append(resumo);
    for (const [tema, lista] of porTema(painel.perguntas)) {
      if (tema) grupo.append(el("p", "menu-categoria menu-tema", tema));
      const ul = el("ul");
      for (const q of lista) {
        const li = el("li");
        const a = el("a", "menu-assunto menu-pergunta", q.titulo);
        a.href = `#pergunta/${q.id}`;
        a.dataset.assunto = `pergunta/${q.id}`;
        li.append(a);
        ul.append(li);
      }
      grupo.append(ul);
    }
    menu.append(grupo, el("p", "menu-andar menu-andar-dados", "Dados"));
  }
  for (const c of categorias(painel)) {
    const grupo = el("div", "menu-grupo");
    // O Laboratório é um andar, não uma categoria dos Dados.
    const andar = c.titulo === "Laboratório";
    grupo.append(el("p", andar ? "menu-andar menu-andar-dados" : "menu-categoria", c.titulo));
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
  // O glossário inteiro, de A a Z (revisão das telas, 15/11/2026).
  const consulta = el("div", "menu-grupo");
  consulta.append(el("p", "menu-categoria", "Consulta"));
  const glossario = el("a", "menu-assunto", "Glossário");
  glossario.href = "#glossario";
  glossario.dataset.assunto = "glossario";
  consulta.append(glossario);
  menu.append(consulta);
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
  const perguntas = menu.querySelector<HTMLDetailsElement>("details.menu-perguntas");
  if (perguntas && assunto.startsWith("pergunta/")) perguntas.open = true;
  for (const a of menu.querySelectorAll<HTMLAnchorElement>("a[data-parte]")) {
    const aqui = a.dataset.parte === `${assunto}/${parte}`;
    a.classList.toggle("ativo", aqui);
    if (aqui) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  }
  // O menu rola por dentro: o assunto aberto (Riscos, no pé) fica à vista, sem mexer na página.
  marcarRolagem(menu);
  const ativo = menu.querySelector<HTMLElement>("a.ativo[data-parte], a.ativo[data-assunto]");
  if (ativo && menu.scrollHeight > menu.clientHeight) {
    const m = menu.getBoundingClientRect();
    const a = ativo.getBoundingClientRect();
    if (a.top < m.top || a.bottom > m.bottom) {
      menu.scrollTop += a.top - m.top - menu.clientHeight / 3;
    }
  }
}

/** Diz ao CSS se o menu tem o que rolar para cima ou para baixo (o texto se apaga na ponta). */
function marcarRolagem(menu: HTMLElement): void {
  const marcar = (): void => {
    const resto = menu.scrollHeight - menu.clientHeight - menu.scrollTop;
    menu.classList.toggle("mais-acima", menu.scrollTop > 2);
    menu.classList.toggle("mais-abaixo", resto > 2);
  };
  if (!menu.dataset.rolagem) {
    menu.dataset.rolagem = "1";
    menu.addEventListener("scroll", marcar, { passive: true });
    window.addEventListener("resize", marcar);
  }
  window.requestAnimationFrame(marcar);
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
    "As perguntas que mais se fazem sobre a economia, respondidas com o dado oficial, a data e a fonte.",
  );
  lema.style.setProperty("--i", "2");
  heroi.append(selo, titulo, lema);

  const essenciais = el("section", "essenciais entra");
  essenciais.style.setProperty("--i", "3");
  essenciais.setAttribute("aria-label", "Os números essenciais");

  void ler<Secao>("resumo.json")
    .then((resumo) => {
      if (resumo.saiu?.length) essenciais.after(saiuPorUltimo(resumo.saiu));
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
    .catch(() => {
      essenciais.remove();
    });

  // As perguntas são a entrada (Caio, 16/11/2026: "o gancho vai ser problemas e perguntas
  // que as pessoas buscam algum tipo de resposta"). Só a pergunta: a resposta abre no clique.
  const bloco = el("section", "bloco");
  bloco.id = "perguntas";
  bloco.append(el("p", "sobretitulo", "Perguntas"));
  const h2 = el("h2");
  h2.append(
    document.createTextNode("O que você quer entender? "),
    el("span", "apagado", "Toque numa pergunta."),
  );
  bloco.append(h2, ...listasDePerguntas(painel.perguntas ?? []));
  if (!painel.perguntas?.length) bloco.remove();

  // Os dados, por assunto, só com o nome: quem quer o número vai direto.
  const dados = el("section", "bloco dados");
  dados.id = "assuntos";
  dados.append(el("p", "sobretitulo", "Dados"), el("h3", "dados-titulo", "Todos os números, por assunto"));
  for (const c of categorias(painel)) {
    const linha = el("p", "dados-linha");
    linha.append(el("span", "dados-categoria", c.titulo));
    for (const s of c.secoes) {
      const a = el("a", "", s.titulo);
      a.href = `#${s.id}`;
      if (!s.ok) a.title = "Não pôde ser atualizado nesta rodada.";
      linha.append(a);
    }
    dados.append(linha);
  }
  // A agenda da semana, atrás de um clique: o calendário do IBGE só é lido quando abre.
  const agenda = agendaDaSemana(painel.secoes);
  agenda.classList.add("entra");
  agenda.style.setProperty("--i", "4");
  conteudo.replaceChildren(heroi, essenciais, bloco, agenda, dados);
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
    p.extras.some((e) => e.startsWith("simulador")) ? "simulador" : "",
    p.extras.includes("alertas") ? "painel" : "",
    p.extras.includes("salario-minimo") ? "comparador" : "",
  ]
    .filter(Boolean)
    .join(" · ");
}

/** A parte em que a peça do endereço ("c-ipca-12m", "t-alertas") mora. */
function parteDaPeca(
  partes: Subcategoria[],
  peca: string,
  s?: Secao,
): Subcategoria | undefined {
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
  const direto = partes.find((p) => p[campo].includes(id));
  if (direto || !s || campo === "cartoes") return direto;
  // Atrás da lista de outro gráfico ou tabela: a parte é a do principal.
  const lista: { id: string; alternativas?: { id: string }[] }[] =
    campo === "graficos" ? s.graficos : s.tabelas;
  const principal = lista.find((x) => x.alternativas?.some((a) => a.id === id));
  return principal ? partes.find((p) => p[campo].includes(principal.id)) : undefined;
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
      "Mexa no juro, no crescimento, na inflação e no primário e veja para onde ela vai",
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
  const simuladorReforma = s.simulador_reforma;
  if (p.extras.includes("simulador-reforma") && simuladorReforma) {
    const caixa = caixaDoSimuladorReforma(simuladorReforma);
    if (caixa instanceof HTMLDetailsElement) caixa.open = true;
    alvo.append(caixa);
  }
  const comparador = s.salario_minimo;
  if (p.extras.includes("salario-minimo") && comparador) {
    const caixa = caixaDoSalarioMinimo(comparador);
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

/** As partes do assunto, em cartões, na visão geral. */
function listaDePartes(id: string, titulo: string, partes: Subcategoria[]): HTMLElement {
  const bloco = el("section", "partes");
  bloco.append(el("h3", "partes-titulo", `${partes.length} partes de ${titulo}`));
  const lista = el("ul", "partes-lista");
  for (const p of partes) {
    const li = el("li");
    const a = el("a", "vidro parte");
    a.href = `#${id}/${p.id}`;
    const nome = el("span", "parte-titulo", p.titulo);
    nome.append(el("span", "seta", "→"));
    a.append(nome, el("span", "parte-resumo", p.resumo));
    const conta = contagem(p);
    if (conta) a.append(el("span", "parte-conta", conta));
    li.append(a);
    lista.append(li);
  }
  bloco.append(lista);
  return bloco;
}

/** Atalhos para partes de outros assuntos que tratam do mesmo (o efeito da Selic na
 * inflação e na dívida). */
function vejaTambem(p: Subcategoria): HTMLElement | null {
  if (!p.veja?.length) return null;
  const bloco = el("section", "partes veja");
  bloco.append(el("h3", "partes-titulo", "Veja também"));
  const lista = el("ul", "partes-lista");
  for (const elo of p.veja) {
    const li = el("li");
    const a = el("a", "vidro parte");
    a.href = elo.endereco;
    const nome = el("span", "parte-titulo", elo.titulo);
    nome.append(el("span", "seta", "→"));
    a.append(nome);
    if (elo.resumo) a.append(el("span", "parte-resumo", elo.resumo));
    li.append(a);
    lista.append(li);
  }
  bloco.append(lista);
  return bloco;
}

/** Embaixo de uma parte: a visão geral e as vizinhas. */
function outrasPartes(id: string, titulo: string, partes: Subcategoria[], atual: string): HTMLElement {
  const outras = el("nav", "outras-partes");
  outras.setAttribute("aria-label", `Outras partes de ${titulo}`);
  outras.append(el("span", "outras-titulo", `Mais em ${titulo}`));
  const geral = el("a", "pilula", "Visão geral");
  geral.href = `#${id}`;
  outras.append(geral);
  for (const p of partes) {
    const a = el("a", p.id === atual ? "pilula atual" : "pilula", p.titulo);
    a.href = `#${id}/${p.id}`;
    if (p.id === atual) a.setAttribute("aria-current", "page");
    outras.append(a);
  }
  return outras;
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
    void ler<Estados>(item.arquivo)
      .then((e) => {
        const partes = e.subcategorias ?? [];
        // "#estados/uf-SP" abre as contas de SP; "#estados/m-divida", o mapa nessa métrica.
        const uf = peca.startsWith("uf-") ? peca.slice(3) : "";
        const alvo = uf ? "estado" : peca.startsWith("m-") ? "mapa" : peca;
        const parte = partes.find((p) => p.id === alvo);
        if (parte) {
          cabecalho(parte.titulo, true);
          marcarMenu(id, parte.id);
          corpo.classList.add("parte-corpo");
          if (parte.resumo) corpo.append(el("p", "secao-resumo", parte.resumo));
          corpo.append(montarEstados(e, parte.id, uf), outrasPartes(id, item.titulo, partes, parte.id));
          return;
        }
        topo.append(agendaDoAssunto(id));
        corpo.append(el("p", "secao-resumo", e.resumo));
        if (partes.length) corpo.append(listaDePartes(id, item.titulo, partes));
        corpo.append(montarEstados(e, "", ""));
      })
      .catch(falhou);
    return;
  }
  void ler<Secao>(item.arquivo)
    .then((s) => {
      const partes = s.subcategorias ?? [];
      const parte =
        partes.find((p) => p.id === peca) ?? (peca ? parteDaPeca(partes, peca, s) : undefined);

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
        const veja = vejaTambem(parte);
        if (veja) corpo.append(veja);
        corpo.append(outrasPartes(id, item.titulo, partes, parte.id));
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
      corpo.append(listaDePartes(id, item.titulo, partes));
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

// ------------------------------------------------------------------ uma pergunta

/** O número de um cartão dos Dados, sem o id (a mesma peça pode aparecer duas vezes aqui). */
function numeroDaPergunta(c: Cartao): HTMLElement {
  const no = montarCartao(c);
  no.removeAttribute("id");
  return no;
}

/** Uma pergunta aberta: a resposta, até três números e as explicações. A primeira explicação
 *  já vem aberta; as outras mostram a frase e abrem o número e o gráfico no clique. */
function vistaPergunta(painel: Painel, id: string, conteudo: HTMLElement): void {
  const item = painel.perguntas?.find((q) => q.id === id);
  if (!item) {
    location.hash = "";
    return;
  }
  const secao = el("section", "secao pergunta-aberta");
  const topo = el("header", "secao-topo");
  const trilha = el("nav", "trilha");
  trilha.setAttribute("aria-label", "Onde você está");
  const volta = el("a", "", "Perguntas");
  volta.href = "#perguntas";
  trilha.append(volta);
  topo.append(trilha, el("h2", "", item.titulo));
  const corpo = el("div", "secao-corpo");
  corpo.append(el("p", "secao-resumo", item.resposta));
  secao.append(topo, corpo);
  conteudo.replaceChildren(secao);
  marcarMenu(`pergunta/${id}`, "");

  void ler<Perguntas>("perguntas.json")
    .then((arquivo) => {
      const q: Pergunta | undefined = arquivo.perguntas.find((x) => x.id === id);
      if (!q) return;
      if (q.numeros.length) {
        const numeros = el("div", "cartoes pergunta-numeros");
        for (const c of q.numeros) numeros.append(numeroDaPergunta(c));
        corpo.append(numeros);
      }
      corpo.append(el("h3", "explicacoes-titulo", "As explicações, e o dado de cada uma"));
      q.blocos.forEach((b, i) => {
        const caixa = el("details", "vidro explicacao");
        const resumo = el("summary");
        const cabeca = el("span", "explicacao-cabeca");
        cabeca.append(
          el("span", "explicacao-numero", String(i + 1)),
          el("span", "explicacao-titulo", b.titulo),
        );
        resumo.append(cabeca, el("span", "explicacao-texto", b.texto));
        const dentro = el("div", "explicacao-corpo");
        caixa.append(resumo, dentro);
        let montada = false;
        const montar = (): void => {
          if (montada) return;
          montada = true;
          if (b.numeros.length) {
            const numeros = el("div", "cartoes explicacao-numeros");
            for (const c of b.numeros) numeros.append(numeroDaPergunta(c));
            dentro.append(numeros);
          }
          if (b.grafico) {
            const grade = el("div", "graficos");
            grade.append(montarPeca(b.grafico));
            dentro.append(grade);
          }
          if (b.tabela) {
            const tabela = montarTabela(b.tabela);
            tabela.removeAttribute("id");
            dentro.append(tabela);
          }
          const elo = el("a", "grafico-elo", `Mais em ${b.assunto_titulo || "Dados"}`);
          elo.append(el("span", "seta", "→"));
          elo.href = b.elo;
          dentro.append(elo);
        };
        caixa.addEventListener("toggle", () => {
          if (caixa.open) montar();
        });
        if (i === 0) {
          caixa.open = true;
          montar();
        }
        corpo.append(caixa);
      });
      if (q.conclusao) {
        const fecho = el("section", "vidro conclusao");
        fecho.append(
          el("h3", "conclusao-titulo", "Juntando as peças"),
          el("p", "conclusao-texto", q.conclusao),
        );
        corpo.append(fecho);
      }
      // Recolhidas: a pessoa abre quando quiser trocar de pergunta.
      const outras = el("details", "outras-perguntas");
      const quantas = (painel.perguntas ?? []).filter((o) => o.id !== id).length;
      const chamada = el("summary", "sobretitulo");
      chamada.append(el("span", "", "Outras perguntas"), el("small", "", `${quantas}`));
      outras.append(chamada);
      outras.append(
        ...listasDePerguntas(
          (painel.perguntas ?? []).filter((o) => o.id !== id),
          item?.tema ?? "",
        ),
      );
      corpo.append(outras);
    })
    .catch((erro: unknown) => {
      corpo.append(el("p", "aviso", `Não foi possível carregar (${String(erro)}).`));
    });
}

async function iniciar(): Promise<void> {
  const conteudo = document.getElementById("conteudo") as HTMLElement;
  ligarTraducao();
  ligarNomesProprios();
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
    const [pedido = "", bruto = ""] = location.hash.slice(1).split("/");
    // Assunto que entrou em outro (16/11/2026): "#pobreza/desigualdade" abre em Trabalho.
    const novo = painel.antigos?.[pedido];
    if (novo) {
      history.replaceState(null, "", `#${novo}${bruto ? `/${bruto}` : ""}`);
    }
    const alvo = novo ?? pedido;
    // Parte que entrou em outra (19/11/2026): a meta fiscal mora em "Primário, juros e
    // meta", e a receita e a despesa da União em "Receita e gasto".
    const parteNova = PARTES_ANTIGAS[`${alvo}/${bruto}`];
    if (parteNova) history.replaceState(null, "", `#${alvo}/${parteNova}`);
    const peca = decodeURIComponent(parteNova ?? bruto);
    const item = painel.secoes.find((s) => s.id === alvo && s.id !== "resumo");
    const assunto = item ? alvo : "";
    const chave = assunto ? `${assunto}/${peca}` : "";
    abrirMenu(false);
    if (alvo === "glossario") {
      if (vistaAtual !== "glossario" || !conteudo.firstChild) {
        vistaAtual = "glossario";
        vistaGlossario(conteudo, peca);
        marcarMenu("glossario", "");
        window.scrollTo(0, 0);
      } else if (peca) document.getElementById(`termo-${peca}`)?.scrollIntoView();
      return;
    }
    if (alvo === "pergunta" && peca) {
      if (vistaAtual !== `pergunta/${peca}` || !conteudo.firstChild) {
        vistaAtual = `pergunta/${peca}`;
        vistaPergunta(painel, peca, conteudo);
        window.scrollTo(0, 0);
      }
      return;
    }
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
    "#conteudo .cartoes, #conteudo .graficos, #conteudo .mapa, #conteudo .ficha-corpo, #conteudo .parte-corpo details",
  );
  if (pronto || tentativas <= 0) window.setTimeout(fazer, 60);
  else window.setTimeout(() => esperarEDepois(fazer, tentativas - 1), 100);
}

void iniciar();
