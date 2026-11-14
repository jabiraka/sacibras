// Peças pequenas que mais de uma vista usa.

export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  classe = "",
  texto = "",
): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (classe) e.className = classe;
  if (texto) e.textContent = texto;
  return e;
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
