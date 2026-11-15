// O salário mínimo contra a inflação no período que a pessoa escolhe (Caio, 15/11/2026: "um
// parâmetro na tabela [...] para colocar outros períodos" e, no gráfico, "o salário mínimo
// inicial ajustado pela inflação, e aí daria pra comparar a diferença no próprio gráfico").
// Só dado oficial (SGS 1619 e o IPCA); aqui se divide e se multiplica. A mesma conta está em
// `builder/src/sacibras/secoes/trabalho.py` (`comparar`), com teste.

import { numero } from "./formato";
import { montarGrafico } from "./grafico";
import { colar, el } from "./pecas";
import { listaSuspensa } from "./pontos";
import type { ComparadorSalario, Grafico } from "./tipos";

const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

type Mes = [string, number, number];

/** "2016-10-01" → "out/2016". */
function nomeDoMes(iso: string): string {
  return `${MESES[Number(iso.slice(5, 7)) - 1]}/${iso.slice(0, 4)}`;
}

/** A alta do mínimo, o IPCA e o ganho acima da inflação entre dois meses, em %. */
export function comparar(de: Mes, ate: Mes): { alta: number; ipca: number; acima: number } {
  const alta = ate[1] / de[1] - 1;
  const ipca = ate[2] / de[2] - 1;
  return { alta: alta * 100, ipca: ipca * 100, acima: ((1 + alta) / (1 + ipca) - 1) * 100 };
}

/** O mês da série mais perto de ano/mês (a lista de meses pode pedir um que não há). */
function mesMaisPerto(meses: Mes[], ano: number, mes: number): number {
  const alvo = `${ano}-${String(mes).padStart(2, "0")}-01`;
  const i = meses.findIndex((m) => m[0] >= alvo);
  return i < 0 ? meses.length - 1 : i;
}

export function montarComparadorSalario(s: ComparadorSalario): HTMLElement[] {
  const meses = s.meses as Mes[];
  const ultimo = meses.length - 1;
  if (ultimo < 1) return [el("p", "aviso", "A série do salário mínimo não veio nesta rodada.")];
  const fim = meses[ultimo] as Mes;
  // Começa em 10 anos, o prazo do meio da tabela.
  let de = mesMaisPerto(meses, Number(fim[0].slice(0, 4)) - 10, Number(fim[0].slice(5, 7)));
  let ate = ultimo;

  const anos = [...new Set(meses.map((m) => m[0].slice(0, 4)))];
  const opcoesAno = anos.map((a) => ({ valor: a, rotulo: a }));
  const opcoesMes = MESES.map((m, i) => ({ valor: String(i + 1), rotulo: m }));
  const anoDe = (i: number): string => (meses[i] as Mes)[0].slice(0, 4);
  const mesDe = (i: number): string => String(Number((meses[i] as Mes)[0].slice(5, 7)));

  const painel = el("div", "simulador");
  const campos = el("div", "barra-controles comparador-controles");
  const resumo = el("p", "comparador-resumo");
  const tabela = el("div", "tabela-rolavel");
  const tela = el("div", "simulador-grafico");

  // De e até: mês e ano em listas suspensas. Se o "de" passar do "até", os dois se ajeitam.
  const escolher = (qual: "de" | "ate", ano: string, mes: string): void => {
    const i = mesMaisPerto(meses, Number(ano), Number(mes));
    if (qual === "de") de = Math.min(i, ultimo - 1);
    else ate = Math.max(i, 1);
    if (de >= ate) {
      if (qual === "de") ate = Math.min(de + 1, ultimo);
      else de = Math.max(ate - 1, 0);
    }
    pintar();
  };
  const listas = {
    deMes: listaSuspensa("sm-de-mes", "De (mês)", opcoesMes, mesDe(de), (v) =>
      escolher("de", anoDe(de), v),
    ),
    deAno: listaSuspensa("sm-de-ano", "De (ano)", opcoesAno, anoDe(de), (v) =>
      escolher("de", v, mesDe(de)),
    ),
    ateMes: listaSuspensa("sm-ate-mes", "Até (mês)", opcoesMes, mesDe(ate), (v) =>
      escolher("ate", anoDe(ate), v),
    ),
    ateAno: listaSuspensa("sm-ate-ano", "Até (ano)", opcoesAno, anoDe(ate), (v) =>
      escolher("ate", v, mesDe(ate)),
    ),
  };
  campos.append(listas.deMes.caixa, listas.deAno.caixa, listas.ateMes.caixa, listas.ateAno.caixa);
  painel.append(campos);

  const linha = (rotulo: string, a: Mes, b: Mes, destaque = false): HTMLTableRowElement => {
    const tr = el("tr", destaque ? "brasil" : "");
    const c = comparar(a, b);
    // A linha escolhida diz o período (o mínimo do início está na frase de cima); as fixas,
    // o começo e o mínimo de então, todas até o último mês.
    const nome = destaque
      ? `${rotulo}: ${nomeDoMes(a[0])} a ${nomeDoMes(b[0])}`
      : `${rotulo}: ${nomeDoMes(a[0])}, R$ ${numero(a[1], 0)}`;
    tr.append(el("th", "", nome));
    for (const v of [c.alta, c.ipca, c.acima]) tr.append(el("td", "", numero(v, 1)));
    return tr;
  };

  const pintar = (): void => {
    const a = meses[de] as Mes;
    const b = meses[ate] as Mes;
    listas.deMes.trocar(opcoesMes, mesDe(de));
    listas.deAno.trocar(opcoesAno, anoDe(de));
    listas.ateMes.trocar(opcoesMes, mesDe(ate));
    listas.ateAno.trocar(opcoesAno, anoDe(ate));
    const c = comparar(a, b);
    const corrigido = (a[1] * b[2]) / a[2];
    const lado = c.acima >= 0 ? "a mais" : "a menos";
    resumo.textContent = colar(
      `De ${nomeDoMes(a[0])} a ${nomeDoMes(b[0])}, o mínimo foi de R$ ${numero(a[1], 0)} para ` +
      `R$ ${numero(b[1], 0)}. Só com a inflação, teria ido para R$ ${numero(corrigido, 0)}: ` +
        `o de ${nomeDoMes(b[0])} compra ${numero(Math.abs(c.acima), 1)} % ${lado}.`,
    );

    // A tabela: o período escolhido em cima, os prazos fixos (até o último mês) embaixo.
    const t = el("table", "dados");
    const cab = t.createTHead().insertRow();
    for (const c2 of ["", "Alta do mínimo (%)", "IPCA no período (%)", "Acima da inflação (%)"]) {
      cab.append(el("th", "", c2));
    }
    const corpo = t.createTBody();
    corpo.append(linha("Escolhido", a, b, true));
    for (const n of s.prazos) {
      const i = mesMaisPerto(meses, Number(fim[0].slice(0, 4)) - n, Number(fim[0].slice(5, 7)));
      const inicio = meses[i] as Mes;
      if (i < ultimo && inicio[0].slice(0, 4) === String(Number(fim[0].slice(0, 4)) - n)) {
        corpo.append(linha(`Em ${n} ano${n > 1 ? "s" : ""}`, inicio, fim));
      }
    }
    corpo.append(linha("Desde o início do real", meses[0] as Mes, fim));
    tabela.replaceChildren(t);

    // O gráfico: o mínimo de cada mês e o do início corrigido pelo IPCA; a faixa é a diferença.
    const trecho = meses.slice(de, ate + 1);
    const corrigidos = trecho.map((m): [string, number] => [m[0], Math.round((a[1] * m[2]) / a[2])]);
    const g: Grafico = {
      id: "salario-minimo-comparado",
      titulo: `Salário mínimo e o de ${nomeDoMes(a[0])} corrigido pelo IPCA`,
      subtitulo: "",
      tipo: "linha",
      unidade: "R$ da época",
      casas: 0,
      periodicidade: "M",
      series: [
        { id: "minimo", nome: "Salário mínimo", papel: "realizado", tracejado_desde: null, pontos: trecho.map((m) => [m[0], m[1]]) },
        { id: "corrigido", nome: `O de ${nomeDoMes(a[0])} corrigido pelo IPCA`, papel: "referencia", tracejado_desde: null, pontos: corrigidos },
      ],
      faixa: {
        nome: c.acima >= 0 ? "ganho acima da inflação" : "perda para a inflação",
        pontos: trecho.map((m, i): [string, number, number] => {
          const r = (corrigidos[i] as [string, number])[1];
          return [m[0], Math.min(m[1], r), Math.max(m[1], r)];
        }),
      },
      intervalos: [],
      linhas: [],
      janela_anos: null,
      fonte: s.fonte,
      nota: "",
      largura: "inteira",
    };
    tela.replaceChildren(montarGrafico(g));
  };
  pintar();
  return [painel, resumo, tabela, tela, el("p", "nota", s.nota)];
}
