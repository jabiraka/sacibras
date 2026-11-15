// A página no idioma de quem visita (Caio, 14/11/2026: "coloque também a página pelo idioma
// de quem entra pra visitar, pelo país, deixe alguma forma de tradução automática").
//
// O painel é escrito em português. Quem chega com o navegador em outro idioma (en-US, es-AR,
// zh-TW…) recebe a página traduzida automaticamente pelo Google Tradutor, e a lista "Idioma"
// no menu troca ou volta ao original. A variante do país vale quando muda a escrita (zh-TW e
// zh-HK: chinês tradicional); português de qualquer país (pt-PT, pt-AO) fica no original.
// O país pelo endereço IP não é usado: pediria um serviço de terceiros só para isso.
//
// O tradutor só é carregado quando o idioma não é o português: quem lê em português não
// baixa nada do Google. A escolha fica guardada no navegador (`sacibras-idioma`).

import { el } from "./pecas";

const ORIGINAL = "pt";
const GUARDADO = "sacibras-idioma";

/** Os idiomas da lista, além do do navegador (que entra se não estiver aqui). */
const LISTA = ["pt", "en", "es", "fr", "de", "it", "zh-CN", "zh-TW", "ja", "ko", "ru", "ar", "hi"];

/** O código que o Google Tradutor entende, a partir do idioma do navegador. */
export function codigoGoogle(idioma: string): string {
  const [lingua = "", regiao = ""] = idioma.toLowerCase().split(/[-_]/);
  if (lingua === "zh") {
    return regiao === "tw" || regiao === "hk" || regiao === "mo" || regiao === "hant"
      ? "zh-TW"
      : "zh-CN";
  }
  // O Google usa os códigos antigos de hebraico e javanês.
  if (lingua === "he") return "iw";
  if (lingua === "jv") return "jw";
  return lingua;
}

/** O nome do idioma nele mesmo ("English", "Español", "中文（台灣）"). */
function nomeProprio(codigo: string): string {
  const bcp = codigo === "iw" ? "he" : codigo === "jw" ? "jv" : codigo;
  try {
    const nome = new Intl.DisplayNames([bcp], { type: "language" }).of(bcp);
    if (nome) return nome.charAt(0).toLocaleUpperCase(bcp) + nome.slice(1);
  } catch {
    // Intl sem o idioma: fica o código.
  }
  return codigo;
}

function lerGuardado(): string | null {
  try {
    return localStorage.getItem(GUARDADO);
  } catch {
    return null;
  }
}

function guardar(codigo: string): void {
  try {
    localStorage.setItem(GUARDADO, codigo);
  } catch {
    // Navegador sem armazenamento: a escolha vale só para esta visita.
  }
}

/** O idioma em que a página deve abrir: a escolha guardada ou o primeiro do navegador. */
export function idiomaDesejado(navegador: readonly string[] = navigator.languages): string {
  const guardado = lerGuardado();
  if (guardado) return guardado;
  const primeiro = navegador[0] ?? navigator.language ?? ORIGINAL;
  return codigoGoogle(primeiro);
}

/** O cookie que o tradutor lê para saber para onde traduzir; vazio volta ao original. */
function cookie(codigo: string): void {
  const valor = codigo === ORIGINAL ? "" : `/${ORIGINAL}/${codigo}`;
  const expira = codigo === ORIGINAL ? "; expires=Thu, 01 Jan 1970 00:00:00 GMT" : "";
  const host = location.hostname;
  for (const dominio of ["", `; domain=${host}`, `; domain=.${host}`]) {
    document.cookie = `googtrans=${valor}; path=/${dominio}${expira}`;
  }
}

let carregado = false;
let idiomaDaPagina = ORIGINAL;

/** O idioma em que a página está sendo mostrada ("pt" quando é o original). */
export function idiomaAtual(): string {
  return idiomaDaPagina;
}

function carregarTradutor(): void {
  if (carregado) return;
  carregado = true;
  const caixa = el("div");
  caixa.id = "gt-caixa";
  caixa.hidden = true;
  document.body.append(caixa);
  const janela = window as unknown as Record<string, unknown>;
  janela.sacibrasTradutor = (): void => {
    const google = (window as unknown as { google?: { translate?: { TranslateElement?: unknown } } })
      .google;
    const Elemento = google?.translate?.TranslateElement as
      | (new (opcoes: object, id: string) => unknown)
      | undefined;
    if (Elemento) new Elemento({ pageLanguage: ORIGINAL, autoDisplay: false }, "gt-caixa");
  };
  const script = document.createElement("script");
  script.src = "https://translate.google.com/translate_a/element.js?cb=sacibrasTradutor";
  script.async = true;
  script.onerror = (): void => {
    const aviso = document.getElementById("idioma-aviso");
    if (aviso) aviso.textContent = "O tradutor automático não respondeu; a página segue em português.";
  };
  document.head.append(script);
}

/** Troca de idioma: grava a escolha e recarrega (o tradutor começa limpo, sem resto do anterior). */
function trocar(codigo: string): void {
  guardar(codigo);
  cookie(codigo);
  location.reload();
}

/** A lista "Idioma" no menu e, se for o caso, a tradução automática já na entrada. */
export function ligarTraducao(): void {
  const alvo = codigoGoogle(idiomaDesejado());
  idiomaDaPagina = alvo;
  const caixa = document.getElementById("idioma");
  if (caixa) {
    const codigos = LISTA.includes(alvo) ? LISTA : [...LISTA, alvo];
    const rotulo = el("label", "idioma-rotulo", "Idioma");
    rotulo.htmlFor = "idioma-lista";
    const lista = el("select", "escolha notranslate");
    lista.id = "idioma-lista";
    lista.setAttribute("translate", "no");
    for (const c of codigos) {
      const opcao = el("option", "", c === ORIGINAL ? "Português (original)" : nomeProprio(c));
      opcao.value = c;
      opcao.lang = c === "iw" ? "he" : c;
      lista.append(opcao);
    }
    lista.value = alvo;
    lista.addEventListener("change", () => trocar(lista.value));
    caixa.append(rotulo, lista);
    if (alvo !== ORIGINAL) {
      caixa.append(
        el("p", "idioma-aviso", "Tradução automática do português (Google Tradutor). Os números e as fontes são os do original."),
      );
      caixa.lastElementChild?.setAttribute("id", "idioma-aviso");
    }
  }
  if (alvo === ORIGINAL) {
    // Pode ter sobrado o cookie de uma visita traduzida.
    if (document.cookie.includes("googtrans=/")) cookie(ORIGINAL);
    return;
  }
  cookie(alvo);
  carregarTradutor();
}

/** Os nomes dos estados, que o tradutor estraga ("To" de Tocantins, "Holy Spirit"). */
const ESTADOS = new Set([
  "Acre", "Alagoas", "Amapá", "Amazonas", "Bahia", "Ceará", "Distrito Federal", "Espírito Santo",
  "Goiás", "Maranhão", "Mato Grosso", "Mato Grosso do Sul", "Minas Gerais", "Pará", "Paraíba",
  "Paraná", "Pernambuco", "Piauí", "Rio de Janeiro", "Rio Grande do Norte", "Rio Grande do Sul",
  "Rondônia", "Roraima", "Santa Catarina", "São Paulo", "Sergipe", "Tocantins",
]);

// Nomes próprios e siglas que o tradutor estraga ("Focus" vira "Foco", "Copom" ganha
// tradução, "IPCA" some no meio da frase) e que não têm tradução: o nome do comitê, da
// pesquisa, do índice. O PIB fica de fora, porque "GDP" e "PIB" em espanhol são a tradução
// certa (15/11/2026).
const NOMES_PROPRIOS = [
  "Copom",
  "Focus",
  "Selic",
  "IPCA-15",
  "IPCA+",
  "IPCA",
  "INPC",
  "IGP-M",
  "IGP-DI",
  "IPA",
  "CDI",
  "IBC-Br",
  "IBC-R",
  "Caged",
  "Novo Caged",
  "PNAD",
  "IBGE",
  "Ibovespa",
  "B3",
  "ICMS",
  "IBS",
  "CBS",
  "INSS",
  "IRPF",
  "IRPJ",
  "CSLL",
  "IOF",
  "IPI",
  "FGTS",
  "BNDES",
  "LDO",
  "LRF",
  "RCL",
  "DBGG",
  "DLSP",
  "CAPAG",
  "Ipea",
  "Pix",
  "Siconfi",
  "Sidra",
  "Bolsa Família",
  "Tesouro Direto",
  "Tesouro Prefixado",
  "Tesouro IPCA+",
  "EX0",
  "EX1",
  "EX2",
  "EX3",
  "P55",
];

const PADRAO_NOMES = new RegExp(
  `(?<![\\p{L}\\p{N}])(${[...NOMES_PROPRIOS]
    .sort((a, b) => b.length - a.length)
    .map((n) => n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .join("|")})(?![\\p{L}\\p{N}+])`,
  "gu",
);

/** Onde os nomes ficam protegidos: os títulos, o menu e os rótulos curtos. O texto corrido
 *  fica com o tradutor (a frase precisa da tradução inteira). */
const TITULOS = [
  "h1",
  "h2",
  "h3",
  "h4",
  "summary",
  ".menu a",
  ".menu-categoria",
  ".trilha",
  ".pilula",
  ".assunto-titulo",
  ".parte-titulo",
  ".cartao-rotulo",
  ".essencial .rotulo",
  ".legenda-item",
  ".busca-titulo",
].join(",");

/** Põe `translate="no"` em volta de cada nome próprio do texto do elemento. Só embrulha o
 *  nome (não o título inteiro), então o resto se traduz, o glossário continua achando a
 *  palavra (lê o texto, que não muda) e a busca não vê diferença. */
export function protegerNomes(raiz: Element): void {
  const andar = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT, {
    acceptNode: (n) =>
      n.parentElement?.closest(".notranslate, [translate='no'], button, script, style")
        ? NodeFilter.FILTER_REJECT
        : NodeFilter.FILTER_ACCEPT,
  });
  const nos: Text[] = [];
  for (let n = andar.nextNode(); n; n = andar.nextNode()) nos.push(n as Text);
  for (const no of nos) {
    const texto = no.data;
    PADRAO_NOMES.lastIndex = 0;
    if (!PADRAO_NOMES.test(texto)) continue;
    PADRAO_NOMES.lastIndex = 0;
    const pedacos: (string | HTMLElement)[] = [];
    let desde = 0;
    for (let m = PADRAO_NOMES.exec(texto); m; m = PADRAO_NOMES.exec(texto)) {
      // Os espaços em volta vão junto: o tradutor apara o texto que traduz, e "Juros e" +
      // "Copom" virava "Interest andCopom".
      let ini = m.index;
      let fim = m.index + (m[1] ?? "").length;
      while (ini > desde && /\s/.test(texto.charAt(ini - 1))) ini -= 1;
      while (fim < texto.length && /\s/.test(texto.charAt(fim))) fim += 1;
      const nome = el("span", "notranslate", texto.slice(ini, fim));
      nome.setAttribute("translate", "no");
      pedacos.push(texto.slice(desde, ini), nome);
      desde = fim;
      PADRAO_NOMES.lastIndex = fim;
    }
    pedacos.push(texto.slice(desde));
    const juntos = pedacos.filter((p) => p !== "");
    // Num título em flex ("Selic e Copom →"), cada pedaço viraria um item afastado do outro:
    // os pedaços vão juntos num span só.
    const pai = no.parentElement;
    const display = pai ? getComputedStyle(pai).display : "";
    if (display.includes("flex") || display.includes("grid")) {
      const caixa = el("span");
      caixa.append(...juntos);
      no.replaceWith(caixa);
    } else no.replaceWith(...juntos);
  }
}

/** Protege os nomes próprios nos títulos e no menu, também no que aparecer depois. Vale com
 *  a página em português também: o tradutor do próprio navegador (o do Chrome) respeita a
 *  marca. */
export function ligarNomesProprios(): void {
  for (const no of document.querySelectorAll(TITULOS)) protegerNomes(no);
  // Só o que entrou na página: a dica do gráfico muda a cada movimento do dedo.
  const fila = new Set<Element>();
  let pendente = 0;
  new MutationObserver((mudancas) => {
    for (const m of mudancas) {
      for (const n of m.addedNodes) {
        const e = n instanceof Element ? n : n.parentElement;
        if (!e) continue;
        const titulo = e.closest(TITULOS);
        if (titulo) fila.add(titulo);
        else if (n instanceof Element) for (const t of n.querySelectorAll(TITULOS)) fila.add(t);
      }
    }
    if (!fila.size) return;
    cancelAnimationFrame(pendente);
    pendente = requestAnimationFrame(() => {
      for (const t of fila) if (t.isConnected) protegerNomes(t);
      fila.clear();
    });
  }).observe(document.body, { childList: true, subtree: true });
}

/** Marca o nó para o Google Tradutor não mexer, se o texto for o nome de um estado. */
export function protegerNomeDeEstado(no: HTMLElement, texto: string): void {
  if (!ESTADOS.has(texto)) return;
  no.classList.add("notranslate");
  no.setAttribute("translate", "no");
}
