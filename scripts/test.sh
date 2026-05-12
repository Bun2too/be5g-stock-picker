#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
WEB_DIR="$ROOT_DIR/apps/web"

if [[ ! -x "$API_DIR/.venv/bin/python" ]]; then
  echo "Backend virtualenv not found. Run 'make setup' first."
  exit 1
fi

if [[ ! -d "$WEB_DIR/node_modules" ]]; then
  echo "Frontend dependencies not found. Run 'make setup' first."
  exit 1
fi

(
  cd "$API_DIR"
  source .venv/bin/activate
  PYTHONPATH=. pytest
)

(
  cd "$WEB_DIR"
  npm run test -- --run
)
