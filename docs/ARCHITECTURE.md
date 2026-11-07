# Architektur

VoxTakt ist eine eigenständige Anwendung im bereitgestellten Repository `mixxermannipro/speechy`. Der Produktname unterscheidet sie von vorhandenen Diktierprodukten namens Speechy. Die Vorprüfung umfasste öffentliche Web- und GitHub-Suchen und ersetzt keine Markenprüfung.

## Technische Entscheidungen

- Tauri 2 zeigt die React-Oberfläche in der Webansicht des Betriebssystems. Rust verwaltet Aufnahme, Sitzung, Modelle, Schlüssel und Einfügen. Die Oberfläche hat keinen allgemeinen Zugriff auf Netzwerk, Dateien oder Shell.
- CPAL öffnet das gewählte Mikrofon. Die App begrenzt die Aufnahme im Speicher und wandelt die Kanäle in Mono mit 16 kHz um. whisper.cpp erkennt Sprache auf der CPU. Eigene Sprachmodelle müssen zum gewählten Modellformat passen.
- Die Aufnahme gehört einer Sitzung mit einem Abbruchsignal. Erst nach Abschluss oder Abbruch kann die nächste Sitzung beginnen. Ein Shortcut startet die Aufnahme, ohne die Hauptansicht zu aktivieren. Die App prüft das Zielfenster erneut vor dem Einfügen. Ergebnisse bleiben bei einem Fokuswechsel zum manuellen Kopieren verfügbar.
- llama.cpp läuft als mitgeliefertes separates Programm. Damit bleiben die GGML-Bibliotheken von Whisper und llama.cpp getrennt. Die App übergibt Text und Einstellungen über eine Pipe und beendet das eigene Programm beim Abbruch. Keine Shell und kein lokaler Server sind erforderlich.
- Cloud-Korrektur ist optional. Anbieter erhalten beim Einsatz den erkannten Text und die Bearbeitungsanweisung. Die Schlüssel werden getrennt in der Schlüsselverwaltung des Betriebssystems gehalten. Ein Fehler in der Korrektur kann auf den Originaltext zurückfallen.
- Der Katalog verwendet feste Modellversionen, Größen und SHA-256-Werte. Ein unvollständiger Download ist nicht auswählbar. Modelle liegen getrennt von der App. Der Quellcode und die Modellgewichte haben eigene Lizenzen.

## Vergleich vor der Umsetzung

| Projekt | Entscheidung für VoxTakt |
| --- | --- |
| [Handy](https://github.com/cjpais/Handy) | Bestätigt Tauri und eine lokale, vom Fenster getrennte Aufnahme als geeigneten Aufbau. Eigene Implementierung für Hotkeys, Modellstatus und Zielprüfung. |
| [OpenWhispr](https://github.com/OpenWhispr/openwhispr) | Zeigt die Kombination aus lokaler Erkennung, Parakeet und optionalen Cloud-Anbietern. Wir verwenden Tauri statt Electron und trennen Anbieterprotokolle von der lokalen Erkennung. |
| [Murmur](https://github.com/EricSekyere/murmur) | Bestätigt Rust, Tauri und getrennte lokale Textkorrektur. Wir konzentrieren die erste Version auf kurze Diktate ohne Aufzeichnungshistorie. |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) | Gewählte Whisper-Laufzeit für mehrsprachige GGML-Gewichte. CPU ist der gemeinsame Ausgangspunkt. |
| [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) | Kandidat für Parakeet. Benötigt speziell konvertierte, kompatible ONNX-Dateien und eine eigene Prüfung der Gewichte und Laufzeit. |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | Gewählte GGUF-Laufzeit für lokale Korrektur mit einem kompatiblen Qwen3-Modell. |

Für die erste Linux-Implementierung verwenden wir X11 für globale Tasten. Wayland erfordert eine eigene Anbindung an die jeweilige Desktop-Umgebung. Eine Aufnahme über das App-Fenster mit manuellem Kopieren bleibt dort verfügbar. Die Details und Prüfergebnisse stehen in [PLATFORM_SUPPORT.md](PLATFORM_SUPPORT.md) und [PROGRESS.md](PROGRESS.md).
