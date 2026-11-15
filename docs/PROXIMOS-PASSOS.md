# Próximos passos

**Leia no começo da sessão e atualize no fim** (Caio, 14/11/2026). Aqui fica só o que está em
aberto: o que foi feito sai (a história está no git), as ideias em espera ficam no
[PROPOSTAS](PROPOSTAS.md) e os limites conhecidos no [PLANO](PLANO.md#12-limites-conhecidos).

Última atualização: 15/11/2026. A sessão da nuvem de 15/11 fez tudo o que dava para fazer de
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
escolhe o resto.

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
