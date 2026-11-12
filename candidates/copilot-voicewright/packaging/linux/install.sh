#!/usr/bin/env bash
# Installs the prebuilt Voicewright bundle for the current user (no root needed
# except for the optional system packages).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.local/opt/voicewright"
BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor/512x512/apps"

echo "==> Installing Voicewright to $DEST"
mkdir -p "$DEST" "$BIN" "$APPS" "$ICONS"
rm -rf "$DEST"/*
cp -r "$HERE"/* "$DEST"/
ln -sf "$DEST/voicewright" "$BIN/voicewright"
cp "$HERE/voicewright.png" "$ICONS/voicewright.png"
sed "s|^Exec=voicewright|Exec=$DEST/voicewright|" "$HERE/voicewright.desktop" > "$APPS/voicewright.desktop"
update-desktop-database "$APPS" >/dev/null 2>&1 || true
gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true

echo
echo "==> Recommended system packages"
if command -v dnf >/dev/null 2>&1; then
  echo "    sudo dnf install portaudio wl-clipboard ydotool xdotool"
elif command -v apt-get >/dev/null 2>&1; then
  echo "    sudo apt install libportaudio2 wl-clipboard ydotool xdotool"
elif command -v pacman >/dev/null 2>&1; then
  echo "    sudo pacman -S portaudio wl-clipboard ydotool xdotool"
fi
if [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
  cat <<'MSG'

==> Wayland detected. For global hotkeys and auto-paste:
    sudo usermod -aG input "$USER"          # hotkey via evdev (log out/in afterwards)
    sudo systemctl enable --now ydotool     # paste via ydotool (Fedora service name)
    Alternative: create a custom keyboard shortcut in GNOME/KDE settings that runs
    "voicewright --toggle".
MSG
fi
echo
echo "Done. Start with: voicewright   (or from your application menu)"
