FROM node:24-bookworm-slim AS node
FROM ghcr.io/astral-sh/uv:0.12.19 AS uv
FROM python:3.12-slim-bookworm

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=uv /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends git libstdc++6 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/plotloom-dependencies
COPY pyproject.toml uv.lock ./
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_PYTHON_DOWNLOADS=never
RUN uv sync --locked --no-dev --no-install-project
COPY services/creator_workbench /opt/plotloom-service
RUN chmod +x /opt/plotloom-service/codex \
    && ln -s /opt/plotloom-service/codex /usr/local/bin/codex
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
CMD ["python", "/opt/plotloom-service/server.py"]
