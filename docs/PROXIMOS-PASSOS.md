# Próximos passos

**Leia no começo da sessão e atualize no fim** (Caio, 14/11/2026). Aqui fica só o que está em
aberto: o que foi feito sai (a história está no git), as ideias em espera ficam no
[PROPOSTAS](PROPOSTAS.md) e os limites conhecidos no [PLANO](PLANO.md#12-limites-conhecidos).

Última atualização: 15/11/2026. A página inicial com gráficos e a saída dos estudos avulsos
estão no branch `ccr-bf38480b-wr13df`, à espera de ir ao `main`.

## Releituras com prazo

A lista inteira sai de `sacibras leituras --todas` (`leituras.py`); a issue `releitura` avisa.
As próximas:

- **até 24/11**: relatório do 5º bimestre (sai até 22/11) → `leis.AVALIACOES_2026` e
  `relatorios.RECEITA_PREVISTA`.
- **até 03/12**: nota fiscal do BC → `relatorios.ELASTICIDADES`.
- **até 23/12**: resolução do Senado que fixa a CBS de 2027 → `CBS_REFERENCIA_2027` e o texto
  "o Senado ainda fixa" em `impostos.py`.
- **até 31/12**: RPM de dezembro → modelos e faixa do efeito da Selic.

## Só do PC

- Planalto: EC 132 e LC 214 no texto compilado (até 15/12), LDO 2027 (até 15/01) e o acórdão
  do TCU da CBS de 2027.
- Nota de crédito no `sisweb.tesouro.gov.br` (fora do ar em 14/11), para confirmar o
  histórico depois de mai/2025.
- Testar fontes que recusam a nuvem: Caged por UF (Ministério do Trabalho) e a tabela do
  SIDRA dos contribuintes da previdência.

## O que fazer, em ordem

1. **Atividade › PIB** (pedido do Caio em 14/11/2026, à espera do "pode"): o gráfico do PIB
   pela oferta no tempo (agropecuária, indústria, serviços; dado já baixado) e a demanda
   privada do Econvitals (consumo das famílias + investimento, pesados pelo tamanho em reais;
   conta nossa, dita na nota). Detalhe no [PROPOSTAS](PROPOSTAS.md), em Atividade.
2. **Efeito da Selic**: atalho em Inflação e em Contas públicas, ciclos alinhados pelo
   primeiro corte. (Atividade e crédito do boxe de mar/2026 não entram: estudo de uma vez só.)
3. **Riscos**: juro real do Brasil menos o dos EUA, hiato de crédito na régua da própria
   história, taxa implícita da DBGG, bloco jurídico (Anexo de Riscos Fiscais, precatórios),
   estados perto dos limites com a nota CAPAG.
4. **Estados**: mínimos de saúde e educação (SIOPS e SIOPE; o RREO não traz pela API), estados
   no tempo (só o 3º quadrimestre), CAPAG, previdência do estado.
5. O resto está no [PROPOSTAS](PROPOSTAS.md): alerta contra outros países (reservas, câmbio),
   Econvitals, Demografia, Impostos, previsões próprias, Brasil no mundo, acabamento.

## Espera o Caio

- Selo "dado anterior" na peça que ficou com o dado da véspera (o campo `mantidos` já está no
  `painel.json`).
- Tarefa agendada que relê os relatórios e abre PR ([PROPOSTAS](PROPOSTAS.md)).
