// O simulador da dívida com as metas do projeto da LDO (Caio, 25/11/2026: "deixe um
// simulador pra pessoa ir mudando os números e vendo como isso afeta a meta"). A linha de
// base é a do governo, do builder; aqui a conta é refeita quando a pessoa mexe:
//   dívida = anterior × (1 + juro) ÷ ((1 + crescimento) × (1 + deflator)) − primário + sobra
// Três respostas: aonde a dívida chega, quando para de subir e de quanto as metas teriam de
// ser para ela voltar ao nível de partida. A faixa vem do erro que as metas já tiveram.

import { numero, sinal } from "./formato";
import { montarGrafico } from "./grafico";
import { el } from "./pecas";
import type { Grafico, SimuladorLDO } from "./tipos";

type Id = "crescimento" | "juro" | "primario";
type Desvios = Record<Id, number>;

interface Controle {
  id: Id;
  rotulo: string;
  ajuda: string;
  min: number;
  max: number;
}

const CONTROLES: Controle[] = [
  { id: "crescimento", rotulo: "Crescimento do PIB", ajuda: "acima da inflação", min: -3, max: 2 },
  { id: "juro", rotulo: "Juro da dívida", ajuda: "o juro médio que a dívida paga por ano", min: -2, max: 3 },
  {
    id: "primario",
    rotulo: "Primário",
    ajuda: "abaixo de zero: a meta não se cumpre inteira",
    min: -3,
    max: 3,
  },
];

export function trajetoriaDaLDO(s: SimuladorLDO, d: Desvios): number[] {
  let divida = s.divida_inicial;
  return s.anos.map((_, i) => {
    const juro = (s.juro[i] ?? 0) + d.juro;
    const cresce = (s.crescimento[i] ?? 0) + d.crescimento;
    const primario = (s.primario[i] ?? 0) + d.primario;
    divida =
      (divida * (1 + juro / 100)) / ((1 + cresce / 100) * (1 + (s.deflator[i] ?? 0) / 100)) -
      primario +
      (s.sobra[i] ?? 0);
    return divida;
  });
}

/** Quanto o primário teria de ficar acima do do projeto, todo ano, para a dívida terminar no
 * nível de partida, com o crescimento e o juro escolhidos (a conta é linear no primário). */
export function primarioQueFalta(s: SimuladorLDO, d: Desvios): number {
  const fim = (p: number) => {
    const t = trajetoriaDaLDO(s, { ...d, primario: p });
    return t[t.length - 1] ?? s.divida_inicial;
  };
  const porPonto = fim(0) - fim(1);
  return porPonto > 0 ? (fim(0) - s.divida_inicial) / porPonto : 0;
}

/** O primeiro ano em que a dívida fica menor que a do ano anterior; null se não há. */
export function anoEmQueCai(s: SimuladorLDO, t: number[]): number | null {
  for (let i = 0; i < t.length; i++) {
    const antes = i === 0 ? s.divida_inicial : (t[i - 1] ?? 0);
    if ((t[i] ?? 0) < antes) return s.anos[i] ?? null;
  }
  return null;
}

export function montarSimuladorLDO(s: SimuladorLDO): HTMLElement[] {
  const desvios: Desvios = { crescimento: 0, juro: 0, primario: 0 };
  const painel = el("div", "simulador");
  const resultado = el("p", "posicao");
  const meta = el("p", "posicao");
  const faixa = el("p", "nota");
  const tela = el("div");
  const valores = new Map<Id, HTMLElement>();
  const entradas = new Map<Id, HTMLInputElement>();
  const primeiro = s.anos[0] ?? s.ano_inicial + 1;
  const ultimo = s.anos[s.anos.length - 1] ?? s.ano_inicial;

  const botoes = el("div", "simulador-botoes");
  for (const c of s.cenarios) {
    const b = el("button", "botao", c.rotulo);
    b.type = "button";
    b.addEventListener("click", () => {
      for (const { id, min, max } of CONTROLES) {
        desvios[id] = Math.min(max, Math.max(min, c[id]));
        const e = entradas.get(id);
        if (e) e.value = String(desvios[id]);
      }
      pintar();
    });
    botoes.append(b);
  }
  painel.append(botoes);

  for (const c of CONTROLES) {
    const linha = el("label", "controle");
    const texto = el("span", "controle-rotulo", c.rotulo);
    texto.append(el("small", "", c.ajuda));
    const entrada = el("input");
    entrada.type = "range";
    entrada.id = `ldo-${c.id}`;
    entrada.min = String(c.min);
    entrada.max = String(c.max);
    entrada.step = "0.1";
    entrada.value = "0";
    const valor = el("output", "controle-valor");
    valor.htmlFor.add(entrada.id);
    valores.set(c.id, valor);
    entradas.set(c.id, entrada);
    entrada.addEventListener("input", () => {
      desvios[c.id] = Number(entrada.value);
      pintar();
    });
    linha.append(texto, entrada, valor);
    painel.append(linha);
  }

  let pendente = 0;
  function pintar(): void {
    const base: Desvios = {
      crescimento: s.crescimento[0] ?? 0,
      juro: s.juro[0] ?? 0,
      primario: s.primario[0] ?? 0,
    };
    for (const c of CONTROLES) {
      const d = desvios[c.id];
      const alvo = valores.get(c.id);
      if (!alvo) continue;
      const unidade = c.id === "primario" ? "% do PIB" : "%";
      const casas = c.id === "primario" ? 2 : 1;
      alvo.textContent =
        d === 0
          ? `como no projeto (${numero(base[c.id], casas)} ${unidade} em ${primeiro})`
          : `${sinal(d, 1)} pp (${numero(base[c.id] + d, casas)} ${unidade} em ${primeiro})`;
    }
    const simulada = trajetoriaDaLDO(s, desvios);
    const fim = simulada[simulada.length - 1] ?? s.divida_inicial;
    const governoFim = s.governo_divida[s.governo_divida.length - 1];
    const focusFim = s.focus_divida[s.focus_divida.length - 1];
    const cai = anoEmQueCai(s, simulada);
    const ao_lado = [
      governoFim === undefined ? "" : `o projeto projeta ${numero(governoFim, 1)} %`,
      focusFim === null || focusFim === undefined ? "" : `o Focus espera ${numero(focusFim, 1)} %`,
    ].filter(Boolean);
    resultado.replaceChildren(
      document.createTextNode("Com essas hipóteses, a dívida bruta chega a "),
      el("b", "", `${numero(fim, 1)} % do PIB em ${ultimo}`),
      document.createTextNode(
        (ao_lado.length ? ` (${ao_lado.join("; ")})` : "") +
          (cai === null
            ? ` e não para de subir até ${ultimo}.`
            : cai === primeiro
              ? ` e já cai em ${cai}.`
              : ` e para de subir em ${cai}.`),
      ),
    );

    // A meta que seria preciso: o primário acima do do projeto que devolve a dívida ao nível
    // de partida, com o crescimento e o juro escolhidos.
    const falta = primarioQueFalta(s, desvios);
    const metaDoAno = s.meta[0];
    const nivel = `${numero(s.divida_inicial, 1)} % do PIB`;
    if (falta <= 0.05) {
      meta.replaceChildren(
        document.createTextNode(
          `Com esse crescimento e esse juro, as metas do projeto, cumpridas, bastam para a dívida voltar em ${ultimo} ao nível de ${s.ano_inicial} (${nivel})` +
            (falta < -0.05 ? `, com folga de ${numero(-falta, 1)} pp do PIB por ano.` : "."),
        ),
      );
    } else {
      meta.replaceChildren(
        document.createTextNode(
          `Com esse crescimento e esse juro, para a dívida voltar em ${ultimo} ao nível de ${s.ano_inicial} (${nivel}), o primário teria de ficar `,
        ),
        el("b", "", `${numero(falta, 1)} pp do PIB acima do que o projeto prevê`),
        document.createTextNode(
          ", todo ano" +
            (metaDoAno === null || metaDoAno === undefined
              ? "."
              : `: meta de ${numero(metaDoAno + falta, 1)} % do PIB em ${primeiro}, no lugar de ${numero(metaDoAno, 2)} %.`),
        ),
      );
    }

    // A faixa: o mesmo crescimento e o mesmo juro, com o erro que as metas já tiveram.
    const [menor, medio, maior] = s.erro_da_historia;
    const com = (erro: number) => {
      const t = trajetoriaDaLDO(s, { ...desvios, primario: -erro });
      return t[t.length - 1] ?? s.divida_inicial;
    };
    faixa.textContent =
      `Se o primário ficar abaixo do projeto como as metas das LDOs já ficaram (${numero(medio, 1)} pp do PIB na média; ` +
      `de ${numero(menor, 1)} a ${numero(maior, 1)} em 90 % dos casos), com esse crescimento e esse juro a dívida vai a ` +
      `${numero(com(medio), 1)} % do PIB em ${ultimo} (de ${numero(com(menor), 1)} a ${numero(com(maior), 1)} %).`;

    cancelAnimationFrame(pendente);
    pendente = requestAnimationFrame(() => {
      const partida: [string, number] = [`${s.ano_inicial}-01-01`, s.divida_inicial];
      // As linhas saem do último ano realizado, para não ficarem soltas no gráfico.
      const antes = s.realizado.filter(([dia]) => dia < partida[0]).slice(-1);
      const linha = (v: (number | null)[]): [string, number | null][] => [
        ...antes,
        partida,
        ...s.anos.map((a, i): [string, number | null] => [`${a}-01-01`, v[i] ?? null]),
      ];
      const g: Grafico = {
        id: "simulador-ldo",
        titulo: "Dívida bruta: o projeto da LDO 2027, o Focus e a sua simulação",
        subtitulo: "",
        tipo: "linha",
        unidade: "% do PIB",
        casas: 1,
        periodicidade: "A",
        series: [
          { id: "realizado", nome: "Realizado", papel: "realizado", tracejado_desde: null, pontos: s.realizado },
          {
            id: "governo",
            nome: "Projeto da LDO 2027 (governo)",
            papel: "previsao",
            tracejado_desde: null,
            pontos: linha(s.governo_divida),
          },
          {
            id: "focus",
            nome: "Focus (mediana)",
            papel: "consenso",
            tracejado_desde: null,
            pontos: linha(s.focus_divida),
          },
          {
            id: "simulacao",
            nome: "Simulação",
            papel: "previsao",
            tracejado_desde: null,
            pontos: linha(simulada.map((v) => Math.round(v * 10) / 10)),
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
  return [
    el("p", "nota", `A linha de base é o ${s.projeto}.`),
    painel,
    resultado,
    meta,
    faixa,
    tela,
    el("p", "nota", s.nota),
  ];
}
