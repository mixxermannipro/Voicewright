#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install -e .
printf 'Start with .venv/bin/voicewright. On Wayland use a desktop shortcut for --toggle.\n'
