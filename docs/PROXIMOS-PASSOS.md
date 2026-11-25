# Próximos passos

**Leia no começo da sessão e atualize no fim** (Caio, 14/11/2026). Aqui fica só o que está em
aberto: o que foi feito sai (a história está no git), as ideias em espera ficam no
[PROPOSTAS](PROPOSTAS.md) e os limites conhecidos no [PLANO](PLANO.md#12-limites-conhecidos).

Última atualização: 25/11/2026 (de novo). A sessão da nuvem de 15/11 fez tudo o que dava para fazer de
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

**25/11/2026, texto curto em todo o site** (Caio: *"Aplique a regra de diminuir e resumir os
textos em todo o site"*). Todas as seções do builder, as perguntas, o painel de alerta
(`alertas.py`, uma frase por campo) e os textos fixos do `web/src`: notas de três a treze
frases ficaram em até duas (o método e a ressalva), títulos, subtítulos e legendas mais curtos,
respostas das perguntas em até duas frases e conclusões em até três. O detalhe que saiu da
tela foi para comentário no código, perto da peça. Ficaram as ressalvas que as regras pedem
("conta nossa", "não é o que a Selic causou", "compara médias", as faixas). O build agora
avisa **"nota longa"** (mais de duas frases ou 240 letras) em gráfico, variante e tabela
(`construir.textos_longos`). **Falta o Caio olhar** as telas: da nuvem não abri o site.
**No mesmo dia, o rótulo "conta nossa" conferido peça por peça** (Caio: *"tem alguns gráficos
que tá como 'conta nossa' mas talvez não seja realmente"*). Corrigido: o PIB por habitante
passa a vir pronto do IBGE (SIDRA 6784), com conta nossa só no ano que o IBGE ainda não
publicou; a linha do IPCA em "Desocupação mais inflação" é a série de 12 meses do IBGE (SGS
13522), e só a soma é nossa; o cartão da dívida que o Focus espera é "mercado", e a alíquota
cheia do Comitê Gestor é "oficial"; nos gráficos do Focus no Laboratório e na expectativa
contra a meta, a fonte diz que só o erro médio ou a meta do prazo é conta nossa; a tabela da
LDO 2027 ganhou "conta nossa" na coluna do primário que estabiliza pelo Focus, que não dizia.
"Cálculo próprio" virou "conta nossa" em todo lugar (eram três nomes para a mesma coisa;
"estimativa nossa" fica para o Laboratório e as perguntas). O que ficou em aberto está no
[PROPOSTAS](PROPOSTAS.md), "Rótulo de conta nossa".

**25/11/2026, o endereço exato de cada fonte** (Caio: *"Em todas as fontes, coloque o site de
onde estamos tirando a informação, o site exato"*). As regras moram em `links.py` (SGS e SIDRA
ganham um endereço por código; as instituições, a página dos dados), vão para `fontes.json` e
o site (`web/src/fontes.ts`) põe os links no rodapé de gráfico, tabela, mapa e ranking, e o
endereço por extenso no PNG, no CSV e na dica do cartão. Fonte sem regra cai na página geral da
instituição (IBGE, Banco Central, Tesouro) ou fica sem link: `links.sem_endereco`. Cada código de série (SGS, SIDRA) é link no próprio texto; instituição ganha o nome
linkado depois do texto, e o endereço vai na dica. Olhado a 390 e 1280 px em Inflação e
Atividade (sem estouro). **Falta**: abrir os endereços das regras do PC (só os SGS/SIDRA vêm das próprias chamadas do builder; os das
instituições foram escritos de cabeça e não foram abertos daqui).

**25/11/2026, troca suave nas listas dos gráficos** (Caio: *"quando clico num drop down [...]
as vezes muda do outro lado os gráficos, e o drop down muda um pouco de posição [...] deixe mais
smooth"*). Nas listas "Gráfico", "Tabela", "Ver em" e "Métrica" (`alternativas.ts`,
`variantes.ts`), a caixa guarda a maior altura que a peça já teve (a linha da grade e o gráfico
vizinho não pulam), a cabeça do gráfico com lista de métrica não encolhe (o menu fica no lugar) e
a peça nova entra com um fade de 0,28 s (`trocarSuave` em `pecas.ts`; sem animação para quem
pede menos movimento). O build passa, **mas da nuvem não abri o site (sem os dados): falta o
Caio olhar a 390 e 1280 px**. As outras listas (Estados, Mundo, Retornos) não mudaram.

**25/11/2026, o projeto da LDO 2027 no Laboratório** (Caio: *"tem como ver se isso vai
estabilizar a dívida [...]?"* e *"Pode já colocar, dizendo que ainda não virou lei [...] a
gente vai ter que monitorar se algo muda até a sanção"*). **O projeto não foi aprovado**: em
25/11 o PLN nº 2/2026 estava na CMO (relatório preliminar aprovado em 11/11, 1.504 emendas até
24/11). Entrou em Laboratório › O prometido e o que veio: o cartão da meta de 2027 (0,50 % do
PIB; "estabilizar pediria 2,2 %", do próprio anexo), o gráfico da dívida bruta do projeto contra
o Focus (atrás de "A dívida que o mercado esperava", lista "Gráfico") e a tabela de 2027 a 2030
(meta, primário antes dos descontos, dívida e PIB do governo e do Focus). Números em
`relatorios.PLDO_2027`, lidos no Senado. **Para monitorar**: `sacibras tramitacao`
(`tramitacao.py`) olha a matéria no Senado todo dia útil no workflow "Prazos de releitura" e
abre a issue `tramitação` quando a situação muda ou sai informe novo. A cada aviso: ler o
parecer ou o autógrafo, conferir a meta e os anexos e atualizar o que foi visto em
`tramitacao.py`. **Sancionada a lei**: a meta de 2027 vai para `leis.METAS_DAS_LDOS` e
`META_PRIMARIA_2027`, a peça deixa de dizer "projeto" e o projeto sai de `tramitacao.PROJETOS`.
No mesmo dia entrou a **conta nossa da dívida** (Caio: *"podemos trazer um cenário mais
realista do que a estimativa do governo aqui"* e *"veja oq é melhor [...] depois vai pro
main"*), no mesmo gráfico e na tabela "A dívida bruta, cenário a cenário": a identidade da
dívida (`modelos/ajuste.py`, "a dívida por cenário") refaz a linha do governo com uma sobra
de 0,6 pp por ano e repete a sensibilidade do Tesouro (Anexo V, tabela 13) a até 0,3 pp;
depois troca uma hipótese por vez pelas do Focus e roda as metas do projeto com o erro que as
LDOs já tiveram (0,6 pp; faixa de 0,1 a 1,2), com crescimento e juro do Focus. Em 25/11: o
governo vê 84,1 % do PIB em 2035, o Focus 103,0 %, a conta 100,0 % (de 94,9 a 105,0 %); da
diferença de 18,9 pp entre o Focus e o governo, 8,8 vêm do primário, 7,6 do crescimento e 2,5
do juro. **Depois de 2030** o Focus não colhe PIB nem Selic, mas colhe primário e dívida até
2035: o crescimento fica na última mediana e o juro é o que fecha a conta com a dívida do
próprio Focus. Testado e fora: manter a diferença de 2030 entre a Selic do Focus e a do
governo levava a dívida a 112 % em 2035, 9 pp acima do que o Focus espera.
E o **simulador da LDO** (Caio: *"deixe um simulador pra pessoa ir mudando os números e
vendo como isso afeta a meta"*), na mesma parte, guardado atrás do título "Simule a dívida
com as metas da LDO 2027": três controles contra o projeto (crescimento, juro, primário),
três botões (projeto, médias do Focus, Focus com o erro da história) e três respostas (a
dívida em 2035, o ano em que para de subir e de quanto a meta teria de ser para a dívida
voltar ao nível de 2026), mais a faixa do erro das metas. Os controles somam o mesmo tanto
em todos os anos, então o botão do Focus chega a 102,3 %, não aos 103,0 % do Focus.
A lista "Simular até" (Caio: *"deixe a pessoa escolher até quando quer ir"*) vai de 2030 a
2060; depois de 2036, o último ano do projeto, repete as hipóteses dele, e as linhas do
governo e do Focus param onde eles publicam.
**Texto curto virou regra** (Caio, 25/11: *"Diminua os textos [...] só informações
relevantes"*; está no CLAUDE.md): as peças da LDO e o simulador foram encurtados; o resto
do site, na sessão seguinte (abaixo).
**O primário que estabiliza, conciliado** (Caio: *"Temos uma diferença mto grande, entre 4,7%
do PIB e 2,2% [...] as pessoas ficarão confusas"*): a tabela "Primário que estabiliza a
dívida: de hoje ao que o governo supõe" (`secoes/estabiliza.py`) vai de um ao outro, em Riscos
› A dívida se sustenta? e no Laboratório: 4,7 % com o juro e o PIB de hoje; −2,5 do juro
(13,0 % → 9,8 %); −0,5 do PIB em reais; +0,5 de emissões que não são déficit; 2,2 % do
governo para 2027; e 3,6 % pelo Focus. O cartão de Riscos diz "com o juro e o PIB de hoje" e
o da LDO traz os dois números. **O 2,2 % do governo** é o primário do ano mais o quanto a
dívida sobe (Anexo IV.3, gráfico 2, lido na imagem: `relatorios.PLDO_2027_REQUERIDO`);
refeito com a tabela do anexo bate em todos os anos menos 2027 (2,4). A sobra de 0,6 pp da
nossa conta é isso: emissões que o governo projeta e a fórmula de livro não tem.
**Riscos continua na fórmula de livro**: testei trocar pelo método do governo (primário mais
a alta da dívida) e o "resto" foi de −3,8 a +4,5 pp do PIB por ano desde 2007, sem sinal
fixo (−0,1 em set/2026); o governo é que o supõe fixo em +0,6.
Olhada a 390 e 1280 px; **falta o Caio olhar**.

**24/11/2026, o site parou de atualizar** (Caio: *"faça com que o sacibras atualize todo dia
[...] como o site era atualizado antes"*): desde 20/11 as cinco rodadas agendadas do Actions
terminaram *canceladas*, porque o passo "Gerar os JSONs" passou dos 20 min do job e o site nunca
chegou a ser montado (o no ar é o de 20/11). `build-deploy.yml` agora tem `timeout-minutes: 60`
e as duas rodadas (9h40 e 19h) seguem de **segunda a sexta** (Caio, 25/11/2026: *"deixa só
se segunda a sexta mesmo"*). Vale olhar o tempo do
primeiro build: se passar de uns 40 min, o build pede corte ou paralelismo (Riscos, Estados e
Mundo são as seções lentas).

**20/11/2026, indicadores clássicos** (Caio: *"veja se dá pra colocar, se não ficar muito
poluído, gráficos ou variações de gráficos com as métricas que temos, alguns indicadores que
economistas usam"*; e depois: *"Pode incluir os outros também de média confiança, faça tudo e
pode deploy"*). Dez gráficos novos, no `main`; nove ficam atrás de uma lista (nenhuma tela
ganhou peça à vista, fora Inflação › Outros índices, que tinha um gráfico só). Olhados a 390
e 1280 px com dados reais; **falta o Caio olhar**:
- **Juros › Curva**, lista "Gráfico" › "Inclinação no tempo": o prefixado de 3 anos menos a
  Selic, mês a mês desde 2011 (`juros.inclinacao_no_tempo`). Abaixo de zero, curva invertida.
- **Inflação › Outros índices e o Focus**: a inflação esperada para os 12 meses seguintes
  (Focus, a suavizada) contra o centro da meta do mesmo período (`inflacao.grafico_expectativa`;
  a meta de cada ano vem da série 13521 do SGS, a mesma do painel de alerta).
- **Trabalho › Renda**, lista da massa › "Emprego ou salário": a variação da massa de
  rendimento em 12 meses repartida entre mais gente ocupada e o rendimento de cada um
  (`decomposicoes.massa_por_fator`; conta nossa, fecha com a massa do IBGE).
- **Exterior › Dólar e bolsa**, lista do Ibovespa › "Descontada a inflação" (`mercados.ibovespa_real`).
- **Atividade › PIB**, lista › "Por habitante, ano a ano": o crescimento do PIB e o mesmo
  descontada a população (`atividade.pib_por_habitante`).
- **Trabalho › Desemprego**: atrás da desocupação, "Somada à inflação" (o índice de miséria
  de Okun, com o nome "Desocupação mais inflação"); atrás de "Por que mudou", "Contra o PIB
  (Okun)" e "Contra a inflação (Phillips)", um ponto por ano desde 2013, com a correlação
  dita em palavras. O gráfico de pontos ganhou o destaque, os nomes da legenda e o rótulo em
  todos os pontos como opção (`Dispersao` no `schema.py`, `web/src/dispersao.ts`).
- **Longo prazo › Produtividade**, lista › "Contra o rendimento": o rendimento real e o PIB
  por ocupado, os dois com 100 em 2012 (`produtividade.rendimento_e_produto`).
- **Contas públicas › Receita e gasto**, lista › "Crescimento real da despesa": a despesa
  total do Governo Central em 12 meses, acima da inflação, contra a faixa de 0,6 % a 2,5 % do
  arcabouço (`leis.FAIXA_DA_DESPESA`, LC 200/2023 lida no Senado, com prazo em `leituras.py`).
  **É a despesa total, não a sujeita ao limite**, e a nota diz isso.
Verbetes novos no glossário (inclinação da curva, expectativas desancoradas, curva de
Phillips, lei de Okun, arcabouço fiscal) e sinônimos na busca. Nenhum entrou em pergunta, mas
cada um responde a uma: a expectativa, "A inflação está sob controle?"; a massa por fator,
Okun e Phillips, "O emprego está bom mesmo?"; a inclinação e o Ibovespa real, "O que o mercado
espera do Brasil?"; o PIB por habitante e o rendimento contra o produto, "Por que o Brasil
cresce pouco?" e "Quem ficou com o crescimento?"; a despesa real, "Onde dá para cortar
gasto?". Trocar um gráfico de lá por um destes é decisão do Caio. Da nuvem, o build completo
não terminou em dez minutos (Riscos, Estados e Mundo são lentos daqui): as seções tocadas
foram geradas uma a uma; conferir o primeiro build do Actions.

**20/11/2026**, a pedido do Caio (*"quando copiar imagem ou PNG, coloque algum indicativo que seja do sacibras para dar os créditos"*): toda imagem de gráfico (PNG e Copiar, `pngDaFigura` em `grafico.ts`) fecha com uma linha de crédito: o losango, "sacibras", "painel da economia brasileira" e o endereço do site (o endereço do GitHub Pages, de `ENDERECO` em `vite.config.ts`). Testada com um gráfico de exemplo; falta olhar o mapa, os rankings, a pirâmide e o painel de alerta.

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

- **até 23/12**: o projeto da LDO 2027 (`relatorios.PLDO_2027`), antes se a issue `tramitação` abrir.
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
