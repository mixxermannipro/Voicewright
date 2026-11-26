# Voicewright __VERSION__

## Deutsch

Voicewright __VERSION__ ist eine lokale Diktier-App für Fedora Linux (x86_64) und Windows (x64). Spracherkennung und regelbasierte Bereinigung laufen ohne Konto und ohne Cloud-Pflicht.

**Neu in dieser Version**

- Einrichtung in vier Schritten: Willkommen, Sprachmodell, Mikrofon-Test, Tastenkürzel und Einfügen.
- Parakeet V3 und SenseVoice funktionieren nach der Installation ohne zusätzliches Extra; `sherpa-onnx` ist Teil der Standardabhängigkeiten.
- Zwei globale Kürzel: Diktat und „Auswahl umschreiben“ (`Ctrl+Alt+Leertaste`).
- Wayland: Die Portal-Freigabe für Tastatureingaben bleibt mit einem `restore_token` erhalten und wird beim Start ohne neuen Dialog wiederverwendet, solange sie gültig ist. Nach einem Widerruf kann das System erneut fragen; lehnst du ab, fällt Voicewright sauber auf `wtype` oder die Zwischenablage zurück.
- Windows: korrigierte 64-Bit-`SendInput`-Struktur, Umlaute und Emoji, kein Konsolenfenster des lokalen Sprachmodells.

**Pakete**

- `Voicewright-__VERSION__-linux-x86_64.tar.gz` und `.sha256`
- `Voicewright-__VERSION__-windows-x64.zip` und `.sha256`
- `Voicewright-__VERSION__-windows-x64-setup.exe` und `.sha256`

Fedora 45: Zuerst `sudo dnf install python3.14 python3.14-devel gcc kernel-headers portaudio` installieren. Der Standard-`python3` ist 3.15 und wird noch nicht unterstützt; ältere Fedora-Releases nutzen Python 3.11–3.13.

Prüfen und installieren:

```bash
sha256sum -c Voicewright-__VERSION__-linux-x86_64.tar.gz.sha256
mkdir voicewright-install
tar -xzf Voicewright-__VERSION__-linux-x86_64.tar.gz -C voicewright-install
bash voicewright-install/Voicewright/install.sh
```

Unter Windows die ZIP entpacken und `Voicewright.exe` starten oder das Setup ausführen.

## English

Voicewright __VERSION__ is a local-first dictation app for Fedora Linux (x86_64) and Windows (x64). Speech recognition and rule-based cleanup run without an account or a cloud requirement.

**Highlights**

- Four-step setup assistant: welcome, speech model, microphone test, shortcut and insertion check.
- Parakeet V3 and SenseVoice work out of the box; `sherpa-onnx` is now a default dependency.
- Two global shortcuts: dictation and “Rewrite selection” (`Ctrl+Alt+Space`).
- Wayland: the portal keyboard permission is persisted with a `restore_token` and reused at startup without another dialog while it remains valid. After a revocation the system may ask again; if you decline, Voicewright falls back cleanly to `wtype` or the clipboard.
- Windows: fixed 64-bit `SendInput` layout, umlauts and emoji, and no console window for the local language model.

**Assets**

- `Voicewright-__VERSION__-linux-x86_64.tar.gz` and `.sha256`
- `Voicewright-__VERSION__-windows-x64.zip` and `.sha256`
- `Voicewright-__VERSION__-windows-x64-setup.exe` and `.sha256`

Fedora 45: install `python3.14` and `python3.14-devel` first (`sudo dnf install python3.14 python3.14-devel gcc kernel-headers portaudio`). The default `python3` is 3.15 and not supported yet; older Fedora releases use Python 3.11–3.13.

Verify before installing:

```bash
sha256sum -c Voicewright-__VERSION__-linux-x86_64.tar.gz.sha256
mkdir voicewright-install
tar -xzf Voicewright-__VERSION__-linux-x86_64.tar.gz -C voicewright-install
bash voicewright-install/Voicewright/install.sh
```

On Windows, extract the ZIP and run `Voicewright.exe`, or use the installer.

## Platform coverage / Plattform-Abdeckung

Linux packages are built and tested in a Fedora 45 container with Xvfb, a virtual PulseAudio source and synthetic German/English speech. Windows packages are built and smoke-tested on a GitHub `windows-2022` runner (executable self-test, portable ZIP, Inno Setup installer). Neither release job uses a real microphone, a real desktop session or real Wayland compositor hardware; please report desktop-specific issues with your distribution, compositor and portal version.
