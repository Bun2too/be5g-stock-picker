#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
WEB_DIR="$ROOT_DIR/apps/web"

python3 -m venv "$API_DIR/.venv"
source "$API_DIR/.venv/bin/activate"
pip install --upgrade pip
pip install -r "$API_DIR/requirements.txt"

cd "$WEB_DIR"
npm install

echo "Setup complete."
