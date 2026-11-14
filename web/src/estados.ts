// Estados: a mesma métrica nas 27 unidades da federação — o mapa do Brasil, pintado do claro
// ao escuro conforme o valor, e o ranking ao lado. A malha é a do IBGE (src/mapa/ufs.json,
// gerada por `npm run malha`).

import * as Plot from "@observablehq/plot";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import { feature } from "topojson-client";
import type { GeometryCollection, Topology } from "topojson-specification";
import { numero } from "./formato";
import malha from "./mapa/ufs.json";
import { el, guardar } from "./pecas";
import type { Estados, MetricaEstados } from "./tipos";

type PropriedadesUF = { uf: string; area: number };
type UFNoMapa = Feature<Geometry, PropriedadesUF>;

const topologia = malha as unknown as Topology<{ ufs: GeometryCollection<PropriedadesUF> }>;
const UFS = feature(topologia, topologia.objects.ufs) as FeatureCollection<
  Geometry,
  PropriedadesUF
>;

/** Uma cor entre as duas pontas da escala (hex), com `t` de 0 a 1. */
function misturar(de: string, ate: string, t: number): string {
  const canal = (hex: string, i: number): number => parseInt(hex.slice(1 + 2 * i, 3 + 2 * i), 16);
  const partes = [0, 1, 2].map((i) =>
    Math.round(canal(de, i) + (canal(ate, i) - canal(de, i)) * t)
      .toString(16)
      .padStart(2, "0"),
  );
  return `#${partes.join("")}`;
}

function cores(): { claro: string; escuro: string; semDado: string; tinta: string; borda: string } {
  const css = getComputedStyle(document.documentElement);
  const v = (nome: string): string => css.getPropertyValue(nome).trim();
  return {
    claro: v("--mapa-claro"),
    escuro: v("--mapa-escuro"),
    semDado: v("--mapa-sem-dado"),
    tinta: v("--tinta"),
    borda: v("--superficie"),
  };
}

function desenharMapa(alvo: HTMLElement, metrica: MetricaEstados, nomes: Map<string, string>): void {
  const largura = Math.max(260, Math.floor(alvo.clientWidth));
  const estreito = largura < 400;
  const c = cores();
  const valores = Object.values(metrica.valores).filter((v): v is number => v !== null);
  const min = Math.min(...valores);
  const max = Math.max(...valores);
  const fracao = (v: number): number => (v - min) / (max - min || 1);
  const valorDe = (d: UFNoMapa): number | null => metrica.valores[d.properties.uf] ?? null;
  const preenchimento = (d: UFNoMapa): string => {
    const v = valorDe(d);
    return v === null ? c.semDado : misturar(c.claro, c.escuro, fracao(v));
  };
  const titulo = (d: UFNoMapa): string => {
    const v = valorDe(d);
    const nome = nomes.get(d.properties.uf) ?? d.properties.uf;
    return `${nome}\n${v === null ? "sem dado" : `${numero(v, metrica.casas)} ${metrica.unidade}`}`;
  };

  // Rótulo só onde cabe: no celular, só os estados grandes; o resto aparece ao tocar.
  // Pernambuco é comprido e fino: no celular o rótulo dele encavala nos vizinhos.
  const comRotulo = UFS.features.filter((d) =>
    estreito ? d.properties.area > 70000 && d.properties.uf !== "PE" : d.properties.area > 15000,
  );
  const comValor = estreito ? [] : comRotulo.filter((d) => d.properties.area > 45000);
  const corDoTexto = (d: UFNoMapa): string => {
    const v = valorDe(d);
    return v !== null && fracao(v) > 0.55 ? "#ffffff" : c.tinta;
  };
  const texto = (d: UFNoMapa): string => {
    const v = valorDe(d);
    if (!comValor.includes(d) || v === null) return d.properties.uf;
    return `${d.properties.uf}\n${numero(v, metrica.casas)}`;
  };

  const mapa = Plot.plot({
    width: largura,
    height: Math.round(largura * 0.98),
    margin: 4,
    projection: { type: "mercator", domain: UFS },
    style: { background: "transparent", fontFamily: "inherit", overflow: "visible" },
    marks: [
      Plot.geo(UFS.features, {
        fill: preenchimento,
        stroke: c.borda,
        strokeWidth: 0.9,
      }),
      Plot.text(
        comRotulo,
        Plot.centroid({
          text: texto,
          fill: corDoTexto,
          fontSize: estreito ? 9.5 : 11,
          fontWeight: 600,
          lineHeight: 1.15,
        }),
      ),
      Plot.tip(UFS.features, Plot.pointer(Plot.centroid({ title: titulo, fontSize: 12 }))),
    ],
  });
  mapa.setAttribute("role", "img");
  mapa.setAttribute(
    "aria-label",
    `${metrica.nome} por estado, ${metrica.referencia}. O ranking ao lado traz todos os valores.`,
  );
  alvo.replaceChildren(mapa);
}

export function montarEstados(e: Estados): HTMLElement {
  const raiz = el("div");
  const nomes = new Map(e.ufs.map((u) => [u.sigla, u.nome]));
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
  const tela = el("div", "mapa");
  const escala = el("div", "mapa-escala");
  const peMapa = el("footer", "grafico-pe");
  painelMapa.append(tituloMapa, subMapa, tela, escala, peMapa);

  const painelRanking = el("div", "painel-mundo");
  const tituloRanking = el("h3", "", "Do maior ao menor");
  const ranking = el("div", "ranking");
  const posicao = el("p", "posicao");
  painelRanking.append(tituloRanking, ranking, posicao);
  grade.append(painelMapa, painelRanking);

  raiz.append(fichas, sobre, grade);
  const caixaTabela = el("div");
  raiz.append(caixaTabela);

  let pendente = 0;
  new ResizeObserver(() => {
    cancelAnimationFrame(pendente);
    pendente = requestAnimationFrame(() => desenharMapa(tela, metrica, nomes));
  }).observe(tela);

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

    if (tela.clientWidth) desenharMapa(tela, metrica, nomes);
    escala.replaceChildren(
      el("span", "", numero(min, metrica.casas)),
      el("i"),
      el("span", "", numero(max, metrica.casas)),
    );
    peMapa.replaceChildren(el("span", "fonte", `Fonte: ${metrica.fonte}. Malha: IBGE, 2024.`));

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
      posicao.textContent = `Traços amarelos: ${metrica.limites
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
            linha.append(el("th", "", u.nome));
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
