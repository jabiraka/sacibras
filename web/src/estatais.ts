// Uma estatal federal por dentro (Caio, 25/11/2026: "abra por estatal um dashboard com
// informações mais relevantes, principalmente histórico de performance, receita ou prejuízo
// e outras métricas relevantes para analisar empresas"). A pessoa escolhe a empresa na lista
// (por setor); a ficha mostra quatro números, o gráfico de receita e lucro com os outros atrás
// da lista "Gráfico" e a tabela de todos os anos, guardada. O arquivo das fichas só é lido
// quando a parte abre.

import { remarcar } from "./glossario";
import { el } from "./pecas";
import { listaSuspensa } from "./pontos";
import type {
  Cartao,
  FichaEstatal,
  FichasEstatais,
  Grafico,
  Tabela,
} from "./tipos";

export interface Construtores {
  ler: (arquivo: string) => Promise<FichasEstatais>;
  cartao: (c: Cartao) => HTMLElement;
  peca: (g: Grafico) => HTMLElement;
  tabela: (t: Tabela) => HTMLElement;
}

export const ID_DA_LISTA = "estatais-ficha";

/** A caixa da ficha; `inicial` é o id da estatal pedida no endereço (`#fiscal/e-ect`). */
export function montarFichasEstatais(
  arquivo: string,
  f: Construtores,
  inicial: string,
): HTMLElement {
  const painel = el("section", "painel-mundo ficha-estatal");
  painel.id = "fichas-estatais";
  painel.append(el("h3", "ficha-estatal-titulo", "Uma estatal por dentro"));
  const carregando = el("p", "nota", "Carregando as estatais…");
  painel.append(carregando);
  f.ler(arquivo)
    .then((dados) => {
      const corpo = el("div", "ficha-estatal-corpo");
      const porId = new Map(dados.fichas.map((x) => [x.id, x]));
      const abrir = (id: string): void => {
        const ficha = porId.get(id);
        if (!ficha) return;
        corpo.replaceChildren(...conteudo(ficha, f));
        remarcar(corpo);
      };
      const primeira = porId.has(inicial) ? inicial : dados.primeira;
      const { caixa } = listaSuspensa(
        ID_DA_LISTA,
        "Estatal",
        dados.fichas.map((x) => ({
          valor: x.id,
          rotulo: x.nome,
          grupo: x.setor,
        })),
        primeira,
        abrir,
      );
      const barra = el("div", "barra-controles");
      barra.append(caixa);
      carregando.replaceWith(barra, corpo);
      abrir(primeira);
    })
    .catch((erro: unknown) => {
      carregando.textContent = `Não foi possível carregar as estatais (${String(erro)}).`;
    });
  return painel;
}

function conteudo(x: FichaEstatal, f: Construtores): HTMLElement[] {
  const cabeca = el("div", "ficha-estatal-cabeca");
  cabeca.append(
    el("p", "ficha-estatal-nome", x.nome_completo),
    el("p", "nota", x.descricao),
  );
  const cartoes = el("div", "cartoes");
  x.cartoes.forEach((c) => cartoes.append(f.cartao(c)));
  const graficos = el("div", "graficos");
  graficos.append(f.peca(x.grafico));
  return [cabeca, cartoes, graficos, f.tabela(x.tabela)];
}
