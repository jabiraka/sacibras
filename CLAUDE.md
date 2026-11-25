# sacibras — regras para o Claude

Painel da economia brasileira (site estático + builder em Python). O plano, as fontes testadas e
as fases estão em [docs/PLANO.md](docs/PLANO.md) — leia antes de começar.

**Comece e termine pelo [docs/PROXIMOS-PASSOS.md](docs/PROXIMOS-PASSOS.md)** (Caio, 14/11/2026):
no começo da sessão ele diz o que fazer e o que espera decisão; no fim, atualize-o (o que foi
feito sai, o que apareceu entra, a data muda) e mande no mesmo commit.
Pedido ou ideia que não entra agora vira linha no [docs/PROPOSTAS.md](docs/PROPOSTAS.md)
(Caio, 14/11/2026: *"anote no propostas"*).

## Dados

- **Sem banco em produção.** O builder chama as APIs e gera JSONs que vão com o site; nada de
  dado é commitado (`web/public/data/` está no `.gitignore`). A exceção é a malha dos estados
  (`web/src/mapa/ufs.json`, ~50 KB): a API de malhas do IBGE recusa quem está fora do Brasil,
  como o GitHub Actions, então ela é gerada do shapefile oficial por `npm run malha` e fica no
  repositório. Fronteira quase não muda; rodar de novo só com malha nova do IBGE.
- **Bases separadas do finance_agent** (Caio, 13/11/2026). Nunca ler nem escrever no Postgres
  (`fa_postgres`, 5433) nem no Supabase dele. O Postgres local do sacibras é `sb_postgres`, porta
  5434, volume `sb_pgdata`, e serve só de cache de desenvolvimento. Código útil do finance_agent
  é copiado e adaptado, nunca importado.
- **Por enquanto, testar em Docker** (Caio, 13/11/2026): `docker compose` com `name: sacibras`.
  No PC do Caio, a `.venv` do uv quebra (o "Á" de "Área de Trabalho" no `.pth` e os hardlinks
  do OneDrive); os testes rodam num container com a venv num volume:
  `docker run --rm -v "$(pwd -W)/builder:/app/builder" -v sb_testvenv:/venv -e UV_PROJECT_ENVIRONMENT=/venv -e UV_LINK_MODE=copy -w /app/builder ghcr.io/astral-sh/uv:python3.12-bookworm-slim sh -c "uv sync --frozen -q && uv run pytest -q"`
  (no Git Bash, com `MSYS_NO_PATHCONV=1`).
- **Registro explícito de séries com unidade** em `builder/src/sacibras/catalogo.py`. Série nova
  só entra depois de conferida no catálogo da fonte (para o SGS:
  `dadosabertos.bcb.gov.br/api/3/action/package_search?fq=codigo_sgs:N`), com a data no comentário.
  Série que o BC não lista no CKAN (EX3, P55, industriais, alimentação no domicílio) se confere
  no serviço de metadados do próprio SGS e, quando der, contra outra fonte oficial (o IBGE),
  dito no comentário (aprovado pelo Caio em 14/11/2026).
- **Número lido à mão tem prazo** (Caio, 14/11/2026): o que entra em `leis.py` ou
  `relatorios.py` ganha linha em `builder/src/sacibras/leituras.py` (lida em, reler até, onde
  procurar). Ao reler, atualizar as duas datas. O workflow "Prazos de releitura" abre a issue
  `releitura`; fonte que falha no build abre a `fonte fora do ar`.
- **Valor nunca em branco** (Caio, 14/11/2026: *"se o agendamento falhar, pode manter os
  dados = ao dia anterior, nunca deixe em branco os valores"*): o workflow roda `sacibras
  anterior` (traz os JSONs do site no ar) antes do build. Seção que falha fica com o JSON
  anterior; seção que sai com fonte falhando recebe de volta o que faltou (`completar` em
  `construir.py`: só ids listados em `PARTES`, e só se uma URL falhou em `rede.FALHAS`). Cada
  peça mantida leva a data de referência dela, e a issue `fonte fora do ar` lista o que ficou.
- **Nada da B3 no projeto** (Caio, 25/11/2026: *"não queremos correr esse risco, então
  retire qualquer que for informações da B3"*): saíram o Ibovespa (que vinha do Ipeadata), os
  índices, os futuros e o código que lia o site (`SB_B3`), e o Ibovespa dos alertas e dos testes
  de estresse. `licencas.B3` tem `mostra=False`: peça que cite a B3 sai da tela sozinha. Dado
  que a B3 licencia (índice, preço de ação, DI, futuros) não volta sem autorização por escrito.
- **Norma se lê na fonte oficial, do PC** (o Planalto e o `servicodados` do IBGE recusam quem
  está fora do Brasil, como a nuvem e o Actions). Da nuvem, lei e emenda abrem em outras duas
  fontes oficiais: o Senado (`legis.senado.leg.br/norma/<id>/publicacao/<id>`) e a Câmara
  (`www2.camara.leg.br/legin/...-normaatualizada-pl.html`, o texto já com as alterações). No Windows, o `curl` do Planalto precisa de
  `--ssl-no-revoke`. Resolução do Senado: `legis.senado.leg.br/norma/<id>` (o id sai de
  `legis.senado.leg.br/dadosabertos/legislacao/lista?tipo=RSF&numero=N&ano=A`). O trecho lido
  vai como comentário em `leis.py`, com a data.
- **Curvas do Tesouro pelo método do Jabs** (Caio, 14/11/2026: *"o Jabs tem uma curva de
  inflação"*): taxa média entre compra e venda, curva zero com os papéis com cupom por
  *bootstrap*, fator de desconto log-linear, nada extrapolado (`builder/src/sacibras/curvas.py`,
  copiado e adaptado do `domain/curves.py` do finance_agent). Comparação com o Focus sempre no
  mesmo prazo (`media_do_caminho`), nunca taxa contra taxa de anos diferentes.
- **Só o que sai com regularidade e com método** (Caio, 15/11/2026: *"elimine tudo oq não
  for publicado regularmente e com metodologia, vamos manter apenas as nossas estimativas
  nesse caso"*). Estudo, artigo, texto para discussão ou nota técnica de uma vez só não entra
  (saíram os multiplicadores de imposto, a incidência por décimo do Ipea, as notas da Fazenda
  de 2024 sobre a alíquota da reforma e a proposta de Lara Resende); onde não há publicação
  regular, fica só a estimativa nossa, com o método dito. Entra o que tem calendário (nota
  mensal, relatório trimestral ou semestral, resolução anual, série) e a nota de crédito,
  que as agências revisam. O simulador da Selic fica (Caio, mesmo dia): os modelos
  semiestruturais são os do BC, usados em todo Relatório de Política Monetária.
- **Conta nossa sobre dado oficial entra, dita como nossa** (Caio, 15/11/2026: *"se fizemos
  a conta, é nossa"*, sobre o carrego do PIB; e *"junte no main"*, sobre o PIB trimestral por
  estado e as decomposições). Vale para o que reparte ou junta número já publicado
  (`modelos/decomposicoes.py`, `modelos/pib_estados.py`): a fonte diz "conta nossa", a soma
  fecha com o número oficial, o método vai em uma frase e, onde a conta pode errar, vai a faixa
  de erro medida e a conferência contra quem publica número parecido (os institutos estaduais,
  `relatorios.CONFERENCIA_PIB_ESTADOS`). Previsão do que ainda não aconteceu continua fora
  (*"sem próprias previsões por enquanto"*).
- **Dado privado: na tela só se a licença deixar, e nunca com download** (Caio, 15/11/2026:
  *"não deixe exportar oq for de fontes privadas, grave a licença de dados desses sites"* e
  *"A regra é não exportar, mas podemos só mostrar se for permitido dessas fontes
  privadas"*): a licença lida de cada fonte que não é do governo mora em
  `builder/src/sacibras/licencas.py`, com o trecho e a data. `mostra=False` (FGV) tira da
  tela sozinho (`ctx.sgs` recusa, o `construir` tira a peça); `exporta=False` (FGV,
  Fecomercio, B3) tira o CSV e o PNG. Série do SGS feita por terceiro leva `origem` no
  catálogo (o SGS repassa, não relicencia). Fonte privada nova só entra com a licença lida e
  registrada; quando quem decide é o Caio, vai em `decisao`.
- **Projeto que ainda não é lei entra dizendo isso** (Caio, 25/11/2026, sobre a LDO 2027:
  *"Pode já colocar, dizendo que ainda não virou lei [...] a gente vai ter que monitorar se
  algo muda até a sanção"*): o número vem do texto do projeto no Senado, em `relatorios.py`,
  e a tela diz "projeto, não é lei" e onde ele está. O projeto entra em
  `tramitacao.PROJETOS`; o `sacibras tramitacao` abre a issue `tramitação` quando ele anda.
  Sancionada a lei, o número passa para `leis.py` e o projeto sai da lista. Junto vai a
  conta nossa da dívida por cenário (Caio, mesmo dia: *"podemos trazer um cenário mais
  realista do que a estimativa do governo"*; `modelos/ajuste.py`): primeiro refaz a linha
  do governo e a sensibilidade que o Tesouro publica, e diz na tela a sobra; depois troca
  uma hipótese por vez pelas do Focus e roda as metas com o erro que as LDOs já tiveram, em
  faixa. Sem efeito do ajuste sobre o PIB nem da dívida sobre o juro. **E o simulador da
  LDO** (Caio, mesmo dia: *"deixe um simulador pra pessoa ir mudando os números e vendo
  como isso afeta a meta"*; `SimuladorLDO`, `web/src/simulador-ldo.ts`), em Laboratório › O
  prometido e o que veio: a linha de base é o projeto; três controles (crescimento, juro,
  primário) e botões que carregam o projeto, as médias do Focus e o erro da história. Diz
  aonde a dívida chega, quando para de subir e de quanto a meta teria de ser para ela
  voltar ao nível de partida, sempre com a faixa do erro que as metas já tiveram.
- **Fonte com o endereço exato** (Caio, 25/11/2026: *"coloque o site de onde estamos tirando a informação, o site exato"*): fonte nova ganha regra em `builder/src/sacibras/links.py` (o site põe o link e o endereço na imagem e no CSV).
- **Fonte oficial e citada** em todo gráfico. Número de lei (meta de inflação, limites da LRF,
  reforma tributária) vem da lei lida.

## Tela

- **O gancho é a pergunta, não o dado** (Caio, 16/11/2026: *"o gancho vai ser problemas e
  perguntas que as pessoas buscam algum tipo de resposta, vamos evitar mostrar só o dado pelo
  dado, ela pode pegar de outros lugares, vamos procurar mostrar o dado que responde uma
  pergunta ou problema"*). O site tem três andares ([docs/PLANO-FASE-2.md](docs/PLANO-FASE-2.md)):
  **Perguntas** (a entrada), **Dados** (os assuntos) e **Laboratório** (estimativas nossas,
  ainda por fazer). As perguntas moram em `builder/src/sacibras/perguntas.py`: resposta curta,
  até 3 números, de 3 a 6 explicações na ordem em que contam a história, cada uma com até 2
  números, 1 gráfico e, se couber, 1 tabela **copiados dos assuntos**, com a data e a fonte
  deles, e a conclusão ("Juntando as peças"). A pergunta pode copiar peça do Laboratório
  (Caio, 19/11/2026, sobre "De onde viria uma crise?"): o texto do bloco diz então
  "estimativa nossa". São dez perguntas, o teto do teste. A tela (`#pergunta/<id>`) abre a primeira
  explicação e guarda as outras atrás do clique. **Peça nova nos Dados diz a que pergunta
  responde**; se não responde a nenhuma, pense duas vezes antes de pôr. Pergunta nova ganha
  as palavras de busca em `palavras`.
- **Perguntas por tema, sem teto para o total** (Caio, 19/11/2026: *"podemos incluir mais
  perguntas com o tempo, entao é bom ter uma sessão própria ou organizar melhor as perguntas
  dentro dos temas"*): cada pergunta tem tema em `perguntas.TEMA_DE` (os temas e a ordem em
  `perguntas.TEMAS`), e a entrada, o menu e o pé de cada pergunta listam por tema. O teto é
  por tema (`MAXIMO_POR_TEMA`, seis, em teste): tema cheio pede tema novo ou juntar duas.
- **Claro onde a evidência é clara, em aberto onde ela é fraca** (Caio, 16/11/2026: *"não
  precisa ser completamente neutro, não existe isso, fale oq for mais provável com base na
  história contada [...] é melhor ser mais claro do que deixar implícito pra interpretação"*;
  e logo depois: *"também não podemos afirmar oq não se sustenta, se a evidência for fraca,
  melhor deixar mais em aberto mesmo"*). Nas perguntas, três degraus, e o texto diz em qual
  está: o que o dado do painel mostra e o que é conta ou regra se afirmam; causa, peso de
  cada causa e efeito de política se dizem plausíveis, disputados ou "os dados daqui não
  decidem". Sem número que o painel não tem. As respostas falam do momento ("ainda não"):
  têm prazo de releitura em `leituras.py` (`perguntas.LIDAS_EM`), e relê-se antes se o dado
  virar.
- **Comparar antes de dizer "pouco" ou "muito"** (Caio, 16/11/2026: *"talvez seja melhor
  comparar com outros países ao invés de mostrar só o quanto investimos"*): quem afirma que
  um número é alto ou baixo mostra contra o quê (outros países, a própria história, a meta).
- **Nome de dentro não vai à tela** (Caio, 16/11/2026: *"elimine 'cálculo do Jabs' [...]
  ninguém sabe oq é isso"*): o método se descreve ("curva zero por bootstrap"), sem "Jabs".
- **Orçamento de atenção** (Caio, 16/11/2026: *"os humanos não conseguem absorver muitas
  informações"*): à vista, uma frase, até 4 números e um gráfico por tela; o resto abre no
  clique. Nos Dados, o teto está em `organizacao.py` e em teste: **até 5 partes por assunto
  e, por parte, até 4 números e 3 gráficos** (tabela não tem teto: fica atrás do clique).
  Entra um, sai um. **Peça que a seção calcula e não está em `PARTES` sai da tela** (não há
  mais "Outros" para cartão, gráfico ou tabela); o builder avisa quais ficaram de fora.
- **Parecidos atrás de uma lista** (Caio, 19/11/2026: *"vamos usar o artifício de colocar
  parâmetros para gráficos parecidos, assim mudando o parâmetro muda o gráfico ou tabela,
  podendo acrescentar informações ao site sem ter que excluir coisas e sem ficar pesado de
  informações, mantendo amostra do principal. Aplique isso sistematicamente"*). Duas
  formas: a mesma conta em outra unidade ou métrica vai em `variantes` do gráfico (lista
  "Ver em" ou "Métrica": `com_variantes` em `secoes/base.py`); outro gráfico ou tabela do
  mesmo tema vai atrás do principal em `AGRUPAR` (`organizacao.py`; lista "Gráfico" ou
  "Tabela"), que conta como um só no orçamento. Peça nova que se parece com uma da tela
  entra atrás dela antes de pensar em tirar outra.
- **Nove assuntos nos Dados** (Caio, 16/11/2026: *"faça 1 e 2 já"*, sobre juntar os
  assuntos e a frase do gráfico): Atividade, Trabalho e renda (com a pobreza), Inflação,
  Juros e crédito, Contas públicas, Impostos, Exterior e mercados, Longo prazo (demografia,
  produtividade e escola) e Riscos; mais os comparadores (Estados, Brasil no mundo) e o
  Laboratório, que por enquanto só tem as Previsões. Cada seção antiga segue no módulo
  dela; `builder/src/sacibras/secoes/juntos.py` as une num assunto, com um arquivo e um
  endereço. Endereço antigo (`#pobreza`, `#credito`, `#mercados`, `#demografia`) redireciona
  (`juntos.ANTIGOS`). Assunto novo só entra tirando ou juntando outro.
- **Todo gráfico sai como imagem** (Caio, 16 e 17/11/2026: *"deixe exportar como imagem
  [...] como PNG ou copiar a imagem"* e *"veja se os outros gráficos podem/tem essa
  facilidade"*): "PNG" e "Copiar" no rodapé, com título, legenda, nota e fonte escritos na
  imagem (`botoesDaImagem` em `grafico.ts`). Gráfico novo fora do `montarGrafico` ganha os
  dois; se a tela é HTML, um `Desenho` no canvas. Dado privado sem exportação não tem nenhum.
- **A frase do gráfico** (Caio, 16/11/2026, junto com os nove assuntos): todo gráfico de série no tempo leva, sob o título, o
  que ele mostra hoje, escrito pelo builder (`manchetes.py`): o último valor contra a meta
  (se o gráfico tem a faixa), o maior ou o menor nível em pelo menos três anos, ou um ano
  antes. Sem causa e sem adjetivo. Quem quiser outra frase preenche `manchete` no gráfico.
- **Página inicial enxuta, o resto abre no clique** (Caio, 14/11/2026: *"muitas métricas na
  página inicial… deixar só as informações essenciais no início e deixar o usuário ir clicando
  pra abrir"*). Na entrada: quatro números (`RESUMO` em `construir.py`), o "Saiu por último",
  as perguntas (só o título de cada uma) e, no fim, os assuntos só pelo nome, uma linha por
  categoria. Os quatro gráficos de 15/11 saíram em 16/11: cada um mora agora na pergunta a
  que responde.
- **"Saiu por último", na entrada** (Caio, 16/11/2026: *"pode incluir"*): logo abaixo dos
  quatro números, o IPCA do mês, a Selic, a desocupação e o PIB contra a última mediana do
  Focus antes de sair (`builder/src/sacibras/saiu.py`, `web/src/saiu.ts`), com o quanto o
  Focus costuma errar ali. Acima ou abaixo do esperado vai em tinta neutra, sem "bom" nem
  "ruim". Divulgação nova só entra se o Focus coletar a mediana dela (mensal, trimestral ou
  por reunião); sem previsão nossa.
- **Regras afrouxadas, só no Laboratório** (Caio, 16/11/2026: *"pode afrouxar minhas
  regras"* e *"pode seguir"*, sobre o [PLANO-FASE-2](docs/PLANO-FASE-2.md)): lá entram
  previsão nossa com o placar contra o Focus na tela, parâmetro da literatura como faixa
  entre pelo menos três estudos citados (nunca um ponto só), simulador cujo resultado sai
  como faixa, e avaliação de política que já aconteceu, com teste de placebo. Nos Dados e
  nas Perguntas nada muda: fonte oficial ou conta nossa que fecha com ela. Continua fora o
  efeito de política futura sobre PIB e emprego. **O Laboratório** (Caio, 17/11/2026: *"Faça
  1) laboratório"*) é a seção `builder/src/sacibras/secoes/laboratorio.py`, ao lado das
  Previsões: juro neutro por três métodos, hiato por dois filtros, regra de Taylor com a
  faixa entre eles, estudo de evento do Copom, teste de Bohn e o PIB por habitante desde
  1950 (Penn World Table). As contas de estatística moram em `modelos/estatistica.py`, sem
  biblioteca de fora (MQO com erro de Newey-West, HP, Hamilton). Cada peça diz o método e
  mostra a faixa; resultado fraco se diz fraco (o estudo de evento, por exemplo, mede mal a
  surpresa sem os juros futuros da B3). Em 19/11/2026 (Caio: *"essas métricas vão nos
  ajudar a ver [...] de onde está vindo se tiver uma crise, bem como oq poderíamos ter feito
  pra prevenir, o foco principal hj está no ajuste fiscal"*; e *"Faz tudo, eu aprovo"*)
  entraram as peças de pressão e ajuste (`secoes/laboratorio_ajuste.py`,
  `modelos/ajuste.py`): o dólar repartido entre o mundo e o Brasil, a dívida com outro primário,
  por onde o primário já mudou, o custo de esperar, a meta original de cada LDO contra o que
  veio (`leis.METAS_DAS_LDOS`) e o primário e a dívida que o Focus esperava. Todas refazem
  o que já aconteceu. O Laboratório está no teto de cinco partes. **Resultado fraco não precisa ir à tela**
  (Caio, 19/11/2026: *"Se o resultado for fraco, acho que não precisa colocar não"*, sobre
  o estudo de evento dos anúncios fiscais, que saiu): conta que não distingue o efeito do
  acaso fica no código e no PROPOSTAS como "testada e fora", não na tela com ressalva. Pelo
  mesmo motivo, do teste de Bohn ficou só a tabela dos dois períodos (Caio, mesmo dia:
  *"Pode tirar só o do Bohn"*): o cartão e o gráfico mostravam a amostra inteira, que não
  se distingue de zero. Peça nova dele vai ao ar com o Caio olhando.
- **O gasto: obrigatório, discricionário e por função** (Caio, 16/11/2026: *"tem como
  separar as despesas das obrigatórias? Talvez fazer uma análise de onde dá pra cortar
  gastos [...] comparar com outros países"*): Contas públicas › Receita e gasto
  (`secoes/gasto.py`). Obrigatória e discricionária vêm do RTN (Governo Central); a
  comparação por função, do COFOG do FMI (governo geral, `fontes/fmi_cofog.py`), contra a
  mediana dos grupos do FMI. A tela não diz onde cortar: mostra onde o Brasil gasta acima dos
  outros e o que a lei amarra, e diz que eficiência de cada programa estes dados não medem.
- **Servidores e estatais** (Caio, 19/11/2026: *"inclua a distribuição dos gastos por
  servidores públicos (quem fica com mais) e compare o rendimento e benefícios dos servidores
  com o setor privado, adicione uma pergunta de quanto as estatais dão lucro ou prejuízo aos
  cofres públicos"*): Contas públicas › Servidores públicos (`secoes/servidores.py`) e ›
  Estatais (`secoes/estatais.py`). A folha vem por esfera e contra os outros países (FMI),
  por tipo (RTN), por poder (Siconfi, com a remuneração média lida na avaliação atuarial do
  PLDO) e o contracheque contra o do setor privado (PNAD). **A comparação é de médias, e a
  tela diz isso**: o servidor tem mais escola, e estes dados não separam o quanto da diferença
  vem daí. Nas estatais, a conta é a do caixa (dividendos menos subvenção e aporte, a mesma
  que a Sest faz), dita como tal: não é o lucro das empresas nem o valor delas, e a tela não
  diz se vale a pena o Estado ser dono. Para caber no teto de cinco partes, a meta fiscal
  entrou em "Primário, juros e meta" e a receita e a despesa da União em "Receita e gasto".
- **Categorias e partes, pouca coisa por tela** (Caio, 14/11/2026: *"humanos não conseguem ler
  muitas informações em uma página [...] classifique melhor em categorias, crie
  subcategorias"*). Tudo mora em `builder/src/sacibras/organizacao.py`: `CATEGORIAS` agrupa os
  assuntos (menu e entrada) e `PARTES` divide cada assunto em 3 a 5 partes. O assunto abre
  numa visão geral (quatro números, a lista das partes e o gráfico principal); cada parte abre
  numa tela só dela (`#inflacao/nucleos`), com a trilha em cima e as outras partes embaixo.
  **Cartão, gráfico ou tabela novo ganha lugar numa parte** em `PARTES`: o que não estiver lá
  não aparece, e o builder avisa ("peças fora da tela"). Estados tem partes
  próprias (`PARTES_ESTADOS`: mapa e ranking, um estado por dentro, duas métricas, tabela;
  Caio, 14/11/2026: *"diminua a tela ao abrir por estado"*), e a ficha do estado mostra um
  bloco de cada vez, em abas. Brasil no mundo tem tela própria, sem partes.
- **Menu lateral** (Caio, 14/11/2026: *"usar um pouco o espaço ao lado esquerdo para colocar
  as abas, e também quem sabe deixar a pesquisa lá"*): na tela larga (≥ 1024 px), uma coluna
  fixa com a marca, a busca e as categorias, e as partes do assunto aberto; no celular, a faixa
  do topo com a marca, a busca e o botão "Assuntos", que abre o mesmo menu.
- **O desenho segue o do finjabs** (Caio, 14/11/2026): cartões de vidro,
  Geist, título grande com a segunda metade apagada. O que é só daqui: as luzes de fundo
  verde, amarela e azul e o losango da marca. **Só o tema claro, sem botão de tema** (Caio,
  14/11/2026: *"deixe sempre o tema claro sem opção de tema escuro"*).
- **Número com meta se mostra contra a meta** (Caio, 14/11/2026, o IPCA na entrada): o
  cartão leva `meta` (centro e intervalo, da norma lida) e a tela diz em palavras e na régua
  se está dentro, acima do teto ou abaixo do piso. A meta de primário (Caio, 14/11/2026,
  opção "b"): o número de quem apura (BC) contra a meta da LDO, em reais, com o desconto da
  apuração oficial dito ao lado, do relatório bimestral (`leis.AVALIACOES_2026`, ler de novo a
  cada bimestre).
- **Busca** (Caio, 14/11/2026: *"barra de pesquisa pras pessoas pesquisarem por nome ou
  sinônimos"*): o campo fica fixo no menu lateral (no celular, na faixa do topo) e os
  resultados aparecem logo abaixo dele, sem janela por cima (Caio, 14/11/2026: *"a pesquisa
  não precisa abrir um outro negócio, pode manter fixo"*); atalho "/". O índice
  (`busca.json`) sai do builder (`busca.py`) com tudo o que a tela mostra, as partes inclusive,
  e cada resultado diz onde mora ("Juros e Copom › Juro real · número"); o clique abre a parte
  e vai até o número, gráfico ou tabela. Coisa nova que alguém procuraria por outra palavra
  ganha o sinônimo em `SINONIMOS`.
- **Glossário** (Caio, 14/11/2026: *"ela clica ou na palavra ou em um ? que abre a definição
  dela [...] só um balão"*): termo que alguém poderia não saber ganha verbete em
  `builder/src/sacibras/glossario.py` (até três frases, sem jargão; número de lei só de norma
  lida). A tela sublinha a palavra e põe "?" nos rótulos sozinha. Indicador novo no painel de
  alerta ganha "o que é / por que é alerta / pode levar a" em `alertas.py`.
- **Texto curto, sempre** (Caio, 25/11/2026: *"Diminua os textos [...] coloque isso como
  regra nas próximas sessões, tem que ser coisas bem mais simples e sumários, só informações
  relevantes nos textos"*). Vale para tudo o que vai à tela: título em uma linha, legenda
  de série em poucas palavras ("Governo", "Focus"), frase do gráfico só com os números,
  nota em até duas frases (o método e a ressalva que muda a leitura) e resultado de
  simulador em uma linha por resposta. Detalhe de método, conferência e história da conta
  ficam no código e nos docs, não na tela. Texto novo se escreve curto; ao mexer numa peça
  antiga, encurta-se o texto dela junto.
- **Resultado: só o essencial** (Caio, 14/11/2026: *"se for apresentar o resultado, escreva
  só o essencial, sem muitos detalhes e contextos"*). O texto embaixo do número no cartão
  (`detalhe`) tem até 60 letras (o builder avisa: "detalhe longo"); explicação vai para a nota
  do gráfico ou para o glossário. Resultado que é um nome (a nota de crédito, "BB") vai em
  `texto` no cartão, não como número.
- **Rótulo de linha de referência** (meta, média, limite) fica na legenda, não escrito no
  desenho (Caio, 14/11/2026: *"os textos estão se confundindo com as linhas"*). Eixo com
  nomes no lugar de números (a nota de crédito) usa `marcas_y`.
- **Idioma de quem visita** (Caio, 14/11/2026: *"coloque também a página pelo idioma de quem
  entra pra visitar, pelo país, deixe alguma forma de tradução automática"*): o texto é
  escrito em português; quem chega com o navegador em outro idioma recebe a página traduzida
  pelo Google Tradutor (`web/src/traducao.ts`), e a lista "Idioma" no menu troca ou volta ao
  original. Em português nada é baixado do Google. Nome próprio ou símbolo que o tradutor
  estraga ganha `translate="no"` (o "?" do glossário, a marca). A busca entende também
  inglês, espanhol e francês: assunto novo ganha as palavras em `OUTRAS_LINGUAS` (`busca.py`).
- **Glossário em tudo o que a tela mostra** (Caio, 14/11/2026: *"coloque glossário mesmo que
  o nome esteja na tabela ou num cartão"*): sigla, índice ou termo técnico novo ganha verbete
  em `builder/src/sacibras/glossario.py`; a marcação (`web/src/glossario.ts`) pega texto,
  cartão, gráfico, legenda e as linhas e colunas das tabelas. Forma com duas maiúsculas só
  casa com a mesma caixa: "Núcleo EX0" não casa com a forma "núcleo EX0" (use só "EX0").
- PT-BR e formato brasileiro: `R$ 1,2 tri`, `4,5 %`, `out/2026`, `3º tri/2026`.
- Previsão nunca sozinha: consenso (Focus) ao lado, faixa de erro e o método em uma frase.
- **O simulador da dívida fica** (Caio, 14/11/2026: tirou e pediu de volta no mesmo dia,
  *"deixe o simulador da dívida, acho legal"*), com quatro controles: juro, crescimento,
  inflação (pedida no mesmo dia) e primário. **O da Selic também** (Caio, 14/11/2026:
  *"algum tipo de simulador, se reduzir a taxa oq acontece com as outras métricas (inflação,
  câmbio, dívida)"*), em Juros › Efeito da Selic: só com número que o Banco Central publica
  para 1 pp de Selic (`relatorios.py`), ao lado do Focus, e separado do que aconteceu de fato
  depois de cada ciclo (as tabelas dos ciclos dizem "não é o que a Selic causou"). **Nele,
  nenhum número sem a faixa de erro** (Caio, 14/11/2026: *"claramente coloque as faixas de
  erro, principalmente no simulador né onde os números estão longe de serem previsíveis
  assim"*): cada efeito com a faixa de 90 % que o BC publica, e cada nível numa régua ao lado
  do Focus com o quanto o Focus costuma errar. O gancho da proposta de Lara Resende saiu em
  15/11/2026 (artigo de uma vez só). **E o da reforma do consumo** (Caio, 14/11/2026: *"dá pra fazer
  simulador de impostos? A reforma tributária vai chegar"*), em Impostos › Reforma do consumo:
  quanto de IBS e CBS vai numa compra, só com a lei lida (`leis.py`) e as contas oficiais da
  alíquota (`relatorios.py`), com a faixa entre o teto da lei e a soma das contas mais
  recentes; não compara com o imposto de hoje, porque não há número oficial por produto. Fora
  os três simuladores e o da LDO (no Laboratório), cenário montado pela pessoa não entra sem o
  "sim" do Caio.
- **Primário que estabiliza a dívida: sempre com a hipótese no nome** (Caio, 25/11/2026:
  *"Temos que achar um jeito de conciliar esses dois, ou as pessoas ficarão confusas"*,
  sobre os 4,7 % de Riscos e os 2,2 % do governo). É a mesma conta com juro e PIB
  diferentes: o número diz de quando são ("de hoje", "governo, para 2027", "Focus") e a
  tabela-ponte (`secoes/estabiliza.py`) vai de um ao outro, nas duas telas. Número novo
  desse tipo entra na ponte.
- **Riscos** (Caio, 14/11/2026): a palavra na tela é *sustentabilidade da dívida*, não
  "calote"; os testes de estresse são cenários fixos, tirados da história, e entram (*"2)
  Entram"*); fonte não oficial fica de fora; e não há nota única de risco: o painel de
  alerta põe cada indicador na régua da própria história (`web/src/alertas.ts`, o lado ruim
  sempre à direita, ▲ e frase junto da cor) e conta quantos estão no quinto pior. **São 17
  indicadores, um por pergunta** (`alertas.NO_PAINEL`; eram 39 até 16/11/2026: saiu o que
  repetia outro); indicador novo no painel tira um. Outras
  formas de ver, na lista "Ver os alertas" (Caio, 14/11/2026): contra outros países, com os
  parecidos (emergentes, América Latina) primeiro e o mesmo número e fonte para todos
  (`alertas-paises.ts`, só onde há par em fonte oficial); o que mudou em um ano; e o
  quadro-resumo com as três. Número
  lido em relatório sem API (nota de crédito, elasticidades do BC, teste dos bancos) mora
  em `builder/src/sacibras/relatorios.py`, com a citação, a data da leitura e quando reler.
- **Comparações** (Caio, 14/11/2026): escolha de ano e de métrica em lista suspensa, não em
  botões; ranking em pontos (`web/src/pontos.ts`), não em barras; e o gráfico de duas
  métricas, um ponto por país ou estado. Grupo de países abre por país (hierarquia do FMI).
  O gráfico de duas métricas sai mesmo com um ou dois países (Caio, 16/11/2026: *"mostre os
  gráfico mesmo se tiver poucos países pra comparar"*); sem nenhum, a tela diz qual métrica
  ainda não tem dado naquele ano, até que ano a fonte vai, e oferece o ano mais novo com as
  duas.
  Barra de erro de previsão é traço vertical em tinta neutra, com as pontas marcadas e a
  parte de 50 % mais grossa quando há (`intervalos` no gráfico; Caio, 14/11/2026: *"não
  gostei da barra azul"*), não faixa sombreada nem cápsula colorida. Projeção vem com o
  "como ler" em palavras de todo dia ("8 em cada 10 futuros sorteados ficam entre as pontas").
- Cada número com data de referência.

## Verificação antes de mostrar

```bash
cd builder && uv run ruff check src tests && uv run ruff format --check src tests \
  && uv run mypy && uv run pytest -q
cd web && npm run build          # tsc + vite
```

Mexeu em gráfico, cartão, tabela ou cor? Rode o builder, abra o site e olhe a 390 e a 1280 px
com tudo aberto ("Mais números", "Mais gráficos", as tabelas guardadas): nada pode sair do
quadro nem cortar texto, e a dica do gráfico tem de ficar visível depois de um toque. As seis
cores de série (`--serie-1` a `--serie-6` em `web/src/estilo.css`) passaram num validador de
paleta para daltônicos; trocar uma pede validar de novo.

## Git

- O `.env` nunca vai ao git.
- Depois de cada commit, `git show --stat HEAD` (o OneDrive já desfez arquivo sozinho no
  finance_agent).
