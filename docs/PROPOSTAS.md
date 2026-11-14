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

## Do Econvitals para o Brasil (Caio, 14/11/2026: *"veja se algumas métricas do Econvitals dá pra implementar aqui"*)

Lido do `data/dashboard.json` do econvitals.org em 14/11/2026. O que tem par brasileiro em
fonte aberta:

| Econvitals (EUA) | Par brasileiro | Fonte | Situação |
|------------------|----------------|-------|----------|
| 2, 5, 10 e 30 anos; 2s10s | juro prefixado de 2, 5 e 10 anos e a inclinação | curva zero do Tesouro (`curvas.py`) | ✅ tabela "Juro e inflação implícita por prazo" (Juros) |
| Real 10y, breakeven 10y, 5y5y forward | juro real e inflação implícita de 5 e 10 anos; a implícita de 5 anos daqui a 5 anos | idem | ✅ na tabela e no cartão da implícita de 5 a 10 anos (6,98 % em 12/11/2026) |
| 10-year decomposition | o prefixado de 10 anos = juro real + inflação implícita, no tempo | idem, um ponto por semana | ✅ no maior prazo que cobre os dois anos (8 anos hoje: o de 10 não existia em 2025) |
| Core PCE 1 e 3 meses anualizados; tabela de medidas | IPCA, núcleos, serviços, industriais, alimentação, livres e administrados em 1, 3 e 12 meses | SGS | ✅ tabela, gráfico e cartão (sem ajuste sazonal, dito na tela). Falta: serviços subjacentes (código SGS não achado) |
| Participação, EPOP, U-6, desemprego de longo prazo | participação, nível de ocupação, subutilização, desalento, informalidade | SIDRA (PNAD Contínua) | ✅ quatro cartões, cinco gráficos e a tabela "Mercado de trabalho, em detalhe" |
| Payrolls com média de 3 meses, por setor | Caged com média de 3 meses, por setor | IPEADATA / Novo Caged | ✅ média de 3 meses. Falta: por setor (o IPEADATA não tem; as séries SGS 28764 a 28783 parecem setoriais, mas sem nome que dê para ler) |
| Current e financial account em partes | balança, renda primária e secundária; investimento direto, carteira, outros, reservas | SGS (BPM6) | ✅ gráfico empilhado e tabela em US$ e % do PIB |
| Mortgage rate, house prices | juro do financiamento imobiliário, IVG-R (preço dos imóveis financiados) | SGS | ✅ juro de mercado e regulado, concessões, IVG-R contra o IPCA |
| Debt service, interest payments | comprometimento da renda só com juros, endividamento sem o imobiliário | SGS | ✅ |
| Saving rate, investimento | taxa de investimento e de poupança (% do PIB) | SIDRA (contas trimestrais) | ideia |
| Real final sales to private domestic purchasers | consumo das famílias + investimento, sem governo e estoques | SIDRA | ideia |
| Productivity | PIB por pessoa ocupada | SIDRA | ideia |
| FedWatch (probabilidades da reunião) | probabilidade do Copom pelos DI curtos | B3 (desligada) | espera o `SB_B3` |
| VIX, NFCI, petróleo, metais | risco-país, Brent, minério | sem fonte aberta estável (EMBI parou em 2024) | fora por ora |
| UMich, Cleveland | expectativa do consumidor (FGV) | FGV cobra | fora |

## Outras

- Previsões próprias de IPCA e desocupação (modelo sazonal), sempre ao lado do Focus.
- Brasil no mundo: câmbio no ano (BIS `WS_XRU`), juro de 10 anos (OCDE), inflação mensal.
- Acabamento: "novo desde sua última visita", PNG dos gráficos, imagem de compartilhamento,
  domínio.
