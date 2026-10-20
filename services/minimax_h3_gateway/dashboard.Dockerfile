FROM ghcr.io/astral-sh/uv:0.13.1 AS uv
FROM python:3.12-slim
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_PYTHON_DOWNLOADS=never
RUN uv sync --locked --no-dev --no-install-project
COPY services/minimax_h3_gateway/src/plotloom_h3_gateway/__init__.py services/minimax_h3_gateway/src/plotloom_h3_gateway/contracts.py services/minimax_h3_gateway/src/plotloom_h3_gateway/naming.py /app/src/plotloom_h3_gateway/
COPY services/minimax_h3_gateway/src/plotloom_h3_gateway/dashboard /app/src/plotloom_h3_gateway/dashboard
ENV PATH="/opt/venv/bin:$PATH" PYTHONPATH=/app/src PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 1000:1000
CMD ["python", "-m", "plotloom_h3_gateway.dashboard"]
