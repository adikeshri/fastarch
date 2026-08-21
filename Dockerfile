# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Builder: resolve dependencies with uv into a self-contained virtualenv.
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install dependencies first so this layer is cached across source-only changes.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY src ./src
COPY README.md LICENSE ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---------------------------------------------------------------------------
# Runtime: slim image, non-root user, no build toolchain.
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

# Pull in whatever OS security patches have landed since this base image tag
# was last rebuilt (the tag itself is a moving target, but not necessarily
# rebuilt as often as Debian ships fixes) — otherwise the image can ship
# known-fixed CVEs (e.g. util-linux) on day one.
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# The base image's system pip (and its vendored copies of msgpack,
# pkg_resources/setuptools, etc. under pip/_vendor/) is never used here — the
# app runs entirely out of the venv copied in below via uv — so drop it
# rather than ship known vulnerabilities in code nothing calls.
RUN rm -rf /usr/local/lib/python3.13/site-packages/pip* \
    /usr/local/lib/python3.13/ensurepip

RUN groupadd --system app && useradd --system --gid app --home-dir /app --create-home app

WORKDIR /app

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app src ./src
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app alembic.ini ./

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health/live', timeout=3).status == 200 else 1)"

ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
