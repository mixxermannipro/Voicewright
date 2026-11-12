#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
version=$(PYTHONPATH=src python -c 'from voicewright import __version__; print(__version__)')
name="Voicewright-${version}-linux-x86_64.tar.gz"
test "$(uname -m)" = x86_64
python -m PyInstaller --noconfirm voicewright.spec
install -m 755 packaging/linux/install.sh dist/Voicewright/install.sh
install -m 644 packaging/linux/voicewright.desktop dist/Voicewright/
install -m 644 src/voicewright/assets/icon.png dist/Voicewright/voicewright.png
install -m 644 LICENSE dist/Voicewright/
mkdir -p release
tar -C dist -czf "release/$name" Voicewright
(cd release && sha256sum "$name" > "$name.sha256")
