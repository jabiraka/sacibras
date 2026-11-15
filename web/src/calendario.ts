// As próximas divulgações do IBGE, buscadas pelo navegador direto na API de calendário
// (servicodados.ibge.gov.br/api/v3/calendario, CORS aberto: conferido no PC em 14/11/2026).
// A API derruba quem está fora do Brasil (o GitHub Actions), por isso não passa pelo builder.
// Se a busca falhar ou demorar, a linha simplesmente não aparece.

import { el } from "./pecas";

const ESPERA_MS = 6000;
const DIAS_A_FRENTE = 75;
const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const SEMANA = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];

/** A pesquisa do IBGE (pelo `alias_produto`), o nome curto na tela e os assuntos onde entra. */
const PESQUISAS: Record<string, { nome: string; assuntos: string[]; movel?: boolean }> = {
  "indice-nacional-de-precos-ao-consumidor-amplo": { nome: "IPCA", assuntos: ["inflacao"] },
  "indice-nacional-de-precos-ao-consumidor-amplo-15": { nome: "IPCA-15", assuntos: ["inflacao"] },
  "indice-nacional-de-precos-ao-consumidor": { nome: "INPC", assuntos: ["inflacao"] },
  "pesquisa-nacional-por-amostra-de-domicilios-continua-mensal": {
    nome: "Desemprego (PNAD)",
    assuntos: ["trabalho"],
    movel: true,
  },
  "pesquisa-nacional-por-amostra-de-domicilios-continua-trimestral": {
    nome: "PNAD por estado",
    assuntos: ["trabalho", "estados"],
  },
  "contas-nacionais-trimestrais": { nome: "PIB", assuntos: ["atividade", "previsoes"] },
  "pesquisa-industrial-mensal-producao-fisica-brasil": {
    nome: "Produção industrial",
    assuntos: ["atividade"],
  },
  "pesquisa-mensal-de-comercio": { nome: "Varejo", assuntos: ["atividade"] },
  "pesquisa-mensal-de-servicos": { nome: "Serviços", assuntos: ["atividade"] },
};

interface ItemDaApi {
  alias_produto?: string;
  data_divulgacao?: string;
  ano_referencia_inicio?: number;
  mes_referencia_inicio?: number;
  ano_referencia_fim?: number;
  mes_referencia_fim?: number;
}

export interface Divulgacao {
  nome: string;
  quando: Date;
  referente: string;
}

/** "11-14-2026": o formato que a API pede em `de` e `ate`. */
function paraApi(d: Date): string {
  const p = (n: number): string => String(n).padStart(2, "0");
  return `${p(d.getMonth() + 1)}-${p(d.getDate())}-${d.getFullYear()}`;
}

/** "11/12/2026 12:00:00" → a data, sem a hora (a API não diz o fuso). */
function lerData(texto: string): Date | null {
  const m = /^(\d{2})\/(\d{2})\/(\d{4})/.exec(texto);
  return m ? new Date(Number(m[3]), Number(m[2]) - 1, Number(m[1])) : null;
}

/** O período a que a divulgação se refere: "nov/2026", "3º tri/2026", "ago–out/2026" (móvel). */
export function referente(i: ItemDaApi, movel = false): string {
  const ano = i.ano_referencia_inicio ?? 0;
  const ini = i.mes_referencia_inicio ?? 0;
  const fim = i.mes_referencia_fim ?? 0;
  if (!ano || !ini) return "";
  if (fim && fim - ini === 2 && ini % 3 === 1) return `${(ini + 2) / 3}º tri/${ano}`;
  const mes = `${MESES[ini - 1] ?? ""}/${ano}`;
  // A PNAD mensal é o trimestre móvel que termina no mês de referência.
  return movel ? `${MESES[(ini + 9) % 12] ?? ""}–${mes}` : mes;
}

export function separar(itens: ItemDaApi[], hoje: Date): Map<string, Divulgacao[]> {
  const inicioDoDia = new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate());
  const porAssunto = new Map<string, Divulgacao[]>();
  const vistos = new Set<string>();
  const ordenados = itens
    .map((i) => ({ i, quando: lerData(i.data_divulgacao ?? "") }))
    .filter((x): x is { i: ItemDaApi; quando: Date } => x.quando !== null && x.quando >= inicioDoDia)
    .sort((a, b) => a.quando.getTime() - b.quando.getTime());
  for (const { i, quando } of ordenados) {
    const pesquisa = PESQUISAS[i.alias_produto ?? ""];
    // Só a próxima de cada pesquisa.
    if (!pesquisa || vistos.has(i.alias_produto ?? "")) continue;
    vistos.add(i.alias_produto ?? "");
    const d: Divulgacao = { nome: pesquisa.nome, quando, referente: referente(i, pesquisa.movel) };
    for (const a of pesquisa.assuntos) porAssunto.set(a, [...(porAssunto.get(a) ?? []), d]);
  }
  return porAssunto;
}

let pedido: Promise<Map<string, Divulgacao[]>> | null = null;

function proximas(): Promise<Map<string, Divulgacao[]>> {
  if (!pedido) {
    pedido = (async () => {
      const hoje = new Date();
      const ate = new Date(hoje.getTime() + DIAS_A_FRENTE * 86_400_000);
      const controle = new AbortController();
      const relogio = setTimeout(() => controle.abort(), ESPERA_MS);
      try {
        const url =
          "https://servicodados.ibge.gov.br/api/v3/calendario/" +
          `?de=${paraApi(hoje)}&ate=${paraApi(ate)}&qtd=300`;
        const resposta = await fetch(url, { signal: controle.signal });
        if (!resposta.ok) return new Map();
        const corpo = (await resposta.json()) as { items?: ItemDaApi[] };
        return separar(corpo.items ?? [], hoje);
      } catch {
        return new Map();
      } finally {
        clearTimeout(relogio);
      }
    })();
    // Falhou? Na próxima vez tenta de novo.
    void pedido.then((m) => {
      if (!m.size) pedido = null;
    });
  }
  return pedido;
}

function dia(d: Date): string {
  const dia = String(d.getDate()).padStart(2, "0");
  return `${SEMANA[d.getDay()]}, ${dia}/${MESES[d.getMonth()]}`;
}

/** As divulgações de hoje até daqui a `dias` dias, uma vez cada (a PNAD por estado entra em
 *  dois assuntos), em ordem de data, com o primeiro assunto em que entra. */
export function daSemana(
  porAssunto: Map<string, Divulgacao[]>,
  hoje: Date,
  dias = 7,
): (Divulgacao & { assunto: string })[] {
  const inicio = new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate());
  const fim = new Date(inicio.getFullYear(), inicio.getMonth(), inicio.getDate() + dias);
  const vistas = new Map<string, Divulgacao & { assunto: string }>();
  for (const [assunto, lista] of porAssunto) {
    for (const d of lista) {
      const chave = `${d.nome}|${d.quando.getTime()}`;
      if (d.quando >= inicio && d.quando < fim && !vistas.has(chave)) {
        vistas.set(chave, { ...d, assunto });
      }
    }
  }
  return [...vistas.values()].sort((a, b) => a.quando.getTime() - b.quando.getTime());
}

/** "O que sai esta semana", na entrada, guardado atrás de um clique: o calendário do IBGE só
 *  é lido quando a pessoa abre. Cada divulgação leva ao assunto dela. */
export function agendaDaSemana(assuntos: { id: string; titulo: string }[]): HTMLElement {
  const caixa = el("details", "vidro agenda-semana");
  const resumo = el("summary");
  resumo.append(
    el("span", "agenda-semana-titulo", "O que sai esta semana"),
    el("span", "agenda-semana-sub", "As próximas divulgações do IBGE, nos próximos 7 dias"),
  );
  const corpo = el("div", "agenda-semana-corpo");
  caixa.append(resumo, corpo);
  let pedido = false;
  caixa.addEventListener("toggle", () => {
    if (!caixa.open || pedido) return;
    pedido = true;
    corpo.replaceChildren(el("p", "agenda-semana-vazio", "Lendo o calendário do IBGE…"));
    void proximas().then((porAssunto) => {
      if (!porAssunto.size) {
        pedido = false; // tenta de novo no próximo clique
        corpo.replaceChildren(
          el("p", "agenda-semana-vazio", "O calendário do IBGE não respondeu agora. Tente mais tarde."),
        );
        return;
      }
      const semana = daSemana(porAssunto, new Date());
      if (!semana.length) {
        corpo.replaceChildren(
          el("p", "agenda-semana-vazio", "Nenhuma das pesquisas do painel sai nos próximos 7 dias."),
        );
      } else {
        const lista = el("ul", "agenda-semana-lista");
        for (const d of semana) {
          const li = el("li");
          const elo = el("a", "agenda-semana-item");
          elo.href = `#${d.assunto}`;
          const oQue = el("span", "agenda-semana-o-que");
          oQue.append(
            el("strong", "", d.nome),
            document.createTextNode(d.referente ? ` de ${d.referente}` : ""),
          );
          elo.append(el("span", "agenda-semana-dia", dia(d.quando)), oQue);
          const assunto = assuntos.find((a) => a.id === d.assunto);
          if (assunto) elo.append(el("span", "agenda-semana-assunto", assunto.titulo));
          li.append(elo);
          lista.append(li);
        }
        corpo.replaceChildren(lista);
      }
      corpo.append(el("p", "agenda-fonte", "Fonte: calendário de divulgações do IBGE"));
    });
  });
  return caixa;
}

/** "Próximas divulgações: IPCA de nov/2026, sex, 11/dez · …". Vazio se nada vier. */
export function agendaDoAssunto(assunto: string): HTMLElement {
  const caixa = el("p", "agenda");
  caixa.hidden = true;
  void proximas().then((porAssunto) => {
    const lista = porAssunto.get(assunto);
    if (!lista?.length) return;
    caixa.append(el("span", "agenda-titulo", lista.length > 1 ? "Próximas divulgações" : "Próxima divulgação"));
    for (const d of lista) {
      const item = el("span", "agenda-item");
      item.append(
        el("strong", "", d.nome),
        document.createTextNode(`${d.referente ? ` de ${d.referente}` : ""}: ${dia(d.quando)}`),
      );
      caixa.append(item);
    }
    caixa.append(el("span", "agenda-fonte", "Fonte: calendário de divulgações do IBGE"));
    caixa.hidden = false;
  });
  return caixa;
}
