# Propostas

O que foi pedido ou pensado e ainda falta, por assunto. Pedido novo vira linha aqui antes de
virar código; o que fica pronto sai (a história está no git e no
[PROXIMOS-PASSOS](PROXIMOS-PASSOS.md) da época). A ordem do que fazer agora fica no
[PROXIMOS-PASSOS](PROXIMOS-PASSOS.md).

Última atualização: 14/11/2026. Tudo o que foi pedido até aqui está no ar (Impostos, Selic,
reforma do consumo, Pobreza, Estados com PIB, comércio por setor, Riscos, Demografia,
glossário com 182 termos, tradução, valor nunca em branco, prazos de releitura); abaixo, só o
que ficou faltando em cada um.

## Fora, por decisão do Caio

- **B3**: o site veda coleta automatizada; `SB_B3` desligado. O que depende dela (IFIX, DI,
  probabilidade do Copom, cupom de IPCA curto) fica fora.
- **Desemprego de equilíbrio (NAIRU)** (14/11/2026): o BC não publica número oficial; só há
  um estudo no blog do BC (7,2 % em mai/2026, faixa de 5,4 a 9,1 %) e o hiato do produto do
  RPM. Não entra.
- **Fonte não oficial** nos Riscos (EMBI, CDS) e cenário montado pela pessoa fora dos três
  simuladores.

## Falta, por assunto

**Juros e Selic**
- Atalho do efeito da Selic em Inflação e em Contas públicas; ciclos alinhados pelo primeiro
  corte (o gráfico só sabe eixo de datas). O efeito na atividade e no crédito (boxe do RPM de
  mar/2026) não entra: é estudo de uma vez só (regra de 15/11/2026).
- Faixa de erro do modelo de 2024, se o BC publicar; efeito por grupo de preços.
- Inflação implícita antes de mai/2029 (só com a B3).

**Mercados**
- "Quanto rendeu R$ 100": Tesouro IPCA+ e prefixado (CSV do Tesouro Direto), ouro, Ibovespa
  com dividendos.

**Atividade** (Caio, 14/11/2026: *"falta aquela de demanda privada que o econvitals tem,
oferta também?"*)
- Demanda privada (o *real final sales to private domestic purchasers* do Econvitals): consumo
  das famílias + investimento, sem governo, estoques e exterior, em Atividade › PIB. Os dados
  já vêm do SIDRA 5932; somar pede pesar cada parte pelo tamanho em reais (conta nossa, dita na
  nota).
- PIB pela oferta no tempo (agropecuária, indústria e serviços): hoje só na tabela "PIB por
  componente", do último trimestre; falta o gráfico, como o "PIB pela demanda". Sem conta
  nossa. O Econvitals não tem oferta.

**Inflação e Trabalho**
- Serviços subjacentes (código SGS não achado), Caged por setor (as séries 28764 a 28783 não
  têm nome legível).
- Previsões próprias de IPCA e desocupação (modelo sazonal) e o PIB agora com indústria,
  varejo e serviços; sempre ao lado do Focus.

**Riscos**
- Dívida: taxa implícita oficial da DBGG e vencimento em 12 meses (planilha mensal da nota
  fiscal do BC), o FMI no leque, juros sobre a receita.
- Mercado: juro real de 10 anos do Brasil menos o dos EUA (falta a história do juro real
  brasileiro de 10 anos), inflação implícita longa contra a meta.
- Painel: hiato de crédito na régua da própria história (contra outros países já está),
  liquidez dos bancos (SGS 29407/29408), expectativa de inflação contra a meta.
- Alerta contra outros países: reservas (FMI), volatilidade do câmbio (BIS), previdência.
- Jurídico: Anexo de Riscos Fiscais da LDO, precatórios, governança do Banco Mundial.
- Estados perto dos limites de pessoal e dívida, com a nota CAPAG.
- Projeção atuarial do RGPS (anexo da LDO).

**Contas públicas e Impostos**
- Reforma: o imposto de hoje ao lado (ICMS modal por estado, 27 leis), regimes próprios,
  Imposto Seletivo, Simples, 2029 a 2032, o que muda por estado com a cobrança no destino.
- IR da pessoa física, imposto sobre consumo e sobre salário contra outros países (a OCDE não
  traz o Brasil; achar outra fonte oficial).
- FPE/FPM ao lado da arrecadação por estado; imposto retido na fonte por faixa de renda;
  gasto tributário antes de 2014 (só PDF); multiplicador de receita da SPE, só se sair com
  regularidade (estudo avulso não entra, regra de 15/11/2026).

**Estados**
- Mínimos de saúde e educação (SIOPS e SIOPE; o RREO não traz pela API).
- Estados no tempo (3º quadrimestre de cada ano), CAPAG, previdência do estado (RREO Anexo 04),
  PIB por setor (tab05 das Contas Regionais), Caged por UF (testar do PC).
- Regime de Recuperação Fiscal e Propag, capitais, repasses da União, comparação com a região.

**Setor externo**
- Exportações por estado de origem na ficha, categorias de uso (CGCE), preço × quantidade,
  serviços.

**Pobreza**
- Moradia e déficit habitacional (PNAD, Fundação João Pinheiro), SINISA por município, fome
  nas pesquisas antigas, educação, topo pelo IR por centil, riqueza declarada, renda por
  escolaridade e idade (SIDRA 7442, 7443).

**Demografia**
- Contribuintes por beneficiário (tabela do SIDRA, testar do PC), projeção da ONU com faixa de
  erro, produtividade por hora, previdência dos servidores e militares, envelhecimento contra
  outros países, pirâmide na ficha do estado.

**Brasil no mundo**
- Câmbio no ano (BIS `WS_XRU`), juro de 10 anos (OCDE), inflação mensal.

**Tela, busca e tradução**
- Busca: sugestões quando nada é achado, busca por número ("13,75"), o glossário na busca
  ("o que é spread"), outras escritas (chinês, japonês, árabe).
- Nomes próprios protegidos do tradutor nos títulos e no menu (Copom, Focus, IPCA, Selic).
- Agenda da semana na entrada, atrás de um clique.
- Acabamento: "novo desde sua última visita", PNG dos gráficos, imagem de compartilhamento,
  domínio.

## Em espera

- **Selo "dado anterior"** na peça mantida (`mantidos` já está no `painel.json`).
- **Tarefa agendada que relê** os relatórios (Caio, 14/11/2026: *"o 3 anote no propostas"*):
  disparada pela issue `releitura` ou por data, lê o PDF, atualiza `relatorios.py`, `leis.py` e
  `leituras.py` e abre PR. Não serve para o que só abre do PC (Planalto); número em imagem no
  PDF pede conferência humana.
