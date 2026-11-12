#!/usr/bin/env bash
# Local release build (Linux/macOS). Output: dist/
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv-build
. .venv-build/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
pyinstaller --noconfirm voicewright.spec
echo "Build finished: dist/"
