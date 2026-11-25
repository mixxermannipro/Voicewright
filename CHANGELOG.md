# Änderungen

## 2.0.0 (unveröffentlicht auf `feat/v2-dictation-suite`)

- **Hybrid-Bedienung (`dictation.py`):** Ein Kürzel für Tippen (Umschalten), Halten (Push-to-Talk) und Abbruch mit `Esc`.
- **Lokale Spracherkennung (`engines.py`, `models.py`):** Parakeet TDT 0.6B v3 und SenseVoice über optionales `sherpa-onnx` (`asr`-Extra) zusätzlich zu Whisper (`faster-whisper`), mit geprüften Dateigrößen und SHA-256-Prüfsummen.
- **Lokale Bereinigung & Schutzprüfung (`cleanup.py`, `runtime.py`, `guard.py`):** Offline-Regeln, optionales lokales `llama.cpp` mit Qwen3 (oder Ollama/LM Studio) sowie Schutzprüfung für Zahlen, Links, E-Mails, Code, Wörterbuch und Verneinungen.
- **Smarte Funktionen (`smart.py`, `stats.py`):** Gesprochene Satzzeichen, Struktur-Erkennung (Stichpunkte, Notizen, E-Mail), Umformulierungsbefehle, Textbausteine, Wortersetzungen, Auswahl umschreiben (`--transform`) und lokale Statistik ohne Textspeicherung.
- **Einfügen & Wayland-Portale (`inject.py`, `injector.py`, `portals.py`):** Plattformwege für Windows (`SendInput`), macOS (`CGEvent`), X11 (`XTEST`/`xdotool`) und Wayland (`GlobalShortcuts`/`RemoteDesktop`-Portal, `wtype`, opt-in `ydotool`, Zwischenablage).
- **Liquid-Glass-Oberfläche (`ui/`):** Neue Seitenleisten-Oberfläche mit 7 Bereichen, Hell-/Dunkel-Design, reduzierbarer Bewegung und überarbeiteter schwebender Status-Pille (`overlay.py`).
- **Konfigurations-Migration (`config.py`):** Schema-Version 2 übernimmt v1-Einstellungen inklusive Legacy-Modellnamen verlustfrei.

## 1.0.0

- Python/PySide6 version with local faster-whisper recognition and Fedora x86_64 packaging.
- Wayland desktop shortcut integration and clipboard output.

## Unveröffentlicht (v1)

- Produktname, Paketkennungen, Programme und Dokumentation auf **Voicewright** vereinheitlicht (Issue #2).
- Hotkey-Zustandsmaschine gegen Burst-, Repeat- und verlorene Tastenlöse-Ereignisse gehärtet; Abbruch invalidiert die laufende Sitzung und verhindert spätes Einfügen (Issue #7).
- Vorhandene Einstellungen und Modelle aus dem alten Datenordner `de.voxtakt.desktop` werden beim ersten Start übernommen.
- API-Schlüssel aus dem alten Schlüsselbund-Dienst bleiben lesbar und werden beim nächsten Speichern unter dem neuen Dienstnamen abgelegt.
- Alpha-Grundlage aus PR #1 nach `main` integriert.

## 0.1.0-alpha.1

Stand der Umsetzung und Prüfergebnisse stehen in [PROGRESS.md](docs/PROGRESS.md).
