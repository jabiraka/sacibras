# Plano do sacibras

Um painel da economia brasileira em uma página de gráficos, atualizado quando os números saem:
atividade, trabalho, inflação, juros e Copom, crédito, mercados, setor externo, contas públicas,
dívida, impostos e estados — com previsões ao lado do consenso de mercado.

Escrito em 13/11/2026. Referência: [econvitals.org](https://econvitals.org/) (EUA).

---

## 1. O que aprendemos com o econvitals

Lido do código público do site (HTML, `dashboard.js`, `data/dashboard.json`) em 13/11/2026:

- **Site estático + builder.** Um builder roda em agenda, chama as fontes, calcula tudo e grava
  JSONs (`dashboard.json`, `markets.json`, `equities.json`, `predictions-*.json`, um JSON por
  gráfico). A página só lê os JSONs. Não há banco por trás.
- **Uma página só**, com seções e âncoras: `quick_lookup` (12 cartões no topo), PIB, trabalho,
  salários, inflação, condições financeiras, Fed, outros, internacional.
- **Cada número tem procedência** (`provenance: hard | soft`) e data de referência (`period`).
- **Nowcast composto**: o PIB do trimestre corrente é uma média ponderada de fontes (GDPNow +
  modelo próprio), com faixa de erro, os pesos declarados e uma frase do que mudou desde a
  última leitura (*"GDPNow +0,5 após ISM e construção"*).
- **Trajetória implícita do juro** (dos futuros de Fed funds) ao lado da trajetória realizada.
- **"Novo desde sua última visita"**, calendário de divulgações, exportar o gráfico como PNG,
  texto alternativo com fonte em cada gráfico.
- Gráficos com Observable Plot; fonte serifada (Literata); Netlify.

O sacibras copia a **arquitetura e o espírito**, não o visual nem o texto.

---

## 2. Princípios

1. **Sem banco em produção.** O builder chama as APIs, calcula e gera JSONs pequenos que vão
   com o site. Nada de dado é commitado no git (o repositório não cresce). O que precisa de
   histórico, a própria fonte já guarda (SGS, SIDRA, Focus, SICONFI).
2. **Fonte oficial e citada** em todo gráfico: órgão, série e data da leitura. Número de lei
   (meta de inflação, limites da LRF, transição da reforma tributária) vem da lei lida.
3. **Registro explícito de séries, com unidade.** Toda série entra num catálogo com código,
   periodicidade e unidade (% a.m., % a.a., % do PIB, R$ milhões, nível). Nunca um código solto.
   Lição do finance_agent: `bcb_sgs.SeriesSpec` e o dólar que viraria 0,0516.
4. **Formato brasileiro na tela**: `R$ 1,2 tri`, `4,5 %`, `out/2026`, `3º tri/2026`.
5. **Previsão nunca sozinha**: sempre ao lado do consenso (Focus) e com faixa de erro tirada
   do histórico de acerto. Método declarado em uma frase na própria seção.
6. **O navegador chama a API direto quando dá** (CORS liberado e série leve), para mostrar o
   último ponto mesmo entre uma rodada e outra do builder; o JSON do builder é o piso, e o site
   nunca quebra se a fonte cair.
7. **Bases separadas do finance_agent.** Nada de ler ou escrever no Postgres nem no Supabase
   dele. Código útil de lá (parsers do SGS, Focus, Tesouro Direto, COTAHIST) é **copiado e
   adaptado**, não importado.

---

## 3. Arquitetura

```
                      ┌──────────────────────── GitHub Actions (cron) ───────────────────────┐
APIs oficiais ──────► │ builder (Python)                                                     │
 BCB SGS / Focus      │  fontes/   → baixa (com cache de arquivos entre rodadas)             │
 IBGE SIDRA           │  secoes/   → monta cada seção (métricas, tabelas, cartões)           │
 SICONFI / Tesouro    │  previsoes/→ nowcast, modelos, backtest                              │
 Receita / B3 / IPEA  │  saída     → web/public/data/*.json  (validado por schema)           │
                      │ vite build → dist/ → deploy no GitHub Pages (artefato, sem commit)   │
                      └──────────────────────────────────────────────────────────────────────┘
                                                   │
navegador ◄── HTML + JS + JSONs (GitHub Pages) ◄───┘
   └─► chama direto SGS / Focus / SIDRA / IPEADATA (CORS ok) para o ponto mais recente
```

**Local, por enquanto, tudo em Docker** (pedido do Caio, 13/11/2026), com projeto, rede,
porta e volume próprios — nada compartilhado com o finance_agent:

| Serviço   | Container      | Porta | Para quê |
|-----------|----------------|-------|----------|
| `db`      | `sb_postgres`  | 5434  | Cache de séries **só para desenvolvimento** (iterar sem martelar as APIs, backtests rápidos). Produção não usa. Volume `sb_pgdata`. |
| `builder` | `sb_builder`   | —     | Roda o builder e grava os JSONs em `web/public/data/`. |
| `web`     | `sb_web`       | 5173  | Vite em modo dev, lendo os JSONs gerados. |

O finance_agent usa `fa_postgres`, porta 5433 e volume `fa_pgdata`; o compose do sacibras
declara `name: sacibras` para isolar rede e volumes.

O builder lê `SB_CACHE_URL`: com ela, usa o Postgres local como cache; sem ela (no Actions),
vai direto às APIs e usa `actions/cache` para os arquivos pesados (CSV do Tesouro, SICONFI).

---

## 4. Fontes testadas (13/11/2026)

Teste feito com `Origin: https://x.github.io`, a partir de uma máquina fora do Brasil.

| Fonte | O que dá | CORS | Quem chama |
|-------|----------|------|------------|
| BCB SGS `api.bcb.gov.br/dados/serie/bcdata.sgs.N` | Selic, IPCA, câmbio, IBC-Br, dívida, NFSP, contas externas, crédito | `*` | navegador + builder |
| BCB Focus (Olinda) `ExpectativasMercadoAnuais/Mensais/Trimestrais/Selic` | consenso de IPCA, PIB, Selic **por reunião**, câmbio, fiscal | ecoa a origem | navegador + builder |
| IBGE SIDRA `apisidra.ibge.gov.br` | PIB trimestral, PNAD, PIM, PMC, PMS, IPCA aberto | `*` | navegador + builder |
| IBGE calendário `servicodados…/api/v3/calendario` | datas de divulgação | `*` | builder |
| IBGE malhas `servicodados…/api/v3/malhas/paises/BR?intrarregiao=UF` | TopoJSON das UFs (31 KB) | `*` | builder (vai junto do site) |
| IPEADATA OData | Ibovespa diário (`GM366_IBVSP366`), séries longas | `*` | navegador + builder |
| SICONFI `apidatalake.tesouro.gov.br/ords/siconfi` | RREO/RGF/DCA de estados e municípios | **não** | builder |
| Tesouro Transparente (CKAN) | RTN, dívida pública federal, Tesouro Direto | **não** | builder |
| B3 (COTAHIST, IndexCall) | ações, índices (IFIX, SMLL, setoriais) | **não** | builder |
| Receita Federal (dados abertos) | arrecadação federal por tributo | a testar | builder |
| Comex Stat (MDIC) | balança comercial detalhada | **HTTP 451** "não disponível para essa origem" | a investigar |
| brapi.dev | cotações | `*`, mas pede token | opcional |
| Yahoo Finance | cotações | **HTTP 429** | não usar |
| Portal da Transparência | despesas detalhadas | `*`, pede chave gratuita | fase posterior |

**Risco nº 1:** o 451 do Comex Stat sugere bloqueio de IP estrangeiro, e os runners do
GitHub Actions ficam nos EUA. A Fase 0 roda um teste de fumaça **de dentro do Actions** para
cada fonte. Se alguma bloquear, as saídas em ordem de preferência: (a) a mesma série por outra
fonte oficial (ex.: balança comercial pelo SGS 22707), (b) o navegador chama (o visitante está
no Brasil), (c) um proxy pequeno (Cloudflare Worker) ou runner próprio.

### Séries do SGS conferidas no catálogo do BCB (13/11/2026)

| Código | Série |
|-------:|-------|
| 24363 | IBC-Br |
| 24364 | IBC-Br, com ajuste sazonal |
| 13762 | Dívida bruta do governo geral (% PIB), metodologia a partir de 2008 |
| 4513  | Dívida líquida do setor público (% PIB), setor público consolidado |
| 5793  | NFSP (% PIB), 12 meses, resultado primário, setor público consolidado |
| 5727  | NFSP (% PIB), 12 meses, resultado nominal, setor público consolidado |
| 22707 | Balança comercial (BP), saldo mensal |
| 22701 | Transações correntes, saldo mensal |
| 23079 | Transações correntes, 12 meses, % do PIB |
| 20539 | Saldo da carteira de crédito, total |
| 1207  | PIB em R$ correntes |
| 4393  | Índice de Confiança do Consumidor |
| 4390  | Selic acumulada no mês |

As demais séries entram no catálogo **depois** de conferidas (`dadosabertos.bcb.gov.br/api/3/
action/package_search?fq=codigo_sgs:N`), e a data da conferência fica no comentário. Do
finance_agent já vêm conferidas: 432 (Selic meta), 11/12 (Selic/CDI diário), 433 (IPCA),
189 (IGP-M), 1 (dólar), 20714 e as de crédito por modalidade.

---

## 5. Seções e métricas

Uma página, nesta ordem. Cada seção é um JSON próprio (carregamento preguiçoso).

### 5.0 Resumo (12 cartões no topo)
PIB do último trimestre (% t/t dessaz. e % a/a) · IBC-Br 12 meses · desocupação (PNAD) ·
IPCA 12 meses · média dos núcleos · Selic meta · juro real ex-ante (prefixado 1 ano − Focus IPCA
12m) · inclinação da curva (prefixado 10a − 2a) · Ibovespa (nível e no ano) · dólar (no ano) ·
dívida bruta % PIB · primário 12 meses % PIB. Cada cartão com data de referência e procedência.

### 5.1 Atividade
- PIB trimestral (SIDRA 5932 / 1846 / 1620): variação, nível, **contribuições** pela ótica da
  demanda (famílias, governo, FBCF, exportações, importações) e da oferta (agro, indústria,
  serviços).
- IBC-Br (24364) mensal e trimestral.
- Indústria (PIM-PF), varejo (PMC, restrito e ampliado), serviços (PMS), confiança.
- **PIB agora** (nowcast do trimestre corrente) — ver §6.

### 5.2 Mercado de trabalho
PNAD Contínua: desocupação (com e sem ajuste), participação, nível de ocupação, informalidade,
rendimento real habitual, massa salarial real. Emprego formal (Novo Caged — fonte a definir:
PDET publica arquivos pesados; procurar série agregada).

### 5.3 Inflação
IPCA e IPCA-15 (mensal, 12 meses, meta de 3 % e banda de 1,5 pp — da resolução do CMN),
núcleos e a média deles, livres × administrados, serviços subjacentes, difusão, abertura por
grupo (contribuição em pp), IGP-M. Expectativas: Focus 12 meses e anuais; **inflação implícita**
da curva do Tesouro (prefixado × IPCA+).

### 5.4 Juros e Copom
Selic meta e efetiva (histórico com as reuniões), calendário do Copom, **trajetória implícita
da Selic** na curva prefixada × Focus por reunião × realizada (o análogo do gráfico do Fed),
curva prefixada e real (hoje, 1 mês e 1 ano atrás), juro real ex-ante.

### 5.5 Crédito e condições financeiras
Saldo de crédito / PIB, concessões, taxa média e spread (PF/PJ, livres/direcionados),
inadimplência, endividamento e comprometimento de renda das famílias. Um índice simples de
condições financeiras (juro real, crédito, câmbio, bolsa), com método declarado.

### 5.6 Mercados (renda variável)
Ibovespa, IBrX, SMLL, IFIX, IDIV e setoriais (nível, dia, semana, mês, ano); maiores altas e
baixas do Ibovespa; amplitude (quantas sobem/caem, acima da média de 200 dias); volume
negociado; dólar, real contra outras moedas emergentes; commodities (IC-Br do BCB).
Fonte: B3 (COTAHIST e índices) e IPEADATA; padrão do finance_agent para COTAHIST.

### 5.7 Setor externo
Balança comercial, transações correntes (% PIB), investimento direto no país, reservas
internacionais, termos de troca, câmbio real efetivo.

### 5.8 Contas públicas (União e setor público)
- Resultado primário do Governo Central (RTN, Tesouro) e do setor público consolidado (NFSP,
  BCB): mensal, 12 meses, % PIB; **meta fiscal do ano e banda** do arcabouço (LC 200/2023).
- Receitas e despesas primárias: Previdência (RGPS), pessoal, discricionárias,
  obrigatórias com controle de fluxo; despesa por função.
- Juros nominais (% PIB), resultado nominal.

### 5.9 Dívida pública
DBGG e DLSP (% PIB), decomposição da variação (juros, primário, crescimento, câmbio),
Dívida Pública Federal (Relatório Mensal da Dívida): estoque, composição por indexador
(prefixado, Selic, IPCA, câmbio), prazo médio, % vencendo em 12 meses, custo médio, detentores.
**Simulador de trajetória** da dívida — ver §6.

### 5.10 Impostos
Arrecadação federal mensal por tributo (real, 12 meses), carga tributária bruta (% PIB, por
esfera), ICMS por UF, transferências constitucionais (FPE/FPM). **Reforma tributária**: a linha
do tempo da transição CBS/IBS (2026 → 2033) a partir da EC 132/2023 e da LC 214/2025 lidas.

### 5.11 Estados (e capitais)
Mapa por UF com seletor de métrica, ranking e série de cada estado (SICONFI):
despesa com pessoal / RCL (RGF Anexo 1, com os limites da LRF), dívida consolidada líquida /
RCL (RGF Anexo 2, limite de 200 %), resultado primário (RREO), receita de ICMS, despesa por
função **per capita** (saúde, educação, segurança — RREO Anexo 2; população vem do próprio
SICONFI), investimento, nota CAPAG (Tesouro). Municípios: só as 27 capitais na primeira versão
(5.570 municípios ficam para depois, se valer o custo).

### 5.12 Calendário
Próximas divulgações (IBGE calendário, Copom, Focus às segundas, RTN, NFSP) e o que saiu nos
últimos 7 dias, com o número.

---

## 6. Previsões

Toda previsão aparece com o consenso ao lado, faixa de erro e método em uma frase.

| O quê | Método próprio | Comparação |
|-------|----------------|------------|
| **PIB agora** (trimestre corrente) | Equação ponte: média trimestral do IBC-Br dessaz. (meses que faltam por AR) + PIM/PMC/PMS; composto com o Focus trimestral com pesos que mudam conforme a divulgação se aproxima (como o econvitals). Frase "o que mudou desde a última leitura". | Focus trimestral |
| IPCA próximos 12 meses | SARIMA no IPCA mensal, com sazonalidade; fan chart pelos erros fora da amostra. | Focus mensal e 12m |
| Selic por reunião | **Implícita na curva prefixada** (taxas a termo entre as datas do Copom, LTN/NTN-F do Tesouro Direto). DI1 futuro da B3 entra se houver acesso estável. | Focus por reunião (`ExpectativasMercadoSelic`) |
| Desocupação | Modelo sazonal simples na PNAD. | Focus, se houver |
| Câmbio | Sem modelo próprio (passeio aleatório é difícil de bater; dizemos isso). | Focus |
| **Dívida bruta** | Dinâmica da dívida: d₊₁ = d·(1+i)/((1+g)(1+π)) − primário, com insumos do Focus. No navegador, controles para mudar juro, crescimento e primário e ver a trajetória. | Focus (DBGG e primário) e projeções do Tesouro |

**Histórico de acerto, sem banco:** o Focus guarda todas as edições, então o erro do consenso
se mede direto da API. Os modelos próprios são avaliados por backtest fora da amostra
(janela que anda) a cada rodada do builder. Limite declarado: é com dado revisado, não com o
dado da época.

---

## 7. Atualização

GitHub Actions em agenda (horário em UTC; Brasília = UTC−3):

| Quando (BRT) | Por quê |
|--------------|---------|
| 09:40 dias úteis | IBGE divulga às 9h; Focus sai segunda às 8h25; SGS atualiza de manhã. |
| 19:00 dias úteis | Depois do fechamento da B3 (mercados, curva do Tesouro). |
| manual (`workflow_dispatch`) | Para dia de Copom, PIB etc. |

O cron do Actions atrasa alguns minutos e às vezes pula; o site mostra *"atualizado em"* e o
navegador completa com a chamada direta. Uma rodada que falha numa fonte publica o resto e
mantém o último JSON bom daquela seção (lido do site no ar antes do build).

Repositório público: Actions e Pages são gratuitos.

---

## 8. Stack

- **Builder:** Python 3.12, `uv`, `httpx`, `pandas`, `statsmodels`, `pydantic` (schema dos
  JSONs), `pytest`, `ruff`, `mypy`. CLI: `sacibras build [--secao X]`, `sacibras fontes-smoke`.
- **Site:** Vite + TypeScript, sem framework; **Observable Plot** para os gráficos,
  `d3-geo` + `topojson-client` para o mapa; CSS próprio com tokens, tema claro e escuro;
  PT-BR. Exportar gráfico em PNG e link para a seção.
- **Hospedagem:** GitHub Pages pelo Actions (artefato; nada de dado no git).
- **Local:** Docker Compose (§3).

---

## 9. Estrutura do repositório

```
sacibras/
├── builder/
│   ├── pyproject.toml
│   ├── src/sacibras/
│   │   ├── catalogo.py        # registro explícito de séries: fonte, código, unidade
│   │   ├── fontes/            # bcb_sgs, bcb_focus, ibge_sidra, siconfi, tesouro, b3, receita…
│   │   ├── secoes/            # resumo, atividade, trabalho, inflacao, juros, credito, …
│   │   ├── previsoes/         # pib_agora, ipca, selic_implicita, divida, backtest
│   │   ├── schema.py          # modelos pydantic dos JSONs de saída
│   │   └── cli.py
│   └── tests/
├── web/
│   ├── index.html
│   ├── src/ (main.ts, secoes/, graficos/, formato.ts, ao_vivo.ts)
│   └── public/data/           # gerado pelo builder; fora do git
├── docker/                    # Dockerfiles do builder e do web
├── docker-compose.yml
├── .github/workflows/         # ci.yml, build-deploy.yml, fontes-smoke.yml
└── docs/PLANO.md
```

---

## 10. Fases

Cada fase termina com o site no ar (ou no Docker local) mostrando o que ela entregou.

**Fase 0 — Fundação**
- Repositório, compose (`db`, `builder`, `web`), CI (ruff, mypy, pytest, `tsc`).
- `sacibras fontes-smoke`: uma chamada mínima a cada fonte do §4, rodada **localmente e dentro
  do Actions**, para mapear bloqueios por IP. Resultado vira tabela neste documento.
- Esqueleto ponta a ponta: catálogo com 5 séries → `resumo.json` → página com 6 cartões →
  deploy no Pages.

**Fase 1 — Macro núcleo**: Resumo completo, Atividade, Trabalho, Inflação, Juros e Copom
(com Focus por reunião e implícita da curva), Setor externo. Chamada direta do navegador
para o ponto mais recente.

**Fase 2 — Contas públicas, dívida e impostos**: RTN, NFSP, DBGG/DLSP, DPF, arrecadação,
carga tributária, linha do tempo da reforma.

**Fase 3 — Estados**: SICONFI, mapa, rankings, limites da LRF, capitais.

**Fase 4 — Mercados**: B3 (índices, altas e baixas, amplitude), câmbio, commodities.

**Fase 5 — Previsões**: PIB agora, IPCA, desocupação, simulador da dívida, histórico de acerto.

**Fase 6 — Acabamento**: calendário, "novo desde sua última visita", PNG dos gráficos,
textos alternativos, imagem de compartilhamento, domínio.

---

## 11. Em aberto

- **Nome e domínio** (`sacibras` é o nome de trabalho).
- **Comex Stat e outros bloqueios**: depende do teste da Fase 0.
- **DI1 futuro**: a B3 publica, mas o acesso estável e gratuito precisa ser confirmado; até lá,
  a implícita sai do Tesouro Direto.
- **Novo Caged**: achar uma série agregada oficial leve antes de baixar os arquivos do PDET.
- **Portal da Transparência**: pede chave gratuita (vira segredo do Actions) — só na Fase 2+.
- **Municípios além das capitais**: custo de chamadas ao SICONFI × valor.
