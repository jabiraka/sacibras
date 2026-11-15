# Propostas

O que foi pedido ou pensado e ainda falta, por assunto. Pedido novo vira linha aqui antes de
virar código; o que fica pronto sai (a história está no git e no
[PROXIMOS-PASSOS](PROXIMOS-PASSOS.md) da época). A ordem do que fazer agora fica no
[PROXIMOS-PASSOS](PROXIMOS-PASSOS.md).

Última atualização: 15/11/2026. Na sessão da nuvem de 15/11 entrou quase tudo o que estava
aqui (PIB pela oferta e demanda privada, ciclos da Selic alinhados, riscos de mercado, dívida
e jurídicos, estados com CAPAG, limites, previdência, exportações, RRF/Propag e capitais,
séries novas em mercados, mundo, setor externo, trabalho, pobreza, demografia e impostos,
busca, tradução e acabamento). Abaixo, só o que ficou: o que depende do PC está marcado e
repetido no PROXIMOS-PASSOS.

## Fora, por decisão do Caio

- **B3**: o site veda coleta automatizada; `SB_B3` desligado. O que depende dela (IFIX, DI,
  probabilidade do Copom, cupom de IPCA curto, Ibovespa com dividendos, inflação implícita
  antes de mai/2029) fica fora.
- **Desemprego de equilíbrio (NAIRU)** (14/11/2026): o BC não publica número oficial; só há
  um estudo no blog do BC e o hiato do produto do RPM. Não entra.
- **Fonte não oficial** nos Riscos (EMBI, CDS) e cenário montado pela pessoa fora dos três
  simuladores.
- **Previsões próprias** (15/11/2026, *"sem próprias previsões por enquanto"*): IPCA e
  desocupação por modelo sazonal e o PIB agora com indústria, varejo e serviços.

## Falta, por assunto

**Juros e Selic**
- Faixa de erro do modelo de 2024, se o BC publicar; efeito por grupo de preços (idem).

**Inflação e Trabalho**
- Serviços subjacentes: achar o código no SGS (**do PC**).
- Caged por UF (**do PC**).

**Riscos**
- Alerta contra outros países: previdência (achar par em fonte oficial com o mesmo número
  para todos; reservas, volatilidade do câmbio e hiato de crédito já entraram).

**Contas públicas e Impostos**
- O imposto de hoje ao lado na reforma: ICMS modal por estado (27 leis; **do PC**, o Confaz
  não respondeu da nuvem). O que muda por estado com a cobrança no destino: não há número
  oficial por estado (só a regra de partilha, que já está no gráfico).
- Alíquotas do Imposto Seletivo: a LC 214 deixa para lei ordinária; entra quando sair.
- Gasto tributário antes de 2014: a Receita só publica em PDF; fica fora sem conferência.
- Multiplicador de receita da SPE: só se sair com regularidade (estudo avulso não entra).

**Estados**
- Mínimos de saúde e educação (SIOPS e SIOPE; **do PC**).

**Setor externo**
- Preço × quantidade das exportações (índices do MDIC; **do PC**, certificado vencido).

**Pobreza**
- Déficit habitacional da Fundação João Pinheiro (**do PC**; ver se sai com regularidade).

**Demografia**
- Contribuintes por beneficiário (tabela do SIDRA; **do PC**).

**Tela, busca e tradução**
- Domínio (com ele, trocar `ENDERECO` em `web/vite.config.ts` e `anterior.SITE`).
- Agenda: as reuniões do Copom na caixa "O que sai esta semana" (não há API de datas
  futuras; só lendo o calendário publicado pelo BC).

## Achados da revisão das telas (15/11/2026)

Caio: *"toque nas telas, veja se consegue pensar em algo que está faltando ou alguma tela
quebrando [...] que eles encontrem oq estão procurando"*. Corrigido na hora: o menu lateral
que escondia Previsões e Riscos, a busca (palavras de ligação, busca por parte das palavras,
linhas das tabelas curtas, IPCA por grupo), o número separado do "%" na quebra de linha e as
frases do PIB dos estados e da Selic. Fica:

- **O que se procura e o painel não tem** (busca testada com 65 termos):
  - juros do cartão de crédito, do rotativo e do cheque especial (SGS, taxa por modalidade;
    conferir os códigos no CKAN);
  - salário mínimo, em reais e descontada a inflação (o valor do decreto, lido na norma);
  - itens do IPCA: gasolina, energia elétrica, aluguel (SIDRA 7060 tem os subitens; hoje a
    busca leva ao grupo, Transportes ou Habitação);
  - IPCA-15 como série (hoje só no detalhe do cartão do IPCA do mês e no glossário).
- **Tabelas no celular**: a 390 px, 23 tabelas rolam para o lado sem sinal de que há coluna
  escondida; várias passam só 10 px (o IPCA por grupo corta o "Peso no índice"). Uma sombra na
  borda direita enquanto houver o que rolar, e apertar as que passam por pouco.
- **Mapa dos estados**: a 1280 px ocupa meia largura e o resto fica vazio; as siglas dos
  estados pequenos (RN, PB, PE, AL, SE, ES, RJ, DF) somem ou se sobrepõem.
- **Página do glossário**: uma lista de todos os termos, no menu ou no rodapé, para quem quer
  ler as definições sem caçá-las na tela.

## Em espera

- **Selo "dado anterior"** na peça mantida (`mantidos` já está no `painel.json`).
- **Tarefa agendada que relê** os relatórios (Caio, 14/11/2026: *"o 3 anote no propostas"*):
  disparada pela issue `releitura` ou por data, lê o PDF, atualiza `relatorios.py`, `leis.py` e
  `leituras.py` e abre PR. Não serve para o que só abre do PC (Planalto); número em imagem no
  PDF pede conferência humana.
