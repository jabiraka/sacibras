// Peças parecidas num lugar só (Caio, 19/11/2026: "vamos usar o artifício de colocar
// parâmetros para gráficos parecidos, assim mudando o parâmetro muda o gráfico ou tabela,
// podendo acrescentar informações ao site sem ter que excluir coisas e sem ficar pesado").
// O builder põe as parecidas em `alternativas` do principal; aqui a lista em cima troca a
// peça inteira, de qualquer tipo (linha, barras, pirâmide, tabela com períodos...).

import { el } from "./pecas";
import { listaSuspensa } from "./pontos";

interface ComAlternativas<T> {
  id: string;
  titulo: string;
  rotulo_opcao?: string;
  alternativas?: T[];
}

/** O principal com a lista das parecidas; `montar` desenha uma peça sem lista. */
export function comAlternativas<T extends ComAlternativas<T>>(
  principal: T,
  montar: (x: T) => HTMLElement,
  prefixo: "g" | "t",
): HTMLElement {
  const todas = [principal, ...(principal.alternativas ?? [])];
  const caixa = el("div", "com-alternativas");
  // Quem procura uma das de trás (a busca, um elo) acha a caixa e a lista escolhe.
  caixa.dataset.alternativas = todas.map((x) => `${prefixo}-${x.id}`).join(" ");
  const idLista = `alternativa-${prefixo}-${principal.id}`;
  const nome = prefixo === "g" ? "Gráfico" : "Tabela";

  function mostrar(id: string): void {
    const escolhida = todas.find((x) => x.id === id) ?? principal;
    const peca = montar({ ...escolhida, alternativas: [] });
    const { caixa: lista } = listaSuspensa(
      idLista,
      nome,
      todas.map((x) => ({ valor: x.id, rotulo: x.rotulo_opcao || x.titulo })),
      escolhida.id,
      (v) => {
        mostrar(v);
        caixa.querySelector<HTMLSelectElement>(`#${idLista}`)?.focus();
      },
    );
    const barra = el("div", "alternativas-barra");
    barra.append(lista);
    // No gráfico, a lista vem antes do título; na tabela guardada, logo abaixo do título.
    const resumo = peca.querySelector(":scope > summary");
    if (resumo) resumo.after(barra);
    else peca.prepend(barra);
    caixa.replaceChildren(peca);
  }
  mostrar(principal.id);
  return caixa;
}

/** A peça `alvo` ("g-x", "t-y") está atrás de uma lista? Escolhe-a e devolve o elemento. */
export function escolherAlternativa(alvo: string): HTMLElement | null {
  for (const caixa of document.querySelectorAll<HTMLElement>(".com-alternativas")) {
    if (!(caixa.dataset.alternativas ?? "").split(" ").includes(alvo)) continue;
    const lista = caixa.querySelector<HTMLSelectElement>("select");
    if (lista && lista.value !== alvo.slice(2)) {
      lista.value = alvo.slice(2);
      lista.dispatchEvent(new Event("change"));
    }
    return document.getElementById(alvo) ?? caixa;
  }
  return null;
}
