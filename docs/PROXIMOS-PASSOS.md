# Próximos passos

**Leia no começo da sessão e atualize no fim** (Caio, 14/11/2026). Aqui fica só o que está em
aberto: o que foi feito sai (a história está no git), as ideias em espera ficam no
[PROPOSTAS](PROPOSTAS.md) e os limites conhecidos no [PLANO](PLANO.md#12-limites-conhecidos).

Última atualização: 16/11/2026. A sessão da nuvem de 15/11 fez tudo o que dava para fazer de
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

## O que vem agora (fase 2)

Na ordem do plano; o que está aqui ainda não foi feito:

1. **Laboratório, o que ficou da leva 1**: o juro neutro e o hiato do Banco Central (lidos
   no Relatório de Política Monetária, com prazo em `leituras.py`) ao lado dos nossos; o
   estudo de evento com uma medida melhor de surpresa (sem a B3, só a curva do Tesouro do
   dia anterior); a decomposição do PIB por habitante com a população em idade de trabalhar
   (ONU), separando demografia de participação.
2. **Laboratório, leva 2** (do plano): controle sintético de episódios, quem ficou com o
   crescimento por faixa de renda, o viés das previsões do orçamento, o tom das atas.
3. **O gasto, o que falta**: a série do gasto por função no tempo (o COFOG do Brasil desde
   2010) e a despesa por função só da União (o Tesouro publica o COFOG do Governo Central).
   América Latina tem só cinco países com COFOG do governo geral no FMI; Chile, México e
   Colômbia publicam só o governo central.
4. **A árvore do diagnóstico de crescimento** e o crédito direcionado nas perguntas.
5. **Contador de acesso nosso**: espera o projeto Supabase do sacibras.
6. **Estados e Brasil no mundo** com 6 métricas na lista; Estados › Duas métricas com poucos
   estados (como já é em Brasil no mundo).
7. **O glossário ainda aponta endereços antigos** (`#pobreza/fome`, `#credito/imoveis`).

## Releituras com prazo

A lista inteira sai de `sacibras leituras --todas` (`leituras.py`); a issue `releitura` avisa.
As próximas:

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
- **Domínio**: a imagem de compartilhamento (`og:image`) usa `ENDERECO` em `web/vite.config.ts`
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
