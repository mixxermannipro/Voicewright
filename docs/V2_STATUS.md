# Voicewright 2.0 – Arbeitsstand

Diese Datei ist der laufende Zwischenstand für den Umbau auf Voicewright 2.0.
Sie wird mit jedem Commit aktualisiert, damit der Stand nie veraltet.
Der freigegebene Entwurf steht in
[superpowers/specs/2026-11-25-voicewright-v2-design.md](superpowers/specs/2026-11-25-voicewright-v2-design.md).

**Branch:** `feat/v2-dictation-suite` · **Stand:** 25. November 2026

---

## Was fertig und geprüft ist

### Spracherkennung

- **Parakeet TDT 0.6B v3 (int8)** läuft echt über `sherpa-onnx 2.0.3`.
  Der entscheidende Punkt: Das Modell ist ein NeMo-TDT-Export und braucht
  `model_type="nemo_transducer"` **und** `feature_dim=128`. Ohne diese beiden
  Werte bricht sherpa-onnx beim Decoder ab
  (`'vocab_size' does not exist in the metadata`).
- Gemessen auf diesem Rechner (CPU, 4 Threads):

  | Test | Audio | Erkennung | Ergebnis |
  | --- | --- | --- | --- |
  | englisches Beispiel (JFK) | 3,8 s | 0,159 s | Text exakt richtig |
  | deutsches Beispiel (espeak-ng) | 5,4 s | 0,198 s | bis auf einen Namen richtig („Villa“ statt „Müller“) |

  Das sind rund 0,04× Echtzeit. Der Name ist ein bekannter Schwachpunkt
  synthetischer Stimmen, kein Absturz und kein Modellfehler.
- **Whisper large-v3-turbo** und die übrigen Whisper-Modelle sind im Katalog
  mit echten Größen und SHA-256 hinterlegt; der Test mit dem vorhandenen
  Whisper-Smoke-Test steht noch aus.
- **SenseVoice** ist im Katalog (asiatische Sprachen), echt geladen und
  geprüft wurde es noch nicht.

### Lokale Textbereinigung

- **Qwen3 0.6B (Q4_K_M)** läuft echt über **llama.cpp b12728** als eigener
  Server auf `127.0.0.1` mit freiem Port.
- Gemessene Antwortzeit für einen kurzen Satz: **0,25–0,5 s**.
- Mit zwei Beispielsätzen (Few-Shot) wird aus
  „ich möchte morgen um neun uhr einen termin mit frau müller vereinbaren“
  → „Ich möchte morgen um neun Uhr einen Termin mit Frau Müller vereinbaren.“
- Ohne Beispiele bleibt das Modell bei Kleinbuchstaben. Die Beispiele sind
  deshalb fester Bestandteil des Prompts, nicht Deko.

### Schutzprüfung (`guard.py`)

Fängt die Fehler ab, die kleine Modelle wirklich machen:

- Protokollreste (`<|im_start|>`, Codeblöcke, `think`-Blöcke)
- Assistenten-Floskeln („Hier ist der korrigierte Text …“)
- zu kurze oder zu lange Ausgabe
- verlorene oder veränderte Zahlen
- verlorene URLs, E-Mail-Adressen und Code
- verlorene Wörter aus dem eigenen Wörterbuch
- verlorene Verneinungen im strengen Modus

Bei Auffälligkeit bleibt der Regeltext stehen. Es gibt **keine** semantische
Garantie – das steht auch so im Entwurf.

### Gerüst

- `config.py`: Schema 2 mit Migration aus Version 1, alle neuen Schlüssel,
  alte Einstellungen bleiben erhalten.
- `models.py`: Katalog mit echten Prüfsummen, fortsetzbarem Download,
  Prüfung nach dem Laden, llama.cpp-Runtime pro Plattform.
- `dictation.py`: Hybrid-Zustandsmaschine (kurz tippen = umschalten,
  halten = Push-to-Talk, Escape = abbrechen).
- `inject.py`: Einfügen über SendInput (Windows), CGEvent (macOS),
  XTEST/xdotool (X11), wtype, ydotool (nur nach Freigabe) und Portal.
- `portals.py`: GlobalShortcuts und RemoteDesktop über D-Bus.
- `smart.py`: gesprochene Satzzeichen, Strukturwünsche, Umformulierungs-
  befehle, Textbausteine, Wortersetzungen.
- `stats.py`: lokale Statistik ohne Textinhalt.
- `ui/theme.py`, `ui/widgets.py`: Farbwerte für Hell/Dunkel und die
  Glas-Bausteine (Karten, Schalter, Segmentwahl, Navigation).

---

## Was gerade in Arbeit ist

**Die Oberfläche.** `ui/theme.py` und `ui/widgets.py` sind geschrieben.
Als Nächstes entsteht `ui/settings_window.py` neu: Seitenleiste statt Reiter,
Seiten für Diktat, Modelle, Bereinigung, Smartes, Ausgabe, Verlauf und Über.
Danach `ui/overlay.py` im gleichen Stil.

**Wichtig:** In diesem Zwischenstand startet die App **noch nicht**. Das alte
`ui/settings_window.py` importiert Funktionen, die es nach dem Umbau nicht
mehr gibt (`recommended_model`, `cuda_available`). Das ist kein Fehler im
fertigen Programm, sondern die Baustelle. Der Draft-PR ist deshalb ausdrücklich
nicht merge-fähig.

---

## Nächste Schritte

1. `ui/settings_window.py` neu bauen, alle Einstellungen aus Version 1
   bekommen einen Platz.
2. `ui/overlay.py` neu gestalten.
3. `app.py` an die neue Oberfläche anschließen (Signale, Seitenwechsel).
4. Tests ergänzen: Hybrid-Zustandsmaschine, Schutzprüfung, smarte Befehle,
   Konfigurationsmigration, Einfüge-Reihenfolge.
5. Echte Smoke-Tests: Whisper large-v3-turbo, SenseVoice, kompletter Ablauf
   mit synthetischem Audio.
6. Dokumentation: README, AGENTS.md, CHANGELOG, Installationshinweise.
7. Prüflauf `python -m pytest -q` und der Whisper-Smoke-Test aus der README.
8. Erst dann PR aus dem Draft holen und um Merge bitten.

---

## Ehrliche Grenzen

- Getestet wurde auf **Fedora 45, Wayland, x86_64**. Windows und macOS sind
  nur über die Codepfade abgedeckt, nicht real ausgeführt.
- Das Einfügen unter Wayland über das Portal braucht eine Zustimmung des
  Desktops. Ohne Zustimmung bleibt der Text in der Zwischenablage. Der
  Freigabedialog wurde hier **nicht** automatisiert durchgeklickt.
- Alle Sprachtests nutzen synthetisches Audio (espeak-ng und vorhandene
  WAV-Dateien), nie das Mikrofon des Eigentümers.
- Die Geschwindigkeitswerte gelten für diesen Rechner und diese Threadzahl,
  nicht als Versprechen für jede Hardware.
