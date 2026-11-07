# Arbeitsstand und Übergabe

Der Alpha-Stand aus [PR #1](https://github.com/mixxermannipro/Voicewright/pull/1)
wurde am 7. November 2026 nach `main` integriert. Der Zweig
`feat/dictation-foundation` ist damit abgeschlossen. Die nächsten Aufgaben
laufen über eigene Zweige und Pull Requests gegen `main`.

Produktname und Repository heißen jetzt **Voicewright**. Die Anwendung
übernimmt vorhandene Einstellungen und Modelle aus dem alten Datenordner
`de.voxtakt.desktop` beim ersten Start. Bereits gespeicherte API-Schlüssel
werden weiterhin gelesen; beim nächsten Speichern werden sie unter dem neuen
Dienstnamen abgelegt. Für diese Version gibt es noch kein veröffentlichtes
Installationspaket.

## Prompt-Härtung – Implementierung in Issue #17

Auf einem separaten Feature-Branch liegt eine erweiterte Standardanweisung,
ein opt-in-Vorschautest mit noch nicht gespeicherten Einstellungen und eine
konservative Ausgabevalidierung. Beim normalen Diktat greift bei abgewiesenen
KI-Ausgaben der vorhandene Original-Fallback (sofern aktiviert). Für
Cloud-Vorschauen ist ein ausdrücklicher Klick mit Bestätigung erforderlich;
dabei werden Testtext und Anweisung an den gewählten Anbieter gesendet,
keine Mikrofonaufnahme.

**Noch ausstehend:** vollständige npm-/Cargo-Prüfungen und echte
Modell-Evaluation in Windows/macOS/Linux. Die Golden-Fälle in
[TESTING.md](TESTING.md) sind eine manuelle Checkliste, kein bereits
bestandener Qualitätsnachweis. Der Validator erkennt keine subtilen
Bedeutungsänderungen oder Halluzinationen.

## Sichere Einstellungsverwaltung (Issue #26)

Ein neuer Branch ergänzt Schema-Versionierung, Migration alter Alpha-Settings,
atomare Datenspeicherung mit Backup unlesbarer Konfiguration, lokalen
JSON-Export ohne API-Schlüssel, Import mit Vorschau, Zurücksetzen als
Entwurf und sicheres Abschalten des Cloud-Modus bei Import.
Die [Anleitung](SETTINGS_BACKUP.md) beschreibt die Datenarten,
Rollback-Möglichkeit und bewusst nicht implementierte vollständige
Löschung persönlicher Modell-/Keyringdaten.

**Teststatus:** Rust/npm, Dateidialoge und reale Plattform-Tests sind
vereinbarungsgemäß für die spätere Abnahme ausstehend. Ein gemergter
Code-PR bedeutet noch keine bestätigte Funktionsfähigkeit. Issue #26
bleibt für vollständige Löschroutine und Tests offen.

## Was vorhanden ist

- Deutsch-englische Tauri-Oberfläche mit Übersicht, Kurzanleitung, Mikrofonwahl, konfigurierbarem Tastenkürzel, Halten und Umschalten, Aufnahmepegel, Abbruch, Statussymbol und Kopiermöglichkeit. Einstellungen bleiben nach Neustart erhalten. Die App speichert keinen Diktatverlauf.
- Lokale Whisper-Erkennung auf der CPU. Der Katalog enthält die mehrsprachigen Modelle Tiny, Base, Small, Medium, Large-v3 und Large-v3 Turbo. Downloads verwenden feste Modellversionen, Größen und SHA-256-Prüfsummen. Es gibt Abbruch, Fortsetzen, Löschen und Import. Beim Import prüft die App Formatkennung, GGUF-Version und Grundstruktur; vertauschte Formate sowie beschädigte oder unvollständige Dateien werden abgelehnt. Nur Whisper Base ist praktisch getestet.
- Lokale Textkorrektur mit mitgeliefertem llama.cpp-Programm und Qwen3-0.6B-Q8_0. Eigene dichte Qwen3-GGUF-Modelle können importiert werden. Anweisungen, Vorlagen, Wörterliste und Ziel für Übersetzung sind einstellbar. Bei Fehlern bleibt der Originaltext verfügbar.
- Optionale Cloud-Korrektur mit OpenAI, Gemini, Anthropic, xAI, OpenRouter, Mistral, Groq, DeepSeek, Together AI, Fireworks, Cerebras und eigenen kompatiblen Servern. Die App sendet Text nur im aktivierten Cloud-Modus. Schlüssel werden im Passwortspeicher des Betriebssystems abgelegt.
- Direkte Texteingabe unter Windows und X11 mit Prüfung des Zielfensters. Bei abweichendem Fokus oder gehaltenen Sondertasten bleibt der Text zum Kopieren in der App. Automatisches Tippen bleibt auf kurze einzeilige Texte beschränkt. macOS nutzt Kopieren. Wayland kann über die App aufnehmen und kopieren.
- Vollständige [Vorlagen für die GitHub-Automatisierung](github-workflows/README.md). GitHub hat das Schreiben nach `.github/workflows/` abgelehnt, da der verwendeten Anmeldung die Berechtigung `workflow` fehlt. Die Dateien bleiben unter `docs/github-workflows/` gesichert, bis ein Token mit dieser Berechtigung verfügbar ist.

## Geprüft am 6. November 2026

| Prüfung | Ergebnis |
| --- | --- |
| Oberfläche am 7. November 2026 | TypeScript, ESLint, 3 Vitest-Tests und Vite-Produktionsbuild nach dem Branding-Wechsel bestanden. |
| Rust-App am 7. November 2026 | Formatierung, Clippy mit `-D warnings` und 30 Standardtests im Podman-Build-Image bestanden. Darunter neue Tests für Burst-Ereignisse, verlorene Tastenlöse-Ereignisse, Abbruch während jeder Phase und Shortcut-Rollback. |
| Korrekturprozess am 7. November 2026 | Formatierung, Clippy mit `-D warnings`, 3 Standardtests und 3 Protokolltests bestanden; der Modelltest bleibt ohne Gewichte übersprungen. |
| Oberfläche am 6. November 2026 | TypeScript, ESLint, 3 Vitest-Tests, Vite-Produktionsbuild und npm-Audit bestanden. npm meldet 0 Schwachstellen. |
| Rust-App auf Linux x64 | Formatierung, Clippy und 22 Standardtests bestanden. Davon 11 für Anbieter mit nachgebildeten Antworten. Keine bezahlten oder echten Cloud-Aufrufe. |
| Whisper Base | SHA-256 geprüft. Je eine künstliche deutsche und englische WAV-Datei wurde in einem Container ohne Netzwerk erkannt. Zusammen 2,08 s für beide Aufrufe inklusive Laden. |
| Qwen3-0.6B-Q8_0 | SHA-256 geprüft. Formatierung, Clippy und 6 Standardtests bestanden. Je eine deutsche und englische Textkorrektur im Container ohne Netzwerk. Einzellauf ab Prozessstart inklusive Laden 0,714 s bzw. 0,698 s. |
| Linux-DEB und Fensterwechsel | Debug-DEB gebaut und in Debian 12 ohne Systeminstallation entpackt. App startete unter X11 im virtuellen Bildschirm. In zwei netzlosen Durchläufen speiste PulseAudio künstliches deutsches Mikrofon-Audio ein. Halten führte zu einem deutschen Satz im externen GTK-Textfeld. Umschalten mit lokalem Qwen3 übersetzte den Text und fügte ihn auf Englisch ein. Die Tests prüfen den Ablauf und ein Stichwort. Beim Beispieldiktat gab es Erkennungsfehler. |
| Start und Speicher | AMD Ryzen 7 7800X3D, 30 GiB System-RAM. Debug-Paket bis zum sichtbaren Fenster etwa 0,50 s. App-Hauptprozess im Leerlauf etwa 169 MiB RSS (belegter physischer Speicher), ohne getrennte WebKit-Prozesse. Keine Messung bis zur ersten nutzbaren Eingabe und keine vollständige Latenzmessung. |
| RustSec | Beide Abhängigkeitslisten gescannt. Keine als Schwachstelle eingestuften Treffer. App-Liste mit 8 Warnungen zu nicht gepflegten Bibliotheken und einer unsicheren GLib-Schnittstelle in dieser Warnungszahl. Engine-Liste ohne Warnung. Warnungen vor Freigabe bewerten. |

Der virtuelle Linux-Test verwendet künstliche Eingabe und kein physisches
Mikrofon. Windows, macOS und Linux Wayland wurden praktisch noch nicht
geprüft. NSIS, DMG und AppImage sind noch nicht gebaut. Die aktuelle
x64-Build-Konfiguration der lokalen Korrektur verwendet AVX2 und verwandte
Prozessorfunktionen. Ein Starttest auf älteren Prozessoren fehlt. Die
Hotkey-Zustandsmaschine ist durch Unit-Tests abgedeckt; echte Tastaturtests
auf Windows, macOS und X11 sowie Sleep/Wake- und RDP-Tests stehen aus.

## Nächste Schritte

1. **Prüfungen auf GitHub aktivieren.** Folge [github-workflows/README.md](github-workflows/README.md). Prüfe den Änderungsvorschlag auf Ubuntu und baue NSIS, DMG und AppImage. Prüfe, ob jedes Paket das Korrekturprogramm und alle nötigen Systembibliotheken enthält. Das lokale DEB ist ein Debug-Testpaket. Die Erstfreigabe braucht einen optimierten Paketbau.
2. **Echte Desktop-Tests nachholen.** Prüfe physisches Mikrofon, Gerätewechsel und Trennung, Tastenkürzel und Abbruch während jeder Phase, Fokuswechsel, Sonderzeichen, Kopieren, Statussymbol bei geschlossenem Fenster und Installationsstart. Prüfe Passwortspeicher und Anbieter freiwillig mit eigenen Testschlüsseln. Wiederhole den automatisierten [Linux-Test](TESTING.md) mit dem endgültigen Paket.
3. **Einfügen und Wayland ergänzen.** Baue die macOS-Zugriffshilfe zur Prüfung des fokussierten Elements und zur Texteingabe. Prüfe das Desktop-Portal für Wayland-Tastenkürzel. Unterstütze mehrzeiligen Text nur mit sicherer, bestätigter Einfügung und Erhalt von Bild- und Textdaten in der Zwischenablage. Die aktuelle X11-Prüfung kennt das Fenster. Sie kann Wechsel zwischen Feldern derselben App nicht zuverlässig erkennen.
4. **Modelle und Leistung vervollständigen.** Prüfe echte Downloads inklusive Unterbrechung, Bereichsantwort, Prüfsummenfehler und freien Speicher. Ergänze bessere Stille-Erkennung, robustere Modellimport-Prüfung, Parakeet V3 mit geprüftem sherpa-onnx-Modell, GPU-Erkennung und Beschleunigung mit CPU-Rückfall. Teste portable x64-Builds auf älteren CPUs. Dokumentiere Ende-zu-Ende-Zeiten, Spitzen-RAM und GPU-Verhalten auf echter Hardware.
5. **Restliche Bedienung und Veröffentlichung.** Ergänze Systemstart, optionale Audiosignale und Diagnose. Manche System- und Anbieterfehler sind nur einsprachig. Prüfe die Lizenzhinweise der tatsächlich ausgelieferten Bibliotheken und RustSec-Warnungen. Führe den Arbeitszweig mit `main` zusammen, wenn die Prüfungen passen. Folge dann [RELEASE.md](RELEASE.md). Signierung, macOS-Notarisierung und authentifizierte Updates sind offen.

Für den Einstieg in den Quellcode siehe [ARCHITECTURE.md](ARCHITECTURE.md).
Die Befehle stehen in [INSTALLATION.md](INSTALLATION.md) und
[TESTING.md](TESTING.md). Die beiden Cargo-Lockdateien und
`package-lock.json` gehören zum Stand.

---

## Sicherheitsreview (Issue #27)

Das [Bedrohungsmodell](THREAT_MODEL.md) dokumentiert die Vertrauensgrenzen
zwischen Mikrofon, nativem ASR/LLM-Prozess, optionalem Cloud-Anbieter,
Modellserver, Tauri-Webview, OS-Zwischenablage und fremdem Editor.
Es enthält konkrete Restrisiken und Sicherheits-Regressionen S01–S10.
**Dies ist ein Dokumentations- und Planungsstand, kein bestandener
Security-Test oder abgeschlossener Audit.** Ohne reale OS-/Netzwerktests,
Paket-Signierung und Nachweise für Hochrisiken bleibt Issue #27 ein
Release-Blocker.

