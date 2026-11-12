FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY horma ./horma
COPY config ./config
COPY alembic.ini ./
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"

# Sin root (el mismo usuario para api y worker)
RUN useradd --system --no-create-home horma
USER horma
EXPOSE 8000
