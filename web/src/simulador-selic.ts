// O simulador da Selic: e se a taxa ficar diferente do que o Focus espera, durante um ano?
// Todo coeficiente vem do builder e é número publicado pelo Banco Central para 1 pp de Selic
// (`relatorios.py`); aqui só se multiplica pela mudança escolhida e se põe ao lado do Focus.
// A mesma conta está em `builder/src/sacibras/modelos/selic.py` (`efeito`), com teste.
//
// Nenhum número aparece sem a faixa (Caio, 14/11/2026: "claramente coloque as faixas de erro,
// principalmente no simulador"): cada efeito vem com a faixa de 90 % do BC, e cada nível vem
// numa régua ao lado do Focus com o quanto o próprio Focus costuma errar.

import { dinheiro, numero, sinal } from "./formato";
import { montarGrafico } from "./grafico";
import { el } from "./pecas";
import type { CenarioSelic, Grafico, SimuladorSelic } from "./tipos";

type Faixa = [number, number];

export interface EfeitoDaSelic {
  ipca: number;
  ipcaOutroModelo: number;
  ipcaFaixa: Faixa;
  dolar: number;
  dolarFaixa: Faixa;
  dividaPelosJuros: number;
  dividaPeloDolar: number;
  dividaPelaInflacao: number;
  divida: number;
  dividaFaixa: Faixa;
}

const emOrdem = (a: number, b: number): Faixa => (a <= b ? [a, b] : [b, a]);

/** O que muda um ano depois, com a Selic `pp` diferente durante quatro trimestres. */
export function efeito(s: SimuladorSelic, pp: number): EfeitoDaSelic {
  // O ano fecha no quarto trimestre: o IPCA de quatro trimestres é o do ano.
  const ipca = (s.ipca_agregado[4] ?? 0) * pp;
  const ipcaFaixa = emOrdem((s.ipca_faixa_menor[4] ?? 0) * pp, (s.ipca_faixa_maior[4] ?? 0) * pp);
  const dolar = s.dolar_por_pp * pp;
  const dolarFaixa = emOrdem(s.dolar_por_pp_faixa[0] * pp, s.dolar_por_pp_faixa[1] * pp);
  const dividaPelosJuros = s.divida_por_pp_de_selic * pp;
  const dividaPeloDolar = s.divida_por_1_de_dolar * dolar;
  const dividaPelaInflacao = s.divida_por_pp_de_precos * ipca;
  // Os juros são conta de estoque, sem faixa; somam-se as pontas do dólar e da inflação.
  const resto = (i: 0 | 1): number =>
    s.divida_por_1_de_dolar * dolarFaixa[i] + s.divida_por_pp_de_precos * ipcaFaixa[i];
  return {
    ipca,
    ipcaOutroModelo: (s.ipca_desagregado[4] ?? 0) * pp,
    ipcaFaixa,
    dolar,
    dolarFaixa,
    dividaPelosJuros,
    dividaPeloDolar,
    dividaPelaInflacao,
    divida: dividaPelosJuros + dividaPeloDolar + dividaPelaInflacao,
    dividaFaixa: [dividaPelosJuros + resto(0), dividaPelosJuros + resto(1)],
  };
}

/** "dentro do intervalo da meta (1,5 % a 4,5 %)", "acima do teto da meta (4,5 %)"… */
function contraAMeta(valor: number, meta: NonNullable<SimuladorSelic["meta"]>): string {
  if (valor > meta.superior) return `acima do teto da meta (${numero(meta.superior, 1)} %)`;
  if (valor < meta.inferior) return `abaixo do piso da meta (${numero(meta.inferior, 1)} %)`;
  return `dentro do intervalo da meta (${numero(meta.inferior, 1)} % a ${numero(meta.superior, 1)} %)`;
}

interface Quadro {
  no: HTMLElement;
  valor: HTMLElement;
  faixa: HTMLElement;
  regua: HTMLElement;
  detalhe: HTMLElement;
}

function quadro(rotulo: string): Quadro {
  const no = el("div", "cartao efeito");
  const valor = el("span", "cartao-valor");
  const faixa = el("span", "efeito-faixa");
  const regua = el("div", "regua-efeito");
  const detalhe = el("span", "cartao-detalhe");
  no.append(el("span", "cartao-rotulo", rotulo), valor, faixa, regua, detalhe);
  return { no, valor, faixa, regua, detalhe };
}

function comPequeno(alvo: HTMLElement, texto: string, unidade: string): void {
  alvo.replaceChildren(document.createTextNode(texto), el("small", "", unidade));
}

interface LinhaDaRegua {
  texto: string;
  ponto: number;
  faixa: Faixa | null;
  classe: string;
}

/**
 * Duas linhas na mesma escala: o Focus com o erro típico dele, e o número com a mudança e a
 * faixa do BC. Traço em tinta neutra com as pontas marcadas, como as barras de erro dos
 * gráficos; o ponto é o valor do meio.
 */
function pintarRegua(alvo: HTMLElement, linhas: LinhaDaRegua[]): void {
  const todos = linhas.flatMap((l) => [l.ponto, ...(l.faixa ?? [])]);
  let min = Math.min(...todos);
  let max = Math.max(...todos);
  const folga = (max - min || Math.abs(max) || 1) * 0.06;
  min -= folga;
  max += folga;
  const em = (v: number): string => `${(((v - min) / (max - min)) * 100).toFixed(2)}%`;
  alvo.replaceChildren(
    ...linhas.map((l) => {
      const linha = el("div", `regua-linha ${l.classe}`);
      const trilho = el("div", "regua-trilho");
      if (l.faixa) {
        const traco = el("i", "regua-traco");
        traco.style.left = em(l.faixa[0]);
        traco.style.width = `calc(${em(l.faixa[1])} - ${em(l.faixa[0])})`;
        trilho.append(traco);
      }
      const ponto = el("i", "regua-ponto");
      ponto.style.left = em(l.ponto);
      trilho.append(ponto);
      linha.append(el("span", "regua-texto", l.texto), trilho);
      return linha;
    }),
  );
}

export function montarSimuladorSelic(s: SimuladorSelic): HTMLElement[] {
  let pp = -1;
  let cenario: CenarioSelic | null = null;
  const limite = Math.max(3, ...s.cenarios.map((c) => Math.ceil(Math.abs(c.pp))));

  const painel = el("div", "simulador");
  const linha = el("label", "controle");
  const texto = el("span", "controle-rotulo", `Selic em ${s.ano}`);
  texto.append(el("small", "", "contra o que o Focus espera, o ano inteiro"));
  const entrada = el("input");
  entrada.type = "range";
  entrada.id = "sim-selic";
  entrada.min = String(-limite);
  entrada.max = String(limite);
  entrada.step = "0.25";
  entrada.value = String(pp);
  const saida = el("output", "controle-valor");
  saida.htmlFor.add(entrada.id);
  linha.append(texto, entrada, saida);

  const atalhos = el("div", "cenarios");
  const zerar = el("button", "botao", "Voltar ao Focus");
  zerar.type = "button";
  atalhos.append(zerar);
  const sobreOCenario = el("div", "nota cenario");
  sobreOCenario.hidden = true;
  for (const c of s.cenarios) {
    const botao = el("button", "botao", c.rotulo);
    botao.type = "button";
    botao.addEventListener("click", () => {
      pp = c.pp;
      cenario = c;
      entrada.value = String(pp);
      pintar();
    });
    atalhos.append(botao);
  }
  painel.append(linha, atalhos, sobreOCenario);

  const frase = el("p", "posicao");
  const quadros = el("div", "efeitos");
  const inflacao = quadro(`IPCA de ${s.ano}`);
  const dolar = quadro(`Dólar no fim de ${s.ano}`);
  const divida = quadro(`Dívida bruta no fim de ${s.ano}`);
  quadros.append(inflacao.no, dolar.no, divida.no);
  const tela = el("div");

  /** "Maior que o efeito" ou "menor": o erro do Focus contra o tamanho do que se simula. */
  function contraOErro(efeitoAbs: number, erro: number | null, unidade: string, casas: number): string {
    if (erro === null) return "";
    const base = `O Focus desta época costuma errar ${numero(erro, casas)} ${unidade}`;
    if (pp === 0) return `${base}.`;
    return efeitoAbs < erro
      ? `${base}: mais do que este efeito.`
      : `${base}: menos do que este efeito.`;
  }

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
          : `${tamanho} do Focus, na média de ${s.ano} (o Focus espera ${numero(s.focus_selic, 2)} % no fim do ano)`;
    frase.replaceChildren(
      document.createTextNode(
        pp === 0
          ? `Com a Selic no caminho que o Focus espera para ${s.ano}, nada muda. Mexa no controle: `
          : `Com a Selic ${tamanho} do que o Focus espera durante ${s.ano}`,
      ),
      pp === 0
        ? el("b", "", "para a esquerda é corte, para a direita é alta.")
        : el("b", "", ", pela conta do Banco Central, um ano depois (estimativa e faixa de 90 %):"),
    );

    if (cenario && cenario.pp === pp) {
      const fonte = el("a", "", `Ler o texto: ${cenario.fonte}`);
      fonte.href = cenario.endereco;
      fonte.target = "_blank";
      fonte.rel = "noopener noreferrer";
      sobreOCenario.replaceChildren(document.createTextNode(`${cenario.texto}\n\n`), fonte);
      sobreOCenario.hidden = false;
    } else {
      cenario = null;
      sobreOCenario.hidden = true;
    }

    // ------------------------------------------------------------ inflação
    comPequeno(inflacao.valor, sinal(e.ipca, 2), "pp");
    inflacao.faixa.textContent =
      pp === 0
        ? ""
        : `faixa de 90 % do BC: de ${sinal(e.ipcaFaixa[0], 2)} a ${sinal(e.ipcaFaixa[1], 2)} pp`;
    if (s.focus_ipca === null) {
      inflacao.regua.replaceChildren();
      inflacao.detalhe.textContent = "em relação ao que seria.";
    } else {
      const f = s.focus_ipca;
      const erro = s.erro_focus_ipca;
      pintarRegua(inflacao.regua, [
        {
          texto: `Focus: ${numero(f, 2)} %${erro === null ? "" : ` (costuma errar ${numero(erro, 2)} pp)`}`,
          ponto: f,
          faixa: erro === null ? null : [f - erro, f + erro],
          classe: "focus",
        },
        {
          texto:
            pp === 0
              ? "Com a mudança: o mesmo"
              : `Com a mudança: ${numero(f + e.ipca, 2)} % (de ${numero(f + e.ipcaFaixa[0], 2)} a ${numero(f + e.ipcaFaixa[1], 2)})`,
          ponto: f + e.ipca,
          faixa: pp === 0 ? null : [f + e.ipcaFaixa[0], f + e.ipcaFaixa[1]],
          classe: "simulado",
        },
      ]);
      const meta = s.meta ? `A estimativa fica ${contraAMeta(f + e.ipca, s.meta)}. ` : "";
      inflacao.detalhe.textContent = `${meta}${contraOErro(Math.abs(e.ipca), erro, "pp", 2)}`;
    }

    // ------------------------------------------------------------ dólar
    comPequeno(dolar.valor, sinal(e.dolar, 1), "%");
    dolar.faixa.textContent =
      pp === 0
        ? ""
        : `faixa de 90 % do BC: de ${sinal(e.dolarFaixa[0], 1)} a ${sinal(e.dolarFaixa[1], 1)} %`;
    if (s.focus_dolar === null) {
      dolar.regua.replaceChildren();
      dolar.detalhe.textContent = "em relação ao que seria.";
    } else {
      const f = s.focus_dolar;
      const erro = s.erro_focus_dolar;
      const com = (pct: number): number => f * (1 + pct / 100);
      pintarRegua(dolar.regua, [
        {
          texto: `Focus: R$ ${numero(f, 2)}${erro === null ? "" : ` (costuma errar ${numero(erro, 0)} %)`}`,
          ponto: f,
          faixa: erro === null ? null : [com(-erro), com(erro)],
          classe: "focus",
        },
        {
          texto:
            pp === 0
              ? "Com a mudança: o mesmo"
              : `Com a mudança: R$ ${numero(com(e.dolar), 2)} (de ${numero(com(e.dolarFaixa[0]), 2)} a ${numero(com(e.dolarFaixa[1]), 2)})`,
          ponto: com(e.dolar),
          faixa: pp === 0 ? null : [com(e.dolarFaixa[0]), com(e.dolarFaixa[1])],
          classe: "simulado",
        },
      ]);
      dolar.detalhe.textContent = contraOErro(Math.abs(e.dolar), erro, "%", 0);
    }

    // ------------------------------------------------------------ dívida
    comPequeno(divida.valor, sinal(e.divida, 2), "pp do PIB");
    divida.faixa.textContent =
      pp === 0
        ? ""
        : `faixa: de ${sinal(e.dividaFaixa[0], 2)} a ${sinal(e.dividaFaixa[1], 2)} pp do PIB`;
    const reais =
      s.pib_em_reais === null || pp === 0
        ? ""
        : `Cerca de ${dinheiro(Math.abs((e.divida / 100) * s.pib_em_reais * 1e9))} a ${e.divida < 0 ? "menos" : "mais"}: `;
    const partes =
      pp === 0
        ? ""
        : `${reais}pelos juros, ${sinal(e.dividaPelosJuros, 2)}; pelo dólar, ${sinal(e.dividaPeloDolar, 2)}; pela inflação, ${sinal(e.dividaPelaInflacao, 2)}. `;
    if (s.focus_divida === null) {
      divida.regua.replaceChildren();
      divida.detalhe.textContent = partes || "em relação ao que seria.";
    } else {
      const f = s.focus_divida;
      const erro = s.erro_focus_divida;
      pintarRegua(divida.regua, [
        {
          texto: `Focus: ${numero(f, 1)} % do PIB${erro === null ? "" : ` (costuma errar ${numero(erro, 1)} pp)`}`,
          ponto: f,
          faixa: erro === null ? null : [f - erro, f + erro],
          classe: "focus",
        },
        {
          texto:
            pp === 0
              ? "Com a mudança: o mesmo"
              : `Com a mudança: ${numero(f + e.divida, 1)} % (de ${numero(f + e.dividaFaixa[0], 1)} a ${numero(f + e.dividaFaixa[1], 1)})`,
          ponto: f + e.divida,
          faixa: pp === 0 ? null : [f + e.dividaFaixa[0], f + e.dividaFaixa[1]],
          classe: "simulado",
        },
      ]);
      divida.detalhe.textContent = `${partes}${contraOErro(Math.abs(e.divida), erro, "pp", 1)}`;
    }

    cancelAnimationFrame(pendente);
    pendente = requestAnimationFrame(() => {
      // "+ 0" tira o zero negativo, que sairia escrito "−0,00".
      const vezes = (v: number | undefined): number => Math.round((v ?? 0) * pp * 100) / 100 + 0;
      const caminho = (porPonto: number[]): [string, number | null][] =>
        s.trimestres.map((t, i): [string, number | null] => [t, vezes(porPonto[i])]);
      const faixa: [string, number, number][] =
        pp === 0
          ? []
          : s.trimestres.slice(1).map((t, i): [string, number, number] => {
              const [a, b] = emOrdem(vezes(s.ipca_faixa_menor[i + 1]), vezes(s.ipca_faixa_maior[i + 1]));
              return [t, a, b];
            });
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
        intervalos: faixa.length
          ? [{ nome: `IPCA: ${s.faixa_do_ipca}`, serie: "ipca-agregado", pontos: faixa, meio: [], nome_meio: "" }]
          : [],
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
