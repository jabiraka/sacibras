# Propostas

A lista do que foi pedido ou pensado e ainda não está pronto, e do que ficou pronto, com a
data. Pedido novo vira linha aqui antes de virar código. A ordem do que fazer agora fica no
[PROXIMOS-PASSOS](PROXIMOS-PASSOS.md).

## Pedidas pelo Caio em 14/11/2026

| Pedido | Situação |
|--------|----------|
| Comparar retornos em reais (mais em Mercados) | ✅ "Quanto rendeu R$ 100": Ibovespa, dólar, euro, CDI e poupança contra o IPCA, período em lista suspensa. Falta: Tesouro IPCA+ e prefixado (o CSV do Tesouro Direto tem o preço diário), ouro, IFIX e índices da B3 (dependem do `SB_B3`), Ibovespa com dividendos. |
| O Focus está abaixo dos títulos públicos? | ✅ Respondido na tela de Juros: os títulos contra o Focus no mesmo prazo, no juro e na inflação, com a distância numa frase e num cartão. |
| Barra de busca por nome ou sinônimo | ✅ Lupa no cabeçalho e caixa na entrada; índice `busca.json` com sinônimos (`busca.py`). Falta: sugestões quando nada é achado, busca por número ("13,75"). |
| Inflação implícita nos títulos (o Jabs tem uma curva) | ✅ Curva zero pelo método do Jabs (`curvas.py`). Falta: o trecho antes de mai/2029 (não há IPCA+ sem cupom mais curto; o cupom de IPCA da B3, DAP, depende do `SB_B3`). |
| O que dá para abrir por estado | Ver abaixo. |

## Por estado

Pronto em 14/11/2026 (a ficha do estado: escolha na lista ou toque no ranking):

- **Receita em partes** (DCA 2025, Anexo I-C): ICMS, IPVA, ITCMD, FPE, outras transferências da
  União, Fundeb, outros impostos, outras. Com a média dos estados ao lado.
- **Despesa por natureza** (DCA I-D): pessoal, custeio, investimentos, inversões, juros e
  amortização da dívida.
- **Despesa por função** (DCA I-E): previdência, educação, saúde, segurança, transporte,
  administração, encargos especiais, outras.
- **Dívida em partes** (RGF Anexo 02, 2º quadrimestre de 2026): renegociação com a União (Lei
  9.496/97), empréstimos no país e no exterior, precatórios; e o que se desconta (caixa,
  haveres).
- **Números soltos**: investimento em % da RCL (com a mediana), dívida com a União (R$, % da
  dívida, % da RCL), ICMS, IPVA, ITCMD e FPE por habitante com a posição entre as 27.

Ideias que ficam:

- **Estados no tempo**: a série de cada número do estado contra o Brasil (3º quadrimestre de
  cada ano, para não multiplicar as chamadas ao SICONFI).
- **Nota CAPAG** do Tesouro (CSV no Tesouro Transparente) e o que ela significa para o estado
  pegar empréstimo com garantia da União.
- **Previdência do estado** (RREO Anexo 04): déficit do regime próprio, servidores ativos e
  inativos.
- **Despesa por função per capita**: saúde e educação por habitante, contra os mínimos
  constitucionais (12 % e 25 %; só depois de ler a Constituição e a LC 141).
- **Regime de Recuperação Fiscal e Propag**: quem está, desde quando, o que muda na dívida com a
  União (precisa ler as leis).
- **Capitais**: os mesmos números para as 27 capitais (SICONFI tem os municípios).
- **Repasses da União**: FPE, SUS, Fundeb e emendas, mês a mês (Tesouro Transparente).
- **Comparação na ficha**: o estado contra a região e contra quem tem tamanho parecido.

## Outras

- Previsões próprias de IPCA e desocupação (modelo sazonal), sempre ao lado do Focus.
- Brasil no mundo: câmbio no ano (BIS `WS_XRU`), juro de 10 anos (OCDE), inflação mensal.
- Acabamento: "novo desde sua última visita", PNG dos gráficos, imagem de compartilhamento,
  domínio.
