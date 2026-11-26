# Voicewright 2.0 – Arbeitsstand

Diese Datei dokumentiert den Abschluss von Voicewright 2.0 auf dem Branch
`feat/v2-production-ready`. Der freigegebene Entwurf steht in
[superpowers/specs/2026-11-25-voicewright-v2-design.md](superpowers/specs/2026-11-25-voicewright-v2-design.md).

**Branch:** `feat/v2-production-ready` · **Stand:** 26. November 2026

---

## Fertiggestellt und geprüft

### Oberfläche & Einrichtung

- `ui/settings_window.py`: Seitenleiste mit sieben Bereichen, Hell-/Dunkel-Design, reduzierte Bewegung und alle v1-Einstellungen (`V1_KEYS`).
- `ui/onboarding.py`: Vier-Schritt-Assistent (Willkommen → Modell → Mikrofon → Kürzel/Einfügen) mit Live-Pegel, Modell-Download, Fehlerzuständen und Autostart-Schalter. Er öffnet beim ersten Start ohne Modell und bleibt über Einstellungen und Tray erreichbar.
- `ui/overlay.py`: Liquid-Glass-Pille für Aufnahme, Verarbeitung, Erfolg und Fehler.
- `i18n.py`: Deutsche und englische Texte für die neuen Bereiche und den Assistenten.
- `main.py`: Qt-Plattformwahl (`wayland;xcb` auf Wayland, `xcb` auf X11, explizite Vorgabe gewinnt) und versteckter `--selftest` für das gepackte Windows-Programm.

### Spracherkennung, Modelle & Einfügen

- `sherpa-onnx` ist Standardabhängigkeit in `requirements.txt` und `pyproject.toml`; `voicewright.spec` sammelt Daten, DLLs und Submodule ein.
- `models.ensure_runnable_default()` verhindert `SHERPA_MISSING` bei einer frischen Installation: Ohne `sherpa-onnx` wird automatisch ein lauffähiges Whisper-Modell gewählt.
- Zwei globale Kürzel: Diktat und „Auswahl umschreiben“ (`Ctrl+Alt+Leertaste`). `HotkeyManager`, `PynputBackend` und `GlobalShortcutsPortal` verarbeiten beide Kombinationen. Überschneidende Kombinationen (gleich, Teilmenge oder Obermenge) werden deaktiviert, weil sonst ein Kürzel das andere mit auslösen würde; Einstellungen und Assistent weisen darauf hin. Die Signalauswertung nutzt das korrekte D-Bus-Headerfeld (`MEMBER`), damit `Activated`/`Deactivated` wirklich ankommen.
- Wayland: `RemoteDesktop` mit `persist_mode=2`, gespeichertem `restore_token`, automatischer Wiederherstellung beim Start und sauberem Rückfall auf `wtype`, opt-in `ydotool` oder Zwischenablage bei Widerruf. D-Bus-Fehlerantworten werden schon beim Methodenaufruf erkannt, statt bis zum Timeout zu warten; auch eine abgelehnte Tastatureingabe führt zum Rückfall. Der Verbindungsaufbau hält keine Sperre, solange der Berechtigungsdialog offen ist, und `key()` wartet höchstens 250 ms – die Oberfläche friert nie hinter dem Dialog ein. Jeder Shortcut-Thread hat eigene Stop-Ereignisse, und `stop()` schließt die D-Bus-Verbindung, damit nach einem Neustart kein zweiter Listener weiterläuft.
- `av>=16,<19` ist festgeschrieben: PyAV 19 hat `metadata_errors` entfernt, das `faster-whisper` 1.2.1 noch übergibt. 16–18.1.1 liefern Räder für Python 3.11–3.14 unter Linux und Windows.
- `numpy>=1.24,<2.5`: numpy 2.5 verlangt Python ≥3.12, Voicewright unterstützt aber 3.11. Die Linux-Constraints bleiben damit auf jedem unterstützten Interpreter installierbar.
- XDG-konforme `preferred_trigger`-Namen (`CTRL+SHIFT+space`, `Return`, `Page_Up` usw.).
- Windows: 64-Bit-`INPUT`/`KEYBDINPUT` (40/24 Bytes), `ULONG_PTR`, `SendInput`-Signaturen, UTF-16-Einheiten für Umlaute und Emoji, `CREATE_NO_WINDOW` für `llama-server.exe`. Schlägt eine Tastensequenz mitten drin fehl, werden Ctrl/Shift im `finally` wieder losgelassen.
- Zwischenablage wird nur wiederhergestellt, wenn sie noch den eingefügten Text enthält. Ein zweites Diktat innerhalb der 400-ms-Wartezeit schiebt die erste Wiederherstellung vorher ab, und „Auswahl umschreiben“ legt den ursprünglichen Inhalt zurück, bevor es den neuen Text einfügt.

### Paketierung, CI & Release

- `packaging/linux/install.sh`: findet automatisch ein kompatibles Python 3.11–3.14. Fedora 45 liefert standardmäßig Python 3.15, deshalb nennen README und Fehlermeldung ausdrücklich `python3.14`; ältere Releases nutzen 3.13/3.12/3.11. Der Installer installiert die Wheel-Abhängigkeiten und legt Desktop-Eintrag, Icon und `~/.local/bin`-Verknüpfung an.
- `packaging/linux/voicewright.desktop`: Aktionen für `--toggle` und `--transform`, `StartupWMClass`.
- `packaging/windows/voicewright.iss`: Standardversion 2.0.0, Version über `/DAppVersion`. Workflow und `build.bat` übergeben absolute Pfade für Quelle und Ziel, weil ISCC `/D`-Pfade relativ zum Skriptordner auflöst.
- `scripts/build.bat`: dynamische Version, Tests, PyInstaller, portable ZIP, Inno-Setup-Installer und SHA-256 mit LF-Zeilenende, damit `sha256sum -c` auch unter Linux funktioniert.
- `.github/workflows/ci.yml`: bestehender Fedora-45-`check`-Job plus Windows-Job (Python 3.11, `pip check`, pytest, PyInstaller, Selbsttest, ZIP, Installer, Prüfsummen).
- `.github/workflows/release.yml`: Tag `v*` oder manueller Start, baut und prüft beide Pakete aus demselben Commit und veröffentlicht sie mit deutschen/englischen Hinweisen. Ein manueller Start baut den eingegebenen Tag, nicht den Branch-Kopf; Schreibrechte hat nur der Veröffentlichungs-Job.
- `docs/release-notes-template.md`: Release-Text mit ehrlicher Plattformabdeckung.

### Tests

- **46 automatisierte Tests**: `tests/test_core.py` (13), `tests/test_v2.py` (10) und `tests/test_production.py` (23).
- Neu abgedeckt: lauffähiges Standardmodell, XDG-Kürzelnamen, gemeinsamer Multi-Hotkey-Listener, überschneidende Kürzel, `persist_mode`/`restore_token`, kein „verbunden“ während des Berechtigungsdialogs, Windows-Strukturgrößen und Flags, UTF-16, `CREATE_NO_WINDOW`, Assistent, Pegelanzeige, Mikrofon-Tester inklusive Aufräumen bei Startfehlern und Zwischenablage-Wiederherstellung.
- Headless-Qt-Prüfung aller sieben Einstellungsseiten und aller Overlay-Zustände.
- GitHub-CI: `pip check`, `pytest -q`, `scripts/smoke-whisper.py` (Whisper Tiny, synthetisches Deutsch/Englisch), `scripts/build-linux.sh`, `scripts/smoke-linux.sh` (installiertes Paket in Xvfb und virtuellem PulseAudio).

---

## Ehrliche Grenzen

- **Fedora Linux (`x86_64`)** wird lokal und im Fedora-45-CI-Container mit Xvfb und virtuellem PulseAudio getestet.
- **Windows (`x64`)** wird auf einem GitHub-`windows-2022`-Runner gebaut und per Selbsttest, portabler ZIP und Inno-Setup-Installer geprüft. Ein echter Desktop-Einfügetest mit realer Tastatur und realen Anwendungen findet in CI nicht statt.
- **Wayland-Portale** (`GlobalShortcuts` / `RemoteDesktop`): D-Bus-Aufbau, Token-Speicherung, Signal-Header und Fehlerpfade sind per Unit-Test geprüft. Die echte Freigabe auf GNOME/KDE wurde nicht automatisch durchgeklickt; ohne Freigabe bleibt die Zwischenablage das Sicherheitsnetz. Der Portal-Vertrag sieht vor, dass ein ungültiger `restore_token` ignoriert und neu gefragt wird – ein bereits widerrufener Token kann deshalb beim Start einen erneuten Systemdialog auslösen, den der Nutzer ablehnen kann.
- **macOS** (`CGEvent`) bleibt ein Quellcodepfad ohne automatische Paketierung oder CI-Ausführung.
- **SenseVoice** ist im Katalog mit Prüfsumme hinterlegt, wurde aber nicht mit echtem asiatischem Audio getestet.
- **Alle Sprachtests** nutzen ausschließlich synthetisches Audio (`espeak-ng`/WAV), nie das Mikrofon des Eigentümers oder einen echten Desktop.
