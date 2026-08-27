# Not wired into docker-compose.yml yet -- Phase 1 runs the app on the host
# against the compose Postgres/Redis for a faster dev loop. Built now so a
# later phase can add an `app` service without starting from scratch.
FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
