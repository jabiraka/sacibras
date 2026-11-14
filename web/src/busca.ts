// A busca: o campo fica fixo no menu lateral (no celular, na faixa do topo) e os resultados
// aparecem logo abaixo dele. O índice (`busca.json`) vem do builder, com os sinônimos de cada item; aqui só
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

/** Põe o cursor no campo da busca, que fica sempre à vista no menu lateral (no celular, no
 *  topo). Atalho: a tecla "/". */
export function abrirBusca(inicial = ""): void {
  const campo = document.getElementById("busca-campo") as HTMLInputElement | null;
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
  const campo = document.getElementById("busca-campo") as HTMLInputElement | null;
  const saida = document.getElementById("busca-saida");
  if (!campo || !saida) return;
  const lista = saida.querySelector("ol") as HTMLOListElement;
  const aviso = saida.querySelector("p") as HTMLParagraphElement;

  const fechar = (): void => {
    saida.hidden = true;
    campo.setAttribute("aria-expanded", "false");
  };
  const ir = (h: string): void => {
    fechar();
    campo.value = "";
    campo.blur();
    if (location.hash === h) window.dispatchEvent(new HashChangeEvent("hashchange"));
    else location.hash = h;
  };
  const itens = (): HTMLAnchorElement[] => [...lista.querySelectorAll<HTMLAnchorElement>("a")];

  let pedido = 0;
  campo.addEventListener("input", () => {
    const meu = ++pedido;
    const texto = campo.value;
    if (!texto.trim()) {
      lista.replaceChildren();
      aviso.textContent = "";
      fechar();
      return;
    }
    void carregar().then((todos) => {
      if (meu !== pedido) return;
      const achados = buscar(todos, texto);
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
      aviso.textContent = achados.length
        ? ""
        : 'Nada com esse nome. Tente outra palavra ("juros", "emprego", "bolsa").';
      saida.hidden = false;
      campo.setAttribute("aria-expanded", "true");
    });
  });
  campo.addEventListener("focus", () => {
    if (campo.value.trim() && (lista.children.length || aviso.textContent)) saida.hidden = false;
  });
  campo.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") {
      ev.preventDefault();
      const primeiro = itens()[0];
      if (primeiro) ir(primeiro.getAttribute("href") ?? "#");
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
  // Dentro de caixas guardadas (o indicador do painel de alerta, num grupo): abre todas.
  for (let d = no.parentElement?.closest("details"); d; d = d.parentElement?.closest("details")) {
    d.open = true;
  }
  const achado = no;
  requestAnimationFrame(() => {
    achado.scrollIntoView({ behavior: "smooth", block: "center" });
    achado.classList.add("achado");
    window.setTimeout(() => achado.classList.remove("achado"), 2200);
  });
}
