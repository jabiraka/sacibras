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
| Glossário: tocar na palavra ou num "?" abre a definição num balão, sem sair da tela | ✅ 89 termos em `glossario.py` (`glossario.json`); o navegador sublinha a palavra no texto corrido e põe "?" no nome dos números, gráficos e alertas (`web/src/glossario.ts`). Falta: o glossário na busca ("o que é spread"), uma lista de todos os termos se alguém pedir. |
| Painel de alerta: classificar, não mostrar tudo de uma vez, dizer o que significa, por que é alerta e no que pode dar | ✅ grupos que abrem no toque (o com mais acesos em cima, um ponto por indicador), atalho com os seis piores acesos, e cada linha abre "O que é / Por que é alerta / Pode levar a" (`alertas.py`) com a história do indicador. |
| Brasil no mundo: os emergentes mudam só o gráfico ou a tabela também? Lista com muitas métricas | Mudavam só o ranking. ✅ Agora a lista "Países" (os 22 principais, médias dos grupos ou todos os países de um grupo do FMI) vale para ranking, duas métricas e tabela; métricas agrupadas por tema na lista; grupo inteiro rola numa caixa com o Brasil à vista. |
| Painel de alerta: comparar com outros países, sobretudo os parecidos, e outras formas de ver além da régua da história | ✅ lista "Ver os alertas": contra a própria história; contra outros países (emergentes por padrão, América Latina, os 22 de Brasil no mundo, avançados, mundo; FMI e BIS, mesmo número e ano para todos; dívida, primário, nominal, juros, conta corrente, inflação, e fora do painel juro real, crescimento e desemprego); o que mudou em um ano; e o quadro-resumo. Falta par internacional para crédito (BIS: serviço da dívida das famílias, hiato de crédito), reservas (FMI, IFS), volatilidade do câmbio (BIS, câmbio diário) e previdência. |
| Melhorar as faixas das projeções (a barra azul) | ✅ traço fino em tinta neutra com as pontas marcadas; no leque, a parte de 50 % mais grossa. Regra no `CLAUDE.md`. |
| Riscos: faixa e "sorteio" mais intuitivos | ✅ "como ler" em palavras de todo dia no leque e nas previsões ("8 em cada 10 futuros sorteados ficam entre as pontas"), nomes da legenda e do cartão reescritos, verbetes no glossário. |
| O primário do Brasil no mundo e o de Contas públicas se conversam? | Conversam, mas não são a mesma conta (FMI: governo geral, receitas menos despesas; BC: setor público com estatais, variação da dívida). ✅ Tabela lado a lado em Contas públicas › Primário e juros, e a diferença dita na descrição da métrica em Brasil no mundo. |

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
  constitucionais (12 % e 25 %; normas lidas em 14/11/2026, a base de cálculo vem do RREO
  Anexos 12 e 08).
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
| Saving rate, investimento | taxa de investimento e de poupança (% do PIB) | SIDRA 6727 e 6726 | ✅ Atividade › Investimento e poupança |
| Real final sales to private domestic purchasers | consumo das famílias + investimento, sem governo e estoques | SIDRA | ideia |
| Productivity | PIB por pessoa ocupada | SIDRA | ✅ em Demografia |
| FedWatch (probabilidades da reunião) | probabilidade do Copom pelos DI curtos | B3 (desligada) | espera o `SB_B3` |
| VIX, NFCI, petróleo, metais | risco-país, Brent, minério | sem fonte aberta estável (EMBI parou em 2024) | fora por ora |
| UMich, Cleveland | expectativa do consumidor (FGV) | FGV cobra | fora |

## Aba "Riscos" (Caio, 14/11/2026: *"me proponha algo que dê pra colocar numa aba só de riscos"*)

No ar desde 14/11/2026 (`secoes/riscos.py`, `modelos/risco.py`, `relatorios.py`,
`web/src/alertas.ts`). Decisões do Caio no mesmo dia: a palavra na tela é **sustentabilidade
da dívida**, não "calote"; os **cenários de estresse entram** (fixos, tirados da história);
**fonte não oficial fica de fora**; e pediu a mais risco de crédito, câmbio, juros sobre a
dívida e o risco demográfico (*"de ficarmos sem grana pra previdência"*).

| Bloco | Situação |
|-------|----------|
| 1. A dívida se sustenta? | ✅ primário que estabiliza a dívida contra o de hoje, juro da dívida menos crescimento, juros em reais (SGS 5045), prazo médio (10618), leque de trajetórias (4.000 sorteios com os choques de 2006 a 2025, cápsulas de 80 %) ao lado do Focus, e as elasticidades que o BC publica (lidas à mão). Falta: a taxa implícita oficial da DBGG e o vencimento em 12 meses (só na planilha mensal da nota fiscal do BC, tabelas 24 e 25: um arquivo por mês), o FMI no leque, juros sobre a receita. |
| 2. O que o mercado cobra | ✅ volatilidade do dólar e do Ibovespa, distância do pico, câmbio real efetivo. Falta: juro real de 10 anos do Brasil menos o dos EUA (a fonte americana foi testada e responde, ver [FONTES](FONTES.md); pede a história do juro real brasileiro de 10 anos, que `juros.py` só calcula para hoje), inflação implícita longa contra a meta no painel. EMBI+ e CDS seguem sem fonte aberta. |
| 3. Nota de crédito | ✅ escada das três agências desde 1994 e o cartão com a distância do grau de investimento, lidos à mão (`relatorios.py`). O sistema do Tesouro (sisweb) estava fora do ar: reler quando voltar e a cada ato de agência. |
| 4. Painel de alerta | ✅ (classificado e explicado em 14/11/2026, ver acima) 32 indicadores em seis grupos, cada um na régua da própria história, com o lado ruim à direita; "aceso" = pior que 80 % da história; limite oficial onde há (teto da meta, mínimo de Basileia). Sem nota única. Falta: hiato de crédito do BIS (testado, ver FONTES), liquidez dos bancos (SGS 29407/29408, trimestrais), expectativa de inflação contra a meta. |
| 5. Testes de estresse | ✅ cinco episódios (2002, 2008, 2015–16, 2020, fim de 2024): o que dólar, bolsa, Selic e PIB fizeram e o mesmo tranco na escala de hoje; a dívida com os choques de 2008, 2015–16 e 2020 somados à linha de base do Focus; o teste dos bancos do REF de out/2026 na nota (lido à mão). 2002 fica fora da conta da dívida (a DBGG atual começa em dez/2006). |
| 6. Risco jurídico e institucional | ⬜ ações contra a União com perda provável e possível (Anexo de Riscos Fiscais da LDO), precatórios, indicadores de governança do Banco Mundial. Tudo lido à mão ou de API lenta: próximo passo. |
| 7. Estados | ⬜ quem está perto do limite de pessoal e de dívida (os limites da lei já estão em `leis.py`), nota CAPAG. |
| Longo prazo e energia (pedido a mais) | ✅ déficit e benefícios do INSS no painel, idosos por 100 em idade ativa (projeção do IBGE, com o resto em Demografia), reservatórios das hidrelétricas (ONS) contra o mesmo mês dos outros anos. Ideias: dependência de commodities nas exportações (Comex Stat), projeção atuarial do RGPS (LDO). |

## Demografia (Caio, 14/11/2026: *"resultados demográficos… riscos demográficos, algo que envolve a produtividade, trabalho e previdência"*)

Pronto em 14/11/2026 (assunto "Demografia"): população, fecundidade, esperança de vida, idade
mediana, idosos e jovens por 100 de 15 a 64, pirâmide etária por ano, nascimentos × óbitos,
idosos por estado (projeção do IBGE, revisão 2024); PIB por pessoa ocupada e a divisão do
crescimento entre ocupação e produtividade; déficit do INSS (RTN).

| Ideia | Fonte | Situação |
|-------|-------|----------|
| Contribuintes da previdência por beneficiário | PNAD Contínua (contribuintes) e boletim da Previdência (benefícios) | a tabela do SIDRA não foi achada sem o catálogo (`sidra.ibge.gov.br` dá 403 de fora); tentar no PC |
| A projeção da ONU (WPP 2024) ao lado da do IBGE, com a faixa de 80 % e 95 % | ONU, World Population Prospects | o portal pede chave; ver o CSV de download. Daria a faixa de erro que o IBGE não publica |
| Produtividade por hora trabalhada | PNAD (horas habituais) | a conferir |
| Projeção atuarial do RGPS (despesa e receita em % do PIB até 2100) | anexo da LDO, lido à mão como as leis | a conferir |
| Previdência dos servidores da União e dos militares | RTN (outras abas) | a conferir |
| Envelhecimento contra outros países (idosos por 100, fecundidade) | Banco Mundial (lento) ou ONU | ligaria com "Brasil no mundo" |
| Ficha do estado com a pirâmide e o ano do pico da população | a mesma projeção do IBGE, por UF | dado já baixado |

## Outras

- Previsões próprias de IPCA e desocupação (modelo sazonal), sempre ao lado do Focus.
- Brasil no mundo: câmbio no ano (BIS `WS_XRU`), juro de 10 anos (OCDE), inflação mensal.
- Acabamento: "novo desde sua última visita", PNG dos gráficos, imagem de compartilhamento,
  domínio.
- **Meta de primário do Governo Central** contra o realizado: a lei está lida; espera decisão
  de como tratar os descontos da apuração oficial ([PROXIMOS-PASSOS](PROXIMOS-PASSOS.md)).
- **Agenda na entrada**: as divulgações da semana (IBGE, já buscado pelo navegador), guardada
  atrás de um clique. O Copom não tem API com as reuniões futuras (ver [FONTES](FONTES.md)).

## Tradução (14/11/2026)

- Busca em outros idiomas: feita para inglês, espanhol e francês (`OUTRAS_LINGUAS`). Falta
  para línguas de outra escrita (chinês, japonês, árabe…).
- Nomes próprios protegidos do tradutor (Copom, Focus, IPCA, Selic): marcar com
  `translate="no"` onde aparecem nos títulos e no menu.
- Simulador: inflação com efeito no juro da parte da dívida corrigida pelo IPCA (falta a
  participação por indexador com o IPCA numa fonte com API; ver "Limites conhecidos").
