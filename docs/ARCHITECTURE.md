# Architektur

Voicewright ist eine eigenständige Anwendung im Repository `mixxermannipro/Voicewright`. Der Produktname wurde mit dem Repository-Namen vereinheitlicht. Eine belastbare Marken- und Namensprüfung steht noch aus und gehört zu Issue #28.

## Technische Entscheidungen

- Tauri 2 zeigt die React-Oberfläche in der Webansicht des Betriebssystems. Rust verwaltet Aufnahme, Sitzung, Modelle, Schlüssel und Einfügen. Die Oberfläche hat keinen allgemeinen Zugriff auf Netzwerk, Dateien oder Shell.
- CPAL öffnet das gewählte Mikrofon. Die App begrenzt die Aufnahme im Speicher und wandelt die Kanäle in Mono mit 16 kHz um. whisper.cpp erkennt Sprache auf der CPU. Eigene Sprachmodelle müssen zum gewählten Modellformat passen.
- Die Aufnahme gehört einer Sitzung mit einem Abbruchsignal. Erst nach Abschluss oder Abbruch kann die nächste Sitzung beginnen. Ein Shortcut startet die Aufnahme, ohne die Hauptansicht zu aktivieren. Die App prüft das Zielfenster erneut vor dem Einfügen. Ergebnisse bleiben bei einem Fokuswechsel zum manuellen Kopieren verfügbar. Eine reine Zustandsmaschine entprellt Tastatur-Bursts und Auto-Wiederholung, erkennt verlorene Tastenlöse-Ereignisse nach einer kurzen Wartezeit und trennt Diktat-, Stopp- und Abbruchtasten. Jede Sitzung trägt eine Generation; ein Abbruch erhöht sie, sodass ein spätes Ergebnis weder den Status überschreibt noch Text einfügt. Beim automatischen Tippen wird der Fokus zwischen kurzen Unicode-Blöcken erneut geprüft, damit ein Abbruch oder Fensterwechsel nicht unbemerkt weiter tippt.
- llama.cpp läuft als mitgeliefertes separates Programm. Damit bleiben die GGML-Bibliotheken von Whisper und llama.cpp getrennt. Die App übergibt Text und Einstellungen über eine Pipe und beendet das eigene Programm beim Abbruch. Keine Shell und kein lokaler Server sind erforderlich.
- Cloud-Korrektur ist optional. Anbieter erhalten beim Einsatz den erkannten Text und die Bearbeitungsanweisung. Die Schlüssel werden getrennt in der Schlüsselverwaltung des Betriebssystems gehalten. Ein Fehler in der Korrektur kann auf den Originaltext zurückfallen.
- Der Katalog verwendet feste Modellversionen, Größen und SHA-256-Werte. Ein unvollständiger Download ist nicht auswählbar. Modelle liegen getrennt von der App. Der Quellcode und die Modellgewichte haben eigene Lizenzen.

## Vergleich vor der Umsetzung

| Projekt | Entscheidung für Voicewright |
| --- | --- |
| [Handy](https://github.com/cjpais/Handy) | Bestätigt Tauri und eine lokale, vom Fenster getrennte Aufnahme als geeigneten Aufbau. Eigene Implementierung für Hotkeys, Modellstatus und Zielprüfung. |
| [OpenWhispr](https://github.com/OpenWhispr/openwhispr) | Zeigt die Kombination aus lokaler Erkennung, Parakeet und optionalen Cloud-Anbietern. Wir verwenden Tauri statt Electron und trennen Anbieterprotokolle von der lokalen Erkennung. |
| [Murmur](https://github.com/EricSekyere/murmur) | Bestätigt Rust, Tauri und getrennte lokale Textkorrektur. Wir konzentrieren die erste Version auf kurze Diktate ohne Aufzeichnungshistorie. |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) | Gewählte Whisper-Laufzeit für mehrsprachige GGML-Gewichte. CPU ist der gemeinsame Ausgangspunkt. |
| [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) | Kandidat für Parakeet. Benötigt speziell konvertierte, kompatible ONNX-Dateien und eine eigene Prüfung der Gewichte und Laufzeit. |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | Gewählte GGUF-Laufzeit für lokale Korrektur mit einem kompatiblen Qwen3-Modell. |

Für die erste Linux-Implementierung verwenden wir X11 für globale Tasten. Wayland erfordert eine eigene Anbindung an die jeweilige Desktop-Umgebung. Eine Aufnahme über das App-Fenster mit manuellem Kopieren bleibt dort verfügbar. Die Details und Prüfergebnisse stehen in [PLATFORM_SUPPORT.md](PLATFORM_SUPPORT.md) und [PROGRESS.md](PROGRESS.md).
