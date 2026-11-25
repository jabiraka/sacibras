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
  gerais: Regra[];
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
          for (const n of new Set((m[1] ?? "").match(/\d+/g) ?? [])) {
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
  if (!achados.size) somar(registro.gerais);
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

function pendurar(no: HTMLElement): void {
  if (no.dataset.fontes === "1") return;
  const fonte = (no.textContent ?? "").replace(/^Fontes?:\s*/, "");
  const lista = enderecosDaFonte(fonte);
  no.dataset.fontes = "1";
  if (!lista.length) return;
  const links = document.createElement("span");
  links.className = "fonte-links";
  links.append(" · ");
  lista.forEach((e, i) => {
    if (i) links.append(" · ");
    const a = document.createElement("a");
    a.href = e.url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = enderecoCurto(e.url);
    a.title = `Abrir ${e.nome} em outra aba`;
    a.translate = false;
    links.append(a);
  });
  no.append(links);
}

function varrer(raiz: ParentNode): void {
  for (const no of raiz.querySelectorAll<HTMLElement>(".fonte:not([data-fontes])")) pendurar(no);
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
