#!/usr/bin/env bash
# Install this Linux bundle for the current user.
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
bin_dir="$HOME/.local/bin"
apps_dir="$HOME/.local/share/applications"
icons_dir="$HOME/.local/share/icons/hicolor/512x512/apps"
install_root="$HOME/.local/opt"

python_bin=${VOICEWRIGHT_PYTHON:-python3.11}
if ! command -v "$python_bin" >/dev/null; then
    printf 'Install Fedora prerequisites first: sudo dnf install python3.11 python3.11-devel gcc kernel-headers portaudio xcb-util-cursor xcb-util-keysyms xcb-util-wm libxkbcommon-x11 libglvnd-egl mesa-libGL
' >&2
    exit 1
fi
wheels=("$source_dir"/voicewright-*.whl)
test "${#wheels[@]}" -eq 1 && test -f "${wheels[0]}"
mkdir -p -- "$bin_dir" "$apps_dir" "$icons_dir" "$install_root"
dest=$(mktemp -d "$install_root/voicewright.XXXXXXXX")
"$python_bin" -m venv "$dest"
"$dest/bin/python" -m pip --disable-pip-version-check install \
    --index-url https://pypi.org/simple --constraint "$source_dir/constraints-linux.txt" "${wheels[0]}"
"$dest/bin/python" -m pip check
ln -sfn -- "$dest/bin/voicewright" "$bin_dir/voicewright"
install -m 644 -- "$source_dir/voicewright.png" "$icons_dir/voicewright.png"
# Desktop files expand neither $HOME nor ~ in Exec.
"$python_bin" - "$source_dir/voicewright.desktop" "$apps_dir/voicewright.desktop" "$bin_dir/voicewright" <<'PY'
import sys
from pathlib import Path

template, desktop_file, executable = sys.argv[1:]
quoted = executable.replace("%", "%%")
for char in '\\"$`':
    quoted = quoted.replace(char, "\\" + char)
quoted = ('"' + quoted + '"').replace("\\", "\\\\")
desktop = Path(template).read_text(encoding="utf-8")
Path(desktop_file).write_text(desktop.replace("Exec=voicewright", f"Exec={quoted}"), encoding="utf-8")
PY
printf 'Voicewright: %s\n' "$bin_dir/voicewright"
