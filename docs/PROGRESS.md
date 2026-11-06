# Arbeitsstand und Übergabe an Codex Cloud

- Repository: `mixxermannipro/speechy`. Arbeitszweig: `feat/dictation-foundation`.
- Zielversion: `0.1.0-alpha.1`. Main und eine Veröffentlichung sind getrennte Schritte.
- Architektur und Datenfluss: [ARCHITECTURE.md](ARCHITECTURE.md).

## Vorhanden

- Tauri-App mit Rust-Aufnahme, Aufnahmezuständen, Halten und Umschalten, Abbruch, Anzeige im Systembereich und manueller Kopiermöglichkeit. Automatisches Einfügen ist für X11 und Windows vorgesehen und an die Prüfung des Zielfokus gebunden. macOS verwendet vorerst Kopieren, Wayland startet über das App-Fenster.
- Mehrsprachige Whisper-Modelle und Qwen3-Korrektur. Der Modellkatalog nutzt feste Quellen und Prüfsummen. Der separate llama.cpp-Prozess verarbeitet Text lokal.
- Cloud-Anbieter OpenAI, Gemini, Anthropic, xAI, OpenRouter, Mistral, Groq, DeepSeek, Together AI, Fireworks und Cerebras sowie ein frei konfigurierbarer kompatibler Zugang. Schlüssel im Betriebssystem-Speicher. API-Tests verwenden nachgebildete Antworten.
- Paket- und Prüfskripte für Ubuntu, Windows x64 und Apple Silicon. Windows und macOS wurden bisher nicht gebaut oder praktisch geprüft.

## Belegt

- Linux-Build der Rust-App mit 19 erfolgreichen Standardtests. Der zusätzliche echte Whisper-Test läuft separat.
- Korrekturprogramm mit 6 erfolgreichen Standardtests, Formatprüfung und Clippy. Der zusätzliche echte Qwen3-Test bestand mit je einem deutschen und englischen Satz und abgeschaltetem Netzwerk. AMD Ryzen 7 7800X3D, gemessen 0,714 s bzw. 0,698 s ab Start des Korrekturprozesses inklusive Modellladen. Keine Ende-zu-Ende-Messung.
- Die Bibliotheksprüfung für npm meldete eine moderate Schwachstelle in einem Entwicklungswerkzeug. Die fertige Oberfläche ist separat zu prüfen.

## Weiterarbeit

1. Oberfläche und native Befehle zusammen prüfen. `npm ci`, `npm run check`, `npm run lint`, `npm test`, `npm run build`, `npm run prepare:engine`, dann Rust-Befehle aus [TESTING.md](TESTING.md). Beide Cargo-Lockdateien erhalten.
2. Offline mit echtem Whisper-Base-Modell, Sprachdateien und Qwen3 prüfen. Danach auf den echten Zielsystemen Mikrofon, Halten/Umschalten, Fokuswechsel, Texte mit Umlauten, Systembereich, Berechtigungen und Installationsstart praktisch prüfen. Die lokale Fedora-Sitzung ist Wayland. X11 kann in einem virtuellen Bildschirm separat getestet werden.
3. Fehlende Funktionen ergänzen: macOS-Zugriffshilfe für Einfügen, Wayland-Tastenkürzel über das Desktop-Portal, sicheres Einfügen mehrzeiliger Texte, Parakeet V3 mit geprüftem ONNX-Modell, bessere Spracherkennung bei Stille, GPU-Erkennung und Hardware-Beschleunigung mit CPU-Rückfall, Systemstart und Audiosignale, optionale Diagnose. Eigene Modelle brauchen stärkere Kompatibilitätsprüfung vor der Auswahl.
4. Paketierung und Sicherheit prüfen. Prüfe Lizenzhinweise der mitgelieferten Bibliotheken, RustSec, gemessenen Start und Speicherbedarf, die Windows- und macOS-Builds und die drei Paketarten. Echtes Anbieter-Login und die Passwortspeicher wurden noch nicht praktisch geprüft.
5. Erst mit bestätigter Prüfkette den Arbeitszweig zusammenführen. Danach das dokumentierte Tag für eine Vorabversion erstellen. Signierung, macOS-Notarisierung und authentifizierte Updates sind noch offen.
