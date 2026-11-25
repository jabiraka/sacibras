// O endereço exato de cada fonte (Caio, 25/11/2026: "coloque o site de onde estamos tirando a
// informação, o site exato"). Os padrões vêm do builder (`fontes.json`, de `links.py`); aqui se
// procura cada um no texto da fonte e se põe o endereço ao lado. Espelha `links.enderecos`.

interface Regra {
  padrao: string;
  nome: string;
  url: string;
  por_numero?: boolean;
}

interface Registro {
  regras: Regra[];
  /** Instituição citada sem link dela: entra a página geral (`dominio` é o pedaço do endereço
   *  que já a cobre). */
  instituicoes: (Regra & { dominio: string })[];
}

export interface Endereco {
  nome: string;
  url: string;
}

let registro: Registro | null = null;

/** Os endereços da fonte, sem repetir; sem regra que case, a página geral da instituição. */
export function enderecosDaFonte(fonte: string): Endereco[] {
  if (!registro) return [];
  const achados = new Map<string, Endereco>();
  const somar = (regras: Regra[]): void => {
    for (const r of regras) {
      for (const m of fonte.matchAll(new RegExp(r.padrao, "g"))) {
        if (r.por_numero) {
          for (const n of new Set((m[1] ?? "").match(/[A-Z][A-Z0-9_]*[0-9_][A-Z0-9_]*|\d+/g) ?? [])) {
            const url = r.url.replace("{n}", n);
            if (!achados.has(url)) achados.set(url, { nome: r.nome.replace("{n}", n), url });
          }
        } else if (!achados.has(r.url)) {
          achados.set(r.url, { nome: r.nome, url: r.url });
        }
      }
    }
  };
  somar(registro.regras);
  for (const i of registro.instituicoes) {
    const cobre = [...achados.keys()].some((u) => u.includes(i.dominio));
    if (!cobre && new RegExp(i.padrao).test(fonte)) somar([i]);
  }
  return [...achados.values()];
}

/** O endereço sem "https://" nem a barra do fim, para ler na tela. */
export function enderecoCurto(url: string): string {
  return url.replace(/^https?:\/\//, "").replace(/\/$/, "");
}

/** "Fonte: …" com os endereços por extenso, para o CSV e a imagem (onde link não clica). */
export function fonteComEnderecos(texto: string): string {
  const fonte = texto.replace(/^Fontes?:\s*/, "");
  const urls = enderecosDaFonte(fonte).map((e) => e.url);
  return urls.length ? `${texto}. Endereço: ${urls.join(" ; ")}` : texto;
}

function ancora(texto: string, e: Endereco): HTMLAnchorElement {
  const a = document.createElement("a");
  a.href = e.url;
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  a.textContent = texto;
  a.title = e.url;
  a.translate = false;
  return a;
}

/** Cada código de série ("SGS 433, 4466") vira link no próprio texto; as instituições, que não
 *  têm palavra no texto para clicar, ganham o nome ao lado, depois de " · ". */
function pendurar(no: HTMLElement): void {
  if (no.dataset.fontes === "1") return;
  no.dataset.fontes = "1";
  const bruto = no.textContent ?? "";
  const prefixo = /^Fontes?:\s*/.exec(bruto)?.[0] ?? "";
  const fonte = bruto.slice(prefixo.length);
  if (!registro) return;
  const nos: { ini: number; fim: number; e: Endereco }[] = [];
  const usados = new Set<string>();
  const percorrer = (regras: Regra[]): void => {
    for (const r of regras) {
      for (const m of fonte.matchAll(new RegExp(r.padrao, "g"))) {
        if (r.por_numero) {
          const base = m.index + m[0].indexOf(m[1] ?? "");
          for (const n of (m[1] ?? "").matchAll(/[A-Z][A-Z0-9_]*[0-9_][A-Z0-9_]*|\d+/g)) {
            const url = r.url.replace("{n}", n[0]);
            nos.push({ ini: base + n.index, fim: base + n.index + n[0].length, e: { nome: n[0], url } });
            usados.add(url);
          }
        }
      }
    }
  };
  percorrer(registro.regras);
  nos.sort((a, b) => a.ini - b.ini);
  const resto = enderecosDaFonte(fonte).filter((e) => !usados.has(e.url));
  if (!nos.length && !resto.length) return;
  const partes: (string | HTMLElement)[] = [prefixo];
  let pos = 0;
  for (const n of nos) {
    if (n.ini < pos) continue;
    partes.push(fonte.slice(pos, n.ini), ancora(n.e.nome, n.e));
    pos = n.fim;
  }
  partes.push(fonte.slice(pos));
  if (resto.length) {
    partes.push(" · ");
    resto.forEach((e, i) => {
      if (i) partes.push(", ");
      partes.push(ancora(e.nome, e));
    });
  }
  no.className += " fonte-links";
  no.replaceChildren(...partes);
}

function varrer(raiz: ParentNode): void {
  for (const no of raiz.querySelectorAll<HTMLElement>(".fonte:not([data-fontes]), #fontes li:not([data-fontes])")) pendurar(no);
}

/** Lê os padrões e passa a pôr o endereço em toda `.fonte` que aparecer dentro de `raiz`. */
export function ligarEnderecos(raiz: HTMLElement): void {
  void fetch("data/fontes.json", { cache: "no-cache" })
    .then((r) => (r.ok ? (r.json() as Promise<Registro>) : null))
    .then((dados) => {
      if (!dados) return;
      registro = dados;
      varrer(raiz);
      let pendente = 0;
      new MutationObserver(() => {
        cancelAnimationFrame(pendente);
        pendente = requestAnimationFrame(() => varrer(raiz));
      }).observe(raiz, { childList: true, subtree: true });
    })
    .catch(() => undefined);
}
