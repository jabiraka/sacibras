# sacibras — regras para o Claude

Painel da economia brasileira (site estático + builder em Python). O plano, as fontes testadas e
as fases estão em [docs/PLANO.md](docs/PLANO.md) — leia antes de começar.

## Dados

- **Sem banco em produção.** O builder chama as APIs e gera JSONs que vão com o site; nada de
  dado é commitado (`web/public/data/` está no `.gitignore`).
- **Bases separadas do finance_agent** (Caio, 13/11/2026). Nunca ler nem escrever no Postgres
  (`fa_postgres`, 5433) nem no Supabase dele. O Postgres local do sacibras é `sb_postgres`, porta
  5434, volume `sb_pgdata`, e serve só de cache de desenvolvimento. Código útil do finance_agent
  é copiado e adaptado, nunca importado.
- **Por enquanto, testar em Docker** (Caio, 13/11/2026): `docker compose` com `name: sacibras`.
- **Registro explícito de séries com unidade** em `builder/src/sacibras/catalogo.py`. Série nova
  só entra depois de conferida no catálogo da fonte (para o SGS:
  `dadosabertos.bcb.gov.br/api/3/action/package_search?fq=codigo_sgs:N`), com a data no comentário.
- **O site da B3 fica desligado** (`SB_B3`), pendente de decisão do Caio: a B3 veda coleta
  automatizada no texto do site (lido em 14/11/2026, [docs/FONTES.md](docs/FONTES.md)). Não
  ligar no workflow nem no compose sem o "sim" dele.
- **Fonte oficial e citada** em todo gráfico. Número de lei (meta de inflação, limites da LRF,
  reforma tributária) vem da lei lida.

## Tela

- PT-BR e formato brasileiro: `R$ 1,2 tri`, `4,5 %`, `out/2026`, `3º tri/2026`.
- Previsão nunca sozinha: consenso (Focus) ao lado, faixa de erro e o método em uma frase.
- Cada número com data de referência.

## Verificação antes de mostrar

```bash
cd builder && uv run ruff check src tests && uv run ruff format --check src tests \
  && uv run mypy && uv run pytest -q
cd web && npm run build          # tsc + vite
```

Mexeu em gráfico, cartão ou cor? Rode o builder, abra o site e olhe a 390 e a 1280 px, nos
dois temas. As seis cores de série (`--serie-1` a `--serie-6` em `web/src/estilo.css`)
passaram num validador de paleta para daltônicos; trocar uma pede validar de novo.

## Git

- O `.env` nunca vai ao git.
- Depois de cada commit, `git show --stat HEAD` (o OneDrive já desfez arquivo sozinho no
  finance_agent).
