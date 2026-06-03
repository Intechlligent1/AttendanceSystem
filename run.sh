#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"

cd "$PROJECT_DIR"

if [[ ! -x "$PYTHON_BIN" || ! -x "$PIP_BIN" ]]; then
    echo "Virtual environment is missing or incomplete."
    echo "Install venv support and create it with:"
    echo
    echo "  sudo apt install python3.12-venv"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

exec "$PYTHON_BIN" app.py
