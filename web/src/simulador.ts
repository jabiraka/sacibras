// O simulador da dívida: a linha de base vem do builder (hipóteses do Focus) e a conta é
// refeita aqui quando a pessoa mexe nos quatro controles (a inflação entrou a pedido do Caio,
// 14/11/2026: "na simulação dá pra colocar também a inflação?").
//   dívida seguinte = dívida × (1 + juro) ÷ ((1 + crescimento) × (1 + inflação)) − primário

import { numero, sinal } from "./formato";
import { montarGrafico } from "./grafico";
import { el } from "./pecas";
import type { Grafico, SimuladorDivida } from "./tipos";

interface Controle {
  id: "juro" | "crescimento" | "inflacao" | "primario";
  rotulo: string;
  ajuda: string;
}

const CONTROLES: Controle[] = [
  { id: "juro", rotulo: "Juro da dívida", ajuda: "quanto a dívida paga por ano" },
  { id: "crescimento", rotulo: "Crescimento do PIB", ajuda: "acima da inflação" },
  {
    id: "inflacao",
    rotulo: "Inflação (IPCA)",
    ajuda: "com o juro parado, mais inflação encolhe a dívida em % do PIB",
  },
  { id: "primario", rotulo: "Resultado primário", ajuda: "receitas menos despesas, sem os juros" },
];

export function trajetoria(
  s: SimuladorDivida,
  d: { juro: number; crescimento: number; inflacao: number; primario: number },
): number[] {
  let divida = s.divida_inicial;
  return s.anos.map((_, i) => {
    const juro = (s.juro[i] ?? 0) + d.juro;
    const crescimento = (s.crescimento[i] ?? 0) + d.crescimento;
    const inflacao = (s.inflacao[i] ?? 0) + d.inflacao;
    const primario = (s.primario[i] ?? 0) + d.primario;
    divida = (divida * (1 + juro / 100)) / ((1 + crescimento / 100) * (1 + inflacao / 100)) - primario;
    return divida;
  });
}

export function montarSimulador(s: SimuladorDivida): HTMLElement[] {
  const desvios = { juro: 0, crescimento: 0, inflacao: 0, primario: 0 };
  const painel = el("div", "simulador");
  const resultado = el("p", "posicao");
  const tela = el("div");
  const valores = new Map<string, HTMLElement>();
  const entradas: HTMLInputElement[] = [];

  for (const c of CONTROLES) {
    const linha = el("label", "controle");
    const texto = el("span", "controle-rotulo", c.rotulo);
    texto.append(el("small", "", c.ajuda));
    const entrada = el("input");
    entrada.type = "range";
    entrada.id = `sim-${c.id}`;
    entrada.min = "-3";
    entrada.max = "3";
    entrada.step = "0.1";
    entrada.value = "0";
    const valor = el("output", "controle-valor");
    valor.htmlFor.add(entrada.id);
    valores.set(c.id, valor);
    entrada.addEventListener("input", () => {
      desvios[c.id] = Number(entrada.value);
      pintar();
    });
    entradas.push(entrada);
    linha.append(texto, entrada, valor);
    painel.append(linha);
  }
  const zerar = el("button", "botao", "Voltar à linha de base");
  zerar.type = "button";
  zerar.addEventListener("click", () => {
    desvios.juro = desvios.crescimento = desvios.inflacao = desvios.primario = 0;
    entradas.forEach((e) => (e.value = "0"));
    pintar();
  });

  let pendente = 0;
  function pintar(): void {
    const primeiro = s.anos[0] ?? s.ano_inicial + 1;
    const base = {
      juro: s.juro[0] ?? 0,
      crescimento: s.crescimento[0] ?? 0,
      inflacao: s.inflacao[0] ?? 0,
      primario: s.primario[0] ?? 0,
    };
    for (const c of CONTROLES) {
      const d = desvios[c.id];
      const alvo = valores.get(c.id);
      if (!alvo) continue;
      const unidade = c.id === "primario" ? "% do PIB" : "%";
      alvo.textContent =
        d === 0
          ? `linha de base (${numero(base[c.id], 1)} ${unidade} em ${primeiro})`
          : `${sinal(d, 1)} pp (${numero(base[c.id] + d, 1)} ${unidade} em ${primeiro})`;
    }
    const simulada = trajetoria(s, desvios);
    const ultimoAno = s.anos[s.anos.length - 1] ?? s.ano_inicial;
    const fim = simulada[simulada.length - 1] ?? s.divida_inicial;
    const focusFim = s.focus_divida[s.focus_divida.length - 1];
    resultado.replaceChildren(
      document.createTextNode(`Com essas hipóteses, a dívida chega a `),
      el("b", "", `${numero(fim, 1)} % do PIB em ${ultimoAno}`),
      document.createTextNode(
        focusFim === null || focusFim === undefined
          ? "."
          : `. O Focus espera ${numero(focusFim, 1)} %.`,
      ),
    );
    cancelAnimationFrame(pendente);
    pendente = requestAnimationFrame(() => {
      const partida: [string, number] = [`${s.ano_inicial}-01-01`, s.divida_inicial];
      const g: Grafico = {
        id: "simulador-divida",
        titulo: "Dívida bruta: o que já foi, o Focus e a sua simulação",
        subtitulo: "",
        tipo: "linha",
        unidade: "% do PIB",
        casas: 1,
        periodicidade: "A",
        series: [
          { id: "realizado", nome: "Realizado", papel: "realizado", tracejado_desde: null, pontos: s.realizado },
          {
            id: "focus",
            nome: "Focus (mediana)",
            papel: "consenso",
            tracejado_desde: null,
            pontos: [partida, ...s.anos.map((a, i): [string, number | null] => [`${a}-01-01`, s.focus_divida[i] ?? null])],
          },
          {
            id: "simulacao",
            nome: "Simulação",
            papel: "previsao",
            tracejado_desde: null,
            pontos: [partida, ...s.anos.map((a, i): [string, number | null] => [`${a}-01-01`, Math.round((simulada[i] ?? 0) * 10) / 10])],
          },
        ],
        faixa: null,
        intervalos: [],
        linhas: [],
        janela_anos: null,
        fonte: s.fonte,
        nota: "",
        largura: "inteira",
      };
      tela.replaceChildren(montarGrafico(g));
    });
  }
  pintar();
  painel.append(zerar);
  return [painel, resultado, tela, el("p", "nota", s.nota)];
}
