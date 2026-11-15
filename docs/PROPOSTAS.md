# Propostas

O que foi pedido ou pensado e ainda falta, por assunto. Pedido novo vira linha aqui antes de
virar código; o que fica pronto sai (a história está no git e no
[PROXIMOS-PASSOS](PROXIMOS-PASSOS.md) da época). A ordem do que fazer agora fica no
[PROXIMOS-PASSOS](PROXIMOS-PASSOS.md).

Última atualização: 15/11/2026 (segunda sessão do dia: PIB trimestral por estado e decomposições). Na primeira sessão da nuvem de 15/11 entrou quase tudo o que estava
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

**Decomposições** (feitas em 15/11/2026, no branch: IPCA por grupo, PIB pela demanda e pela
oferta, fatores da dívida e da desocupação, carrego do PIB). O que ficou de fora:
- IPCA pelas categorias do BC (serviços, industriais, alimentação no domicílio, administrados):
  o SGS dá a variação, não o peso; sairia dos subitens do IBGE, classificados um a um.
- IPCA por grupo antes de dez/2020 (tabelas 1419 e 2938 do SIDRA, com outra estrutura de pesos).
- Massa de renda = gente ocupada × rendimento médio; crédito por pessoa física e empresa.
- Exportações em preço × quantidade (índices do MDIC; **do PC**).
- A tabela oficial de fatores condicionantes da DBGG (só na nota mensal do BC, em planilha
  com poucos meses): ler à mão ou achar o arquivo com a série.
- Prévia de dado atrasado que ainda não tem conta: pobreza e Gini (PNAD anual), carga
  tributária (OCDE, dois anos) e PIB dos municípios (2023). Nenhuma tem indicador mensal
  bom o bastante; ficam sem prévia até aparecer um.

**Estados**
- Mínimos de saúde e educação (SIOPS e SIOPE; **do PC**).
- PIB trimestral por estado (feito em 15/11/2026, no branch, à espera do Caio). O que ficou
  de fora: o IBC-R de MT, MS, RN e MA (conferir os códigos no SGS); a série do estado no tempo
  na ficha ("Um estado por dentro"); a conferência automática contra os institutos estaduais
  (o arquivo muda de nome a cada trimestre); e agropecuária por estado para corrigir o
  trimestre da safra (LSPA), onde a conta mais erra (RS, MT).

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

## Em espera

- **Selo "dado anterior"** na peça mantida (`mantidos` já está no `painel.json`).
- **Tarefa agendada que relê** os relatórios (Caio, 14/11/2026: *"o 3 anote no propostas"*):
  disparada pela issue `releitura` ou por data, lê o PDF, atualiza `relatorios.py`, `leis.py` e
  `leituras.py` e abre PR. Não serve para o que só abre do PC (Planalto); número em imagem no
  PDF pede conferência humana.
