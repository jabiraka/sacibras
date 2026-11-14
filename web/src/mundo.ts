// Brasil no mundo: a mesma métrica para vários países — o ranking do ano escolhido, a
// trajetória (realizado e projeção do FMI) e a tabela com todas as métricas lado a lado.

import { numero } from "./formato";
import { montarGrafico } from "./grafico";
import type { Grafico, MetricaMundo, Mundo, Pais } from "./tipos";

const GRUPOS: [Pais["grupo"], string][] = [
  ["america_latina", "América Latina"],
  ["emergentes", "Outros emergentes"],
  ["avancados", "Avançados"],
  ["agregado", "Agregados"],
];

const INICIAIS = ["BRA", "MEX", "CHL", "USA"];
const MAXIMO = 6;

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  classe = "",
  texto = "",
): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (classe) e.className = classe;
  if (texto) e.textContent = texto;
  return e;
}

function ordinal(n: number): string {
  return `${n}º`;
}

export function montarMundo(m: Mundo): HTMLElement {
  const raiz = el("div");
  const nomes = new Map(m.paises.map((p) => [p.iso3, p]));
  let metrica: MetricaMundo = m.metricas[0] as MetricaMundo;
  let ano = m.ano_corrente;
  // país → casa da paleta. O Brasil é sempre a casa 0 (verde); os outros pegam a casa livre
  // e a mantêm enquanto estiverem marcados.
  const casas = new Map<string, number>();
  INICIAIS.filter((i) => nomes.has(i)).forEach((iso, i) => casas.set(iso, i));

  const valor = (mt: MetricaMundo, iso: string, a: number): number | null => {
    const i = mt.anos.indexOf(a);
    return i < 0 ? null : (mt.valores[iso]?.[i] ?? null);
  };
  const projetado = (mt: MetricaMundo, a: number): boolean =>
    mt.primeiro_ano_projetado !== null && a >= mt.primeiro_ano_projetado;

  // ---------------------------------------------------------------- métricas
  const fichas = el("div", "mundo-controles");
  fichas.setAttribute("role", "group");
  fichas.setAttribute("aria-label", "Métrica comparada");
  const botoesMetrica = m.metricas.map((mt) => {
    const b = el("button", "ficha", mt.nome);
    b.type = "button";
    b.addEventListener("click", () => {
      metrica = mt;
      pintar();
    });
    fichas.append(b);
    return b;
  });
  const sobre = el("p", "secao-resumo");

  // ---------------------------------------------------------------- ranking
  const grade = el("div", "mundo-grade");
  const painelRanking = el("div", "painel-mundo");
  const tituloRanking = el("h3");
  const subRanking = el("p", "sub");
  const anos = el("div", "anos");
  anos.setAttribute("role", "group");
  anos.setAttribute("aria-label", "Ano");
  const ranking = el("div", "ranking");
  const posicao = el("p", "posicao");
  const fonteRanking = el("footer", "grafico-pe");
  painelRanking.append(tituloRanking, subRanking, anos, ranking, posicao, fonteRanking);

  // ---------------------------------------------------------------- trajetória
  const ladoLinha = el("div");
  const escolha = el("div", "mundo-controles");
  escolha.setAttribute("role", "group");
  escolha.setAttribute("aria-label", "Países no gráfico");
  const caixaGrafico = el("div");
  ladoLinha.append(escolha, caixaGrafico);
  grade.append(painelRanking, ladoLinha);

  // ---------------------------------------------------------------- tabela
  const cartaoTabela = el("div", "tabela-cartao");
  cartaoTabela.style.marginTop = "14px";
  const tituloTabela = el("h3");
  const subTabela = el("p", "sub");
  const rolavel = el("div", "tabela-rolavel");
  rolavel.style.maxHeight = "none";
  const peTabela = el("footer", "grafico-pe");
  cartaoTabela.append(tituloTabela, subTabela, rolavel, peTabela);
  let ordem: { id: string; sentido: 1 | -1 } | null = null;

  raiz.append(fichas, sobre, grade, cartaoTabela);

  function pintarAnos(): void {
    anos.replaceChildren();
    const lista = metrica.anos.filter((a) => a >= m.ano_corrente - 6);
    if (!lista.includes(ano)) ano = lista.includes(m.ano_corrente) ? m.ano_corrente : (lista[0] ?? ano);
    for (const a of lista) {
      const b = el("button", `ficha ${projetado(metrica, a) ? "proj" : ""}`, String(a));
      b.type = "button";
      b.setAttribute("aria-pressed", String(a === ano));
      if (projetado(metrica, a)) b.title = "Projeção do FMI";
      b.addEventListener("click", () => {
        ano = a;
        pintar();
      });
      anos.append(b);
    }
    // No celular a lista de anos rola: o ano escolhido fica à vista, sem mexer na página.
    const marcado = anos.querySelector<HTMLElement>('[aria-pressed="true"]');
    if (marcado) {
      requestAnimationFrame(() => {
        anos.scrollLeft = marcado.offsetLeft - anos.offsetLeft - anos.clientWidth / 2 + marcado.offsetWidth / 2;
      });
    }
  }

  function pintarRanking(): void {
    const proj = projetado(metrica, ano);
    tituloRanking.textContent = `${metrica.nome} em ${ano}${proj ? " (projeção)" : ""}`;
    subRanking.textContent = metrica.unidade;
    const linhas = m.paises
      .map((p) => ({ p, v: valor(metrica, p.iso3, ano) }))
      .filter((x): x is { p: Pais; v: number } => x.v !== null)
      .sort((a, b) => b.v - a.v);
    const max = Math.max(0, ...linhas.map((x) => x.v));
    const min = Math.min(0, ...linhas.map((x) => x.v));
    const amplitude = max - min || 1;
    const zero = ((0 - min) / amplitude) * 100;
    ranking.replaceChildren();
    let lugar = 0;
    let lugarBrasil = 0;
    let total = 0;
    for (const { p, v } of linhas) {
      const agregado = p.grupo === "agregado";
      if (!agregado) {
        lugar += 1;
        total += 1;
        if (p.iso3 === "BRA") lugarBrasil = lugar;
      }
      const linha = el(
        "div",
        `rank-linha ${p.iso3 === "BRA" ? "brasil" : ""} ${agregado ? "agregado" : ""}`,
      );
      const trilho = el("div", "rank-trilho");
      const marca = el("div", "rank-zero");
      marca.style.left = `${zero}%`;
      const barra = el("div", `rank-barra ${v < 0 ? "negativa" : ""}`);
      const tamanho = (Math.abs(v) / amplitude) * 100;
      barra.style.left = `${v < 0 ? zero - tamanho : zero}%`;
      barra.style.width = `${tamanho}%`;
      trilho.append(barra, marca);
      linha.append(
        el("span", "rank-pos", agregado ? "" : String(lugar)),
        el("span", "rank-nome", p.nome),
        trilho,
        el("span", "rank-valor", numero(v, metrica.casas)),
      );
      linha.title = `${p.nome}: ${numero(v, metrica.casas)} ${metrica.unidade}`;
      ranking.append(linha);
    }
    posicao.replaceChildren();
    const vBrasil = valor(metrica, "BRA", ano);
    if (lugarBrasil && vBrasil !== null) {
      posicao.append(
        document.createTextNode("Brasil: "),
        el("b", "", `${numero(vBrasil, metrica.casas)} ${metrica.unidade}`),
        document.createTextNode(`, o ${ordinal(lugarBrasil)} maior entre ${total} países.`),
      );
      const mundo = valor(metrica, "G001", ano);
      if (mundo !== null) {
        posicao.append(document.createTextNode(` Mundo: ${numero(mundo, metrica.casas)}.`));
      }
    }
    fonteRanking.replaceChildren(el("span", "fonte", `Fonte: ${metrica.fonte}`));
  }

  function pintarEscolha(): void {
    escolha.replaceChildren();
    const css = getComputedStyle(document.documentElement);
    for (const p of m.paises) {
      const casa = casas.get(p.iso3);
      const b = el("button", "ficha pais");
      b.type = "button";
      b.setAttribute("aria-pressed", String(casa !== undefined));
      if (casa !== undefined) {
        b.style.setProperty("--cor", css.getPropertyValue(`--serie-${casa + 1}`).trim());
        b.append(el("i"));
      }
      b.append(document.createTextNode(p.nome));
      if (p.iso3 === "BRA") b.disabled = true;
      b.addEventListener("click", () => {
        if (casas.has(p.iso3)) {
          casas.delete(p.iso3);
        } else {
          if (casas.size >= MAXIMO) return;
          const usadas = new Set(casas.values());
          let livre = 0;
          while (usadas.has(livre)) livre += 1;
          casas.set(p.iso3, livre);
        }
        pintarEscolha();
        pintarLinha();
      });
      escolha.append(b);
    }
  }

  function pintarLinha(): void {
    const corte = metrica.primeiro_ano_projetado;
    const escolhidos = [...casas.entries()].sort((a, b) => a[1] - b[1]);
    const g: Grafico = {
      id: `mundo-${metrica.id}`,
      titulo: `${metrica.nome}: Brasil e outros países`,
      subtitulo: corte ? `tracejado: projeção do FMI a partir de ${corte}` : "",
      tipo: "linha",
      unidade: metrica.unidade,
      casas: metrica.casas,
      periodicidade: "A",
      series: escolhidos.map(([iso, casa]) => ({
        id: iso,
        nome: nomes.get(iso)?.nome ?? iso,
        papel: "realizado" as const,
        tracejado_desde: corte ? `${corte}-01-01` : null,
        cor: casa,
        pontos: metrica.anos.map((a, i): [string, number | null] => [
          `${a}-01-01`,
          metrica.valores[iso]?.[i] ?? null,
        ]),
      })),
      faixa: null,
      linhas: [],
      janela_anos: 20,
      fonte: metrica.fonte,
      nota: "",
      largura: "inteira",
    };
    caixaGrafico.replaceChildren(montarGrafico(g));
  }

  function pintarTabela(): void {
    tituloTabela.textContent = `Todas as métricas em ${ano}`;
    subTabela.textContent =
      "Toque no nome da coluna para ordenar. Em itálico, projeção do FMI para o ano.";
    const tabela = el("table", "dados larga");
    const cab = tabela.createTHead().insertRow();
    cab.append(el("th", "", "País"));
    for (const mt of m.metricas) {
      const th = el("th");
      const b = el("button", "", mt.nome);
      b.type = "button";
      b.title = `${mt.nome} (${mt.unidade})`;
      if (ordem?.id === mt.id) {
        th.setAttribute("aria-sort", ordem.sentido === -1 ? "descending" : "ascending");
      }
      b.addEventListener("click", () => {
        if (ordem?.id !== mt.id) ordem = { id: mt.id, sentido: -1 };
        else if (ordem.sentido === -1) ordem = { id: mt.id, sentido: 1 };
        else ordem = null;
        pintarTabela();
      });
      th.append(b);
      cab.append(th);
    }
    const corpo = tabela.createTBody();
    const linhaDe = (p: Pais): void => {
      const tr = corpo.insertRow();
      if (p.iso3 === "BRA") tr.className = "brasil";
      tr.append(el("th", "", p.nome));
      for (const mt of m.metricas) {
        const v = valor(mt, p.iso3, ano);
        const td = el("td", projetado(mt, ano) ? "proj" : "", v === null ? "–" : numero(v, mt.casas));
        tr.append(td);
      }
    };
    if (ordem) {
      const alvo = m.metricas.find((x) => x.id === ordem?.id);
      const sentido = ordem.sentido;
      const lista = [...m.paises].sort((a, b) => {
        const va = alvo ? valor(alvo, a.iso3, ano) : null;
        const vb = alvo ? valor(alvo, b.iso3, ano) : null;
        if (va === null) return 1;
        if (vb === null) return -1;
        return (va - vb) * sentido;
      });
      lista.forEach(linhaDe);
    } else {
      for (const [grupo, nome] of GRUPOS) {
        const lista = m.paises.filter((p) => p.grupo === grupo);
        if (!lista.length) continue;
        const tr = corpo.insertRow();
        tr.className = "grupo";
        const th = el("th", "", nome);
        th.colSpan = m.metricas.length + 1;
        tr.append(th);
        lista.forEach(linhaDe);
      }
    }
    rolavel.replaceChildren(tabela);
    peTabela.replaceChildren(el("span", "fonte", `Fonte: FMI, ${m.edicao}.`));
  }

  function pintar(): void {
    botoesMetrica.forEach((b, i) =>
      b.setAttribute("aria-pressed", String(m.metricas[i]?.id === metrica.id)),
    );
    sobre.textContent = metrica.descricao;
    pintarAnos();
    pintarRanking();
    pintarEscolha();
    pintarLinha();
    pintarTabela();
  }

  pintar();
  document.addEventListener("tema", pintarEscolha);
  return raiz;
}
