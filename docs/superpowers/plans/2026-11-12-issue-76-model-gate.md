# Issue #76 – autonome Modellprüfung

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Die bisher ignorierten echten Whisper-/Qwen-Tests verbindlich in CI ausführen, ohne Nutzergeräte oder persönliche Daten.

**Architecture:** Ein Python-Standardbibliothek-Skript prüft die festgeschriebenen Kataloggewichte, erzeugt synthetische WAVs und führt die bestehenden Rust-Integrationstests mit Zeitlimit aus. Der bestehende Rust-Job übernimmt die Prüfung und lädt einen JSON-Bericht auch bei Fehlern hoch; `check` bleibt das übergeordnete Pflicht-Gate. Keine zusätzliche Produktfunktion, keine neuen Laufzeitabhängigkeiten.

**Tech Stack:** Python 3, eSpeak NG, FFmpeg, Node 24, Rust 1.99.1, GitHub Actions.

**Spec:** `docs/V1_SCOPE.md`, `docs/VIRTUAL_TESTING.md`, Issue #76 Phase 1.

## Global Constraints

- Modelle, WAVs und Build-Dateien bleiben außerhalb von Git; nur synthetische Inhalte.
- Modellquellen sind commit-gepinnt, Hash/Größe werden bei jedem Cachetreffer erneut geprüft.
- Beide Cargo-Projekte mit `--manifest-path`, `--locked`, `--all-targets` prüfen.
- Keine OS-Freigaben, Signatur-Secrets oder Veröffentlichung; vorhandene fremde Änderungen bleiben unangetastet.
- Dies ist ein Teilauftrag, nicht die Schlussabnahme der V1. UI, Wayland und native Paketnachweise bleiben separate kleine PRs.

## Review Focus

1. Defekter Cache darf keine Modellinferenz erreichen: Hash-/Größenfehler testen.
2. Downloadfehler hinterlassen keine nutzbare Teildatei: atomare Übernahme testen.
3. Falsche/stille Audios dürfen keine echte ASR vortäuschen: WAV-Spezifikation/Pegel testen.
4. Ein Prozessfehler oder Timeout muss Gate und Bericht auf Fehler setzen: Exitcodes testen.
5. Berichte müssen Commit/Runner/real-vs-mock/offene Grenzen enthalten, auch bei frühem Fehler: Reporttests.

## Task 1: Modell-Gate mit getesteten Fehlerpfaden

**Files:** `scripts/model_gate.py`, `scripts/test_model_gate.py`, `scripts/model-gate-models.json`.

**Interfaces:** `verify_model(path, entry)`, `fetch_model(cache, entry)`, `validate_wav(path)`, `run_check(name, command, env, report, timeout)`; CLI `--cache`, `--output`.

- [x] Tests für Cacheintegrität, atomaren Download, WAV-Format/Stille, Katalogkonsistenz und Fehlerberichte schreiben.
- [x] `python3 -m unittest discover -s scripts -p test_model_gate.py` muss zunächst fehlschlagen.
- [x] Skript mit SHA256/Größe, HTTPS-Download, temporären Fixtures, begrenzten Prozessen und JSON-Bericht implementieren.
- [x] Tests erneut ausführen; echte synthetische Modelltests mit vorhandenen verifizierbaren Gewichten laufen lassen.

## Task 2: Verbindliche CI und dokumentierter Nachweis

**Files:** `.github/workflows/ci.yml`, `docs/TESTING.md`, `docs/VIRTUAL_TESTING.md`, `docs/PROGRESS.md`.

- [x] Python-Tests, eSpeak/FFmpeg, Modellcache, Modell-Gate und Always-Upload im Rust-Job ergänzen; reguläre Tests auf `--all-targets` umstellen.
- [x] `actionlint`, Python-Tests, Web-Gates, beide Rust-Gates und `git diff --check` ausführen.
- [ ] Gesamten Diff prüfen, DeepSeek-Review einholen, gezielt committen; Branch pushen und PR mit `Part of #76` öffnen.
- [ ] CI auswerten, Fehler beheben; nur belegten Stand in #76 dokumentieren. Kein Stable-Release und kein Abhaken der gesamten V1.
