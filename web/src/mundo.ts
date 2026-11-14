// Brasil no mundo: a mesma métrica para vários países.
//   1. o ranking do ano, em pontos; tocar num país o põe no gráfico ao lado, tocar num grupo
//      (Emergentes, Avançados…) abre os países dele;
//   2. a trajetória dos países escolhidos, com as projeções do FMI;
//   3. duas métricas ao mesmo tempo, um ponto por país;
//   4. a tabela com tudo, guardada.

import { numero } from "./formato";
import { montarGrafico } from "./grafico";
import { el, guardar } from "./pecas";
import {
  desenharDispersao,
  linhaDoRanking,
  listaSuspensa,
  reguaDe,
  type Opcao,
  type PontoDisperso,
} from "./pontos";
import type { Grafico, GrupoMundo, MetricaMundo, Mundo, MundoPaises, Pais } from "./tipos";

const GRUPOS_DA_TABELA: [Pais["grupo"], string][] = [
  ["america_latina", "América Latina"],
  ["emergentes", "Outros emergentes"],
  ["avancados", "Avançados"],
  ["agregado", "Grupos"],
];

const INICIAIS = ["BRA", "MEX", "CHL", "USA"];
const MAXIMO = 6;
// Os pares que abrem o gráfico de duas métricas.
const EIXO_X = "inflacao";
const EIXO_Y = "juro";

function cor(casa: number): string {
  return getComputedStyle(document.documentElement).getPropertyValue(`--serie-${casa + 1}`).trim();
}

export function montarMundo(m: Mundo): HTMLElement {
  const raiz = el("div");
  const principais = new Map(m.paises.map((p) => [p.iso3, p]));
  const nomeDe = (iso: string): string => principais.get(iso)?.nome ?? m.nomes[iso] ?? iso;
  const grupoDe = new Map<string, GrupoMundo>(m.grupos.map((g) => [g.iso3, g]));
  let metrica = m.metricas[0] as MetricaMundo;
  let ano = m.ano_corrente;
  const abertos = new Set<string>();
  let todos: MundoPaises | null = null;
  let carregando: Promise<void> | null = null;

  // país → casa da paleta. O Brasil é sempre a casa 0 (verde); os outros pegam a casa livre e
  // a mantêm enquanto estiverem escolhidos: a cor segue o país, não a ordem.
  const casas = new Map<string, number>();
  INICIAIS.filter((i) => principais.has(i)).forEach((iso, i) => casas.set(iso, i));

  const projetado = (mt: MetricaMundo, a: number): boolean =>
    mt.primeiro_ano_projetado !== null && a >= mt.primeiro_ano_projetado;

  /** O valor de um país num ano: dos principais, ou do arquivo de todos os países. */
  const valor = (mt: MetricaMundo, iso: string, a: number): number | null => {
    const i = mt.anos.indexOf(a);
    const v = i < 0 ? undefined : mt.valores[iso]?.[i];
    if (v !== undefined && v !== null) return v;
    const daLista = todos?.metricas.find((x) => x.id === mt.id);
    if (!daLista) return null;
    const j = daLista.anos.indexOf(a);
    return j < 0 ? null : (daLista.valores[iso]?.[j] ?? null);
  };

  const carregarTodos = (): Promise<void> => {
    if (todos || !m.arquivo_paises) return Promise.resolve();
    carregando ??= fetch(`data/${m.arquivo_paises}`)
      .then((r) => (r.ok ? (r.json() as Promise<MundoPaises>) : null))
      .then((d) => {
        todos = d;
      })
      .catch(() => undefined);
    return carregando;
  };

  // ---------------------------------------------------------------- controles
  const anosDe = (mt: MetricaMundo): Opcao[] =>
    mt.anos
      .filter((a) => a >= m.ano_corrente - 10 && mt.anos.includes(a))
      .reverse()
      .map((a) => ({ valor: String(a), rotulo: projetado(mt, a) ? `${a} (projeção do FMI)` : String(a) }));
  const barra = el("div", "barra-controles");
  const escolhaMetrica = listaSuspensa(
    "mundo-metrica",
    "Métrica",
    m.metricas.map((mt) => ({ valor: mt.id, rotulo: mt.nome })),
    metrica.id,
    (id) => {
      metrica = m.metricas.find((x) => x.id === id) ?? metrica;
      if (!metrica.anos.includes(ano)) ano = Math.min(m.ano_corrente, Math.max(...metrica.anos));
      escolhaAno.trocar(anosDe(metrica), String(ano));
      pintar();
    },
  );
  const escolhaAno = listaSuspensa("mundo-ano", "Ano", anosDe(metrica), String(ano), (a) => {
    ano = Number(a);
    pintar();
  });
  barra.append(escolhaMetrica.caixa, escolhaAno.caixa);
  const sobre = el("p", "secao-resumo");

  // ---------------------------------------------------------------- ranking e trajetória
  const grade = el("div", "mundo-grade");
  const painelRanking = el("div", "painel-mundo");
  const tituloRanking = el("h3");
  const subRanking = el("p", "sub");
  const ranking = el("div", "ranking-pontos");
  const posicao = el("p", "posicao");
  const tituloGrupos = el("h4", "subtitulo-lista", "Grupos de países");
  const subGrupos = el("p", "sub", "Média do FMI para o grupo. Toque num grupo para ver os países dele.");
  const rankingGrupos = el("div", "ranking-pontos");
  const fonteRanking = el("footer", "grafico-pe");
  painelRanking.append(
    tituloRanking,
    subRanking,
    ranking,
    posicao,
    tituloGrupos,
    subGrupos,
    rankingGrupos,
    fonteRanking,
  );

  const ladoLinha = el("div", "lado-trajetoria");
  const escolhidos = el("div", "escolhidos");
  const caixaGrafico = el("div");
  ladoLinha.append(escolhidos, caixaGrafico);
  grade.append(painelRanking, ladoLinha);

  // ---------------------------------------------------------------- duas métricas
  const painelDispersao = el("div", "painel-mundo dispersao-painel");
  painelDispersao.append(
    el("h3", "", "Duas métricas ao mesmo tempo"),
    el("p", "sub", "Um ponto por país, no ano escolhido. Toque num ponto para ver os números."),
  );
  let eixoX = m.metricas.find((x) => x.id === EIXO_X) ?? (m.metricas[0] as MetricaMundo);
  let eixoY = m.metricas.find((x) => x.id === EIXO_Y) ?? (m.metricas[1] as MetricaMundo);
  let grupoNaDispersao = "";
  const opcoesMetricas = m.metricas.map((mt) => ({ valor: mt.id, rotulo: mt.nome }));
  const barraDispersao = el("div", "barra-controles");
  barraDispersao.append(
    listaSuspensa("mundo-x", "Na horizontal", opcoesMetricas, eixoX.id, (id) => {
      eixoX = m.metricas.find((x) => x.id === id) ?? eixoX;
      pintarDispersao();
    }).caixa,
    listaSuspensa("mundo-y", "Na vertical", opcoesMetricas, eixoY.id, (id) => {
      eixoY = m.metricas.find((x) => x.id === id) ?? eixoY;
      pintarDispersao();
    }).caixa,
    listaSuspensa(
      "mundo-grupo",
      "Incluir os países de",
      [{ valor: "", rotulo: "nenhum grupo" }, ...m.grupos.map((g) => ({ valor: g.iso3, rotulo: g.nome }))],
      "",
      (g) => {
        grupoNaDispersao = g;
        void carregarTodos().then(pintarDispersao);
      },
    ).caixa,
  );
  const legendaDispersao = el("div", "legenda");
  const telaDispersao = el("div", "tela-dispersao");
  const notaDispersao = el("p", "posicao");
  let comExtremos = false;
  const peDispersao = el("footer", "grafico-pe");
  painelDispersao.append(barraDispersao, legendaDispersao, telaDispersao, notaDispersao, peDispersao);

  const caixaTabela = el("div");
  raiz.append(barra, sobre, grade, painelDispersao, caixaTabela);

  // ---------------------------------------------------------------- ranking
  function alternarPais(iso: string): void {
    if (iso === "BRA") return;
    if (casas.has(iso)) casas.delete(iso);
    else {
      if (casas.size >= MAXIMO) return;
      const usadas = new Set(casas.values());
      let livre = 0;
      while (usadas.has(livre)) livre += 1;
      casas.set(iso, livre);
    }
    pintarRanking();
    pintarEscolhidos();
    pintarLinha();
    pintarDispersao();
  }

  function pintarRanking(): void {
    const proj = projetado(metrica, ano);
    tituloRanking.textContent = `${metrica.nome} em ${ano}${proj ? " (projeção)" : ""}`;
    subRanking.textContent = `${metrica.unidade} · toque num país para pô-lo no gráfico ao lado`;
    const comValor = m.paises
      .map((p) => ({ p, v: valor(metrica, p.iso3, ano) }))
      .filter((x): x is { p: Pais; v: number } => x.v !== null)
      .sort((a, b) => b.v - a.v);
    const paises = comValor.filter((x) => x.p.grupo !== "agregado");
    const grupos = comValor.filter((x) => x.p.grupo === "agregado");
    // Uma régua só para países e grupos: o mesmo valor fica no mesmo lugar nas duas listas.
    const regua = reguaDe(comValor.map((x) => x.v));
    ranking.replaceChildren(
      ...paises.map(({ p, v }, i) => {
        const casa = casas.get(p.iso3);
        return linhaDoRanking(
          {
            chave: p.iso3,
            nome: p.nome,
            valor: v,
            marca: p.iso3 === "BRA" ? "brasil" : "comum",
            posicao: i + 1,
            cor: casa !== undefined && p.iso3 !== "BRA" ? cor(casa) : undefined,
            dica: `${p.nome}: ${numero(v, metrica.casas)} ${metrica.unidade}`,
          },
          regua,
          metrica.casas,
          () => alternarPais(p.iso3),
        );
      }),
    );
    rankingGrupos.replaceChildren();
    for (const { p, v } of grupos) {
      const grupo = grupoDe.get(p.iso3);
      const abre = Boolean(grupo && m.arquivo_paises);
      rankingGrupos.append(
        linhaDoRanking(
          {
            chave: p.iso3,
            nome: p.nome,
            valor: v,
            marca: "grupo",
            posicao: null,
            abre: grupo && abre ? { aberto: abertos.has(p.iso3), quantos: grupo.membros.length } : undefined,
            dica: `${p.nome}: ${numero(v, metrica.casas)} ${metrica.unidade}`,
          },
          regua,
          metrica.casas,
          abre
            ? () => {
                if (abertos.has(p.iso3)) abertos.delete(p.iso3);
                else abertos.add(p.iso3);
                void carregarTodos().then(pintarRanking);
              }
            : undefined,
        ),
      );
      if (grupo && abertos.has(p.iso3)) rankingGrupos.append(membrosDoGrupo(grupo, regua));
    }
    tituloGrupos.hidden = subGrupos.hidden = grupos.length === 0;
    posicao.replaceChildren();
    const lugarBrasil = paises.findIndex((x) => x.p.iso3 === "BRA") + 1;
    const vBrasil = valor(metrica, "BRA", ano);
    if (lugarBrasil && vBrasil !== null) {
      posicao.append(
        document.createTextNode("Brasil: "),
        el("b", "", `${numero(vBrasil, metrica.casas)} ${metrica.unidade}`),
        document.createTextNode(`, o ${lugarBrasil}º maior entre ${paises.length} países.`),
      );
      const mundo = valor(metrica, "G001", ano);
      if (mundo !== null) posicao.append(document.createTextNode(` Mundo: ${numero(mundo, metrica.casas)}.`));
    }
    fonteRanking.replaceChildren(el("span", "fonte", `Fonte: ${metrica.fonte}`));
  }

  /** Os países de um grupo, ordenados, numa caixa que rola. */
  function membrosDoGrupo(grupo: GrupoMundo, regua: ReturnType<typeof reguaDe>): HTMLElement {
    const caixa = el("div", "ponto-membros");
    if (!todos) {
      caixa.append(el("p", "posicao", carregando ? "Carregando os países…" : "Sem a lista de países nesta rodada."));
      return caixa;
    }
    const membros = grupo.membros
      .map((iso) => ({ iso, v: valor(metrica, iso, ano) }))
      .filter((x): x is { iso: string; v: number } => x.v !== null)
      .sort((a, b) => b.v - a.v);
    const sem = grupo.membros.length - membros.length;
    caixa.append(
      el(
        "p",
        "ponto-membros-titulo",
        `${grupo.nome}: ${membros.length} países com dado${sem ? ` (${sem} sem)` : ""}. Pontos fora da régua ficam na ponta, com o valor ao lado.`,
      ),
    );
    membros.forEach(({ iso, v }, i) => {
      const casa = casas.get(iso);
      caixa.append(
        linhaDoRanking(
          {
            chave: iso,
            nome: nomeDe(iso),
            valor: v,
            marca: iso === "BRA" ? "brasil" : "membro",
            posicao: i + 1,
            cor: casa !== undefined && iso !== "BRA" ? cor(casa) : undefined,
          },
          regua,
          metrica.casas,
          () => alternarPais(iso),
        ),
      );
    });
    return caixa;
  }

  // ---------------------------------------------------------------- trajetória
  function pintarEscolhidos(): void {
    escolhidos.replaceChildren();
    const ordenados = [...casas.entries()].sort((a, b) => a[1] - b[1]);
    for (const [iso, casa] of ordenados) {
      const ficha = el("button", "ficha pais escolhida");
      ficha.type = "button";
      ficha.style.setProperty("--cor", cor(casa));
      ficha.append(el("i"), document.createTextNode(nomeDe(iso)));
      if (iso === "BRA") ficha.disabled = true;
      else {
        ficha.append(el("span", "tirar", "×"));
        ficha.setAttribute("aria-label", `Tirar ${nomeDe(iso)} do gráfico`);
        ficha.addEventListener("click", () => alternarPais(iso));
      }
      escolhidos.append(ficha);
    }
    const disponiveis = [...m.paises.map((p) => p.iso3)].filter((iso) => !casas.has(iso));
    if (casas.size < MAXIMO && disponiveis.length) {
      const adicionar = listaSuspensa(
        "mundo-adicionar",
        "",
        [
          { valor: "", rotulo: "+ Adicionar país ou grupo" },
          ...disponiveis.map((iso) => ({ valor: iso, rotulo: nomeDe(iso) })),
        ],
        "",
        (iso) => {
          if (iso) alternarPais(iso);
        },
      );
      adicionar.caixa.classList.add("adicionar");
      escolhidos.append(adicionar.caixa);
    }
  }

  function pintarLinha(): void {
    const corte = metrica.primeiro_ano_projetado;
    const ordenados = [...casas.entries()].sort((a, b) => a[1] - b[1]);
    const serieDe = (iso: string): [string, number | null][] => {
      const proprio = metrica.valores[iso];
      if (proprio) return metrica.anos.map((a, i) => [`${a}-01-01`, proprio[i] ?? null]);
      const daLista = todos?.metricas.find((x) => x.id === metrica.id);
      const outro = daLista?.valores[iso];
      return daLista && outro ? daLista.anos.map((a, i) => [`${a}-01-01`, outro[i] ?? null]) : [];
    };
    const g: Grafico = {
      id: `mundo-${metrica.id}`,
      titulo: `${metrica.nome}: o Brasil e os escolhidos`,
      subtitulo: corte ? `tracejado: projeção do FMI a partir de ${corte}` : "",
      tipo: "linha",
      unidade: metrica.unidade,
      casas: metrica.casas,
      periodicidade: "A",
      series: ordenados.map(([iso, casa]) => ({
        id: iso,
        nome: nomeDe(iso),
        papel: "realizado" as const,
        tracejado_desde: corte ? `${corte}-01-01` : null,
        cor: casa,
        pontos: serieDe(iso),
      })),
      faixa: null,
      intervalos: [],
      linhas: [],
      janela_anos: 20,
      fonte: metrica.fonte,
      nota: "",
      largura: "inteira",
    };
    caixaGrafico.replaceChildren(montarGrafico(g));
  }

  // ---------------------------------------------------------------- duas métricas
  function pintarDispersao(): void {
    const pontos: PontoDisperso[] = [];
    const vistos = new Set<string>();
    const incluir = (iso: string, marca: PontoDisperso["marca"]): void => {
      if (vistos.has(iso)) return;
      const x = valor(eixoX, iso, ano);
      const y = valor(eixoY, iso, ano);
      if (x === null || y === null) return;
      vistos.add(iso);
      const casa = casas.get(iso);
      pontos.push({
        chave: iso,
        nome: nomeDe(iso),
        x,
        y,
        marca: iso === "BRA" ? "brasil" : marca,
        cor: casa !== undefined && iso !== "BRA" ? cor(casa) : undefined,
        rotulo: iso === "BRA" || casa !== undefined,
      });
    };
    incluir("BRA", "brasil");
    for (const p of m.paises) if (p.grupo !== "agregado") incluir(p.iso3, "comum");
    const grupo = grupoDe.get(grupoNaDispersao);
    if (grupo) for (const iso of grupo.membros) incluir(iso, "membro");
    telaDispersao.dataset.vazio = String(pontos.length < 3);
    const ex = { nome: eixoX.nome, unidade: eixoX.unidade, casas: eixoX.casas };
    const ey = { nome: eixoY.nome, unidade: eixoY.unidade, casas: eixoY.casas };
    const aoTocar = (iso: string): void => {
      if (principais.has(iso)) alternarPais(iso);
    };
    // Quem é quem: o Brasil e os escolhidos numa legenda, em vez de rótulos que encavalam.
    legendaDispersao.replaceChildren(
      ...pontos
        .filter((p) => p.marca === "brasil" || p.cor)
        .map((p) => {
          const item = el("span", "legenda-item");
          const chave = el("i", "chave redonda");
          chave.style.setProperty("--cor", p.cor ?? "var(--verde)");
          item.append(chave, document.createTextNode(p.nome));
          return item;
        }),
    );
    for (const p of pontos) p.rotulo = p.marca === "brasil";
    let fora: PontoDisperso[] = [];
    const desenhar = (): void => {
      fora = desenharDispersao(telaDispersao, pontos, ex, ey, aoTocar, comExtremos);
      escreverNota();
    };
    const escreverNota = (): void => {
      notaDispersao.replaceChildren(
        document.createTextNode(
          `Verde: Brasil. Cinza: os outros países. ` +
            (grupo ? `Pontos menores: os países de ${grupo.nome}. ` : "") +
            `Ano: ${ano}${projetado(eixoX, ano) || projetado(eixoY, ano) ? " (projeção do FMI em ao menos uma das métricas)" : ""}. `,
        ),
      );
      if (fora.length || comExtremos) {
        const lista = fora
          .slice(0, 6)
          .map((p) => `${p.nome} (${numero(p.x, eixoX.casas)}; ${numero(p.y, eixoY.casas)})`)
          .join(", ");
        const botao = el("button", "botao-texto", comExtremos ? "Tirar os valores extremos" : "Mostrar todos");
        botao.type = "button";
        botao.addEventListener("click", () => {
          comExtremos = !comExtremos;
          desenhar();
        });
        if (fora.length) {
          notaDispersao.append(
            document.createTextNode(
              `Fora do desenho, por estarem muito longe dos outros: ${lista}${fora.length > 6 ? ` e mais ${fora.length - 6}` : ""}. `,
            ),
          );
        }
        notaDispersao.append(botao);
      }
    };
    if (pontos.length < 3) {
      telaDispersao.replaceChildren(el("p", "vazio", `Poucos países com as duas métricas em ${ano}.`));
      notaDispersao.textContent = "";
    } else if (telaDispersao.clientWidth) {
      desenhar();
    }
    ultimaDispersao = desenhar;
    peDispersao.replaceChildren(
      el("span", "fonte", eixoX.fonte === eixoY.fonte ? `Fonte: ${eixoX.fonte}` : `Fontes: ${eixoX.fonte}; ${eixoY.fonte}`),
    );
  }
  let ultimaDispersao: (() => void) | null = null;
  let pendente = 0;
  new ResizeObserver(() => {
    cancelAnimationFrame(pendente);
    pendente = requestAnimationFrame(() => {
      if (telaDispersao.dataset.vazio !== "true") ultimaDispersao?.();
    });
  }).observe(telaDispersao);

  // ---------------------------------------------------------------- tabela
  function pintarTabela(): void {
    caixaTabela.replaceChildren(
      guardar(
        `Todas as métricas em ${ano}, país a país`,
        "Em itálico, projeção do FMI para o ano.",
        () => {
          const rolavel = el("div", "tabela-rolavel");
          rolavel.style.maxHeight = "none";
          const tabela = el("table", "dados larga");
          const cab = tabela.createTHead().insertRow();
          cab.append(el("th", "", "País"));
          for (const mt of m.metricas) {
            const th = el("th", "", mt.nome);
            th.title = `${mt.nome} (${mt.unidade})`;
            cab.append(th);
          }
          const corpo = tabela.createTBody();
          for (const [grupo, nome] of GRUPOS_DA_TABELA) {
            const lista = m.paises.filter((p) => p.grupo === grupo);
            if (!lista.length) continue;
            const tr = corpo.insertRow();
            tr.className = "grupo";
            const th = el("th", "", nome);
            th.colSpan = m.metricas.length + 1;
            tr.append(th);
            for (const p of lista) {
              const linha = corpo.insertRow();
              if (p.iso3 === "BRA") linha.className = "brasil";
              linha.append(el("th", "", p.nome));
              for (const mt of m.metricas) {
                const v = valor(mt, p.iso3, ano);
                linha.append(el("td", projetado(mt, ano) ? "proj" : "", v === null ? "–" : numero(v, mt.casas)));
              }
            }
          }
          rolavel.append(tabela);
          const pe = el("footer", "grafico-pe");
          pe.append(el("span", "fonte", `Fonte: FMI, ${m.edicao}; juros: BIS.`));
          return [rolavel, pe];
        },
      ),
    );
  }

  function pintar(): void {
    sobre.textContent = metrica.descricao;
    pintarRanking();
    pintarEscolhidos();
    pintarLinha();
    pintarDispersao();
    pintarTabela();
  }

  pintar();
  return raiz;
}
