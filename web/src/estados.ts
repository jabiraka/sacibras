// Estados: a mesma métrica nas 27 unidades da federação — um mapa em grade (cada estado um
// quadrado, mais ou menos no lugar dele) e o ranking. Sem geometria para baixar.

import { numero } from "./formato";
import { el, guardar } from "./pecas";
import type { Estados, MetricaEstados } from "./tipos";

// [coluna, linha] de cada estado na grade de 7 × 9.
const LUGAR: Record<string, [number, number]> = {
  RR: [2, 0], AP: [3, 0],
  AM: [1, 1], PA: [2, 1], MA: [3, 1], CE: [4, 1], RN: [5, 1],
  AC: [0, 2], RO: [1, 2], TO: [2, 2], PI: [3, 2], PE: [4, 2], PB: [5, 2],
  MT: [1, 3], GO: [2, 3], BA: [3, 3], AL: [4, 3], SE: [5, 3],
  MS: [1, 4], DF: [2, 4], MG: [3, 4], ES: [4, 4],
  SP: [2, 5], RJ: [3, 5],
  PR: [2, 6], SC: [2, 7], RS: [2, 8],
};

export function montarEstados(e: Estados): HTMLElement {
  const raiz = el("div");
  const nomes = new Map(e.ufs.map((u) => [u.sigla, u]));
  let metrica = e.metricas[0] as MetricaEstados;

  const fichas = el("div", "mundo-controles");
  fichas.setAttribute("role", "group");
  fichas.setAttribute("aria-label", "Métrica");
  const botoes = e.metricas.map((m) => {
    const b = el("button", "ficha", m.nome);
    b.type = "button";
    b.addEventListener("click", () => {
      metrica = m;
      pintar();
    });
    fichas.append(b);
    return b;
  });
  const sobre = el("p", "secao-resumo");

  const grade = el("div", "mundo-grade");
  const painelMapa = el("div", "painel-mundo");
  const tituloMapa = el("h3");
  const subMapa = el("p", "sub");
  const mapa = el("div", "mapa-grade");
  mapa.setAttribute("role", "img");
  const escala = el("div", "mapa-escala");
  const peMapa = el("footer", "grafico-pe");
  painelMapa.append(tituloMapa, subMapa, mapa, escala, peMapa);

  const painelRanking = el("div", "painel-mundo");
  const tituloRanking = el("h3", "", "Do maior ao menor");
  const ranking = el("div", "ranking");
  const posicao = el("p", "posicao");
  painelRanking.append(tituloRanking, ranking, posicao);
  grade.append(painelMapa, painelRanking);

  raiz.append(fichas, sobre, grade);
  const caixaTabela = el("div");
  raiz.append(caixaTabela);

  function pintar(): void {
    botoes.forEach((b, i) => b.setAttribute("aria-pressed", String(e.metricas[i]?.id === metrica.id)));
    sobre.textContent = metrica.descricao;
    tituloMapa.textContent = metrica.nome;
    subMapa.textContent = `${metrica.unidade} · ${metrica.referencia}`;

    const linhas = e.ufs
      .map((u) => ({ u, v: metrica.valores[u.sigla] ?? null }))
      .filter((x): x is { u: (typeof e.ufs)[number]; v: number } => x.v !== null)
      .sort((a, b) => b.v - a.v);
    const valores = linhas.map((x) => x.v);
    const min = Math.min(...valores);
    const max = Math.max(...valores);

    // O mapa: um tom só, do claro ao forte conforme o valor.
    mapa.replaceChildren();
    for (const u of e.ufs) {
      const lugar = LUGAR[u.sigla];
      if (!lugar) continue;
      const v = metrica.valores[u.sigla] ?? null;
      const peca = el("div", "uf");
      peca.style.gridColumn = String(lugar[0] + 1);
      peca.style.gridRow = String(lugar[1] + 1);
      const forca = v === null ? 0 : 0.14 + 0.72 * ((v - min) / (max - min || 1));
      peca.style.setProperty("--forca", String(forca));
      if (v === null) peca.classList.add("sem-dado");
      else if (forca > 0.55) peca.classList.add("forte");
      peca.append(el("b", "", u.sigla), el("span", "", v === null ? "–" : numero(v, metrica.casas)));
      peca.title = `${u.nome}: ${v === null ? "sem dado" : `${numero(v, metrica.casas)} ${metrica.unidade}`}`;
      mapa.append(peca);
    }
    mapa.setAttribute(
      "aria-label",
      `${metrica.nome} por estado, ${metrica.referencia}. A lista ao lado traz todos os valores.`,
    );
    escala.replaceChildren(
      el("span", "", numero(min, metrica.casas)),
      el("i"),
      el("span", "", numero(max, metrica.casas)),
    );
    peMapa.replaceChildren(el("span", "fonte", `Fonte: ${metrica.fonte}`));

    // O ranking, com o Brasil e os limites que a fonte publica.
    const teto = Math.max(max, metrica.brasil ?? 0, ...metrica.limites.map((l) => l.valor));
    const piso = Math.min(0, min);
    const amplitude = teto - piso || 1;
    const zero = ((0 - piso) / amplitude) * 100;
    ranking.replaceChildren();
    const comBrasil: { nome: string; v: number; brasil: boolean }[] = linhas.map((x) => ({
      nome: x.u.nome,
      v: x.v,
      brasil: false,
    }));
    if (metrica.brasil !== null) {
      comBrasil.push({ nome: "Brasil", v: metrica.brasil, brasil: true });
      comBrasil.sort((a, b) => b.v - a.v);
    }
    let lugar = 0;
    for (const x of comBrasil) {
      if (!x.brasil) lugar += 1;
      const linha = el("div", `rank-linha ${x.brasil ? "brasil" : ""}`);
      const trilho = el("div", "rank-trilho");
      const barra = el("div", `rank-barra ${x.v < 0 ? "negativa" : ""}`);
      const tamanho = (Math.abs(x.v) / amplitude) * 100;
      barra.style.left = `${x.v < 0 ? zero - tamanho : zero}%`;
      barra.style.width = `${tamanho}%`;
      trilho.append(barra);
      for (const l of metrica.limites) {
        const marca = el("div", "rank-limite");
        marca.style.left = `${((l.valor - piso) / amplitude) * 100}%`;
        marca.title = `${l.rotulo}: ${numero(l.valor, metrica.casas)}`;
        trilho.append(marca);
      }
      linha.append(
        el("span", "rank-pos", x.brasil ? "" : String(lugar)),
        el("span", "rank-nome", x.nome),
        trilho,
        el("span", "rank-valor", numero(x.v, metrica.casas)),
      );
      ranking.append(linha);
    }
    posicao.replaceChildren();
    if (metrica.limites.length) {
      posicao.textContent = `Traços no gráfico: ${metrica.limites
        .map((l) => `${l.rotulo} (${numero(l.valor, metrica.casas)})`)
        .join("; ")}.`;
    }
    const semDado = e.ufs.filter((u) => (metrica.valores[u.sigla] ?? null) === null);
    if (semDado.length) {
      posicao.append(
        document.createTextNode(
          ` Sem dado neste período: ${semDado.map((u) => u.sigla).join(", ")}.`,
        ),
      );
    }

    // Todas as métricas lado a lado, guardadas.
    caixaTabela.replaceChildren(
      guardar("Todas as métricas, estado por estado", "Agrupado por região", () => {
        const rolavel = el("div", "tabela-rolavel");
        const tabela = el("table", "dados larga");
        const cab = tabela.createTHead().insertRow();
        cab.append(el("th", "", "Estado"));
        for (const m of e.metricas) {
          const th = el("th", "", m.nome);
          th.title = `${m.unidade} · ${m.referencia}`;
          cab.append(th);
        }
        const corpo = tabela.createTBody();
        for (const regiao of ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]) {
          const tr = corpo.insertRow();
          tr.className = "grupo";
          const th = el("th", "", regiao);
          th.colSpan = e.metricas.length + 1;
          tr.append(th);
          for (const u of e.ufs.filter((x) => x.regiao === regiao)) {
            const linha = corpo.insertRow();
            linha.append(el("th", "", nomes.get(u.sigla)?.nome ?? u.sigla));
            for (const m of e.metricas) {
              const v = m.valores[u.sigla] ?? null;
              linha.append(el("td", "", v === null ? "–" : numero(v, m.casas)));
            }
          }
        }
        rolavel.append(tabela);
        return [rolavel];
      }),
    );
  }

  pintar();
  return raiz;
}
