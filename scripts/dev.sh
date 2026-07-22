#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x .venv/bin/python ]]; then
  printf 'Run scripts/bootstrap.sh first.\n' >&2
  exit 1
fi

if [[ ! -f frontend/dist/index.html ]]; then
  npm --prefix frontend run build
fi

.venv/bin/alembic upgrade head

exec .venv/bin/uvicorn agentsystem.main:app --host 127.0.0.1 --port "${PORT:-8000}" --reload
