// "Quanto rendeu R$ 100", em Mercados: a pessoa escolhe desde quando (lista suspensa), vê o
// ranking em pontos (com a inflação como marco: à direita dela, ganhou poder de compra) e o
// gráfico com as linhas partindo de R$ 100 na mesma data. São mais aplicações do que cores na
// paleta: o gráfico mostra a inflação e até cinco delas, e tocar numa linha do ranking a põe
// ou tira do gráfico (como os países em Brasil no mundo). A cor segue a aplicação.

import { data, dinheiro, numero, periodo } from "./formato";
import { montarGrafico, tema } from "./grafico";
import { el } from "./pecas";
import { linhaDoRanking, listaSuspensa, reguaDe, type Opcao } from "./pontos";
import type { Grafico, Serie } from "./tipos";

const DIA = 86_400_000;
/** As que abrem no gráfico, e quantas cabem nele além da inflação. */
const INICIAIS = ["cdi", "ibov", "dolar", "tesouro-ipca", "ouro"];
const MAXIMO = 5;

function iso(d: Date): string {
  return d.toISOString().slice(0, 10);
}

/** A série reescrita com R$ 100 na data `inicio` (o último ponto até ela é a base). */
function rebasear(s: Serie, inicio: string): Serie {
  const validos = s.pontos.filter((p): p is [string, number] => p[1] !== null);
  const antes = validos.filter(([d]) => d <= inicio);
  const base = antes.at(-1) ?? validos[0];
  if (!base) return { ...s, pontos: [] };
  const depois = validos.filter(([d]) => d > inicio);
  return {
    ...s,
    pontos: [
      [inicio, 100],
      ...depois.map(([d, v]): [string, number] => [d, (v / base[1]) * 100]),
    ],
  };
}

export function montarRetornos(g: Grafico): HTMLElement {
  const caixa = el("div", "retornos");
  const ultimo = g.series
    .flatMap((s) => s.pontos.map(([d]) => d))
    .reduce((a, b) => (a > b ? a : b), "");
  const primeiro = g.series
    .map((s) => s.pontos[0]?.[0] ?? ultimo)
    .reduce((a, b) => (a > b ? a : b), "");
  const hoje = data(ultimo);
  const anos = (n: number) => iso(new Date(hoje.getTime() - n * 365.25 * DIA));
  const opcoes: (Opcao & { inicio: string })[] = [
    { valor: "ano", rotulo: `No ano (desde 31/12/${hoje.getUTCFullYear() - 1})`, inicio: `${hoje.getUTCFullYear() - 1}-12-31` },
    { valor: "12m", rotulo: "Em 12 meses", inicio: anos(1) },
    { valor: "3a", rotulo: "Em 3 anos", inicio: anos(3) },
    { valor: "5a", rotulo: "Em 5 anos", inicio: anos(5) },
    { valor: "tudo", rotulo: `Desde ${periodo(primeiro, "M")}`, inicio: primeiro },
  ];
  let escolha = opcoes[1] ?? opcoes[0];

  const painel = el("article", "grafico inteira painel-retornos");
  const cabeca = el("header", "grafico-cabeca");
  const titulos = el("div");
  titulos.append(
    el("h3", "", g.titulo),
    el("p", "sub", "Retorno no período, em %, antes de imposto · toque numa aplicação para pô-la no gráfico ou tirá-la"),
  );
  cabeca.append(titulos);
  const barra = el("div", "barra-controles");
  const lista = listaSuspensa(
    "retornos-desde",
    "Período",
    opcoes,
    escolha?.valor ?? "12m",
    (v) => {
      escolha = opcoes.find((o) => o.valor === v) ?? escolha;
      pintar();
    },
  );
  barra.append(lista.caixa);
  const ranking = el("div", "ranking-pontos");
  const frase = el("p", "posicao");
  const pe = el("footer", "grafico-pe");
  pe.append(el("span", "fonte", `Fonte: ${g.fonte}`));
  painel.append(cabeca, barra, ranking, frase, pe);
  const lugarDoGrafico = el("div", "retornos-grafico");
  caixa.append(painel, lugarDoGrafico);

  const cores = tema().series;
  // aplicação → casa da paleta. A inflação fica com a última casa; as outras, com a primeira
  // livre, e a mantêm enquanto estiverem no gráfico.
  const daInflacao = cores.length - 1;
  const casas = new Map<string, number>();
  const aplicacoesIds = g.series.filter((s) => s.papel === "realizado").map((s) => s.id);
  const iniciais = INICIAIS.filter((id) => aplicacoesIds.includes(id));
  for (const id of aplicacoesIds) if (iniciais.length < MAXIMO && !iniciais.includes(id)) iniciais.push(id);
  iniciais.forEach((id, i) => casas.set(id, i));
  function alternar(id: string): void {
    if (casas.has(id)) {
      if (casas.size > 1) casas.delete(id);
    } else if (casas.size < MAXIMO) {
      const usadas = new Set(casas.values());
      let livre = 0;
      while (usadas.has(livre)) livre += 1;
      casas.set(id, livre);
    }
    pintar();
  }
  function pintar(): void {
    if (!escolha) return;
    const inicio = escolha.inicio;
    const series = g.series.map((s) => ({
      ...rebasear(s, inicio),
      cor: s.papel === "realizado" ? casas.get(s.id) : daInflacao,
    }));
    const finais = series.map((s) => ({ s, valor: (s.pontos.at(-1)?.[1] ?? 100) - 100 }));
    const inflacao = finais.find((f) => f.s.papel !== "realizado");
    const aplicacoes = finais.filter((f) => f !== inflacao).sort((a, b) => b.valor - a.valor);
    const marcos = inflacao ? [{ valor: inflacao.valor, rotulo: "inflação" }] : [];
    const regua = reguaDe(
      finais.map((f) => f.valor),
      marcos,
    );
    ranking.replaceChildren(
      ...[...aplicacoes, ...(inflacao ? [inflacao] : [])].map((f, i) =>
        linhaDoRanking(
          {
            chave: f.s.id,
            nome: f.s.nome,
            valor: f.valor,
            marca: f === inflacao ? "grupo" : "comum",
            posicao: f === inflacao ? null : i + 1,
            cor: f.s.cor === undefined ? undefined : cores[f.s.cor % cores.length],
            dica: `${f.s.nome}: R$ 100 viraram ${dinheiro(100 + f.valor)}`,
          },
          regua,
          1,
          f === inflacao ? undefined : () => alternar(f.s.id),
        ),
      ),
    );
    if (inflacao) {
      const ganharam = aplicacoes.filter((f) => f.valor > inflacao.valor).map((f) => f.s.nome);
      frase.textContent =
        `A inflação foi de ${numero(inflacao.valor, 1)} % no período. ` +
        (ganharam.length
          ? `Ganharam dela: ${ganharam.join(", ")}.`
          : "Nenhuma das aplicações ganhou dela.");
    }
    lugarDoGrafico.replaceChildren(
      montarGrafico({
        ...g,
        titulo: "R$ 100 ao longo do período",
        subtitulo: `a partir de ${periodo(inicio, "D")}`,
        janela_anos: null,
        series: series.filter((s) => s.cor !== undefined),
      }),
    );
  }
  pintar();
  return caixa;
}
