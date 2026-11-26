# Änderungen

## 2.0.0

- **Hybrid-Bedienung (`dictation.py`):** Ein Kürzel für Tippen (Umschalten), Halten (Push-to-Talk) und Abbruch mit `Esc`.
- **Einrichtungsassistent (`ui/onboarding.py`):** Vier Schritte mit Willkommen, Modellwahl, Live-Mikrofonpegel und Tastenkürzel-/Einfügetest; jederzeit über Einstellungen und Tray erreichbar.
- **Lokale Spracherkennung (`engines.py`, `models.py`):** `sherpa-onnx` ist jetzt Standardabhängigkeit, damit Parakeet TDT 0.6B v3 und SenseVoice ohne Extra laufen. Fehlt die Bibliothek auf einer Plattform, wählt Voicewright automatisch ein lauffähiges Whisper-Modell. Alle Modelle bleiben per Größe und SHA-256 geprüft.
- **Zwei globale Kürzel (`hotkey.py`, `portals.py`):** Diktat (`Ctrl+Shift+Leertaste`) und Auswahl umschreiben (`Ctrl+Alt+Leertaste`) teilen sich einen Listener bzw. eine `GlobalShortcuts`-Sitzung; gleiche oder überlappende Belegungen werden ignoriert und in Einstellungen und Assistent gemeldet.
- **Wayland-Freigabe bleibt erhalten (`portals.py`, `injector.py`):** `RemoteDesktop` nutzt `persist_mode=2` und speichert den `restore_token`. Solange die Freigabe gültig ist, wird die Sitzung beim Start ohne neuen Dialog wiederhergestellt. Ein widerrufener Token wird verworfen; nach einer erneuten Systemabfrage fällt Voicewright sauber auf `wtype`/Zwischenablage zurück. Der offene Berechtigungsdialog blockiert weder die Oberfläche noch die Tastatureingabe, und ein Neustart hinterlässt keinen zweiten Shortcut-Listener.
- **Windows gehärtet (`inject.py`, `runtime.py`):** Korrekte 64-Bit-`INPUT`/`KEYBDINPUT`-Strukturen inklusive `ULONG_PTR`, `SendInput`-Signaturen, UTF-16 für Umlaute und Emoji sowie `CREATE_NO_WINDOW` für `llama-server.exe`.
- **Zwischenablage (`injector.py`):** Stellt den vorherigen Inhalt nur wieder her, wenn die Zwischenablage noch den eingefügten Text enthält – eine neue Kopie des Nutzers bleibt unangetastet. Schnell aufeinanderfolgende Diktate und „Auswahl umschreiben“ verlieren den ursprünglichen Inhalt nicht.
- **Paketierung & CI:** Windows-Job (Tests, PyInstaller, Selbsttest, ZIP, Inno-Setup-Installer, SHA-256), Tag-Release-Workflow für Linux und Windows, dynamische Version in `voicewright.iss` und `scripts/build.bat`. Inno Setup erhält absolute Pfade, Prüfsummen nutzen LF, und nur der Veröffentlichungs-Job hat Schreibrechte.
- **Unterstützte Interpreter:** Python 3.11–3.14. Fedora 45 liefert standardmäßig 3.15; README, Installer und Release-Hinweise nennen deshalb ausdrücklich `python3.14`. `numpy` ist auf `<2.5` begrenzt, weil 2.5 Python 3.11 ausschließt.
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
