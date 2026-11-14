// O painel de alerta da aba de riscos: cada indicador como um ponto na régua da própria
// história, com o lado ruim sempre à direita. Fica guardado; abre no clique.
// A cor nunca vai sozinha: indicador "aceso" leva ▲ e a frase.
// Caio, 14/11/2026: "classifique, não precisa mostrar tudo de uma vez [...] o que falta dizer é
// o que significa, por que é um alerta, o que isso pode levar". Os grupos abrem um de cada vez
// (o com mais acesos em cima), os acesos ficam num atalho, e cada linha abre a explicação.

import "./alertas.css";
import { comUnidade, data, numero, periodo } from "./formato";
import {
  carregarPaises,
  comparar,
  dosPaises,
  EXTRAS,
  listaDeParecidos,
  opcoesDeGrupo,
  PARES,
  semPar,
  type Comparacao,
  type Dados,
  type Par,
} from "./alertas-paises";
import { el, guardar } from "./pecas";
import { listaSuspensa } from "./pontos";
import type { Alerta } from "./tipos";

/** Daqui para cima o indicador está no quinto pior da própria história. */
const ACESO = 80;
/** Quantos acesos aparecem no atalho antes do "+N". */
const FICHAS = 6;

export function acesos(alertas: Alerta[]): number {
  return alertas.filter((a) => a.pior_que >= ACESO).length;
}

/** A régua: o melhor valor que a história já viu à esquerda, o pior à direita. */
function regua(a: Alerta, antes: number | null = null): HTMLElement {
  const alto = a.pior_quando === "alto";
  const [melhor, pior] = alto ? [a.minimo, a.maximo] : [a.maximo, a.minimo];
  const amplitude = a.maximo - a.minimo || 1;
  const pos = (v: number): string => {
    const fracao = alto ? (v - a.minimo) / amplitude : (a.maximo - v) / amplitude;
    return `${Math.min(100, Math.max(0, fracao * 100))}%`;
  };
  const caixa = el("div", "alerta-regua");
  const trilho = el("span", "alerta-trilho");
  trilho.setAttribute("aria-hidden", "true");
  const mediana = el("i", "alerta-mediana");
  mediana.style.left = pos(a.mediana);
  trilho.append(mediana);
  if (a.limite) {
    const limite = el("i", "alerta-limite");
    limite.style.left = pos(a.limite.valor);
    trilho.append(limite);
  }
  if (antes !== null) {
    // Na vista do ano: o ponto de um ano antes, vazado, e um fio até o de hoje.
    const de = pos(antes);
    const ate = pos(a.valor);
    const fio = el("i", "alerta-fio");
    fio.style.left = `min(${de}, ${ate})`;
    fio.style.width = `calc(max(${de}, ${ate}) - min(${de}, ${ate}))`;
    const velho = el("i", "alerta-ponto antigo");
    velho.style.left = de;
    trilho.append(fio, velho);
  }
  const ponto = el("i", "alerta-ponto");
  ponto.style.left = pos(a.valor);
  trilho.append(ponto);
  const pontas = el("span", "alerta-pontas");
  pontas.append(el("span", "", numero(melhor, a.casas)), el("span", "", numero(pior, a.casas)));
  caixa.append(trilho, pontas);
  return caixa;
}

/** O que abre ao tocar na linha: o que é, por que é alerta, no que pode dar e a história. */
function explicacao(a: Alerta): HTMLElement {
  const caixa = el("div", "alerta-texto");
  const campo = (titulo: string, texto: string): void => {
    if (!texto) return;
    const p = el("p");
    p.append(el("b", "", titulo), document.createTextNode(` ${texto}`));
    caixa.append(p);
  };
  campo("O que é.", a.significa ?? "");
  campo("Por que é alerta.", a.por_que ?? "");
  campo("Pode levar a.", a.pode_levar ?? "");
  const desde = data(a.desde).getUTCFullYear();
  const lado = a.pior_quando === "alto" ? "alto" : "baixo";
  const historia = el(
    "p",
    "alerta-historia",
    `Desde ${desde}, foi de ${numero(a.minimo, a.casas)} a ${numero(a.maximo, a.casas)}, com ` +
      `mediana ${numero(a.mediana, a.casas)}; o lado ruim é o valor ${lado}. Hoje está pior ` +
      `que ${numero(a.pior_que, 0)} % da própria história.` +
      (a.limite ? ` ${a.limite.rotulo}: ${numero(a.limite.valor, a.casas)}.` : ""),
  );
  caixa.append(historia);
  return caixa;
}

function linha(a: Alerta, modo: "historia" | "tendencia" = "historia"): HTMLElement {
  const aceso = a.pior_que >= ACESO;
  const no = el("details", aceso ? "alerta aceso" : "alerta");
  no.id = `a-${a.id}`;
  const cabeca = el("summary", "alerta-linha");

  const nome = el("div", "alerta-nome");
  nome.append(
    el("span", "", a.nome),
    el("small", "", `${periodo(a.referencia, a.periodicidade)} · ${a.fonte}`),
  );
  if (a.limite) {
    // O traço do limite pode ficar atrás do ponto: o número vai também por escrito.
    const limite = el("small", "alerta-limite-texto");
    limite.append(el("i"), document.createTextNode(`${a.limite.rotulo}: ${numero(a.limite.valor, a.casas)}`));
    nome.append(limite);
  }

  const valor = el("div", "alerta-valor");
  valor.append(el("strong", "", comUnidade(a.valor, a.unidade, a.casas)));
  const r = modo === "tendencia" ? rumo(a) : null;
  if (r && a.ha_um_ano !== null && a.ha_um_ano !== undefined) {
    const selo = el("span", RUMOS[r].classe);
    selo.append(el("i", "", RUMOS[r].simbolo), document.createTextNode(RUMOS[r].selo));
    const quando = a.ha_um_ano_em ? ` em ${periodo(a.ha_um_ano_em, a.periodicidade)}` : "";
    valor.append(selo, el("small", "alerta-antes", `era ${numero(a.ha_um_ano, a.casas)}${quando}`));
  } else {
    const selo = el("span", aceso ? "situacao acima" : "situacao");
    if (aceso) selo.append(el("i", "", "▲"));
    selo.append(document.createTextNode(`pior que ${numero(a.pior_que, 0)} % da história`));
    valor.append(selo);
  }

  const abre = el("span", "alerta-abre", "›");
  abre.setAttribute("aria-hidden", "true");
  cabeca.append(nome, regua(a, modo === "tendencia" ? (a.ha_um_ano ?? null) : null), valor, abre);
  no.append(cabeca, explicacao(a));
  return no;
}

/** Abre o grupo e a linha do indicador, e leva a tela até ela. */
function irAte(id: string): void {
  const no = document.getElementById(`a-${id}`);
  if (!(no instanceof HTMLDetailsElement)) return;
  const grupo = no.parentElement?.closest("details");
  if (grupo instanceof HTMLDetailsElement) grupo.open = true;
  no.open = true;
  no.scrollIntoView({ behavior: "smooth", block: "center" });
  no.classList.add("achado");
  window.setTimeout(() => no.classList.remove("achado"), 2200);
}

/** A vista de sempre: cada indicador na régua da própria história, por grupo. */
function vistaHistoria(alertas: Alerta[]): HTMLElement[] {
  const partes: HTMLElement[] = [];
  // Os acesos primeiro, como atalho: o toque abre o grupo e a linha.
  const ligadosAgora = alertas
    .filter((a) => a.pior_que >= ACESO)
    .sort((a, b) => b.pior_que - a.pior_que);
  if (ligadosAgora.length) {
    const atalho = el("div", "alerta-atalhos");
    atalho.append(el("p", "alerta-atalhos-titulo", `Acesos agora (${ligadosAgora.length})`));
    const lista = el("div", "alerta-fichas");
    const ficha = (a: Alerta): HTMLElement => {
      const b = el("button", "alerta-ficha");
      b.type = "button";
      b.append(el("i", "", "▲"), document.createTextNode(a.nome));
      b.addEventListener("click", () => irAte(a.id));
      return b;
    };
    // Os seis piores à vista; o resto num toque.
    ligadosAgora.slice(0, FICHAS).forEach((a) => lista.append(ficha(a)));
    const resto = ligadosAgora.slice(FICHAS);
    if (resto.length) {
      const mais = el("button", "alerta-ficha mais", `+${resto.length}`);
      mais.type = "button";
      mais.setAttribute("aria-label", `Mostrar mais ${resto.length} acesos`);
      mais.addEventListener("click", () => mais.replaceWith(...resto.map(ficha)));
      lista.append(mais);
    }
    atalho.append(lista);
    partes.push(atalho);
  }

  for (const [grupo, itens] of porGrupo(alertas)) {
    const n = acesos(itens);
    const legenda = el("p", "alerta-legenda");
    legenda.append(
      el("span", "", "← melhor da história"),
      el("span", "alerta-legenda-meio", "traço: mediana"),
      el("span", "", "pior da história →"),
    );
    partes.push(
      caixaDeGrupo(
        grupo,
        itens.map((a) => a.pior_que >= ACESO),
        n ? `${n} de ${itens.length} ${n === 1 ? "aceso" : "acesos"}` : `0 de ${itens.length} acesos`,
        n > 0,
        [legenda, ...itens.map((a) => linha(a))],
      ),
    );
  }
  const primeiros = alertas.map((a) => data(a.desde).getUTCFullYear());
  partes.push(
    el(
      "p",
      "nota",
      "Cada linha põe o valor mais recente na régua de tudo o que o indicador já marcou " +
        `(desde ${Math.min(...primeiros)}, ou desde que a série existe). "Aceso" (▲) é estar pior ` +
        "que 80 % da própria história. Não é previsão de crise nem nota de risco: um " +
        "indicador pode estar no pior da história dele e ainda assim longe de um nível perigoso, " +
        "e o contrário. Onde há limite oficial, ele aparece como traço amarelo.",
    ),
  );
  return partes;
}

/** Os grupos do painel, o com mais acesos (em proporção) primeiro. */
function porGrupo(alertas: Alerta[]): [string, Alerta[]][] {
  const grupos = new Map<string, Alerta[]>();
  for (const a of alertas) grupos.set(a.grupo, [...(grupos.get(a.grupo) ?? []), a]);
  return [...grupos].sort(([, x], [, y]) => acesos(y) / y.length - acesos(x) / x.length);
}

/** Uma caixa que abre no toque: o nome, um ponto por item (cheio se ruim) e a conta. */
function caixaDeGrupo(
  nome: string,
  ruins: boolean[],
  conta: string,
  temRuim: boolean,
  dentro: HTMLElement[],
  aberta = false,
): HTMLElement {
  const bloco = el("details", "alerta-grupo-caixa");
  bloco.open = aberta;
  const cabeca = el("summary", "alerta-grupo");
  const pontos = el("span", "alerta-grupo-pontos");
  pontos.setAttribute("aria-hidden", "true");
  for (const r of [...ruins].sort((a, b) => Number(b) - Number(a))) pontos.append(el("i", r ? "aceso" : ""));
  cabeca.append(
    el("span", "alerta-grupo-nome", nome),
    pontos,
    el("small", temRuim ? "alerta-grupo-conta tem" : "alerta-grupo-conta", conta),
    el("span", "seta", "→"),
  );
  const lista = el("div", "alerta-lista");
  lista.append(...dentro);
  bloco.append(cabeca, lista);
  return bloco;
}

// ------------------------------------------------------------------ o que mudou em um ano

type Rumo = "piorou" | "igual" | "melhorou";

/** Andar 5 pontos ou mais na régua da história conta como mudança. */
const MUDOU = 5;

function rumo(a: Alerta): Rumo | null {
  if (a.pior_que_ha_um_ano === null || a.pior_que_ha_um_ano === undefined) return null;
  const passo = a.pior_que - a.pior_que_ha_um_ano;
  return passo >= MUDOU ? "piorou" : passo <= -MUDOU ? "melhorou" : "igual";
}

const RUMOS: Record<Rumo, { titulo: string; selo: string; simbolo: string; classe: string }> = {
  piorou: { titulo: "Pioraram em um ano", selo: "piorou", simbolo: "▲", classe: "situacao acima" },
  igual: { titulo: "Quase iguais", selo: "quase igual", simbolo: "=", classe: "situacao" },
  melhorou: { titulo: "Melhoraram em um ano", selo: "melhorou", simbolo: "▼", classe: "situacao dentro" },
};

function vistaTendencia(alertas: Alerta[]): HTMLElement[] {
  const partes: HTMLElement[] = [];
  const legenda = el("p", "alerta-legenda");
  legenda.append(
    el("span", "", "← melhor da história"),
    el("span", "alerta-legenda-meio", "○ um ano antes · ● hoje"),
    el("span", "", "pior da história →"),
  );
  partes.push(legenda);
  for (const r of ["piorou", "igual", "melhorou"] as Rumo[]) {
    const itens = alertas
      .filter((a) => rumo(a) === r)
      .sort((a, b) => b.pior_que - (b.pior_que_ha_um_ano ?? 0) - (a.pior_que - (a.pior_que_ha_um_ano ?? 0)));
    if (!itens.length) continue;
    partes.push(
      caixaDeGrupo(
        RUMOS[r].titulo,
        itens.map(() => r === "piorou"),
        `${itens.length} ${itens.length === 1 ? "indicador" : "indicadores"}`,
        r === "piorou",
        itens.map((a) => linha(a, "tendencia")),
        r === "piorou",
      ),
    );
  }
  const sem = alertas.filter((a) => rumo(a) === null);
  if (sem.length) {
    partes.push(el("p", "alerta-intro", `Sem o dado de um ano antes: ${sem.map((a) => a.nome).join("; ")}.`));
  }
  partes.push(
    el(
      "p",
      "nota",
      "Compara o valor de hoje com o de um ano antes (o ponto mais perto de 12 meses atrás), " +
        "os dois na régua da história do próprio indicador. Andou 5 pontos ou mais para o lado " +
        "ruim: piorou; para o lado bom: melhorou. Serve para ver o rumo: um indicador pode estar " +
        "num nível bom e piorando depressa, ou num nível ruim e melhorando.",
    ),
  );
  return partes;
}

// ------------------------------------------------------------------ outros países

function reguaDosPaises(c: Comparacao, par: Par, aceso: boolean): HTMLElement {
  const ordenados = [...c.valores].sort((a, b) => a - b);
  const q = (f: number): number => ordenados[Math.round(f * (ordenados.length - 1))] ?? 0;
  // Do 5º ao 95º percentil (e o Brasil): um país com inflação de 200 % não achata o resto.
  const lo = Math.min(q(0.05), c.brasil);
  const hi = Math.max(q(0.95), c.brasil);
  const alto = par.pior_quando === "alto";
  const amplitude = hi - lo || 1;
  const pos = (v: number): string => {
    const f = alto ? (v - lo) / amplitude : (hi - v) / amplitude;
    return `${Math.min(100, Math.max(0, f * 100))}%`;
  };
  const caixa = el("div", "alerta-regua");
  const trilho = el("span", "alerta-trilho");
  trilho.setAttribute("aria-hidden", "true");
  for (const v of c.valores) {
    const p = el("i", "alerta-par");
    p.style.left = pos(v);
    trilho.append(p);
  }
  const med = el("i", "alerta-mediana");
  med.style.left = pos(c.mediana);
  trilho.append(med);
  const br = el("i", aceso ? "alerta-ponto aceso" : "alerta-ponto");
  br.style.left = pos(c.brasil);
  trilho.append(br);
  const pontas = el("span", "alerta-pontas");
  const casas = 1;
  pontas.append(el("span", "", numero(alto ? lo : hi, casas)), el("span", "", numero(alto ? hi : lo, casas)));
  caixa.append(trilho, pontas);
  return caixa;
}

/** "os emergentes", "a América Latina": para a legenda. */
function quem(grupo: string): string {
  return (
    { G200: "os emergentes", G205: "a América Latina", G110: "os avançados", G001: "o mundo" }[grupo] ??
    "os países"
  );
}

function linhaDoPais(
  id: string,
  nome: string,
  par: Par,
  c: Comparacao,
  d: Dados,
  grupo: string,
  texto: string[],
): HTMLElement {
  const aceso = c.pior_que >= ACESO;
  const no = el("details", aceso ? "alerta aceso entre-paises" : "alerta entre-paises");
  no.id = `ap-${id}`;
  const cabeca = el("summary", "alerta-linha");
  const nomeNo = el("div", "alerta-nome");
  nomeNo.append(
    el("span", "", par.nome),
    el("small", "", `${c.ano} · ${c.fonte}${nome !== par.nome ? ` · no painel: ${nome}` : ""}`),
  );
  const valor = el("div", "alerta-valor");
  const unidade = par.unidade ?? d.m.metricas.find((x) => x.id === par.metrica)?.unidade ?? "";
  valor.append(el("strong", "", `${numero(c.brasil, 1)}${unidade ? ` ${unidade}` : ""}`));
  const selo = el("span", aceso ? "situacao acima" : "situacao");
  if (aceso) selo.append(el("i", "", "▲"));
  selo.append(document.createTextNode(`pior que ${numero(c.pior_que, 0)} %`));
  selo.title = `Pior que ${numero(c.pior_que, 0)} % ${dosPaises(d, grupo, c.n)}`;
  valor.append(selo);
  const abre = el("span", "alerta-abre", "›");
  abre.setAttribute("aria-hidden", "true");
  cabeca.append(nomeNo, reguaDosPaises(c, par, aceso), valor, abre);

  const corpo = el("div", "alerta-texto");
  const medias: string[] = [`mediana ${dosPaises(d, grupo, c.n)}: ${numero(c.mediana, 1)}`];
  if (grupo !== "G205" && c.latina !== null) medias.push(`da América Latina e Caribe: ${numero(c.latina, 1)}`);
  if (grupo !== "G200" && c.emergentes !== null) medias.push(`dos emergentes: ${numero(c.emergentes, 1)}`);
  const p1 = el("p");
  p1.append(el("b", "", "Brasil e os outros."), document.createTextNode(` Brasil: ${numero(c.brasil, 1)}; ${medias.join("; ")}.`));
  corpo.append(p1);
  if (c.parecidos.length) {
    const p2 = el("p");
    p2.append(el("b", "", "Os parecidos."), document.createTextNode(` ${listaDeParecidos(c, 1)}.`));
    corpo.append(p2);
  }
  for (const t of texto) corpo.append(el("p", "", t));
  corpo.append(el("p", "alerta-historia", par.conceito));
  no.append(cabeca, corpo);
  return no;
}

function vistaPaises(alertas: Alerta[], d: Dados, grupo: string): HTMLElement[] {
  const partes: HTMLElement[] = [];
  const legenda = el("p", "alerta-legenda");
  legenda.append(
    el("span", "", `← melhor entre ${quem(grupo)}`),
    el("span", "alerta-legenda-meio", "cada ponto cinza é um país · traço: mediana"),
    el("span", "", "pior →"),
  );
  partes.push(legenda);
  const linhas: { pior: number; no: HTMLElement }[] = [];
  for (const a of alertas) {
    const par = PARES[a.id];
    if (!par) continue;
    const c = comparar(d, par, grupo);
    if (!c) continue;
    linhas.push({ pior: c.pior_que, no: linhaDoPais(a.id, a.nome, par, c, d, grupo, [a.por_que ?? ""].filter(Boolean)) });
  }
  linhas.sort((x, y) => y.pior - x.pior);
  partes.push(...linhas.map((l) => l.no));

  const extras: HTMLElement[] = [];
  for (const x of EXTRAS) {
    const c = comparar(d, x, grupo);
    if (c) extras.push(linhaDoPais(x.id, x.nome, x, c, d, grupo, [x.explica]));
  }
  if (extras.length) {
    partes.push(el("h4", "alerta-subtitulo", "Fora do painel, para completar o quadro"), ...extras);
  }
  const fora = semPar(alertas);
  partes.push(
    el(
      "p",
      "nota",
      "Cada linha põe o Brasil entre os outros países no mesmo número, da mesma fonte e do " +
        "mesmo ano (o último que o FMI já dá como realizado; o juro, no último mês do BIS; o " +
        "crédito privado, no último trimestre que o BIS publicou de cada país). " +
        "\"Pior que 97 %\" quer dizer que 97 % dos países do grupo estão melhor que o Brasil; " +
        "▲ a partir de 80 %. A régua vai do 5º ao 95º percentil dos " +
        "países, para um caso extremo não esconder o resto.\n\n" +
        `Os outros ${fora.length} indicadores do painel (${[...new Set(fora.map((a) => a.grupo.toLowerCase()))].join(", ")}) ` +
        "ainda não têm comparação internacional em fonte aberta e oficial: ficam só nas outras vistas.",
    ),
  );
  return partes;
}

// ------------------------------------------------------------------ quadro-resumo

function celula(texto: string, ruim: boolean, simbolo = ""): HTMLElement {
  const td = el("td", ruim ? "ruim" : "");
  if (ruim && simbolo) td.append(el("i", "", `${simbolo} `));
  td.append(document.createTextNode(texto));
  return td;
}

function vistaResumo(alertas: Alerta[], d: Dados | null, grupo: string): HTMLElement[] {
  const rolavel = el("div", "tabela-rolavel");
  rolavel.style.maxHeight = "none";
  const tabela = el("table", "dados alerta-quadro");
  const cab = tabela.createTHead().insertRow();
  const nomeGrupo = d ? (d.m.grupos.find((g) => g.iso3 === grupo)?.nome ?? "países de Brasil no mundo") : "";
  cab.append(
    el("th", "", "Indicador"),
    el("th", "", "História"),
    el("th", "", d ? (grupo === "principais" ? "Países" : nomeGrupo) : "Países"),
    el("th", "", "Um ano"),
  );
  const corpo = tabela.createTBody();
  for (const [g, itens] of porGrupo(alertas)) {
    const tr = corpo.insertRow();
    tr.className = "grupo";
    const th = el("th", "", g);
    th.colSpan = 4;
    tr.append(th);
    for (const a of itens) {
      const linhaTr = corpo.insertRow();
      linhaTr.append(el("th", "", a.nome));
      linhaTr.append(celula(`${numero(a.pior_que, 0)} %`, a.pior_que >= ACESO, "▲"));
      const par = PARES[a.id];
      const c = d && par ? comparar(d, par, grupo) : null;
      linhaTr.append(c ? celula(`${numero(c.pior_que, 0)} %`, c.pior_que >= ACESO, "▲") : el("td", "sem", "–"));
      const r = rumo(a);
      if (r) {
        // No celular fica só o símbolo (▲ ▼ =); a palavra vai no título e na nota.
        const td = el("td", r === "piorou" ? "ruim rumo" : "rumo");
        td.title = RUMOS[r].selo;
        td.append(el("i", "", RUMOS[r].simbolo), el("span", "palavra", ` ${RUMOS[r].selo === "quase igual" ? "igual" : RUMOS[r].selo}`));
        linhaTr.append(td);
      } else linhaTr.append(el("td", "sem", "–"));
    }
  }
  rolavel.append(tabela);
  return [
    rolavel,
    el(
      "p",
      "nota",
      "As três formas de ver, lado a lado. História: em quantos % dos meses (ou dias) da " +
        "própria história o indicador esteve melhor que hoje. Países: quantos % dos países do " +
        "grupo estão melhor que o Brasil. ▲ a partir de 80 %. " +
        "Um ano: ▲ piorou, ▼ melhorou ou = ficou quase igual (andou menos de 5 pontos na régua " +
        "da própria história). Traço: " +
        "sem par internacional em fonte aberta, ou sem o dado de um ano antes.",
    ),
  ];
}

// ------------------------------------------------------------------ o painel

type Vista = "historia" | "paises" | "tendencia" | "resumo";

const VISTAS: { valor: Vista; rotulo: string; explica: string }[] = [
  {
    valor: "historia",
    rotulo: "Contra a própria história",
    explica:
      "Cada indicador na régua de tudo o que ele já marcou: está num nível comum para ele, ou no " +
      "pior que já se viu? Abra um grupo e toque num indicador para saber o que ele é.",
  },
  {
    valor: "paises",
    rotulo: "Contra outros países",
    explica:
      "O Brasil entre países parecidos (emergentes, América Latina) ou entre os ricos, no mesmo " +
      "número e na mesma fonte para todos. Só os indicadores que têm comparação em fonte oficial.",
  },
  {
    valor: "tendencia",
    rotulo: "O que mudou em um ano",
    explica:
      "Se cada indicador melhorou ou piorou de um ano para cá. Um nível ruim que melhora preocupa " +
      "menos que um nível bom que piora depressa.",
  },
  {
    valor: "resumo",
    rotulo: "Quadro-resumo (as três juntas)",
    explica: "Uma linha por indicador: a história, os outros países e o rumo de um ano, lado a lado.",
  },
];

export function montarAlertas(alertas: Alerta[]): HTMLElement {
  const total = alertas.length;
  const ligados = acesos(alertas);
  const caixa = guardar(
    "Painel de alerta",
    `${ligados} de ${total} indicadores estão no quinto pior da própria história`,
    () => {
      let vista: Vista = "historia";
      let grupo = "G200";
      const explica = el("p", "alerta-intro");
      const corpo = el("div", "alerta-vista");
      const barra = el("div", "barra-controles");
      const escolhaGrupo = el("div", "alerta-grupo-escolha");
      barra.append(
        listaSuspensa(
          "alertas-vista",
          "Ver os alertas",
          VISTAS.map((v) => ({ valor: v.valor, rotulo: v.rotulo })),
          vista,
          (v) => {
            vista = v as Vista;
            pintar();
          },
        ).caixa,
        escolhaGrupo,
      );

      const pintar = (): void => {
        explica.textContent = VISTAS.find((v) => v.valor === vista)?.explica ?? "";
        const precisaPaises = vista === "paises" || vista === "resumo";
        escolhaGrupo.hidden = !precisaPaises;
        if (vista === "historia") corpo.replaceChildren(...vistaHistoria(alertas));
        else if (vista === "tendencia") corpo.replaceChildren(...vistaTendencia(alertas));
        else {
          corpo.replaceChildren(el("p", "alerta-intro", "Lendo os números dos outros países…"));
          const pedida = vista;
          void carregarPaises().then((d) => {
            if (vista !== pedida) return;
            if (d && !escolhaGrupo.firstChild) {
              escolhaGrupo.append(
                listaSuspensa("alertas-grupo", "Comparar com", opcoesDeGrupo(d), grupo, (g) => {
                  grupo = g;
                  pintar();
                }).caixa,
              );
            }
            if (vista === "resumo") corpo.replaceChildren(...vistaResumo(alertas, d, grupo));
            else if (d) corpo.replaceChildren(...vistaPaises(alertas, d, grupo));
            else corpo.replaceChildren(el("p", "alerta-intro", "Os números dos outros países não vieram nesta rodada."));
          });
        }
      };
      pintar();
      return [barra, explica, corpo];
    },
  );
  caixa.id = "t-alertas";
  return caixa;
}
