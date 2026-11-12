#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
version=$(PYTHONPATH=src python -c 'from voicewright import __version__; print(__version__)')
name="Voicewright-${version}-linux-x86_64.tar.gz"
test "$(uname -m)" = x86_64
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
bundle="$scratch/Voicewright"
mkdir -p -- "$bundle" release
python -m pip wheel --no-deps --wheel-dir "$bundle" .
python -m pip freeze > "$bundle/constraints-linux.txt"
install -m 755 packaging/linux/install.sh "$bundle/"
install -m 644 packaging/linux/voicewright.desktop LICENSE README.md "$bundle/"
install -m 644 src/voicewright/assets/icon.png "$bundle/voicewright.png"
tar -C "$scratch" -czf "release/$name" Voicewright
(cd release && sha256sum "$name" > "$name.sha256")
