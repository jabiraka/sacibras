# Próximos passos

**Leia isto no começo de cada sessão e atualize no fim** (Caio, 14/11/2026: *"deixe os próximos
passos sempre anotado num .md, assim a próxima sessão sabe o que fazer"*). O plano inteiro está
no [PLANO](PLANO.md); as fontes testadas, em [FONTES](FONTES.md). Aqui fica só o que vem a
seguir, em ordem, e o que espera decisão.

Última atualização: 14/11/2026 (quarta sessão do dia).

---

## Onde paramos

- Trabalho no branch `ccr-615b3774-yyp5n8` (CI verde). **Ainda não está no `main` nem no ar.**
- O site: página inicial ("Status da economia brasileira", seis números com o ponto mais novo
  buscado pelo navegador, o IPCA contra a meta) e onze assuntos — atividade, trabalho,
  inflação, juros e Copom, crédito, mercados, setor externo, contas públicas e dívida, estados,
  Brasil no mundo, previsões.
- Feito nesta sessão: curva zero do Tesouro pelo método do Jabs (`curvas.py`) e, em Juros, os
  títulos contra o Focus no mesmo prazo (juro e inflação; responde "o Focus está abaixo dos
  títulos?": empatam em jan/2027, 1 ponto acima em jan/2028, ~4,7 pontos em 2036); "Quanto
  rendeu R$ 100" em Mercados; a busca com sinônimos (lupa no cabeçalho, caixa na entrada);
  a ficha de cada estado (receita, despesa por natureza e por função, investimento, dívida em
  partes e com a União, pela DCA 2025 e o RGF), com a média dos estados ao lado; o teste das fontes no Actions passou (resultado em [FONTES](FONTES.md)).
- Prévia privada: https://claude.ai/artifact/YPR6sEPLQNHPSkzxektAMS — republicar depois de
  mudança visível.

## Esperando decisão do Caio (no PC)

1. **Publicar.** Juntar o branch no `main` e ligar o Pages (Settings → Pages → Source: GitHub
   Actions). O `build-deploy.yml` publica a cada push no `main` e duas vezes por dia útil. A
   sessão na nuvem não manda ao `main` sem o "sim"; pode abrir o PR.
2. **B3: ligar ou não** (`SB_B3`). O site da B3 veda coleta automatizada. Recomendação: deixar
   desligado até ter autorização. Detalhe em [FONTES](FONTES.md).
3. **Normas que faltam ler** (o Planalto não abre de fora do Brasil). Colando os trechos, entram
   na tela: LC 200/2023 e LDO 2026 (meta de primário e banda), LC 101/2000 arts. 19 e 20
   (limites de pessoal), Resolução do Senado 40/2001 (dívida dos estados).
4. **Calendário de divulgações.** A API de calendário do IBGE (`servicodados`) derruba a conexão
   de fora do Brasil, então não dá para testar daqui. No PC: abrir
   `https://servicodados.ibge.gov.br/api/v3/calendario/?qtd=20` no navegador e ver se responde
   com `Access-Control-Allow-Origin`; se sim, o navegador do visitante pode buscar direto.

## Próximos passos, em ordem (dá para fazer na nuvem)

1. **Contas de cada estado: conferir.** Pronto nesta sessão (ficha do estado, 27 UFs, somas
   conferidas). Falta olhar com calma os casos estranhos: TO e PR (partes da dívida contratual
   fora das contas lidas, vão para "Outras"), o ITCMD do DF, RR e AC com dívida com a União
   perto de zero. A lista do que mais dá para abrir por estado está no [PROPOSTAS](PROPOSTAS.md).
2. **Estados no tempo.** O assunto é uma foto do último período. Faltam a série de cada estado
   (tocar no estado e ver a linha dele contra o Brasil), a nota CAPAG (CSV do Tesouro) e a
   despesa por função per capita. Cuidado com o custo: cada período a mais são 54 chamadas ao
   SICONFI; usar só o 3º quadrimestre de cada ano (o fechamento) para a história.
3. **Arrecadação federal por tributo** (RTN aba 1.1 ou o CSV da Receita) e **carga tributária**.
4. **Previsões próprias que faltam:** IPCA e desocupação com modelo sazonal; "o que mudou desde a
   última leitura" no PIB agora (precisa guardar a leitura anterior, por exemplo no cache do
   Actions); PIB agora com indústria, varejo e serviços além do IBC-Br. Sempre ao lado do
   Focus, com barra de erro e o método numa frase.
5. **Brasil no mundo:** câmbio contra o dólar no ano (BIS `WS_XRU`), juro de 10 anos (OCDE),
   inflação mensal em 12 meses (BIS). A trajetória de país que só está no arquivo de todos os
   países mostra só de 2020 a 2031.
6. **Acabamento:** "novo desde sua última visita", PNG dos gráficos, imagem de compartilhamento,
   domínio.

## Limites conhecidos

- O "PIB agora" é estimativa própria (reta com o IBC-Br), ao lado do Focus. Com dois meses do
  trimestre, o erro real é maior que o erro típico medido.
- O histórico de acerto do Focus compara com o dado revisado de hoje, não com o da época.
- O simulador da dívida é conta de ordem de grandeza: não separa a dívida atrelada ao câmbio.
- A participação da dívida por indexador não traz o IPCA no SGS: "índices de preços" é o que
  falta para 100 %.
- No resultado primário dos estados, o numerador é o acumulado do ano (jan–ago) e o
  denominador é a RCL de 12 meses.
- O gráfico de duas métricas de "Brasil no mundo" tira do desenho, por padrão, quem fica muito
  longe dos outros (a Turquia na inflação), com aviso e botão para mostrar; em "Estados"
  mostra todos (os extremos, RJ, MG e RS na dívida, são a história).
- O build a frio leva cerca de 2 minutos com cache vazio de SICONFI e Focus (medido
  localmente: 1 min 40 s com parte em cache).

## Para conferir antes de mostrar

```bash
cd builder && uv run ruff check src tests && uv run ruff format --check src tests \
  && uv run mypy && uv run pytest -q && uv run sacibras build
cd web && npm run build
```

Depois, olhar a 390 e a 1280 px com tudo aberto (regra no `CLAUDE.md`).
