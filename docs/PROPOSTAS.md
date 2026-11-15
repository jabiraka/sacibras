# Propostas

O que foi pedido ou pensado e ainda falta, por assunto. Pedido novo vira linha aqui antes de
virar código; o que fica pronto sai (a história está no git e no
[PROXIMOS-PASSOS](PROXIMOS-PASSOS.md) da época). A ordem do que fazer agora fica no
[PROXIMOS-PASSOS](PROXIMOS-PASSOS.md).

Última atualização: 15/11/2026. Na sessão da nuvem de 15/11 entrou quase tudo o que estava
aqui (PIB pela oferta e demanda privada, ciclos da Selic alinhados, riscos de mercado, dívida
e jurídicos, estados com CAPAG, limites, previdência, exportações, RRF/Propag e capitais,
séries novas em mercados, mundo, setor externo, trabalho, pobreza, demografia e impostos,
busca, tradução e acabamento). Abaixo, só o que ficou: o que depende do PC está marcado e
repetido no PROXIMOS-PASSOS.

## Fora, por decisão do Caio

- **B3**: o site veda coleta automatizada; `SB_B3` desligado. O que depende dela (IFIX, DI,
  probabilidade do Copom, cupom de IPCA curto, Ibovespa com dividendos, inflação implícita
  antes de mai/2029) fica fora.
- **Desemprego de equilíbrio (NAIRU)** (14/11/2026): o BC não publica número oficial; só há
  um estudo no blog do BC e o hiato do produto do RPM. Não entra.
- **Fonte não oficial** nos Riscos (EMBI, CDS) e cenário montado pela pessoa fora dos três
  simuladores.
- **Previsões próprias** (15/11/2026, *"sem próprias previsões por enquanto"*): IPCA e
  desocupação por modelo sazonal e o PIB agora com indústria, varejo e serviços.

## Falta, por assunto

**Juros e Selic**
- Faixa de erro do modelo de 2024, se o BC publicar; efeito por grupo de preços (idem).

**Inflação e Trabalho**
- Serviços subjacentes: achar o código no SGS (**do PC**).
- Caged por UF (**do PC**).

**Riscos**
- Alerta contra outros países: previdência (achar par em fonte oficial com o mesmo número
  para todos; reservas, volatilidade do câmbio e hiato de crédito já entraram).

**Contas públicas e Impostos**
- O imposto de hoje ao lado na reforma: ICMS modal por estado (27 leis; **do PC**, o Confaz
  não respondeu da nuvem). O que muda por estado com a cobrança no destino: não há número
  oficial por estado (só a regra de partilha, que já está no gráfico).
- Alíquotas do Imposto Seletivo: a LC 214 deixa para lei ordinária; entra quando sair.
- Gasto tributário antes de 2014: a Receita só publica em PDF; fica fora sem conferência.
- Multiplicador de receita da SPE: só se sair com regularidade (estudo avulso não entra).

**Estados**
- Mínimos de saúde e educação (SIOPS e SIOPE; **do PC**).

**Setor externo**
- Preço × quantidade das exportações (índices do MDIC; **do PC**, certificado vencido).

**Pobreza**
- Déficit habitacional da Fundação João Pinheiro (**do PC**; ver se sai com regularidade).

**Demografia**
- Contribuintes por beneficiário (tabela do SIDRA; **do PC**).
- **O custo do envelhecimento** (Caio, 15/11/2026: *"estimativas de risco [...] quanto
  custaria a aposentadoria, mantendo a taxa de fecundidade constante, quanto cada trabalhador
  futuro iria pagar, qual o déficit da previdência"*). Testado da nuvem em 15/11/2026, tudo
  abre de fora do Brasil; espera o Caio escolher quais entram. Numa parte nova ("O custo do
  envelhecimento"), para não lotar "Envelhecimento e Previdência":
  1. **Projeção oficial do INSS até 2100**: PLDO 2027, anexo IV.10 (SRGPS/MPS, abr/2026;
     sai todo ano com a LDO, por exigência da LRF): déficit de 2,49 % do PIB (2026), 3,79 %
     (2050), 6,89 % (2070) e 10,41 % (2100); despesa de 8,26 % a 16,76 %. Número lido →
     `relatorios.py` + `leituras.py` (reler no PLDO 2028, abr/2027). Os anexos IV.11
     (servidores da União) e IV.13 (BPC) vêm do mesmo jeito.
  2. **Trabalhadores por idoso com faixa de erro**: a ONU publica a razão 65+/15-64 já com
     as faixas de 80 e 95 % (`UN_PPP2024_Output_Annual_OldAgeDepRatio.xlsx`, mesma pasta e
     quase o mesmo formato da planilha de população; uma linha por ano, uma coluna por faixa
     de idade). Hoje 5,8 por idoso; 2050: 2,8 (2,6 a 3,0); 2070: 1,9 (1,6 a 2,3).
  3. **Fecundidade constante e as outras variantes da ONU**: 65+ por 100 de 15-64 em 2070:
     IBGE (fecundidade cai a 1,44) 54; ONU mediana 51; fecundidade constante em 1,62: 51;
     volta imediata a 2,1: 42; meio filho a menos: 62. Antes de 2045 a fecundidade quase não
     muda nada (quem trabalha em 2045 já nasceu). Custo: o arquivo das variantes por idade
     tem 231 MB (`WPP2024_PopulationByAge5GroupSex_OtherVariants.csv.gz`); cache de 30 dias
     ou o arquivo por idade simples só da fecundidade constante.
  4. **Quanto cada um paga**: o INSS custou R$ 581 por mês por pessoa de 15 a 64 anos em
     2025 (R$ 180 de déficit). Com o mesmo benefício por idoso de hoje, em reais de hoje:
     R$ 1.270 em 2050 e R$ 1.890 em 2070. Estimativa nossa, só com a pirâmide do IBGE.
  5. **A idade que manteria a proporção de hoje** (5,8 em idade de trabalhar por idoso):
     70 anos em 2040, 73 em 2050, 79 em 2070 (IBGE; com a ONU, 78 a 79 em 2070 em qualquer
     fecundidade). Estimativa nossa, interpolando os grupos de cinco anos.
  6. **Só a idade × a conta oficial**: se o gasto por idoso acompanhasse a renda por pessoa
     em idade de trabalhar, a despesa iria de 8,3 % do PIB a 17,5 % em 2050 e 26 % em 2070;
     a LDO chega a 13,3 %. A diferença é o que as regras seguram (idade mínima de 2019,
     benefício acima do mínimo só com a inflação): em 2070, o gasto por idoso relativo à
     renda fica na metade do de hoje. Delicado: entra como nota ou gráfico só com o "sim".
  7. **O freio no PIB por pessoa**: a parte da população de 15 a 64 anos cai de 68,9 % para
     63,2 % (2050) e 57,0 % (2070): -0,36 pp por ano no PIB por pessoa até 2050 e -0,51 pp
     depois, com a mesma produtividade. Vai na parte Produtividade.
  8. **Simulador da previdência** (idade de aposentadoria, variante de fecundidade, reajuste
     dos benefícios): seria o quarto simulador, então só com o "sim" do Caio.

**Tela, busca e tradução**
- Domínio (com ele, trocar `ENDERECO` em `web/vite.config.ts` e `anterior.SITE`).
- Agenda: as reuniões do Copom na caixa "O que sai esta semana" (não há API de datas
  futuras; só lendo o calendário publicado pelo BC).

## Em espera

- **Selo "dado anterior"** na peça mantida (`mantidos` já está no `painel.json`).
- **Tarefa agendada que relê** os relatórios (Caio, 14/11/2026: *"o 3 anote no propostas"*):
  disparada pela issue `releitura` ou por data, lê o PDF, atualiza `relatorios.py`, `leis.py` e
  `leituras.py` e abre PR. Não serve para o que só abre do PC (Planalto); número em imagem no
  PDF pede conferência humana.
