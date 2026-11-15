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
import { montarFicha, type Regiao } from "./ficha";
import { remarcar } from "./glossario";
import type { Estados, EstadosContas, MetricaEstados, PeriodoDaMetrica } from "./tipos";
import { protegerNomeDeEstado } from "./traducao";

type PropriedadesUF = { uf: string; area: number };
type UFNoMapa = Feature<Geometry, PropriedadesUF>;

const topologia = malha as unknown as Topology<{ ufs: GeometryCollection<PropriedadesUF> }>;
const UFS = feature(topologia, topologia.objects.ufs) as FeatureCollection<
  Geometry,
  PropriedadesUF
>;

/** O valor escrito: o nome, quando a métrica é uma nota (CAPAG), ou o número. */
function escrito(m: MetricaEstados, v: number): string {
  return m.marcas?.find((x) => x.valor === v)?.rotulo ?? numero(v, m.casas);
}

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

// ------------------------------------------------------------------ janela do PIB
//
// O crescimento do PIB vem com a série anual (o índice de volume das Contas Regionais e, no
// ano seguinte ao último do IBGE, a prévia pelo IBC-R). A pessoa escolhe de que ano a que
// ano (Caio, 14/11/2026: "não deixe a janela de 10 anos por padrão, deixe a pessoa escolher a
// janela"); a janela vale para o mapa, o ranking e a tabela, e fica ao trocar de parte.

interface Janela {
  de: number;
  ate: number;
}
let janela: Janela | null = null;

function anosDe(m: MetricaEstados): number[] {
  return Object.keys(m.anuais?.BR ?? {})
    .map(Number)
    .sort((a, b) => a - b);
}

/** Padrão: o último ano do IBGE sobre o anterior. */
function janelaPadrao(m: MetricaEstados): Janela {
  const anos = anosDe(m);
  const oficiais = anos.filter((a) => !m.ano_previsto || a < m.ano_previsto);
  const ate = oficiais[oficiais.length - 1] ?? anos[anos.length - 1] ?? 0;
  return { de: ate - 1, ate };
}

function janelaDe(m: MetricaEstados): Janela {
  const anos = anosDe(m);
  if (janela && anos.includes(janela.de) && anos.includes(janela.ate) && janela.de < janela.ate) {
    return janela;
  }
  return janelaPadrao(m);
}

/** A métrica do PIB recalculada na janela escolhida; as outras passam como vieram. */
function naJanela(m: MetricaEstados, todas: MetricaEstados[]): MetricaEstados {
  if (!m.anuais || anosDe(m).length < 2) return m;
  const series = m.anuais;
  const { de, ate } = janelaDe(m);
  const anos = ate - de;
  const cresc = (serie?: Record<string, number>): number | null => {
    const a = serie?.[String(de)];
    const b = serie?.[String(ate)];
    return a && b ? ((b / a) ** (1 / anos) - 1) * 100 : null;
  };
  const valores: Record<string, number | null> = {};
  for (const sigla of Object.keys(m.valores)) valores[sigla] = cresc(series[sigla]);
  const comPrevia = !!m.ano_previsto && ate >= m.ano_previsto;
  const previa = comPrevia ? todas.find((x) => x.id === "ibcr_ano") : undefined;
  const periodo = anos === 1 ? `em ${ate} sobre ${de}` : `por ano, em média, de ${de} a ${ate}`;
  let descricao = `Quanto a economia do estado cresceu ${periodo}, sem o efeito dos preços.`;
  descricao += comPrevia
    ? ` ${m.ano_previsto} ainda não tem número do IBGE: entra a prévia nossa pelo IBC-R do Banco Central (o do estado ou, para quem não tem, o da região), que é previsão e erra.`
    : " É o número oficial do IBGE (Contas Regionais), que sai com quase dois anos de atraso.";
  if (anos === 1 && !comPrevia && m.ano_previsto) {
    descricao += ` Para um sinal mais novo, escolha ${m.ano_previsto} (prévia) em "até".`;
  }
  const sozinha = anos === 1 && previa !== undefined;
  return {
    ...m,
    nome: anos === 1 ? "Crescimento do PIB" : "Crescimento médio do PIB",
    descricao,
    unidade: anos === 1 ? "%" : "% ao ano",
    referencia: (anos === 1 ? String(ate) : `${de}–${ate}`) + (comPrevia ? " (prévia)" : ""),
    fonte: previa ? `${m.fonte}; prévia: ${previa.fonte}` : m.fonte,
    valores,
    brasil: cresc(series.BR),
    // Só a prévia de um ano tem faixa de erro medida; numa janela longa, ela se dilui.
    intervalos: sozinha ? previa.intervalos : undefined,
    estimados: previa?.estimados,
    como_ler: sozinha
      ? previa.como_ler
      : previa
        ? "Ponto vazado: estado sem IBC-R, que no último ano cresce como a região."
        : "",
  };
}

// O PIB trimestral dos estados (estimativa nossa) vem com um valor por trimestre: a pessoa
// escolhe o trimestre numa lista (Caio, 15/11/2026: "a decomposição do PIB por estados em cada
// trimestre"). A escolha vale para as métricas que têm o mesmo trimestre e fica ao trocar.
let trimestre = "";

function periodoDe(m: MetricaEstados): PeriodoDaMetrica | undefined {
  return m.periodos?.find((p) => p.referencia === trimestre) ?? m.periodos?.[0];
}

/** A métrica no trimestre escolhido; sem `periodos`, passa como veio. */
function noTrimestre(m: MetricaEstados): MetricaEstados {
  const p = periodoDe(m);
  if (!p) return m;
  const semFaixa = !Object.keys(p.intervalos ?? {}).length;
  return {
    ...m,
    descricao: p.nota ? `${p.nota} ${m.descricao}` : m.descricao,
    referencia: p.referencia,
    valores: p.valores,
    brasil: p.brasil,
    intervalos: p.intervalos,
    estimados: p.estimados ?? m.estimados,
    // Ano que o IBGE já publicou: a soma do ano fecha com o oficial e não há faixa a mostrar.
    como_ler: semFaixa
      ? "Neste trimestre, a soma do ano já fecha com o PIB oficial do estado (IBGE); só a divisão entre os trimestres é estimada. Ponto vazado: estado sem IBC-R, repartido pelo índice da região."
      : m.como_ler,
  };
}

/** A lista "Trimestre"; some quando a métrica só tem um período. */
function controleDoTrimestre(
  id: string,
  aoMudar: () => void,
): { caixa: HTMLElement; pintar: (m: MetricaEstados | undefined) => void } {
  const lista = listaSuspensa(id, "Trimestre", [], "", (v) => {
    trimestre = v;
    aoMudar();
  });
  function pintar(m: MetricaEstados | undefined): void {
    const periodos = m?.periodos ?? [];
    lista.caixa.hidden = periodos.length < 2;
    if (!m || periodos.length < 2) return;
    lista.trocar(
      periodos.map((p) => ({ valor: p.referencia, rotulo: p.referencia })),
      periodoDe(m)?.referencia ?? "",
    );
  }
  return { caixa: lista.caixa, pintar };
}

/** As listas "Crescimento de" e "até"; somem quando a métrica não tem série. */
function controlesDaJanela(
  prefixo: string,
  aoMudar: () => void,
): { caixa: HTMLElement; pintar: (m: MetricaEstados | undefined) => void } {
  const caixa = el("div", "janela-pib");
  let atual: MetricaEstados | undefined;
  const de = listaSuspensa(`${prefixo}-de`, "Crescimento de", [], "", (v) => {
    if (!atual) return;
    const novo = Number(v);
    janela = { de: novo, ate: Math.max(janelaDe(atual).ate, novo + 1) };
    aoMudar();
  });
  const ate = listaSuspensa(`${prefixo}-ate`, "até", [], "", (v) => {
    if (!atual) return;
    const novo = Number(v);
    janela = { de: Math.min(janelaDe(atual).de, novo - 1), ate: novo };
    aoMudar();
  });
  caixa.append(de.caixa, ate.caixa);
  function pintar(m: MetricaEstados | undefined): void {
    atual = m;
    const anos = m ? anosDe(m) : [];
    caixa.hidden = !m || anos.length < 2;
    if (!m || anos.length < 2) return;
    const j = janelaDe(m);
    const rotulo = (a: number): string =>
      m.ano_previsto && a >= m.ano_previsto ? `${a} (prévia)` : String(a);
    de.trocar(
      anos.slice(0, -1).map((a) => ({ valor: String(a), rotulo: String(a) })),
      String(j.de),
    );
    ate.trocar(
      anos.slice(1).map((a) => ({ valor: String(a), rotulo: rotulo(a) })),
      String(j.ate),
    );
  }
  return { caixa, pintar };
}

// ------------------------------------------------------------------ mapa

function desenharMapa(alvo: HTMLElement, metrica: MetricaEstados, nomes: Map<string, string>): void {
  let largura = Math.max(260, Math.floor(alvo.clientWidth));
  // Em tela cheia, o mapa cabe também na altura.
  if (alvo.closest(".mapa-cheio")) {
    largura = Math.max(260, Math.min(largura, Math.floor(alvo.clientHeight / 0.98)));
  }
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
      `${nome}\n${metrica.marcas?.length ? `${metrica.unidade} ${escrito(metrica, v)}` : `${numero(v, metrica.casas)} ${metrica.unidade}`}` +
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
    return `${d.properties.uf}\n${escrito(metrica, v)}`;
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
  let escolhida = e.metricas[0] as MetricaEstados;
  let metrica = naJanela(escolhida, e.metricas);
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
    // Nota (a CAPAG) não vira eixo: seis degraus com nome, não uma régua.
    const numericas = opcoes.filter((o) => !e.metricas.find((m) => m.id === o.valor)?.marcas?.length);
    raiz.append(montarDispersao(e, nomes, numericas, corDestaque));
    return raiz;
  }
  if (parte === "limites") {
    raiz.append(montarLimites(e));
    return raiz;
  }

  // Visão geral (o mapa sozinho, menor) ou a parte "mapa" (mapa e ranking lado a lado).
  const comRanking = parte === "mapa";
  const barra = el("div", "barra-controles");
  const janelaMapa = controlesDaJanela("estados-janela", () => pintar());
  const trimestreMapa = controleDoTrimestre("estados-trimestre", () => pintar());
  barra.append(
    listaSuspensa("estados-metrica", "Métrica", opcoes, escolhida.id, (id) => {
      escolhida = e.metricas.find((m) => m.id === id) ?? escolhida;
      pintar();
    }).caixa,
    janelaMapa.caixa,
    trimestreMapa.caixa,
  );
  const sobre = el("p", "secao-resumo");
  const grade = el("div", comRanking ? "mundo-grade" : "estados-so-mapa");
  const painelMapa = el("div", "painel-mundo");
  const tituloMapa = el("h3");
  const subMapa = el("p", "sub");
  const tela = el("div", "mapa");
  const escala = el("div", "mapa-escala");
  const peMapa = el("footer", "grafico-pe");
  // Tela cheia (Caio, 14/11/2026: "o mapa também pode aumentar, se ela quiser ver só o mapa,
  // pode deixar cobrindo a tela"): o painel cobre a tela; Esc ou o botão fecham.
  const ampliar = el("button", "mapa-ampliar", "Tela cheia");
  ampliar.type = "button";
  ampliar.setAttribute("aria-pressed", "false");
  const topoMapa = el("div", "mapa-topo");
  const titulos = el("div");
  titulos.append(tituloMapa, subMapa);
  topoMapa.append(titulos, ampliar);
  const fecharComEsc = (ev: KeyboardEvent): void => {
    if (ev.key === "Escape") alternarTelaCheia(false);
  };
  function alternarTelaCheia(ligar: boolean): void {
    painelMapa.classList.toggle("mapa-cheio", ligar);
    document.documentElement.classList.toggle("sem-rolagem", ligar);
    ampliar.textContent = ligar ? "Fechar ✕" : "Tela cheia";
    ampliar.setAttribute("aria-pressed", String(ligar));
    if (ligar) document.addEventListener("keydown", fecharComEsc);
    else document.removeEventListener("keydown", fecharComEsc);
  }
  ampliar.addEventListener("click", () =>
    alternarTelaCheia(!painelMapa.classList.contains("mapa-cheio")),
  );
  // Ao trocar de tela, a rolagem volta.
  window.addEventListener("hashchange", () => alternarTelaCheia(false), { once: true });
  painelMapa.append(topoMapa, tela, escala, peMapa);
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
      texto: metrica.marcas?.length ? escrito(metrica, x.v) : undefined,
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
    if (metrica.conferencia) posicao.append(document.createTextNode(` ${metrica.conferencia}`));
    const semDado = e.ufs.filter((u) => (metrica.valores[u.sigla] ?? null) === null);
    if (semDado.length) {
      posicao.append(
        document.createTextNode(` Sem dado neste período: ${semDado.map((u) => u.sigla).join(", ")}.`),
      );
    }
  }

  function pintar(): void {
    metrica = noTrimestre(naJanela(escolhida, e.metricas));
    janelaMapa.pintar(escolhida);
    trimestreMapa.pintar(escolhida);
    sobre.textContent = metrica.descricao;
    tituloMapa.textContent = metrica.nome;
    // O texto mudou: o glossário marca de novo (o "?" do título, o sublinhado da descrição).
    remarcar(sobre);
    remarcar(painelMapa);
    subMapa.textContent = `${metrica.unidade} · ${metrica.referencia}`;
    const valores = Object.values(metrica.valores).filter((v): v is number => v !== null);
    if (tela.clientWidth) desenharMapa(tela, metrica, nomes);
    escala.replaceChildren(
      el("span", "", escrito(metrica, Math.min(...valores))),
      el("i"),
      el("span", "", escrito(metrica, Math.max(...valores))),
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
  const regiaoDe = (uf: string): Regiao | undefined => {
    const nome = e.ufs.find((u) => u.sigla === uf)?.regiao;
    return nome ? { nome, ufs: new Set(e.ufs.filter((u) => u.regiao === nome).map((u) => u.sigla)) } : undefined;
  };
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
          ? montarFicha(c, todas, regiaoDe(uf))
          : [el("p", "sub", "As contas deste estado não vieram nesta rodada.")]),
      );
    });
  }
  abrir(e.ufs.some((u) => u.sigla === ufInicial) ? ufInicial : "");
  return painel;
}

// ------------------------------------------------------------------ perto dos limites

interface Situacao {
  grau: number;
  diz: string;
}

/** Onde o valor está entre os degraus (do mais alto ao mais baixo): o grau e a frase. */
function situacao(v: number | null, degraus: { valor?: number; diz: string; grau: number }[]): Situacao {
  if (v === null) return { grau: 0, diz: "" };
  for (const d of degraus) if (d.valor !== undefined && v > d.valor) return { grau: d.grau, diz: d.diz };
  return { grau: 0, diz: "" };
}

/** Uma linha da tabela dos limites: o ente (estado ou capital) e onde o nome leva. */
interface Ente {
  sigla: string;
  nome: string;
  href?: string;
}

/** Uma coluna a mais, depois de pessoal e dívida (CAPAG, acordo da dívida, primário). */
interface ColunaExtra {
  titulo: string;
  sub: string;
  texto: (sigla: string) => string;
  /** Classe da célula (a nota fraca em cor); vazio quando nada a destacar. */
  classe?: (sigla: string) => string;
  /** Peso a mais na ordem (a nota fraca sobe na lista). */
  peso?: (sigla: string) => number;
}

/** Pessoal e dívida contra os limites da lei (que vêm nas próprias métricas), mais as
 * colunas extras: quem passou de algum alerta primeiro. */
function tabelaDeLimites(
  entes: Ente[],
  pessoal: MetricaEstados,
  divida: MetricaEstados,
  extras: ColunaExtra[],
  primeiraColuna: string,
): { tabela: HTMLTableElement; acima: number } {
  const limite = (m: MetricaEstados, rotulo: string): number | undefined =>
    m.limites.find((l) => l.rotulo === rotulo)?.valor;
  const degrausPessoal = [
    { valor: limite(pessoal, "limite máximo"), diz: "acima do máximo", grau: 3 },
    { valor: limite(pessoal, "limite prudencial"), diz: "acima do prudencial", grau: 2 },
    { valor: limite(pessoal, "limite de alerta"), diz: "acima do alerta", grau: 1 },
  ];
  const degrausDivida = [
    { valor: limite(divida, "limite"), diz: "acima do limite", grau: 3 },
    { valor: limite(divida, "limite de alerta"), diz: "acima do alerta", grau: 1 },
  ];
  const linhas = entes.map((u) => {
    const p = pessoal.valores[u.sigla] ?? null;
    const d = divida.valores[u.sigla] ?? null;
    const sp = situacao(p, degrausPessoal);
    const sd = situacao(d, degrausDivida);
    const peso = extras.reduce((a, c) => a + (c.peso?.(u.sigla) ?? 0), 0);
    return { u, p, d, sp, sd, peso };
  });
  linhas.sort(
    (a, b) =>
      Math.max(b.sp.grau, b.sd.grau) - Math.max(a.sp.grau, a.sd.grau) ||
      b.sp.grau + b.sd.grau + b.peso - (a.sp.grau + a.sd.grau + a.peso) ||
      (b.p ?? 0) - (a.p ?? 0),
  );
  const tabela = el("table", "dados limites-tabela");
  const cab = tabela.createTHead().insertRow();
  const colunas: [string, string][] = [
    [primeiraColuna, ""],
    ["Pessoal", "% da RCL"],
    ["Dívida", "% da RCL"],
    ...extras.map((c): [string, string] => [c.titulo, c.sub]),
  ];
  for (const [nome, sub] of colunas) {
    const th = el("th", "", nome);
    if (sub) th.append(el("span", "sub", ` ${sub}`));
    cab.append(th);
  }
  const corpo = tabela.createTBody();
  const celula = (v: number | null, s: Situacao, m: MetricaEstados): HTMLElement => {
    const td = el("td");
    if (v === null) {
      td.textContent = "–";
      return td;
    }
    // Sem "−0,0": o que arredonda a zero sai zero.
    td.append(document.createTextNode(numero(Math.abs(v) < 0.05 ? 0 : v, m.casas)));
    if (s.diz) td.append(el("span", `limite-diz grau-${s.grau}`, s.diz));
    return td;
  };
  for (const x of linhas) {
    const tr = corpo.insertRow();
    const th = el("th");
    if (x.u.href) {
      const a = el("a", "", x.u.nome);
      a.href = x.u.href;
      th.append(a);
    } else {
      th.textContent = x.u.nome;
    }
    protegerNomeDeEstado(th, x.u.nome);
    tr.append(th, celula(x.p, x.sp, pessoal), celula(x.d, x.sd, divida));
    for (const c of extras) {
      const td = el("td", c.classe?.(x.u.sigla) ?? "", c.texto(x.u.sigla));
      tr.append(td);
    }
  }
  return { tabela, acima: linhas.filter((x) => x.sp.grau || x.sd.grau).length };
}

const limitesEmTexto = (m: MetricaEstados): string =>
  m.limites.map((l) => `${l.rotulo} ${numero(l.valor, String(l.valor).split(".")[1]?.length ?? 0)} %`).join(", ");

/** Os 27 estados contra os limites de pessoal e de dívida, com a CAPAG e o acordo da dívida. */
function limitesDosEstados(e: Estados): HTMLElement {
  const caixa = el("div");
  const achar = (id: string): MetricaEstados | undefined => e.metricas.find((m) => m.id === id);
  const pessoal = achar("pessoal");
  const divida = achar("divida");
  const capag = achar("capag");
  const acordo = achar("acordo_divida");
  if (!pessoal || !divida) {
    caixa.append(el("p", "vazio", "Os relatórios fiscais dos estados não vieram nesta rodada."));
    return caixa;
  }
  const notaFraca = capag?.marcas?.find((m) => m.rotulo === "C")?.valor ?? 0;
  const fraca = (s: string): boolean => {
    const n = capag?.valores[s] ?? null;
    return n !== null && n <= notaFraca;
  };
  const extras: ColunaExtra[] = [];
  if (capag) {
    extras.push({
      titulo: "CAPAG",
      sub: "",
      texto: (s) => {
        const n = capag.valores[s] ?? null;
        return n === null ? "–" : escrito(capag, n);
      },
      classe: (s) => (fraca(s) ? "nota-fraca" : ""),
      peso: (s) => Number(fraca(s)),
    });
  }
  if (acordo) {
    extras.push({
      titulo: "Acordo",
      sub: "com a União",
      texto: (s) => {
        const n = acordo.valores[s] ?? null;
        const nome = n === null ? "" : escrito(acordo, n);
        return !nome || nome === "Nenhum" ? "–" : nome;
      },
    });
  }
  const { tabela, acima } = tabelaDeLimites(
    e.ufs.map((u) => ({ sigla: u.sigla, nome: u.nome, href: e.arquivo_contas ? `#estados/uf-${u.sigla}` : undefined })),
    pessoal,
    divida,
    extras,
    "Estado",
  );
  const fracas = e.ufs.filter((u) => fraca(u.sigla)).length;
  caixa.append(
    el("h3", "", "Os estados contra os limites da lei"),
    el(
      "p",
      "sub",
      `${acima} de ${e.ufs.length} estados acima de algum alerta` +
        (capag ? `; ${fracas} com nota CAPAG C ou D.` : ".") +
        ` Pessoal e dívida: RGF do ${pessoal.referencia}.` +
        (capag ? ` CAPAG: ${capag.referencia}.` : ""),
    ),
  );
  // A tabela inteira à vista: são 27 linhas, e quem está bem também conta.
  const rolavel = el("div", "tabela-rolavel inteira");
  rolavel.append(tabela);
  const pe = el("footer", "grafico-pe");
  const fontes = [pessoal.fonte, divida.fonte, ...(capag ? [capag.fonte] : []), ...(acordo ? [acordo.fonte] : [])];
  pe.append(el("span", "fonte", `Fontes: ${fontes.join("; ")}.`));
  caixa.append(
    rolavel,
    pe,
    el(
      "p",
      "nota",
      `Limites da lei, em % da receita corrente líquida. Pessoal do Poder Executivo: ${limitesEmTexto(pessoal)}. ` +
        `Dívida: ${limitesEmTexto(divida)}.` +
        (acordo
          ? ` Acordo: RRF é o Regime de Recuperação Fiscal; Propag, o programa de 2025 que refinancia a dívida em 30 anos (${acordo.referencia}).`
          : "") +
        (e.arquivo_contas ? " Toque no nome para abrir as contas do estado." : ""),
    ),
  );
  return caixa;
}

/** As capitais contra os limites da lei para os municípios, com o resultado primário. */
function limitesDasCapitais(e: Estados): HTMLElement {
  const caixa = el("div");
  const c = e.capitais;
  const achar = (id: string): MetricaEstados | undefined => c?.metricas.find((m) => m.id === id);
  const pessoal = achar("pessoal");
  const divida = achar("divida");
  const primario = achar("primario");
  if (!c || !pessoal || !divida) {
    caixa.append(el("p", "vazio", "Os relatórios fiscais das capitais não vieram nesta rodada."));
    return caixa;
  }
  const extras: ColunaExtra[] = [];
  if (primario) {
    extras.push({
      titulo: "Primário",
      sub: `% da RCL, ${primario.referencia}`,
      texto: (s) => {
        const v = primario.valores[s] ?? null;
        return v === null ? "–" : numero(Math.abs(v) < 0.05 ? 0 : v, primario.casas);
      },
      classe: (s) => ((primario.valores[s] ?? 0) < 0 ? "deficit" : ""),
    });
  }
  const entes = Object.entries(c.nomes)
    .map(([sigla, nome]) => ({ sigla, nome: `${nome} (${sigla})` }))
    .sort((a, b) => a.nome.localeCompare(b.nome));
  const { tabela, acima } = tabelaDeLimites(entes, pessoal, divida, extras, "Capital");
  const semRelatorio = entes.filter(
    (x) => (pessoal.valores[x.sigla] ?? null) === null && (divida.valores[x.sigla] ?? null) === null,
  );
  caixa.append(
    el("h3", "", "As capitais contra os limites da lei"),
    el(
      "p",
      "sub",
      `${acima} de ${entes.length - semRelatorio.length} capitais com relatório acima de algum alerta. ` +
        `Pessoal e dívida: RGF do ${pessoal.referencia}.` +
        (primario ? ` Primário: ${primario.referencia}.` : "") +
        (semRelatorio.length
          ? ` Sem relatório do período: ${semRelatorio.map((x) => x.nome).join(", ")}.`
          : ""),
    ),
  );
  const rolavel = el("div", "tabela-rolavel inteira");
  rolavel.append(tabela);
  const pe = el("footer", "grafico-pe");
  const fontes = [pessoal.fonte, divida.fonte, ...(primario ? [primario.fonte] : [])];
  pe.append(el("span", "fonte", `Fontes: ${fontes.join("; ")}.`));
  caixa.append(
    rolavel,
    pe,
    el(
      "p",
      "nota",
      `Limites da lei para os municípios, em % da receita corrente líquida. Pessoal do Poder Executivo: ${limitesEmTexto(pessoal)}. ` +
        `Dívida: ${limitesEmTexto(divida)}. Primário: receitas menos despesas sem os juros, no ano até o bimestre; negativo é déficit. ` +
        "Brasília fica de fora: o Distrito Federal presta contas como estado.",
    ),
  );
  return caixa;
}

/** Estados e capitais contra os limites, um de cada vez (as abas em cima). */
function montarLimites(e: Estados): HTMLElement {
  const painel = el("div", "painel-mundo limites");
  const abas: { nome: string; montar: () => HTMLElement }[] = [{ nome: "Estados", montar: () => limitesDosEstados(e) }];
  if (e.capitais?.metricas.length) abas.push({ nome: "Capitais", montar: () => limitesDasCapitais(e) });
  const palco = el("div");
  if (abas.length > 1) {
    const barra = el("div", "ficha-abas limites-abas");
    barra.setAttribute("role", "tablist");
    barra.setAttribute("aria-label", "Estados ou capitais");
    const botoes = abas.map((a, i) => {
      const b = el("button", "pilula", a.nome);
      b.type = "button";
      b.setAttribute("role", "tab");
      b.addEventListener("click", () => mostrar(i));
      barra.append(b);
      return b;
    });
    const mostrar = (i: number): void => {
      botoes.forEach((b, k) => {
        b.setAttribute("aria-selected", String(k === i));
        b.classList.toggle("atual", k === i);
      });
      palco.replaceChildren(abas[i]?.montar() ?? el("div"));
      remarcar(palco);
    };
    painel.append(barra, palco);
    mostrar(0);
  } else {
    painel.append(palco);
    palco.append(limitesDosEstados(e));
    remarcar(palco);
  }
  return painel;
}

// ------------------------------------------------------------------ tabela completa

const CHAVE_COLUNAS = "sacibras.estados.colunas";

/** As colunas guardadas no navegador (conveniência; sem ele, vale o padrão). */
function colunasGuardadas(): string[] | null {
  try {
    const bruto = localStorage.getItem(CHAVE_COLUNAS);
    const lido: unknown = bruto ? JSON.parse(bruto) : null;
    return Array.isArray(lido) ? lido.filter((x): x is string => typeof x === "string") : null;
  } catch {
    return null;
  }
}

function guardarColunas(ids: string[]): void {
  try {
    localStorage.setItem(CHAVE_COLUNAS, JSON.stringify(ids));
  } catch {
    /* sem armazenamento: só não lembra */
  }
}

/** As métricas lado a lado, agrupadas por região. A pessoa escolhe as colunas (Caio,
 * 14/11/2026: "deixe parâmetros na tabela pra ela escolher oq quer ver"); abre com a
 * primeira métrica de cada assunto. As fontes ficam dobradas embaixo. */
function tabelaCompleta(e: Estados): HTMLElement {
  const caixa = el("div", "painel-mundo tabela-estados");
  const ids = new Set(e.metricas.map((m) => m.id));
  const padrao = e.metricas
    .filter((m, i) => i === 0 || m.grupo !== e.metricas[i - 1]?.grupo)
    .map((m) => m.id);
  const guardadas = colunasGuardadas()?.filter((id) => ids.has(id));
  const visiveis = new Set(guardadas?.length ? guardadas : padrao);

  // Escolha das colunas: caixas de marcar por assunto, dentro de "Escolher colunas".
  const escolha = el("details", "colunas-escolha");
  const resumo = el("summary");
  const marcas = el("div", "colunas-grupos");
  escolha.append(resumo, marcas);
  const grupos = new Map<string, MetricaEstados[]>();
  for (const m of e.metricas) {
    const g = m.grupo ?? "";
    grupos.set(g, [...(grupos.get(g) ?? []), m]);
  }
  const caixasDeMarcar: HTMLInputElement[] = [];
  for (const [grupo, ms] of grupos) {
    const bloco = el("fieldset", "colunas-grupo");
    bloco.append(el("legend", "", grupo || "Outras"));
    for (const m of ms) {
      const rotulo = el("label", "coluna-marca");
      const marca = el("input");
      marca.type = "checkbox";
      marca.value = m.id;
      marca.checked = visiveis.has(m.id);
      marca.addEventListener("change", () => {
        if (marca.checked) visiveis.add(m.id);
        else visiveis.delete(m.id);
        guardarColunas([...visiveis]);
        pintar();
      });
      caixasDeMarcar.push(marca);
      rotulo.append(marca, document.createTextNode(` ${m.nome}`));
      bloco.append(rotulo);
    }
    marcas.append(bloco);
  }
  const atalhos = el("div", "colunas-atalhos");
  const atalho = (texto: string, quais: () => string[]): HTMLButtonElement => {
    const b = el("button", "botao-texto", texto);
    b.type = "button";
    b.addEventListener("click", () => {
      visiveis.clear();
      for (const id of quais()) visiveis.add(id);
      for (const c of caixasDeMarcar) c.checked = visiveis.has(c.value);
      guardarColunas([...visiveis]);
      pintar();
    });
    return b;
  };
  atalhos.append(
    atalho("Todas", () => [...ids]),
    atalho("Só o essencial", () => padrao),
    atalho("Nenhuma", () => []),
  );
  marcas.append(atalhos);

  const barra = el("div", "barra-controles");
  const janelaTabela = controlesDaJanela("tabela-janela", () => pintar());
  barra.append(escolha, janelaTabela.caixa);

  const rolavel = el("div", "tabela-rolavel");
  const fontes = el("details", "fontes-dobradas");
  caixa.append(barra, rolavel, fontes);

  function pintar(): void {
    const ms = e.metricas.filter((m) => visiveis.has(m.id)).map((m) => naJanela(m, e.metricas));
    resumo.textContent = `Escolher colunas (${ms.length} de ${e.metricas.length})`;
    janelaTabela.pintar(e.metricas.find((m) => visiveis.has(m.id) && m.anuais));
    if (!ms.length) {
      rolavel.replaceChildren(el("p", "vazio", "Nenhuma coluna escolhida."));
      fontes.replaceChildren();
      fontes.hidden = true;
      return;
    }
    rolavel.replaceChildren(montarTabela(e, ms));
    remarcar(rolavel);
    const lista = [...new Set(ms.map((m) => m.fonte))];
    const ul = el("ul");
    for (const f of lista) ul.append(el("li", "", f));
    fontes.hidden = false;
    fontes.replaceChildren(el("summary", "", `Fontes (${lista.length})`), ul);
  }
  pintar();
  return caixa;
}

function montarTabela(e: Estados, metricas: MetricaEstados[]): HTMLTableElement {
  const tabela = el("table", "dados larga");
  const cabeca = tabela.createTHead();
  // Uma linha com o assunto de cada bloco de colunas (Economia, Trabalho e renda…).
  if (metricas.some((m) => m.grupo)) {
    const grupos = cabeca.insertRow();
    grupos.className = "grupos";
    grupos.append(el("th"));
    for (const m of metricas) {
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
  for (const m of metricas) {
    const th = el("th", "", m.nome);
    th.append(el("span", "sub", ` ${m.unidade} · ${m.referencia}`));
    th.title = `${m.unidade} · ${m.referencia}`;
    cab.append(th);
  }
  const corpo = tabela.createTBody();
  for (const regiao of ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]) {
    const tr = corpo.insertRow();
    tr.className = "grupo";
    const th = el("th", "", regiao);
    th.colSpan = metricas.length + 1;
    tr.append(th);
    for (const u of e.ufs.filter((x) => x.regiao === regiao)) {
      const linha = corpo.insertRow();
      const nome = el("th", "", u.nome);
      protegerNomeDeEstado(nome, u.nome);
      linha.append(nome);
      for (const m of metricas) {
        const v = m.valores[u.sigla] ?? null;
        const td = el("td", "", v === null ? "–" : escrito(m, v));
        if (v !== null && m.estimados?.includes(u.sigla)) {
          td.title = "estimado pela região";
          td.append(el("sup", "", "*"));
        }
        linha.append(td);
      }
    }
  }
  const brasil = corpo.insertRow();
  brasil.className = "brasil";
  brasil.append(el("th", "", "Brasil"));
  for (const m of metricas) {
    brasil.append(el("td", "", m.brasil === null ? "–" : escrito(m, m.brasil)));
  }
  if (metricas.some((m) => m.estimados?.length)) {
    const nota = tabela.createTFoot().insertRow();
    const td = el("td", "nota-tabela", "* Estimado pela região (estado sem IBC-R).");
    td.colSpan = metricas.length + 1;
    nota.append(td);
  }
  return tabela;
}
