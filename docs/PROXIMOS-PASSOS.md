# Próximos passos

**Leia isto no começo de cada sessão e atualize no fim** (Caio, 14/11/2026: *"deixe os próximos
passos sempre anotado num .md, assim a próxima sessão sabe o que fazer"*). O plano inteiro está
no [PLANO](PLANO.md); as fontes testadas, em [FONTES](FONTES.md); as ideias em espera, no
[PROPOSTAS](PROPOSTAS.md). Aqui fica só o que vem a seguir, em ordem, e o que espera decisão.

Última atualização: 14/11/2026 (o efeito da Selic, o simulador dela com faixas de erro e o gancho da proposta de Lara Resende, juntos no `main` com Impostos, Estados em partes e tradução).

---

## Onde paramos

- **Publicado no `main`** em 14/11/2026, a pedido do Caio (*"pode publicar no main"*). O
  trabalho da nuvem continua no branch `ccr-615b3774-yyp5n8` e vai ao `main` quando pronto.
- O site: página inicial ("Status da economia brasileira", seis números com o ponto mais novo
  buscado pelo navegador, o IPCA contra a meta, a busca) e onze assuntos — atividade,
  trabalho, inflação, juros e Copom, crédito, mercados, setor externo, contas públicas e
  dívida, estados (com a ficha de cada um), Brasil no mundo, previsões; e, desde 14/11,
  demografia e riscos; e Impostos (catorze ao todo).
- Feito na última sessão:
  - Do Econvitals ([PROPOSTAS](PROPOSTAS.md), tabela com o par brasileiro de cada métrica):
    juro e inflação implícita por prazo e a implícita de 5 a 10 anos à frente; o prefixado
    longo decomposto; medidas de inflação em 1, 3 e 12 meses; subutilização, participação,
    nível de ocupação, informalidade, desalento e a média de 3 meses do Caged; balanço de
    pagamentos em partes; financiamento imobiliário, IVG-R e os juros na renda das famílias.
  - Títulos × Focus: a comparação vai só até onde o Focus projeta (fim de 2030).
  - Contas dos estados: o leitor da dívida não lia "Demais dívidas contratuais" (TO e PR);
    corrigido, as partes fecham nas 27 UFs. RR e AC (pouca dívida com a União) e o ITCMD do DF
    foram conferidos no dado bruto: é o dado mesmo.
- **Demografia, novo assunto** (Caio, 14/11/2026: *"resultados demográficos… riscos
  demográficos, algo que envolve a produtividade, trabalho e previdência"*), entre Estados e
  Brasil no mundo. Da projeção do IBGE (revisão 2024, FTP, `fontes/ibge_projecao.py`):
  população, fecundidade, idosos por 100 de 15 a 64, esperança de vida, idade mediana,
  pirâmide etária com ano em lista e contorno de 2000 (`web/src/piramide.ts`), nascimentos ×
  óbitos, crescimento da população de 15 a 64 e a tabela de idosos por estado. Produtividade:
  PIB por ocupado (SIDRA 1620 + PNAD) e o crescimento de cada ano dividido entre mais gente
  ocupada e mais produto por ocupado. Previdência: déficit do INSS em % do PIB (RTN, linha nova
  "arrecadação líquida para o RGPS"). Gráfico com projeção de mais de 10 anos fica sem os
  botões de janela (`grafico.ts`).
- **Título da aba** sem o travessão (Caio, 14/11/2026): `sacibras · status da economia
  brasileira` (`web/index.html`). O menu lateral está no ar desde o deploy das 12h15: aparece
  a partir de 1024 px de largura; abaixo disso fica o botão "Assuntos" na faixa do topo.
- Prévia privada: https://claude.ai/artifact/YPR6sEPLQNHPSkzxektAMS — republicar depois de
  mudança visível.

## Sessão da Selic (14/11/2026, na nuvem, branch `ccr-567b9de5-xode7j`, publicada no `main`)

Pedido do Caio: *"senti também falta de uma sessão sobre o impacto da taxa selic na inflação, ou
algum tipo de simulador, se reduzir a taxa oq acontece com as outras métricas (inflação,
câmbio, dívida)"*.

- **Juros › Efeito da Selic** (parte nova, `#juros/efeito`): três números (1 pp de Selic no
  IPCA, no dólar e na dívida bruta), o simulador "E se a Selic mudar?" (`simulador_selic` no
  JSON, `web/src/simulador-selic.ts`), a tabela com as contas do BC e as duas dos ciclos.
- **De onde vêm os números** (`relatorios.py`, lidos em 14/11/2026): Relatório de Inflação de
  jun/2024, boxe "Atualização dos modelos semiestruturais de pequeno porte" (IPCA: −0,27 e
  −0,24 pp no 4º trimestre; dólar: 1,90 % por ponto, faixa de 0,77 a 3,22; as curvas por
  trimestre saíram das coordenadas do desenho vetorial); RPM de mar/2026, boxe do repasse
  cambial; e as elasticidades da dívida, que já estavam lá. **Reler** quando o BC publicar outra
  atualização dos modelos (o próximo relatório sai em dezembro; os de mar/2026 e jun/2026
  ainda remetem ao boxe de 2024).
- **Os ciclos** (`modelos/selic.py`): mudanças seguidas no mesmo sentido, um ano parado separa;
  de 2003 em diante. A tabela diz o que aconteceu com IPCA, dólar e dívida, e que isso não é o
  efeito da Selic.
- **Faixas de erro em tudo** (Caio: *"claramente coloque as faixas de erro, principalmente no
  simulador"*): sob cada efeito, a faixa de 90 % do BC; em cada quadro, a régua com o Focus e o
  erro típico dele (`acerto_focus.medir`, agora também em % para o dólar) e o número simulado
  com a faixa; barras de erro no gráfico. A faixa do IPCA é a do Relatório de Inflação de
  dez/2021 (p. 77), a última publicada: a versão de 2024 saiu sem faixa (**conferir a cada
  relatório se o BC publica a nova**).
- **Gancho** (Caio: *"aquela proposta do André Lara Resende para baixar o juros"*): botão no
  simulador que põe a Selic no tamanho da proposta ("Eu Acuso", 25/09/2026, Selic perto de
  7,5 % em cerca de 12 meses; lido no Substack do autor, trechos em `relatorios.py`). O
  tamanho sai do Focus do dia (metade da distância entre 7,5 % e a Selic que o Focus espera
  para o fim do ano seguinte). **Rever** se o autor mudar a proposta ou quando ela envelhecer.
- Busca ("se a selic cair", "corte de juros", "simulador", "lara resende") e quatro verbetes
  no glossário (93).
- Conferido a 1280 e a 390 px, com tudo aberto e o toque no gráfico. A prévia privada foi
  republicada com tudo (os treze assuntos e o glossário, que ela ainda não tinha). **Publicado
  no `main`** em 14/11/2026, a pedido do Caio (*"pode juntar"*), junto com o que já estava lá
  (Impostos, Estados em partes, tradução).

## Sessão dos Impostos (14/11/2026, na nuvem, branch `ccr-d0c7a2f5-n0uby2`, publicada no `main`)

- **Pedido do Caio**: *"estou sentindo falta de alguma sessão sobre impostos, ou impacto de
  impostos no crescimento"*. Para o crescimento, ele escolheu as quatro peças oferecidas.
- **Assunto novo "Impostos"** (`secoes/impostos.py`), em Contas públicas, entre Contas públicas
  e Estados, com cinco partes:
  - **Arrecadação federal**: o CSV da Receita por UF e tributo (`fontes/receita_arrecadacao.py`),
    soma de 12 meses a preços de hoje (IPCA), crescimento real, % do PIB e a tabela por tributo.
    Desde 2013 (antes, o arquivo não traz a previdência por estado; 2001–2002 têm números
    ambíguos).
  - **Carga tributária** e **sobre o que se cobra**: OCDE, Global Revenue Statistics
    (`fontes/ocde_receita.py`): Brasil × média da OCDE × América Latina, quem arrecada, a
    composição por base e a tabela com 12 países.
  - **Impostos e crescimento**: gráfico de pontos novo (`Grafico.dispersao`,
    `web/src/dispersao.ts`, o mesmo desenho de Brasil no mundo) com a carga média e o
    crescimento médio do PIB por habitante (FMI) em dez anos, a correlação dita em palavras e
    o aviso de que andar junto não é causa; e a tabela dos estudos oficiais lidos
    (`relatorios.EFEITOS_DE_IMPOSTO`: FMI WP 16/79, Ipea TD 1377, Ipea Carta 60, Prêmio
    Tesouro 2024), cada um com o trecho original e a página.
  - **Gasto tributário**: o DGT da Receita, bases efetivas (`fontes/receita_gastos.py`), 2014 a
    2023 juntando quatro edições, e os maiores itens do último ano.
- Glossário (+9 termos), sinônimos da busca, teste de fumaça das três fontes novas.
- **Esperando decisão do Caio**: a lista "Impostos: o que mais cabe" no
  [PROPOSTAS](PROPOSTAS.md) (dez sugestões).
## 11ª sessão (14/11/2026, na nuvem, branch `claude/ui-refinements-glossary-v417zq`)

Pedidos do Caio: *"diminua a tela ao abrir por estado"*, *"adicione RCL e outros termos na aba
de Estados para o glossário"*, *"não encontrei o número do grau de investimento do Brasil"*,
*"os textos estão se confundindo com as linhas"* e *"se for apresentar o resultado, escreva só
o essencial"*.

- **Estados em partes** (`organizacao.PARTES_ESTADOS`, `web/src/estados.ts`): a visão geral
  só com o mapa (menor); "Mapa e ranking"; "Um estado por dentro" (`#estados/uf-SP`), com os
  números e as contas **um bloco de cada vez, em abas** (Receita, Gasto por tipo, Gasto por
  área, Dívida, Descontos da dívida); "Duas métricas"; "Tabela completa". Tocar num estado do
  ranking dá o atalho "Ver as contas de …". Descrições dos blocos encurtadas.
- **Glossário em Estados**: a ficha (rótulos, detalhes, nomes das linhas da tabela) agora é
  lida pelo glossário, e o texto da métrica trocada na lista é marcado de novo
  (`remarcar`). 24 verbetes novos: despesa com pessoal, limites máximo, prudencial e de
  alerta, dívida consolidada (e a líquida), dívida com a União, haveres, caixa, custeio,
  inversões, amortização, encargos especiais, Fundeb, transferências da União, RPPS, acima da
  linha, RGF, RREO, DCA, SICONFI, quadrimestre, hiato de crédito e serviço da dívida (113 ao
  todo).
- **Nota de crédito em letras**: o cartão mostra "BB" (campo `texto` do `Cartao`), com "2
  degraus abaixo do grau de investimento; Moody's Ba1"; o gráfico tem o eixo com as notas
  (`marcas_y`: BBB/Baa2 … B/B2) e a dica diz a nota. A busca acha por "rating", "grau de
  investimento", "S&P"…
- **Linhas de referência** (meta, média, limite, grau de investimento) com o nome na legenda,
  não mais escrito no desenho por cima das séries (e cortado no celular).
- **Cartões enxutos**: `detalhe` até 60 letras (o builder avisa "detalhe longo"); 25 textos
  encurtados (Riscos, Demografia, Inflação, Juros, meta de primário, ficha dos estados). Regra
  no `CLAUDE.md`.
- **Crédito privado contra outros países** (item 0 de antes, parte): serviço da dívida do setor
  privado (BIS `WS_DSR`; o BIS não separa as famílias para o Brasil, dito na linha) e hiato de
  crédito (BIS `WS_CREDIT_GAP`) entram em Brasil no mundo (tema "Crédito") e na vista "outros
  países" do painel de alerta, em "Fora do painel".
- **Inflação no simulador da dívida** (Caio: *"na simulação dá pra colocar também a
  inflação?"*): quarto controle, ±3 pp sobre o IPCA do Focus. Na conta o juro não reage à
  inflação (dito no controle e na nota: na vida real parte dos títulos é corrigida pelo IPCA
  e o BC sobe a Selic, então é para mexer no juro junto). +2 pp de inflação levam a dívida de
  2034 de 104,8 % para 89,8 % do PIB, com o juro parado.
- **Tradução automática** (Caio: *"a página pelo idioma de quem entra pra visitar, pelo
  país"*; `web/src/traducao.ts`): o navegador em outro idioma abre a página traduzida pelo
  Google Tradutor (o cookie `googtrans`, sem a faixa do Google); a variante do país vale
  quando muda a escrita (zh-TW/zh-HK tradicional), e português de qualquer país fica no
  original. Lista "Idioma" no menu (no celular, no alto do menu aberto) com 13 idiomas mais o
  do navegador; a escolha fica no navegador. Em português, nada é baixado do Google.
  Conferido com navegador en-US, es-AR e pt-BR. Limites: o país pelo IP não é usado (pediria
  serviço de terceiros); o tradutor às vezes estraga nomes próprios ("Copom" virou "Cocom" no
  espanhol) e traduz "Desocupação" por "Eviction" no inglês.
- **Busca em outras línguas** (Caio: *"arrume a busca"*): `OUTRAS_LINGUAS` em `busca.py` põe
  no índice as palavras em inglês, espanhol e francês de cada assunto (unemployment,
  desempleo, chômage; credit rating; GDP…); a que vem do título (`lt`) pesa mais que a do
  resumo, para "unemployment" trazer a Desocupação antes de Estados. Em outra língua (japonês,
  chinês…), o aviso diz que a busca entende português, inglês, espanhol e francês. Coisa nova
  que um estrangeiro procuraria ganha a palavra em `OUTRAS_LINGUAS`.
- **Publicado no `main`** em 14/11/2026, a pedido do Caio (*"pode juntar no main"*).
- Conferido a 390 e a 1280 px (Estados nas cinco telas, Riscos › Mercado e contas externas, a
  vista por países, o simulador, a página traduzida). A prévia privada não foi republicada
  nesta sessão.

## Décima sessão (14/11/2026, na nuvem, branch `ccr-3122c6b7-8l15l1`)

- **Glossário** (`glossario.py` → `glossario.json`, `web/src/glossario.ts`): 89 termos; a
  palavra sublinhada ou o "?" ao lado do nome abre a definição num balão, com "Ver no painel".
  Termo novo que alguém não saberia: um verbete a mais.
- **Painel de alerta** classificado (grupos que abrem no toque, atalho dos acesos) e
  explicado: cada linha abre o que é, por que é alerta e no que pode dar (`alertas.py`; o teste
  obriga indicador novo a ter texto). A busca leva direto ao indicador (`#riscos/a-<id>`).
- **Brasil no mundo**: a lista "Países" (principais, médias dos grupos, todos de um grupo do
  FMI) vale para ranking, duas métricas e tabela; métricas por tema; régua do 5º ao 95º
  percentil quando a lista é um grupo inteiro.
- **Barras de erro** em tinta neutra com as pontas marcadas (e a parte de 50 % grossa no leque),
  "como ler" no leque e nas previsões; `.nota` aceita parágrafo (`\n\n`).
- **Primário BC × FMI**: tabela em Contas públicas › Primário e juros e aviso na métrica do
  Brasil no mundo.
- **Investimento e poupança** (SIDRA 6727 e 6726), parte nova em Atividade.
- **Painel de alerta em quatro vistas** (lista "Ver os alertas"): a própria história; outros
  países (`alertas-paises.ts`, lê `mundo.json` e `mundo-paises.json`; emergentes por padrão);
  o que mudou em um ano (`ha_um_ano` e `pior_que_ha_um_ano` no `Alerta`); e o quadro-resumo.
- Conferido a 1280 e a 390 px. **Publicado no `main`** em 14/11/2026, a pedido do Caio
  (*"pode juntar no main quando acabar"*).

## Resolvido no PC em 14/11/2026

- **Pages ligado** pela API (Source: GitHub Actions): o site está em
  https://jabiraka.github.io/sacibras/, com as onze seções saindo `ok` no primeiro deploy.
- **B3 fica desligada** (`SB_B3`), decisão do Caio.
- **Séries fora do CKAN do BC** (27863, 27864): a saída da regra no `CLAUDE.md` foi aprovada.
- **Normas lidas** no Planalto e no Senado (trechos em `leis.py`): os limites de pessoal (LRF,
  arts. 19, 20, 22 e 59) e de dívida (Resolução do Senado 40/2001) dos estados agora vêm da lei,
  com o artigo na descrição, e o estado cujo RGF traz outro limite é nomeado; a meta de primário
  de 2026 (LDO, art. 2º) está registrada e na tela (abaixo); os mínimos de saúde (LC 141,
  art. 6º) e de educação (Constituição, art. 212) estão anotados.
- **Calendário do IBGE**: do Brasil responde com CORS `*`. Cada assunto mostra a próxima
  divulgação das pesquisas dele (`web/src/calendario.ts`), buscada pelo navegador.

## Navegação nova e meta fiscal (sétima sessão, 14/11/2026)

- **Categorias e partes** (`builder/src/sacibras/organizacao.py`): cinco categorias (Atividade e
  emprego; Preços, juros e crédito; Mercados e exterior; Contas públicas; O que vem pela
  frente) e cada assunto em 3 a 6 partes. O assunto abre numa visão geral (quatro números, as
  partes, o gráfico principal) e cada parte numa tela só dela (`#inflacao/nucleos`), com
  trilha em cima e as outras partes embaixo. Peça nova sem lugar em `PARTES` cai em "Outros" e
  o builder avisa.
- **Menu lateral** com a busca fixa (resultados logo abaixo do campo, sem janela); no celular,
  faixa do topo com a busca e o botão "Assuntos". A busca indexa as partes e diz onde cada
  resultado mora. Conferido a 1280 e 390 px (prints da sessão).
- **Meta de primário na tela** (opção "b" do Caio): parte "Meta fiscal" em Contas públicas.
  Cartão e gráfico com o primário do Governo Central em 12 meses (SGS 4639, no catálogo)
  contra a meta da LDO 2026 em reais, e a tabela "A meta de 2026 pela conta do governo"
  (relatórios do 3º e 4º bimestres: −R$ 80,9 bi projetados, R$ 67,3 bi de desconto,
  −R$ 13,6 bi para a meta, abaixo do piso). **Ler de novo** o relatório do 5º bimestre (sai
  até 22/11) e acrescentar em `leis.AVALIACOES_2026`.
- Commitado e publicado no `main` em 14/11/2026, junto com Demografia e Riscos (as três
  sessões mexeram nos mesmos arquivos; juntas, passam no teste e no build).

## Riscos, novo assunto (14/11/2026)

- **No ar**: "Riscos" na categoria "O que vem pela frente", em seis partes — painel de
  alerta (32 indicadores na régua da própria história), a dívida se sustenta?, testes de
  estresse, mercado e contas externas (com a nota de crédito), bancos e crédito, energia e
  população. O que entrou e o que falta, bloco a bloco, está no [PROPOSTAS](PROPOSTAS.md).
- **Lido à mão, com prazo para reler** (`builder/src/sacibras/relatorios.py`): as
  elasticidades da dívida (nota fiscal do BC, **todo mês**; a próxima sai no fim de
  novembro), o teste de estresse dos bancos (REF, maio e outubro) e a nota de crédito (a
  cada ato de agência; o sistema do Tesouro estava fora do ar em 14/11 e o histórico veio
  de cópias arquivadas das páginas dele: **reler em `sisweb.tesouro.gov.br/apex/f?p=2810:2`
  quando voltar**, para confirmar que nada mudou depois de 30/05/2025).
- Conferido a 1280 e a 390 px, com o painel e as tabelas abertos.
- **Para rodar o builder neste PC sem Docker** (o OneDrive recusa o `.venv` e o caminho com
  "Área" quebra o `.pth`): `UV_PROJECT_ENVIRONMENT="$LOCALAPPDATA/sacibras-venv"
  UV_LINK_MODE=copy PYTHONUTF8=1 PYTHONPATH=src`, `uv sync --frozen --no-install-project` uma
  vez e depois `uv run --frozen --no-sync …`.

## Próximos passos, em ordem (dá para fazer na nuvem)

0. **O que falta do efeito da Selic** ([PROPOSTAS](PROPOSTAS.md)): atividade e crédito (boxe
   do RPM de mar/2026, a ler inteiro), o atalho para a parte em Inflação e em Contas públicas,
   e o gráfico dos ciclos alinhados pelo primeiro corte.
0. **Mais pares internacionais no painel de alerta**: reservas (FMI), volatilidade do câmbio
   dos emergentes (BIS, câmbio diário). Cada par novo entra em `PARES` com a frase do
   conceito. (Serviço da dívida privada e hiato de crédito: feitos, em "Fora do painel".)
0. **O que falta dos Riscos**: juro real do Brasil menos o dos EUA (fonte americana
   testada; falta a história do juro real brasileiro de 10 anos), o hiato de crédito do BIS
   como linha do painel na régua da própria história (o número já está na comparação com
   outros países), a taxa implícita oficial da DBGG (planilha mensal da nota fiscal do BC), o bloco
   jurídico (Anexo de Riscos Fiscais da LDO, precatórios, governança do Banco Mundial) e os
   estados perto dos limites com a nota CAPAG.

1. **Mínimos de saúde e educação dos estados**: as normas já estão lidas (`leis.py`), mas os
   RREO Anexos 08 e 12 **não vêm na API do SICONFI** (conferido em 14/11/2026). Testar o SIOPS
   (saúde) e o SIOPE (educação), de onde os dois saem. Na ficha do estado, contra 12 % e 25 %.
2. **O que faltou do Econvitals:** serviços subjacentes (achar o código SGS), Caged por setor
   (achar fonte com nome legível), consumo das famílias + investimento (a "demanda privada").
   (PIB por pessoa ocupada e taxas de investimento e poupança: feitos.) Lista no
   [PROPOSTAS](PROPOSTAS.md).
2a. **O que falta da Demografia** (lista no [PROPOSTAS](PROPOSTAS.md)): contribuintes da
   previdência na PNAD (achar a tabela do SIDRA), a projeção da ONU ao lado da do IBGE (com a
   faixa de erro que o IBGE não publica), produtividade por hora trabalhada, a projeção
   atuarial do RGPS (anexo da LDO, lido à mão) e o Brasil contra outros países.
3. **Estados no tempo.** A ficha é uma foto. Faltam a série de cada estado contra o Brasil, a
   nota CAPAG, a previdência do estado (RREO Anexo 04). Cuidado com o custo: cada período a
   mais são 54 chamadas ao SICONFI; usar só o 3º quadrimestre de cada ano.
4. **O que falta de Impostos** (lista no [PROPOSTAS](PROPOSTAS.md)): a linha do tempo da
   reforma do consumo (CBS/IBS de 2026 a 2033) depende de **ler a EC 132/2023 e a LC 214/2025
   no Planalto, do PC** (a nuvem não alcança); a carga como métrica em Brasil no mundo (a OCDE
   já está lida); arrecadação federal e ICMS na ficha do estado; o PLOA ao lado do gasto
   tributário. **Reler** o DGT quando sair a edição 2024 (prevista para 2027) e o
   multiplicador de receita da SPE, se a nota metodológica do Boletim Impulso Estrutural do
   Gasto for publicada.
5. **Previsões próprias que faltam:** IPCA e desocupação com modelo sazonal; "o que mudou desde a
   última leitura" no PIB agora; PIB agora com indústria, varejo e serviços além do IBC-Br.
   Sempre ao lado do Focus, com barra de erro e o método numa frase.
6. **Brasil no mundo:** câmbio no ano (BIS `WS_XRU`), juro de 10 anos (OCDE), inflação mensal.
7. **Acabamento:** "novo desde sua última visita", PNG dos gráficos, imagem de compartilhamento,
   domínio.

## Limites conhecidos

- O "PIB agora" é estimativa própria (reta com o IBC-Br), ao lado do Focus. Com dois meses do
  trimestre, o erro real é maior que o erro típico medido.
- O histórico de acerto do Focus compara com o dado revisado de hoje, não com o da época.
- O simulador da dívida é conta de ordem de grandeza: não separa a dívida atrelada ao câmbio.
- A participação da dívida por indexador não traz o IPCA no SGS: "índices de preços" é o que
  falta para 100 %.
- Inflação implícita só a partir de mai/2029 (não há IPCA+ sem cupom mais curto no Tesouro
  Direto). A diferença títulos × Focus junta expectativa diferente e prêmio de prazo.
- Os anualizados de 3 meses da inflação são sem ajuste sazonal (dito na tela).
- O saldo do Caged é a diferença do estoque no SGS 28763 (set/2026: 121 mil), um pouco
  diferente do saldo oficial com ajuste (115 mil).
- No resultado primário dos estados, o numerador é o acumulado do ano (jan–ago) e o
  denominador é a RCL de 12 meses.
- O build a frio leva perto de 3 minutos (SICONFI, DCA e Focus sem cache).
- A projeção da população é a do IBGE, sem faixa de erro (o IBGE não publica). O PIB por
  ocupado é por pessoa, não por hora; de 2020 a 2022 a pandemia distorce a decomposição (dito
  na tela). O déficit do INSS é só o Regime Geral (sem servidores e militares).
- Impostos: a carga é a da OCDE (33,7 % do PIB em 2024), não a da Receita (outro método); a
  arrecadação soma as UFs do CSV da Receita, que fica perto do total oficial mas não igual; o
  gasto tributário é só o federal e sai com dois anos de atraso. O gráfico carga ×
  crescimento não mede efeito de imposto: o efeito está só nos estudos lidos, e nenhum é do
  BC, do Tesouro ou da SPE (não publicaram multiplicador de receita).
- No celular, as tabelas de quatro colunas rolam de lado com a primeira coluna parada (é a
  regra do CSS para toda tabela do site).
- O calendário mostra só o dia da divulgação: a API traz a hora sem dizer o fuso. Se a API do
  IBGE não responder em 6 s, a linha não aparece.

- No simulador da Selic, a faixa do IPCA é de uma versão anterior do modelo (dez/2021), e a
  da dívida soma pontas (larga de propósito). O erro do Focus compara com o dado revisado de
  hoje: na dívida são só sete anos, e parte do erro é o PIB revisado depois. O gancho de Lara
  Resende mede só o primeiro ano, com a queda posta como média do ano.
- O simulador da Selic é linear (o dobro da mudança, o dobro do efeito) e vale para um ano:
  o risco do país e o juro de fora ficam parados, e um corte lido como descuido com a inflação
  mexeria mais no dólar e nos preços do que a conta mostra. A soma das três parcelas da dívida
  (juros, dólar, inflação) é nossa; cada parcela é do BC. O modelo é o de jun/2024.
- As tabelas dos ciclos da Selic mostram o que veio depois, não o que a Selic causou; o último
  ciclo pode não ter acabado.

- Riscos: o painel de alerta compara cada indicador com a própria história, não com um nível
  perigoso (o capital dos bancos está "aceso" e bem acima do mínimo). O leque e os testes de
  estresse usam a conta do simulador (ordem de grandeza, sem separar a dívida cambial); o
  "juro que a dívida paga" são os juros do setor público sobre a dívida bruta, não a taxa
  implícita oficial. As janelas dos episódios de crise são escolha nossa, dita na tabela.
  A dívida externa de curto prazo (SGS 21519) não diz se o prazo é o original ou o residual.

## Para conferir antes de mostrar

```bash
cd builder && uv run ruff check src tests && uv run ruff format --check src tests \
  && uv run mypy && uv run pytest -q && uv run sacibras build
cd web && npm run build
```

Depois, olhar a 390 e a 1280 px com tudo aberto (regra no `CLAUDE.md`).
