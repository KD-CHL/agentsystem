#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
npm --prefix frontend install
npm --prefix frontend run build
mkdir -p data/artifacts data/workspaces
.venv/bin/alembic upgrade head

printf 'AgentSystem is ready. Start it with scripts/dev.sh\n'
