# sacibras

A economia brasileira em uma página de gráficos: atividade, trabalho, inflação, juros e Copom,
crédito, mercados, setor externo, contas públicas, dívida, impostos e estados — atualizada
quando os números saem, com previsões ao lado do consenso de mercado.

Inspirado na arquitetura do [econvitals.org](https://econvitals.org/): um builder chama as
fontes oficiais em agenda, calcula tudo e publica JSONs pequenos junto de um site estático.
Sem banco de dados em produção.

**Estado:** planejamento. O plano completo está em [docs/PLANO.md](docs/PLANO.md).

## Fontes

Banco Central (SGS, Focus), IBGE (SIDRA), Tesouro Nacional (SICONFI, Tesouro Transparente,
RTN, Dívida Pública Federal), Receita Federal, B3 e IPEADATA. Cada gráfico cita a fonte, a
série e a data da leitura. Dados do Tesouro Transparente sob licença ODbL.

## Rodar localmente

Por enquanto, tudo em Docker, separado de outros projetos (porta 5434, volume `sb_pgdata`):

```bash
cp .env.example .env
docker compose up -d db
```

O builder e o site entram no compose na Fase 0 do plano.

## Licença

Código sob MIT. Os dados pertencem às fontes citadas.
