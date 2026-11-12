#!/usr/bin/env bash
# Run Voicewright from source on Fedora (also works on most other distros with tweaks).
set -euo pipefail
cd "$(dirname "$0")/.."
sudo dnf install -y python3 python3-devel gcc portaudio portaudio-devel \
  wl-clipboard ydotool xdotool xcb-util-cursor kernel-headers
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -e .
echo
echo "Optional for Wayland:"
echo "  sudo usermod -aG input \$USER && sudo systemctl enable --now ydotool"
echo "Start:  .venv/bin/voicewright   (or ./scripts/run.sh)"
