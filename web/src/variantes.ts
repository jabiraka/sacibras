// Gráfico com escolha: a lista "Métrica" troca o que o gráfico mostra (as séries, a unidade e
// a nota) e as fichas ligam e desligam cada série (Caio, 19/11/2026, no teste de estresse:
// "coloque o parâmetro pra mudar a métrica no gráfico mesmo" e "deixe tbm escolher qual
// teste mostrar, se todos ou só alguns"). A série de consenso (a linha de base) fica sempre.
// A cor segue a série em todas as métricas: a crise de 2008 tem a mesma cor no dólar e na
// dívida.

import { montarGrafico, tema } from "./grafico";
import { el } from "./pecas";
import { listaSuspensa } from "./pontos";
import type { Grafico, Serie, VarianteGrafico } from "./tipos";

let contador = 0;

export function montarComEscolha(g: Grafico): HTMLElement {
  contador += 1;
  const idLista = `metrica-${g.id}-${contador}`;
  const variantes: VarianteGrafico[] = g.variantes?.length
    ? g.variantes
    : [
        {
          id: g.id,
          rotulo: g.titulo,
          titulo: g.titulo,
          unidade: g.unidade,
          casas: g.casas,
          periodicidade: g.periodicidade,
          series: g.series,
          linhas: g.linhas,
          nota: g.nota,
        },
      ];
  const escolhivel = (s: Serie): boolean => !!g.escolher_series && s.papel !== "consenso";
  // Uma casa da paleta por série escolhível, na ordem em que aparecem; a casa 0 fica com a
  // linha de base, como no gráfico sem escolha.
  const casas = new Map<string, number>();
  const nomes = new Map<string, string>();
  // Na ordem da métrica que tem mais delas (os episódios em ordem de data).
  const porTamanho = [...variantes].sort(
    (a, b) => b.series.filter(escolhivel).length - a.series.filter(escolhivel).length,
  );
  for (const v of porTamanho)
    for (const s of v.series)
      if (escolhivel(s) && !casas.has(s.id)) {
        casas.set(s.id, casas.size + 1);
        nomes.set(s.id, s.nome);
      }
  const ligadas = new Set(casas.keys());
  let atual = variantes[0] as VarianteGrafico;
  const caixa = el("div", "grafico-com-escolha");
  const cores = tema().series;

  function controles(): HTMLElement {
    const barra = el("div", "escolhidos");
    if (variantes.length > 1) {
      const lista = listaSuspensa(
        idLista,
        g.rotulo_variantes || "Métrica",
        variantes.map((v) => ({ valor: v.id, rotulo: v.rotulo })),
        atual.id,
        (id) => {
          atual = variantes.find((v) => v.id === id) ?? atual;
          pintar();
          caixa.querySelector<HTMLSelectElement>(`#${idLista}`)?.focus();
        },
      );
      barra.append(lista.caixa);
    }
    const presentes = [...casas.keys()].filter((id) => atual.series.some((s) => s.id === id));
    if (presentes.length > 1) {
      const todas = presentes.every((id) => ligadas.has(id));
      const botaoTodos = el("button", "ficha", "Todos");
      botaoTodos.type = "button";
      botaoTodos.setAttribute("aria-pressed", String(todas));
      botaoTodos.addEventListener("click", () => {
        if (todas) for (const id of presentes) ligadas.delete(id);
        else for (const id of presentes) ligadas.add(id);
        pintar();
      });
      barra.append(botaoTodos);
    }
    for (const id of presentes) {
      const ficha = el("button", "ficha pais");
      ficha.type = "button";
      ficha.style.setProperty("--cor", cores[(casas.get(id) ?? 0) % cores.length] ?? "");
      ficha.setAttribute("aria-pressed", String(ligadas.has(id)));
      ficha.append(el("i"), document.createTextNode(nomes.get(id) ?? id));
      ficha.addEventListener("click", () => {
        if (ligadas.has(id)) ligadas.delete(id);
        else ligadas.add(id);
        pintar();
      });
      barra.append(ficha);
    }
    return barra;
  }

  function pintar(): void {
    const series = atual.series
      .filter((s) => !escolhivel(s) || ligadas.has(s.id))
      // Sem fichas, a cor segue a ordem da série, como em qualquer gráfico.
      .map((s) => ({ ...s, cor: g.escolher_series ? (casas.get(s.id) ?? 0) : undefined }));
    const vazio = series.length === 0;
    const grafico = montarGrafico({
      ...g,
      titulo: atual.titulo,
      unidade: atual.unidade,
      casas: atual.casas,
      periodicidade: atual.periodicidade,
      linhas: atual.linhas,
      nota: atual.nota,
      fonte: atual.fonte || g.fonte,
      // A frase do builder fala da primeira métrica; nas outras, nada.
      manchete: atual.id === variantes[0]?.id ? g.manchete : "",
      series: vazio ? atual.series.slice(0, 0) : series,
    });
    const cabeca = grafico.querySelector("header");
    const barra = controles();
    if (cabeca) cabeca.after(barra);
    else grafico.prepend(barra);
    if (vazio) barra.after(el("p", "vazio", "Nenhum episódio escolhido: toque em um acima."));
    caixa.replaceChildren(grafico);
  }
  pintar();
  return caixa;
}
