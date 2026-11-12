#!/usr/bin/env bash
set -euo pipefail
archive=$(realpath "$1")
model=$(realpath "$2")
scratch=$(mktemp -d)
app_pid=
pulse_pid=
cleanup() {
    if [[ -n "$app_pid" ]]; then kill "$app_pid" 2>/dev/null || true; fi
    if [[ -n "$pulse_pid" ]]; then kill "$pulse_pid" 2>/dev/null || true; fi
    rm -rf -- "$scratch"
}
trap cleanup EXIT
export HOME="$scratch/home with spaces"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_RUNTIME_DIR="$scratch/runtime"
export VOICEWRIGHT_CONFIG_DIR="$scratch/config"
export VOICEWRIGHT_DATA_DIR="$scratch/data"
# Model Fedora Wayland's desktop-managed shortcut via IPC, with a virtual X
# display for Qt's XWayland clipboard path.
export XDG_SESSION_TYPE=wayland QT_QPA_PLATFORM=xcb
export PULSE_SERVER="unix:$scratch/pulse.sock"
export ALSA_CONFIG_PATH="$scratch/asound.conf"
mkdir -m 700 -p -- "$HOME" "$XDG_RUNTIME_DIR" "$VOICEWRIGHT_CONFIG_DIR" "$VOICEWRIGHT_DATA_DIR/models"
cp -r -- "$model" "$VOICEWRIGHT_DATA_DIR/models/tiny"
cat > "$VOICEWRIGHT_CONFIG_DIR/config.json" <<'JSON'
{"whisper_model":"tiny","whisper_device":"cpu","sounds_enabled":false,"add_trailing_space":false}
JSON
cat > "$scratch/asound.conf" <<'ALSA'
pcm.!default {
    type pulse
}
ctl.!default {
    type pulse
}
ALSA
cat > "$scratch/pulse.conf" <<PULSE
load-module module-native-protocol-unix socket=$scratch/pulse.sock auth-anonymous=1
load-module module-null-sink sink_name=voicewright_fixture rate=16000 channels=1
set-default-sink voicewright_fixture
set-default-source voicewright_fixture.monitor
PULSE
pulseaudio -n -F "$scratch/pulse.conf" --daemonize=no --exit-idle-time=-1 >"$scratch/pulse.log" 2>&1 &
pulse_pid=$!
for _ in {1..40}; do
    if pactl info >/dev/null 2>&1; then break; fi
    sleep .25
done
pactl info >/dev/null || { cat "$scratch/pulse.log"; exit 1; }
tar -xzf "$archive" -C "$scratch"
bash "$scratch/Voicewright/install.sh"
app="$HOME/.local/bin/voicewright"
version=$(PYTHONPATH=src python3.11 -c 'from voicewright import __version__; print(__version__)')
[[ "$("$app" --version)" == "Voicewright $version" ]]
"$app" >"$scratch/startup.log" 2>&1 &
app_pid=$!
for _ in {1..80}; do
    if ! kill -0 "$app_pid" 2>/dev/null; then cat "$scratch/startup.log"; exit 1; fi
    if grep -q 'Loaded Whisper model tiny' "$scratch/startup.log"; then break; fi
    sleep .25
done
grep -q 'Loaded Whisper model tiny' "$scratch/startup.log" || { cat "$scratch/startup.log"; exit 1; }

check_dictation() {
    local voice=$1 phrase=$2 word=$3 text=
    espeak-ng -v "$voice" -s 140 -w "$scratch/fixture.wav" "$phrase"
    "$app" --toggle
    for _ in {1..40}; do
        if [[ -n "$(pactl list short source-outputs)" ]]; then break; fi
        sleep .25
    done
    [[ -n "$(pactl list short source-outputs)" ]] || { cat "$scratch/startup.log"; exit 1; }
    paplay "$scratch/fixture.wav"
    sleep .5
    "$app" --toggle
    for _ in {1..80}; do
        text=$(timeout 2 xclip -selection clipboard -out 2>/dev/null || true)
        if [[ "${text,,}" == *"$word"* ]]; then
            printf 'Installed app, %s: %s\n' "$voice" "$text"
            return
        fi
        sleep .25
    done
    cat "$scratch/startup.log"
    printf 'Expected %s in clipboard: %s\n' "$word" "$text" >&2
    exit 1
}

check_dictation de 'Das ist ein einfacher Test. Wir sprechen heute über das Wetter.' wetter
check_dictation en-us 'This is a simple test. Today we are talking about the weather.' weather
timeout 10 "$app" --quit
for _ in {1..40}; do
    if ! kill -0 "$app_pid" 2>/dev/null; then
        wait "$app_pid"
        app_pid=
        echo 'Installed application transcribed both languages and accepted its quit command.'
        exit 0
    fi
    sleep .25
done
exit 1
