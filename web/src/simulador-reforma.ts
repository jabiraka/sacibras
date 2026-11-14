// O simulador da reforma do consumo: quanto de IBS e CBS vai numa compra.
// As regras vêm do builder e são lei lida (`leis.py`: a alíquota zero da cesta básica, os
// descontos de 60 % e 30 %, a devolução à baixa renda) ou conta oficial (`relatorios.py`: a CBS
// de 2027 pelo TCU, a alíquota cheia pelo Comitê Gestor do IBS). Aqui só se multiplica.
// A mesma conta está em `builder/src/sacibras/modelos/reforma.py`, com teste.
//
// A alíquota de 2033 não existe ainda: o resultado vem sempre com a faixa entre o teto da lei
// e a soma das contas oficiais mais recentes (Caio, 14/11/2026: nenhum número sem a faixa).

import { numero } from "./formato";
import { el } from "./pecas";
import { listaSuspensa } from "./pontos";
import type { EtapaDaReforma, SimuladorReforma, TipoDeCompra } from "./tipos";

export interface Compra {
  cbs: number;
  ibs: number;
  imposto: number;
  devolucao: number;
}

/** `valor` é o preço sem IBS nem CBS; as alíquotas são as cheias, em %. */
export function compra(
  valor: number,
  tipo: TipoDeCompra,
  cbs: number,
  ibs: number,
  baixaRenda: boolean,
  devolveIbs: boolean,
): Compra {
  const pagoCbs = (valor * cbs * tipo.paga) / 10000;
  const pagoIbs = (valor * ibs * tipo.paga) / 10000;
  const devolucao = baixaRenda
    ? (pagoCbs * tipo.volta_cbs) / 100 + (devolveIbs ? (pagoIbs * tipo.volta_ibs) / 100 : 0)
    : 0;
  return { cbs: pagoCbs, ibs: pagoIbs, imposto: pagoCbs + pagoIbs, devolucao };
}

const reais = (v: number): string => `R$ ${numero(v, 2)}`;

function quadro(rotulo: string): { no: HTMLElement; valor: HTMLElement; faixa: HTMLElement; detalhe: HTMLElement } {
  const no = el("div", "cartao efeito");
  const valor = el("span", "cartao-valor");
  const faixa = el("span", "efeito-faixa");
  const detalhe = el("span", "cartao-detalhe");
  no.append(el("span", "cartao-rotulo", rotulo), valor, faixa, detalhe);
  return { no, valor, faixa, detalhe };
}

export function montarSimuladorReforma(s: SimuladorReforma): HTMLElement[] {
  let valor = 100;
  let tipo: TipoDeCompra | undefined = s.tipos[0];
  let etapa: EtapaDaReforma | undefined = s.etapas.find((e) => e.id === s.etapa_inicial) ?? s.etapas[0];
  let aliquota = s.aliquota;
  let baixaRenda = false;

  const painel = el("div", "simulador");
  const campos = el("div", "barra-controles");

  const campoValor = el("label", "escolha-campo");
  campoValor.htmlFor = "ref-valor";
  const entradaValor = el("input", "escolha");
  entradaValor.id = "ref-valor";
  entradaValor.type = "number";
  entradaValor.min = "0";
  entradaValor.step = "10";
  entradaValor.inputMode = "decimal";
  entradaValor.value = String(valor);
  campoValor.append(el("span", "escolha-rotulo", "Valor sem o imposto (R$)"), entradaValor);

  const listaTipo = listaSuspensa(
    "ref-tipo",
    "O que é a compra",
    s.tipos.map((t) => ({ valor: t.id, rotulo: t.rotulo })),
    tipo?.id ?? "",
    (v) => {
      tipo = s.tipos.find((t) => t.id === v) ?? tipo;
      pintar();
    },
  );
  const listaEtapa = listaSuspensa(
    "ref-etapa",
    "Quando",
    s.etapas.map((e) => ({ valor: e.id, rotulo: e.rotulo })),
    etapa?.id ?? "",
    (v) => {
      etapa = s.etapas.find((e) => e.id === v) ?? etapa;
      pintar();
    },
  );
  campos.append(campoValor, listaTipo.caixa, listaEtapa.caixa);

  const linhaAliquota = el("label", "controle");
  const textoAliquota = el("span", "controle-rotulo", "Alíquota cheia (IBS + CBS)");
  textoAliquota.append(el("small", "", "ainda não existe: escolha dentro das contas oficiais"));
  const entradaAliquota = el("input");
  entradaAliquota.type = "range";
  entradaAliquota.id = "ref-aliquota";
  entradaAliquota.min = String(Math.floor(s.aliquota_minima - 1));
  entradaAliquota.max = String(Math.ceil(s.aliquota_maxima + 0.5));
  entradaAliquota.step = "0.1";
  entradaAliquota.value = String(aliquota);
  const saidaAliquota = el("output", "controle-valor");
  saidaAliquota.htmlFor.add(entradaAliquota.id);
  linhaAliquota.append(textoAliquota, entradaAliquota, saidaAliquota);

  const marcas = el("div", "cenarios");
  for (const m of s.marcas) {
    const botao = el("button", "botao", `${m.rotulo}: ${numero(m.valor, 1)} %`);
    botao.type = "button";
    botao.addEventListener("click", () => {
      aliquota = m.valor;
      entradaAliquota.value = String(m.valor);
      pintar();
    });
    marcas.append(botao);
  }

  const linhaRenda = el("label", "marcar");
  const caixaRenda = el("input");
  caixaRenda.type = "checkbox";
  caixaRenda.id = "ref-baixa-renda";
  linhaRenda.append(
    caixaRenda,
    el("span", "", "Família de baixa renda (Cadastro Único, até meio salário mínimo por pessoa)"),
  );

  painel.append(campos, linhaAliquota, marcas, linhaRenda);

  const frase = el("p", "posicao");
  const quadros = el("div", "efeitos");
  const imposto = quadro("IBS e CBS nesta compra");
  const preco = quadro("Preço com o imposto");
  const volta = quadro("Volta para a família");
  quadros.append(imposto.no, preco.no, volta.no);
  const aviso = el("p", "nota");

  function pintar(): void {
    if (!tipo || !etapa) return;
    const fixa = etapa.cbs !== null && etapa.ibs !== null;
    linhaAliquota.hidden = fixa;
    marcas.hidden = fixa;
    const partes = (total: number): [number, number] => [total * (1 - s.parte_do_ibs), total * s.parte_do_ibs];
    const [cbs, ibs] = fixa ? [etapa.cbs ?? 0, etapa.ibs ?? 0] : partes(aliquota);
    const conta = (c: number, i: number): Compra =>
      compra(valor, tipo as TipoDeCompra, c, i, baixaRenda, (etapa as EtapaDaReforma).devolve_ibs);
    const meio = conta(cbs, ibs);
    const baixo = conta(...partes(s.aliquota_minima));
    const alto = conta(...partes(s.aliquota_maxima));
    const cheia = cbs + ibs;
    const efetiva = (cheia * tipo.paga) / 100;
    saidaAliquota.textContent = `${numero(aliquota, 1)} %`;

    frase.replaceChildren(
      document.createTextNode(`Numa compra de ${reais(valor)} sem o imposto, `),
      el(
        "b",
        "",
        tipo.paga === 0
          ? "a alíquota é zero: não há IBS nem CBS."
          : `com a alíquota cheia de ${numero(cheia, 1)} %${tipo.paga < 100 ? ` e ${numero(100 - tipo.paga, 0)} % de desconto (paga ${numero(efetiva, 1)} %)` : ""}:`,
      ),
    );

    const semFaixa = fixa || tipo.paga === 0;
    imposto.valor.textContent = reais(meio.imposto);
    imposto.faixa.textContent = semFaixa
      ? fixa && tipo.paga > 0
        ? "alíquota calculada pelo TCU; o Senado ainda fixa"
        : ""
      : `faixa: de ${reais(baixo.imposto)} a ${reais(alto.imposto)}`;
    imposto.detalhe.textContent =
      tipo.paga === 0
        ? `${tipo.descricao} (${tipo.norma}).`
        : `CBS ${reais(meio.cbs)} e IBS ${reais(meio.ibs)}. ${tipo.descricao} (${tipo.norma}).`;

    const final = valor + meio.imposto;
    preco.valor.textContent = reais(final);
    preco.faixa.textContent = semFaixa
      ? ""
      : `faixa: de ${reais(valor + baixo.imposto)} a ${reais(valor + alto.imposto)}`;
    preco.detalhe.textContent = fixa
      ? "Só com o IBS e a CBS: falta somar o ICMS ou o ISS, que seguem valendo."
      : final > 0
        ? `Do que se paga, ${numero((meio.imposto / final) * 100, 1)} % é imposto.`
        : "";

    volta.no.hidden = !baixaRenda;
    if (baixaRenda) {
      volta.valor.textContent = reais(meio.devolucao);
      volta.faixa.textContent =
        semFaixa || meio.devolucao === 0
          ? ""
          : `faixa: de ${reais(baixo.devolucao)} a ${reais(alto.devolucao)}`;
      const doIbs = etapa.devolve_ibs ? `${numero(tipo.volta_ibs, 0)} % do IBS` : "o IBS ainda não volta";
      volta.detalhe.textContent =
        meio.imposto === 0
          ? "Nada a devolver: a compra não paga IBS nem CBS."
          : `${numero(tipo.volta_cbs, 0)} % da CBS e ${doIbs}. No fim, a família paga ${reais(meio.imposto - meio.devolucao)} de imposto.`;
    }
    aviso.textContent = etapa.aviso;
  }

  entradaValor.addEventListener("input", () => {
    const lido = Number(entradaValor.value.replace(",", "."));
    valor = Number.isFinite(lido) && lido >= 0 ? lido : 0;
    pintar();
  });
  entradaAliquota.addEventListener("input", () => {
    aliquota = Number(entradaAliquota.value);
    pintar();
  });
  caixaRenda.addEventListener("change", () => {
    baixaRenda = caixaRenda.checked;
    pintar();
  });
  pintar();

  const pe = el("footer", "grafico-pe");
  pe.append(el("span", "fonte", `Fonte: ${s.fonte}`));
  return [painel, frase, quadros, aviso, pe, el("p", "nota", `${s.como_ler}\n\n${s.nota}`)];
}
