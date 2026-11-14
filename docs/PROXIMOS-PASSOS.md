# Próximos passos

**Leia isto no começo de cada sessão e atualize no fim** (Caio, 14/11/2026: *"deixe os próximos
passos sempre anotado num .md, assim a próxima sessão sabe o que fazer"*). O plano inteiro está
no [PLANO](PLANO.md); as fontes testadas, em [FONTES](FONTES.md). Aqui fica só o que vem a
seguir, em ordem, e o que espera decisão.

Última atualização: 14/11/2026.

---

## Onde paramos

- Trabalho no branch `ccr-615b3774-yyp5n8` (CI verde). **Ainda não está no `main` nem no ar.**
- O site tem a página inicial ("Status da economia brasileira", seis números, o IPCA contra a
  meta) e onze assuntos: atividade, trabalho, inflação, juros e Copom, crédito, mercados, setor
  externo, contas públicas e dívida, estados (com o mapa do Brasil), Brasil no mundo e
  previsões.
- Tema só claro. Sem "Anterior"/"Próximo": só o "Voltar".
- Prévia privada (dados de 14/11/2026): https://claude.ai/artifact/YPR6sEPLQNHPSkzxektAMS —
  republicar depois de mudança visível na tela.

## Esperando decisão do Caio

1. **Publicar.** Juntar o branch no `main` e ligar o Pages (Settings → Pages → Source: GitHub
   Actions). O workflow `build-deploy.yml` já gera e publica a cada push no `main` e duas vezes
   por dia útil. A sessão não pode mandar ao `main` sem o "sim"; pode abrir o PR.
2. **B3: ligar ou não** (`SB_B3`). O site da B3 veda coleta automatizada. Desligado, o
   Ibovespa vem do IPEADATA (um dia de atraso). Ligado, entram índices setoriais e futuros.
   Recomendação: deixar desligado até ter autorização. Detalhe em [FONTES](FONTES.md).
3. **Normas que faltam ler.** O Planalto não abre de fora do Brasil. Se o Caio colar os
   trechos, entram na tela: LC 200/2023 e LDO 2026 (meta de primário e banda), LC 101/2000
   arts. 19 e 20 (limites de pessoal), Resolução do Senado 40/2001 (dívida dos estados).

## Próximos passos, em ordem

1. **Rodar o teste das fontes de dentro do Actions** (`fontes-smoke.yml`, "Run workflow").
   Os runners ficam nos EUA: pode aparecer bloqueio que daqui não aparece (o IBGE `servicodados`
   já bloqueia). Anotar o resultado em [FONTES](FONTES.md).
2. **O ponto mais recente direto do navegador.** O site lê os JSONs do builder; SGS, Focus,
   SIDRA e IPEADATA têm CORS aberto, então o navegador pode buscar o último valor e trocar o
   número se for mais novo. Começar pelos seis números da página inicial.
3. **Calendário de divulgações.** Próximas divulgações (IBGE, Copom, Focus às segundas) e o que
   saiu nos últimos 7 dias. A API de calendário do IBGE não abre de fora do Brasil: testar do
   navegador. As datas do Copom não têm API: hoje o gráfico da Selic aproxima o mês da reunião.
4. **Estados no tempo.** Hoje o assunto é uma foto do último período. Faltam a série de cada
   estado, ICMS (RREO Anexo 03), resultado primário (RREO Anexo 06) e a nota CAPAG (CSV do
   Tesouro). Campos já anotados em [FONTES](FONTES.md).
5. **Arrecadação federal por tributo** (RTN aba 1.1 ou o CSV da Receita) e **carga tributária**.
6. **Previsões próprias que faltam:** IPCA e desocupação com modelo sazonal; "o que mudou desde
   a última leitura" no PIB agora (precisa guardar a leitura anterior, por exemplo no cache do
   Actions); PIB agora com indústria, varejo e serviços além do IBC-Br. Sempre ao lado do Focus,
   com faixa de erro e o método numa frase.
7. **Brasil no mundo:** câmbio e bolsa no ano, juro de 10 anos (OCDE), inflação mensal.
8. **Acabamento:** "novo desde sua última visita", PNG dos gráficos, imagem de compartilhamento,
   domínio.

## Guardado para depois

- **Simulador da dívida** (Caio, 14/11/2026: *"tire 'a sua simulação' nos gráficos por
  enquanto, deixe anotado pra incluirmos no futuro, vamos deixar só de fontes que temos"*).
  Está pronto e testado, só fora da tela: a conta em `builder/src/sacibras/modelos/divida.py`,
  a linha de base em `secoes/previsoes.py` (`_simulador`), a tela em `web/src/simulador.ts`.
  Para religar: `MOSTRAR_SIMULADOR = True` em `secoes/previsoes.py` e tirar o teste
  `test_simulador_fica_fora_da_tela_por_enquanto`. Só com o "sim" do Caio.

## Limites conhecidos

- O "PIB agora" é estimativa própria (reta com o IBC-Br), mostrada ao lado do Focus. Com só dois
  meses do trimestre, o erro real é maior que o erro típico medido.
- O histórico de acerto do Focus compara com o dado revisado de hoje, não com o da época.
- A participação da dívida por indexador não traz o IPCA no SGS: "índices de preços" é o que
  falta para 100 %.
- O RTN sai com uns dois meses de atraso; o RGF dos estados, por quadrimestre (o 3º de 2026
  ainda vazio).
- O build a frio (sem cache) faz ~54 chamadas ao SICONFI e ~60 ao Focus; não foi medido.

## Para conferir antes de mostrar

```bash
cd builder && uv run ruff check src tests && uv run ruff format --check src tests \
  && uv run mypy && uv run pytest -q && uv run sacibras build
cd web && npm run build
```

Depois, olhar a 390 e a 1280 px com tudo aberto (regra no `CLAUDE.md`).
