# Voicewright

Voicewright ist eine lokale Diktier-App (Version 2.0) für Fedora Linux (x86_64) und Windows (x64). macOS ist im Quellcode unterstützt. Spracherkennung und regelbasierte Textbereinigung laufen lokal ohne Konto oder Cloud-Pflicht.

[Zur englischen Anleitung / English instructions](#english)

## Überblick (Version 2.0)

- **Hybrid-Bedienung:** Ein Tastenkürzel (Standard `Ctrl+Shift+Leertaste`) für beide Gesten — kurz tippen schaltet die Aufnahme um, gedrückt halten spricht nur währenddessen, `Esc` bricht ab.
- **Lokale Spracherkennung:** Parakeet TDT 0.6B v3 und SenseVoice über `sherpa-onnx` (Standardabhängigkeit) sowie Whisper (Tiny bis Large v3) über `faster-whisper`. Alle Modelle sind per Größe und SHA-256 geprüft. Fehlt `sherpa-onnx` auf einer Plattform, wählt Voicewright automatisch ein lauffähiges Whisper-Modell.
- **Lokale & optionale Textbereinigung:** Gesprochene Satzzeichen, Textbausteine, Wortersetzungen und Offline-Regeln laufen sofort und ohne KI. Optional lässt sich ein lokales Sprachmodell (Qwen3 über `llama.cpp`, Ollama oder LM Studio) oder ein Cloud-Anbieter mit eigenem API-Schlüssel aktivieren. Eine Schutzprüfung bewahrt Zahlen, Links, E-Mails, Code, Wörterbuch-Einträge und Verneinungen.
- **Direktes Einfügen:** Unter Wayland über das offizielle Desktop-Portal (`GlobalShortcuts` / `RemoteDesktop` nach ausdrücklicher Freigabe), alternativ über `wtype`, opt-in `ydotool` oder die Zwischenablage. Unter X11 per XTEST/`xdotool`, unter Windows per `SendInput` und unter macOS per `CGEvent`.
- **Einrichtung:** Ein Assistent führt in vier Schritten durch Willkommen, Modellwahl, Mikrofon-Test und Tastenkürzel/Einfügen.
- **Datenschutz:** Cloud-Bereinigung und Diktat-Verlauf sind standardmäßig aus. API-Schlüssel speichert Voicewright ausschließlich im System-Schlüsselbund.

## Fedora installieren

Installiere einmalig die Fedora-Abhängigkeiten.

```bash
sudo dnf install python3.14 python3.14-devel gcc kernel-headers portaudio xcb-util-cursor xcb-util-keysyms xcb-util-wm libxkbcommon-x11 libglvnd-egl mesa-libGL
```

Fedora 45's default `python3` is 3.15, which the pinned PySide6 does not support yet. Voicewright therefore installs with Python 3.11–3.14; on older Fedora releases use `python3.13`, `python3.12` or `python3.11` instead of `python3.14`.

1. Lade das Linux-x86_64-Paket und die passende SHA-256-Datei aus den [GitHub-Releases](https://github.com/mixxermannipro/Voicewright/releases).
2. Prüfe im Download-Ordner das Paket und entpacke es in einen leeren Ordner. Ersetze gegebenenfalls die Versionsnummer.

   ```bash
   sha256sum -c Voicewright-2.0.0-linux-x86_64.tar.gz.sha256
   mkdir voicewright-install
   tar -xzf Voicewright-2.0.0-linux-x86_64.tar.gz -C voicewright-install
   bash voicewright-install/Voicewright/install.sh
   ```
3. Starte **Voicewright** im Anwendungsmenü. Der Einrichtungsassistent führt durch Modellwahl, Mikrofon-Test und Tastenkürzel; **Parakeet V3** funktioniert ohne zusätzliches Extra, alternativ stehen **Whisper Small** und **Whisper Tiny** bereit.

Der Installer sucht ein kompatibles Python 3.11–3.14, lädt die Abhängigkeiten von PyPI und richtet Voicewright nur für dein Benutzerkonto ein. Für XWayland heißt das Paket `xorg-x11-server-Xwayland`.

Ein Update ersetzt nur die Verknüpfung in `~/.local/bin`. Ältere Installationen bleiben unter `~/.local/opt/voicewright.*` liegen und können nach dem Beenden von Voicewright manuell gelöscht werden. Zum Deinstallieren entferne `~/.local/bin/voicewright`, `~/.local/share/applications/voicewright.desktop`, das Icon und den Ordner unter `~/.local/opt`.

## Diktieren

- **Tastenkürzel:** Im Hybrid-Modus startet ein Druck sofort die Aufnahme; kurzes Loslassen hält sie aktiv bis zum nächsten Druck, langes Halten beendet beim Loslassen. `Esc` verwirft die Aufnahme.
- **Wayland:** Beim ersten Start bittet Voicewright über das Desktop-Portal um Freigabe für globale Kürzel und Tastatureingaben. Solange die Freigabe gültig ist, wird sie über einen `restore_token` beim nächsten Start ohne neuen Dialog wiederverwendet. Nach einem Widerruf kann das System erneut fragen; lehnst du ab, fällt Voicewright sauber auf `wtype`, opt-in `ydotool` oder die Zwischenablage zurück. Alternativ kannst du in GNOME oder KDE einen System-Kurzbefehl für `~/.local/bin/voicewright --toggle` anlegen.
- **Auswahl umschreiben:** Standardmäßig `Ctrl+Alt+Leertaste` oder `voicewright --transform`. Voicewright kopiert die aktuelle Auswahl (nur wenn sich die Zwischenablage ändert), bereinigt sie und fügt sie wieder ein. Beide Wege teilen sich eine Portal-Sitzung.

## English

Voicewright 2.0 is a local-first dictation application for Fedora Linux (`x86_64`) and Windows (`x64`), with a macOS source path. Speech recognition runs locally using `faster-whisper` (Whisper models) and `sherpa-onnx` (Parakeet TDT 0.6B v3, SenseVoice), which is a default dependency. If `sherpa-onnx` is unavailable on a platform, Voicewright automatically selects a runnable Whisper model.

Download the Linux `x86_64` archive or the Windows ZIP/installer and its SHA-256 file from [GitHub Releases](https://github.com/mixxermannipro/Voicewright/releases), verify it with `sha256sum -c`, extract it into an empty directory, and run `bash Voicewright/install.sh` on Linux. On Fedora 45 install `python3.14` and `python3.14-devel` first: the default `python3` is 3.15 and not supported yet. Older releases use Python 3.11–3.13. On Windows, extract the ZIP and run `Voicewright.exe`, or use the installer. Updates replace the launcher; older copies stay in `~/.local/opt/voicewright.*` and can be removed manually.

The four-step setup assistant covers the model, a live microphone test, the dictation shortcut and an insertion check. Use one shortcut (`Ctrl+Shift+Space` by default) in **Hybrid** mode: tap to toggle recording on/off, hold to talk until release, or press `Esc` to cancel. `Ctrl+Alt+Space` rewrites the current selection. On Wayland, Voicewright uses the official `GlobalShortcuts` and `RemoteDesktop` desktop portals after explicit consent. While the permission is valid, it is reused at startup through a `restore_token` without another dialog. After a revocation the system may ask again; if you decline, Voicewright falls back to `wtype`, opt-in `ydotool`, a desktop shortcut (`voicewright --toggle`), or the clipboard. Cloud cleanup and local history are off by default; API keys are stored only in the system keyring.

## Entwicklung / Development

Use Python 3.11–3.14 in an isolated environment. Install `requirements-dev.txt` (and optionally `pip install -e ".[x11]"`) and run `python -m pytest -q`. The `check` workflow verifies the [MIT-licensed Whisper Tiny model](https://huggingface.co/Systran/faster-whisper-tiny) by checksum, recognizes synthetic German and English speech, builds the Linux archive and tests the installed app in a Fedora 45 container with Xvfb and a virtual PulseAudio microphone. The `windows` workflow runs the same tests, builds the windowed executable, smoke-tests it, and creates the portable ZIP, Inno Setup installer and SHA-256 files. Run the equivalent Linux checks locally with:

```bash
PYTHONPATH=src xvfb-run -a python scripts/smoke-whisper.py /tmp/voicewright-test-model
bash scripts/build-linux.sh
xvfb-run -a bash scripts/smoke-linux.sh release/Voicewright-*-linux-x86_64.tar.gz /tmp/voicewright-test-model
```

**Plattformabdeckung / Platform coverage:** Linux Fedora (`x86_64`) is tested automatically in CI with Xvfb and virtual PulseAudio, including an installed-package dictation test. Windows (`x64`) is built and smoke-tested automatically on a GitHub `windows-2022` runner: unit tests, `SendInput` structure checks, PyInstaller executable self-test, portable ZIP and Inno Setup installer. Neither platform is tested with a real microphone, a real desktop session or real Wayland compositor hardware in CI; macOS (`CGEvent`) remains a source path without automated packaging.
