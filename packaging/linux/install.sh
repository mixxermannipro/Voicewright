#!/usr/bin/env bash
# Install this Linux bundle for the current user.
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
bin_dir="$HOME/.local/bin"
apps_dir="$HOME/.local/share/applications"
icons_dir="$HOME/.local/share/icons/hicolor/512x512/apps"
install_root="$HOME/.local/opt"

test -x "$source_dir/voicewright"
test -d "$source_dir/_internal"
mkdir -p -- "$bin_dir" "$apps_dir" "$icons_dir" "$install_root"
dest=$(mktemp -d "$install_root/voicewright.XXXXXXXX")
cp -a -- "$source_dir/voicewright" "$source_dir/_internal" "$dest/"
ln -sfn -- "$dest/voicewright" "$bin_dir/voicewright"
install -m 644 -- "$source_dir/voicewright.png" "$icons_dir/voicewright.png"
# Desktop files expand neither $HOME nor ~ in Exec.
python3 - "$source_dir/voicewright.desktop" "$apps_dir/voicewright.desktop" "$bin_dir/voicewright" <<'PY'
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
