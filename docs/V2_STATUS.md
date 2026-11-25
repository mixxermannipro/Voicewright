# Voicewright 2.0 – Arbeitsstand

Diese Datei dokumentiert den Abschluss des Umbaus auf Voicewright 2.0 auf dem
Branch `feat/v2-dictation-suite`.
Der freigegebene Entwurf steht in
[superpowers/specs/2026-11-25-voicewright-v2-design.md](superpowers/specs/2026-11-25-voicewright-v2-design.md).

**Branch:** `feat/v2-dictation-suite` · **Stand:** 25. November 2026

---

## Fertiggestellt und geprüft

### Oberfläche & Steuerung

- `ui/widgets.py`: Konkrete `QPushButton`-Basis in `Segmented` und `NavList` sowie korrekte Geometrie-Interpolation für das gleitende Segment.
- `ui/overlay.py`: Liquid-Glass-Pille (300 × 64) mit Unterstützung für Hell-/Dunkel-Design aus `ui/theme.py` ohne Fokusverlust.
- `ui/settings_window.py`: Komplett neu gebaut mit 220-px-Seitenleiste und sieben Bereichen (*Übersicht*, *Modelle*, *Bereinigung*, *Smartes*, *Ausgabe*, *Verlauf*, *Info*). Alle v1-Einstellungen bleiben erhalten (`V1_KEYS`).
- `app.py` & `main.py`: Anbindung an die neue Seitenleiste, Live-Aktualisierung von Hybrid-Modus/Tipp-Schwelle, Theme-Initialisierung beim Start und CLI-Befehl `--transform`.
- `i18n.py`: Deutsche Übersetzungen für alle neuen v2-Oberflächentexte ergänzt.

### Konfiguration, Modelle & Pipeline

- `config.py`: Schema 2 mit echter v1→v2-Migration **vor** dem Zusammenführen mit Standardwerten und Zuordnung alter Kurznamen (`tiny` → `whisper-tiny`, `small` → `whisper-small` usw.).
- `models.py`: Katalog mit geprüften Größen und SHA-256-Prüfsummen sowie `recommended_model(cuda, sherpa)`.
- `engines.py` & `transcriber.py`: Parakeet V3 und SenseVoice (`sherpa-onnx`, optionales Extra `asr`) sowie Whisper (`faster-whisper`).
- `cleanup.py`, `runtime.py`, `guard.py`, `smart.py`: Lokale Regelstufe, smarte Befehle/Struktur/Textbausteine/Wortersetzungen, optionales lokales `llama.cpp` mit Qwen3 und Schutzprüfung.

### Tests

- `tests/test_core.py` (13 Tests) + `tests/test_v2.py` (10 Tests): insgesamt **23 automatisierte Tests**, inklusive Headless-Qt-Prüfung aller 7 Einstellungsseiten und aller Overlay-Zustände.
- E2E-Sprachtest mit synthetischem Audio (DE/EN) über Parakeet V3 (`sherpa-onnx`) + Regelbereinigung.
- GitHub-CI (`check` auf Fedora 45): `pip check`, `pytest -q`, `scripts/smoke-whisper.py` (Whisper Tiny mit echtem Audio-Test DE/EN), `scripts/build-linux.sh` und `scripts/smoke-linux.sh` (installiertes Paket in Xvfb + virtuellem PulseAudio).

---

## Ehrliche Grenzen

- **Getestet auf Fedora Linux (`x86_64`)** lokal und im Fedora-45-CI-Container (Xvfb + virtuelles PulseAudio).
- **Windows und macOS:** Codepfade (`SendInput`, `CGEvent`) sind per Unit-Test mit Mocks geprüft, aber **nicht** auf echter Windows- oder macOS-Hardware ausgeführt.
- **Wayland-Portale (`GlobalShortcuts` / `RemoteDesktop`):** D-Bus-Nachrichtenaufbau ist per Unit-Test geprüft; die echte Desktop-Freigabe auf GNOME/KDE wurde nicht automatisch durchgeklickt (ohne Freigabe bleibt die Zwischenablage als Sicherheitsnetz).
- **SenseVoice:** Im Katalog mit echter Prüfsumme hinterlegt, aber nicht mit echtem asiatischem Audio geladen/getestet.
- **Alle Sprachtests** nutzen ausschließlich synthetisches Audio (`espeak-ng` / WAV-Dateien), nie das Mikrofon des Eigentümers.
