// Peças pequenas que mais de uma vista usa.

export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  classe = "",
  texto = "",
): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (classe) e.className = classe;
  if (texto) e.textContent = colar(texto);
  return e;
}

/** O número não se separa da unidade na quebra de linha: "2,2 %" não vira "2,2" numa linha e
 *  "%" na outra (Brasil no mundo, 390 px). Espaço inseparável entre o número e "%", "pp",
 *  "a.a." e "p.p.", e entre "R$"/"US$" e o número. */
export function colar(texto: string): string {
  return texto
    .replace(/(\d) (%|pp\b|p\.p\.|a\.a\.)/g, "$1\u00a0$2")
    .replace(/(R\$|US\$) (?=[\d−-])/g, "$1\u00a0");
}

/** Algo guardado: só o título aparece; o conteúdo é montado e aberto no clique. */
export function guardar(
  titulo: string,
  subtitulo: string,
  conteudo: () => HTMLElement[],
): HTMLElement {
  const caixa = el("details", "vidro guardado");
  const cabeca = el("summary");
  const nome = el("span", "", titulo);
  if (subtitulo) nome.append(el("small", "", subtitulo));
  cabeca.append(nome, el("span", "seta", "→"));
  const dentro = el("div", "conteudo");
  let montado = false;
  caixa.addEventListener("toggle", () => {
    if (caixa.open && !montado) {
      dentro.append(...conteudo());
      montado = true;
    }
  });
  caixa.append(cabeca, dentro);
  return caixa;
}

/** Troca a peça de uma caixa sem pulo (Caio, 25/11/2026: o menu mudava de lugar e o gráfico
 *  vizinho se mexia ao escolher outra opção): a caixa guarda a maior altura que a peça já teve,
 *  então a linha da grade não encolhe; a peça nova entra com um fade curto, só na troca. */
export function trocarSuave(caixa: HTMLElement, nova: HTMLElement, primeira: boolean): void {
  const antiga = caixa.firstElementChild as HTMLElement | null;
  const altura = Math.max(Number(caixa.dataset.altura ?? 0), antiga?.offsetHeight ?? 0);
  caixa.replaceChildren(nova);
  if (primeira || !antiga) return;
  const minima = Math.max(altura, Number(caixa.dataset.altura ?? 0));
  caixa.dataset.altura = String(minima);
  nova.style.minHeight = `${minima}px`;
  nova.classList.add("troca-entra");
  nova.addEventListener("animationend", () => nova.classList.remove("troca-entra"), { once: true });
}
