// Brasil no mundo: a mesma métrica para vários países.
//   0. três listas no alto: a métrica (por tema), o ano e os países. "Países" vale para tudo
//      abaixo (Caio, 14/11/2026: escolher os emergentes mudava só o ranking, não a tabela);
//   1. o ranking do ano, em pontos; tocar num país o põe no gráfico ao lado, tocar num grupo
//      (na lista "Médias dos grupos") abre os países dele;
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
import type { Marca } from "./pontos";

const GRUPOS_DA_TABELA: [Pais["grupo"], string][] = [
  ["america_latina", "América Latina"],
  ["emergentes", "Outros emergentes"],
  ["avancados", "Avançados"],
  ["agregado", "Grupos"],
];

const INICIAIS = ["BRA", "MEX", "CHL", "USA"];
/** As métricas por tema, para a lista não ser uma fila de onze nomes. */
const TEMAS: Record<string, string> = {
  pib: "Atividade e emprego",
  pib_per_capita: "Atividade e emprego",
  investimento: "Atividade e emprego",
  desemprego: "Atividade e emprego",
  inflacao: "Preços e juros",
  juro: "Preços e juros",
  juro_real: "Preços e juros",
  inflacao_12m: "Preços e juros",
  juro_10a: "Preços e juros",
  divida: "Contas públicas",
  primario: "Contas públicas",
  nominal: "Contas públicas",
  carga: "Contas públicas",
  conta_corrente: "Contas externas",
  cambio: "Contas externas",
  servico_divida: "Crédito",
  hiato_credito: "Crédito",
  ptf: "Produtividade",
  produtividade_hora: "Produtividade",
  capital_ocupado: "Produtividade",
  capital_humano: "Produtividade",
  horas_ano: "Produtividade",
  parte_trabalho: "Produtividade",
  retorno_capital: "Produtividade",
  preco_investimento: "Produtividade",
};
const ORDEM_DOS_TEMAS = [
  "Atividade e emprego",
  "Produtividade",
  "Preços e juros",
  "Crédito",
  "Contas públicas",
  "Contas externas",
];
/** Os países que se comparam: os principais, as médias dos grupos ou um grupo do FMI. */
const PRINCIPAIS = "principais";
const MEDIAS = "medias";
/** Lista mais longa que isto rola dentro da caixa. */
const LISTA_CURTA = 24;
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
  const temaDe = (mt: MetricaMundo): string => TEMAS[mt.id] ?? "Outras";
  const porTema = [...m.metricas].sort(
    (a, b) =>
      (ORDEM_DOS_TEMAS.indexOf(temaDe(a)) + 1 || 99) - (ORDEM_DOS_TEMAS.indexOf(temaDe(b)) + 1 || 99),
  );
  const opcoesMetricas: Opcao[] = porTema.map((mt) => ({
    valor: mt.id,
    rotulo: mt.nome,
    grupo: temaDe(mt),
  }));
  let conjunto = PRINCIPAIS;
  const escolhaMetrica = listaSuspensa(
    "mundo-metrica",
    "Métrica",
    opcoesMetricas,
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
  const opcoesConjunto: Opcao[] = [
    { valor: PRINCIPAIS, rotulo: `Os ${m.paises.filter((p) => p.grupo !== "agregado").length} principais` },
    { valor: MEDIAS, rotulo: "Médias dos grupos do FMI" },
    ...(m.arquivo_paises
      ? m.grupos.map((g) => ({ valor: g.iso3, rotulo: `${g.nome} (${g.membros.length})`, grupo: "Todos os países de" }))
      : []),
  ];
  const escolhaConjunto = listaSuspensa("mundo-paises", "Países", opcoesConjunto, conjunto, (c) => {
    trocarConjunto(c);
  });
  barra.append(escolhaMetrica.caixa, escolhaAno.caixa, escolhaConjunto.caixa);
  const sobre = el("p", "secao-resumo");

  // ---------------------------------------------------------------- ranking e trajetória
  const grade = el("div", "mundo-grade");
  const painelRanking = el("div", "painel-mundo");
  const tituloRanking = el("h3");
  const subRanking = el("p", "sub");
  const ranking = el("div", "ranking-pontos");
  const posicao = el("p", "posicao");
  const fonteRanking = el("footer", "grafico-pe");
  painelRanking.append(tituloRanking, subRanking, ranking, posicao, fonteRanking);

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

  /** Os países (ou grupos) da comparação, na lista "Países". */
  function membros(): { iso: string; marca: Marca }[] {
    if (conjunto === MEDIAS) {
      return m.paises.filter((p) => p.grupo === "agregado").map((p) => ({ iso: p.iso3, marca: "grupo" as Marca }));
    }
    const grupo = grupoDe.get(conjunto);
    const lista = grupo
      ? grupo.membros
      : m.paises.filter((p) => p.grupo !== "agregado").map((p) => p.iso3);
    // O Brasil sempre aparece, para servir de régua mesmo num grupo de que ele não faz parte.
    const isos = lista.includes("BRA") ? lista : ["BRA", ...lista];
    return isos.map((iso) => ({ iso, marca: (iso === "BRA" ? "brasil" : "comum") as Marca }));
  }

  function nomeDoConjunto(): string {
    if (conjunto === MEDIAS) return "grupos";
    const grupo = grupoDe.get(conjunto);
    return grupo ? `países de ${grupo.nome}` : "países";
  }

  function trocarConjunto(c: string): void {
    conjunto = c;
    escolhaConjunto.trocar(opcoesConjunto, c);
    if (grupoDe.has(c)) {
      ranking.replaceChildren(el("p", "posicao", "Carregando os países…"));
      void carregarTodos().then(pintarConjunto);
    } else pintarConjunto();
  }

  function pintarConjunto(): void {
    pintarRanking();
    pintarDispersao();
    pintarTabela();
  }

  function pintarRanking(): void {
    const proj = projetado(metrica, ano);
    tituloRanking.textContent = `${metrica.nome} em ${ano}${proj ? " (projeção)" : ""}`;
    const emGrupo = grupoDe.has(conjunto);
    if (emGrupo && !todos) {
      ranking.replaceChildren(el("p", "posicao", "Sem a lista de países nesta rodada."));
      posicao.replaceChildren();
      return;
    }
    subRanking.textContent =
      conjunto === MEDIAS
        ? `${metrica.unidade} · média do FMI para cada grupo; toque num grupo para ver os países dele`
        : `${metrica.unidade} · toque num país para pô-lo no gráfico ao lado`;
    const comValor = membros()
      .map((x) => ({ ...x, v: valor(metrica, x.iso, ano) }))
      .filter((x): x is { iso: string; marca: Marca; v: number } => x.v !== null)
      .sort((a, b) => b.v - a.v);
    // Num grupo inteiro, os extremos (a Turquia com 30 % de inflação) achatariam todo o resto:
    // a régua vai do 5º ao 95º percentil, e quem passa fica na ponta, com o valor ao lado.
    const ordenados = comValor.map((x) => x.v).sort((a, b) => a - b);
    const corte = (q: number): number => ordenados[Math.round(q * (ordenados.length - 1))] ?? 0;
    const regua = reguaDe(ordenados.length > LISTA_CURTA ? [corte(0.05), corte(0.95)] : ordenados);
    const linhas = comValor.map(({ iso, marca, v }, i) => {
      const casa = casas.get(iso);
      const ehGrupo = marca === "grupo";
      const grupo = grupoDe.get(iso);
      return linhaDoRanking(
        {
          chave: iso,
          nome: nomeDe(iso),
          valor: v,
          marca,
          posicao: ehGrupo ? null : i + 1,
          cor: casa !== undefined && iso !== "BRA" ? cor(casa) : undefined,
          abre: ehGrupo && grupo && m.arquivo_paises ? { aberto: false, quantos: grupo.membros.length } : undefined,
          dica: `${nomeDe(iso)}: ${numero(v, metrica.casas)} ${metrica.unidade}`,
        },
        regua,
        metrica.casas,
        ehGrupo
          ? grupo && m.arquivo_paises
            ? () => trocarConjunto(iso)
            : undefined
          : () => alternarPais(iso),
      );
    });
    if (!linhas.length) {
      // A Penn World Table não faz média de grupo, e nenhuma fonte cobre todos os anos.
      ranking.replaceChildren(
        el(
          "p",
          "posicao",
          conjunto === MEDIAS
            ? "A fonte desta métrica não publica médias de grupos: escolha os países principais ou um grupo para ver os países dele."
            : `Sem ${metrica.nome.toLowerCase()} em ${ano} para estes países.`,
        ),
      );
    } else if (linhas.length > LISTA_CURTA) {
      // Lista longa (um grupo do FMI inteiro): rola dentro da caixa, com o Brasil à vista.
      const caixa = el("div", "ponto-membros lista-longa");
      caixa.append(...linhas);
      ranking.replaceChildren(caixa);
      const brasil = caixa.querySelector<HTMLElement>(".ponto-linha.brasil");
      requestAnimationFrame(() => {
        if (brasil) caixa.scrollTop = brasil.offsetTop - caixa.clientHeight / 2;
      });
    } else ranking.replaceChildren(...linhas);

    posicao.replaceChildren();
    const paises = comValor.filter((x) => x.marca !== "grupo");
    const lugarBrasil = paises.findIndex((x) => x.iso === "BRA") + 1;
    const vBrasil = valor(metrica, "BRA", ano);
    if (vBrasil !== null && (lugarBrasil || conjunto === MEDIAS)) {
      posicao.append(document.createTextNode("Brasil: "), el("b", "", `${numero(vBrasil, metrica.casas)} ${metrica.unidade}`));
      if (lugarBrasil) {
        posicao.append(document.createTextNode(`, o ${lugarBrasil}º maior entre ${paises.length} ${nomeDoConjunto()}.`));
      } else posicao.append(document.createTextNode("."));
      const media = valor(metrica, emGrupo ? conjunto : "G001", ano);
      if (media !== null && conjunto !== MEDIAS) {
        const quem = emGrupo ? `Média de ${grupoDe.get(conjunto)?.nome ?? "grupo"}` : "Mundo";
        posicao.append(document.createTextNode(` ${quem}: ${numero(media, metrica.casas)}.`));
      }
    }
    fonteRanking.replaceChildren(el("span", "fonte", `Fonte: ${metrica.fonte}`));
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
    const grupo = grupoDe.get(conjunto);
    // Os escolhidos no gráfico de linha entram sempre; o resto, do conjunto da lista "Países".
    for (const iso of casas.keys()) incluir(iso, "comum");
    for (const x of membros()) incluir(x.iso, conjunto === MEDIAS ? "grupo" : grupo ? "membro" : "comum");
    // Nas médias dos grupos, os principais países ficam também (o juro do BIS não tem grupo).
    if (conjunto === MEDIAS) for (const p of m.paises) if (p.grupo !== "agregado") incluir(p.iso3, "comum");
    telaDispersao.dataset.vazio = String(pontos.length < 3);
    const ex = { nome: eixoX.nome, unidade: eixoX.unidade, casas: eixoX.casas };
    const ey = { nome: eixoY.nome, unidade: eixoY.unidade, casas: eixoY.casas };
    const aoTocar = (iso: string): void => {
      if (!iso.startsWith("G")) alternarPais(iso);
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
            (pontos.some((p) => p.marca === "grupo") ? "Losangos: as médias dos grupos do FMI. " : "") +
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
    const grupo = grupoDe.get(conjunto);
    const titulo =
      conjunto === MEDIAS
        ? `Todas as métricas em ${ano}, grupo a grupo`
        : grupo
          ? `Todas as métricas em ${ano}: ${grupo.nome}, país a país`
          : `Todas as métricas em ${ano}, país a país`;
    caixaTabela.replaceChildren(
      guardar(titulo, "Em itálico, projeção do FMI para o ano.", () => {
        const rolavel = el("div", "tabela-rolavel");
        rolavel.style.maxHeight = grupo ? "70vh" : "none";
        const tabela = el("table", "dados larga");
        const cab = tabela.createTHead().insertRow();
        cab.append(el("th", "", conjunto === MEDIAS ? "Grupo" : "País"));
        for (const mt of porTema) {
          const th = el("th", "", mt.nome);
          th.title = `${mt.nome} (${mt.unidade})`;
          cab.append(th);
        }
        const corpo = tabela.createTBody();
        const linhaDe = (iso: string): void => {
          const linha = corpo.insertRow();
          if (iso === "BRA") linha.className = "brasil";
          linha.append(el("th", "", nomeDe(iso)));
          for (const mt of porTema) {
            const v = valor(mt, iso, ano);
            linha.append(el("td", projetado(mt, ano) ? "proj" : "", v === null ? "–" : numero(v, mt.casas)));
          }
        };
        const titulo = (nome: string): void => {
          const tr = corpo.insertRow();
          tr.className = "grupo";
          const th = el("th", "", nome);
          th.colSpan = porTema.length + 1;
          tr.append(th);
        };
        if (conjunto === MEDIAS) {
          m.paises.filter((p) => p.grupo === "agregado").forEach((p) => linhaDe(p.iso3));
        } else if (grupo) {
          // O Brasil em cima; os outros em ordem alfabética.
          const isos = grupo.membros.filter((i) => i !== "BRA");
          isos.sort((a, b) => nomeDe(a).localeCompare(nomeDe(b), "pt-BR"));
          linhaDe("BRA");
          titulo(`${grupo.nome}: ${isos.length + (grupo.membros.includes("BRA") ? 1 : 0)} países`);
          isos.forEach(linhaDe);
        } else {
          for (const [g, nome] of GRUPOS_DA_TABELA) {
            const lista = m.paises.filter((p) => p.grupo === g);
            if (!lista.length || g === "agregado") continue;
            titulo(nome);
            lista.forEach((p) => linhaDe(p.iso3));
          }
        }
        rolavel.append(tabela);
        const pe = el("footer", "grafico-pe");
        pe.append(
          el("span", "fonte", `Fonte: FMI, ${m.edicao}; juro básico, inflação em 12 meses e câmbio: BIS; juro de 10 anos: OCDE e Tesouro Nacional; carga tributária: OCDE; produtividade: Penn World Table (CC BY 4.0).`),
        );
        return [rolavel, pe];
      }),
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
