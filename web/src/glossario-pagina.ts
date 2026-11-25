// A página do glossário (#glossario): todas as palavras do painel numa lista, de A a Z, para
// quem quer ler as definições sem caçá-las na tela (revisão das telas, 15/11/2026). O texto é o
// mesmo dos balões (`glossario.json`, de `builder/src/sacibras/glossario.py`).

import type { Verbete } from "./busca";
import { normalizar } from "./busca";
import { el } from "./pecas";

/** A letra em que o verbete entra na lista: sem acento, "Ágio" fica no A. */
function letraDe(v: Verbete): string {
  const primeira = normalizar(v.nome).charAt(0).toUpperCase();
  return /[A-Z]/.test(primeira) ? primeira : "#";
}

/** Os verbetes em ordem alfabética (sem acento e sem caixa), agrupados pela letra. */
export function porLetra(lista: Verbete[]): Map<string, Verbete[]> {
  const ordem = [...lista].sort((a, b) =>
    normalizar(a.nome).localeCompare(normalizar(b.nome), "pt-BR"),
  );
  const grupos = new Map<string, Verbete[]>();
  for (const v of ordem) {
    const letra = letraDe(v);
    const grupo = grupos.get(letra) ?? [];
    grupo.push(v);
    grupos.set(letra, grupo);
  }
  return grupos;
}

function montar(lista: Verbete[]): HTMLElement {
  const grupos = porLetra(lista);
  const corpo = el("div", "glossario-pagina");

  // As letras: um toque leva ao grupo (rolagem, sem mudar o endereço da página).
  const letras = el("nav", "glossario-letras");
  letras.setAttribute("aria-label", "Letras");
  for (const letra of grupos.keys()) {
    const b = el("button", "pilula", letra);
    b.type = "button";
    b.addEventListener("click", () => {
      document.getElementById(`glossario-${letra}`)?.scrollIntoView({ behavior: "smooth" });
    });
    letras.append(b);
  }
  corpo.append(letras);

  for (const [letra, verbetes] of grupos) {
    const bloco = el("section", "glossario-grupo vidro");
    bloco.id = `glossario-${letra}`;
    bloco.append(el("h3", "glossario-letra", letra));
    const dl = el("dl");
    for (const v of verbetes) {
      const dt = el("dt", "", v.nome);
      dt.id = `termo-${v.id}`;
      const dd = el("dd");
      dd.append(el("span", "glossario-def", v.definicao));
      if (v.elo) {
        const elo = el("a", "glossario-elo", "Ver no painel →");
        elo.href = v.elo;
        dd.append(" ", elo);
      }
      dl.append(dt, dd);
    }
    bloco.append(dl);
    corpo.append(bloco);
  }
  return corpo;
}

/** Monta a página em `conteudo`. `termo` ("#glossario/pib") rola até aquele verbete. */
export function vistaGlossario(conteudo: HTMLElement, termo = ""): void {
  const secao = el("section", "secao");
  const topo = el("header", "secao-topo");
  const corpo = el("div", "secao-corpo");
  const trilha = el("nav", "trilha");
  trilha.setAttribute("aria-label", "Onde você está");
  trilha.append(el("span", "", "Consulta"));
  topo.append(trilha, el("h2", "", "Glossário"));
  secao.append(topo, corpo);
  conteudo.replaceChildren(secao);
  void fetch("data/glossario.json", { cache: "no-cache" })
    .then((r) => (r.ok ? (r.json() as Promise<Verbete[]>) : []))
    .then((lista) => {
      if (!lista.length) {
        corpo.append(el("p", "aviso", "O glossário não pôde ser carregado nesta rodada."));
        return;
      }
      corpo.append(
        el(
          "p",
          "secao-resumo",
          `As ${lista.length} palavras do painel que alguém poderia não saber. ` +
            "Na tela, a palavra sublinhada ou o “?” abre a definição.",
        ),
        montar(lista),
      );
      if (termo) document.getElementById(`termo-${termo}`)?.scrollIntoView();
    })
    .catch(() => {
      corpo.append(el("p", "aviso", "O glossário não pôde ser carregado nesta rodada."));
    });
}
