// A busca: a lupa no cabeçalho (e a caixa no início) abre um painel com o campo e os
// resultados. O índice (`busca.json`) vem do builder, com os sinônimos de cada item; aqui só
// se compara sem acento e por começo de palavra.

import { el } from "./pecas";

interface Item {
  t: string;
  o: string;
  h: string;
  p?: string;
}

interface Indexado extends Item {
  titulo: string;
  resto: string;
}

let indice: Promise<Indexado[]> | null = null;

export function normalizar(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

function carregar(): Promise<Indexado[]> {
  indice ??= fetch("data/busca.json", { cache: "no-cache" })
    .then((r) => (r.ok ? (r.json() as Promise<Item[]>) : []))
    .then((itens) =>
      itens.map((i) => ({ ...i, titulo: normalizar(i.t), resto: normalizar(`${i.o} ${i.p ?? ""}`) })),
    )
    .catch(() => []);
  return indice;
}

/** Pontua o item: cada palavra da busca tem de aparecer (no começo de uma palavra do título,
 *  do lugar ou dos sinônimos); no título vale mais. */
export function pontuar(item: { titulo: string; resto: string }, palavras: string[]): number {
  let total = 0;
  for (const p of palavras) {
    const noTitulo = new RegExp(`(^|[^a-z0-9])${p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`);
    if (noTitulo.test(item.titulo)) total += item.titulo.startsWith(p) ? 4 : 3;
    else if (noTitulo.test(item.resto)) total += 1;
    else return 0;
  }
  return total;
}

export function buscar(itens: Indexado[], texto: string, limite = 12): Indexado[] {
  const palavras = normalizar(texto)
    .split(/\s+/)
    .filter((p) => p.length > 1 || /\d/.test(p));
  if (!palavras.length) return [];
  return itens
    .map((i) => ({ i, nota: pontuar(i, palavras) - (i.o === "Assunto" ? 0 : 0.5) }))
    .filter((x) => x.nota > 0)
    .sort((a, b) => b.nota - a.nota || a.i.t.length - b.i.t.length)
    .slice(0, limite)
    .map((x) => x.i);
}

let painel: HTMLDialogElement | null = null;
let fechadoEm = 0;

export function abrirBusca(inicial = ""): void {
  // O Enter que escolhe um resultado devolve o foco ao botão que abriu a busca, e o mesmo
  // Enter o "clica" de novo: logo depois de fechar, não reabre.
  if (Date.now() - fechadoEm < 400) return;
  painel ??= montarPainel();
  const campo = painel.querySelector("input") as HTMLInputElement;
  campo.value = inicial;
  campo.dispatchEvent(new Event("input"));
  if (!painel.open) painel.showModal();
  campo.focus();
}

function montarPainel(): HTMLDialogElement {
  const dialogo = el("dialog", "busca vidro");
  dialogo.setAttribute("aria-label", "Buscar no painel");
  const linha = el("div", "busca-linha");
  const campo = el("input", "busca-campo");
  campo.type = "search";
  campo.placeholder = "Buscar: inflação, dólar, desemprego, dívida dos estados…";
  campo.setAttribute("aria-label", "O que você quer ver?");
  campo.autocomplete = "off";
  campo.enterKeyHint = "go";
  const fechar = el("button", "busca-fechar", "Fechar");
  fechar.type = "button";
  fechar.addEventListener("click", () => dialogo.close());
  linha.append(campo, fechar);
  const lista = el("ol", "busca-resultados");
  const aviso = el("p", "busca-aviso");
  dialogo.append(linha, aviso, lista);

  const ir = (h: string): void => {
    dialogo.close();
    if (location.hash === h) window.dispatchEvent(new HashChangeEvent("hashchange"));
    else location.hash = h;
  };
  let pedido = 0;
  campo.addEventListener("input", () => {
    const meu = ++pedido;
    void carregar().then((itens) => {
      if (meu !== pedido) return;
      const achados = buscar(itens, campo.value);
      lista.replaceChildren(
        ...achados.map((a) => {
          const li = el("li");
          const elo = el("a", "busca-item");
          elo.href = a.h;
          elo.addEventListener("click", (ev) => {
            ev.preventDefault();
            ir(a.h);
          });
          elo.append(el("span", "busca-titulo", a.t), el("span", "busca-onde", a.o));
          li.append(elo);
          return li;
        }),
      );
      aviso.textContent =
        campo.value.trim() && !achados.length
          ? "Nada com esse nome. Tente outra palavra (\"juros\", \"emprego\", \"bolsa\")."
          : "";
    });
  });
  campo.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") {
      ev.preventDefault();
      const primeiro = lista.querySelector("a");
      if (primeiro) ir(primeiro.getAttribute("href") ?? "#");
    }
  });
  // Toque fora do painel fecha.
  dialogo.addEventListener("click", (ev) => {
    if (ev.target === dialogo) dialogo.close();
  });
  dialogo.addEventListener("close", () => {
    fechadoEm = Date.now();
  });
  document.body.append(dialogo);
  return dialogo;
}

/** Depois de abrir o assunto: mostra o elemento pedido, abrindo o que estiver guardado. */
export function revelar(alvo: string): void {
  if (!alvo) return;
  let no = document.getElementById(alvo);
  if (!no && alvo.startsWith("m-")) {
    // Métrica de estados ou de países: escolhe na lista suspensa.
    const lista = document.querySelector<HTMLSelectElement>("#estados-metrica, #mundo-metrica");
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
  if (!no && (alvo.startsWith("uf-") || alvo.startsWith("p-"))) {
    no = document.getElementById(alvo) ?? document.querySelector(".mapa, .ranking-pontos");
  }
  if (!no) {
    // Pode estar atrás de "Mais números"/"Mais gráficos" ou numa tabela guardada.
    document.querySelectorAll<HTMLButtonElement>(".abrir button").forEach((b) => b.click());
    no = document.getElementById(alvo);
    const guardado = no?.closest("details");
    if (guardado) guardado.open = true;
  }
  if (!no) {
    for (const d of document.querySelectorAll<HTMLDetailsElement>("details.guardado")) {
      if (d.id === alvo) {
        d.open = true;
        no = d;
      }
    }
  }
  if (!no) return;
  if (no instanceof HTMLDetailsElement) no.open = true; // tabela guardada: abre
  const achado = no;
  requestAnimationFrame(() => {
    achado.scrollIntoView({ behavior: "smooth", block: "center" });
    achado.classList.add("achado");
    window.setTimeout(() => achado.classList.remove("achado"), 2200);
  });
}
