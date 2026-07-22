#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

.venv/bin/alembic upgrade head

exec .venv/bin/uvicorn agentsystem.main:app --host 127.0.0.1 --port "${PORT:-8000}"
