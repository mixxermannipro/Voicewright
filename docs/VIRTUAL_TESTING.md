# Virtuelle V1-Teststrategie: vollständig autonom bis zur Nutzerabnahme

**Stand 12.11.2026 · Owner-Gate: keines während der Entwicklung.** [Issue #76](https://github.com/mixxermannipro/Voicewright/issues/76) ist verbindlich. Die folgende Matrix definiert *Sollzustände* – keine Behauptung, dass sämtliche Tests bereits existieren oder bestanden sind.

## Scharfe Trennung der Prüfarten

| Ebene | Automatisch testbar? | Nachweis/Begrenzung |
| --- | --- | --- |
| TypeScript/Vitest, Rust/Clippy/fmt/Test, Audits | Ja, CI | Prozessende/Exitcodes, Testreports und Warnungen |
| Audioaufnahme/ASR | Ja, mit virtuellem Mikrofon und rechtmäßigem synthetischem Sprachmaterial, echten Modellgewichten | Version/Hash/Device-Runner, WER/CER & Latenz; kein Beleg für echten Mikrofon-Treiber |
| Linux X11-Texteingabe | Ja, Xvfb + GTK/Qt/Browser-Testfelder | Tatsächlicher Einfügecode im isolierten Fenster; nicht jede Fremd-App |
| Wayland-Portale | Teilweise, virtuelle Compositor-Sitzung und D-Bus-Mocks | Statusänderungen, Permission-Denial/Fallback; echter Freigabedialog eines Desktopusers nicht voll simuliert |
| Windows/macOS | Builds, automatisierte OS-Tests auf GitHub-Runnern; viele simulierte Editorfälle | Aktive Session/TCC/physischer Shortcut/Signaturverhalten nicht vollständig beweisbar |
| Installer/Artefakte | Ja, Struktur, Sidecar, Hash, Start in Runner soweit möglich | Unsignierte DMG/EXE sind keine vollständig öffentlich freigegebenen Apps |
| Echte Hardware, Mikrofone und Nutzer-OS-Permissions | **Erst später** | Einmaliger privater V1-Abnahmetest durch Eigentümer, dann Feedback |

## Bestehender automatisierter Pfad (am Stichtag)

- `.github/workflows/ci.yml`: Node 24 Webchecks, Rust 1.99.1 inklusive beiden Cargo-Projekten (`--all-targets`), Workflow-Lint und Linux-Paketjob. Sammelstatus `check`. Der Rust-Job führt zusätzlich die explizit ausgewählten echten Whisper-/Qwen-Integrationstests aus; ihr Fehler blockiert `check`.
- `.github/workflows/linux-package.yml`: auf Ubuntu 22.04 AppImage+DEB bauen, ABI/Contents/Checksummen prüfen. Derzeit keine vollständige synthetische Mikrofon-E2E in CI.
- `scripts/linux-smoke/x11-insertion.sh`: isolierter Xvfb + echter GTK-TextView/Insertion-Adapter, Unicode/Emoji/Absatz. In CI als separaten verpflichtenden, nicht bloß dokumentierten Test integrieren.
- `scripts/linux-smoke/run.sh`: AppImage/DEB + pulseaudio `module-pipe-source` + synthetische PCM-Datei + `xdotool` + GTK. Modelle/Audiodateien sind vorausgesetzt und **dürfen nicht** aus persönlichen Quellen kopiert werden.
- Modelltests `src-tauri/tests/speech.rs` und `engines/cleanup/tests/protocol.rs` bleiben im normalen Offline-Unit-Lauf ignoriert. `scripts/model_gate.py` führt beide gezielt mit echten CPU-Engines und synthetischen DE/EN-WAVs aus. Gewichte sind in `scripts/model-gate-models.json` nach Quelle, Commit, Größe, SHA256 und Lizenz festgeschrieben; jeder Cachetreffer wird erneut geprüft. Ein erfolgreicher Cargo-Aufruf mit null ausgewählten Tests gilt als Fehler.

### Maschinenbericht des Modell-Gates / Model-gate evidence

Das CI-Artefakt `model-evidence-<OS>-<ARCH>-<SHA>` enthält `report.json` und Prozesslogs, keine Gewichte oder WAV-Dateien. Der Bericht nennt Commit, Workflow-URL, Runner, Modell-/Fixture-Hashes, Lizenzquellen, Ergebnis, Zeitlimit und gemessene Prozesslaufzeit. Fehlerberichte werden ebenfalls hochgeladen, wenn das Gate gestartet ist; ein vorheriger Build-/Setupfehler kann noch keinen Modellbericht erzeugen und bleibt ein roter CI-Job.

The artifact records real CPU-model integration, not microphone capture or desktop E2E. Timings include Cargo/test startup and are not inference-only latency. Fixture hashes identify the actual eSpeak/FFmpeg output on that runner; they need not match across tool versions. Tool-version logs are included. The small substring smoke assertions are not a WER/CER benchmark or proof of general cleanup quality. Virtual microphone, noise/long-audio, resource/stress, insertion and OS-permission coverage remain separate gates.

## V1-Automatisierungsaufträge

1. **Priorität P0 – CI „check“:** alle bestehenden Prüfungen zuverlässig grün, zusätzlicher X11-insertion-Smoke als Pflicht. Nur mit isoliertem `DISPLAY`, synthetischem Text und Timeouts; keine Tests auf Nutzerdesktop.
2. **P0 – Audio & echte Modelle:** Test-Fixures synthetisch erzeugen und hash-/lizenzgeprüfte Whisper-/Qwen-Gewichte nur temporär beziehen; automatisierte Batch-/Live-Audio-Tests in isolierter Pipeline. Caching ohne personenbezogene Daten; Grenzen/Kosten/Laufzeit messen.
3. **P0 – Session/Permission/Fokus:** Fake-Audio/Provider, Appwechsel, Timeout, Widerruf, FocusGuard, Passwort-/Secure-Field, Copy-Undo, Unicode/Absätze, Lost KeyUp und Stopp/Abbruch deterministisch simulieren.
4. **P0 – Wayland:** D-Bus-Mocks mit `granted/denied/pending/revoked/unavailable`; bei unbekanntem Portalzustand kein Einfügen. Bei echten Portalen in isolierter Test-Session legitime Freigabe abwarten, **nicht** automatisiert Sicherheit umgehen. Kein angebliches „Wayland supported“ allein aus Mocks.
5. **P0 – OS-Packaging:** GitHub Windows/macOS-Runners für NSIS/DMG und integrationsnahe Tests, Linux AppImage/DEB mit ABI/GLIBC-Prüfung. Kein Signing-Secret voraussetzen; Signaturstatus in Bericht und UI sauber kennzeichnen.
6. **P1 – Langlauf/Fault-Injection:** 100+ synthetische Hotkey-/Start-/Stop-/Cancel-Zyklen, Speichergrenzen, Defektmodelle, ausfallender Keyring, Neustarts, keine Leaks.
7. **P0 – Ergebnisreport:** pro PR `COMMIT_SHA`, OS, Testname, real/mock, Artefakt-ID, Ergebnis und offene Plattformgrenzen in PR und [PROGRESS.md](PROGRESS.md) nachweisen.

## Was *nicht* gewünscht ist

- Keine Abfrage von persönlichem Bildschirm, Mikrofon, Apple-TCC oder Wayland-/RemoteDesktop-Freigaben für CI.
- Keine echten API-/Cloud-Schlüssel oder private Aufnahmen zum Testen; kein kostenpflichtiger Cloud-Traffic ohne bewusste Entscheidung.
- Kein Bypass von OS-Dialogen/Signaturprüfungen, keine `sudo`-`uinput`-Automatisierung als produktiver Einfügeweg.
- Kein Mergen roter/flaky Tests und kein stilles Umdeuten von ungetestet zu bestanden.

## Einziger späterer Nutzer-Testzyklus

**Wenn** ein autonom gebauter, CI-grüner, installierbarer V1-Testkandidat mit Versions-/Hashliste bereitsteht, gibt der Eigentümer pro Plattform Feedback (funktioniert / nicht funktioniert, Schritte, App, OS). Coding-Agenten reproduzieren dies möglichst als automatisierten Regressionstest, beheben und erstellen neuen Kandidaten. Erst der Eigentümer entscheidet nach dem Praxistest über die öffentliche Freigabe.

**V1-Testkandidat ≠ stabile öffentlich zertifizierte V1.** Kritische Sicherheits-/Privacy-Probleme bleiben Blocker schon vor der privaten Übergabe.
