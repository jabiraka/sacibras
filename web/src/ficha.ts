// A ficha de um estado: as contas dele abertas em partes (de onde vem a receita, para onde
// vai a despesa, do que é feita a dívida), cada parte com a fatia dela e a média dos estados
// ao lado. O arquivo das contas só é lido quando a pessoa escolhe um estado.

import { numero, periodo } from "./formato";
import { tema } from "./grafico";
import { el } from "./pecas";
import type { BlocoDeConta, ContasEstado, EstadosContas } from "./tipos";

/** R$ milhões por extenso curto: "R$ 1,2 tri", "R$ 34,5 bi", "R$ 820 mi". */
export function reaisDeMilhoes(v: number): string {
  const a = Math.abs(v);
  if (a >= 1e6) return `R$ ${numero(v / 1e6, 2)} tri`;
  if (a >= 1e3) return `R$ ${numero(v / 1e3, 1)} bi`;
  return `R$ ${numero(v, 0)} mi`;
}

function emReais(v: number, unidade: string): string {
  return unidade === "R$ milhões" ? reaisDeMilhoes(v) : `${numero(v, 1)} ${unidade}`;
}

/** "R$ 213,2 bi", "R$ 3.756 por pessoa", "5,4 % da RCL". */
function numeroDaFicha(v: number, unidade: string, casas: number): string {
  if (unidade === "R$ milhões") return reaisDeMilhoes(v);
  if (unidade === "R$ bilhões") return `R$ ${numero(v, casas)} bi`;
  if (unidade.startsWith("R$ ")) return `R$ ${numero(v, casas)} ${unidade.slice(3)}`;
  return `${numero(v, casas)} ${unidade}`;
}

interface Parte {
  nome: string;
  valor: number;
  fatia: number;
}

/** As partes do bloco, com "Outras" quando as fatias não fecham o total. */
function partes(b: BlocoDeConta): { lista: Parte[]; total: number } {
  const soma = b.fatias.reduce((s, f) => s + f.valor, 0);
  const total = b.total ?? soma;
  const lista = b.fatias.map((f) => ({ ...f, fatia: total ? f.valor / total : 0 }));
  const sobra = total - soma;
  if (b.total !== null && sobra > Math.abs(total) * 0.005) {
    lista.push({ nome: "Outras", valor: sobra, fatia: sobra / total });
  }
  return { lista, total };
}

/** A fatia média de cada parte nos estados que têm o mesmo bloco. */
function medias(todas: EstadosContas, id: string): Map<string, number> {
  const somas = new Map<string, { s: number; n: number }>();
  for (const c of Object.values(todas.contas)) {
    const b = c.blocos.find((x) => x.id === id);
    if (!b) continue;
    for (const p of partes(b).lista) {
      const atual = somas.get(p.nome) ?? { s: 0, n: 0 };
      somas.set(p.nome, { s: atual.s + p.fatia, n: atual.n + 1 });
    }
  }
  return new Map([...somas].map(([k, { s, n }]) => [k, s / n]));
}

function montarBloco(b: BlocoDeConta, todas: EstadosContas): HTMLElement {
  const caixa = el("section", "ficha-bloco");
  const { lista, total } = partes(b);
  const cab = el("header", "ficha-bloco-cabeca");
  const titulos = el("div");
  titulos.append(el("h4", "", b.titulo), el("p", "sub", [b.descricao, b.referencia].filter(Boolean).join(" · ")));
  cab.append(titulos, el("strong", "ficha-total", emReais(total, b.unidade)));
  caixa.append(cab);

  // A barra dividida: só faz sentido quando todas as partes são positivas.
  const cores = tema().series;
  const corDe = (i: number, nome: string): string =>
    // Seis cores validadas; da sétima parte em diante, cinza escuro (não repete cor).
    nome === "Outras" ? "var(--neutro-barra)" : (cores[i] ?? "var(--tinta-3)");
  if (lista.every((p) => p.valor >= 0) && total > 0) {
    const barra = el("div", "ficha-barra");
    barra.setAttribute("aria-hidden", "true");
    lista.forEach((p, i) => {
      const pedaco = el("i");
      pedaco.style.width = `${(p.fatia * 100).toFixed(2)}%`;
      pedaco.style.background = corDe(i, p.nome);
      pedaco.title = `${p.nome}: ${numero(p.fatia * 100, 1)} %`;
      barra.append(pedaco);
    });
    caixa.append(barra);
  }
  const media = medias(todas, b.id);
  const tabela = el("table", "ficha-partes");
  const cabeca = tabela.createTHead().insertRow();
  for (const t of ["", "Valor", "Parte", "Média dos estados"]) cabeca.append(el("th", "", t));
  const corpo = tabela.createTBody();
  lista.forEach((p, i) => {
    const tr = corpo.insertRow();
    const nome = el("th");
    const chave = el("i", "ficha-chave");
    chave.style.background = corDe(i, p.nome);
    nome.append(chave, document.createTextNode(p.nome));
    const m = media.get(p.nome);
    tr.append(
      nome,
      el("td", "", emReais(p.valor, b.unidade)),
      el("td", "", `${numero(p.fatia * 100, 1)} %`),
      el("td", "media", m === undefined ? "–" : `${numero(m * 100, 1)} %`),
    );
  });
  const rolavel = el("div", "tabela-rolavel");
  rolavel.append(tabela);
  caixa.append(rolavel, el("p", "fonte", `Fonte: ${b.fonte}`));
  return caixa;
}

/** O nome curto de cada bloco, na aba. */
const ABA: Record<string, string> = {
  receita: "Receita",
  despesa_grupo: "Gasto por tipo",
  despesa_funcao: "Gasto por área",
  divida: "Dívida",
  deducoes: "Descontos da dívida",
};

export function montarFicha(c: ContasEstado, todas: EstadosContas): HTMLElement[] {
  const saida: HTMLElement[] = [];
  if (c.numeros.length) {
    const grade = el("div", "ficha-numeros");
    for (const n of c.numeros) {
      const item = el("div", "ficha-numero");
      const valor = el("strong");
      valor.textContent = numeroDaFicha(n.valor, n.unidade, n.casas);
      item.append(el("span", "rotulo", n.rotulo), valor);
      if (n.detalhe) item.append(el("span", "detalhe", n.detalhe));
      item.append(el("span", "quando", periodo(n.referencia, n.periodicidade)));
      item.title = `Fonte: ${n.fonte}`;
      grade.append(item);
    }
    saida.push(grade);
  }
  // Um bloco de cada vez (Caio, 14/11/2026: "não precisa mostrar tudo em uma página só"):
  // as abas em cima, o bloco escolhido embaixo.
  const blocos = c.blocos.filter((b) => b.fatias.length);
  if (!blocos.length) return saida;
  const abas = el("div", "ficha-abas");
  abas.setAttribute("role", "tablist");
  abas.setAttribute("aria-label", `As contas de ${c.nome}`);
  const palco = el("div", "ficha-palco");
  palco.setAttribute("role", "tabpanel");
  const botoes = blocos.map((b, i) => {
    const botao = el("button", "pilula", ABA[b.id] ?? b.titulo);
    botao.type = "button";
    botao.setAttribute("role", "tab");
    botao.addEventListener("click", () => mostrar(i));
    abas.append(botao);
    return botao;
  });
  const mostrar = (i: number): void => {
    const b = blocos[i];
    if (!b) return;
    botoes.forEach((x, k) => {
      x.setAttribute("aria-selected", String(k === i));
      x.classList.toggle("atual", k === i);
    });
    palco.replaceChildren(montarBloco(b, todas));
  };
  mostrar(0);
  saida.push(abas, palco);
  return saida;
}
