# Plano da fase 2: menos coisa na tela, mais análise nossa

Caio, 16/11/2026: *"pode afrouxar minhas regras, e me dê um plano estruturado do que vc
colocaria e também oq simplificaria no site hoje, lembrando que os humanos não conseguem
absorver muitas informações"*. Aprovado em 16/11/2026 (*"pode seguir, o gancho vai ser problemas e perguntas que as pessoas
buscam algum tipo de resposta"*). **Feito no mesmo dia**: o "Saiu por último", as oito
perguntas, a entrada e o menu por perguntas e o painel de alerta com 17 indicadores. O que
falta está no [PROXIMOS-PASSOS](PROXIMOS-PASSOS.md), "O que vem agora". Também feitos em
16/11: o corte dos Dados, os nove assuntos e a frase do gráfico. Em 17/11, a leva 1 do
Laboratório (sem o juro neutro do BC) e o gasto obrigatório contra o discricionário. Do
plano, falta o resto do Laboratório, o contador de acesso e os comparadores com menos métricas.

## O ponto de partida

Hoje o site tem 13 assuntos, 64 partes, 156 cartões, 142 gráficos, 58 tabelas, 39 alertas e
80 métricas de comparação (estados e países). É um banco de dados bem organizado. Quem chega
com uma pergunta ("o juro vai cair?", "a dívida preocupa?") precisa montar a resposta sozinho.

## A ideia: três andares, e cada um com um trabalho

| Andar | Para quem | O que tem | Regra |
|---|---|---|---|
| **Hoje e Perguntas** | quem chega | a entrada e umas 8 páginas de pergunta | uma frase de resposta, no máximo 5 gráficos, cada gráfico com a conclusão no título |
| **Dados** | quem quer o número | os assuntos de hoje, enxutos | só fonte oficial e conta que fecha com ela, como hoje |
| **Laboratório** | quem quer ir fundo | modelos e estimativas nossas | método em uma frase, faixa de erro sempre, placar de acerto na tela |

O Laboratório é o que permite afrouxar as regras sem contaminar o resto: o número oficial e a
estimativa nossa nunca aparecem na mesma peça sem a marca de qual é qual.

## Regras que mudam (e as que ficam)

**Mudam, só dentro do Laboratório:**

1. *"Sem próprias previsões por enquanto"* → previsão nossa entra, com o placar ao lado: o
   quanto erramos e o quanto o Focus errou nas mesmas datas, desde o primeiro dia.
2. *"Só o que sai com regularidade e com método"* → estudo avulso continua fora como fonte
   de número. Mas parâmetro da literatura (uma elasticidade) pode alimentar uma conta nossa,
   como faixa entre o menor e o maior de pelo menos três estudos citados, nunca um ponto só.
3. *"Simulador novo não entra"* → entra se o resultado sai como faixa e a pessoa vê de onde
   vem cada ponta.
4. Avaliação de política que já aconteceu (o Brasil contra um Brasil sem ela) entra, com o
   teste de placebo na tela.

**Ficam como estão:** fonte oficial e citada nos Dados; a B3 desligada; as licenças; valor
nunca em branco; a palavra neutra (sem "bom" e "ruim", sem dizer qual teoria está certa);
tema claro; formato brasileiro; bases separadas do finance_agent.

**Uma regra nova, a do orçamento de atenção:**

- Por tela, à vista: uma frase, até 4 números e um gráfico. O resto abre no clique.
- Por assunto: até 5 partes (eram até 4 no plano; Riscos e Pobreza pediram cinco); por
  parte, até 4 cartões e 3 gráficos.
- Nos Dados, **entra um, sai um**: peça nova diz qual peça velha sai.
- Todo gráfico tem no título o que ele mostra hoje, escrito pelo builder a partir do dado
  ("Inflação acima do teto da meta há 5 meses"), e não só o nome da série.

## O que simplificar no site de hoje

1. **A entrada**: ficam os quatro números e o "Saiu por último". Saem os quatro gráficos e a
   lista dos 13 assuntos com as partes; no lugar, as perguntas (oito linhas). Os assuntos
   continuam no menu, sob "Dados".
2. **De 13 assuntos para 9**, mais os dois comparadores:
   - Trabalho + Pobreza e desigualdade → **Trabalho e renda**;
   - Crédito entra em **Juros e crédito**;
   - Mercados + Setor externo → **Exterior e mercados**;
   - Demografia + Produtividade (hoje em Atividade) + educação → **Longo prazo**;
   - Previsões sai dos Dados e vira parte do Laboratório;
   - ficam Atividade, Inflação, Contas públicas, Impostos e Riscos; Estados e Brasil no
     mundo ficam como "Comparar".
3. **Riscos**: o painel de 39 alertas para 17 (a lista está no
   [PROPOSTAS](PROPOSTAS.md), "O que incluir e tirar") e de 6 partes para 3.
4. **Os mais carregados primeiro**: Pobreza (26 cartões, 16 gráficos), Riscos (24 e 18),
   Impostos (18 tabelas) e Juros (15 e 11). Meta do site: de 156 cartões para uns 70 e de
   142 gráficos para uns 80. O que sai da tela continua na tabela completa e na busca.
5. **Medir antes do segundo corte**: contador de acesso por parte e por termo de busca, sem
   cookie. O primeiro corte sai pela regra do orçamento; o segundo, um mês depois, pelo uso.
6. **Comparadores**: Estados abre com 6 métricas na lista e "mais métricas" para as outras
   22; Brasil no mundo, o mesmo.

## As páginas de pergunta

Cada uma: a resposta em uma frase com o dado de hoje, de três a cinco explicações que os
economistas dão (uma frase e um gráfico cada, sem dizer qual está certa) e o elo para o
Laboratório quando houver estimativa nossa.

1. Por que o juro é tão alto?
2. A dívida pública se sustenta?
3. Por que o Brasil cresce pouco? (com a árvore do diagnóstico de crescimento de Hausmann,
   Rodrik e Velasco: poupança, custo do capital, retorno, apropriação, um dado em cada nó)
4. A inflação está sob controle?
5. Para onde vai o imposto, e quem paga?
6. O emprego está bom mesmo?
7. Quem ficou com o crescimento?
8. O que o mercado espera do Brasil?

## O Laboratório, em quatro levas

Da mais segura para a mais difícil. Cada peça só vai ao ar com método, faixa e teste.

**Leva 1, medição com dado que já lemos**
- Juro neutro por vários métodos (o do BC, regra de Taylor invertida, o implícito na curva
  longa, filtro sobre o juro real), com o intervalo entre eles à vista; o mesmo para o
  hiato do produto. Regra de Taylor: onde a Selic estaria por cada versão.
- Estudo de evento: a surpresa de cada Copom (já medida no "Saiu por último") contra o
  movimento da curva e do câmbio no dia; depois, os anúncios fiscais, com a lista de datas
  lida à mão e com prazo.
- Reação fiscal: quando a dívida sobe, o primário responde? (o teste de Bohn, 1998–hoje).
- De onde veio o PIB por habitante (produtividade, ocupação, demografia) e a convergência
  contra os EUA desde 1950.

**Leva 2, avaliar o que já aconteceu**
- Controle sintético: a recessão de 2015–16, o teto de gastos, a reforma trabalhista e a
  desoneração da folha, cada um com placebo.
- Quem ficou com o crescimento, por faixa de renda (PNAD com o IRPF).
- O viés do governo: os parâmetros do orçamento de cada ano contra o que aconteceu.
- O tom das atas do Copom desde 1999.

**Leva 3, previsão com placar**
- PIB e IPCA por modelo de fatores com os indicadores mensais, ao lado do Focus, com o
  erro dos dois acumulado na tela.
- Previdência por coortes (população do IBGE e as regras da lei), com a idade mínima e a
  regra do reajuste como controles.

**Leva 4, microdado, a mais incerta**
- Imposto com comportamento: quem paga cada imposto por faixa de renda (POF, PNAD, IRPF) e
  a arrecadação de uma mudança de alíquota como faixa, pelas elasticidades da literatura.
- Custo de vida entre estados (o que R$ 5 mil compram em cada um) e complexidade da pauta
  de exportação por estado.

Não conferi ainda a fonte de cada peça. As levas 1 e 2 usam quase só o que o builder já lê;
a 4 depende de microdado pesado, que teria de ser processado fora do build diário e entrar
como resultado datado, com o script no repositório.

## O que continua de fora

Efeito de política futura sobre PIB e emprego ("subir o imposto X derruba o PIB em Y"): a
faixa honesta costuma incluir o zero. Nota única de risco. Fonte privada sem licença lida.

## Ordem proposta

1. Juntar o "Saiu por último" e ligar o contador de acesso.
2. Simplificar (itens 1 a 4 e 6 acima) e criar os três andares no menu.
3. As oito perguntas, com os gráficos que já existem.
4. Leva 1 do Laboratório; depois as outras, uma por vez, com o Caio olhando cada peça.
