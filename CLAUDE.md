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
- **O site da B3 fica desligado** (`SB_B3`; Caio, 14/11/2026: *"deixar desligado"*): a B3 veda
  coleta automatizada no texto do site (lido em 14/11/2026, [docs/FONTES.md](docs/FONTES.md)).
  Não ligar no workflow nem no compose; o que depende dela fica fora.
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
- **Estimativa nossa só onde não há a oficial** (Caio, 15/11/2026: *"não vamos colocar as
  nossas estimativas quando temos oficial, só se pedirem"*). Havendo número oficial (o INSS
  até 2100 do PLDO, as projeções da ONU e do IBGE), entra só ele; a conta nossa entra onde
  não há nenhum (a idade de corte, o freio da idade no PIB por habitante) ou quando o Caio
  pedir. Dividir dois números oficiais (o INSS por pessoa) não é estimativa, mas leva
  "calculado" e a conta na nota.
- **Fonte oficial e citada** em todo gráfico. Número de lei (meta de inflação, limites da LRF,
  reforma tributária) vem da lei lida.

## Tela

- **Página inicial enxuta, o resto abre no clique** (Caio, 14/11/2026: *"muitas métricas na
  página inicial… deixar só as informações essenciais no início e deixar o usuário ir clicando
  pra abrir"*). Na entrada: quatro números (`RESUMO` em `construir.py`), quatro gráficos
  (`RESUMO_GRAFICOS`: inflação contra a meta, PIB, juro real e dívida, cada um com o elo para
  o assunto; Caio, 15/11/2026: *"coloque também alguns gráficos que achar mais importante pra
  entender o Brasil. Pode eliminar alguns cartões"*) e os assuntos com a manchete de cada um,
  agrupados por categoria.
- **Categorias e partes, pouca coisa por tela** (Caio, 14/11/2026: *"humanos não conseguem ler
  muitas informações em uma página [...] classifique melhor em categorias, crie
  subcategorias"*). Tudo mora em `builder/src/sacibras/organizacao.py`: `CATEGORIAS` agrupa os
  assuntos (menu e entrada) e `PARTES` divide cada assunto em 3 a 6 partes. O assunto abre
  numa visão geral (quatro números, a lista das partes e o gráfico principal); cada parte abre
  numa tela só dela (`#inflacao/nucleos`), com a trilha em cima e as outras partes embaixo.
  **Cartão, gráfico ou tabela novo ganha lugar numa parte** em `PARTES`: o que não estiver lá
  cai em "Outros" e o builder avisa ("sem parte em organizacao.py"). Estados tem partes
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
  os três simuladores, cenário montado pela pessoa não entra sem o "sim" do Caio.
- **Riscos** (Caio, 14/11/2026): a palavra na tela é *sustentabilidade da dívida*, não
  "calote"; os testes de estresse são cenários fixos, tirados da história, e entram (*"2)
  Entram"*); fonte não oficial fica de fora; e não há nota única de risco: o painel de
  alerta põe cada indicador na régua da própria história (`web/src/alertas.ts`, o lado ruim
  sempre à direita, ▲ e frase junto da cor) e conta quantos estão no quinto pior. Outras
  formas de ver, na lista "Ver os alertas" (Caio, 14/11/2026): contra outros países, com os
  parecidos (emergentes, América Latina) primeiro e o mesmo número e fonte para todos
  (`alertas-paises.ts`, só onde há par em fonte oficial); o que mudou em um ano; e o
  quadro-resumo com as três. Número
  lido em relatório sem API (nota de crédito, elasticidades do BC, teste dos bancos) mora
  em `builder/src/sacibras/relatorios.py`, com a citação, a data da leitura e quando reler.
- **Comparações** (Caio, 14/11/2026): escolha de ano e de métrica em lista suspensa, não em
  botões; ranking em pontos (`web/src/pontos.ts`), não em barras; e o gráfico de duas
  métricas, um ponto por país ou estado. Grupo de países abre por país (hierarquia do FMI).
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
