# Próximos passos

**Leia isto no começo de cada sessão e atualize no fim** (Caio, 14/11/2026: *"deixe os próximos
passos sempre anotado num .md, assim a próxima sessão sabe o que fazer"*). O plano inteiro está
no [PLANO](PLANO.md); as fontes testadas, em [FONTES](FONTES.md); as ideias em espera, no
[PROPOSTAS](PROPOSTAS.md). Aqui fica só o que vem a seguir, em ordem, e o que espera decisão.

Última atualização: 14/11/2026 (quinta sessão do dia).

---

## Onde paramos

- **Publicado no `main`** em 14/11/2026, a pedido do Caio (*"pode publicar no main"*). O
  trabalho da nuvem continua no branch `ccr-615b3774-yyp5n8` e vai ao `main` quando pronto.
- O site: página inicial ("Status da economia brasileira", seis números com o ponto mais novo
  buscado pelo navegador, o IPCA contra a meta, a busca) e onze assuntos — atividade,
  trabalho, inflação, juros e Copom, crédito, mercados, setor externo, contas públicas e
  dívida, estados (com a ficha de cada um), Brasil no mundo, previsões.
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
- Prévia privada: https://claude.ai/artifact/YPR6sEPLQNHPSkzxektAMS — republicar depois de
  mudança visível.

## Esperando decisão do Caio (no PC)

1. **Ligar o Pages** (Settings → Pages → Source: GitHub Actions). O `build-deploy.yml` publica
   a cada push no `main` e duas vezes por dia útil; sem o Pages ligado, o deploy falha.
2. **B3: ligar ou não** (`SB_B3`). O site da B3 veda coleta automatizada. Recomendação: deixar
   desligado até ter autorização. Com ela vêm os futuros de DI (a probabilidade da próxima
   reunião do Copom, como o FedWatch do Econvitals), os índices setoriais e o cupom de IPCA.
3. **Séries fora do catálogo do BC.** Bens industriais (27863) e alimentação no domicílio
   (27864) não estão no CKAN do BC; foram conferidas no serviço de metadados do SGS e a
   alimentação bate com o IBGE. A regra do `CLAUDE.md` ganhou essa saída: confirmar.
4. **Normas que faltam ler** (o Planalto não abre de fora do Brasil). Colando os trechos, entram
   na tela: LC 200/2023 e LDO 2026 (meta de primário e banda), LC 101/2000 arts. 19 e 20
   (limites de pessoal), Resolução do Senado 40/2001 (dívida dos estados), Constituição e
   LC 141 (mínimos de saúde e educação, para a despesa por função dos estados).
5. **Calendário de divulgações.** A API de calendário do IBGE (`servicodados`) derruba a conexão
   de fora do Brasil (daqui e do Actions). No PC: abrir
   `https://servicodados.ibge.gov.br/api/v3/calendario/?qtd=20` no navegador e ver se responde
   com `Access-Control-Allow-Origin`; se sim, o navegador do visitante pode buscar direto.

## Próximos passos, em ordem (dá para fazer na nuvem)

1. **Conferir o site no ar** depois do primeiro deploy: o build do Actions roda a frio (sem
   cache) e leva uns 3 minutos; ver se as onze seções saíram e se a busca acha.
2. **O que faltou do Econvitals:** serviços subjacentes (achar o código SGS), Caged por setor
   (achar fonte com nome legível), taxa de investimento e de poupança, consumo das famílias +
   investimento (a "demanda privada"), PIB por pessoa ocupada. Lista no [PROPOSTAS](PROPOSTAS.md).
3. **Estados no tempo.** A ficha é uma foto. Faltam a série de cada estado contra o Brasil, a
   nota CAPAG, a previdência do estado (RREO Anexo 04). Cuidado com o custo: cada período a
   mais são 54 chamadas ao SICONFI; usar só o 3º quadrimestre de cada ano.
4. **Arrecadação federal por tributo** (RTN aba 1.1 ou o CSV da Receita) e **carga tributária**.
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

## Para conferir antes de mostrar

```bash
cd builder && uv run ruff check src tests && uv run ruff format --check src tests \
  && uv run mypy && uv run pytest -q && uv run sacibras build
cd web && npm run build
```

Depois, olhar a 390 e a 1280 px com tudo aberto (regra no `CLAUDE.md`).
