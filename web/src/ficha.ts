// A ficha de um estado: as contas dele abertas em partes (de onde vem a receita, para onde
// vai a despesa, do que é feita a dívida, o que a economia produz), cada parte com a fatia
// dela e a média dos estados e da região ao lado; e as contas no fim de cada ano, com a soma
// dos estados ao lado. O arquivo das contas só é lido quando a pessoa escolhe um estado.
// As exportações (o que vende e para onde) e a pirâmide etária entram como abas também.

import { dinheiro, numero, periodo } from "./formato";
import { montarGrafico, tema } from "./grafico";
import { el } from "./pecas";
import { montarPiramide } from "./piramide";
import { listaSuspensa } from "./pontos";
import type { BlocoDeConta, ContasEstado, EstadosContas, Grafico, HistoricoEstado, Piramide } from "./tipos";

/** R$ milhões por extenso curto: "R$ 1,2 tri", "R$ 34,5 bi", "R$ 820 mi". */
export function reaisDeMilhoes(v: number): string {
  const a = Math.abs(v);
  if (a >= 1e6) return `R$ ${numero(v / 1e6, 2)} tri`;
  if (a >= 1e3) return `R$ ${numero(v / 1e3, 1)} bi`;
  return `R$ ${numero(v, 0)} mi`;
}

/** US$ milhões por extenso curto: "US$ 1,2 bi", "US$ 820 mi". */
function dolaresDeMilhoes(v: number): string {
  const a = Math.abs(v);
  if (a >= 1e3) return `US$ ${numero(v / 1e3, 1)} bi`;
  return `US$ ${numero(v, a >= 10 ? 0 : 1)} mi`;
}

function emReais(v: number, unidade: string): string {
  if (unidade === "R$ milhões") return reaisDeMilhoes(v);
  if (unidade === "US$ milhões") return dolaresDeMilhoes(v);
  return `${numero(v, 1)} ${unidade}`;
}

/** "R$ 213,2 bi", "−R$ 25,4 bi", "R$ 3.756 por pessoa", "5,4 % da RCL"; a nota é o nome. */
function numeroDaFicha(n: ContasEstado["numeros"][number]): string {
  const { valor: v, unidade, casas } = n;
  if (n.texto) return n.texto;
  if (unidade === "R$ milhões") return reaisDeMilhoes(v);
  if (unidade === "R$ bilhões") return dinheiro(v * 1e9);
  if (unidade === "US$ bilhões") return `US$ ${numero(v, casas)} bi`;
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

/** A fatia média de cada parte nos estados que têm o mesmo bloco (só os de `quais`, se vier). */
function medias(todas: EstadosContas, id: string, quais?: Set<string>): Map<string, number> {
  const somas = new Map<string, { s: number; n: number }>();
  for (const c of Object.values(todas.contas)) {
    if (quais && !quais.has(c.uf)) continue;
    const b = c.blocos.find((x) => x.id === id);
    if (!b) continue;
    for (const p of partes(b).lista) {
      const atual = somas.get(p.nome) ?? { s: 0, n: 0 };
      somas.set(p.nome, { s: atual.s + p.fatia, n: atual.n + 1 });
    }
  }
  return new Map([...somas].map(([k, { s, n }]) => [k, s / n]));
}

/** A região do estado, para a coluna da média dela: o nome e quem mais está nela. */
export interface Regiao {
  nome: string;
  ufs: Set<string>;
}

function montarBloco(b: BlocoDeConta, todas: EstadosContas, regiao?: Regiao): HTMLElement {
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
    nome.startsWith("Outr") ? "var(--neutro-barra)" : (cores[i] ?? "var(--tinta-3)");
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
  // Sem média quando as partes mudam de estado para estado (os produtos e os países).
  const compara = b.compara !== false;
  const media = compara ? medias(todas, b.id) : undefined;
  // A média da região, com o próprio estado dentro, como na média dos estados.
  const daRegiao =
    compara && regiao && regiao.ufs.size > 1 ? medias(todas, b.id, regiao.ufs) : undefined;
  const tabela = el("table", "ficha-partes");
  const cabeca = tabela.createTHead().insertRow();
  const titulosDasColunas = ["", "Valor", "Parte"];
  if (media) titulosDasColunas.push("Média dos estados");
  if (daRegiao && regiao) titulosDasColunas.push(`Média do ${regiao.nome}`);
  for (const t of titulosDasColunas) cabeca.append(el("th", "", t));
  const corpo = tabela.createTBody();
  const pct = (m: number | undefined): string => (m === undefined ? "–" : `${numero(m * 100, 1)} %`);
  lista.forEach((p, i) => {
    const tr = corpo.insertRow();
    const nome = el("th");
    const chave = el("i", "ficha-chave");
    chave.style.background = corDe(i, p.nome);
    nome.append(chave, document.createTextNode(p.nome));
    tr.append(
      nome,
      el("td", "", emReais(p.valor, b.unidade)),
      el("td", "", `${numero(p.fatia * 100, 1)} %`),
    );
    if (media) tr.append(el("td", "media", pct(media.get(p.nome))));
    if (daRegiao) tr.append(el("td", "media", pct(daRegiao.get(p.nome))));
  });
  const rolavel = el("div", "tabela-rolavel");
  rolavel.append(tabela);
  caixa.append(rolavel, el("p", "fonte", `Fonte: ${b.fonte}`));
  return caixa;
}

/** As contas no fim de cada ano: uma de cada vez, o estado contra a soma dos estados. */
function montarNoTempo(c: ContasEstado, todas: EstadosContas): HTMLElement {
  const caixa = el("section", "ficha-bloco ficha-tempo");
  const historico = c.historico ?? [];
  let atual = historico[0] as HistoricoEstado;
  const escolha = listaSuspensa(
    `ficha-tempo-${c.uf}`,
    "Conta",
    historico.map((h) => ({ valor: h.id, rotulo: h.titulo })),
    atual.id,
    (id) => {
      atual = historico.find((h) => h.id === id) ?? atual;
      pintar();
    },
  );
  const barra = el("div", "barra-controles");
  barra.append(escolha.caixa);
  const tela = el("div");
  caixa.append(barra, tela);
  const serie = (pontos: Record<string, number>): [string, number | null][] =>
    Object.keys(pontos)
      .map(Number)
      .sort((a, b) => a - b)
      .map((ano) => [`${ano}-01-01`, pontos[String(ano)] ?? null]);
  function pintar(): void {
    const brasil = todas.historico_brasil?.[atual.id];
    const g: Grafico = {
      id: `ficha-${c.uf}-${atual.id}`,
      titulo: `${atual.titulo}: ${c.nome}`,
      subtitulo: "no fim de cada ano",
      tipo: "linha",
      unidade: atual.unidade,
      casas: atual.casas,
      periodicidade: "A",
      series: [
        { id: c.uf, nome: c.nome, papel: "realizado", tracejado_desde: null, pontos: serie(atual.pontos) },
        ...(brasil
          ? [
              {
                id: "todos",
                nome: "Todos os estados",
                papel: "referencia" as const,
                tracejado_desde: null,
                pontos: serie(brasil),
              },
            ]
          : []),
      ],
      faixa: null,
      intervalos: [],
      linhas: atual.linhas,
      janela_anos: null,
      fonte: atual.fonte,
      nota: atual.nota,
      largura: "inteira",
    };
    tela.replaceChildren(montarGrafico(g));
  }
  pintar();
  return caixa;
}

/** A pirâmide etária do estado, com a mesma peça da de Demografia. */
function montarPiramideDoEstado(c: ContasEstado, p: Piramide): HTMLElement {
  const g: Grafico = {
    id: `ficha-${c.uf}-piramide`,
    titulo: `Pirâmide etária: ${c.nome}`,
    subtitulo: "",
    tipo: "barras",
    unidade: "% da população",
    casas: 1,
    periodicidade: "A",
    series: [],
    faixa: null,
    intervalos: [],
    linhas: [],
    janela_anos: null,
    fonte: c.fonte_piramide ?? "IBGE, Projeções da População",
    nota:
      `Homens à esquerda, mulheres à direita, em % da população do estado no ano. O contorno é ${p.ano_contorno}. ` +
      `Até ${p.primeiro_ano_projetado - 1}, dado ajustado aos Censos; depois, projeção do IBGE, que conta também quem muda de estado.`,
    largura: "inteira",
    piramide: p,
  };
  return montarPiramide(g, p);
}

const NUMEROS_DA_FICHA = 4;

/** O nome curto de cada bloco, na aba. Blocos com o mesmo nome dividem a aba. */
const ABA: Record<string, string> = {
  receita: "Receita",
  despesa_grupo: "Gasto por tipo",
  despesa_funcao: "Gasto por área",
  divida: "Dívida",
  deducoes: "Descontos da dívida",
  pib_setor: "Economia",
  exportacoes_produtos: "Exportações",
  exportacoes_destinos: "Exportações",
};

export function montarFicha(c: ContasEstado, todas: EstadosContas, regiao?: Regiao): HTMLElement[] {
  const saida: HTMLElement[] = [];
  if (c.numeros.length) {
    const grade = el("div", "ficha-numeros");
    const numero = (n: (typeof c.numeros)[number]): HTMLElement => {
      const item = el("div", "ficha-numero");
      const valor = el("strong");
      valor.textContent = numeroDaFicha(n);
      item.append(el("span", "rotulo", n.rotulo), valor);
      if (n.detalhe) item.append(el("span", "detalhe", n.detalhe));
      item.append(el("span", "quando", periodo(n.referencia, n.periodicidade)));
      item.title = `Fonte: ${n.fonte}`;
      return item;
    };
    // Pouca coisa por tela: quatro números à vista, o resto atrás de "Mais números".
    c.numeros.slice(0, NUMEROS_DA_FICHA).forEach((n) => grade.append(numero(n)));
    saida.push(grade);
    const resto = c.numeros.slice(NUMEROS_DA_FICHA);
    if (resto.length) {
      const caixa = el("div", "abrir");
      const botao = el("button", "", "Mais números");
      botao.type = "button";
      botao.append(el("span", "", `+${resto.length}`));
      botao.addEventListener("click", () => {
        resto.forEach((n) => grade.append(numero(n)));
        caixa.remove();
      });
      caixa.append(botao);
      saida.push(caixa);
    }
  }
  // Um bloco de cada vez (Caio, 14/11/2026: "não precisa mostrar tudo em uma página só"):
  // as abas em cima, o bloco escolhido embaixo. "No tempo" é a última aba.
  const abasDaFicha: { nome: string; montar: () => HTMLElement }[] = [];
  const porNome = new Map<string, BlocoDeConta[]>();
  for (const b of c.blocos.filter((x) => x.fatias.length)) {
    const nome = ABA[b.id] ?? b.titulo;
    const juntos = porNome.get(nome);
    if (juntos) {
      juntos.push(b);
      continue;
    }
    const lista = [b];
    porNome.set(nome, lista);
    abasDaFicha.push({
      nome,
      montar: () => {
        if (lista.length === 1) return montarBloco(b, todas, regiao);
        const caixa = el("div", "ficha-juntos");
        caixa.append(...lista.map((x) => montarBloco(x, todas, regiao)));
        return caixa;
      },
    });
  }
  const piramide = c.piramide;
  if (piramide) abasDaFicha.push({ nome: "Idade", montar: () => montarPiramideDoEstado(c, piramide) });
  if (c.historico?.length) abasDaFicha.push({ nome: "No tempo", montar: () => montarNoTempo(c, todas) });
  if (!abasDaFicha.length) return saida;
  const abas = el("div", "ficha-abas");
  abas.setAttribute("role", "tablist");
  abas.setAttribute("aria-label", `As contas de ${c.nome}`);
  const palco = el("div", "ficha-palco");
  palco.setAttribute("role", "tabpanel");
  const botoes = abasDaFicha.map((a, i) => {
    const botao = el("button", "pilula", a.nome);
    botao.type = "button";
    botao.setAttribute("role", "tab");
    botao.addEventListener("click", () => mostrar(i));
    abas.append(botao);
    return botao;
  });
  const mostrar = (i: number): void => {
    const a = abasDaFicha[i];
    if (!a) return;
    botoes.forEach((x, k) => {
      x.setAttribute("aria-selected", String(k === i));
      x.classList.toggle("atual", k === i);
    });
    palco.replaceChildren(a.montar());
  };
  mostrar(0);
  saida.push(abas, palco);
  return saida;
}
