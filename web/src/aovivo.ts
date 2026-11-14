// O ponto mais novo de um número, buscado pelo navegador direto na fonte (SGS e SIDRA têm
// CORS aberto). O JSON do builder é o piso: se a busca falhar, demorar ou não trouxer data mais
// nova, fica o número do builder e nada muda na tela.

import type { Cartao } from "./tipos";

const ESPERA_MS = 6000;

async function buscar(url: string): Promise<unknown> {
  const controle = new AbortController();
  const relogio = setTimeout(() => controle.abort(), ESPERA_MS);
  try {
    const resposta = await fetch(url, { signal: controle.signal, cache: "no-cache" });
    if (!resposta.ok) return null;
    return await resposta.json();
  } catch {
    return null;
  } finally {
    clearTimeout(relogio);
  }
}

/** "13/11/2026" → "2026-11-13". */
function dataDoSgs(texto: string): string {
  const [d, m, a] = texto.split("/");
  return `${a}-${m}-${d}`;
}

/** O código de período do SIDRA ("202602" = 2º tri; "202609" = setembro) em data ISO. */
function dataDoSidra(codigo: string, trimestral: boolean): string {
  const ano = codigo.slice(0, 4);
  const n = Number(codigo.slice(4, 6));
  const mes = trimestral ? 3 * n - 2 : n;
  return `${ano}-${String(mes).padStart(2, "0")}-01`;
}

/** [data ISO, valor] do ponto mais recente na fonte, ou null. */
export async function pontoMaisNovo(c: Cartao): Promise<[string, number] | null> {
  const av = c.ao_vivo;
  if (!av) return null;
  if (av.tipo === "sgs" && av.codigo) {
    const dados = await buscar(
      `https://api.bcb.gov.br/dados/serie/bcdata.sgs.${av.codigo}/dados/ultimos/1?formato=json`,
    );
    if (!Array.isArray(dados) || !dados.length) return null;
    const ultimo = dados[dados.length - 1] as { data?: string; valor?: string };
    const valor = Number(ultimo.valor);
    if (!ultimo.data || !Number.isFinite(valor)) return null;
    return [dataDoSgs(ultimo.data), valor * av.escala];
  }
  if (av.tipo === "sidra" && av.caminho) {
    const dados = await buscar(`https://apisidra.ibge.gov.br/values/${av.caminho}`);
    if (!Array.isArray(dados) || dados.length < 2) return null;
    const cabecalho = dados[0] as Record<string, string>;
    const linha = dados[dados.length - 1] as Record<string, string>;
    const coluna = Object.keys(cabecalho).find(
      (k) => k.endsWith("C") && /^(Trimestre|Mês)/.test(cabecalho[k] ?? ""),
    );
    const valor = Number(linha.V);
    if (!coluna || !linha[coluna] || !Number.isFinite(valor)) return null;
    const trimestral = (cabecalho[coluna] ?? "").startsWith("Trimestre");
    return [dataDoSidra(linha[coluna] ?? "", trimestral), valor * av.escala];
  }
  return null;
}
