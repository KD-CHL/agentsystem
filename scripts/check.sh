#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

.venv/bin/python -m compileall -q src tests
.venv/bin/pytest -q
npm --prefix frontend test -- --run
npm --prefix frontend run build
.venv/bin/alembic current

printf 'AgentSystem quality checks passed.\n'
