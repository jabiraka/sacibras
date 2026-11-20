// Um ponto por país, com duas métricas (em Impostos, a carga tributária contra o
// crescimento). O desenho é o mesmo de "Brasil no mundo" (`desenharDispersao`): o Brasil em
// verde e com nome, os outros em cinza; quem fica muito longe dos outros sai do desenho e
// a nota diz quem é, com o botão para mostrar todos. A tabela com todos os países fica
// guardada embaixo, como a dos outros gráficos.

import { numero } from "./formato";
import { botoesDaImagem, textoSemBotoes } from "./grafico";
import { el } from "./pecas";
import { desenharDispersao, type PontoDisperso } from "./pontos";
import type { Dispersao, Grafico } from "./tipos";

export function montarDispersao(g: Grafico, d: Dispersao): HTMLElement {
  const artigo = el("article", `grafico ${g.largura === "inteira" ? "inteira" : ""}`);
  artigo.id = `g-${g.id}`;
  const cabeca = el("header", "grafico-cabeca");
  const titulos = el("div");
  titulos.append(el("h3", "", g.titulo), el("p", "sub", g.subtitulo));
  cabeca.append(titulos);
  artigo.append(cabeca);

  const destaque = d.destaque ?? "BRA";
  const nomeDestaque = d.nome_destaque ?? "Brasil";
  const nomeOutros = d.nome_outros ?? "Outros países";
  const legenda = el("div", "legenda");
  const item = el("span", "legenda-item");
  const chave = el("i", "chave redonda");
  chave.style.setProperty("--cor", "var(--verde)");
  item.append(chave, document.createTextNode(nomeDestaque));
  const outros = el("span", "legenda-item");
  const chaveOutros = el("i", "chave redonda");
  chaveOutros.style.setProperty("--cor", "var(--eixo)");
  outros.append(chaveOutros, document.createTextNode(nomeOutros));
  legenda.append(item, outros);
  artigo.append(legenda);

  const tela = el("div", "tela-dispersao");
  const aviso = el("p", "posicao");
  artigo.append(tela, aviso);

  const pe = el("footer", "grafico-pe");
  pe.append(el("span", "fonte", `Fonte: ${g.fonte}`));
  const acoes = el("span", "acoes");
  const verTabela = el("button", "", "Tabela");
  verTabela.type = "button";
  verTabela.setAttribute("aria-expanded", "false");
  acoes.append(verTabela);
  // A imagem das duas métricas, para baixar ou copiar (Caio, 16/11/2026); dado privado não.
  if (!g.sem_download) {
    const css = getComputedStyle(document.documentElement);
    acoes.append(
      ...botoesDaImagem(() => ({
        id: g.id,
        titulo: g.titulo,
        sub: g.subtitulo,
        fonte: `Fonte: ${g.fonte}`,
        nota: textoSemBotoes(aviso),
        legenda: [
          {
            nome: nomeDestaque,
            chave: "ponto",
            cor: css.getPropertyValue("--verde").trim(),
          },
          {
            nome: nomeOutros,
            chave: "ponto",
            cor: css.getPropertyValue("--eixo").trim(),
          },
        ],
        svg: tela.querySelector("svg"),
      })),
    );
  }
  pe.append(acoes);
  artigo.append(pe);
  if (g.nota) artigo.append(el("p", "nota", g.nota));

  const caixaTabela = el("div", "tabela-rolavel");
  caixaTabela.hidden = true;
  artigo.append(caixaTabela);
  verTabela.addEventListener("click", () => {
    if (!caixaTabela.firstChild) caixaTabela.append(tabela(g, d));
    caixaTabela.hidden = !caixaTabela.hidden;
    verTabela.setAttribute("aria-expanded", String(!caixaTabela.hidden));
  });

  const pontos: PontoDisperso[] = d.pontos.map((p) => ({
    chave: p.chave,
    nome: p.nome,
    x: p.x,
    y: p.y,
    marca: p.chave === destaque ? "brasil" : "comum",
    rotulo: p.chave === destaque || d.rotular_todos === true,
  }));
  let comExtremos = false;
  const desenhar = (): void => {
    if (!tela.clientWidth) return;
    const fora = desenharDispersao(tela, pontos, d.eixo_x, d.eixo_y, undefined, comExtremos);
    aviso.replaceChildren();
    if (fora.length || comExtremos) {
      if (fora.length) {
        const lista = fora
          .slice(0, 6)
          .map((p) => `${p.nome} (${numero(p.x, d.eixo_x.casas)}; ${numero(p.y, d.eixo_y.casas)})`)
          .join(", ");
        aviso.append(
          document.createTextNode(
            `Fora do desenho, por estarem muito longe dos outros: ${lista}${fora.length > 6 ? ` e mais ${fora.length - 6}` : ""}. `,
          ),
        );
      }
      const botao = el("button", "botao-texto", comExtremos ? "Tirar os valores extremos" : "Mostrar todos");
      botao.type = "button";
      botao.addEventListener("click", () => {
        comExtremos = !comExtremos;
        desenhar();
      });
      aviso.append(botao);
    }
  };
  let pendente = 0;
  new ResizeObserver(() => {
    cancelAnimationFrame(pendente);
    pendente = requestAnimationFrame(desenhar);
  }).observe(tela);
  return artigo;
}

function tabela(g: Grafico, d: Dispersao): HTMLTableElement {
  const t = el("table", "dados");
  const cab = t.createTHead().insertRow();
  cab.append(
    el("th", "", d.coluna ?? "País"),
    el("th", "", `${d.eixo_x.nome} (${d.eixo_x.unidade})`),
    el("th", "", `${d.eixo_y.nome} (${d.eixo_y.unidade})`),
  );
  const corpo = t.createTBody();
  const porChave = (d.coluna ?? "País") !== "País";
  const ordenados = [...d.pontos].sort((a, b) => (porChave ? b.chave.localeCompare(a.chave) : b.x - a.x));
  for (const p of ordenados) {
    const linha = corpo.insertRow();
    linha.append(
      el("th", "", p.nome),
      el("td", "", numero(p.x, d.eixo_x.casas)),
      el("td", "", numero(p.y, d.eixo_y.casas)),
    );
  }
  t.createCaption().textContent = `${g.titulo}, ${g.subtitulo}`;
  return t;
}
