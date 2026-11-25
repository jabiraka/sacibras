// A busca: o campo fica fixo no menu lateral (no celular, na faixa do topo) e os resultados
// aparecem logo abaixo dele. O índice (`busca.json`) vem do builder, com os sinônimos de cada
// item e os números que cada peça mostra; aqui se compara sem acento e por começo de palavra.
// Além do nome, a busca entende (15/11/2026):
//   - um número ("13,75", "4,5 %", "1.234"): acha o cartão ou a tabela que o mostra;
//   - "o que é spread": a definição do glossário vem no topo, antes dos resultados;
//   - chinês e japonês, que não separam palavras: o termo do índice dentro do que se digitou;
//   - nada achado: as buscas parecidas que acham alguma coisa e alguns assuntos.

import { escolherAlternativa } from "./alternativas";
import { el } from "./pecas";
import { idiomaAtual } from "./traducao";

/** As línguas que o índice entende (os sinônimos de `busca.py`). */
const LINGUAS_DO_INDICE = ["pt", "en", "es", "fr", "zh", "ja", "ar"];

interface Item {
  t: string;
  o: string;
  h: string;
  p?: string;
  /** O título em outras línguas (vale mais que os sinônimos). */
  lt?: string;
  /** Os números que a peça mostra, como `comoNumero` os escreve ("13,75 128450"). */
  n?: string;
}

export interface Indexado extends Item {
  titulo: string;
  traducao: string;
  resto: string;
  numeros: string[];
  /** Os termos em chinês e japonês do título traduzido e dos sinônimos. */
  juntosTitulo: string[];
  juntosResto: string[];
}

export interface Verbete {
  id: string;
  nome: string;
  definicao: string;
  formas: string[];
  elo?: string;
}

let indice: Promise<Indexado[]> | null = null;
let glossario: Promise<Verbete[]> | null = null;

/** Sem acento (os do alfabeto latino e as vogais curtas do árabe) e em minúsculas; igual ao
 *  `normalizar` de `busca.py`. */
export function normalizar(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[̀-ًͯ-ٰٟ]/g, "")
    .normalize("NFC")
    .toLowerCase();
}

/** Escrita sem espaço entre as palavras (chinês, japonês). */
const SEM_ESPACO = /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}]/u;

function juntos(texto: string): string[] {
  return texto.split(/\s+/).filter((t) => SEM_ESPACO.test(t));
}

/** O item do índice pronto para comparar. */
export function indexar(i: Item): Indexado {
  const traducao = normalizar(i.lt ?? "");
  const resto = normalizar(`${i.o} ${i.p ?? ""}`);
  return {
    ...i,
    titulo: normalizar(i.t),
    traducao,
    resto,
    numeros: i.n ? i.n.split(" ") : [],
    juntosTitulo: juntos(traducao),
    juntosResto: juntos(resto),
  };
}

function carregar(): Promise<Indexado[]> {
  indice ??= fetch("data/busca.json", { cache: "no-cache" })
    .then((r) => (r.ok ? (r.json() as Promise<Item[]>) : []))
    .then((itens) => itens.map(indexar))
    .catch(() => []);
  return indice;
}

function carregarGlossario(): Promise<Verbete[]> {
  glossario ??= fetch("data/glossario.json", { cache: "no-cache" })
    .then((r) => (r.ok ? (r.json() as Promise<Verbete[]>) : []))
    .catch(() => []);
  return glossario;
}

// ------------------------------------------------------------------ números

/** O número digitado do jeito que o índice guarda ("13,75", "1234", "-2,1"), ou null se a
 *  palavra não for número. Aceita "13.75" (ponto decimal), "1.234" (milhar), "4,5%", "−2". */
export function comoNumero(palavra: string): string | null {
  let p = palavra
    .replace(/[−–]/g, "-")
    .replace(/%$/, "")
    .replace(/^(r|us)\$/, "");
  if (!/^-?\d[\d.,]*$/.test(p) || /[.,]$/.test(p)) return null;
  if (p.includes(",")) p = p.replace(/\./g, "");
  else if (/^-?\d{1,3}(\.\d{3})+$/.test(p)) p = p.replace(/\./g, "");
  else p = p.replace(".", ",");
  if ((p.match(/[.,]/g) ?? []).length > 1) return null;
  return p.replace(/^(-?)0+(?=\d)/, "$1");
}

/** "128450" → "128.450", "-2,1" → "−2,1": o número como a tela mostra. */
export function numeroNaTela(n: string): string {
  const [inteiro = "", decimais] = n.replace("-", "").split(",");
  const comPontos = inteiro.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const sinal = n.startsWith("-") ? "−" : "";
  return `${sinal}${comPontos}${decimais !== undefined ? `,${decimais}` : ""}`;
}

/** O número do índice que casa com o digitado: igual (3), ou começando com ele — "13" acha
 *  "13,75", "13,7" também (1,5). */
function casarNumero(
  numeros: string[],
  q: string,
): { nota: number; numero: string } | null {
  if (numeros.includes(q)) return { nota: 3, numero: q };
  const parecido = numeros.find(
    (n) => n.startsWith(q) && (q.includes(",") || n.charAt(q.length) === ","),
  );
  return parecido ? { nota: 1.5, numero: parecido } : null;
}

// ------------------------------------------------------------------ a nota de cada item

export interface Achado {
  item: Indexado;
  nota: number;
  /** O número que casou, quando se buscou um número. */
  numero?: string;
  /** Casou só com parte das palavras (nada casou com todas). */
  parcial?: boolean;
}

function escaparRegex(texto: string): string {
  return texto.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Pontua o item: cada palavra da busca tem de aparecer (no começo de uma palavra do título,
 *  do lugar ou dos sinônimos; o número, entre os que a peça mostra); no título vale mais. */
export function pontuar(item: Indexado, palavras: string[]): Achado | null {
  let total = 0;
  let numero: string | undefined;
  for (const p of palavras) {
    const q = comoNumero(p);
    const casou = q === null ? null : casarNumero(item.numeros, q);
    if (casou) {
      total += casou.nota;
      numero ??= casou.numero;
      continue;
    }
    if (SEM_ESPACO.test(p)) {
      // Chinês e japonês: o digitado dentro do texto, ou um termo do índice dentro do digitado.
      if (item.titulo.includes(p)) total += 3;
      else if (
        item.traducao.includes(p) ||
        item.juntosTitulo.some((t) => p.includes(t))
      )
        total += 2;
      else if (
        item.resto.includes(p) ||
        item.juntosResto.some((t) => p.includes(t))
      )
        total += 1;
      else return null;
      continue;
    }
    const noTitulo = new RegExp(`(^|[^a-z0-9])${escaparRegex(p)}`);
    if (noTitulo.test(item.titulo)) total += item.titulo.startsWith(p) ? 4 : 3;
    else if (item.traducao && noTitulo.test(item.traducao)) total += 2;
    else if (noTitulo.test(item.resto)) total += 1;
    else return null;
  }
  return { item, nota: total, numero };
}

/** As palavras da busca: sem acento, "4,5 %" junto, letra solta de fora (menos as escritas
 *  em que uma letra é uma palavra: "州", "税"). */
export function palavrasDe(texto: string): string[] {
  const palavras = normalizar(texto)
    .replace(/(\d)\s*%/g, "$1")
    .replace(/[?!¿¡]/g, " ")
    .split(/\s+/)
    .filter((p) => p.length > 1 || /\d/.test(p) || SEM_ESPACO.test(p));
  // "PIB de São Paulo", "quanto vai ser a inflação": as palavras de ligação ficam de fora
  // (15/11/2026: o "de" e o "vai" tinham de casar também, e nada aparecia).
  const cheias = palavras.filter((p) => !VAZIAS.has(p));
  return cheias.length ? cheias : palavras;
}

/** Palavras que não dizem o que se procura, sem acento (português, inglês, espanhol e
 *  francês). */
const VAZIAS = new Set(
  (
    "de da do das dos na no nas nos em ao aos pra para por pelo pela com sem e ou um uma os as " +
    "que qual quais quanto quanta quantos como onde quando esta estao vai vao ser sera foi " +
    "tem hoje agora atual brasil brasileiro brasileira " +
    "the of in on for and to is what how much del la el los las en y du des le les et"
  ).split(" "),
);

function ordenar(achados: Achado[], limite: number): Achado[] {
  return achados
    .map((x) => ({ ...x, nota: x.nota - (x.item.o === "Assunto" ? 0 : 0.5) }))
    .sort((a, b) => b.nota - a.nota || a.item.t.length - b.item.t.length)
    .slice(0, limite);
}

export function buscar(
  itens: Indexado[],
  texto: string,
  limite = 12,
  parcial = true,
): Achado[] {
  const palavras = palavrasDe(texto);
  if (!palavras.length) return [];
  const todas = itens
    .map((i) => pontuar(i, palavras))
    .filter((x): x is Achado => x !== null && x.nota > 0);
  if (todas.length || !parcial || palavras.length < 2)
    return ordenar(todas, limite);
  // Nada com todas as palavras ("PIB de São Paulo", "juros do cartão"): o que casa com mais
  // delas, cada palavra pesando o que pesaria sozinha. Palavra com número fica de fora.
  const avulsas = palavras.filter((p) => comoNumero(p) === null);
  let melhor = 0;
  const parciais: { achado: Achado; casadas: number }[] = [];
  for (const item of itens) {
    let casadas = 0;
    let nota = 0;
    for (const p of avulsas) {
      const um = pontuar(item, [p]);
      if (um) {
        casadas += 1;
        nota += um.nota;
      }
    }
    if (!casadas) continue;
    melhor = Math.max(melhor, casadas);
    parciais.push({ achado: { item, nota, parcial: true }, casadas });
  }
  return ordenar(
    parciais.filter((x) => x.casadas === melhor).map((x) => x.achado),
    limite,
  );
}

// ------------------------------------------------------------------ o glossário na busca

const PERGUNTA =
  /^(?:o\s*que\s+(?:e|eh|sao|significa|quer dizer)|oq\s+e|que\s+(?:e|sao)|significado\s+de|definicao\s+de|what\s+(?:is|are)|what's|que\s+(?:es|son)|qu'est-ce\s+que|qu'est-ce\s+qu'|c'est\s+quoi)\s+(.+)$/;
const ARTIGO =
  /^(?:o|a|os|as|um|uma|the|an|el|la|los|las|le|les|un|une)\s+|^l'/;

/** "o que é spread", "what is GDP", "qué es el PIB?" → "spread", "gdp", "pib"; senão, null. */
export function perguntaDeTermo(texto: string): string | null {
  const t = normalizar(texto)
    .trim()
    .replace(/\s*\?+$/, "")
    .replace(/^¿\s*/, "");
  const resto = PERGUNTA.exec(t)?.[1]?.replace(ARTIGO, "").trim();
  return resto || null;
}

/** O verbete com esse nome ou forma (sem acento, sem caixa). Na pergunta ("o que é spre"),
 *  se nenhum for igual, o de nome mais curto que começa assim; a palavra solta só traz o
 *  verbete de nome igual ("inflação" não abre "Inflação implícita"). */
export function verbeteDe(
  lista: Verbete[],
  termo: string,
  pergunta = true,
): Verbete | undefined {
  const alvo = normalizar(termo).trim();
  if (!alvo) return undefined;
  const nomes = (v: Verbete): string[] => [v.nome, ...v.formas].map(normalizar);
  const igual = lista.find((v) => nomes(v).includes(alvo));
  if (igual || !pergunta || alvo.length < 3) return igual;
  return lista
    .filter((v) => nomes(v).some((n) => n.startsWith(alvo)))
    .sort((a, b) => a.nome.length - b.nome.length)[0];
}

// ------------------------------------------------------------------ nada achado: sugestões

/** Distância de edição com troca de vizinhas ("inlfação" está a 1 de "inflação"); para de
 *  contar quando passa do `teto`. */
export function distancia(a: string, b: string, teto = 3): number {
  if (Math.abs(a.length - b.length) > teto) return teto + 1;
  let antes2: number[] = [];
  let antes = Array.from({ length: b.length + 1 }, (_, j) => j);
  for (let i = 1; i <= a.length; i++) {
    const atual = [i];
    let menor = i;
    for (let j = 1; j <= b.length; j++) {
      const custo = a[i - 1] === b[j - 1] ? 0 : 1;
      let d = Math.min(
        (antes[j] ?? 0) + 1,
        (atual[j - 1] ?? 0) + 1,
        (antes[j - 1] ?? 0) + custo,
      );
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) {
        d = Math.min(d, (antes2[j - 2] ?? 0) + 1);
      }
      atual.push(d);
      menor = Math.min(menor, d);
    }
    if (menor > teto) return teto + 1;
    antes2 = antes;
    antes = atual;
  }
  return antes[b.length] ?? teto + 1;
}

interface Palavra {
  forma: string;
  conta: number;
  /** Só aparece no título em outra língua ("inflacion"): sugerida só na página traduzida. */
  deFora: boolean;
}

const vocabularios = new WeakMap<Indexado[], Map<string, Palavra>>();

/** As palavras dos títulos (com o acento de origem, para mostrar) e as das outras línguas. */
function palavrasDoIndice(itens: Indexado[]): Map<string, Palavra> {
  const pronto = vocabularios.get(itens);
  if (pronto) return pronto;
  const mapa = new Map<string, Palavra>();
  const contar = (forma: string, deFora: boolean): void => {
    const chave = normalizar(forma);
    if (chave.length < 3 || /\d/.test(chave) || SEM_ESPACO.test(chave)) return;
    const ja = mapa.get(chave);
    if (ja) {
      ja.conta += 1;
      ja.deFora &&= deFora;
    } else
      mapa.set(chave, {
        forma: forma.toLocaleLowerCase("pt-BR"),
        conta: 1,
        deFora,
      });
  };
  for (const i of itens) {
    for (const f of i.t.split(/[^\p{L}\p{N}+-]+/u)) contar(f, false);
    for (const f of i.traducao.split(/[^\p{L}\p{N}+-]+/u)) contar(f, true);
  }
  vocabularios.set(itens, mapa);
  return mapa;
}

/** As palavras do índice mais perto da digitada: até 1 letra de diferença em palavra curta,
 *  até 2 nas outras; também contra o começo da palavra do índice (quem ainda digita). */
function parecidas(
  palavra: string,
  vocab: Map<string, Palavra>,
  quantas: number,
  deFora: boolean,
): string[] {
  if (palavra.length < 3) return [];
  const teto = palavra.length <= 4 ? 1 : 2;
  const candidatas: { forma: string; d: number; conta: number }[] = [];
  for (const [chave, p] of vocab) {
    if (chave === palavra || (p.deFora && !deFora)) continue;
    let d = distancia(palavra, chave, teto);
    if (d > teto && palavra.length >= 4 && chave.length > palavra.length) {
      d = distancia(palavra, chave.slice(0, palavra.length), teto) + 0.5;
    }
    if (d <= teto + 0.5) candidatas.push({ forma: p.forma, d, conta: p.conta });
  }
  return candidatas
    .sort(
      (a, b) =>
        a.d - b.d || b.conta - a.conta || a.forma.length - b.forma.length,
    )
    .slice(0, quantas)
    .map((c) => c.forma);
}

/** As buscas a sugerir quando nada foi achado: cada palavra sem resultado trocada pela mais
 *  parecida do índice (a busca inteira corrigida primeiro), só as que acham alguma coisa.
 *  As palavras das outras línguas entram só com a página traduzida (`deFora`). */
export function sugestoes(
  itens: Indexado[],
  texto: string,
  quantas = 4,
  deFora = false,
): string[] {
  const palavras = palavrasDe(texto);
  const vocab = palavrasDoIndice(itens);
  const falhas = palavras.filter(
    (p) => comoNumero(p) === null && !buscar(itens, p, 1, false).length,
  );
  if (!falhas.length) return [];
  const trocas = new Map(
    falhas.map((f) => [f, parecidas(f, vocab, quantas, deFora)]),
  );
  const montar = (troca: (p: string) => string): string =>
    palavras.map((p) => (trocas.has(p) ? troca(p) : p)).join(" ");
  const opcoes = [montar((p) => trocas.get(p)?.[0] ?? p)];
  const primeira = falhas[0] ?? "";
  for (const alternativa of (trocas.get(primeira) ?? []).slice(1)) {
    opcoes.push(
      montar((p) => (p === primeira ? alternativa : (trocas.get(p)?.[0] ?? p))),
    );
  }
  const vistas = new Set<string>([palavras.join(" ")]);
  return opcoes
    .filter((o) => {
      if (vistas.has(o) || !buscar(itens, o, 1, false).length) return false;
      vistas.add(o);
      return true;
    })
    .slice(0, quantas);
}

/** Os assuntos a oferecer quando nada foi achado: os mais procurados que existirem. */
const ASSUNTOS_SUGERIDOS = [
  "#inflacao",
  "#juros",
  "#trabalho",
  "#atividade",
  "#externo",
  "#fiscal",
];

function assuntosSugeridos(itens: Indexado[]): Indexado[] {
  const assuntos = itens.filter((i) => i.o === "Assunto");
  const preferidos = ASSUNTOS_SUGERIDOS.map((h) =>
    assuntos.find((a) => a.h === h),
  ).filter((a): a is Indexado => a !== undefined);
  const resto = assuntos.filter((a) => !preferidos.includes(a));
  return [...preferidos, ...resto].slice(0, 6);
}

// ------------------------------------------------------------------ o campo e a lista

/** Põe o cursor no campo da busca, que fica sempre à vista no menu lateral (no celular, no
 *  topo). Atalho: a tecla "/". */
export function abrirBusca(inicial = ""): void {
  const campo = document.getElementById(
    "busca-campo",
  ) as HTMLInputElement | null;
  if (!campo) return;
  if (inicial) {
    campo.value = inicial;
    campo.dispatchEvent(new Event("input"));
  }
  campo.focus();
}

/** Liga o campo fixo aos resultados logo abaixo dele (sem janela por cima da página:
 *  Caio, 14/11/2026, "a pesquisa não precisa abrir um outro negócio, pode manter fixo"). */
export function ligarBusca(): void {
  const campo = document.getElementById(
    "busca-campo",
  ) as HTMLInputElement | null;
  const saida = document.getElementById("busca-saida");
  if (!campo || !saida) return;
  const lista = saida.querySelector(".busca-resultados") as HTMLOListElement;
  const aviso = saida.querySelector(".busca-aviso") as HTMLParagraphElement;
  const definicao = saida.querySelector(".busca-definicao") as HTMLElement;
  const outras = saida.querySelector(".busca-sugestoes") as HTMLElement;

  const fechar = (): void => {
    saida.hidden = true;
    campo.setAttribute("aria-expanded", "false");
  };
  const ir = (h: string): void => {
    fechar();
    campo.value = "";
    campo.blur();
    if (location.hash === h)
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    else location.hash = h;
  };
  const buscarDeNovo = (texto: string): void => {
    campo.value = texto;
    campo.dispatchEvent(new Event("input"));
    campo.focus();
  };
  const itens = (): HTMLAnchorElement[] => [
    ...lista.querySelectorAll<HTMLAnchorElement>("a"),
  ];

  /** A definição do glossário no topo ("o que é spread"). */
  const mostrarDefinicao = (v: Verbete | undefined): void => {
    definicao.hidden = !v;
    if (!v) {
      definicao.replaceChildren();
      return;
    }
    const nome = el("p", "busca-def-nome");
    nome.append(
      el("span", "busca-def-rotulo", "Glossário"),
      document.createTextNode(v.nome),
    );
    const partes: HTMLElement[] = [
      nome,
      el("p", "busca-def-texto", v.definicao),
    ];
    if (v.elo) {
      const destino = v.elo;
      const elo = el("a", "busca-def-elo", "Ver no painel →");
      elo.href = destino;
      elo.addEventListener("click", (ev) => {
        ev.preventDefault();
        ir(destino);
      });
      partes.push(elo);
    }
    definicao.replaceChildren(...partes);
  };

  /** Nada achado: as buscas parecidas que acham alguma coisa e alguns assuntos. */
  const mostrarSugestoes = (todos: Indexado[], texto: string): void => {
    const blocos: HTMLElement[] = [];
    const parecidas = sugestoes(todos, texto, 4, idiomaAtual() !== "pt");
    if (parecidas.length) {
      const linha = el("div", "busca-sug-linha");
      linha.append(el("span", "busca-sug-titulo", "Você quis dizer"));
      for (const s of parecidas) {
        const b = el("button", "pilula", s);
        b.type = "button";
        b.addEventListener("click", () => buscarDeNovo(s));
        linha.append(b);
      }
      blocos.push(linha);
    }
    const linha = el("div", "busca-sug-linha");
    linha.append(el("span", "busca-sug-titulo", "Ou abra um assunto"));
    for (const a of assuntosSugeridos(todos)) {
      const elo = el("a", "pilula", a.t);
      elo.href = a.h;
      elo.addEventListener("click", (ev) => {
        ev.preventDefault();
        ir(a.h);
      });
      linha.append(elo);
    }
    blocos.push(linha);
    outras.replaceChildren(...blocos);
    outras.hidden = false;
  };

  let pedido = 0;
  campo.addEventListener("input", () => {
    const meu = ++pedido;
    const texto = campo.value;
    if (!texto.trim()) {
      lista.replaceChildren();
      aviso.textContent = "";
      mostrarDefinicao(undefined);
      outras.hidden = true;
      fechar();
      return;
    }
    void Promise.all([carregar(), carregarGlossario()]).then(
      ([todos, verbetes]) => {
        if (meu !== pedido) return;
        // "o que é spread": a definição em cima e os resultados de "spread" embaixo. A palavra
        // sozinha, se for o nome de um termo do glossário, também traz a definição.
        const termo = perguntaDeTermo(texto);
        const verbete = verbeteDe(verbetes, termo ?? texto, termo !== null);
        mostrarDefinicao(verbete);
        const achados = buscar(todos, termo ?? texto);
        lista.replaceChildren(
          ...achados.map((a) => {
            const li = el("li");
            const elo = el("a", "busca-item");
            elo.href = a.item.h;
            elo.addEventListener("click", (ev) => {
              ev.preventDefault();
              ir(a.item.h);
            });
            const onde = el("span", "busca-onde", a.item.o);
            if (a.numero)
              onde.append(
                el("span", "busca-valor", `mostra ${numeroNaTela(a.numero)}`),
              );
            elo.append(el("span", "busca-titulo", a.item.t), onde);
            li.append(elo);
            return li;
          }),
        );
        const outraLingua = !LINGUAS_DO_INDICE.includes(
          idiomaAtual().slice(0, 2),
        );
        const parcial = achados.some((a) => a.parcial);
        const nada = (!achados.length || parcial) && !verbete;
        const numerico = palavrasDe(texto).some((p) => comoNumero(p) !== null);
        aviso.textContent = !nada
          ? ""
          : parcial
            ? "Nada com todas as palavras. Abaixo, o que tem parte delas:"
            : numerico
              ? 'Nenhum número da tela é esse. A busca acha o número como ele aparece no cartão ou na tabela ("13,75", "4,5").'
              : outraLingua
                ? 'Nada com esse nome. A busca entende português, inglês, espanhol, francês, chinês, japonês e árabe: tente, por exemplo, "inflation" ou "GDP".'
                : "Nada com esse nome.";
        if (nada && !parcial) mostrarSugestoes(todos, texto);
        else outras.hidden = true;
        saida.hidden = false;
        campo.setAttribute("aria-expanded", "true");
      },
    );
  });
  campo.addEventListener("focus", () => {
    const algo =
      lista.children.length || aviso.textContent || !definicao.hidden;
    if (campo.value.trim() && algo) saida.hidden = false;
  });
  campo.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") {
      ev.preventDefault();
      const primeiro = itens()[0];
      if (primeiro) ir(primeiro.getAttribute("href") ?? "#");
      else if (!outras.hidden)
        outras.querySelector<HTMLButtonElement>("button")?.click();
    } else if (ev.key === "ArrowDown") {
      ev.preventDefault();
      itens()[0]?.focus();
    } else if (ev.key === "Escape") {
      campo.value = "";
      campo.dispatchEvent(new Event("input"));
    }
  });
  // Setas entre os resultados; Esc volta ao campo.
  lista.addEventListener("keydown", (ev) => {
    const todos = itens();
    const i = todos.indexOf(document.activeElement as HTMLAnchorElement);
    if (ev.key === "ArrowDown") {
      ev.preventDefault();
      todos[Math.min(i + 1, todos.length - 1)]?.focus();
    } else if (ev.key === "ArrowUp") {
      ev.preventDefault();
      if (i <= 0) campo.focus();
      else todos[i - 1]?.focus();
    } else if (ev.key === "Escape") {
      campo.focus();
      fechar();
    }
  });
  // Toque fora da busca fecha a lista (o texto fica, e volta ao focar o campo).
  document.addEventListener("pointerdown", (ev) => {
    if (!(ev.target as HTMLElement).closest(".busca-fixa")) fechar();
  });
}

/** Depois de abrir o assunto: mostra o elemento pedido, abrindo o que estiver guardado. */
export function revelar(alvo: string): void {
  if (!alvo) return;
  let no = document.getElementById(alvo);
  if (!no && alvo.startsWith("m-")) {
    // Métrica de estados ou de países: escolhe na lista suspensa.
    const lista = document.querySelector<HTMLSelectElement>(
      "#estados-metrica, #mundo-metrica",
    );
    const valor = alvo.slice(2);
    if (lista && [...lista.options].some((o) => o.value === valor)) {
      lista.value = valor;
      lista.dispatchEvent(new Event("change"));
      no = lista.closest(".barra-controles") ?? lista;
    }
  }
  if (!no && alvo.startsWith("uf-")) {
    // Um estado: abre a ficha dele.
    const lista = document.querySelector<HTMLSelectElement>("#estados-ficha");
    if (lista) {
      lista.value = alvo.slice(3);
      lista.dispatchEvent(new Event("change"));
      no = lista.closest(".painel-mundo") as HTMLElement | null;
    }
  }
  if (!no && alvo.startsWith("e-")) {
    // Uma estatal: a ficha já abre nela pelo endereço; se a lista estiver na tela, troca.
    const lista = document.querySelector<HTMLSelectElement>("#estatais-ficha");
    if (lista && [...lista.options].some((o) => o.value === alvo.slice(2))) {
      lista.value = alvo.slice(2);
      lista.dispatchEvent(new Event("change"));
    }
    no = document.getElementById("fichas-estatais");
  }
  if (!no && (alvo.startsWith("uf-") || alvo.startsWith("p-"))) {
    no =
      document.getElementById(alvo) ??
      document.querySelector(".mapa, .ranking-pontos");
  }
  if (!no && (alvo.startsWith("g-") || alvo.startsWith("t-")))
    no = escolherAlternativa(alvo);
  if (!no) {
    // Pode estar atrás de "Mais números"/"Mais gráficos" ou numa tabela guardada.
    document
      .querySelectorAll<HTMLButtonElement>(".abrir button")
      .forEach((b) => b.click());
    no = document.getElementById(alvo);
    const guardado = no?.closest("details");
    if (guardado) guardado.open = true;
  }
  if (!no) {
    for (const d of document.querySelectorAll<HTMLDetailsElement>(
      "details.guardado",
    )) {
      if (d.id === alvo) {
        d.open = true;
        no = d;
      }
    }
  }
  if (!no) return;
  if (no instanceof HTMLDetailsElement) no.open = true; // tabela guardada: abre
  // Dentro de caixas guardadas (o indicador do painel de alerta, num grupo): abre todas.
  for (
    let d = no.parentElement?.closest("details");
    d;
    d = d.parentElement?.closest("details")
  ) {
    d.open = true;
  }
  const achado = no;
  requestAnimationFrame(() => {
    achado.scrollIntoView({ behavior: "smooth", block: "center" });
    achado.classList.add("achado");
    window.setTimeout(() => achado.classList.remove("achado"), 2200);
  });
}
