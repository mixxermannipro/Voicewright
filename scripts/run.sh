#!/usr/bin/env bash
# Start Voicewright from source (Linux/macOS). Creates a venv on first run.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -e .
fi
exec .venv/bin/python -m voicewright "$@"
