// O painel de alerta da aba de riscos: cada indicador como um ponto na régua da própria
// história, com o lado ruim sempre à direita. Fica guardado; abre no clique.
// A cor nunca vai sozinha: indicador "aceso" leva ▲ e a frase.
// Caio, 14/11/2026: "classifique, não precisa mostrar tudo de uma vez [...] o que falta dizer é
// o que significa, por que é um alerta, o que isso pode levar". Os grupos abrem um de cada vez
// (o com mais acesos em cima), os acesos ficam num atalho, e cada linha abre a explicação.

import "./alertas.css";
import { comUnidade, data, numero, periodo } from "./formato";
import { el, guardar } from "./pecas";
import type { Alerta } from "./tipos";

/** Daqui para cima o indicador está no quinto pior da própria história. */
const ACESO = 80;
/** Quantos acesos aparecem no atalho antes do "+N". */
const FICHAS = 6;

export function acesos(alertas: Alerta[]): number {
  return alertas.filter((a) => a.pior_que >= ACESO).length;
}

/** A régua: o melhor valor que a história já viu à esquerda, o pior à direita. */
function regua(a: Alerta): HTMLElement {
  const alto = a.pior_quando === "alto";
  const [melhor, pior] = alto ? [a.minimo, a.maximo] : [a.maximo, a.minimo];
  const amplitude = a.maximo - a.minimo || 1;
  const pos = (v: number): string => {
    const fracao = alto ? (v - a.minimo) / amplitude : (a.maximo - v) / amplitude;
    return `${Math.min(100, Math.max(0, fracao * 100))}%`;
  };
  const caixa = el("div", "alerta-regua");
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
  caixa.append(trilho, pontas);
  return caixa;
}

/** O que abre ao tocar na linha: o que é, por que é alerta, no que pode dar e a história. */
function explicacao(a: Alerta): HTMLElement {
  const caixa = el("div", "alerta-texto");
  const campo = (titulo: string, texto: string): void => {
    if (!texto) return;
    const p = el("p");
    p.append(el("b", "", titulo), document.createTextNode(` ${texto}`));
    caixa.append(p);
  };
  campo("O que é.", a.significa ?? "");
  campo("Por que é alerta.", a.por_que ?? "");
  campo("Pode levar a.", a.pode_levar ?? "");
  const desde = data(a.desde).getUTCFullYear();
  const lado = a.pior_quando === "alto" ? "alto" : "baixo";
  const historia = el(
    "p",
    "alerta-historia",
    `Desde ${desde}, foi de ${numero(a.minimo, a.casas)} a ${numero(a.maximo, a.casas)}, com ` +
      `mediana ${numero(a.mediana, a.casas)}; o lado ruim é o valor ${lado}. Hoje está pior ` +
      `que ${numero(a.pior_que, 0)} % da própria história.` +
      (a.limite ? ` ${a.limite.rotulo}: ${numero(a.limite.valor, a.casas)}.` : ""),
  );
  caixa.append(historia);
  return caixa;
}

function linha(a: Alerta): HTMLElement {
  const aceso = a.pior_que >= ACESO;
  const no = el("details", aceso ? "alerta aceso" : "alerta");
  no.id = `a-${a.id}`;
  const cabeca = el("summary", "alerta-linha");

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

  const valor = el("div", "alerta-valor");
  valor.append(el("strong", "", comUnidade(a.valor, a.unidade, a.casas)));
  const selo = el("span", aceso ? "situacao acima" : "situacao");
  if (aceso) selo.append(el("i", "", "▲"));
  selo.append(document.createTextNode(`pior que ${numero(a.pior_que, 0)} % da história`));
  valor.append(selo);

  const abre = el("span", "alerta-abre", "›");
  abre.setAttribute("aria-hidden", "true");
  cabeca.append(nome, regua(a), valor, abre);
  no.append(cabeca, explicacao(a));
  return no;
}

/** Abre o grupo e a linha do indicador, e leva a tela até ela. */
function irAte(id: string): void {
  const no = document.getElementById(`a-${id}`);
  if (!(no instanceof HTMLDetailsElement)) return;
  const grupo = no.parentElement?.closest("details");
  if (grupo instanceof HTMLDetailsElement) grupo.open = true;
  no.open = true;
  no.scrollIntoView({ behavior: "smooth", block: "center" });
  no.classList.add("achado");
  window.setTimeout(() => no.classList.remove("achado"), 2200);
}

export function montarAlertas(alertas: Alerta[]): HTMLElement {
  const total = alertas.length;
  const ligados = acesos(alertas);
  const caixa = guardar(
    "Painel de alerta",
    `${ligados} de ${total} indicadores estão no quinto pior da própria história`,
    () => {
      const partes: HTMLElement[] = [];
      partes.push(
        el(
          "p",
          "alerta-intro",
          "Os indicadores estão em seis grupos. Abra um grupo para ver cada indicador na régua " +
            "da própria história, e toque num indicador para saber o que ele é, por que é um " +
            "sinal de alerta e no que pode dar.",
        ),
      );

      // Os acesos primeiro, como atalho: o toque abre o grupo e a linha.
      const ligadosAgora = alertas
        .filter((a) => a.pior_que >= ACESO)
        .sort((a, b) => b.pior_que - a.pior_que);
      if (ligadosAgora.length) {
        const atalho = el("div", "alerta-atalhos");
        atalho.append(el("p", "alerta-atalhos-titulo", `Acesos agora (${ligadosAgora.length})`));
        const lista = el("div", "alerta-fichas");
        const ficha = (a: Alerta): HTMLElement => {
          const b = el("button", "alerta-ficha");
          b.type = "button";
          b.append(el("i", "", "▲"), document.createTextNode(a.nome));
          b.addEventListener("click", () => irAte(a.id));
          return b;
        };
        // Os seis piores à vista; o resto num toque.
        ligadosAgora.slice(0, FICHAS).forEach((a) => lista.append(ficha(a)));
        const resto = ligadosAgora.slice(FICHAS);
        if (resto.length) {
          const mais = el("button", "alerta-ficha mais", `+${resto.length}`);
          mais.type = "button";
          mais.setAttribute("aria-label", `Mostrar mais ${resto.length} acesos`);
          mais.addEventListener("click", () => mais.replaceWith(...resto.map(ficha)));
          lista.append(mais);
        }
        atalho.append(lista);
        partes.push(atalho);
      }

      const grupos = new Map<string, Alerta[]>();
      for (const a of alertas) grupos.set(a.grupo, [...(grupos.get(a.grupo) ?? []), a]);
      // O grupo com mais acesos (em proporção) primeiro.
      const ordem = [...grupos].sort(
        ([, x], [, y]) => acesos(y) / y.length - acesos(x) / x.length,
      );
      for (const [grupo, itens] of ordem) {
        const bloco = el("details", "alerta-grupo-caixa");
        const cabeca = el("summary", "alerta-grupo");
        const nome = el("span", "alerta-grupo-nome", grupo);
        // Um ponto por indicador: cheio e laranja se aceso, vazio se não.
        const pontos = el("span", "alerta-grupo-pontos");
        pontos.setAttribute("aria-hidden", "true");
        for (const a of [...itens].sort((x, y) => y.pior_que - x.pior_que)) {
          pontos.append(el("i", a.pior_que >= ACESO ? "aceso" : ""));
        }
        const n = acesos(itens);
        const conta = el(
          "small",
          n ? "alerta-grupo-conta tem" : "alerta-grupo-conta",
          `${n} de ${itens.length} ${n === 1 ? "aceso" : "acesos"}`,
        );
        cabeca.append(nome, pontos, conta, el("span", "seta", "→"));
        const lista = el("div", "alerta-lista");
        const legenda = el("p", "alerta-legenda");
        legenda.append(
          el("span", "", "← melhor da história"),
          el("span", "alerta-legenda-meio", "traço: mediana"),
          el("span", "", "pior da história →"),
        );
        lista.append(legenda);
        itens.forEach((a) => lista.append(linha(a)));
        bloco.append(cabeca, lista);
        partes.push(bloco);
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
