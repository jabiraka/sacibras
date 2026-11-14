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
import {
  desenharDispersao,
  linhaDoRanking,
  listaSuspensa,
  reguaDe,
  type LinhaDoRanking,
  type PontoDisperso,
} from "./pontos";
import { montarFicha } from "./ficha";
import type { Estados, EstadosContas, MetricaEstados } from "./tipos";

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
  // Rótulo só onde cabe; o resto aparece ao tocar. Pernambuco é comprido e fino, e os estados
  // pequenos do Nordeste e do Sudeste encavalam: ficam sem rótulo.
  const comRotulo = UFS.features.filter(
    (d) => d.properties.area > (estreito ? 70000 : 50000) && d.properties.uf !== "PE",
  );
  const comValor = estreito ? [] : comRotulo.filter((d) => d.properties.area > 90000);
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
  // O estado tocado no ranking ou no gráfico de duas métricas fica destacado nos dois.
  let destaque = "";

  const opcoes = e.metricas.map((m) => ({ valor: m.id, rotulo: m.nome }));
  const barra = el("div", "barra-controles");
  barra.append(
    listaSuspensa("estados-metrica", "Métrica", opcoes, metrica.id, (id) => {
      metrica = e.metricas.find((m) => m.id === id) ?? metrica;
      pintar();
    }).caixa,
  );
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
  const ranking = el("div", "ranking-pontos");
  const posicao = el("p", "posicao");
  painelRanking.append(tituloRanking, ranking, posicao);
  grade.append(painelMapa, painelRanking);

  // Duas métricas ao mesmo tempo, um ponto por estado.
  const painelDispersao = el("div", "painel-mundo dispersao-painel");
  let eixoX = e.metricas.find((m) => m.id === "pessoal") ?? (e.metricas[0] as MetricaEstados);
  let eixoY = e.metricas.find((m) => m.id === "divida") ?? (e.metricas[1] as MetricaEstados);
  const barraDispersao = el("div", "barra-controles");
  barraDispersao.append(
    listaSuspensa("estados-x", "Na horizontal", opcoes, eixoX.id, (id) => {
      eixoX = e.metricas.find((m) => m.id === id) ?? eixoX;
      pintarDispersao();
    }).caixa,
    listaSuspensa("estados-y", "Na vertical", opcoes, eixoY.id, (id) => {
      eixoY = e.metricas.find((m) => m.id === id) ?? eixoY;
      pintarDispersao();
    }).caixa,
  );
  const telaDispersao = el("div", "tela-dispersao");
  const notaDispersao = el("p", "posicao");
  const peDispersao = el("footer", "grafico-pe");
  // Com só 27 estados, os extremos são a história (a dívida de RJ, MG e RS): todos à vista.
  let comExtremos = true;
  painelDispersao.append(
    el("h3", "", "Duas métricas ao mesmo tempo"),
    el("p", "sub", "Um ponto por estado. Toque num ponto para ver os números e destacá-lo."),
    barraDispersao,
    telaDispersao,
    notaDispersao,
    peDispersao,
  );

  // A ficha de um estado: escolhida na lista ou com um toque no ranking.
  const painelFicha = el("div", "painel-mundo ficha");
  const corpoFicha = el("div", "ficha-corpo");
  let contas: Promise<EstadosContas | null> | null = null;
  const lerContas = (): Promise<EstadosContas | null> =>
    (contas ??= e.arquivo_contas
      ? fetch(`data/${e.arquivo_contas}`, { cache: "no-cache" })
          .then((r) => (r.ok ? (r.json() as Promise<EstadosContas>) : null))
          .catch(() => null)
      : Promise.resolve(null));
  let fichaDe = "";
  const opcoesUf = [{ valor: "", rotulo: "Escolha um estado" }, ...[...e.ufs].sort((a, b) => a.nome.localeCompare(b.nome)).map((u) => ({ valor: u.sigla, rotulo: u.nome }))];
  const escolhaFicha = listaSuspensa(
    "estados-ficha",
    "Estado",
    opcoesUf,
    "",
    (uf) => abrirFicha(uf),
  );
  const barraFicha = el("div", "barra-controles");
  barraFicha.append(escolhaFicha.caixa);
  painelFicha.append(
    el("h3", "", "As contas de um estado"),
    el(
      "p",
      "sub",
      "De onde vem a receita, para onde vai a despesa, quanto investe e do que é feita a dívida. Escolha na lista ou toque num estado do ranking.",
    ),
    barraFicha,
    corpoFicha,
  );
  function abrirFicha(uf: string): void {
    fichaDe = uf;
    escolhaFicha.trocar(opcoesUf, uf);
    if (!uf) {
      corpoFicha.replaceChildren();
      return;
    }
    corpoFicha.replaceChildren(el("p", "sub", "Lendo as contas…"));
    void lerContas().then((todas) => {
      if (fichaDe !== uf) return;
      const c = todas?.contas[uf];
      corpoFicha.replaceChildren(
        ...(todas && c
          ? montarFicha(c, todas)
          : [el("p", "sub", "As contas deste estado não vieram nesta rodada.")]),
      );
    });
  }

  raiz.append(barra, sobre, grade);
  if (e.arquivo_contas) raiz.append(painelFicha);
  raiz.append(painelDispersao);
  const caixaTabela = el("div");
  raiz.append(caixaTabela);

  let pendente = 0;
  new ResizeObserver(() => {
    cancelAnimationFrame(pendente);
    pendente = requestAnimationFrame(() => desenharMapa(tela, metrica, nomes));
  }).observe(tela);
  let pendenteDispersao = 0;
  new ResizeObserver(() => {
    cancelAnimationFrame(pendenteDispersao);
    pendenteDispersao = requestAnimationFrame(pintarDispersao);
  }).observe(telaDispersao);

  function destacar(uf: string): void {
    destaque = destaque === uf ? "" : uf;
    if (destaque && e.arquivo_contas) abrirFicha(destaque);
    pintarRanking();
    pintarDispersao();
  }

  function pintarDispersao(): void {
    if (!telaDispersao.clientWidth) return;
    const corDestaque = getComputedStyle(document.documentElement).getPropertyValue("--serie-2").trim();
    const pontos: PontoDisperso[] = [];
    for (const u of e.ufs) {
      const x = eixoX.valores[u.sigla] ?? null;
      const y = eixoY.valores[u.sigla] ?? null;
      if (x === null || y === null) continue;
      pontos.push({
        chave: u.sigla,
        nome: u.sigla,
        x,
        y,
        marca: "comum",
        cor: u.sigla === destaque ? corDestaque : undefined,
        // Sigla em todos: são só 27, e é o jeito de achar o seu estado.
        rotulo: true,
      });
    }
    if (pontos.length < 3) {
      telaDispersao.replaceChildren(el("p", "vazio", "Poucos estados com as duas métricas."));
      return;
    }
    const fora = desenharDispersao(
      telaDispersao,
      pontos,
      { nome: eixoX.nome, unidade: eixoX.unidade, casas: eixoX.casas },
      { nome: eixoY.nome, unidade: eixoY.unidade, casas: eixoY.casas },
      destacar,
      comExtremos,
    );
    // Quem saiu do desenho por estar muito longe dos outros é dito, com o botão de mostrar.
    notaDispersao.replaceChildren();
    if (fora.length || comExtremos) {
      if (fora.length) {
        notaDispersao.append(
          document.createTextNode(
            `Fora do desenho, por estar muito longe dos outros: ${fora
              .map((p) => `${nomes.get(p.chave) ?? p.chave} (${numero(p.x, eixoX.casas)}; ${numero(p.y, eixoY.casas)})`)
              .join(", ")}. `,
          ),
        );
      }
      const botao = el("button", "botao-texto", comExtremos ? "Tirar os valores extremos" : "Mostrar todos");
      botao.type = "button";
      botao.addEventListener("click", () => {
        comExtremos = !comExtremos;
        pintarDispersao();
      });
      notaDispersao.append(botao);
    }
    peDispersao.replaceChildren(
      el(
        "span",
        "fonte",
        `${eixoX.nome}: ${eixoX.referencia}. ${eixoY.nome}: ${eixoY.referencia}. Fontes: ${eixoX.fonte}${eixoX.fonte === eixoY.fonte ? "" : `; ${eixoY.fonte}`}.`,
      ),
    );
  }

  function pintarRanking(): void {
    const linhas = e.ufs
      .map((u) => ({ u, v: metrica.valores[u.sigla] ?? null }))
      .filter((x): x is { u: (typeof e.ufs)[number]; v: number } => x.v !== null)
      .sort((a, b) => b.v - a.v);
    const corDestaque = getComputedStyle(document.documentElement).getPropertyValue("--serie-2").trim();
    const regua = reguaDe(
      [...linhas.map((x) => x.v), ...(metrica.brasil === null ? [] : [metrica.brasil])],
      metrica.limites,
    );
    const itens: LinhaDoRanking[] = linhas.map((x, i) => ({
      chave: x.u.sigla,
      nome: x.u.nome,
      valor: x.v,
      marca: "comum",
      posicao: i + 1,
      cor: x.u.sigla === destaque ? corDestaque : undefined,
    }));
    if (metrica.brasil !== null) {
      itens.push({ chave: "BR", nome: "Brasil", valor: metrica.brasil, marca: "brasil", posicao: null });
      itens.sort((a, b) => b.valor - a.valor);
    }
    ranking.replaceChildren(
      ...itens.map((item) =>
        linhaDoRanking(item, regua, metrica.casas, item.marca === "brasil" ? undefined : () => destacar(item.chave)),
      ),
    );
    posicao.replaceChildren();
    if (metrica.limites.length) {
      posicao.textContent = `Traços amarelos: ${metrica.limites
        .map((l) => `${l.rotulo} (${numero(l.valor, metrica.casas)})`)
        .join("; ")}.`;
    }
    const semDado = e.ufs.filter((u) => (metrica.valores[u.sigla] ?? null) === null);
    if (semDado.length) {
      posicao.append(
        document.createTextNode(` Sem dado neste período: ${semDado.map((u) => u.sigla).join(", ")}.`),
      );
    }
  }

  function pintar(): void {
    sobre.textContent = metrica.descricao;
    tituloMapa.textContent = metrica.nome;
    subMapa.textContent = `${metrica.unidade} · ${metrica.referencia}`;
    const valores = Object.values(metrica.valores).filter((v): v is number => v !== null);
    if (tela.clientWidth) desenharMapa(tela, metrica, nomes);
    escala.replaceChildren(
      el("span", "", numero(Math.min(...valores), metrica.casas)),
      el("i"),
      el("span", "", numero(Math.max(...valores), metrica.casas)),
    );
    peMapa.replaceChildren(el("span", "fonte", `Fonte: ${metrica.fonte}. Malha: IBGE, 2024.`));
    pintarRanking();
    pintarDispersao();

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
