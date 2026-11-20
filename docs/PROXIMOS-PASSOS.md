# Próximos passos

**Leia no começo da sessão e atualize no fim** (Caio, 14/11/2026). Aqui fica só o que está em
aberto: o que foi feito sai (a história está no git), as ideias em espera ficam no
[PROPOSTAS](PROPOSTAS.md) e os limites conhecidos no [PLANO](PLANO.md#12-limites-conhecidos).

Última atualização: 20/11/2026. A sessão da nuvem de 15/11 fez tudo o que dava para fazer de
fora do Brasil; uma segunda olhou todas as telas a 390 e 1280 px e a busca com 65 termos (o
que ficou está no [PROPOSTAS](PROPOSTAS.md), "Achados da revisão das telas"). Depois entrou a
Penn World Table (Demografia › Eficiência (PTF), com a PTF estendida até 2025 por conta nossa
com dados do IBGE, e oito métricas de produtividade em Brasil no mundo), e o dado privado
ficou sem CSV nem PNG, e na tela só se a licença deixar (a FGV saiu), com as licenças em
`licencas.py`. Outra sessão do mesmo dia fez o PIB trimestral por estado, as decomposições
(IPCA por grupo, PIB por componente, fatores da dívida e da desocupação, carrego do PIB), o
IBC-R dos quatro estados novos e a conferência contra os institutos estaduais; o Caio olhou e
mandou juntar (*"junte no main e pode fazer oq recomendar"*). Tudo no `main`. Depois, a pedido do Caio:
Produtividade e Eficiência (PTF) saíram de Demografia para Atividade (`secoes/produtividade.py`),
a PTF contra a dos EUA ficou só com o Brasil, os gráficos do PIB ficaram em pares lado a lado,
a tabela "PIB por componente" ganhou a lista de trimestre ou ano com os pontos que somam o PIB,
a dica dos gráficos usa a unidade curta e o "Quanto rendeu" abre com CDI e Ibovespa e a pessoa
escolhe o resto. Em Estados, o mapa e o ranking ganharam a lista do período (trimestre, ano
ou mês) em treze métricas além do PIB; as que faltam estão no [PROPOSTAS](PROPOSTAS.md).

**20/11/2026**, a pedido do Caio (*"quando copiar imagem ou PNG, coloque algum indicativo que seja do sacibras para dar os créditos"*): toda imagem de gráfico (PNG e Copiar, `pngDaFigura` em `grafico.ts`) fecha com uma linha de crédito: o losango, "sacibras", "painel da economia brasileira" e o endereço do site (o de quem abriu a página). **Falta olhar uma imagem de cada tipo** (a nuvem não monta o site).

**19/11/2026**, a pedido do Caio: as perguntas ficam recolhidas (no menu, "Perguntas" abre no toque e sozinho dentro de uma pergunta; no pé da pergunta, "Outras perguntas") e a vista aberta do painel de alerta sai como imagem (PNG e Copiar, `desenhoDosAlertas` em `alertas.ts`, nas quatro vistas). **Falta olhar a 390 e 1280 px com o site rodando** (a nuvem não abre as fontes para montar os dados).

**19/11/2026, servidores e estatais** (Caio: *"inclua a distribuição dos gastos por
servidores públicos (quem fica com mais) e compare o rendimento e benefícios dos servidores
com o setor privado, adicione uma pergunta de quanto as estatais dão lucro ou prejuízo aos
cofres públicos"*), no `main`:
- **Contas públicas › Servidores públicos** (`secoes/servidores.py`): a folha por esfera e
  contra os outros países (FMI: 11,1 % do PIB na ativa, contra 8,6 % na mediana dos
  emergentes; estados e municípios ficam com 81 % da folha da ativa), por tipo na União
  (RTN: 43 % da folha vai a aposentados e pensionistas), por poder (Siconfi; e a remuneração
  média lida na avaliação atuarial do PLDO 2027: Legislativo R$ 18,5 mil, Ministério Público
  R$ 16,7 mil, Judiciário R$ 15,0 mil, Executivo R$ 13,4 mil), o rendimento contra o setor
  privado (PNAD: estatutário R$ 6.825, privado com carteira R$ 3.403) e a aposentadoria
  contra a do INSS (R$ 13,3 mil contra R$ 2,1 mil, com os dois tetos).
- **Contas públicas › Estatais** (`secoes/estatais.py`): dividendos por empresa (RTN), a
  conta do ano (Sest: em 2025, R$ 45,8 bi de dividendos menos R$ 32,6 bi de subvenção e
  aporte, saldo de R$ 13,1 bi, o menor desde 2021), quem recebe a subvenção, o lucro dos
  maiores e o primário das estatais (BC: déficit de R$ 7,3 bi nas federais em 12 meses).
- **As perguntas por tema** (Caio: *"é bom ter uma sessão própria ou organizar melhor as
  perguntas dentro dos temas"*): quatro temas (`perguntas.TEMAS`), na entrada, no menu e no
  pé de cada pergunta; o teto de nove no total deu lugar a seis por tema.
- **Duas perguntas novas** (doze agora, com a da crise): "Servidor público ganha
  mais que quem trabalha no setor privado?" e "As estatais dão lucro ou prejuízo aos cofres
  públicos?"; e a explicação "A folha dos servidores" em "Onde dá para cortar gasto?".
- **Para caber no teto de cinco partes**: "Meta fiscal" entrou em "Primário, juros e meta"
  (o gráfico do primário mês a mês saiu da tela) e "Receita e despesa da União" juntou-se a
  "Onde está o gasto", agora "Receita e gasto" (saiu o cartão da obrigatória em % do PIB).
  Os endereços `#fiscal/meta` e `#fiscal/receita-despesa` redirecionam (`PARTES_ANTIGAS` em
  `main.ts`).

**16/11/2026**, no `main`: a entrada virou perguntas (Caio: *"o gancho vai ser problemas e
perguntas [...] mostrar o dado que responde uma pergunta ou problema"*). Feito: o "Saiu por
último" (o número contra o Focus, `saiu.py`); as oito perguntas (`perguntas.py`,
`#pergunta/<id>`), cada uma com resposta, números e explicações com o gráfico dos Dados; a
entrada sem os quatro gráficos e com os assuntos só pelo nome; o menu em Perguntas e Dados;
as perguntas na busca; o painel de alerta de 39 para 17 (`alertas.NO_PAINEL`). A "Minha
inflação" foi para o finjabs (M174 de lá). O plano inteiro está no
[PLANO-FASE-2](PLANO-FASE-2.md).

Depois, no mesmo dia, a pedido do Caio: as respostas tomam posição onde o dado sustenta e
dizem o que fica em aberto, e cada pergunta fecha com "Juntando as peças"; a tabela do
primário que estabiliza a dívida com outros juros e crescimentos (Riscos › A dívida se
sustenta?, e na pergunta da dívida); o investimento e a poupança do Brasil contra a América
Latina, os emergentes e os avançados (FMI; Atividade › Investimento e poupança, e nas
perguntas do juro e do crescimento); e "o método do Jabs" saiu das fontes e notas.

Por último, o corte dos Dados pelo orçamento de atenção: as partes foram de 64 para 49
(nenhum assunto com mais de 5; nenhuma parte com mais de 4 números e 3 gráficos), os
cartões de 158 para 141 e os gráficos de 144 para 113. O que saiu da tela continua sendo
calculado (volta pondo o id numa parte): em Atividade, a confiança do consumidor, o PIB em
linhas pela oferta e pela demanda e a demanda privada em gráfico; em Trabalho, desalento e
procura longa; em Demografia, a projeção da ONU, a mortalidade infantil e os idosos em
gráfico; em Pobreza, a parte da fome virou "Pobreza e fome" e saíram lenha, aluguel, a
razão 10/40 e seis outros; em Juros, o juro real entrou em "Selic e juro real"; em Setor
externo, seis partes viraram três; em Impostos, seis viraram quatro; em Riscos, seis
viraram cinco e saíram a bolsa, os swaps, a dívida externa líquida, os atrasos do crédito,
os reservatórios e a tabela de governança.

E, a pedido do Caio (*"faça 1 e 2 já"*): **nove assuntos no lugar de treze**
(`secoes/juntos.py`: Trabalho e renda com a pobreza, Juros e crédito, Exterior e mercados,
Longo prazo com a demografia, a produtividade e a escola; as Previsões no Laboratório; os
endereços antigos redirecionam) e **a frase do que cada gráfico mostra hoje**
(`manchetes.py`, em 68 dos 100 gráficos). Os totais nos Dados: 42 partes, 125 cartões e
100 gráficos (eram 64, 158 e 144 de manhã). Saiu da tela na junção, e volta pondo o id
numa parte: o saneamento e a moradia, a fome em cartões, o Bolsa Família, a renda por sexo
e cor em cartões, os imóveis (concessões e taxa em gráfico), a curva de juro real e a
implícita a termo, a mortalidade infantil e os nascimentos.

Em Brasil no mundo, "Duas métricas" desenha com qualquer número de países e, quando não há
nenhum, diz por quê (a carga tributária da OCDE vai até 2024; em 2025 não há país) e leva
ao ano mais novo com as duas. Falta fazer o mesmo em Estados › Duas métricas.

O gráfico de duas métricas (Brasil no mundo, Estados e o de Impostos) agora sai como
imagem, em "PNG" ou "Copiar" (Caio, 16/11/2026: *"deixe exportar como imagem as duas
métricas ao mesmo tempo também"*), com o título, os eixos, quem ficou fora do desenho e a
fonte escritos nela (`botoesDaImagem` em `grafico.ts`). O "Copiar" vale para todos os
gráficos e só aparece onde o navegador copia imagem; dado privado continua sem nenhum dos
dois. Em 17/11 (*"veja se os outros gráficos podem/tem essa facilidade"*) ganharam os dois
botões também o mapa e o ranking de Estados, o ranking de Brasil no mundo e a pirâmide
etária (o ranking e a pirâmide são HTML na tela; para a imagem, são redesenhados no canvas:
`desenhoDoRanking` em `pontos.ts`, `desenhoDaPiramide` em `piramide.ts`). Ficam sem imagem,
por não serem gráfico: o painel de alerta, o "Saiu por último" e as tabelas (estas têm o CSV).

**17/11/2026** (Caio: *"Faça 1) laboratório que faltou e tem como separar as despesas das
obrigatórias? [...] comparar com outros países"*):
- **O Laboratório, leva 1** (`secoes/laboratorio.py`, `modelos/estatistica.py`): juro
  neutro por três métodos (Focus de três anos, juro real a termo de 5 a 10 anos dos títulos
  IPCA+, média de dez anos do juro real esperado), hiato por HP e Hamilton, regra de Taylor
  com a faixa das seis combinações, estudo de evento do Copom (167 reuniões desde 2006),
  teste de Bohn (até 2013 o primário reagia à dívida; depois, não se distingue de zero) e
  o PIB por habitante desde 1950 contra os EUA, com a decomposição por década.
- **Onde está o gasto** (Contas públicas, `secoes/gasto.py`): obrigatória e discricionária
  (RTN; ~10 % da despesa federal é discricionária) e a despesa por função do governo geral
  contra a mediana dos emergentes, da América Latina e dos avançados (COFOG do FMI).
- **Pergunta nova**: "Onde dá para cortar gasto?" (nove perguntas agora).

**19/11/2026** (Caio: *"nos impostos, dá pra separar oq é receita da união e dos Estados
e outros? E ver onde cada Estado e outros está gastando com a receita?"*):
- **Impostos › União, estados e municípios** (`impostos._esferas`): quanto cada esfera
  arrecada (OCDE; a União com o INSS fica com ~71 %), o repasse geral da União (FPE, FPM;
  4,7 % do PIB em 2024) e a tabela "Para onde vai a despesa de cada esfera" (FMI, COFOG por
  esfera: `fmi_cofog.por_esfera`, até 2024). O gráfico "Quem arrecada", que estava fora da
  tela, voltou nela. A pergunta "Para onde vai o imposto?" ganhou a tabela.
- **Estados › Mapa e ranking**: quatro métricas novas, "Gasto com saúde / educação /
  segurança / previdência", em % da despesa do estado sem os encargos especiais (DCA,
  conta nossa; `estados._gasto_por_area`).
- **Riscos › Custo, rolagem e crises**, o teste de estresse (Caio, mesmo dia: *"veja o
  efeito sobre outras métricas tb, coloque o parâmetro pra mudar a métrica no gráfico
  mesmo"* e *"deixe tbm escolher qual teste mostrar, se todos ou só alguns"*): o gráfico
  ganhou a lista "Métrica" (dívida, PIB, inflação, primário, dólar, Ibovespa e Selic) e
  fichas para ligar e desligar cada episódio, com "Todos". As contas anuais usam os mesmos
  desvios que já moviam a dívida; o mercado repete os 24 meses desde o começo da janela,
  no nível de hoje. O mecanismo é geral (`variantes` e `escolher_series` no `Grafico`,
  `web/src/variantes.ts`): outro gráfico pode usar.
- **"Ver em" nos gráficos de fluxo** (Caio, mesmo dia: *"No gráfico da arrecadação
  Federal, coloque um parâmetro pra mudar o gráfico em % do PIB, veja outras métricas
  parecidas [...] e aplique"*): a lista troca entre reais de hoje (pelo IPCA), % do PIB e,
  na arrecadação, o crescimento real. Em seis gráficos: arrecadação federal, os maiores
  tributos, receita e despesa, para onde vai a despesa, obrigatória × discricionária e o
  INSS (`com_variantes` e `em_reais_de_hoje` em `secoes/base.py`). Ficaram de fora, por
  pedirem série nova do SGS conferida no catálogo: o primário, a dívida e a conta corrente
  em reais (ou dólares). Entraram depois, conferidas: a dívida bruta e a líquida em reais
  (SGS 13761, que o CKAN não lista, e 4478; a razão com o PIB fecha com a 13762 e a 4513),
  o primário em reais de hoje (soma nossa da série mensal) e a conta corrente em dólares.
- **Parecidos atrás de uma lista, em todo o site** (Caio, mesmo dia: *"Aplique isso
  sistematicamente"*; a regra está no CLAUDE.md): gráfico ou tabela parecida fica atrás do
  principal, numa lista ("Gráfico" ou "Tabela"), e conta como um no orçamento
  (`AGRUPAR` em `organizacao.py`, `web/src/alternativas.ts`). Voltaram assim 44 dos 49
  gráficos e tabelas que estavam calculados e fora da tela (o PIB pela oferta e pela demanda, a fome,
  o saneamento, a moradia, o Gini, o desalento, as curvas de juro real, o imobiliário, a
  dívida por vencimento, a carga contra o crescimento, a população, a esperança de vida, a
  previdência dos servidores, os riscos de mercado...), e partes com dois ou três gráficos
  do mesmo tema ficaram com um na tela. A busca acha a peça de trás e a tela abre a lista
  nela. Ficaram fora: os três de Trabalho que repetem Longo prazo (analfabetismo e renda
  por escolaridade), os reservatórios e a tabela de governança de Riscos (sem par
  parecido) e 35 cartões (Trabalho, Juros, Longo prazo, Riscos): cartão não entra em lista
  (Caio, 19/11/2026: *"nos cartões não vamos aplicar por enquanto"*). O Laboratório não mudou: muda com o
  Caio olhando.
- Falta: os municípios um por um (são 5.570; hoje só as capitais têm conta no SICONFI aqui)
  e a receita de cada esfera *depois* dos repasses (o FMI separa o repasse geral, mas não
  quanto vai a estados e quanto a municípios).

**19/11/2026** (Caio: *"continue o laboratório com as propostas [...] essas métricas vão
nos ajudar a ver o desenrolar e de onde está vindo se tiver uma crise, bem como oq
poderíamos ter feito pra prevenir, o foco principal hj está no ajuste fiscal"*; e, sobre as
sugestões: *"Faz tudo, eu aprovo"*). No `main`. Oito peças novas no Laboratório
(`secoes/laboratorio_ajuste.py`, contas em `modelos/ajuste.py`), todas sobre o que já
aconteceu, e uma pergunta:
- **O mercado: de onde vem a pressão** (`#laboratorio/pressao`): o dólar em 12 meses
  repartido entre o que veio de fora e o que é só do Brasil (Federal Reserve, H.10), com as
  cinco maiores altas; e o estudo de evento do Copom, que veio para cá. O **estudo de
  evento dos anúncios fiscais** foi feito (24 datas conferidas em página oficial) e saiu da
  tela no mesmo dia: resultado fraco (Caio: *"Se o resultado for fraco, acho que não
  precisa colocar não"*); a lista e a conta ficam no código, sem serem chamadas.
- **O ajuste fiscal: o que foi feito** (`#laboratorio/reacao-fiscal`): a dívida com outro
  primário desde 2014, por onde o primário já mudou (receita ou despesa, RTN desde 1997), o
  **custo de esperar** (o primário que estabiliza conforme o ano de partida, com a dívida
  do Focus e a faixa do juro neutro) e o teste de Bohn.
- **O prometido e o que veio** (`#laboratorio/promessa`): **a meta original de cada LDO**
  contra o primário do Governo Central (25 leis lidas no Senado, `leis.METAS_DAS_LDOS`;
  abaixo da meta em 14 de 24 anos, e sem 2020 a média não se distingue de zero), o primário
  que o Focus esperava de um a quatro anos antes e a **dívida bruta que o Focus esperava,
  safra a safra**.
- **Pergunta nova, "De onde viria uma crise?"** (a décima; o teto do teste foi de nove
  para dez): copia peças do Laboratório, com "estimativa nossa" no texto.
O Laboratório segue com cinco partes: o estudo do Copom perdeu a parte própria, e os
cartões `dolar-beta` e `copom-dias` saíram da tela (continuam calculados).

## O que vem agora (fase 2)

Na ordem do plano; o que está aqui ainda não foi feito:

1. **Laboratório, o que ficou da leva 1**: o juro neutro e o hiato do Banco Central (lidos
   no Relatório de Política Monetária, com prazo em `leituras.py`) ao lado dos nossos; o
   estudo de evento com uma medida melhor de surpresa (sem a B3, só a curva do Tesouro do
   dia anterior); a decomposição do PIB por habitante com a população em idade de trabalhar
   (ONU), separando demografia de participação.
2. **Laboratório, leva 2** (do plano): controle sintético de episódios, quem ficou com o
   crescimento por faixa de renda, o tom das atas. Do viés das previsões, entraram o do
   Focus e a meta de cada LDO (19/11); faltam os parâmetros de cada orçamento (PIB, inflação
   e receita previstos) contra o que veio. O que sobrou de pressão e ajuste está no
   [PROPOSTAS](PROPOSTAS.md), "Crise e ajuste fiscal".
3. **O gasto, o que falta**: a série do gasto por função no tempo (o COFOG do Brasil desde
   2010) e a despesa por função só da União (o Tesouro publica o COFOG do Governo Central).
   América Latina tem só cinco países com COFOG do governo geral no FMI; Chile, México e
   Colômbia publicam só o governo central.
   **Servidores, o que falta**: o prêmio salarial com a mesma escolaridade (pede os
   microdados da PNAD: a tabela do SIDRA não cruza posição com instrução); a remuneração
   por poder nos estados (o RGF de cada tribunal e assembleia, 27 × 5 chamadas, e sem
   contagem de servidores); a folha por função (professores, policiais, saúde). **Estatais,
   o que falta**: as estaduais (só há o primário do BC) e a série da subvenção antes de 2021.
4. **A árvore do diagnóstico de crescimento** e o crédito direcionado nas perguntas.
5. **Contador de acesso nosso**: espera o projeto Supabase do sacibras.
6. **Estados e Brasil no mundo** com 6 métricas na lista; Estados › Duas métricas com poucos
   estados (como já é em Brasil no mundo).
7. **O glossário ainda aponta endereços antigos** (`#pobreza/fome`, `#credito/imoveis`).

## Releituras com prazo

A lista inteira sai de `sacibras leituras --todas` (`leituras.py`); a issue `releitura` avisa.
As próximas:

- **até 15/01/2027**: a LDO 2027 no Senado → o ano novo em `leis.METAS_DAS_LDOS`.
- **até 19/02/2027**: as dez perguntas (`perguntas.LIDAS_EM`).
- **até 24/11**: relatório do 5º bimestre (sai até 22/11) → `leis.AVALIACOES_2026` e
  `relatorios.RECEITA_PREVISTA`.
- **até 03/12**: nota fiscal do BC → `relatorios.ELASTICIDADES`.
- **até 14/12**: nota de crédito (`relatorios.NOTAS`; o sisweb estava fora do ar).
- **até 15/12**: quem está no RRF e no Propag (`relatorios.ACORDOS`): o RMGH de 2026 do
  Tesouro não abriu ("Falha na integração THOT/3PRO"); a lista saiu do RMGH de out/2025 e do
  RAF nº 114 da IFI (jul/2026).
- **até 23/12**: resolução do Senado que fixa a CBS de 2027 → `CBS_REFERENCIA_2027` e o texto
  "o Senado ainda fixa" em `impostos.py`.
- **até 31/12**: RPM de dezembro → modelos e faixa do efeito da Selic.
- **até 10/01/2027**: decreto do salário mínimo de 2027 → `leis.SALARIO_MINIMO_NORMAS`
  (o valor vem do SGS 1619; a tela só cita a norma do ano que estiver no dicionário).
- **até 20/01/2027**: teto do INSS de 2027 (portaria de janeiro) → `relatorios.TETO_INSS`.
- **até 28/02/2027**: aposentadoria média do INSS (BEPS, quadro 15) →
  `relatorios.INSS_APOSENTADORIA_MEDIA`.
- **até 15/05/2027**: avaliações atuariais do PLDO 2028 → `relatorios.SERVIDORES_POR_PODER`
  e `MILITARES_ATIVOS` (as tabelas por poder são imagem no PDF).
- **até 15/07/2027**: Relatório Agregado das Estatais 2027 (Sest) →
  `relatorios.ESTATAIS_POR_ANO`; a resposta da pergunta diz "o menor em cinco anos".
- **até 30/11/2027**: a conferência do PIB trimestral por estado contra RS, PR, MG, BA e ES
  (`relatorios.CONFERENCIA_PIB_ESTADOS`; `scripts/conferir_pib_estados.py` refaz).

## Só do PC

- Planalto: LDO 2027 (meta de primário, até 15/01), o acórdão do TCU da CBS de 2027 e a LRF
  compilada (limites de pessoal; da nuvem, a Câmara deu 404 e a lei foi lida no Senado). A EC
  132 e a LC 214 saíram desta lista: lidas no texto atualizado da Câmara em 15/11/2026.
- Nota de crédito no `sisweb.tesouro.gov.br` (fora do ar em 14/11), para confirmar o
  histórico depois de mai/2025.
- Fontes que recusam a nuvem, para testar e, se abrirem, pôr no painel:
  - Caged por UF (Ministério do Trabalho) e a tabela do SIDRA dos contribuintes da previdência
    (Demografia: contribuintes por beneficiário).
  - SIOPS e SIOPE: mínimos de saúde e educação dos estados (o TabNet do SIOPS derruba a
    conexão; o SIOPE só tem formulário, e o de indicadores é municipal).
  - Serviços subjacentes do IPCA: achar o código no SGS (a busca de séries dá 502 da nuvem;
    não está no CKAN nem nos códigos vizinhos).
  - Índices de preço e quantidade das exportações do MDIC (`balanca.economia.gov.br/balanca/IPQ/`,
    certificado vencido).
  - Déficit habitacional da Fundação João Pinheiro (403 da nuvem; ver se sai com regularidade).
  - ICMS modal por estado (o Confaz não respondeu; sem tabela oficial, são 27 leis).
  - O calendário do IBGE na caixa "O que sai esta semana" da entrada: a nuvem é recusada e as
    fotos usaram um calendário fabricado; conferir do PC que a caixa abre com o de verdade.

## Espera o Caio

- **Servidores e estatais foram ao `main`** (Caio, 19/11/2026: *"Pode manter assim"* e
  *"Vai pro main e deploy"*), com as perguntas agrupadas por tema. Segue para olhar quando
  der: a comparação de rendimento é de médias, sem controlar a escolaridade (o texto diz);
  na aposentadoria, o servidor é de jul/2025 e o INSS de set/2026; saíram da tela o primário
  mês a mês e o cartão da obrigatória em % do PIB. O tema "Governo: dívida, gasto e
  impostos" já tem cinco perguntas das seis que cabem: a próxima dele pede dividir o tema
  (por exemplo, "Dívida e impostos" e "Gasto, servidores e estatais").
- **Olhar as peças de 19/11**, que foram ao `main` (Caio: *"junte ao main"*). O que
  decidi sozinho e pode ser trocado: (1) "só do Brasil" no dólar é um resto e a faixa é
  estreita quando o dólar lá fora quase não se mexe; (2) o segundo cenário da dívida é piso
  de 1 % do PIB (a média de 2003 a 2013 dava 33 % do PIB, longe demais do que a conta
  mede); (3) pela regra do resultado fraco, do teste de Bohn ficou só a tabela dos
  dois períodos (o cartão e o gráfico saíram da tela); a meta da LDO fica inteira (Caio:
  *"Pode tirar só o do Bohn"*); (4) a meta da LDO é a cheia, sem o abatimento de PPI e PAC que a lei
  deixava de 2007 a 2014; (5) a décima pergunta passou do teto de nove: se pesar, a
  candidata a juntar com ela é "O que o mercado espera do Brasil?".
- **Na página traduzida para o inglês**, a 390 px, a tela "O prometido e o que veio" passa
  17 px do quadro (a unidade "pp do PIB" vira "percentage points of GDP" no cartão); em
  português cabe. Já era assim com o cartão do teste de Bohn.
- **Olhar o Laboratório e a pergunta do gasto**: os textos dizem o que a conta acha e onde
  ela é fraca. Pontos a conferir: a regra de Taylor dá 11,7 % contra a Selic de 13,75 %; o
  juro neutro vai de 5,1 % a 7,2 % conforme o método; o estudo de evento acha 4,5 pb no juro
  de 2 anos por 0,25 pp de surpresa (fora 2020).
- **Olhar as nove perguntas de novo**, agora com posição: cada resposta e cada "Juntando
  as peças" afirma o que o dado mostra e marca o que é disputado. Diga onde afirmei demais
  ou de menos. Prazo de releitura: 16/02/2027 (`perguntas.LIDAS_EM`).
- **Contador de acesso nosso** (Caio, 16/11/2026: *"a gente mesmo não pode saber quem
  acessou?"*): o site é estático, então a contagem precisa de um lugar para gravar. A
  proposta: um projeto Supabase só do sacibras (separado do finance_agent), com uma tabela
  que soma visitas por dia, página e termo de busca, sem cookie, sem IP e sem identificar
  ninguém. Falta o Caio criar o projeto (ou dizer para usar outro serviço).
- **Os 22 alertas que saíram do painel**: a lista está em `alertas.NO_PAINEL`; se algum
  fizer falta, volta trocando por outro.
- **Trecho da B3 sobre gráficos informativos**: o Ibovespa fica na tela por decisão do
  Caio (15/11/2026, *"Os termos da B3 permitem gráficos informativos"*), mas a cláusula não
  apareceu nos termos de uso nem na Política Comercial de Market Data 2027. Com o elo,
  copiar o trecho para `licencas.B3` e `docs/FONTES.md`.
- **FGV**: IGP-M e capacidade instalada saíram da tela (os termos vedam divulgar). Voltam
  com autorização por escrito da FGV ([PROPOSTAS](PROPOSTAS.md)).
- **Domínio**: a imagem de compartilhamento (`og:image`) usa `ENDERECO` em `web/vite.config.ts` (também o crédito escrito nas imagens dos gráficos)
  (hoje `https://jabiraka.github.io/sacibras/`); com domínio novo, trocar ali e em
  `anterior.SITE`.
- **Previsões próprias** de IPCA, desocupação e o PIB agora com indústria, varejo e serviços:
  fora por enquanto (Caio, 15/11/2026: *"sem próprias previsões por enquanto"*).
- Para olhar: Atividade › PIB tem seis gráficos em três pares (o PIB e a demanda privada;
  quem produziu e quem comprou; oferta e demanda em linhas). Se pesar, o par de linhas é o
  candidato a sair: a tabela com a escolha do período já dá a taxa de cada parte.
- Selo "dado anterior" na peça que ficou com o dado da véspera (o campo `mantidos` já está no
  `painel.json`).
- Tarefa agendada que relê os relatórios e abre PR ([PROPOSTAS](PROPOSTAS.md)).
- **Estados**: em que métrica Estados abre e o mapa a 1280 px; no [PROPOSTAS](PROPOSTAS.md),
  "Achados da revisão das telas", para uma sessão própria (Caio, 15/11/2026).
- Para olhar: a PTF estendida (2024 e 2025) é estimativa do que já passou, com dado oficial,
  não previsão. O ponto usa o capital humano da PNAD, que sobe mais devagar que o da PWT; a
  barra vai até a versão com o ritmo da PWT. Quando sair a PWT 12, comparar e, se a
  diferença for grande, rever a escolha.
- Para olhar: em Brasil no mundo, a PTF da Turquia (109 % da dos EUA) e a da Argentina
  passam a de vários países ricos; é o número da Penn World Table (PPC de cada ano), não erro
  daqui. O elo `#mundo/m-…` leva uns 4 s para trocar a métrica (já era assim).
- Para olhar: a ficha do estado tem agora 9 abas (quatro números à vista, o resto em "Mais
  números"); a CAPAG e o acordo da dívida aparecem com posição no ranking, como se fossem
  número.

## Dados estranhos na fonte (anotados na tela)

- Centis do IRPF de 2018 (Receita): o 0,01 % de cima com R$ 948 bi de renda (115 e 162 nos
  vizinhos) e a renda total do ano inflada junto: o ano fica em branco no gráfico do topo.
- RREO da União: o déficit do FCDF cai de R$ 8,5 bi (2024) para R$ 4,0 bi (2025) sem
  explicação; fica fora da previdência dos servidores.
- Previdência dos estados: saltos de registro (DF em 2023, SC em 2024, MS zerado em 2023-24;
  PI sem o Anexo 04 em 2021 e 2023).
- Caged por setor (SGS): os 11 subsetores de serviços não somam o total (falta ~1,15 mi em
  set/2026); a diferença vai numa linha "Demais serviços".
- Tesouro Direto: `tesouro_direto.curvas` fazia média com taxa 0,00 (lado sem negócio) e
  guardava linha sem preço; corrigido em 15/11 (a inflação implícita antiga de Juros pode
  mudar um pouco no próximo build).
