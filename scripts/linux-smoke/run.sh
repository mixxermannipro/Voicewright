#!/usr/bin/env bash
# Run only in an isolated Linux test container. Uses synthetic microphone audio and a private X11 display.
set -euo pipefail
if [[ $# != 3 && $# != 4 ]]; then
  echo "Usage: $0 PACKAGE.deb WHISPER-BASE.bin GERMAN-48000-STEREO-S16LE.raw [QWEN3.gguf]" >&2
  exit 2
fi
package=$(realpath "$1")
whisper_model=$(realpath "$2")
recording=$(realpath "$3")
cleanup_model=
if [[ $# == 4 ]]; then cleanup_model=$(realpath "$4"); fi
fixture_dir=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
export HOME="$work/home" XDG_DATA_HOME="$work/data" XDG_RUNTIME_DIR="$work/runtime" XDG_CACHE_HOME="$work/cache"
export XDG_SESSION_TYPE=x11 ALSA_CONFIG_PATH="$work/alsa.conf"
unset WAYLAND_DISPLAY
mkdir -m 700 "$HOME" "$XDG_RUNTIME_DIR"
mkdir -p "$XDG_DATA_HOME/de.voicewright.desktop/models" "$XDG_CACHE_HOME" "$work/package"
app_data="$XDG_DATA_HOME/de.voicewright.desktop"
trap 'kill "${app:-}" "${target:-}" "${xvfb:-}" 2>/dev/null || true; pulseaudio --kill 2>/dev/null || true; rm -rf -- "$work"' EXIT
cp "$whisper_model" "$app_data/models/ggml-base.bin"
if [[ -n "$cleanup_model" ]]; then
  cp "$cleanup_model" "$app_data/models/Qwen3-0.6B-Q8_0.gguf"
  printf '%s\n' '{"speech_language":"de","cleanup_mode":"local","fallback":false,"recording_mode":"toggle","translation":"English"}' >"$app_data/settings.json"
fi
dpkg-deb -x "$package" "$work/package"
test -x "$work/package/usr/bin/voicewright-cleanup"
cc "$fixture_dir/probe.c" $(pkg-config --cflags --libs gtk+-3.0) -o "$work/probe"
cat >"$ALSA_CONFIG_PATH" <<'ALSA'
pcm.!default {
  type pulse
  hint { show on description "Synthetic microphone" }
}
ctl.!default { type pulse }
ALSA
Xvfb -displayfd 3 -screen 0 1280x900x24 -nolisten tcp -ac 3>"$work/display" &
xvfb=$!
for _ in {1..50}; do [[ -s "$work/display" ]] && break; sleep 0.1; done
export DISPLAY=":$(cat "$work/display")"
# Rootless test containers may not support WebKit's nested sandbox. The caller isolates this test with --network=none.
export WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1
pulseaudio -n --daemonize=true --exit-idle-time=-1 \
  --load=module-native-protocol-unix \
  --load="module-pipe-source source_name=voicewright file=$work/voice.pcm format=s16le rate=48000 channels=2"
pactl set-default-source voicewright

start=$(date +%s%N)
"$work/package/usr/bin/voicewright" >"$work/app.log" 2>&1 &
app=$!
if ! timeout 30 xdotool search --sync --onlyvisible --name '^Voicewright$' >/dev/null; then
  cat "$work/app.log" >&2
  exit 1
fi
echo "Time to visible window (ms): $(( ($(date +%s%N) - start) / 1000000 ))"
sleep 2
ps -o pid,rss,comm -p "$app"
"$work/probe" "$work/result.txt" &
target=$!
window=$(timeout 10 xdotool search --sync --onlyvisible --name '^External Dictation Probe$')
xdotool windowfocus --sync "$window"
xdotool keydown ctrl keydown shift keydown space
if [[ -n "$cleanup_model" ]]; then xdotool keyup space keyup shift keyup ctrl; fi
sleep 0.4
timeout 20 python3 - "$recording" "$work/voice.pcm" <<'PY'
import sys
import time

with open(sys.argv[1], 'rb') as sample, open(sys.argv[2], 'wb', buffering=0) as mic:
    while frames := sample.read(3840):
        mic.write(frames)
        time.sleep(0.02)
PY
sleep 0.25
if [[ -n "$cleanup_model" ]]; then xdotool keydown ctrl keydown shift keydown space; fi
xdotool keyup space keyup shift keyup ctrl

needle='Morgen'
if [[ -n "$cleanup_model" ]]; then needle='morning'; fi
for _ in {1..45}; do
  if [[ -f "$work/result.txt" ]] && grep -qi "$needle" "$work/result.txt"; then
    cat "$work/result.txt"
    echo
    exit 0
  fi
  sleep 1
done
cat "$work/app.log" >&2
if [[ -f "$work/result.txt" ]]; then cat "$work/result.txt" >&2; fi
echo "Expected text did not reach the external X11 input." >&2
exit 1
