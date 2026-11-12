<p align="center">
  <img src="src/voicewright/assets/icon.png" width="120" alt="Voicewright">
</p>

<h1 align="center">Voicewright</h1>

<p align="center">
  <b>Überall diktieren.</b> Tastenkürzel drücken, sprechen – der Text wird lokal transkribiert,
  bereinigt und direkt dort eingefügt, wo dein Cursor steht.<br>
  Windows · macOS · Linux (Fedora, X11 &amp; Wayland)
</p>

---

## Funktionen

| | |
|---|---|
| 🎙️ **Globales Tastenkürzel** | Frei wählbar (Standard: `Ctrl+Shift+Space`), funktioniert in jeder App |
| 🔁 **Zwei Modi** | **Umschalten** (einmal drücken = Start, nochmal drücken = fertig) oder **Push-to-Talk** (gedrückt halten, loslassen = fertig) |
| 🔒 **100 % lokale Spracherkennung** | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2). Modelle werden in der App heruntergeladen, mit Empfehlung passend zur Hardware |
| ✨ **KI-Bereinigung – Bring Your Own Key** | Google AI Studio (Gemini), OpenAI, Anthropic, Groq, OpenRouter, Mistral oder jeder OpenAI-kompatible Server. Modellliste wird live per API geladen |
| 🏠 **Lokale Bereinigung** | Ollama, LM Studio oder Offline-Regeln ganz ohne KI |
| 🌍 **Übersetzung** | Optional: Ausgabe in einer anderen Sprache (per KI) oder offline nach Englisch (Whisper) |
| 📋 **Einfügen am Cursor** | Über Zwischenablage + Einfügen-Kürzel (Zwischenablage wird wiederhergestellt) oder simuliertes Tippen |
| 🟣 **Aufnahme-Anzeige** | Schwebende Pille mit Pegel, stiehlt keinen Fokus |
| 🗂️ **Verlauf, Wörterbuch, eigene Anweisungen** | Alles lokal gespeichert, API-Keys im System-Schlüsselbund |
| 🖥️ **CLI-Steuerung** | `voicewright --toggle` – ideal für Wayland-Desktop-Tastenkürzel |

## Schnellstart

1. **Installieren** (siehe unten) und Voicewright starten – es erscheint im Infobereich / in der Menüleiste.
2. Beim ersten Start öffnet sich **Einstellungen → Sprachmodell**. Das empfohlene Modell (★) herunterladen.
   - Ohne GPU: `small` · Mit NVIDIA-GPU: `large-v3-turbo`
3. **KI-Bereinigung**: Anbieter wählen, API-Key einfügen (z. B. kostenlos bei [Google AI Studio](https://aistudio.google.com/apikey)), „Modelle laden“, Modell wählen, „Verbindung testen“.
4. In ein beliebiges Textfeld klicken, `Ctrl+Shift+Space` drücken, sprechen, nochmal drücken – fertig.

## Installation

### Fertige Builds (GitHub Releases)

| System | Datei | Hinweis |
|---|---|---|
| Windows | `Voicewright-…-windows-x64-setup.exe` oder `…-portable.zip` | Kein Admin nötig |
| macOS (Apple Silicon) | `Voicewright-…-macos-arm64.dmg` | App nach *Programme* ziehen. Unsigniert: beim ersten Start Rechtsklick → *Öffnen* |
| Linux | `Voicewright-…-linux-x86_64.tar.gz` | Entpacken, `./Voicewright/install.sh` ausführen |

### Aus dem Quellcode

Voraussetzung: Python 3.10–3.12.

**Fedora**
```bash
./scripts/setup_fedora.sh      # installiert portaudio, wl-clipboard, ydotool … und ein venv
./scripts/run.sh
```

**macOS / andere Linux-Distributionen**
```bash
./scripts/run.sh               # legt beim ersten Start .venv an und installiert alles
```

**Windows**
```bat
scripts\run.bat
```

Oder klassisch: `pip install -e .` und dann `voicewright`.

## Plattform-Hinweise

### Linux / Fedora (Wayland)

Fedora nutzt standardmäßig Wayland. Wayland erlaubt Apps aus Sicherheitsgründen kein globales Mithören von Tasten und kein Tippen in andere Fenster. Voicewright unterstützt dafür drei Wege:

1. **evdev-Backend (empfohlen, inkl. Push-to-Talk):**
   ```bash
   sudo usermod -aG input $USER     # danach ab- und wieder anmelden
   ```
2. **Desktop-Tastenkürzel** (nur Umschalt-Modus): In *GNOME-Einstellungen → Tastatur → Eigene Tastenkürzel* bzw. *KDE-Systemeinstellungen → Kurzbefehle* einen Befehl anlegen:
   ```
   voicewright --toggle
   ```
   und in Voicewright als Hotkey-Backend „Keins“ wählen.
3. **X11-Sitzung** – dort funktioniert alles ohne Zusatzschritte.

**Text einfügen unter Wayland** braucht `wl-clipboard` und `ydotool`:
```bash
sudo dnf install wl-clipboard ydotool
sudo systemctl enable --now ydotool
```
Falls `ydotool` einen Socket-Fehler meldet, `ydotoold` als eigener Benutzer starten oder `YDOTOOL_SOCKET` passend setzen. Unter wlroots-Compositors (Sway, Hyprland) geht alternativ `wtype`. Ohne diese Werkzeuge kopiert Voicewright den Text in die Zwischenablage, und du fügst ihn selbst ein.

> In Terminals funktioniert `Ctrl+V` oft nicht – unter *Ausgabe → Einfüge-Kürzel* kann `Ctrl+Shift+V` gewählt werden.

### macOS

Beim ersten Start fragt macOS nach Berechtigungen. Erteile sie unter *Systemeinstellungen → Datenschutz & Sicherheit*:
- **Mikrofon** – für die Aufnahme
- **Bedienungshilfen** – für das Einfügen von Text (simulierte Tastendrücke)
- **Eingabeüberwachung** – für das globale Tastenkürzel

Nach dem Erteilen Voicewright einmal neu starten. Die App läuft als Menüleisten-App (kein Dock-Symbol).

### Windows

Läuft ohne weitere Schritte. Für GPU-Beschleunigung mit NVIDIA werden die CUDA-12-Bibliotheken **cuBLAS** und **cuDNN 9** benötigt (siehe [faster-whisper GPU](https://github.com/SYSTRAN/faster-whisper#gpu)). Fehlen sie, fällt Voicewright automatisch auf die CPU zurück.

## Sprachmodelle

| Modell | Größe | Sprachen | Empfehlung |
|---|---|---|---|
| `tiny` | 75 MB | mehrsprachig | Testen, sehr schwache Hardware |
| `base` | 145 MB | mehrsprachig | Schnell, deutliche Sprache |
| `small` ★ | 485 MB | mehrsprachig | **Beste Wahl für CPU / Laptop** |
| `medium` | 1,5 GB | mehrsprachig | Genau, langsam auf CPU |
| `large-v3-turbo` ★ | 1,6 GB | mehrsprachig | **Beste Wahl mit GPU** oder schneller CPU |
| `large-v3` | 3,1 GB | mehrsprachig | Maximale Genauigkeit |
| `distil-large-v3`, `small.en`, `base.en` | | nur Englisch | Schneller für reines Englisch |

Modelle werden von Hugging Face geladen (abbrechbar, fortsetzbar) und liegen im Datenordner (siehe *Info*-Tab). Die Offline-Übersetzung nach Englisch („Aufgabe“) funktioniert am besten mit `medium`/`large-v3`; `large-v3-turbo` ist dafür nicht trainiert. Für Übersetzungen in andere Sprachen die KI-Ausgabesprache verwenden.

## KI-Bereinigung (Bring Your Own Key)

| Anbieter | Key | Empfohlene Modelle |
|---|---|---|
| Google AI Studio (Gemini) | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | `gemini-2.5-flash`, `gemini-2.5-flash-lite` |
| OpenAI | platform.openai.com | `gpt-4.1-mini`, `gpt-4.1-nano` |
| Anthropic | console.anthropic.com | `claude-3-5-haiku-latest` |
| Groq | console.groq.com | `llama-3.3-70b-versatile` |
| OpenRouter | openrouter.ai | beliebig |
| Mistral | console.mistral.ai | `mistral-small-latest` |
| Ollama (lokal) | – | `llama3.2`, `qwen2.5:7b`, `gemma3:4b` |
| LM Studio (lokal) | – | beliebig |
| Eigener Server | optional | jeder OpenAI-kompatible Endpunkt |
| Offline-Regeln | – | entfernt Füllwörter/Wiederholungen ohne KI |

Mit „Modelle laden“ wird die aktuelle Modellliste direkt vom Anbieter geholt; jeder Modellname kann auch frei eingetippt werden. API-Keys liegen im System-Schlüsselbund (Windows Credential Manager, macOS-Schlüsselbund, Secret Service/KWallet) – falls keiner verfügbar ist, in einer Datei mit Rechten nur für den Benutzer. Alternativ per Umgebungsvariable, z. B. `VOICEWRIGHT_GEMINI_API_KEY`.

**Stile:** Sauber (Standard) · Minimal · Formell · Locker – plus eigene Anweisungen und ein Wörterbuch für Namen und Fachbegriffe (wird auch an Whisper übergeben).

Schlägt die KI-Anfrage fehl (offline, Limit erreicht …), greifen auf Wunsch die Offline-Regeln – dein Diktat geht nie verloren und landet zusätzlich im Verlauf.

## Kommandozeile

```
voicewright               # starten bzw. Einstellungen der laufenden Instanz öffnen
voicewright --toggle      # Aufnahme starten/beenden
voicewright --start | --stop | --cancel | --show | --quit
voicewright --minimized   # im Infobereich starten
voicewright --debug       # ausführliches Logging
```

## Datenablage

| | Windows | macOS | Linux |
|---|---|---|---|
| Konfiguration | `%APPDATA%\Voicewright` | `~/Library/Application Support/Voicewright` | `~/.config/voicewright` |
| Modelle, Verlauf, Logs | `%LOCALAPPDATA%\Voicewright` | `~/Library/Application Support/Voicewright` | `~/.local/share/voicewright` |

Überschreibbar mit `VOICEWRIGHT_CONFIG_DIR` / `VOICEWRIGHT_DATA_DIR`.

**Datenschutz:** Audio verlässt nie deinen Rechner. Nur der transkribierte Text wird – falls ein Cloud-Anbieter gewählt ist – zur Bereinigung an diesen Anbieter gesendet.

## Release bauen

Die GitHub-Action `.github/workflows/release.yml` baut für Windows, macOS und Linux:

```bash
git tag v1.0.0
git push origin v1.0.0
```

→ Tests laufen, PyInstaller-Builds werden erstellt (Windows: Setup + portable ZIP, macOS: DMG, Linux: tar.gz mit Installer), und ein GitHub-Release mit allen Dateien wird angelegt. Über *Actions → Build & Release → Run workflow* lassen sich Builds auch ohne Tag erzeugen (als Artefakte).

Lokal bauen: `./scripts/build.sh` bzw. `scripts\build.bat` → Ergebnis in `dist/`.

## Projektstruktur

```
src/voicewright/
├── main.py            Einstieg, CLI, Single-Instance-IPC
├── app.py             Controller: Hotkey → Aufnahme → Whisper → Bereinigung → Einfügen
├── hotkey.py          Globale Hotkeys (pynput / evdev), Halten & Umschalten
├── audio.py           Mikrofonaufnahme (16 kHz), Stille-Trimmung, Signaltöne
├── transcriber.py     faster-whisper, CPU/GPU-Auswahl mit Fallback
├── models.py          Modellkatalog + fortsetzbarer Downloader
├── cleanup.py         BYOK-Anbieter, lokale LLMs, Offline-Regeln, Prompt
├── injector.py        Zwischenablage + Einfügen / Tippen (inkl. Wayland-Tools)
├── keystore.py        API-Keys im System-Schlüsselbund
├── config.py          JSON-Konfiguration
├── history.py         Lokaler Verlauf
├── autostart.py       Beim Anmelden starten (alle Plattformen)
├── i18n.py            Deutsch / Englisch
└── ui/                Einstellungsfenster, Aufnahme-Overlay, Hotkey-Recorder
```

Tests: `pip install pytest numpy && python -m pytest`

## Fehlerbehebung

| Problem | Lösung |
|---|---|
| Tastenkürzel reagiert nicht (Linux/Wayland) | Gruppe `input` (siehe oben) oder `voicewright --toggle` als Desktop-Kürzel |
| Tastenkürzel reagiert nicht (macOS) | Bedienungshilfen + Eingabeüberwachung erlauben, App neu starten |
| Text wird nicht eingefügt, nur kopiert | Linux: `ydotool`/`wl-clipboard` installieren · macOS: Bedienungshilfen erlauben |
| Falsche Zeichen beim Einfügen | „Einfüge-Verzögerung“ erhöhen (z. B. 250 ms) |
| Langsame Transkription | Kleineres Modell oder GPU nutzen; „Modell im Speicher halten“ aktivieren |
| Mikrofon-Fehler | In *Allgemein* das Eingabegerät wählen; Linux: `sudo dnf install portaudio` |
| KI-Fehler „HTTP 429“ | Anbieter-Limit erreicht – anderes Modell/Anbieter oder kurz warten |

Logs: *Einstellungen → Info → Log-Ordner öffnen*.

## Danksagung

Inspiriert von [OpenWhisper](https://github.com/Knuckles92/OpenWhisper), [OpenWhispr](https://github.com/OpenWhispr/openwhispr), [yap](https://github.com/nicremo/yap) und Wispr Flow. Voicewright ist eine eigenständige Neuentwicklung.

## Lizenz

MIT – siehe [LICENSE](LICENSE).
