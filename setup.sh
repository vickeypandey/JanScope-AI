#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if command -v python3.13 >/dev/null 2>&1; then
  JANSCOPE_PYTHON=python3.13
elif command -v python3.12 >/dev/null 2>&1; then
  JANSCOPE_PYTHON=python3.12
else
  echo "Python 3.13 or 3.12 is required."
  exit 1
fi
"$JANSCOPE_PYTHON" -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -r requirements.txt
test -f .env || cp .env.example .env
.venv/bin/python scripts/init_db.py
echo "Setup complete. Run ./run_backend.sh and ./run_frontend.sh"
