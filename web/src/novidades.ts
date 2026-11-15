// "Novo desde a sua última visita" (15/11/2026): o navegador guarda a data de referência de
// cada número que a pessoa viu; na visita seguinte, o número cuja referência passou da que
// ela viu ganha um selo discreto "novo". Comparar com a data da visita não serviria: o IPCA
// de outubro (referência 01/10) sai em novembro, depois de uma visita em 05/11.
//
// A "visita" é o dia: o selo fica o dia inteiro (recarregar a página não o apaga) e some no
// dia seguinte, se a pessoa voltar. Na primeira visita nada é novo. Tudo fica só no navegador
// (`sacibras-visita`); sem armazenamento (janela anônima, bloqueio), simplesmente não há selo.

import { el } from "./pecas";

const CHAVE = "sacibras-visita";

interface Guardado {
  /** O dia da última visita ("2026-11-15", no fuso de quem visita). */
  dia: string;
  /** A referência mais nova vista de cada número ("inflacao/ipca-12m" → "2026-10-01"). */
  vistos: Record<string, string>;
  /** As referências como estavam antes do dia de hoje: a régua do selo. */
  antes: Record<string, string>;
}

let estado: Guardado | null = null;
let gravar = 0;

function hoje(): string {
  const d = new Date();
  const p = (n: number): string => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function ler(): Guardado {
  if (estado) return estado;
  const dia = hoje();
  let guardado: Partial<Guardado> = {};
  try {
    guardado = JSON.parse(localStorage.getItem(CHAVE) ?? "{}") as Partial<Guardado>;
  } catch {
    guardado = {};
  }
  const vistos = guardado.vistos ?? {};
  // Num dia novo, o que foi visto até ontem vira a régua; no mesmo dia, a régua continua.
  const antes = guardado.dia === dia ? (guardado.antes ?? {}) : { ...vistos };
  estado = { dia, vistos, antes };
  agendarGravacao();
  return estado;
}

function agendarGravacao(): void {
  window.clearTimeout(gravar);
  gravar = window.setTimeout(() => {
    try {
      localStorage.setItem(CHAVE, JSON.stringify(estado));
    } catch {
      // Sem armazenamento: sem selo na próxima visita, e nada mais muda.
    }
  }, 400);
}

/** Registra que a pessoa viu o número e diz se ele é novo desde a última visita. */
export function novoDesdeAUltimaVisita(secao: string, id: string, referencia: string): boolean {
  if (!secao || !referencia) return false;
  const e = ler();
  const chave = `${secao}/${id}`;
  const visto = e.vistos[chave];
  if (!visto || referencia > visto) {
    e.vistos[chave] = referencia;
    agendarGravacao();
  }
  const antes = e.antes[chave];
  return antes !== undefined && referencia > antes;
}

/** O selo "novo", com o porquê no título. */
export function seloNovo(): HTMLElement {
  const selo = el("span", "selo-novo", "novo");
  selo.title = "Saiu um dado mais novo desde a sua última visita";
  return selo;
}
