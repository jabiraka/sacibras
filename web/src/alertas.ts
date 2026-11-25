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
import { botoesDaImagem, tema, type Desenho, type Figura, type ItemDaLegenda } from "./grafico";
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
      `O valor de hoje na régua da história do indicador (desde ${Math.min(...primeiros)}); ` +
        "▲ aceso é pior que 80 % dela, e o traço amarelo, o limite oficial. " +
        "Não é previsão de crise: o pior da história pode estar longe de um nível perigoso.",
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
      "Hoje contra um ano antes, na régua da história do indicador: 5 pontos ou mais para o " +
        "lado ruim é piorou; para o bom, melhorou. Um nível bom pode piorar depressa, e um ruim, melhorar.",
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
      "O Brasil contra os outros países no mesmo número, fonte e ano (o último realizado do " +
        "FMI; no BIS, o último mês, trimestre ou 21 dias úteis). " +
        "\"Pior que 97 %\": 97 % dos países do grupo estão melhor; ▲ a partir de 80 %; a " +
        "régua vai do 5º ao 95º percentil.\n\n" +
        `Os outros ${fora.length} indicadores do painel (${[...new Set(fora.map((a) => a.grupo.toLowerCase()))].join(", ")}) ` +
        "ainda não têm comparação em fonte aberta e oficial.",
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
      "História: % da própria história melhor que hoje. Países: % dos países do grupo melhor " +
        "que o Brasil. ▲ a partir de 80 %. Um ano: ▲ piorou, ▼ melhorou, = quase igual " +
        "(menos de 5 pontos). Traço: sem o dado.",
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
      "Cada indicador na régua da própria história: nível comum ou o pior já visto? Toque num " +
      "indicador para saber o que ele é.",
  },
  {
    valor: "paises",
    rotulo: "Contra outros países",
    explica:
      "O Brasil entre países parecidos (emergentes, América Latina) ou entre os ricos, com o " +
      "mesmo número e a mesma fonte. Só onde há fonte oficial.",
  },
  {
    valor: "tendencia",
    rotulo: "O que mudou em um ano",
    explica:
      "Se cada indicador melhorou ou piorou em um ano. Nível ruim melhorando preocupa menos " +
      "que nível bom piorando depressa.",
  },
  {
    valor: "resumo",
    rotulo: "Quadro-resumo (as três juntas)",
    explica: "Uma linha por indicador: a história, os outros países e o rumo de um ano, lado a lado.",
  },
];

// ------------------------------------------------------------------ o painel como imagem
// Caio, 19/11/2026: "dê um jeito de exportar as fotos da página de alertas". A tela é HTML,
// então a imagem é um desenho no canvas da vista aberta: os grupos, cada indicador com o
// nome, a régua, o valor e a situação (▲ e a frase, nunca só a cor).

interface ReguaImg {
  /** Onde cai o ponto de hoje (0 = melhor, 1 = pior). */
  ponto: number;
  mediana?: number;
  limite?: number;
  antes?: number;
  pares?: number[];
  pontas: [string, string];
}

interface LinhaImg {
  nome: string;
  sub: string;
  valor: string;
  selo: string;
  aceso: boolean;
  regua?: ReguaImg;
  colunas?: { texto: string; ruim: boolean }[];
}

interface GrupoImg {
  titulo: string;
  conta: string;
  linhas: LinhaImg[];
}

const limitar = (f: number): number => Math.min(1, Math.max(0, f));

function fracaoDoAlerta(a: Alerta, v: number): number {
  const amplitude = a.maximo - a.minimo || 1;
  return limitar(a.pior_quando === "alto" ? (v - a.minimo) / amplitude : (a.maximo - v) / amplitude);
}

function linhaDoAlerta(a: Alerta, modo: "historia" | "tendencia"): LinhaImg {
  const aceso = a.pior_que >= ACESO;
  const alto = a.pior_quando === "alto";
  const [melhor, pior] = alto ? [a.minimo, a.maximo] : [a.maximo, a.minimo];
  const r = modo === "tendencia" ? rumo(a) : null;
  const comAntes = r && a.ha_um_ano !== null && a.ha_um_ano !== undefined;
  const quando = a.ha_um_ano_em ? ` em ${periodo(a.ha_um_ano_em, a.periodicidade)}` : "";
  return {
    nome: a.nome,
    sub:
      `${periodo(a.referencia, a.periodicidade)} · ${a.fonte}` +
      (a.limite ? ` · ${a.limite.rotulo}: ${numero(a.limite.valor, a.casas)}` : ""),
    valor: comUnidade(a.valor, a.unidade, a.casas),
    selo: comAntes
      ? `${RUMOS[r].simbolo} ${RUMOS[r].selo} (era ${numero(a.ha_um_ano as number, a.casas)}${quando})`
      : `${aceso ? "▲ " : ""}pior que ${numero(a.pior_que, 0)} % da história`,
    aceso: comAntes ? r === "piorou" : aceso,
    regua: {
      ponto: fracaoDoAlerta(a, a.valor),
      mediana: fracaoDoAlerta(a, a.mediana),
      limite: a.limite ? fracaoDoAlerta(a, a.limite.valor) : undefined,
      antes: comAntes ? fracaoDoAlerta(a, a.ha_um_ano as number) : undefined,
      pontas: [numero(melhor, a.casas), numero(pior, a.casas)],
    },
  };
}

function gruposDaHistoria(alertas: Alerta[]): GrupoImg[] {
  return porGrupo(alertas).map(([titulo, itens]) => {
    const n = acesos(itens);
    return {
      titulo,
      conta: `${n} de ${itens.length} ${n === 1 ? "aceso" : "acesos"}`,
      linhas: itens.map((a) => linhaDoAlerta(a, "historia")),
    };
  });
}

function gruposDaTendencia(alertas: Alerta[]): GrupoImg[] {
  const grupos: GrupoImg[] = [];
  for (const r of ["piorou", "igual", "melhorou"] as Rumo[]) {
    const itens = alertas
      .filter((a) => rumo(a) === r)
      .sort((a, b) => b.pior_que - (b.pior_que_ha_um_ano ?? 0) - (a.pior_que - (a.pior_que_ha_um_ano ?? 0)));
    if (!itens.length) continue;
    grupos.push({
      titulo: RUMOS[r].titulo,
      conta: `${itens.length} ${itens.length === 1 ? "indicador" : "indicadores"}`,
      linhas: itens.map((a) => linhaDoAlerta(a, "tendencia")),
    });
  }
  return grupos;
}

function gruposDosPaises(alertas: Alerta[], d: Dados, grupo: string): GrupoImg[] {
  const linhaDe = (nome: string, par: Par, c: Comparacao): LinhaImg => {
    const aceso = c.pior_que >= ACESO;
    const ordenados = [...c.valores].sort((a, b) => a - b);
    const q = (f: number): number => ordenados[Math.round(f * (ordenados.length - 1))] ?? 0;
    const lo = Math.min(q(0.05), c.brasil);
    const hi = Math.max(q(0.95), c.brasil);
    const alto = par.pior_quando === "alto";
    const amplitude = hi - lo || 1;
    const pos = (v: number): number => limitar(alto ? (v - lo) / amplitude : (hi - v) / amplitude);
    const unidade = par.unidade ?? d.m.metricas.find((x) => x.id === par.metrica)?.unidade ?? "";
    return {
      nome,
      sub: `${c.ano} · ${c.fonte}`,
      valor: `${numero(c.brasil, 1)}${unidade ? ` ${unidade}` : ""}`,
      selo: `${aceso ? "▲ " : ""}pior que ${numero(c.pior_que, 0)} %`,
      aceso,
      regua: {
        ponto: pos(c.brasil),
        mediana: pos(c.mediana),
        pares: c.valores.map(pos),
        pontas: [numero(alto ? lo : hi, 1), numero(alto ? hi : lo, 1)],
      },
    };
  };
  const principais: { pior: number; linha: LinhaImg }[] = [];
  for (const a of alertas) {
    const par = PARES[a.id];
    const c = par ? comparar(d, par, grupo) : null;
    if (par && c) principais.push({ pior: c.pior_que, linha: linhaDe(a.nome, par, c) });
  }
  principais.sort((x, y) => y.pior - x.pior);
  const grupos: GrupoImg[] = [
    {
      titulo: `O Brasil entre ${quem(grupo)}`,
      conta: `${acesos2(principais.map((p) => p.pior))} de ${principais.length} acesos`,
      linhas: principais.map((p) => p.linha),
    },
  ];
  const extras: LinhaImg[] = [];
  for (const x of EXTRAS) {
    const c = comparar(d, x, grupo);
    if (c) extras.push(linhaDe(x.nome, x, c));
  }
  if (extras.length) grupos.push({ titulo: "Fora do painel, para completar o quadro", conta: "", linhas: extras });
  return grupos;
}

const acesos2 = (piores: number[]): number => piores.filter((p) => p >= ACESO).length;

function gruposDoResumo(alertas: Alerta[], d: Dados | null, grupo: string): GrupoImg[] {
  return porGrupo(alertas).map(([titulo, itens]) => ({
    titulo,
    conta: "",
    linhas: itens.map((a) => {
      const par = PARES[a.id];
      const c = d && par ? comparar(d, par, grupo) : null;
      const r = rumo(a);
      return {
        nome: a.nome,
        sub: "",
        valor: "",
        selo: "",
        aceso: false,
        colunas: [
          { texto: `${a.pior_que >= ACESO ? "▲ " : ""}${numero(a.pior_que, 0)} %`, ruim: a.pior_que >= ACESO },
          c
            ? { texto: `${c.pior_que >= ACESO ? "▲ " : ""}${numero(c.pior_que, 0)} %`, ruim: c.pior_que >= ACESO }
            : { texto: "–", ruim: false },
          r ? { texto: `${RUMOS[r].simbolo} ${RUMOS[r].selo}`, ruim: r === "piorou" } : { texto: "–", ruim: false },
        ],
      };
    }),
  }));
}

/** Corta o texto com reticências para caber na largura. */
function caber(ctx: CanvasRenderingContext2D, texto: string, largura: number): string {
  if (ctx.measureText(texto).width <= largura) return texto;
  let t = texto;
  while (t.length > 1 && ctx.measureText(`${t}…`).width > largura) t = t.slice(0, -1);
  return `${t.trimEnd()}…`;
}

function desenhoDosAlertas(grupos: GrupoImg[], cabecalho: string[] | null): Desenho {
  const t = tema();
  const css = getComputedStyle(document.documentElement);
  const verde = css.getPropertyValue("--verde").trim() || "#00853a";
  const laranja = css.getPropertyValue("--alerta").trim() || "#b54708";
  const barra = css.getPropertyValue("--neutro-barra").trim() || t.fio;
  const familia = getComputedStyle(document.body).fontFamily;
  const w = 760;
  const alturaLinha = 50;
  const alturaGrupo = 34;
  const h = grupos.reduce((s, g) => s + alturaGrupo + g.linhas.length * alturaLinha, 0) + (cabecalho ? 26 : 0);
  const fonte = (peso: number, px: number): string => `${peso} ${px}px ${familia}`;
  return {
    w,
    h,
    pintar: (ctx, x0, y0) => {
      ctx.save();
      ctx.textBaseline = "alphabetic";
      let y = y0;
      const colX = [x0 + 380, x0 + 500, x0 + 620];
      if (cabecalho) {
        ctx.font = fonte(600, 11);
        ctx.fillStyle = t.tinta3;
        ctx.textAlign = "left";
        cabecalho.forEach((c, i) => ctx.fillText(c, colX[i] ?? x0, y + 14));
        y += 26;
      }
      for (const g of grupos) {
        ctx.textAlign = "left";
        ctx.font = fonte(600, 14);
        ctx.fillStyle = t.tinta;
        ctx.fillText(g.titulo, x0, y + 22);
        if (g.conta) {
          ctx.font = fonte(400, 12);
          ctx.fillStyle = t.tinta2;
          ctx.textAlign = "right";
          ctx.fillText(g.conta, x0 + w, y + 22);
        }
        y += alturaGrupo;
        for (const l of g.linhas) {
          ctx.strokeStyle = t.fio;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(x0, y + 0.5);
          ctx.lineTo(x0 + w, y + 0.5);
          ctx.stroke();
          const larguraNome = l.regua ? 300 : 360;
          ctx.textAlign = "left";
          ctx.font = fonte(500, 13);
          ctx.fillStyle = t.tinta;
          ctx.fillText(caber(ctx, l.nome, larguraNome), x0, y + 22);
          if (l.sub) {
            ctx.font = fonte(400, 10.5);
            ctx.fillStyle = t.tinta3;
            ctx.fillText(caber(ctx, l.sub, larguraNome), x0, y + 38);
          }
          if (l.colunas) {
            l.colunas.forEach((c, i) => {
              ctx.font = fonte(c.ruim ? 600 : 400, 13);
              ctx.fillStyle = c.ruim ? laranja : t.tinta;
              ctx.fillText(c.texto, colX[i] ?? x0, y + 30);
            });
          }
          const r = l.regua;
          if (r) {
            const rx = x0 + 316;
            const rw = 220;
            const ry = y + 22;
            const px = (f: number): number => rx + f * rw;
            ctx.fillStyle = barra;
            ctx.fillRect(rx, ry - 1, rw, 2);
            for (const f of r.pares ?? []) {
              ctx.fillStyle = t.tinta3;
              ctx.globalAlpha = 0.45;
              ctx.beginPath();
              ctx.arc(px(f), ry, 2.5, 0, Math.PI * 2);
              ctx.fill();
              ctx.globalAlpha = 1;
            }
            if (r.mediana !== undefined) {
              ctx.strokeStyle = t.tinta3;
              ctx.lineWidth = 1.5;
              ctx.beginPath();
              ctx.moveTo(px(r.mediana), ry - 6);
              ctx.lineTo(px(r.mediana), ry + 6);
              ctx.stroke();
            }
            if (r.limite !== undefined) {
              ctx.strokeStyle = t.faixa;
              ctx.lineWidth = 2;
              ctx.setLineDash([3, 2]);
              ctx.beginPath();
              ctx.moveTo(px(r.limite), ry - 8);
              ctx.lineTo(px(r.limite), ry + 8);
              ctx.stroke();
              ctx.setLineDash([]);
            }
            if (r.antes !== undefined) {
              ctx.strokeStyle = t.tinta3;
              ctx.lineWidth = 2;
              ctx.beginPath();
              ctx.moveTo(px(r.antes), ry);
              ctx.lineTo(px(r.ponto), ry);
              ctx.stroke();
              ctx.fillStyle = t.superficie;
              ctx.beginPath();
              ctx.arc(px(r.antes), ry, 5, 0, Math.PI * 2);
              ctx.fill();
              ctx.stroke();
            }
            ctx.fillStyle = l.aceso ? laranja : verde;
            ctx.strokeStyle = t.superficie;
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(px(r.ponto), ry, 6, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();
            ctx.font = fonte(400, 10);
            ctx.fillStyle = t.tinta3;
            ctx.textAlign = "left";
            ctx.fillText(r.pontas[0], rx, y + 42);
            ctx.textAlign = "right";
            ctx.fillText(r.pontas[1], rx + rw, y + 42);
            ctx.textAlign = "right";
            ctx.font = fonte(600, 13);
            ctx.fillStyle = t.tinta;
            ctx.fillText(l.valor, x0 + w, y + 22);
            ctx.font = fonte(l.aceso ? 600 : 400, 10.5);
            ctx.fillStyle = l.aceso ? laranja : t.tinta2;
            ctx.fillText(caber(ctx, l.selo, 200), x0 + w, y + 38);
          }
          y += alturaLinha;
        }
      }
      ctx.restore();
    },
  };
}

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
            dadosDaVista.paises = d;
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
      // A vista aberta como imagem (19/11/2026): "PNG" e "Copiar" no pé, como nos gráficos.
      const pe = el("footer", "grafico-pe");
      const fonteTexto = el("span", "fonte");
      const acoes = el("span", "acoes");
      pe.append(fonteTexto, acoes);
      const figura = (): Figura | null => {
        const v = VISTAS.find((x) => x.valor === vista);
        if (!v || !dadosDaVista) return null;
        const grupos =
          vista === "historia"
            ? gruposDaHistoria(alertas)
            : vista === "tendencia"
              ? gruposDaTendencia(alertas)
              : vista === "paises"
                ? dadosDaVista.paises
                  ? gruposDosPaises(alertas, dadosDaVista.paises, grupo)
                  : []
                : gruposDoResumo(alertas, dadosDaVista.paises, grupo);
        if (!grupos.length) return null;
        const fontes = new Set<string>();
        if (vista === "paises" || vista === "resumo") {
          if (dadosDaVista.paises) {
            for (const a of alertas) {
              const par = PARES[a.id];
              const c = par ? comparar(dadosDaVista.paises, par, grupo) : null;
              if (c) fontes.add(c.fonte);
            }
          }
        }
        if (vista !== "paises") for (const a of alertas) fontes.add(a.fonte);
        const legenda: ItemDaLegenda[] =
          vista === "resumo"
            ? []
            : [
                { nome: vista === "tendencia" ? "Hoje (cheio) e um ano antes (vazado)" : "Hoje", chave: "ponto" },
                { nome: vista === "paises" ? "Mediana (cada ponto cinza é um país)" : "Mediana", chave: "referencia" },
              ];
        return {
          id: `alertas-${vista}`,
          titulo: `Painel de alerta: ${v.rotulo.toLowerCase()}`,
          sub: `${acesos(alertas)} de ${alertas.length} indicadores no quinto pior da própria história · ▲ = pior que 80 %`,
          fonte: `Fonte: ${[...new Set([...fontes].flatMap((f) => f.split(";").map((x) => x.split(",")[0]?.trim() ?? "")).filter(Boolean))].join("; ")}. Conta do painel; a fonte de cada indicador está na tela.`,
          nota: `${v.explica} Não é previsão de crise nem nota de risco.`,
          legenda,
          desenho: desenhoDosAlertas(grupos, vista === "resumo" ? ["História", "Países", "Um ano"] : null),
        };
      };
      const dadosDaVista: { paises: Dados | null } = { paises: null };
      acoes.append(...botoesDaImagem(figura));
      pintar();
      return [barra, explica, corpo, pe];
    },
  );
  caixa.id = "t-alertas";
  return caixa;
}
