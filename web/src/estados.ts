// Estados: a mesma métrica nas 27 unidades da federação — o mapa do Brasil, pintado do claro
// ao escuro conforme o valor, e o ranking ao lado. A malha é a do IBGE (src/mapa/ufs.json,
// gerada por `npm run malha`).
//
// A tela vem em partes (Caio, 14/11/2026: "diminua a tela ao abrir por estado, também não
// precisa mostrar tudo em uma página só"): a visão geral só com o mapa; "mapa" com o
// ranking; "estado" com a ficha de um estado, um bloco de cada vez; "duas-metricas"; e
// "tabela". As partes vêm do builder (`organizacao.PARTES_ESTADOS`).

import * as Plot from "@observablehq/plot";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import { feature } from "topojson-client";
import type { GeometryCollection, Topology } from "topojson-specification";
import { numero } from "./formato";
import malha from "./mapa/ufs.json";
import { el } from "./pecas";
import {
  desenharDispersao,
  linhaDoRanking,
  listaSuspensa,
  reguaDe,
  type LinhaDoRanking,
  type PontoDisperso,
} from "./pontos";
import { montarFicha } from "./ficha";
import { remarcar } from "./glossario";
import type { Estados, EstadosContas, MetricaEstados } from "./tipos";
import { protegerNomeDeEstado } from "./traducao";

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
    if (v === null) return `${nome}\nsem dado`;
    const f = metrica.intervalos?.[d.properties.uf];
    return (
      `${nome}\n${numero(v, metrica.casas)} ${metrica.unidade}` +
      (f ? `\nfaixa de erro: de ${numero(f[0], metrica.casas)} a ${numero(f[1], metrica.casas)}` : "") +
      (metrica.estimados?.includes(d.properties.uf) ? "\nestimado pela região" : "")
    );
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

export function montarEstados(e: Estados, parte: string, ufInicial = ""): HTMLElement {
  const raiz = el("div", "estados");
  const nomes = new Map(e.ufs.map((u) => [u.sigla, u.nome]));
  let metrica = e.metricas[0] as MetricaEstados;
  // O estado tocado no ranking ou no gráfico de duas métricas fica destacado nos dois.
  let destaque = "";
  const opcoes = e.metricas.map((m) => ({ valor: m.id, rotulo: m.nome, grupo: m.grupo || undefined }));
  const corDestaque = (): string =>
    getComputedStyle(document.documentElement).getPropertyValue("--serie-2").trim();

  if (parte === "estado") {
    raiz.append(montarParteFicha(e, ufInicial));
    return raiz;
  }
  if (parte === "tabela") {
    raiz.append(tabelaCompleta(e));
    return raiz;
  }
  if (parte === "duas-metricas") {
    raiz.append(montarDispersao(e, nomes, opcoes, corDestaque));
    return raiz;
  }

  // Visão geral (o mapa sozinho, menor) ou a parte "mapa" (mapa e ranking lado a lado).
  const comRanking = parte === "mapa";
  const barra = el("div", "barra-controles");
  barra.append(
    listaSuspensa("estados-metrica", "Métrica", opcoes, metrica.id, (id) => {
      metrica = e.metricas.find((m) => m.id === id) ?? metrica;
      pintar();
    }).caixa,
  );
  const sobre = el("p", "secao-resumo");
  const grade = el("div", comRanking ? "mundo-grade" : "estados-so-mapa");
  const painelMapa = el("div", "painel-mundo");
  const tituloMapa = el("h3");
  const subMapa = el("p", "sub");
  const tela = el("div", "mapa");
  const escala = el("div", "mapa-escala");
  const peMapa = el("footer", "grafico-pe");
  painelMapa.append(tituloMapa, subMapa, tela, escala, peMapa);
  grade.append(painelMapa);

  const ranking = el("div", "ranking-pontos");
  const posicao = el("p", "posicao");
  if (comRanking) {
    const painelRanking = el("div", "painel-mundo");
    painelRanking.append(el("h3", "", "Do maior ao menor"), ranking, posicao);
    grade.append(painelRanking);
  }
  raiz.append(barra, sobre, grade);

  let pendente = 0;
  new ResizeObserver(() => {
    cancelAnimationFrame(pendente);
    pendente = requestAnimationFrame(() => desenharMapa(tela, metrica, nomes));
  }).observe(tela);

  function destacar(uf: string): void {
    destaque = destaque === uf ? "" : uf;
    pintarRanking();
  }

  function pintarRanking(): void {
    if (!comRanking) return;
    const linhas = e.ufs
      .map((u) => ({ u, v: metrica.valores[u.sigla] ?? null }))
      .filter((x): x is { u: (typeof e.ufs)[number]; v: number } => x.v !== null)
      .sort((a, b) => b.v - a.v);
    const faixas = metrica.intervalos ?? {};
    const estimados = new Set(metrica.estimados ?? []);
    const regua = reguaDe(
      [
        ...linhas.map((x) => x.v),
        ...Object.values(faixas).flat(),
        ...(metrica.brasil === null ? [] : [metrica.brasil]),
      ],
      metrica.limites,
    );
    const itens: LinhaDoRanking[] = linhas.map((x, i) => ({
      chave: x.u.sigla,
      nome: x.u.nome,
      valor: x.v,
      marca: "comum",
      posicao: i + 1,
      cor: x.u.sigla === destaque ? corDestaque() : undefined,
      faixa: faixas[x.u.sigla],
      estimado: estimados.has(x.u.sigla),
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
    remarcar(posicao);
    if (destaque && e.arquivo_contas) {
      // O estado tocado: o caminho para as contas dele, na parte própria.
      const a = el("a", "pilula", `Ver as contas de ${nomes.get(destaque) ?? destaque} →`);
      a.href = `#estados/uf-${destaque}`;
      posicao.append(a, el("br"));
    }
    if (metrica.limites.length) {
      posicao.append(
        document.createTextNode(
          `Traços amarelos: ${metrica.limites
            .map((l) => `${l.rotulo} (${numero(l.valor, metrica.casas)})`)
            .join("; ")}.`,
        ),
      );
    }
    if (metrica.como_ler) posicao.append(document.createTextNode(metrica.como_ler));
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
    // O texto mudou: o glossário marca de novo (o "?" do título, o sublinhado da descrição).
    remarcar(sobre);
    remarcar(painelMapa);
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
  }

  pintar();
  return raiz;
}

/** Duas métricas ao mesmo tempo, um ponto por estado. */
function montarDispersao(
  e: Estados,
  nomes: Map<string, string>,
  opcoes: { valor: string; rotulo: string }[],
  corDestaque: () => string,
): HTMLElement {
  const painel = el("div", "painel-mundo dispersao-painel");
  let destaque = "";
  let eixoX = e.metricas.find((m) => m.id === "pessoal") ?? (e.metricas[0] as MetricaEstados);
  let eixoY = e.metricas.find((m) => m.id === "divida") ?? (e.metricas[1] as MetricaEstados);
  const barra = el("div", "barra-controles");
  barra.append(
    listaSuspensa("estados-x", "Na horizontal", opcoes, eixoX.id, (id) => {
      eixoX = e.metricas.find((m) => m.id === id) ?? eixoX;
      pintar();
    }).caixa,
    listaSuspensa("estados-y", "Na vertical", opcoes, eixoY.id, (id) => {
      eixoY = e.metricas.find((m) => m.id === id) ?? eixoY;
      pintar();
    }).caixa,
  );
  const tela = el("div", "tela-dispersao");
  const nota = el("p", "posicao");
  const pe = el("footer", "grafico-pe");
  // Com só 27 estados, os extremos são a história (a dívida de RJ, MG e RS): todos à vista.
  let comExtremos = true;
  painel.append(
    el("h3", "", "Duas métricas ao mesmo tempo"),
    el("p", "sub", "Um ponto por estado. Toque num ponto para ver os números."),
    barra,
    tela,
    nota,
    pe,
  );
  let pendente = 0;
  new ResizeObserver(() => {
    cancelAnimationFrame(pendente);
    pendente = requestAnimationFrame(pintar);
  }).observe(tela);

  function pintar(): void {
    if (!tela.clientWidth) return;
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
        cor: u.sigla === destaque ? corDestaque() : undefined,
        // Sigla em todos: são só 27, e é o jeito de achar o seu estado.
        rotulo: true,
      });
    }
    if (pontos.length < 3) {
      tela.replaceChildren(el("p", "vazio", "Poucos estados com as duas métricas."));
      return;
    }
    const fora = desenharDispersao(
      tela,
      pontos,
      { nome: eixoX.nome, unidade: eixoX.unidade, casas: eixoX.casas },
      { nome: eixoY.nome, unidade: eixoY.unidade, casas: eixoY.casas },
      (uf) => {
        destaque = destaque === uf ? "" : uf;
        pintar();
      },
      comExtremos,
    );
    // Quem saiu do desenho por estar muito longe dos outros é dito, com o botão de mostrar.
    nota.replaceChildren();
    if (fora.length) {
      nota.append(
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
      pintar();
    });
    nota.append(botao);
    pe.replaceChildren(
      el(
        "span",
        "fonte",
        `${eixoX.nome}: ${eixoX.referencia}. ${eixoY.nome}: ${eixoY.referencia}. Fontes: ${eixoX.fonte}${eixoX.fonte === eixoY.fonte ? "" : `; ${eixoY.fonte}`}.`,
      ),
    );
  }
  return painel;
}

/** A ficha de um estado: escolhido na lista, ou vindo do ranking e da busca (`uf-SP`). */
function montarParteFicha(e: Estados, ufInicial: string): HTMLElement {
  const painel = el("div", "painel-mundo ficha");
  const corpo = el("div", "ficha-corpo");
  let contas: Promise<EstadosContas | null> | null = null;
  const lerContas = (): Promise<EstadosContas | null> =>
    (contas ??= e.arquivo_contas
      ? fetch(`data/${e.arquivo_contas}`, { cache: "no-cache" })
          .then((r) => (r.ok ? (r.json() as Promise<EstadosContas>) : null))
          .catch(() => null)
      : Promise.resolve(null));
  let fichaDe = "";
  const opcoesUf = [
    { valor: "", rotulo: "Escolha um estado" },
    ...[...e.ufs].sort((a, b) => a.nome.localeCompare(b.nome)).map((u) => ({ valor: u.sigla, rotulo: u.nome })),
  ];
  const escolha = listaSuspensa("estados-ficha", "Estado", opcoesUf, "", (uf) => abrir(uf));
  const barra = el("div", "barra-controles");
  barra.append(escolha.caixa);
  painel.append(barra, corpo);

  function abrir(uf: string): void {
    fichaDe = uf;
    escolha.trocar(opcoesUf, uf);
    if (!uf) {
      corpo.replaceChildren(el("p", "sub", "Escolha um estado na lista."));
      return;
    }
    corpo.replaceChildren(el("p", "sub", "Lendo as contas…"));
    void lerContas().then((todas) => {
      if (fichaDe !== uf) return;
      const c = todas?.contas[uf];
      corpo.replaceChildren(
        ...(todas && c
          ? montarFicha(c, todas)
          : [el("p", "sub", "As contas deste estado não vieram nesta rodada.")]),
      );
    });
  }
  abrir(e.ufs.some((u) => u.sigla === ufInicial) ? ufInicial : "");
  return painel;
}

/** Todas as métricas lado a lado, agrupadas por região. */
function tabelaCompleta(e: Estados): HTMLElement {
  const caixa = el("div", "painel-mundo");
  const rolavel = el("div", "tabela-rolavel");
  const tabela = el("table", "dados larga");
  const cabeca = tabela.createTHead();
  // Uma linha com o assunto de cada bloco de colunas (Economia, Trabalho e renda…).
  if (e.metricas.some((m) => m.grupo)) {
    const grupos = cabeca.insertRow();
    grupos.className = "grupos";
    grupos.append(el("th"));
    for (const m of e.metricas) {
      const ultimo = grupos.lastElementChild as HTMLTableCellElement;
      if (grupos.cells.length > 1 && ultimo.dataset.grupo === (m.grupo ?? "")) {
        ultimo.colSpan += 1;
        continue;
      }
      const th = el("th", "", m.grupo ?? "");
      th.dataset.grupo = m.grupo ?? "";
      th.scope = "colgroup";
      grupos.append(th);
    }
  }
  const cab = cabeca.insertRow();
  cab.append(el("th", "", "Estado"));
  for (const m of e.metricas) {
    const th = el("th", "", m.nome);
    th.append(el("span", "sub", ` ${m.unidade}`));
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
      const nome = el("th", "", u.nome);
      protegerNomeDeEstado(nome, u.nome);
      linha.append(nome);
      for (const m of e.metricas) {
        const v = m.valores[u.sigla] ?? null;
        linha.append(el("td", "", v === null ? "–" : numero(v, m.casas)));
      }
    }
  }
  rolavel.append(tabela);
  const fontes = [...new Set(e.metricas.map((m) => m.fonte))].join("; ");
  caixa.append(rolavel, el("p", "fonte", `Fontes: ${fontes}.`));
  return caixa;
}
