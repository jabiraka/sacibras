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

## Resolvido no PC em 14/11/2026

- **Pages ligado** pela API (Source: GitHub Actions): o site está em
  https://jabiraka.github.io/sacibras/, com as onze seções saindo `ok` no primeiro deploy.
- **B3 fica desligada** (`SB_B3`), decisão do Caio.
- **Séries fora do CKAN do BC** (27863, 27864): a saída da regra no `CLAUDE.md` foi aprovada.
- **Normas lidas** no Planalto e no Senado (trechos em `leis.py`): os limites de pessoal (LRF,
  arts. 19, 20, 22 e 59) e de dívida (Resolução do Senado 40/2001) dos estados agora vêm da lei,
  com o artigo na descrição, e o estado cujo RGF traz outro limite é nomeado; a meta de primário
  de 2026 (LDO, art. 2º) está registrada, fora da tela (abaixo); os mínimos de saúde (LC 141,
  art. 6º) e de educação (Constituição, art. 212) estão anotados.
- **Calendário do IBGE**: do Brasil responde com CORS `*`. Cada assunto mostra a próxima
  divulgação das pesquisas dele (`web/src/calendario.ts`), buscada pelo navegador.

## Esperando decisão do Caio

1. **Meta de primário na tela: como mostrar.** A LDO 2026 foi lida: meta de R$ 34,3 bi, piso
   R$ 0, teto R$ 68,5 bi (`leis.META_PRIMARIA_2026`); a LC 200 diz que quem apura é o BC. O
   primário do Governo Central no BC (SGS 4639, ainda fora do catálogo) dá déficit de R$ 52,7 bi
   em 12 meses até set/2026 e de R$ 93,6 bi no ano. Mas a apuração oficial desconta despesas que
   outras normas tiram da meta (EC 136/2025, LCs 221, 223 e 235: R$ 67,3 bi no 4º bimestre,
   segundo a nota da Consultoria de Orçamento do Senado de 25/09/2026). O número cru diria
   "abaixo do piso". Opções: (a) a meta contra o resultado "para fins de meta" do relatório
   bimestral, lido à mão a cada dois meses; (b) o número do BC contra a meta, com o desconto em
   reais dito ao lado; (c) fora da tela.

## Próximos passos, em ordem (dá para fazer na nuvem)

1. **Mínimos de saúde e educação dos estados**: o RREO Anexo 12 (saúde) e o Anexo 08
   (educação) trazem o percentual apurado sobre a base que a lei manda; as normas já estão
   lidas (`leis.py`). Na ficha do estado, contra 12 % e 25 %.
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
- O calendário mostra só o dia da divulgação: a API traz a hora sem dizer o fuso. Se a API do
  IBGE não responder em 6 s, a linha não aparece.

## Para conferir antes de mostrar

```bash
cd builder && uv run ruff check src tests && uv run ruff format --check src tests \
  && uv run mypy && uv run pytest -q && uv run sacibras build
cd web && npm run build
```

Depois, olhar a 390 e a 1280 px com tudo aberto (regra no `CLAUDE.md`).
