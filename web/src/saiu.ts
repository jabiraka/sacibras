// "Saiu por último", na entrada (Caio, 16/11/2026): o número mais novo de cada divulgação
// contra a última mediana do Focus antes dele, e quanto o Focus costuma errar ali. A conta
// vem pronta do builder (`saiu.py`); aqui só se escreve a frase. Acima ou abaixo do esperado
// não é bom nem ruim: a seta e o texto vão em tinta neutra.

import { comUnidade, data, numero } from "./formato";
import { el } from "./pecas";
import type { Divulgado } from "./tipos";

function diaMes(iso: string): string {
  const d = data(iso);
  const p = (n: number): string => String(n).padStart(2, "0");
  return `${p(d.getUTCDate())}/${p(d.getUTCMonth() + 1)}`;
}

/** "▼ 0,13 pp abaixo do esperado", "▲ 0,25 pp acima do esperado", "como o esperado". */
export function leitura(d: Divulgado): string {
  if (d.surpresa === null) return "";
  if (d.surpresa === 0) return "como o esperado";
  const tamanho = `${numero(Math.abs(d.surpresa), d.casas)} pp`;
  return d.surpresa > 0 ? `▲ ${tamanho} acima do esperado` : `▼ ${tamanho} abaixo do esperado`;
}

/** "Focus esperava 0,27 % em 06/11 · costuma errar 0,10 pp". */
export function contexto(d: Divulgado): string {
  if (d.esperado === null) return "Sem a mediana do Focus para esta divulgação.";
  const partes = [`Focus esperava ${comUnidade(d.esperado, d.unidade, d.casas)}`];
  if (d.esperado_em) partes[0] += ` em ${diaMes(d.esperado_em)}`;
  if (d.erro_de_costume !== null) {
    const erro = numero(d.erro_de_costume, d.casas);
    partes.push(
      Number(d.erro_de_costume.toFixed(d.casas)) === 0
        ? `acertou as ${d.divulgacoes} anteriores`
        : `costuma errar ${erro} pp`,
    );
  }
  return partes.join(" · ");
}

export function saiuPorUltimo(itens: Divulgado[]): HTMLElement {
  const caixa = el("section", "vidro saiu entra");
  caixa.style.setProperty("--i", "4");
  caixa.setAttribute("aria-label", "O que saiu por último, contra o esperado");
  const topo = el("div", "saiu-topo");
  topo.append(
    el("h2", "saiu-titulo", "Saiu por último"),
    el("span", "saiu-sub", "Contra o que os analistas esperavam (Focus)"),
  );
  const lista = el("ul", "saiu-lista");
  for (const d of itens) {
    const li = el("li");
    const a = el("a", "saiu-item");
    a.href = `#${d.secao}`;
    const nome = el("span", "saiu-nome");
    nome.append(
      el("strong", undefined, d.nome),
      el("span", "saiu-periodo", d.nota ? `${d.periodo} · ${d.nota}` : d.periodo),
    );
    a.append(
      nome,
      el("span", "saiu-valor", comUnidade(d.valor, d.unidade, d.casas)),
      el("span", "saiu-leitura", leitura(d)),
      el("span", "saiu-contexto", contexto(d)),
    );
    li.append(a);
    lista.append(li);
  }
  const nota = el(
    "p",
    "saiu-nota",
    "“Costuma errar”: a média do erro do Focus nas divulgações do último ano (dois anos, no " +
      "PIB). PIB e desocupação são revistos depois de sair. " +
      "Fontes: IBGE e Banco Central (SGS, Copom e Focus).",
  );
  caixa.append(topo, lista, nota);
  return caixa;
}
