# O builder: chama as fontes e grava os JSONs do site em /dados.
FROM python:3.12-slim

RUN pip install --no-cache-dir uv
WORKDIR /app/builder

# Dependências primeiro, para o cache do Docker sobreviver a mudanças no código.
COPY builder/pyproject.toml builder/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY builder/src ./src
RUN uv sync --frozen --no-dev

ENV SB_CACHE_DIR=/cache
VOLUME ["/cache", "/dados"]
CMD ["uv", "run", "--no-dev", "sacibras", "build", "--saida", "/dados", "--tolerante"]
