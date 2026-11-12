# Voicewright

Voicewright ist eine Diktier-App für Fedora Linux (x86_64). Nach dem Herunterladen eines Whisper-Sprachmodells läuft die Spracherkennung lokal. Voicewright kopiert das fertige Diktat in die Zwischenablage.

[Zur englischen Anleitung / English instructions](#english)

## Fedora installieren

Installiere einmalig die Fedora-Abhängigkeiten.

```bash
sudo dnf install python3.11 python3.11-devel gcc kernel-headers portaudio xcb-util-cursor libxkbcommon-x11
```

1. Lade das Linux-x86_64-Paket und die passende SHA-256-Datei aus den [GitHub-Releases](https://github.com/mixxermannipro/Voicewright/releases).
2. Prüfe im Download-Ordner das Paket und entpacke es in einen leeren Ordner. Ersetze gegebenenfalls die Versionsnummer.

   ```bash
   sha256sum -c Voicewright-1.0.0-linux-x86_64.tar.gz.sha256
   mkdir voicewright-install
   tar -xzf Voicewright-1.0.0-linux-x86_64.tar.gz -C voicewright-install
   bash voicewright-install/Voicewright/install.sh
   ```
3. Starte **Voicewright** im Anwendungsmenü und lade unter **Sprachmodell** ein Modell. Beginne mit **Small** für Deutsch und Englisch oder **Tiny** für einen schnellen ersten Test.

Der Installer lädt Python-Abhängigkeiten von PyPI und richtet Voicewright nur für dein Benutzerkonto ein. Für den Start unter Wayland verwendet das Paket XWayland, sofern es läuft. Für XWayland heißt das Paket `xorg-x11-server-Xwayland`.

## Diktieren

Starte und stoppe mit der Schaltfläche in den Einstellungen. Unter KDE oder GNOME mit Wayland kannst du für denselben Vorgang in den Systemeinstellungen ein eigenes Tastenkürzel anlegen. Verwende als Befehl den vollständigen Pfad zu `~/.local/bin/voicewright` gefolgt von ` --toggle`. Unter X11 ist standardmäßig `Ctrl+Shift+Leertaste` eingerichtet. Füge den Text danach mit `Ctrl+V` ein.

Externe Textkorrektur und lokaler Verlauf sind bei einer frischen Installation ausgeschaltet. Aktivierst du einen Cloud-Dienst, erhält dieser den erkannten Text. API-Schlüssel speichert Voicewright im System-Schlüsselbund.

## English

Download the Linux x86_64 archive and its checksum from [GitHub Releases](https://github.com/mixxermannipro/Voicewright/releases). Verify it with `sha256sum -c`, extract it into an empty directory, then run `bash Voicewright/install.sh` from that directory. Launch **Voicewright** and download a speech model. **Small** works for German and English. **Tiny** is useful for a quick test.

Start and stop recording using the button in Settings. On Wayland, set a custom GNOME or KDE shortcut to the full path of `~/.local/bin/voicewright` followed by ` --toggle`. On X11 the default shortcut is `Ctrl+Shift+Space`. Paste the finished text with `Ctrl+V`.

Install the Fedora prerequisites shown above. The installer fetches Python dependencies from PyPI and installs Voicewright for the current user. The app uses XWayland when available. Cloud cleanup and local history are off by default. Enabling cloud cleanup sends recognized text to the chosen provider. Keys are stored in the system keyring.

## Entwicklung / Development

Use Python 3.11 in an isolated environment. Install `requirements-dev.txt` and run `python -m pytest -q`. The `check` workflow also verifies the [MIT-licensed Whisper Tiny model](https://huggingface.co/Systran/faster-whisper-tiny) by checksum, recognizes synthetic German and English speech, builds the Linux archive and tests the installed app in a Fedora 45 container with Xvfb and a virtual PulseAudio microphone. Run the equivalent checks locally with:

```bash
PYTHONPATH=src xvfb-run -a python scripts/smoke-whisper.py /tmp/voicewright-test-model
bash scripts/build-linux.sh
xvfb-run -a bash scripts/smoke-linux.sh release/Voicewright-*-linux-x86_64.tar.gz /tmp/voicewright-test-model
```

The target for this release is Fedora Linux x86_64. Windows and macOS packaging files are included for future work.
