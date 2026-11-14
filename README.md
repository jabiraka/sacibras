# sacibras

A economia brasileira em uma página de gráficos: atividade, trabalho, inflação, juros e Copom,
crédito, mercados, setor externo, contas públicas, dívida, impostos e estados — atualizada
quando os números saem, com previsões ao lado do consenso de mercado.

Inspirado na arquitetura do [econvitals.org](https://econvitals.org/): um builder chama as
fontes oficiais em agenda, calcula tudo e publica JSONs pequenos junto de um site estático.
Sem banco de dados em produção.

**Estado (14/11/2026):** builder e site funcionando com dez seções de dados reais; ainda sem
deploy. O plano está em [docs/PLANO.md](docs/PLANO.md), o que vem a seguir em
[docs/PROXIMOS-PASSOS.md](docs/PROXIMOS-PASSOS.md) e as fontes testadas em
[docs/FONTES.md](docs/FONTES.md).

## Fontes

Banco Central (SGS, Focus, Copom), IBGE (SIDRA), Tesouro Nacional (Tesouro Direto), IPEADATA,
FMI (World Economic Outlook) e BIS. Cada gráfico cita a fonte e a série; cada número, a data
de referência. Dados do Tesouro Transparente sob licença ODbL.

## Rodar localmente

Por enquanto, tudo em Docker, separado de outros projetos (`name: sacibras`, porta 5434,
volumes `sb_*`):

```bash
docker compose run --rm builder   # chama as fontes e grava os JSONs (~1 min)
docker compose up web             # o site em http://localhost:5173
```

Sem Docker:

```bash
cd builder && uv sync && uv run sacibras build      # grava em web/public/data/
cd web && npm ci && npm run dev
```

Outros comandos do builder: `sacibras build --secao inflacao` (só uma seção) e
`sacibras fontes-smoke` (uma chamada a cada fonte). Verificação: `uv run ruff check src tests`,
`uv run mypy`, `uv run pytest` e, no site, `npm run build`.

## Licença

Código sob MIT. Os dados pertencem às fontes citadas.
