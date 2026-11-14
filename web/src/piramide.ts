// A pirâmide etária, em Demografia: homens à esquerda, mulheres à direita, cada grupo de
// cinco anos em % da população do ano. O ano se escolhe na lista suspensa; o primeiro ano
// da série fica desenhado em contorno, para ver o envelhecimento. A escala é a mesma em
// todos os anos, então a forma muda e a régua não.

import { numero } from "./formato";
import { tema } from "./grafico";
import { el } from "./pecas";
import { listaSuspensa } from "./pontos";
import type { Grafico, Piramide } from "./tipos";

type Lado = "homens" | "mulheres";

/** Fatias em % da população de cada ano: [ano][grupo]. */
function fatias(p: Piramide): Record<Lado, number[][]> {
  const totais = p.anos.map(
    (_, i) =>
      (p.homens[i] ?? []).reduce((a, b) => a + b, 0) + (p.mulheres[i] ?? []).reduce((a, b) => a + b, 0),
  );
  const emPct = (m: number[][]): number[][] =>
    m.map((linha, i) => linha.map((v) => (v / (totais[i] || 1)) * 100));
  return { homens: emPct(p.homens), mulheres: emPct(p.mulheres) };
}

/** O primeiro número do rótulo do grupo: "65 a 69" → 65. */
function idadeInicial(grupo: string): number {
  return Number.parseInt(grupo, 10);
}

function pessoas(mil: number): string {
  return mil >= 1000 ? `${numero(mil / 1000, 2)} milhões` : `${numero(mil, 0)} mil`;
}

export function montarPiramide(g: Grafico, p: Piramide): HTMLElement {
  const artigo = el("article", "grafico inteira piramide");
  artigo.id = `g-${g.id}`;
  const pct = fatias(p);
  const maximo = Math.max(...pct.homens.flat(), ...pct.mulheres.flat());
  const cores = tema().series;
  artigo.style.setProperty("--cor-homens", cores[1] ?? "currentColor");
  artigo.style.setProperty("--cor-mulheres", cores[2] ?? "currentColor");

  const cabeca = el("header", "grafico-cabeca");
  const titulos = el("div");
  const sub = el("p", "sub");
  titulos.append(el("h3", "", g.titulo), sub);
  cabeca.append(titulos);

  const rotuloDoAno = (a: number): string =>
    a >= p.primeiro_ano_projetado ? `${a} · projeção` : String(a);
  let indice = Math.max(0, p.anos.indexOf(p.ano_inicial));
  const contorno = Math.max(0, p.anos.indexOf(p.ano_contorno));
  const barra = el("div", "barra-controles");
  const lista = listaSuspensa(
    `${g.id}-ano`,
    "Ano",
    p.anos.map((a) => ({ valor: String(a), rotulo: rotuloDoAno(a) })),
    String(p.anos[indice]),
    (v) => {
      indice = Math.max(0, p.anos.indexOf(Number(v)));
      pintar();
    },
  );
  barra.append(lista.caixa);

  const legenda = el("div", "legenda");
  for (const [classe, nome] of [
    ["homens", "Homens"],
    ["mulheres", "Mulheres"],
  ] as const) {
    const item = el("span", "legenda-item");
    item.append(el("i", `chave chave-${classe}`), document.createTextNode(nome));
    legenda.append(item);
  }
  const itemContorno = el("span", "legenda-item");
  itemContorno.append(el("i", "chave chave-contorno"), document.createTextNode(String(p.ano_contorno)));
  legenda.append(itemContorno);

  const corpo = el("div", "piramide-corpo");
  corpo.setAttribute("role", "img");
  const dica = el("p", "piramide-dica");
  dica.setAttribute("aria-live", "polite");
  const frase = el("p", "posicao");

  const pe = el("footer", "grafico-pe");
  pe.append(el("span", "fonte", `Fonte: ${g.fonte}`));
  artigo.append(cabeca, barra, legenda, corpo, dica, frase, pe);
  if (g.nota) artigo.append(el("p", "nota", g.nota));

  // Os grupos de cima para baixo: o mais velho no alto.
  const ordem = p.grupos.map((_, k) => k).reverse();
  let escolhido: number | null = null;

  function lado(classe: Lado, k: number): HTMLElement {
    const celula = el("div", `piramide-lado ${classe}`);
    const barraDoAno = el("i", "piramide-barra");
    const contornoDoAno = el("i", "piramide-contorno");
    celula.append(barraDoAno, contornoDoAno);
    celula.dataset.grupo = String(k);
    return celula;
  }

  const linhas = ordem.map((k) => {
    const linha = el("div", "piramide-linha");
    linha.tabIndex = 0;
    const h = lado("homens", k);
    const m = lado("mulheres", k);
    linha.append(h, el("span", "piramide-grupo", p.grupos[k] ?? ""), m);
    const escolher = (): void => {
      escolhido = k;
      escrever();
      linhas.forEach((x) => x.linha.classList.toggle("ativa", x.k === k));
    };
    linha.addEventListener("pointerenter", escolher);
    linha.addEventListener("pointerdown", escolher);
    linha.addEventListener("focus", escolher);
    corpo.append(linha);
    return { k, linha, h, m };
  });

  // Régua embaixo: as marcas de % nos dois lados.
  const regua = el("div", "piramide-linha piramide-regua");
  regua.setAttribute("aria-hidden", "true");
  const passo = maximo > 6 ? 2 : 1;
  const marcas = (classe: Lado): HTMLElement => {
    const celula = el("div", `piramide-lado ${classe}`);
    for (let v = passo; v <= maximo; v += passo) {
      // No celular só as marcas pares cabem: as ímpares somem pelo CSS.
      const impar = Math.round(v / passo) % 2 === 1;
      const marca = el("span", `piramide-marca${impar ? " impar" : ""}`, `${numero(v, 0)} %`);
      marca.style.setProperty("--pos", `${(v / maximo) * 100}%`);
      celula.append(marca);
    }
    return celula;
  };
  regua.append(marcas("homens"), el("span", "piramide-grupo", "idade"), marcas("mulheres"));
  corpo.append(regua);

  function largura(v: number): string {
    return `${(v / maximo) * 100}%`;
  }

  function escrever(): void {
    const ano = p.anos[indice] ?? 0;
    const k = escolhido;
    if (k === null) {
      dica.textContent = "Toque ou passe o mouse numa faixa de idade para ver os números.";
      return;
    }
    const h = pct.homens[indice]?.[k] ?? 0;
    const m = pct.mulheres[indice]?.[k] ?? 0;
    const hMil = p.homens[indice]?.[k] ?? 0;
    const mMil = p.mulheres[indice]?.[k] ?? 0;
    const antes =
      contorno !== indice
        ? ` Em ${p.ano_contorno}: ${numero((pct.homens[contorno]?.[k] ?? 0) + (pct.mulheres[contorno]?.[k] ?? 0), 1)} %.`
        : "";
    dica.textContent =
      `${p.grupos[k]} anos, em ${ano}: homens ${numero(h, 1)} % (${pessoas(hMil)}), ` +
      `mulheres ${numero(m, 1)} % (${pessoas(mMil)}); juntos, ${numero(h + m, 1)} % da população.` +
      antes;
  }

  function pintar(): void {
    const ano = p.anos[indice] ?? 0;
    sub.textContent = `% da população · ${rotuloDoAno(ano)}`;
    for (const { k, h, m } of linhas) {
      for (const [celula, classe] of [
        [h, "homens"],
        [m, "mulheres"],
      ] as const) {
        const [barraDoAno, contornoDoAno] = [...celula.children] as HTMLElement[];
        if (barraDoAno) barraDoAno.style.width = largura(pct[classe][indice]?.[k] ?? 0);
        if (contornoDoAno) {
          contornoDoAno.style.width = largura(pct[classe][contorno]?.[k] ?? 0);
          contornoDoAno.hidden = contorno === indice;
        }
      }
    }
    itemContorno.hidden = contorno === indice;
    const soma = (ate: (idade: number) => boolean, i: number): number =>
      p.grupos.reduce(
        (a, grupo, k) =>
          ate(idadeInicial(grupo)) ? a + (pct.homens[i]?.[k] ?? 0) + (pct.mulheres[i]?.[k] ?? 0) : a,
        0,
      );
    const jovens = soma((x) => x < 15, indice);
    const idosos = soma((x) => x >= 65, indice);
    frase.textContent =
      `Em ${ano}, ${numero(jovens, 1)} % têm menos de 15 anos e ${numero(idosos, 1)} % têm 65 ou mais` +
      (contorno !== indice
        ? ` (em ${p.ano_contorno}: ${numero(soma((x) => x < 15, contorno), 1)} % e ${numero(soma((x) => x >= 65, contorno), 1)} %).`
        : ".");
    corpo.setAttribute("aria-label", `${g.titulo}, ${ano}. ${frase.textContent}`);
    escrever();
  }

  pintar();
  return artigo;
}
