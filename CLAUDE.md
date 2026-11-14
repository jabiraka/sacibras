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
- **O site da B3 fica desligado** (`SB_B3`; Caio, 14/11/2026: *"deixar desligado"*): a B3 veda
  coleta automatizada no texto do site (lido em 14/11/2026, [docs/FONTES.md](docs/FONTES.md)).
  Não ligar no workflow nem no compose; o que depende dela fica fora.
- **Norma se lê na fonte oficial, do PC** (o Planalto e o `servicodados` do IBGE recusam quem
  está fora do Brasil, como a nuvem e o Actions). No Windows, o `curl` do Planalto precisa de
  `--ssl-no-revoke`. Resolução do Senado: `legis.senado.leg.br/norma/<id>` (o id sai de
  `legis.senado.leg.br/dadosabertos/legislacao/lista?tipo=RSF&numero=N&ano=A`). O trecho lido
  vai como comentário em `leis.py`, com a data.
- **Curvas do Tesouro pelo método do Jabs** (Caio, 14/11/2026: *"o Jabs tem uma curva de
  inflação"*): taxa média entre compra e venda, curva zero com os papéis com cupom por
  *bootstrap*, fator de desconto log-linear, nada extrapolado (`builder/src/sacibras/curvas.py`,
  copiado e adaptado do `domain/curves.py` do finance_agent). Comparação com o Focus sempre no
  mesmo prazo (`media_do_caminho`), nunca taxa contra taxa de anos diferentes.
- **Fonte oficial e citada** em todo gráfico. Número de lei (meta de inflação, limites da LRF,
  reforma tributária) vem da lei lida.

## Tela

- **Página inicial enxuta, o resto abre no clique** (Caio, 14/11/2026: *"muitas métricas na
  página inicial… deixar só as informações essenciais no início e deixar o usuário ir clicando
  pra abrir"*). Na entrada: seis números (`RESUMO` em `construir.py`) e os assuntos com a
  manchete de cada um, agrupados por categoria.
- **Categorias e partes, pouca coisa por tela** (Caio, 14/11/2026: *"humanos não conseguem ler
  muitas informações em uma página [...] classifique melhor em categorias, crie
  subcategorias"*). Tudo mora em `builder/src/sacibras/organizacao.py`: `CATEGORIAS` agrupa os
  assuntos (menu e entrada) e `PARTES` divide cada assunto em 3 a 6 partes. O assunto abre
  numa visão geral (quatro números, a lista das partes e o gráfico principal); cada parte abre
  numa tela só dela (`#inflacao/nucleos`), com a trilha em cima e as outras partes embaixo.
  **Cartão, gráfico ou tabela novo ganha lugar numa parte** em `PARTES`: o que não estiver lá
  cai em "Outros" e o builder avisa ("sem parte em organizacao.py"). Estados e Brasil no mundo
  têm tela própria, sem partes.
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
- PT-BR e formato brasileiro: `R$ 1,2 tri`, `4,5 %`, `out/2026`, `3º tri/2026`.
- Previsão nunca sozinha: consenso (Focus) ao lado, faixa de erro e o método em uma frase.
- **O simulador da dívida fica** (Caio, 14/11/2026: tirou e pediu de volta no mesmo dia,
  *"deixe o simulador da dívida, acho legal"*). Fora ele, cenário montado pela pessoa não
  entra sem o "sim" do Caio.
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
