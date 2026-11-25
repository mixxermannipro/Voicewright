# Voicewright

Voicewright ist eine lokale Diktier-App (Version 2.0) für Fedora Linux (x86_64) mit Unterstützung für Windows und macOS im Quellcode. Spracherkennung und regelbasierte Textbereinigung laufen lokal ohne Konto oder Cloud-Pflicht.

[Zur englischen Anleitung / English instructions](#english)

## Überblick (Version 2.0)

- **Hybrid-Bedienung:** Ein Tastenkürzel (Standard `Ctrl+Shift+Leertaste`) für beide Gesten — kurz tippen schaltet die Aufnahme um, gedrückt halten spricht nur währenddessen, `Esc` bricht ab.
- **Lokale Spracherkennung:** Parakeet TDT 0.6B v3 und SenseVoice über `sherpa-onnx` (optionales Extra `asr`) sowie Whisper (Tiny bis Large v3) über `faster-whisper`. Alle Modelle sind per Größe und SHA-256 geprüft.
- **Lokale & optionale Textbereinigung:** Gesprochene Satzzeichen, Textbausteine, Wortersetzungen und Offline-Regeln laufen sofort und ohne KI. Optional lässt sich ein lokales Sprachmodell (Qwen3 über `llama.cpp`, Ollama oder LM Studio) oder ein Cloud-Anbieter mit eigenem API-Schlüssel aktivieren. Eine Schutzprüfung bewahrt Zahlen, Links, E-Mails, Code, Wörterbuch-Einträge und Verneinungen.
- **Direktes Einfügen:** Unter Wayland über das offizielle Desktop-Portal (`GlobalShortcuts` / `RemoteDesktop` nach ausdrücklicher Freigabe), alternativ über `wtype`, opt-in `ydotool` oder die Zwischenablage. Unter X11 per XTEST/`xdotool`, unter Windows per `SendInput` und unter macOS per `CGEvent`.
- **Datenschutz:** Cloud-Bereinigung und Diktat-Verlauf sind standardmäßig aus. API-Schlüssel speichert Voicewright ausschließlich im System-Schlüsselbund.

## Fedora installieren

Installiere einmalig die Fedora-Abhängigkeiten.

```bash
sudo dnf install python3.11 python3.11-devel gcc kernel-headers portaudio xcb-util-cursor xcb-util-keysyms xcb-util-wm libxkbcommon-x11 libglvnd-egl mesa-libGL
```

1. Lade das Linux-x86_64-Paket und die passende SHA-256-Datei aus den [GitHub-Releases](https://github.com/mixxermannipro/Voicewright/releases).
2. Prüfe im Download-Ordner das Paket und entpacke es in einen leeren Ordner. Ersetze gegebenenfalls die Versionsnummer.

   ```bash
   sha256sum -c Voicewright-2.0.0-linux-x86_64.tar.gz.sha256
   mkdir voicewright-install
   tar -xzf Voicewright-2.0.0-linux-x86_64.tar.gz -C voicewright-install
   bash voicewright-install/Voicewright/install.sh
   ```
3. Starte **Voicewright** im Anwendungsmenü und lade unter **Modelle** ein Sprachmodell (z. B. **Parakeet V3** bei installiertem `asr`-Extra oder **Whisper Small** / **Whisper Tiny**).

Der Installer lädt Python-Abhängigkeiten von PyPI und richtet Voicewright nur für dein Benutzerkonto ein. Für XWayland heißt das Paket `xorg-x11-server-Xwayland`.

## Diktieren

- **Tastenkürzel:** Im Hybrid-Modus startet ein Druck sofort die Aufnahme; kurzes Loslassen hält sie aktiv bis zum nächsten Druck, langes Halten beendet beim Loslassen. `Esc` verwirft die Aufnahme.
- **Wayland:** Beim Start bittet Voicewright optional über das Desktop-Portal um Freigabe für globale Kürzel und Einfügen. Alternativ kannst du in GNOME oder KDE einen System-Kurzbefehl für `~/.local/bin/voicewright --toggle` anlegen. Ohne Freigabe oder Helfer bleibt der fertige Text sicher in der Zwischenablage (`Ctrl+V`).
- **Auswahl umschreiben:** `voicewright --transform` kopiert die aktuelle Auswahl (nur wenn sich die Zwischenablage ändert), bereinigt sie und fügt sie wieder ein.

## English

Voicewright 2.0 is a local-first dictation application targeting Fedora Linux (`x86_64`), with Windows and macOS code paths included (not executed in CI). Speech recognition runs locally using `faster-whisper` (Whisper models) and optionally `sherpa-onnx` (Parakeet TDT 0.6B v3, SenseVoice).

Download the Linux `x86_64` archive and its checksum from [GitHub Releases](https://github.com/mixxermannipro/Voicewright/releases), verify it with `sha256sum -c`, extract it into an empty directory, and run `bash Voicewright/install.sh`. Launch **Voicewright** and download a speech model in **Models**.

Use one shortcut (`Ctrl+Shift+Space` by default) in **Hybrid** mode: tap to toggle recording on/off, hold to talk until release, or press `Esc` to cancel. On Wayland, Voicewright uses the official `GlobalShortcuts` and `RemoteDesktop` desktop portals after explicit consent, falling back to `wtype`, opt-in `ydotool`, a desktop shortcut (`voicewright --toggle`), or the clipboard. Cloud cleanup and local history are off by default; API keys are stored only in the system keyring.

## Entwicklung / Development

Use Python 3.11+ in an isolated environment. Install `requirements-dev.txt` (and optionally `pip install -e ".[asr,x11]"`) and run `python -m pytest -q`. The `check` workflow verifies the [MIT-licensed Whisper Tiny model](https://huggingface.co/Systran/faster-whisper-tiny) by checksum, recognizes synthetic German and English speech, builds the Linux archive and tests the installed app in a Fedora 45 container with Xvfb and a virtual PulseAudio microphone. Run the equivalent checks locally with:

```bash
PYTHONPATH=src xvfb-run -a python scripts/smoke-whisper.py /tmp/voicewright-test-model
bash scripts/build-linux.sh
xvfb-run -a bash scripts/smoke-linux.sh release/Voicewright-*-linux-x86_64.tar.gz /tmp/voicewright-test-model
```

**Plattformabdeckung / Platform coverage:** Linux Fedora (`x86_64`) is tested automatically in CI with Xvfb and virtual PulseAudio. Windows (`SendInput`) and macOS (`CGEvent`) injection paths and packaging files are included in the codebase and covered by unit mocks, not run on real Windows/macOS hardware.
