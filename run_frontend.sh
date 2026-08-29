#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec .venv/bin/python -m streamlit run frontend/streamlit_app.py --server.port 8501
