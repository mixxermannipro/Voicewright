#!/usr/bin/env bash
set -euo pipefail
archive=$(realpath "$1")
scratch=$(mktemp -d)
app_pid=
cleanup() {
    if [[ -n "$app_pid" ]]; then kill "$app_pid" 2>/dev/null || true; fi
    rm -rf -- "$scratch"
}
trap cleanup EXIT
export HOME="$scratch/home with spaces"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_RUNTIME_DIR="$scratch/runtime"
export XDG_SESSION_TYPE=x11 QT_QPA_PLATFORM=xcb
mkdir -m 700 -p -- "$HOME" "$XDG_RUNTIME_DIR"
tar -xzf "$archive" -C "$scratch"
bash "$scratch/Voicewright/install.sh"
app="$HOME/.local/bin/voicewright"
version=$(PYTHONPATH=src python3 -c 'from voicewright import __version__; print(__version__)')
[[ "$("$app" --version)" == "Voicewright $version" ]]
"$app" >"$scratch/startup.log" 2>&1 &
app_pid=$!
for _ in {1..40}; do
    if ! kill -0 "$app_pid" 2>/dev/null; then cat "$scratch/startup.log"; exit 1; fi
    if grep -q 'Hotkey backend: pynput' "$scratch/startup.log"; then break; fi
    sleep .25
done
cat "$scratch/startup.log"
grep -q 'Hotkey backend: pynput' "$scratch/startup.log"
timeout 10 "$app" --quit
for _ in {1..40}; do
    if ! kill -0 "$app_pid" 2>/dev/null; then
        wait "$app_pid"
        app_pid=
        echo 'Installed application started and accepted its quit command.'
        exit 0
    fi
    sleep .25
done
exit 1
