#!/usr/bin/env bash
# Real X11 insertion probe for Unicode, emoji and paragraphs.
#
# Run only in an isolated Linux container that provides Rust, GTK 3 development
# headers, Xvfb, xdotool and a C compiler (the voxtakt-build image has all of
# them). The script starts a private X server, focuses a GTK multiline widget
# and lets the real insertion module type into it. It never touches the
# caller's display.
set -euo pipefail

script_dir=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$script_dir/../.." && pwd)
work=$(mktemp -d)
export XDG_SESSION_TYPE=x11
unset WAYLAND_DISPLAY
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$work/target}"

cleanup() {
  kill "${probe:-}" "${xvfb:-}" 2>/dev/null || true
  rm -rf -- "$work"
}
trap cleanup EXIT

text=$'Grüße aus Köln.\nZweiter Absatz 😀 🇩🇪👨‍👩‍👧‍👦 – ß, é, €.'
printf '%s' "$text" >"$work/expected.txt"

cargo build --quiet --manifest-path "$root/src-tauri/Cargo.toml" --locked \
  --example x11_insertion_probe
cc "$script_dir/probe-multiline.c" $(pkg-config --cflags --libs gtk+-3.0) \
  -o "$work/probe-multiline"

Xvfb -displayfd 3 -screen 0 1280x900x24 -nolisten tcp -ac 3>"$work/display" &
xvfb=$!
for _ in {1..50}; do [[ -s "$work/display" ]] && break; sleep 0.1; done
export DISPLAY=":$(cat "$work/display")"

"$work/probe-multiline" "$work/result.txt" >"$work/probe.log" 2>&1 &
probe=$!
window=$(timeout 10 xdotool search --sync --onlyvisible \
  --name '^External Multiline Probe$' | head -n1)
xdotool windowfocus --sync "$window"
sleep 0.3

"$CARGO_TARGET_DIR/debug/examples/x11_insertion_probe" "$text"

for _ in {1..50}; do
  if [[ -f "$work/result.txt" ]] && cmp -s "$work/expected.txt" "$work/result.txt"; then
    cat "$work/result.txt"
    echo
    echo "X11 insertion probe passed."
    exit 0
  fi
  sleep 0.1
done

echo "Expected text did not reach the GTK multiline widget." >&2
if [[ -f "$work/result.txt" ]]; then
  echo "Actual text:" >&2
  cat "$work/result.txt" >&2
  echo >&2
fi
cat "$work/probe.log" >&2
exit 1
