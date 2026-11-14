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
- **Registro explícito de séries com unidade** em `builder/src/sacibras/catalogo.py`. Série nova
  só entra depois de conferida no catálogo da fonte (para o SGS:
  `dadosabertos.bcb.gov.br/api/3/action/package_search?fq=codigo_sgs:N`), com a data no comentário.
  Série que o BC não lista no CKAN (EX3, P55, industriais, alimentação no domicílio) se confere
  no serviço de metadados do próprio SGS e, quando der, contra outra fonte oficial (o IBGE),
  dito no comentário.
- **O site da B3 fica desligado** (`SB_B3`), pendente de decisão do Caio: a B3 veda coleta
  automatizada no texto do site (lido em 14/11/2026, [docs/FONTES.md](docs/FONTES.md)). Não
  ligar no workflow nem no compose sem o "sim" dele.
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
  pra abrir"*). Na entrada: seis números (`RESUMO` em `construir.py`) e um cartão por assunto,
  com a manchete dele. Dentro do assunto: quatro números e o primeiro gráfico; o resto fica
  atrás de "Mais números", "Mais gráficos" e das tabelas guardadas. Coisa nova entra guardada,
  não na entrada. Sem "Anterior"/"Próximo" entre assuntos: só o "Voltar" (Caio, 14/11/2026).
- **O desenho segue o do finjabs** (Caio, 14/11/2026): cartões de vidro, cabeçalho em pílula,
  Geist, título grande com a segunda metade apagada. O que é só daqui: as luzes de fundo
  verde, amarela e azul e o losango da marca. **Só o tema claro, sem botão de tema** (Caio,
  14/11/2026: *"deixe sempre o tema claro sem opção de tema escuro"*).
- **Número com meta se mostra contra a meta** (Caio, 14/11/2026, o IPCA na entrada): o
  cartão leva `meta` (centro e intervalo, da norma lida) e a tela diz em palavras e na régua
  se está dentro, acima do teto ou abaixo do piso.
- **Busca** (Caio, 14/11/2026: *"barra de pesquisa pras pessoas pesquisarem por nome ou
  sinônimos"*): a lupa no cabeçalho e a caixa na entrada abrem a mesma busca; o índice
  (`busca.json`) sai do builder (`busca.py`) com tudo o que a tela mostra, e o resultado leva
  direto ao número, gráfico ou tabela, abrindo o que estiver guardado. Coisa nova que alguém
  procuraria por outra palavra ganha o sinônimo em `SINONIMOS`.
- PT-BR e formato brasileiro: `R$ 1,2 tri`, `4,5 %`, `out/2026`, `3º tri/2026`.
- Previsão nunca sozinha: consenso (Focus) ao lado, faixa de erro e o método em uma frase.
- **O simulador da dívida fica** (Caio, 14/11/2026: tirou e pediu de volta no mesmo dia,
  *"deixe o simulador da dívida, acho legal"*). Fora ele, cenário montado pela pessoa não
  entra sem o "sim" do Caio.
- **Comparações** (Caio, 14/11/2026): escolha de ano e de métrica em lista suspensa, não em
  botões; ranking em pontos (`web/src/pontos.ts`), não em barras; e o gráfico de duas
  métricas, um ponto por país ou estado. Grupo de países abre por país (hierarquia do FMI).
  Barra de erro de previsão é cápsula vertical (`intervalos` no gráfico), não faixa sombreada.
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
