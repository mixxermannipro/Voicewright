#!/usr/bin/env bash
# Real X11 insertion probe for Unicode, emoji and paragraphs.
#
# Run only in an isolated Linux container that provides Rust, GTK 3 development
# headers, Xvfb, xdotool and a C compiler (the voxtakt-build image has all of
# them). The script starts a private X server, focuses a GTK multiline widget
# and lets the real insertion module type into it. It never touches the
# caller's display.
set -euo pipefail

# Always create our own bus. Neither metadata lookup nor GTK may use the
# contributor's accessibility bus; this is not a user permission bypass.
if [[ "${VOICEWRIGHT_PRIVATE_TEST_BUS:-}" != 1 ]]; then
  exec dbus-run-session -- env VOICEWRIGHT_PRIVATE_TEST_BUS=1 bash "$0" "$@"
fi

script_dir=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$script_dir/../.." && pwd)
work=$(mktemp -d)
export XDG_SESSION_TYPE=x11
unset WAYLAND_DISPLAY
unset AT_SPI_BUS_ADDRESS
export GTK_MODULES=atk-bridge
export NO_AT_BRIDGE=0
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$work/target}"

cleanup() {
  kill "${probe:-}" "${xvfb:-}" "${inserter:-}" 2>/dev/null || true
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

launch_probe() {
  "$work/probe-multiline" "$work/result.txt" "$1" >"$work/probe.log" 2>&1 &
  probe=$!
  window=$(timeout 10 xdotool search --sync --onlyvisible \
    --name '^External Multiline Probe$' | head -n1)
  xdotool windowfocus --sync "$window"
  sleep 0.5
}

stop_probe() {
  kill "$probe"
  wait "$probe" 2>/dev/null || true
}

launch_probe multiline

"$CARGO_TARGET_DIR/debug/examples/x11_insertion_probe" "$text"

for _ in {1..50}; do
  if [[ -f "$work/result.txt" ]] && cmp -s "$work/expected.txt" "$work/result.txt"; then
    cat "$work/result.txt"
    echo
    break
  fi
  sleep 0.1
done

if ! cmp -s "$work/expected.txt" "$work/result.txt"; then
  echo "Expected text did not reach the GTK multiline widget." >&2
  cat "$work/probe.log" >&2
  exit 1
fi
if [[ -f "$work/result.txt.enter" ]]; then
  echo "A paragraph generated Return; a chat widget could submit it." >&2
  exit 1
fi
stop_probe

expect_blocked() {
  if "$CARGO_TARGET_DIR/debug/examples/x11_insertion_probe" "$1" \
      >"$work/blocked.log" 2>&1; then
    echo "Unsafe insertion unexpectedly succeeded." >&2
    exit 1
  fi
  grep -F "$2" "$work/blocked.log"
}

launch_probe password
expect_blocked "$text" "no verified editable X11 text field"
test ! -s "$work/result.txt"
stop_probe

launch_probe single
"$CARGO_TARGET_DIR/debug/examples/x11_insertion_probe" "synthetic single line"
printf '%s' "synthetic single line" >"$work/single-expected.txt"
cmp -s "$work/single-expected.txt" "$work/result.txt"
expect_blocked "$text" "Paragraphs require the safe copy path"
cmp -s "$work/single-expected.txt" "$work/result.txt"
stop_probe

# Do not destroy an existing selection; preserve the original synthetic text.
launch_probe multiline
"$CARGO_TARGET_DIR/debug/examples/x11_insertion_probe" "synthetic selection"
printf '%s' "synthetic selection" >"$work/selection-expected.txt"
xdotool key --clearmodifiers ctrl+a
sleep 0.1
expect_blocked "must not replace selection" "The target changed"
cmp -s "$work/selection-expected.txt" "$work/result.txt"
stop_probe

# A real field change in the same GTK window must invalidate the saved target.
launch_probe switch
VOICEWRIGHT_PROBE_CAPTURED="$work/captured" VOICEWRIGHT_PROBE_RELEASE="$work/release" \
  "$CARGO_TARGET_DIR/debug/examples/x11_insertion_probe" "synthetic field switch" \
  >"$work/switch.log" 2>&1 &
inserter=$!
for _ in {1..50}; do [[ -f "$work/captured" ]] && break; sleep 0.1; done
test -f "$work/captured"
xdotool key --clearmodifiers Tab
sleep 0.1
touch "$work/release"
if wait "$inserter"; then
  echo "Insertion after same-window field switch unexpectedly succeeded." >&2
  exit 1
fi
grep -F "The target changed" "$work/switch.log"
test ! -s "$work/result.txt"
stop_probe

launch_probe multiline
DBUS_SESSION_BUS_ADDRESS="unix:path=$work/missing-bus" \
  expect_blocked "synthetic unavailable bus" "no verified editable X11 text field"
test ! -s "$work/result.txt"
stop_probe

echo "X11 Unicode, password, single-line, field-switch and unavailable-bus probes passed."
exit 0
