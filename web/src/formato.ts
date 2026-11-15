// Formato brasileiro: "4,5 %", "R$ 1,2 tri", "out/2026", "3º tri/2026".

import type { Periodicidade } from "./tipos";

const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

export function data(iso: string): Date {
  const [a, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(a ?? 1970, (m ?? 1) - 1, d ?? 1));
}

export function numero(valor: number, casas = 1): string {
  // O sinal de menos tipográfico (−) e não o hífen: o hífen fica curto e solto ("- 2").
  return valor
    .toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas })
    .replace(/^-/, "−");
}

/** O valor com a unidade do jeito que se lê: "13,75 % a.a.", "R$ 5,42", "128.450 pontos". */
export function comUnidade(valor: number, unidade: string, casas = 1): string {
  const n = numero(valor, casas);
  if (unidade.startsWith("%")) return `${n} ${unidade}`;
  if (unidade === "pp") return `${n} pp`;
  if (unidade === "R$/US$" || unidade === "R$") return `R$ ${n}`;
  // "R$ por pessoa", "R$ por mês, em reais de 2026": o símbolo antes do número.
  if (unidade.startsWith("R$ por ")) return `R$ ${n} ${unidade.slice(3)}`;
  if (unidade === "US$") return `US$ ${n}`;
  if (unidade === "R$ milhões") return dinheiro(valor * 1e6, "R$");
  if (unidade === "R$ bilhões") return dinheiro(valor * 1e9, "R$");
  if (unidade === "US$ milhões") return dinheiro(valor * 1e6, "US$");
  if (unidade === "US$ bilhões") return dinheiro(valor * 1e9, "US$");
  return `${n} ${unidade}`.trim();
}

/** "R$ 1,2 tri", "US$ 345,6 bi", "R$ 12,3 mi". */
export function dinheiro(valor: number, moeda = "R$"): string {
  const abs = Math.abs(valor);
  const sinal = valor < 0 ? "−" : "";
  const faixas: [number, string][] = [
    [1e12, "tri"],
    [1e9, "bi"],
    [1e6, "mi"],
    [1e3, "mil"],
  ];
  for (const [base, nome] of faixas) {
    if (abs >= base) return `${sinal}${moeda} ${numero(abs / base, 1)} ${nome}`;
  }
  return `${sinal}${moeda} ${numero(abs, 2)}`;
}

/** Só o número, para eixo e tabela (a unidade vai no título). */
export function eixo(valor: number, unidade: string, casas: number): string {
  if (unidade === "pontos" && Math.abs(valor) >= 10000) return `${numero(valor / 1000, 0)} mil`;
  const inteiro = Math.abs(valor - Math.round(valor)) < 1e-9;
  return numero(valor, inteiro ? 0 : Math.min(casas, 2));
}

export function periodo(iso: string, p: Periodicidade): string {
  const d = data(iso);
  const ano = d.getUTCFullYear();
  const mes = d.getUTCMonth();
  if (p === "A") return String(ano);
  if (p === "T") return `${Math.floor(mes / 3) + 1}º tri/${ano}`;
  if (p === "M") return `${MESES[mes]}/${ano}`;
  return `${String(d.getUTCDate()).padStart(2, "0")}/${String(mes + 1).padStart(2, "0")}/${ano}`;
}

export function dataHora(iso: string): string {
  const d = new Date(iso);
  const dia = d.toLocaleDateString("pt-BR", { timeZone: "America/Sao_Paulo" });
  const hora = d.toLocaleTimeString("pt-BR", {
    timeZone: "America/Sao_Paulo",
    hour: "2-digit",
    minute: "2-digit",
  });
  return `${dia}, ${hora}`;
}

export function mesCurto(d: Date): string {
  return MESES[d.getUTCMonth()] ?? "";
}

export function sinal(valor: number, casas = 1): string {
  const n = numero(Math.abs(valor), casas);
  if (valor > 0) return `+${n}`;
  if (valor < 0) return `−${n}`;
  return n;
}
