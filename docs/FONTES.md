# Fontes testadas

Teste de 14/11/2026, de uma máquina **fora do Brasil** (o que revela bloqueio por IP
estrangeiro), sem chave e sem serviço pago. "CORS" é a resposta a
`Origin: https://x.github.io`: com CORS, o navegador do visitante também pode chamar.

**De dentro do GitHub Actions** (máquina nos EUA, execução de 14/11/2026, workflow
`fontes-smoke.yml`): responderam todas as fontes que o builder usa — SGS, Focus, Copom, SIDRA,
FMI (WEO e grupos), BIS, SICONFI (RGF e RREO), CKAN e RTN, IPEADATA, Tesouro Direto (16 s),
Comex Stat. Só o IBGE `servicodados` (calendário e malhas) caiu por tempo (41 s), como daqui:
por isso a malha fica no repositório e o calendário é buscado pelo navegador do visitante.

## Em uso no builder

| Fonte | O que dá | Responde de fora? | CORS | Observações |
|-------|----------|-------------------|------|-------------|
| BCB SGS `api.bcb.gov.br/dados/serie/bcdata.sgs.N` | 60 séries do catálogo | sim | `*` | Série diária recusa janela maior que 10 anos; alguns códigos voltam em ordem decrescente de data; a 432 (Selic meta) vem preenchida até a próxima reunião do Copom. |
| BCB Focus (Olinda) `…/Expectativas/versao/v1/odata/` | medianas anuais, mensais, trimestrais e Selic por reunião | sim, 0,2–1 s | ecoa a origem | O recurso mensal é `ExpectativaMercadoMensais` (sem "s"). Não aceita `+` como espaço: usar `%20`. `DataReferencia` e `Reuniao` são texto, ordenar no cliente. |
| BCB Copom `bcb.gov.br/api/servico/sitebcb/historicotaxasjuros` | as 290 reuniões, com data e meta | sim | – | Não há API com o calendário das reuniões futuras. |
| IBGE SIDRA `apisidra.ibge.gov.br/values/…` | PIB (5932), PNAD (6381, 6390, 6392), PIM (8888), PMC (8880, 8881), PMS (5906), IPCA (7060) | sim | `*` | Variáveis e categorias conferidas pela própria resposta (lista em `secoes/`). `desctabapi.aspx` dá 403. |
| FMI WEO, SDMX `api.imf.org/external/sdmx/2.1/data/IMF.RES,WEO,9.0.0/` | anuais e projeções até 2031, 22 países e agregados | sim, 1–2 s | `*` | Edição de out/2026 (`PUBLICATION_DATE`). Agregados: G001 mundo, G110 avançados, G163 zona do euro, G200 emergentes, G205 América Latina. Pedir `Accept: application/json`. |
| BIS `stats.bis.org/api/v2/data/dataflow/BIS/` | juro básico (WS_CBPOL) e inflação em 12 meses (WS_LONG_CPI) | sim | sim | CSV. Alemanha, França, Itália e Espanha: usar XM (BCE). Argentina parada em jun/2025. |
| Tesouro Direto (CSV do Tesouro Transparente) | taxa e preço diários de cada título desde 2004 | sim, ~15 s | não | 15 MB, `;` e decimal com vírgula. Conexão cai de vez em quando: o builder insiste. Licença ODbL. |
| IPEADATA OData `ipeadata.gov.br/api/odata4/` | Ibovespa diário (`GM366_IBVSP366`) | sim (usar https) | `*` | Um dia de atraso em relação à B3. EMBI+ (`JPM366_EMBI366`) parou em 30/07/2024. Saldo do Novo Caged: `CAGED12_SALDONAJU12`. |

Entraram depois, no mesmo dia, com o que se aprendeu ao usar:

| Fonte | O que dá | Observações |
|-------|----------|-------------|
| SICONFI, RGF Anexos 01 e 02 | pessoal/RCL, dívida líquida/RCL e RCL das 27 UFs | ~54 chamadas em série (cache de 24 h). O 3º quadrimestre de 2026 ainda vem vazio: vale o 2º. O DF é esfera `D` em `entes`, mas o RGF dele só responde com `co_esfera=E`. O Amapá informa os percentuais de limite em fração (0,49): os limites saem da razão entre os valores em reais e a RCL ajustada. O limite que o RGF traz **varia por estado** (pessoal: 49 % na maioria, 48,6 % em PA, BA e GO; dívida: 200 % na maioria, 90,2 % em RR): a tela mostra o da lei (`leis.py`, lida em 14/11/2026) e diz quem difere. |
| IBGE SIDRA 4099 (nível UF) | desocupação trimestral por estado | A tabela 5938 (PIB por UF) para em 2023 e a 6579 não tem a população desse ano: PIB per capita ficou de fora. |
| Tesouro Transparente, RTN (XLSX, aba 1.1) | receita líquida, despesa total, Previdência, pessoal e primário do Governo Central, mensais | O nome do arquivo muda todo mês: o builder o descobre pelo CKAN (`package_show`). As linhas são achadas pelo texto do rótulo. Sai com uns dois meses de atraso. |
| BCB SGS 4639 | primário mensal do Governo Federal e Banco Central (o Governo Central da meta), R$ milhões | Soma de 12 meses contra a meta da LDO. A conta da meta (desconto de precatórios, defesa, saúde) não tem API: vem do relatório bimestral do Executivo, lido à mão pela nota da Consultoria de Orçamentos do Senado (`leis.AVALIACOES_2026`). |
| BCB SGS 4173 a 4180 | dívida mobiliária federal por indexador | A família não tem o IPCA: "índices de preços" é o que falta para 100 % (confere com a fatia das NTN-B). |
| BCB Focus, edições antigas | a mediana de qualquer data passada | Permite medir o erro do consenso sem banco: ~60 consultas, um mês de cache. |
| IBGE FTP, Projeções da População revisão 2024 (`ftp.ibge.gov.br/Projecao_da_Populacao/Projecao_da_Populacao_2024/`) | população por sexo e idade, fecundidade, esperança de vida, nascimentos, óbitos, razões de dependência e idade mediana, de 2000 a 2070, Brasil e 27 UFs | Responde de fora do Brasil (14/11/2026), 1 a 2 MB por XLSX. Usadas as tabelas 2, 3 e 4; colunas achadas pelo nome do cabeçalho. O relatório metodológico (3ª ed.) diz: referência em 1º de julho; até 2022 dado ajustado aos Censos, depois projeção; sem faixa de erro. A nota da tabela 4 escreve "60 anos ou mais" na razão de dependência dos idosos de 65, mas os valores são de 65+ (conferido: 65+ ÷ 15-64). |
| IBGE SIDRA 1620 | PIB em volume, trimestral (série encadeada, média 1995 = 100), para o PIB por ocupado | Conferido pela resposta em 14/11/2026: variável 583, classificação 11255/90707. |
| Tesouro RTN, aba 1.1, linha "1.3 Arrecadação Líquida para o RGPS" | a receita do INSS, contra os benefícios (linha 4.1) | O rótulo vem com um " - " depois da numeração: o `normalizar` tira. |

| IBGE geoftp, Malha Territorial 2024 (`BR_UF_2024.zip`, 15 MB) | o contorno das 27 UFs | Responde de fora do Brasil; a API de malhas (`servicodados`) não. Simplificada por `npm run malha` (mapshaper, 0,6 % dos vértices, sem as ilhas oceânicas) para um TopoJSON de 48 KB que fica no repositório. |

| FMI SDMX, hierarquia `H_WEO_COUNTRIES` (`hierarchicalcodelist/all/all/latest`, 2,7 MB) | quem pertence a cada grupo do WEO (Mundo 197, Avançados 43, Emergentes 154, América Latina 33, Zona do euro 21…) | Responde de fora. Os nomes em português vêm do `pycountry` (tradução pt_BR do ISO 3166), com 20 corrigidos à mão. A chave de país vazia no WEO traz os 197 numa chamada. |
| SICONFI, RREO Anexos 03 e 06 | ICMS de 12 meses e resultado primário do ano, por UF | 4º bimestre de 2026 nas 27 UFs (o 5º ainda vazio). ICMS somado: R$ 909,6 bi em 12 meses. Primário: a conta "sem RPPS, acima da linha", a mesma da meta da LDO. |
| BCB SGS 195 (poupança, rentabilidade no período) | o rendimento da poupança de cada aniversário | Conferida no `package_search` em 14/11/2026. Cada dia traz o rendimento do mês que começa nele; "Quanto rendeu R$ 100" usa o do dia 1º. |
| Tesouro Direto, os quatro tipos | curva zero nominal (Prefixado + Prefixado com Juros Semestrais) e real (IPCA+ + IPCA+ com Juros Semestrais) | Taxa média entre compra e venda (o "mid", como no finance_agent). Os papéis com cupom entram por *bootstrap* depois do último sem cupom (`curvas.py`); o preço refeito pela curva bate com o da taxa do papel. O IPCA+ sem cupom mais curto vence em mai/2029: antes disso não há inflação implícita. |
| SGS e SIDRA, pelo navegador | o ponto mais novo dos números da página inicial | CORS `*` conferido com `Origin` de github.io. O SGS às vezes devolve HTML no lugar do JSON: o builder agora pede de novo antes de desistir. |

Da aba de riscos (14/11/2026):

| Fonte | O que dá | Observações |
|-------|----------|-------------|
| ONS, dados abertos `ons-aws-prod-opendata.s3.amazonaws.com/dataset/ear_subsistema_di/EAR_DIARIO_SUBSISTEMA_<ano>.csv` | energia armazenada nos reservatórios, por subsistema, dia a dia desde 2000 | Um CSV por ano (~60 KB), `;`, licença CC-BY, responde em menos de 1 s. O percentual do país não vem pronto: soma dos quatro subsistemas sobre a soma das capacidades (`fontes/ons.py`). |
| BCB SGS, séries de risco | juros em reais (5045), prazo médio da dívida (10618), DLSP externa (4535), dívida externa bruta e de curto prazo (3684, 21519), importações (22709), swaps cambiais (29723), inadimplência PF e PJ (21084, 21083), atrasos de 15 a 90 dias (21003), Basileia e capital principal (29661, 29663) | Metade não está no CKAN: conferidas no serviço de metadados do SGS (FachadaWSSGS). Basileia sai com uns oito meses de atraso. O swap mensal (29533) tem o sinal contrário ao diário. A taxa implícita da DBGG, as compromissadas em % do PIB e o vencimento em 12 meses **não existem no SGS**: estão na planilha `…/hist_estatisticasfiscais/AAAAMM_Tabelas_de_estatisticas_fiscais.xlsx` (tabelas 24, 17 e 25), um arquivo por mês com poucos meses dentro. Séries paradas a evitar: 21424 e 21802 (Basileia antiga, jun/2023), 12504 e 11411 (2018), 29403 (ROE, 2024). |
| BCB, nota para a imprensa Estatísticas fiscais (PDF mensal) | elasticidades da DLSP e da DBGG ao câmbio, à Selic e aos preços | `bcb.gov.br/content/estatisticas/hist_estatisticasfiscais/AAAAMM_Texto_de_estatisticas_fiscais.pdf` (AAAAMM é o mês da publicação). O quadro é imagem: lido à mão em `relatorios.py`, todo mês. |
| BCB, Relatório de Estabilidade Financeira (PDF, maio e outubro) | teste de estresse dos bancos | `bcb.gov.br/content/publicacoes/ref/AAAAMM/RELESTABAAAAMM-refPub.pdf`. Lido à mão (seção 1.2.5). |
| Tesouro Nacional, classificação de risco | nota de crédito do país nas três agências | A página do gov.br está com a tabela vazia e o sistema que a serve (`sisweb.tesouro.gov.br/apex/f?p=2810:2`) dava 503 em 14/11/2026. Histórico lido no PDF do Tesouro (até fev/2016) e em cópias do sisweb no Internet Archive (2018 e 2024); atos de 2023 a 2025 nos comunicados de `gov.br/tesouronacional`. Não serve para o builder chamar: entra lido à mão. |

## Testadas, ainda sem uso (próximas fases)

| Fonte | O que dá | Responde de fora? | CORS | Observações |
|-------|----------|-------------------|------|-------------|
| SICONFI `apidatalake.tesouro.gov.br/ords/siconfi/tt/` | RGF e RREO dos estados | sim, 1–2 s por chamada | ecoa | Mais recente em 2026: RGF do 2º quadrimestre, RREO do 4º bimestre. Campos (conferidos em SP): pessoal/RCL em RGF-Anexo 01 `DespesaComPessoalTotal`, coluna "% sobre a RCL Ajustada"; DCL/RCL em RGF-Anexo 02 `PercentualDaDCLSobreARCL`; ICMS em RREO-Anexo 03; primário em RREO-Anexo 06. ~108 chamadas para as 27 UFs. O DF é esfera `D`. |
| Tesouro Transparente (CKAN) | RTN (XLSX, aba 1.1 mensal desde 1997), estoque da DPF por título, CAPAG | sim | não | O nome do arquivo do RTN muda todo mês: descobrir pelo CKAN. Prazo médio, custo e detentores da dívida não estão em dado aberto leve. |
| Receita Federal `gov.br/receitafederal/dados/arrecadacao-estado.csv` | arrecadação por UF e tributo | sim | não | 2,4 MB, latin-1. |
| Comex Stat `api-comexstat.mdic.gov.br` | balança comercial detalhada | sim (POST `/general`) | ecoa | O HTTP 451 de 13/11 só acontece no GET com cabeçalho `Origin`. Os CSVs de `balanca.economia.gov.br` falham por cadeia de certificado incompleta. |
| Banco Mundial `api.worldbank.org/v2` | indicadores anuais | sim, mas lento | `*` | A primeira chamada de cada URL levou de 21 a 88 s. Reserva, não fonte principal. |
| OCDE SDMX `sdmx.oecd.org` | CPI, PIB trimestral, juro de 10 anos, Economic Outlook | sim | sim | Cobertura irregular fora da OCDE (Peru e Argentina faltam em várias). |
| FRED `fred.stlouisfed.org/graph/fredgraph.csv?id=` | séries dos EUA | instável | não | Um id por chamada; deu timeout numa das rodadas. |
| Tesouro dos EUA `home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/<ano>/all?type=daily_treasury_real_yield_curve&field_tdr_date_value=<ano>&page&_format=csv` | juro real (e nominal, com `daily_treasury_yield_curve`) dos títulos americanos, por prazo, dia a dia | sim, 0,5 s | `*` | Um CSV por ano, data `MM/DD/YYYY`, ordem decrescente; o real de 10 anos começa em 02/01/2003. De 2003 a 2023 há um arquivo só em `…/daily-treasury-rate-archives/par-real-yield-curve-rates-2003-2023.csv` (outro cabeçalho, ordem crescente). Ler a coluna pelo nome. Para o risco-país pelo juro real (aba de riscos). |
| BIS `stats.bis.org/api/v2/data/dataflow/BIS/WS_CREDIT_GAP/1.0/Q.BR.P.A.C?format=csv` | hiato de crédito do Brasil (C), razão crédito/PIB (A) e tendência (B); serviço da dívida do setor privado em `WS_DSR/1.0/Q.BR.P` | sim, 1 a 9 s | não visto | Trimestral, dois trimestres de atraso; o hiato começa em 2006. A ordem das colunas muda entre os dois conjuntos: ler pelo nome. |
| ANBIMA ETTJ `anbima.com.br/informacoes/est-termo/CZ-down.asp` | curva zero do dia | sim | – | Só o dia corrente foi testado. |

## Não funcionam daqui

| Fonte | O que aconteceu |
|-------|-----------------|
| IBGE `servicodados.ibge.gov.br` (calendário de divulgações, malhas, metadados) | conexão derrubada no TLS em todas as tentativas. **Do Brasil responde** (PC do Caio, 14/11/2026): o calendário (`/api/v3/calendario/?de=MM-DD-AAAA&ate=MM-DD-AAAA&qtd=N`) volta com `Access-Control-Allow-Origin: *`, e o navegador do visitante o busca direto (`web/src/calendario.ts`). Alguns títulos vêm com acento em codificação dupla ("Ã§"): a tela usa nomes próprios, não o título da API. |
| Planalto `planalto.gov.br/ccivil_03` | redireciona para a página inicial. **Do Brasil abre** (PC do Caio, 14/11/2026; no `curl` do Windows, com `--ssl-no-revoke`). Lidos nesse dia: LC 200/2023, LDO 2026 (Lei 15.321/2025), LC 101/2000, LC 141/2012 e a Constituição (arts. 198 e 212); trechos em `leis.py`. A Resolução do Senado 40/2001 foi lida em `legis.senado.leg.br/norma/562458`. Falta o Decreto 12.079/2024. |
| FMI DataMapper `imf.org/external/datamapper/api` | 403 (Akamai) em parte das chamadas; trocado pela API SDMX. |
| Stooq, Yahoo Finance | desafio de JavaScript, HTTP 429 ou sem CORS; não usar. |
| DBnomics | responde, mas o WEO mais novo lá é abril/2025. |

## B3: funciona, mas o site veda a coleta

Tecnicamente tudo abaixo responde de fora (com `403` ao acaso do Cloudflare, que passa na
tentativa seguinte). **Mas** a página do Boletim Diário do Mercado da B3 diz, em texto lido em
14/11/2026:

> é expressamente vedada a coleta automatizada, inclusive por meio de ferramentas de
> inteligência artificial, para quaisquer finalidades, comerciais ou não, próprias ou de
> terceiros.

Por isso o builder **não lê o site da B3 por padrão**: o Ibovespa vem do IPEADATA, o câmbio do
Banco Central e a curva de juros do Tesouro Direto. As fontes abaixo estão escritas e ligam com
`SB_B3=1`, que **fica desligado** (Caio, 14/11/2026).

| Rota | O que dá |
|------|----------|
| `sistemaswebb3-listados.b3.com.br/indexStatisticsProxy/IndexCall/GetPortfolioDay/<base64>` | fechamento diário de qualquer índice (IBOV, IBXX, SMLL, IDIV, IFIX, IFNC, IMAT, ICON, UTIL, IMOB, IEEX, INDX), um ano por chamada. Escrito em `fontes/b3_indices.py`. |
| `cotacao.b3.com.br/mds/api/v1/DerivativeQuotation/{DI1,DOL,IND,DAP,BGI,CCM,SJC,ICF}` | todos os vencimentos de um futuro, com último negócio, ajuste anterior e contratos em aberto (CORS `*`). Escrito em `fontes/b3_derivativos.py`. |
| `b3.com.br/pesquisapregao/download?filelist=PRaammdd.zip` | ajustes de todos os futuros de um dia passado (XML BVBG.086, 11 MB compactado), desde 2018. Não escrito. |
| `bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_Dddmmaaaa.ZIP` | cotações do dia, com os ETFs de índice (BOVA11, SMAL11, IVVB11, DIVO11, GOLD11, HASH11, XFIX11, NASD11). Não escrito. |
| `arquivos.b3.com.br/bdi/table/EconomicIndicators/…` (POST) | moedas de emergentes, bolsas de fora, participação do investidor estrangeiro; só ~21 dias de janela. Não escrito. |
| Taxas referenciais (DI × pré, cupom cambial) | a página antiga não responde mais; a curva sai dos futuros. |

## Ideias de preços relevantes para o macro

O que já está na tela: Ibovespa (em reais e em dólares), dólar, euro, curva prefixada, curva de
juro real, inflação implícita, Selic embutida na curva, IC-Br (commodities em reais).

O que dá para acrescentar, por ordem de valor para a leitura macro:

1. **Juros futuros de DI** e a Selic embutida mês a mês — o termômetro mais rápido da política
   monetária (B3; hoje a versão aberta usa os prefixados do Tesouro, com menos vértices).
2. **Índices setoriais** como sensor de juro e câmbio: financeiro, consumo e imobiliário sentem
   a Selic; materiais básicos, o dólar e as commodities (B3).
3. **Dólar futuro e cupom cambial** (DOL, DDI/FRC): quanto custa proteger-se do câmbio (B3).
4. **Futuros agrícolas** (boi, milho, soja, café) como antecipação da inflação de alimentos (B3).
5. **ETFs de índice** (BOVA11, SMAL11, IVVB11, DIVO11, IMAB11) — repetem os índices; valem pelo
   volume negociado e pelo fluxo (B3, COTAHIST).
6. **Fluxo do investidor estrangeiro** na bolsa (B3, BDI).
7. **Moedas de emergentes contra o dólar** e o real entre elas: BIS (`WS_XRU`, mensal, aberto).
8. **Juro de 10 anos e bolsas de fora** para comparar: OCDE (`DF_FINMARK`) e FRED.
9. **Risco-país**: o EMBI+ aberto parou em 2024; CDS não tem fonte gratuita.
