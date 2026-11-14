// O simulador da Selic: e se a taxa ficar diferente do que o Focus espera, durante um ano?
// Todo coeficiente vem do builder e é número publicado pelo Banco Central para 1 pp de Selic
// (`relatorios.py`); aqui só se multiplica pela mudança escolhida e se põe ao lado do Focus.
// A mesma conta está em `builder/src/sacibras/modelos/selic.py` (`efeito`), com teste.

import { dinheiro, numero, sinal } from "./formato";
import { montarGrafico } from "./grafico";
import { el } from "./pecas";
import type { Grafico, SimuladorSelic } from "./tipos";

export interface EfeitoDaSelic {
  ipca: number;
  ipcaOutroModelo: number;
  dolar: number;
  dolarFaixa: [number, number];
  dividaPelosJuros: number;
  dividaPeloDolar: number;
  dividaPelaInflacao: number;
  divida: number;
}

/** O que muda um ano depois, com a Selic `pp` diferente durante quatro trimestres. */
export function efeito(s: SimuladorSelic, pp: number): EfeitoDaSelic {
  // O ano fecha no quarto trimestre: o IPCA de quatro trimestres é o do ano.
  const ipca = (s.ipca_agregado[4] ?? 0) * pp;
  const dolar = s.dolar_por_pp * pp;
  const pontas = s.dolar_por_pp_faixa.map((k) => k * pp).sort((a, b) => a - b);
  const dividaPelosJuros = s.divida_por_pp_de_selic * pp;
  const dividaPeloDolar = s.divida_por_1_de_dolar * dolar;
  const dividaPelaInflacao = s.divida_por_pp_de_precos * ipca;
  return {
    ipca,
    ipcaOutroModelo: (s.ipca_desagregado[4] ?? 0) * pp,
    dolar,
    dolarFaixa: [pontas[0] ?? 0, pontas[1] ?? 0],
    dividaPelosJuros,
    dividaPeloDolar,
    dividaPelaInflacao,
    divida: dividaPelosJuros + dividaPeloDolar + dividaPelaInflacao,
  };
}

/** "dentro do intervalo da meta (1,5 % a 4,5 %)", "acima do teto da meta (4,5 %)"… */
function contraAMeta(valor: number, meta: NonNullable<SimuladorSelic["meta"]>): string {
  if (valor > meta.superior) return `acima do teto da meta (${numero(meta.superior, 1)} %)`;
  if (valor < meta.inferior) return `abaixo do piso da meta (${numero(meta.inferior, 1)} %)`;
  return `dentro do intervalo da meta (${numero(meta.inferior, 1)} % a ${numero(meta.superior, 1)} %)`;
}

function quadro(rotulo: string): { no: HTMLElement; valor: HTMLElement; detalhe: HTMLElement } {
  const no = el("div", "cartao efeito");
  const valor = el("span", "cartao-valor");
  const detalhe = el("span", "cartao-detalhe");
  no.append(el("span", "cartao-rotulo", rotulo), valor, detalhe);
  return { no, valor, detalhe };
}

function comPequeno(alvo: HTMLElement, texto: string, unidade: string): void {
  alvo.replaceChildren(document.createTextNode(texto), el("small", "", unidade));
}

export function montarSimuladorSelic(s: SimuladorSelic): HTMLElement[] {
  let pp = -1;
  const painel = el("div", "simulador");
  const linha = el("label", "controle");
  const texto = el("span", "controle-rotulo", `Selic em ${s.ano}`);
  texto.append(el("small", "", "contra o que o Focus espera, o ano inteiro"));
  const entrada = el("input");
  entrada.type = "range";
  entrada.id = "sim-selic";
  entrada.min = "-3";
  entrada.max = "3";
  entrada.step = "0.25";
  entrada.value = String(pp);
  const saida = el("output", "controle-valor");
  saida.htmlFor.add(entrada.id);
  linha.append(texto, entrada, saida);
  const zerar = el("button", "botao", "Voltar ao Focus");
  zerar.type = "button";
  painel.append(linha, zerar);

  const frase = el("p", "posicao");
  const quadros = el("div", "efeitos");
  const inflacao = quadro(`IPCA de ${s.ano}`);
  const dolar = quadro(`Dólar no fim de ${s.ano}`);
  const divida = quadro(`Dívida bruta no fim de ${s.ano}`);
  quadros.append(inflacao.no, dolar.no, divida.no);
  const tela = el("div");

  let pendente = 0;
  function pintar(): void {
    const e = efeito(s, pp);
    const lado = pp < 0 ? "abaixo" : "acima";
    const tamanho = `${numero(Math.abs(pp), 2)} pp ${lado}`;
    saida.textContent =
      pp === 0
        ? "igual ao Focus"
        : s.focus_selic === null
          ? `${tamanho} do Focus`
          : `${tamanho} do Focus (${numero(s.focus_selic + pp, 2)} % no fim de ${s.ano})`;
    frase.replaceChildren(
      document.createTextNode(
        pp === 0
          ? `Com a Selic no caminho que o Focus espera para ${s.ano}, nada muda. Mexa no controle: `
          : `Com a Selic ${tamanho} do que o Focus espera durante ${s.ano}`,
      ),
      pp === 0
        ? el("b", "", "para a esquerda é corte, para a direita é alta.")
        : el("b", "", ", pela conta do Banco Central, um ano depois:"),
    );

    // Inflação
    comPequeno(inflacao.valor, sinal(e.ipca, 2), "pp");
    const outro = pp === 0 ? "" : ` No outro modelo do BC, ${sinal(e.ipcaOutroModelo, 2)} pp.`;
    if (s.focus_ipca === null) {
      inflacao.detalhe.textContent = `em relação ao que seria.${outro}`;
    } else {
      const nivel = s.focus_ipca + e.ipca;
      const meta = s.meta ? `, ${contraAMeta(nivel, s.meta)}` : "";
      inflacao.detalhe.textContent =
        pp === 0
          ? `O Focus espera ${numero(s.focus_ipca, 2)} %${meta}.`
          : `Perto de ${numero(nivel, 2)} %${meta}. O Focus espera ${numero(s.focus_ipca, 2)} %.${outro}`;
    }

    // Dólar
    comPequeno(dolar.valor, sinal(e.dolar, 1), "%");
    const faixa =
      pp === 0
        ? ""
        : ` A faixa do BC vai de ${sinal(e.dolarFaixa[0], 1)} % a ${sinal(e.dolarFaixa[1], 1)} %.`;
    if (s.focus_dolar === null) {
      dolar.detalhe.textContent = `em relação ao que seria.${faixa}`;
    } else {
      const nivel = s.focus_dolar * (1 + e.dolar / 100);
      dolar.detalhe.textContent =
        pp === 0
          ? `O Focus espera R$ ${numero(s.focus_dolar, 2)}.`
          : `Perto de R$ ${numero(nivel, 2)}. O Focus espera R$ ${numero(s.focus_dolar, 2)}.${faixa}`;
    }

    // Dívida
    comPequeno(divida.valor, sinal(e.divida, 2), "pp do PIB");
    const reais =
      s.pib_em_reais === null || pp === 0
        ? ""
        : ` (cerca de ${dinheiro(Math.abs((e.divida / 100) * s.pib_em_reais * 1e9))} a ${e.divida < 0 ? "menos" : "mais"})`;
    const partes =
      pp === 0
        ? ""
        : ` Pelos juros, ${sinal(e.dividaPelosJuros, 2)}; pelo dólar, ${sinal(e.dividaPeloDolar, 2)}; pela inflação, ${sinal(e.dividaPelaInflacao, 2)}.`;
    if (s.focus_divida === null) {
      divida.detalhe.textContent = `em relação ao que seria${reais}.${partes}`;
    } else {
      divida.detalhe.textContent =
        pp === 0
          ? `O Focus espera ${numero(s.focus_divida, 1)} % do PIB.`
          : `Perto de ${numero(s.focus_divida + e.divida, 1)} % do PIB${reais}. O Focus espera ${numero(s.focus_divida, 1)} %.${partes}`;
    }

    cancelAnimationFrame(pendente);
    pendente = requestAnimationFrame(() => {
      const caminho = (porPonto: number[]): [string, number | null][] =>
        s.trimestres.map((t, i): [string, number | null] => [
          t,
          // "+ 0" tira o zero negativo, que sairia escrito "−0,00".
          Math.round((porPonto[i] ?? 0) * pp * 100) / 100 + 0,
        ]);
      const g: Grafico = {
        id: "simulador-selic",
        titulo: "A Selic simulada e o que muda no IPCA, trimestre a trimestre",
        subtitulo: "Diferença em relação ao que seria sem a mudança; IPCA acumulado em 12 meses",
        tipo: "linha",
        unidade: "pp",
        casas: 2,
        periodicidade: "T",
        series: [
          { id: "selic", nome: "Selic (a mudança simulada)", papel: "realizado", tracejado_desde: null, pontos: caminho(s.selic_caminho) },
          { id: "ipca-agregado", nome: "IPCA, modelo agregado do BC", papel: "previsao", tracejado_desde: null, pontos: caminho(s.ipca_agregado) },
          { id: "ipca-desagregado", nome: "IPCA, modelo desagregado do BC", papel: "previsao", tracejado_desde: null, pontos: caminho(s.ipca_desagregado) },
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

  entrada.addEventListener("input", () => {
    pp = Number(entrada.value);
    pintar();
  });
  zerar.addEventListener("click", () => {
    pp = 0;
    entrada.value = "0";
    pintar();
  });
  pintar();
  return [painel, frase, quadros, tela, el("p", "nota", `${s.como_ler}\n\n${s.nota}`)];
}
