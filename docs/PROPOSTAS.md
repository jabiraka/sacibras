# Propostas

O que foi pedido ou pensado e ainda falta, por assunto. Pedido novo vira linha aqui antes de
virar código; o que fica pronto sai (a história está no git e no
[PROXIMOS-PASSOS](PROXIMOS-PASSOS.md) da época). A ordem do que fazer agora fica no
[PROXIMOS-PASSOS](PROXIMOS-PASSOS.md).

Última atualização: 20/11/2026 (por último, os indicadores clássicos que ficaram em espera).
Na primeira sessão da nuvem de 15/11 entrou quase tudo o que estava aqui (PIB pela oferta e demanda privada, ciclos da Selic alinhados, riscos de mercado, dívida
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
- **FGV IBRE** (15/11/2026; Caio: *"podemos só mostrar se for permitido"*): os termos de
  uso vedam reproduzir e divulgar sem autorização
  ([FONTES](FONTES.md#licença-do-dado-o-privado-só-vai-à-tela-se-a-licença-deixar-e-nunca-com-download)).
  Saíram da tela o IGP-M (Inflação › Outros índices) e a utilização da capacidade instalada
  (Atividade); ficam fora a decomposição do IGP-M (IPA, IPC e INCC; o detalhe por grupo e
  item é por assinatura) e o Observatório da Produtividade (PTF trimestral, por setor e
  regional). A PTF anual entrou pela Penn World Table, de licença aberta. Com autorização
  por escrito: `mostra=True` em `licencas.FGV_IBRE` e os gráficos de volta.

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

**Decomposições** (feitas em 15/11/2026: IPCA por grupo, PIB pela demanda e pela
oferta, fatores da dívida e da desocupação, carrego do PIB). O que ficou de fora:
- IPCA pelas categorias do BC (serviços, industriais, alimentação no domicílio, administrados):
  o SGS dá a variação, não o peso; sairia dos subitens do IBGE, classificados um a um.
- IPCA por grupo antes de dez/2020 (tabelas 1419 e 2938 do SIDRA, com outra estrutura de pesos).
- Massa de renda = gente ocupada × rendimento médio; crédito por pessoa física e empresa.
- Exportações em preço × quantidade (índices do MDIC; **do PC**).
- A tabela oficial de fatores condicionantes da DBGG (só na nota mensal do BC, em planilha
  com poucos meses): ler à mão ou achar o arquivo com a série.
- Prévia de dado atrasado que ainda não tem conta: pobreza e Gini (PNAD anual), carga
  tributária (OCDE, dois anos) e PIB dos municípios (2023). Nenhuma tem indicador mensal
  bom o bastante; ficam sem prévia até aparecer um.

**Estados**
- Mínimos de saúde e educação (SIOPS e SIOPE; **do PC**).
- PIB trimestral por estado: o que ficou de fora é a série do estado no tempo na ficha ("Um
  estado por dentro"); a conferência automática contra os institutos estaduais (o arquivo muda
  de nome a cada trimestre; hoje é à mão, uma vez por ano); e agropecuária por estado para
  corrigir o trimestre da safra (LSPA), onde a conta mais erra (RS).
- Escolher o período nas métricas que ainda não têm a lista (Caio, 15/11/2026: *"escolher a
  data em outras métricas além do crescimento do PIB"*; entraram trabalho, Gini, pobreza,
  PIB por habitante e peso, concentração, inflação, IBC-R em 12 meses e crédito). Faltam as
  contas do governo do estado (pessoal, dívida, RCL, primário, ICMS: uma consulta ao SICONFI
  por período e estado), exportações e arrecadação federal (mais downloads por mês) e a prévia
  do PIB pelo IBC-R (a faixa de erro é de um ano só). A lista vale no mapa e no ranking; a
  tabela completa e "Duas métricas" seguem no período mais novo.

**Setor externo**
- Preço × quantidade das exportações (índices do MDIC; **do PC**, certificado vencido).

**Pobreza**
- Déficit habitacional da Fundação João Pinheiro (**do PC**; ver se sai com regularidade).

**Demografia**
- Contribuintes por beneficiário (tabela do SIDRA; **do PC**).

**Tela, busca e tradução**
- Domínio (com ele, trocar `ENDERECO` em `web/vite.config.ts` e `anterior.SITE`).
- Agenda: as reuniões do Copom na caixa "O que sai esta semana" (não há API de datas
  futuras; só lendo o calendário publicado pelo BC).

## O que incluir e tirar (conversa de 16/11/2026)

Caio: *"Os simuladores tem mto erro né, melhor focarmos no que podemos pegar e fazer."* O
"Saiu por último" (o número contra o Focus, na entrada) entrou no mesmo dia. Fica:

- **Fora**: o efeito de política futura sobre PIB e emprego, e o simulador de imposto com
  a base parada (*"a base parada não sei se fica factível, as pessoas se ajustam"*). Com as
  regras afrouxadas no mesmo dia, o de imposto volta no Laboratório, com o comportamento
  na conta e o resultado como faixa ([PLANO-FASE-2](PLANO-FASE-2.md), leva 4).
- **"Minha inflação" é do finjabs**, não daqui (*"eu queria que o finjabs fizesse essa
  conta"*): está no PROPOSTAS de lá, M174. Quando existir, Inflação › Por tipo de preço
  aponta para ela; corrigir um valor pela inflação já existe lá
  (`finjabs.com.br/calculadora/corrigir-valor-pela-inflacao`) e pode ganhar o mesmo elo.
- **Páginas de pergunta**: feitas em 16/11/2026 (oito, em `perguntas.py`). Falta a série do
  crédito direcionado (SGS) na do juro alto e a árvore do diagnóstico de crescimento.
- **Onde estou na renda** (PNAD e centis do IRPF) e **quanto do meu salário é imposto**
  (IRPF e INSS pela lei lida): a segunda é conta do finjabs; a primeira pode ser daqui
  (Pobreza › distribuição), com um campo só. Pede o "sim" do Caio, por ser entrada da pessoa.
- **Contar acesso por pergunta, parte e termo de busca**, nós mesmos (Caio, 16/11/2026):
  um projeto Supabase só do sacibras, uma tabela de contagem por dia (página, termo,
  idioma, de onde veio), gravada por uma função que só soma; sem cookie, sem IP, sem
  identificar pessoa. Dizer no rodapé o que se conta. Espera o projeto.
- **Riscos**: o painel de alerta foi de 39 para 17 em 16/11/2026 (`alertas.NO_PAINEL`).
  Falta: as partes de 6 para 3, os reservatórios irem para Atividade e a tabela de
  governança sair.
- **Crescimento e longo prazo, o que dá para pegar** (Caio: *"há muitas teorias de
  crescimento e longo prazo, não sei oq dá pra encaixar"*). Só dado publicado ou conta
  nossa sobre ele, sem previsão:
  - **De onde veio o PIB por habitante**: crescimento = produtividade por ocupado × parcela
    da população que trabalha × parcela em idade de trabalhar (IBGE; conta nossa, fecha com
    o número oficial). Mostra o fim do bônus demográfico: quanto do crescimento desde 1990
    veio de ter mais gente trabalhando, que acabou, e quanto de produtividade.
  - **Convergência**: o PIB por habitante do Brasil em % do dos EUA desde 1950, com Coreia,
    Chile, México, China e Turquia (Penn World Table, já lida). É o gráfico da "armadilha
    da renda média".
  - **Hiato do produto e juro neutro**: o BC publica os dois no Relatório de Política
    Monetária (trimestral; o neutro, uma vez por ano) e a IFI publica o hiato. Leitura à
    mão com prazo (`relatorios.py`, `leituras.py`). Com eles, o juro real ao lado do
    neutro diz o quanto a Selic aperta, sem modelo nosso.
  - **Duas métricas no tempo** (o gráfico de pontos que já existe, com um ponto por ano):
    desocupação × inflação de serviços (a curva de Phillips), crescimento do PIB × variação
    da desocupação (a lei de Okun), termos de troca × câmbio. A teoria em uma frase e o
    dado dizendo se ela aparece ou não no Brasil; não é previsão.
  - **Termos de troca** (Funcex pelo Ipeadata ou os índices do MDIC, **do PC**) e o peso
    das commodities na exportação (Comex Stat): o quanto o crescimento acompanha o preço do
    que se exporta.
  - **Indústria de transformação em % do PIB** desde 1947 (IBGE, contas nacionais), contra
    países de renda parecida: a desindustrialização em um gráfico.
  - **Educação**, que hoje não tem lugar próprio: Ideb (Inep, a cada dois anos), PISA
    (OCDE, a cada três) e anos de estudo (PNAD), por estado onde houver. É o capital
    humano da conta do crescimento.
  - **Crédito direcionado** em % do crédito total (SGS): serve à página do juro alto.

## Crise e ajuste fiscal (sessão de 19/11/2026)

Caio: *"essas métricas vão nos ajudar a ver o desenrolar e de onde está vindo se tiver uma
crise, bem como oq poderíamos ter feito pra prevenir, o foco principal hj está no ajuste
fiscal, mas temo que o governo não queira implementar"*; e *"Faz tudo, eu aprovo"*. Entrou
tudo o que estava aqui (meta de cada LDO, dívida esperada por safra, custo de esperar e a
pergunta da crise; o estudo dos anúncios fiscais foi feito e saiu). Ficou:

- **Os parâmetros de cada orçamento contra o que veio** (PIB, inflação e receita previstos
  no PLOA): a outra metade do "viés do governo". Leitura à mão de umas vinte mensagens
  presidenciais, com prazo.
- **O mundo ou o Brasil, para o juro longo e a bolsa**: a mesma conta do dólar com o juro
  real de 10 anos contra o dos EUA (já lido em Riscos) e com o Ibovespa contra um índice de
  emergentes (falta fonte oficial e aberta para o índice).
- **Receita de uma vez só nos episódios**: separar, na tabela "receita ou despesa", o que
  foi receita extraordinária (concessões, dividendos, Refis; o RTN tem as linhas) do que
  ficou.
- **Testado e fora da tela: o estudo de evento dos anúncios fiscais** (Caio, 19/11/2026:
  *"Se o resultado for fraco, acho que não precisa colocar não"*). Com 24 datas conferidas
  e janela de dois pregões, o juro de 5 anos subiu em 8 de 12 anúncios de menos aperto e
  em 5 de 9 de mais aperto: não se distingue do acaso. Volta se houver medida melhor: a
  hora de cada anúncio (quase nenhuma página oficial dá) e o juro do dia (a B3 está
  desligada). A lista (`relatorios.ANUNCIOS_FISCAIS`) e a conta ficam no código.
- **Meta da LDO com o abatimento**: refazer a comparação com a meta já descontada do PPI e
  do PAC efetivamente usados (2007 a 2014), que está nos relatórios de cumprimento de meta.
- **Testado e fora**: a correlação móvel entre o juro prefixado de 5 anos e o dólar (dias
  em que os dois sobem juntos como sinal de prêmio de risco). É positiva quase sempre desde
  2013 (entre 0,2 e 0,7), sem marcar 2015 nem 2024 melhor que os outros anos, e custa 45 s
  de build (uma curva por dia). Não entra.

## A LDO 2027 e a conta da dívida (sessão de 25/11/2026)

Entraram o projeto da LDO 2027 e a conta nossa da dívida por cenário (ver o
[PROXIMOS-PASSOS](PROXIMOS-PASSOS.md)). Ficou:

- **Botões no simulador da dívida** que carregam "governo", "Focus" e "história" nos quatro
  controles (hoje a pessoa digita).
- **O erro da meta conforme a antecedência**: a conta usa o mesmo erro (0,6 pp) em todos os
  anos, mas as metas de 2028 a 2030 são indicativas e costumam ser revistas; medir pede ler
  as metas indicativas de cada LDO desde 2024 (antes eram de três anos, nos anexos).
- **O juro pela Selic do Focus**, no lugar do que fecha com a dívida do Focus: pede o quanto
  da dívida acompanha a Selic (a tabela 13 do Anexo V dá a sensibilidade do Tesouro) e uma
  hipótese para depois de 2030.
- **A mesma peça a cada PLDO** (abril) e a cada LDO sancionada: hoje os nomes dizem 2027.

## Indicadores clássicos (sessão de 20/11/2026)

Caio: *"veja se dá pra colocar, se não ficar muito poluído, gráficos ou variações de gráficos
com as métricas que temos, alguns indicadores que economistas usam [...] só os que vc tiver
high ou medium confidente"*; e depois: *"Pode incluir os outros também de média confiança,
faça tudo"*. Entraram os dez (ver o [PROXIMOS-PASSOS](PROXIMOS-PASSOS.md)). Ficou:

- **A despesa sujeita ao limite**, no lugar da despesa total, contra a faixa do arcabouço: o
  número oficial sai no Relatório de Avaliação bimestral (leitura à mão, com prazo).
- **Phillips e Okun com mais anos**: a PNAD Contínua começa em 2012; antes, só emendando a
  PME (outra pesquisa, seis regiões), o que pede dizer a emenda na tela.

Pensados e fora (confiança baixa): a regra de Sahm (calibrada para os EUA, e a PNAD já é
média de três meses), o impulso de crédito (segunda derivada, ruidosa mês a mês), o primário
estrutural (depende do hiato, que é do Laboratório), a curva de Beveridge (não há série
oficial de vagas abertas) e os termos de troca (a fonte é a Funcex, privada, ou o MDIC, só
do PC).

## Achados da revisão das telas (15/11/2026)

Caio: *"toque nas telas, veja se consegue pensar em algo que está faltando ou alguma tela
quebrando [...] que eles encontrem oq estão procurando"*. Corrigido: o menu lateral que
escondia Previsões e Riscos, a busca (palavras de ligação, busca por parte das palavras,
linhas das tabelas curtas, IPCA por grupo, o glossário), o número separado do "%" na quebra
de linha, as frases do PIB dos estados e da Selic, as tabelas no celular (sombra na borda
enquanto há coluna escondida; as que passavam 10 px agora cabem) e a página do glossário
(`#glossario`, no menu e no rodapé). E o que a busca procurava e o painel não tinha (Caio,
15/11/2026: *"coloque os itens que as pessoas procuram e o painel não tem"*): o juro de cada
modalidade das pessoas físicas, do cartão rotativo ao consignado (Crédito › Volume e custo);
o salário mínimo, em reais, e um comparador contra o IPCA no período que a pessoa escolhe,
com os prazos fixos de 1, 5, 10 e 20 anos e desde 1995 e o gráfico do mínimo do início
corrigido pela inflação (Trabalho › Renda); os 15 subitens que mais
pesam no IPCA e a gasolina, a luz e o aluguel em 12 meses (Inflação › Por tipo de preço); e
o IPCA-15 no gráfico dos outros índices. Fica:

- **Estados** (Caio, 15/11/2026: *"anote [...] dos Estados em propostas mas não mexa"*; fica
  para a sessão de Estados):
  - a tela abre no crescimento do PIB de 2024, o número oficial mais novo, com quase dois
    anos (a prévia de 2025 só aparece escolhendo em "até"). Abrir na desocupação do
    trimestre, na prévia de 2025, ou deixar como está?
  - o mapa, a 1280 px, ocupa meia largura e o resto fica vazio; as siglas dos estados
    pequenos (RN, PB, PE, AL, SE, ES, RJ, DF) somem ou se sobrepõem.

## Em espera

- **Selo "dado anterior"** na peça mantida (`mantidos` já está no `painel.json`).
- **Tarefa agendada que relê** os relatórios (Caio, 14/11/2026: *"o 3 anote no propostas"*):
  disparada pela issue `releitura` ou por data, lê o PDF, atualiza `relatorios.py`, `leis.py` e
  `leituras.py` e abre PR. Não serve para o que só abre do PC (Planalto); número em imagem no
  PDF pede conferência humana.
