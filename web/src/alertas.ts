// O painel de alerta da aba de riscos: cada indicador como um ponto na régua da própria
// história, com o lado ruim sempre à direita. Fica guardado; abre no clique.
// A cor nunca vai sozinha: indicador "aceso" leva ▲ e a frase.

import "./alertas.css";
import { comUnidade, data, numero, periodo } from "./formato";
import { el, guardar } from "./pecas";
import type { Alerta } from "./tipos";

/** Daqui para cima o indicador está no quinto pior da própria história. */
const ACESO = 80;

export function acesos(alertas: Alerta[]): number {
  return alertas.filter((a) => a.pior_que >= ACESO).length;
}

function linha(a: Alerta): HTMLElement {
  const aceso = a.pior_que >= ACESO;
  const no = el("div", aceso ? "alerta aceso" : "alerta");
  no.id = `a-${a.id}`;

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

  // À esquerda o melhor valor que a história já viu; à direita, o pior.
  const alto = a.pior_quando === "alto";
  const [melhor, pior] = alto ? [a.minimo, a.maximo] : [a.maximo, a.minimo];
  const amplitude = a.maximo - a.minimo || 1;
  const pos = (v: number): string => {
    const fracao = alto ? (v - a.minimo) / amplitude : (a.maximo - v) / amplitude;
    return `${Math.min(100, Math.max(0, fracao * 100))}%`;
  };
  const regua = el("div", "alerta-regua");
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
  const ponto = el("i", "alerta-ponto");
  ponto.style.left = pos(a.valor);
  trilho.append(ponto);
  const pontas = el("span", "alerta-pontas");
  pontas.append(el("span", "", numero(melhor, a.casas)), el("span", "", numero(pior, a.casas)));
  regua.append(trilho, pontas);

  const valor = el("div", "alerta-valor");
  valor.append(el("strong", "", comUnidade(a.valor, a.unidade, a.casas)));
  const selo = el("span", aceso ? "situacao acima" : "situacao");
  if (aceso) selo.append(el("i", "", "▲"));
  selo.append(document.createTextNode(`pior que ${numero(a.pior_que, 0)} % da história`));
  valor.append(selo);

  const desde = data(a.desde).getUTCFullYear();
  no.title =
    `${a.nome}: ${comUnidade(a.valor, a.unidade, a.casas)} em ${periodo(a.referencia, a.periodicidade)}. ` +
    `Desde ${desde}, foi de ${numero(a.minimo, a.casas)} a ${numero(a.maximo, a.casas)}, com mediana ` +
    `${numero(a.mediana, a.casas)}.` +
    (a.limite ? ` ${a.limite.rotulo}: ${numero(a.limite.valor, a.casas)}.` : "") +
    ` Fonte: ${a.fonte}.`;
  no.append(nome, regua, valor);
  return no;
}

export function montarAlertas(alertas: Alerta[]): HTMLElement {
  const total = alertas.length;
  const ligados = acesos(alertas);
  const caixa = guardar(
    "Painel de alerta",
    `${ligados} de ${total} indicadores estão no quinto pior da própria história`,
    () => {
      const partes: HTMLElement[] = [];
      const legenda = el("p", "alerta-legenda");
      legenda.append(
        el("span", "", "← melhor da história"),
        el("span", "alerta-legenda-meio", "traço: mediana"),
        el("span", "", "pior da história →"),
      );
      partes.push(legenda);
      const grupos = new Map<string, Alerta[]>();
      for (const a of alertas) grupos.set(a.grupo, [...(grupos.get(a.grupo) ?? []), a]);
      for (const [grupo, itens] of grupos) {
        const titulo = el("h3", "alerta-grupo", grupo);
        titulo.append(el("small", "", `${acesos(itens)} de ${itens.length} acesos`));
        const bloco = el("div", "alerta-lista");
        itens.forEach((a) => bloco.append(linha(a)));
        partes.push(titulo, bloco);
      }
      const primeiros = alertas.map((a) => data(a.desde).getUTCFullYear());
      partes.push(
        el(
          "p",
          "nota",
          "Cada linha põe o valor mais recente na régua de tudo o que o indicador já marcou " +
            `(desde ${Math.min(...primeiros)}, ou desde que a série existe). "Aceso" (▲) é estar pior ` +
            "que 80 % da própria história. Não é previsão de crise nem nota de risco: um " +
            "indicador pode estar no pior da história dele e ainda assim longe de um nível perigoso, " +
            "e o contrário. Onde há limite oficial, ele aparece como traço amarelo.",
        ),
      );
      return partes;
    },
  );
  caixa.id = "t-alertas";
  return caixa;
}
