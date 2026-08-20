# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Builder: resolve dependencies with uv into a self-contained virtualenv.
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /build

# Install dependencies first so this layer is cached across source-only changes.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY src ./src
COPY README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---------------------------------------------------------------------------
# Runtime: slim image, non-root user, no build toolchain.
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

RUN groupadd --system app && useradd --system --gid app --home-dir /app --create-home app

WORKDIR /app

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=builder --chown=app:app /build/.venv /app/.venv
COPY --chown=app:app src ./src
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app alembic.ini ./

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health/live', timeout=3).status == 200 else 1)"

ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
