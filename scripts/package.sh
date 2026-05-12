#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
WEB_DIR="$ROOT_DIR/apps/web"
BUILD_DIR="$ROOT_DIR/build"

if [[ ! -x "$API_DIR/.venv/bin/python" ]]; then
  echo "Backend virtualenv not found. Run 'make setup' first."
  exit 1
fi

if [[ ! -d "$WEB_DIR/node_modules" ]]; then
  echo "Frontend dependencies not found. Run 'make setup' first."
  exit 1
fi

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

(
  cd "$WEB_DIR"
  npm run build
)

cp -R "$WEB_DIR/dist" "$BUILD_DIR/web-dist"
tar \
  --exclude=".venv" \
  --exclude="__pycache__" \
  --exclude=".pytest_cache" \
  --exclude="tests/__pycache__" \
  -czf "$BUILD_DIR/api-source.tgz" \
  -C "$API_DIR" .

echo "Artifacts created in $BUILD_DIR"
