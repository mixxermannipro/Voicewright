# Voicewright 2.0 – Entwurf

Stand: 25. November 2026
Status: Entwurf zur Freigabe
Branch: `feat/v2-dictation-suite`

## 1. Wofür

Voicewright soll das schnellste und angenehmste lokale Diktierwerkzeug für
Windows, Linux (Fedora, GNOME und KDE) und macOS werden.

Der Ablauf, den der Anwender erwartet:

1. Tastenkürzel drücken.
2. Sprechen.
3. Kurz tippen: Aufnahme läuft weiter, bis das Kürzel erneut getippt wird.
   Länger halten: Aufnahme endet beim Loslassen.
4. Der Text wird lokal bereinigt und direkt in das aktive Fenster geschrieben.

Alles läuft lokal. Kein Konto, keine Cloud-Pflicht, keine Telemetrie.

## 2. Ziele

- **Ein Kürzel, zwei Bedienungen gleichzeitig.** Tippen und Halten ohne
  Umschalten. Das ist der wichtigste Unterschied zu heute.
- **Direktes Einfügen** in das aktive Fenster auf allen drei Plattformen.
  Unter Wayland über das offizielle Desktop-Portal, nicht über Rohgeräte.
- **Sehr schnelle, lokale Bereinigung** mit mehreren Modellen zur Auswahl,
  jeweils mit Größe und geschätzter Zeit.
- **Sehr gute Spracherkennung** mit Parakeet V3 als Standard für europäische
  Sprachen und Whisper als Fallback für alle 99 Sprachen.
- **Intelligente Funktionen** im Sinne von Gemini Rambler: Stichpunkte,
  Aufgabenlisten, E-Mails, Befehle in natürlicher Sprache, Textbausteine.
- **Ruhiges Liquid-Glass-Design** mit Dark- und Light-Mode, weichen
  Animationen und klarer Bedienung.
- **Stabil und prüfbar.** Jede Stufe hat einen klaren Rückfallweg.

## 3. Nicht-Ziele

- Keine Cloud-Pflicht und kein Abo.
- Kein Keylogging, kein Root, kein `uinput` als Standardweg.
- Keine automatische Installation von Systempaketen.
- Keine Synchronisation zwischen Geräten.
- Keine echte Streaming-Transkription während des Sprechens in Version 2.0.
  Der Text erscheint nach dem Loslassen bzw. nach dem zweiten Tippen.
- Kein Training eigener Modelle.

## 4. Anti-Ziele

Diese Ergebnisse gelten als Fehlschlag, auch wenn die App technisch startet:

- Text landet im falschen Fenster oder geht verloren.
- Die Bereinigung erfindet Inhalte, ändert Zahlen, Namen oder Negationen.
- Die App braucht Root-Rechte oder ein dauerhaftes Keylogging.
- Die Oberfläche ruckelt oder die Aufnahme startet spürbar verzögert.
- Ein Plattformweg wird als „getestet" verkauft, obwohl er es nicht ist.

## 5. Vom Anwender entschieden

- Wayland: Portal plus Helfer-Rückfall, sonst Zwischenablage.
- Bereinigung: mehrere lokale Modelle mit Größe und geschätzter Zeit.
  Standard soll sehr schnell sein und ausreichende Qualität liefern.
- Spracherkennung: Parakeet **und** Whisper.
- Lieferung: ein Branch, ein Pull Request, viele kleine Commits.
- Zusätzlich: intelligente Funktionen wie bei Gemini Rambler.

## 6. Betrachtete Wege

### 6.1 Einfügen unter Wayland

| Weg | GNOME | KDE | wlroots | Bewertung |
|---|---|---|---|---|
| RemoteDesktop-Portal | ja (46+) | ja (6.1+) | nein | Offizieller Weg, einmalige Freigabe, kein Root. **Gewählt als erster Weg.** |
| `wtype` | nein | nein | ja | Sauber, aber nur wlroots. Rückfall. |
| `ydotool` | ja | ja | ja | Braucht Daemon und `/dev/uinput`. Letzter Rückfall. |
| Nur Zwischenablage | ja | ja | ja | Immer verfügbar. Sicherheitsnetz. |

Der Portalweg nutzt die Zwischenablage und sendet Strg+V über die vom
Portal erlaubte Tastatur. Damit funktioniert er auch in Terminals, wenn
der Anwender dort Strg+Shift+V wählt.

### 6.2 Lokale Bereinigung

| Weg | Qualität | Tempo | Download | Bewertung |
|---|---|---|---|---|
| Nur Regeln | vorhersehbar, aber flach | < 10 ms | 0 MB | Immer als erste Stufe. |
| Qwen3 0.6B Q4 | ausreichend für Grammatik und Füllwörter | ca. 0,4–1,5 s | 397 MB | **Standard.** |
| Qwen3 1.7B Q4 | deutlich besser | ca. 1–3 s | 1,1 GB | Optional für mehr Qualität. |
| Cloud | sehr gut | netzabhängig | 0 MB | Bleibt opt-in, nicht Standard. |

Kleine Modelle neigen dazu, korrekten Text unverändert zurückzugeben oder
Inhalte zu erfinden. Deshalb gibt es eine harte Schutzprüfung und einen
Rückfall auf die Regelstufe.

### 6.3 Spracherkennung

| Modell | Sprachen | Tempo (CPU) | Größe | Rolle |
|---|---|---|---|---|
| Parakeet TDT 0.6B v3 int8 | 25 europäische | ca. 0,05–0,15× Echtzeit | 675 MB | **Standard für DE/EN/EU.** |
| Whisper large-v3-turbo | 99 | ca. 0,8–1,5× Echtzeit | 1,6 GB | Beste Qualität mit GPU. |
| Whisper small | 99 | ca. 0,3–0,5× Echtzeit | 485 MB | Kleiner Allrounder. |
| Whisper tiny/base | 99 | sehr schnell | 75/145 MB | Test und schwache Geräte. |
| SenseVoice int8 | zh/en/ja/ko/yue | ca. 0,08× Echtzeit | 166 MB | Asiatische Sprachen. |

Zeitangaben sind Schätzungen für einen modernen 8-Kern-Prozessor und
10 Sekunden Audio. Sie werden in der Oberfläche als „ca." angezeigt und
nach dem ersten echten Lauf durch gemessene Werte ersetzt.

## 7. Aufbau

```
Mikrofon → Recorder → VAD/Trimmen → Engine (Parakeet/Whisper/SenseVoice)
        → Smart-Formatierung → Regeln → optionales lokales LLM
        → Schutzprüfung → Einfügen (Portal/Paste/Tippen/Zwischenablage)
```

Jede Stufe ist einzeln abschaltbar. Bei einem Fehler fällt die Pipeline auf
die vorherige Stufe zurück, nie auf einen leeren Text.

### 7.1 Module

| Datei | Aufgabe |
|---|---|
| `hotkey.py` | Hybrid-Erkennung (Tippen/Halten), pynput- und Portal-Backend |
| `portals.py` | D-Bus: GlobalShortcuts und RemoteDesktop (nur Linux) |
| `injector.py` | Einfügen: Windows, macOS, X11, Wayland-Portal, wtype, ydotool |
| `engines.py` | Whisper (faster-whisper) und sherpa-onnx (Parakeet, SenseVoice) |
| `models.py` | Modellkatalog, geprüfte Downloads, Fortschritt, Abbruch |
| `cleanup.py` | Regeln, Prompt, LLM-Client, Schutzprüfung, Rückfall |
| `runtime.py` | llama.cpp herunterladen, starten, überwachen, beenden |
| `smart.py` | Gesprochene Zeichen, Befehle, Struktur, Textbausteine |
| `stats.py` | Lokale Statistik (Wörter, Zeit, Verlauf) |
| `ui/theme.py` | Farben, Radien, Schatten, Animationen, Hell/Dunkel |
| `ui/widgets.py` | Glas-Karten, Schalter, Segmente, animierte Seiten |
| `ui/settings_window.py` | Hauptfenster mit sieben Bereichen |
| `ui/overlay.py` | Schwebende Glas-Pille mit Pegel und Status |
| `ui/onboarding.py` | Ersteinrichtung in vier Schritten |

### 7.2 Zustandsmaschine

```
idle ──Kürzel↓──► recording ──Kürzel↑ kurz──► recording (bleibt)
                      │                           │
                      │◄──── Kürzel↓ ─────────────┘
                      │
                      ├──Kürzel↑ lang──► processing → idle
                      └──Esc───────────► idle (verworfen)
```

- Ein Druck startet sofort die Aufnahme. Kein Warten auf das Loslassen.
- Loslassen vor 350 ms: Aufnahme bleibt an (Tipp-Betrieb).
- Loslassen nach 350 ms: Aufnahme endet (Halte-Betrieb).
- Zweiter Druck beendet eine getippte Aufnahme.
- Esc verwirft.
- Tastenwiederholung wird ignoriert.
- Ein Wechsel des Kürzels während der Aufnahme beendet die Aufnahme sauber.

### 7.3 Einfügen

Reihenfolge der Wege:

1. **Windows:** Zwischenablage + Strg+V über `SendInput`.
2. **macOS:** Zwischenablage + Cmd+V über `CGEventPost` (Bedienungshilfen).
3. **Linux X11:** Zwischenablage + Strg+V über XTEST.
4. **Linux Wayland:** Portal → `wtype` → `ydotool` → Zwischenablage.
5. **Immer:** Wenn nichts davon klappt, bleibt der Text in der
   Zwischenablage und die App sagt es deutlich.

Die Zwischenablage wird gesichert und nach dem Einfügen wiederhergestellt,
sofern der Anwender sie nicht inzwischen selbst geändert hat.

### 7.4 Bereinigung

**Stufe 0 – gesprochene Formatierung** (immer, < 5 ms):
Komma, Punkt, Fragezeichen, neue Zeile, neuer Absatz, Aufzählung,
Stichpunkt, Anführungszeichen – deutsch und englisch. Geschützte Zitate
und Code bleiben unverändert. Keine Betriebssystembefehle.

**Stufe 1 – Regeln** (immer, < 10 ms):
Füllwörter, Stottern, Doppelwörter, Selbstkorrekturen („nein, ich meine"),
Zeichensetzung, Groß-/Kleinschreibung, Abstände, Wörterbuch,
Ersetzungen, Zahlen.

**Stufe 2 – lokales Sprachmodell** (opt-in, 0,4–3 s):
Qwen3 0.6B oder 1.7B über einen mitgelieferten llama.cpp-Server, oder
Ollama/LM Studio, wenn vorhanden. Stile: Sauber, Minimal, Formell,
Locker, Notizen, E-Mail, Eigene Anweisung.

**Stufe 3 – Schutzprüfung** (immer, < 20 ms):
Zahlen, Datumsangaben, URLs, E-Mails, Code, Namen aus dem Wörterbuch und
Negationen müssen erhalten bleiben. Längenverhältnis und Prompt-Reste
werden geprüft. Bei Verstoß: Ergebnis von Stufe 1.

**Stufe 4 – Cloud** (nur wenn ausdrücklich aktiviert):
Bestehende Anbieter bleiben erhalten. Standard aus.

### 7.5 Intelligente Funktionen

- **Stichpunkte und Aufgaben:** „Stichpunkte", „als Liste", „Aufgaben"
  am Anfang oder Ende. Erkennt „erstens/zweitens", „1. 2. 3." und
  „außerdem". Erzeugt Aufzählung oder Kästchen.
- **E-Mail:** „als E-Mail" erzeugt Anrede, Absätze und Gruß.
- **Notizen:** „als Notizen" erzeugt Überschrift und kurze Abschnitte.
- **Befehle in natürlicher Sprache:** „mach das kürzer", „formeller",
  „übersetze auf Englisch", „füge Emojis hinzu", „korrigiere nur die
  Grammatik". Wirken auf das gerade Diktierte.
- **Auswahl umschreiben:** eigenes Kürzel (Standard `Ctrl+Alt+Space`).
  Liest die aktuelle Auswahl, bereinigt oder formt sie um und schreibt
  sie zurück. Lokal, außer Cloud ist ausdrücklich an.
- **Textbausteine:** „Textbaustein <Name>" setzt einen gespeicherten Text
  ein. Verwaltung in der Oberfläche.
- **Wörterbuch und Ersetzungen:** Eigennamen richtig schreiben,
  häufige Hörfehler automatisch ersetzen.
- **Statistik:** Wörter, Diktate, gesparte Zeit, letzte Einträge. Lokal.
- **Emojis:** nur auf ausdrücklichen Wunsch, nie ungefragt.

## 8. Modellkatalog

### 8.1 Spracherkennung

| ID | Engine | Größe | Sprachen | Tempo | Genauigkeit | Hinweis |
|---|---|---|---|---|---|---|
| `parakeet-v3` | sherpa-onnx | 675 MB | 25 EU | ★★★★★ | ★★★★☆ | Standard für Deutsch/Englisch |
| `parakeet-v2` | sherpa-onnx | 660 MB | EN | ★★★★★ | ★★★★☆ | Nur Englisch |
| `sensevoice` | sherpa-onnx | 166 MB | zh/en/ja/ko/yue | ★★★★★ | ★★★☆☆ | Asiatische Sprachen |
| `whisper-small` | faster-whisper | 485 MB | 99 | ★★★☆☆ | ★★★☆☆ | Kleiner Allrounder |
| `whisper-medium` | faster-whisper | 1,5 GB | 99 | ★★☆☆☆ | ★★★★☆ | CPU-lastig |
| `whisper-large-v3-turbo` | faster-whisper | 1,6 GB | 99 | ★★★☆☆ | ★★★★★ | Mit GPU sehr gut |
| `whisper-large-v3` | faster-whisper | 3,1 GB | 99 | ★☆☆☆☆ | ★★★★★ | Maximale Qualität |
| `whisper-tiny` / `base` | faster-whisper | 75/145 MB | 99 | ★★★★★ | ★☆☆☆☆ | Test |

Downloads werden mit fester Version, Größe und SHA-256 geprüft, sind
fortsetzbar und lassen sich abbrechen. Parakeet und SenseVoice kommen
als einzelne ONNX-Dateien von Hugging Face, Whisper als CTranslate2-Modell.

### 8.2 Bereinigung

| ID | Modell | Größe | Zeit (CPU) | Qualität | Lizenz |
|---|---|---|---|---|---|
| `off` | Aus | 0 MB | 0 ms | – | – |
| `rules` | Regeln | 0 MB | < 10 ms | ★★☆☆☆ | MIT |
| `qwen3-0.6b-q4` | Qwen3 0.6B Q4_K_M | 397 MB | ca. 0,4–1,5 s | ★★★☆☆ | Apache-2.0 |
| `qwen3-1.7b-q4` | Qwen3 1.7B Q4_K_M | 1,1 GB | ca. 1–3 s | ★★★★☆ | Apache-2.0 |
| `qwen3-0.6b-q8` | Qwen3 0.6B Q8_0 | 639 MB | ca. 0,6–2 s | ★★★☆☆ | Apache-2.0 |

Die Zeiten gelten für einen Absatz mit etwa 60 Wörtern auf einem modernen
Prozessor ohne GPU. Mit GPU sind sie deutlich kürzer. Die App zeigt nach
dem ersten Lauf die gemessene Zeit an.

## 9. Oberfläche

### 9.1 Gestaltung

- **Fenster:** randlos, 1.040 × 720, Radius 22 px, weicher äußerer Schatten,
  1 px helle Innenkante.
- **Seitenleiste:** 220 px, Glas, sieben Bereiche, unten Status.
- **Karten:** Radius 18 px, halbtransparent, feine Kante, obere Lichtkante,
  weicher Schatten. Kein harter Blur, sondern geschichtete Transparenz –
  das ist auf allen drei Plattformen schnell und stabil.
- **Farben:** Indigo als Akzent, Rot für Aufnahme, Grün für Erfolg, Amber
  für Warnung. Hell und Dunkel aus derselben Token-Liste.
- **Schrift:** Systemschrift (SF Pro, Segoe UI, Cantarell/Inter). Titel
  28 px, Abschnitt 17 px, Text 13 px, Hinweis 11 px.
- **Bewegung:** 180–260 ms, `cubic-bezier(0.22, 1, 0.36, 1)`. Seiten
  blenden ein und gleiten 8 px. Schalter federn. Pegel glättet.
  „Bewegung reduzieren" ist eine Einstellung.
- **Barrierefreiheit:** sichtbarer Fokusring, Tastaturbedienung,
  ausreichender Kontrast, keine Information nur über Farbe.

### 9.2 Bereiche

1. **Übersicht:** große Aufnahmefläche, aktives Modell, Kürzel, Statistik,
   letztes Diktat.
2. **Modelle:** Karten mit Größe, Sprachen, Tempo, Genauigkeit, Zeit,
   Download, Aktivieren, Löschen.
3. **Bereinigung:** Regeln/lokale KI/Cloud, Modellkarten mit Zeit,
   Stil, Sprache, Wörterbuch, Schutzprüfung.
4. **Intelligenz:** gesprochene Zeichen, Befehle, Struktur, Textbausteine,
   Auswahl-Kürzel, Emojis.
5. **Ausgabe:** Einfügeweg, Wayland-Status, Terminal-Taste, Leerzeichen,
   Töne, Overlay.
6. **Verlauf:** Einträge, roher Text, Kopieren, Statistik.
7. **Info:** Version, Pfade, Protokolle, Diagnose, Lizenzen.

### 9.3 Overlay

Eine Glas-Pille (300 × 64) am unteren oder oberen Rand. Sie zeigt
Aufnahmepegel, Zeit und Zustand, stiehlt keinen Fokus und verschwindet
nach Erfolg oder Fehler weich. Sie morpht zwischen den Zuständen, statt
hart umzuschalten.

### 9.4 Ersteinrichtung

Vier Schritte: Willkommen → Modell wählen und laden → Mikrofon testen →
Kürzel und Einfügen prüfen. Downloads starten nie ohne Klick.

## 10. Konfiguration

Schema-Version 2. Neue Schlüssel mit sicheren Standardwerten:

```json
{
  "version": 2,
  "hotkey_mode": "hybrid",
  "tap_threshold_ms": 350,
  "insert_mode": "auto",
  "paste_shortcut": "auto",
  "restore_clipboard": true,
  "clipboard_restore_ms": 400,
  "speech_model": "parakeet-v3",
  "cleanup_provider": "rules",
  "cleanup_model": "qwen3-0.6b-q4",
  "llm_runtime": "auto",
  "smart_formatting": true,
  "structure_mode": "auto",
  "command_mode": true,
  "transform_hotkey": "ctrl+alt+space",
  "snippets": [],
  "replacements": {},
  "theme": "system",
  "reduce_motion": false,
  "stats_enabled": true,
  "wayland_consent": false
}
```

Alte Einstellungen werden verlustfrei übernommen. Unbekannte Schlüssel
bleiben erhalten. Eine kaputte Datei wird gesichert, nicht überschrieben.

## 11. Sicherheit und Datenschutz

- Audio und Text bleiben lokal, außer der Anwender aktiviert Cloud.
- Der Wayland-Weg nutzt ausschließlich das offizielle Portal mit
  ausdrücklicher Freigabe. Kein `uinput`, kein Root, kein Keylogging.
- Die Freigabe wird gespeichert, aber nie stillschweigend erneuert.
- API-Schlüssel bleiben im Systemschlüsselbund.
- Downloads werden per SHA-256 geprüft; Größe und Struktur zusätzlich.
- Das lokale Sprachmodell läuft auf `127.0.0.1` mit zufälligem Port und
  wird beim Beenden geschlossen.
- Protokolle enthalten keine diktierten Texte.
- Der Verlauf ist standardmäßig aus.

## 12. Fehler und Rückfall

| Fehler | Verhalten |
|---|---|
| Kein Mikrofon | Klare Meldung, Einstellungen öffnen |
| Modell fehlt | Hinweis, Download anbieten, kein Absturz |
| Portal verweigert | `wtype`, `ydotool`, dann Zwischenablage |
| Einfügen scheitert | Text bleibt in der Zwischenablage, Meldung |
| LLM antwortet schlecht | Schutzprüfung verwirft, Regeltext bleibt |
| LLM stürzt ab | Server neu starten, sonst Regeln |
| Download bricht ab | Fortsetzen oder neu beginnen |
| Konfiguration kaputt | Sicherung anlegen, Standardwerte |

## 13. Prüfplan

**Automatisch (lokal und CI):**

- Hybrid-Zustandsmaschine: Tippen, Halten, Wiederholung, Esc, Zusatztasten.
- Gesprochene Formatierung: deutsche und englische Goldfälle.
- Regeln: Füllwörter, Selbstkorrektur, Wörterbuch, Zahlen.
- Schutzprüfung: Zahlen, URLs, E-Mails, Negationen, Länge, Prompt-Reste.
- Befehle und Struktur: Erkennung und Ergebnis.
- Textbausteine und Ersetzungen.
- Modellkatalog: eindeutige IDs, Größen, Hashes.
- Konfiguration: v1 → v2, kaputte Datei, Import.
- Einfügen: Auswahl des Weges mit nachgebildeter Plattform.
- Zwischenablage: Sichern und Wiederherstellen.
- Portal: Aufbau der D-Bus-Nachrichten mit nachgebildeter Verbindung.
- Oberfläche: Aufbau aller Seiten und Overlay-Zustände ohne Bildschirm.
- Bestehender Whisper-Smoke-Test bleibt Pflicht.

**Nur auf echter Hardware möglich (wird klar gekennzeichnet):**

- Wayland-Portal auf GNOME und KDE, inklusive Freigabedialog.
- Echtes Mikrofon und echte Tastatur.
- Windows und macOS, inklusive Bedienungshilfen.
- Paketinstallation auf fremden Distributionen.

## 14. Lieferung

Ein Branch, ein Pull Request, zwölf Commits:

1. Konfiguration und Migration.
2. Hybrid-Tastenkürzel.
3. Einfügen auf allen Plattformen.
4. Wayland-Portale.
5. Parakeet, SenseVoice und Modellkatalog.
6. Lokale Bereinigung, Laufzeit und Schutzprüfung.
7. Intelligente Funktionen.
8. Liquid-Glass-Oberfläche.
9. Statistik und Verlauf.
10. Dokumentation und Grenzen.
11. Tests.
12. Paketierung für Windows und macOS.

Der Pull Request wird erst nach grüner CI und eigener Prüfung als bereit
markiert. Gemergt wird nur nach ausdrücklichem „ja".

## 15. Antworten auf die Prüferfragen

Ein unabhängiger Bau-Prüfer hat den Entwurf gelesen. Diese acht Punkte waren
offen. So werden sie entschieden:

**1. Gilt der Entwurf vor der Wayland-Regel in `AGENTS.md`?**
Ja. Der Anwender hat dem Portal-Weg ausdrücklich zugestimmt. Die Regel wird
präzisiert, nicht aufgeweicht: Erlaubt ist das offizielle Portal mit
ausdrücklicher Freigabe. Verboten bleiben Root, `uinput` als Standardweg und
Keylogging. `ydotool` wird **nicht** mitgeliefert und ist standardmäßig aus;
es lässt sich nur bewusst in den Einstellungen aktivieren, mit Warnhinweis.

**2. Wayland ohne GlobalShortcuts-Portal?**
Dann bleibt der Desktop-Kurzbefehl (`voicewright --toggle`) mit reiner
Tipp-Bedienung. Halten und Esc gibt es dort nicht. Die Oberfläche sagt das
pro Sitzung klar an, statt es zu verschweigen. Zwei Portal-Freigaben
(Kurzbefehle und Fernsteuerung) sind zumutbar und werden in der
Ersteinrichtung zusammen erklärt.

**3. Downloads und Prüfsummen?**
Während der Entwicklung werden Parakeet V3 (675 MB) und Qwen3 0.6B Q4
(397 MB) wirklich geladen, damit die Engines echt getestet sind. Die
SHA-256-Werte stammen aus den Hugging-Face-Prüfsummen (LFS-OID), nicht aus
dem Gedächtnis. CI bleibt bei Whisper-tiny; der Parakeet-Test ist ein
eigener, ausdrücklich gestarteter Smoke-Test. Kein 675-MB-Download pro
CI-Lauf.

**4. Neue Abhängigkeiten und fremde Programme?**
- `sherpa-onnx` als **optionales** Extra `asr`. Fehlt es, bleibt Whisper.
- `jeepney` (reines Python, klein) für D-Bus. Fehlt es, bleibt `wtype`.
- `python-xlib` optional für X11. Fehlt es, bleibt `xdotool`, dann
  Zwischenablage.
- Windows und macOS nutzen nur `ctypes`, keine neuen Pakete.
- llama.cpp wird **nicht** zur Laufzeit blind geladen. Der Anwender lädt es
  in der Oberfläche mit sichtbarer Version und Prüfsumme, oder nutzt
  Ollama/LM Studio. Ohne Laufzeit bleibt die Regelstufe.

**5. Alte Einstellungen?**
Nichts wird stillschweigend entfernt. Jeder v1-Schlüssel behält einen Platz:
`whisper_*` und `beam_size`/`vad_filter`/`initial_prompt` unter „Modelle →
Erweitert", `output_language`/`cleanup_style`/`custom_instructions` unter
„Bereinigung", `add_trailing_space`/`start_minimized`/`ui_language`/
`history_limit` unter „Ausgabe" und „Info". Die Migration bildet
`whisper_model` auf `speech_model` ab und lädt nichts nach.

**6. Overlay unter Wayland?**
Best effort. Das Fenster wird vom Compositor platziert; die App merkt sich
die zuletzt bekannte Position und dokumentiert die Einschränkung. Kein
Layer-Shell-Zusatzpaket in 2.0. GNOME bekommt die schlichtere Variante.

**7. Umformulierungsbefehle und Schutzprüfung?**
Ausdrücklich diktierte Befehle („kürzer", „formeller", „übersetze")
schalten die Prüfung in einen eigenen Modus: Zahlen, Datumsangaben, URLs,
E-Mails und Code müssen erhalten bleiben, die Wortreihenfolge nicht.
Ohne lokale KI und ohne Cloud erscheint eine klare Meldung, dass für diesen
Befehl ein Modell nötig ist – der Text bleibt unverändert.

**8. Auswahl umschreiben?**
Nur mit Sicherheitsbedingung: Nach Strg+C muss sich die Zwischenablage
geändert haben. Sonst bricht die Funktion mit „Keine Auswahl erkannt" ab und
schreibt nichts zurück. Damit kann kein alter Inhalt erneut eingefügt werden.

## 16. Offene Punkte für den Bau

- Genaue Portal-Antworten auf GNOME und KDE können erst am echten Desktop
  geprüft werden. Der Code muss beide Antwortformen tolerieren.
- llama.cpp-Binärdateien werden auf eine feste Version gesetzt. Wenn ein
  System sie nicht ausführen kann, bleibt der Regelweg.
- Die Zeitangaben sind Startwerte und werden nach Messungen angepasst.
- Windows- und macOS-Pakete werden gebaut, aber hier nicht praktisch
  geprüft. Das wird im README und im PR offen benannt.
