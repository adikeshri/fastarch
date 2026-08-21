#!/usr/bin/env bash
# One-shot setup for a fresh clone: install deps, start infra, migrate, run tests.
# See README.md "Setup" for the same steps explained individually.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

command -v uv >/dev/null 2>&1 || {
  echo "uv not found — installing (see https://docs.astral.sh/uv/getting-started/installation/)"
  curl -LsSf https://astral.sh/uv/install.sh | sh
}

echo "==> Installing dependencies"
uv sync

if [ ! -f .env ]; then
  echo "==> Creating .env from .env.example"
  cp .env.example .env
fi

echo "==> Starting Postgres + Redis + the app + worker"
docker compose up -d --build

echo "==> Running unit tests (no infra required)"
uv run pytest tests/unit -m unit -q

echo ""
echo "Done. The API is at http://localhost:8000 (docs at /api/docs)."
echo "Run 'make test' for the full suite (needs Docker for testcontainers)."
