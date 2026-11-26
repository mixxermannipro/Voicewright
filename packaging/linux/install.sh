#!/usr/bin/env bash
# Install this Linux bundle for the current user.
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
bin_dir="$HOME/.local/bin"
apps_dir="$HOME/.local/share/applications"
icons_dir="$HOME/.local/share/icons/hicolor/512x512/apps"
install_root="$HOME/.local/opt"

# Voicewright supports Python 3.11 to 3.14. Fedora 45's default python3 is
# 3.15, which is too new, so install python3.14 explicitly; older releases
# ship a compatible python3. This search prefers the explicit versions.
find_python() {
    local candidate
    for candidate in "${VOICEWRIGHT_PYTHON:-}" python3.14 python3.13 python3.12 python3.11 python3; do
        [[ -n "$candidate" ]] || continue
        command -v "$candidate" >/dev/null 2>&1 || continue
        if "$candidate" -c 'import sys; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 15) else 1)' 2>/dev/null; then
            command -v "$candidate"
            return 0
        fi
    done
    return 1
}
if ! python_bin=$(find_python); then
    printf 'Voicewright needs Python 3.11 to 3.14, but no compatible interpreter was found.\n On Fedora 45 (default python3 is 3.15) install 3.14 explicitly:\n  sudo dnf install python3.14 python3.14-devel gcc kernel-headers portaudio xcb-util-cursor xcb-util-keysyms xcb-util-wm libxkbcommon-x11 libglvnd-egl mesa-libGL\n On older Fedora releases use python3.13, python3.12 or python3.11 instead.\n Or point VOICEWRIGHT_PYTHON at a compatible interpreter.\n' >&2
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
