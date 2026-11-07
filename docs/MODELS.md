# Lokale Modelle

Die Spracherkennung nutzt **Whisper** in einem Format für
[whisper.cpp](https://github.com/ggml-org/whisper.cpp). Für lokale
Textkorrektur verwendet Voicewright **GGUF** mit
[llama.cpp](https://github.com/ggml-org/llama.cpp). Die Dateiformate sind
verschieden. Die lokale Korrektur erwartet eine einzelne Qwen3-GGUF-Datei
mit höchstens 2 GiB. Eine passende Dateiendung allein reicht für die
Kompatibilität nicht aus.

Ein Modell muss auf den Rechner geladen werden, bevor es ohne Internet
arbeitet. Die App nutzt dafür ihren Modellordner. Die Installationspakete
enthalten keine Modellgewichte. Die Lizenz eines Modells ist von der
MIT-Lizenz des App-Codes getrennt. Prüfe bei importierten Dateien die Herkunft
und die Lizenz des Originalmodells und der Konvertierung.

## Importprüfung

Beim Import reicht die Dateiendung nicht aus. Für Whisper prüft die App die
GGML-Kennung und einen plausiblen Wortschatz. Für GGUF prüft sie Version,
Anzahl der Tensoren und Metadaten sowie die Mindestgröße. Vertauschte Formate
und unvollständige Dateien werden abgelehnt. Vor jeder Verwendung prüft die App
die gespeicherte Datei erneut. Die Prüfung ersetzt keine vollständige
Modellvalidierung durch die jeweilige Laufzeit.

## Modellkatalog

| Modell | Downloadgröße | Format | Lizenz |
| --- | ---: | --- | --- |
| Whisper Tiny | 78 MB | GGML | MIT |
| Whisper Base | 148 MB | GGML | MIT |
| Whisper Small | 488 MB | GGML | MIT |
| Whisper Medium | 1,53 GB | GGML | MIT |
| Whisper Large-v3 | 3,10 GB | GGML | MIT |
| Whisper Large-v3-Turbo | 1,62 GB | GGML | MIT |
| Qwen3-0.6B-Q8_0 | 639 MB | GGUF | Apache-2.0 |

Die Größen sind gerundete Dateigrößen. Der Arbeitsspeicherbedarf ist höher
und hängt von Modell und Aufnahme ab. Die erste Version verwendet die CPU.
Die Whisper-Dateien stammen aus einem festgelegten Stand des
[whisper.cpp-Katalogs](https://huggingface.co/ggerganov/whisper.cpp/tree/5359861c739e955e79d9a303bcbc70fb988958b1).
Die GGUF-Datei stammt aus einem festgelegten Stand des
[Qwen-Katalogs](https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/tree/23749fefcc72300e3a2ad315e1317431b06b590a).
Die Prüfsummen stammen aus den Dateimetadaten der beiden Kataloge.

## Auswahl

- Kleine mehrsprachige Whisper-Modelle sind ein guter Ausgangspunkt für
  Deutsch und Englisch. Größere Modelle benötigen mehr RAM und Rechenzeit.
- Wähle bei gemischten Diktaten die automatische Spracherkennung, sofern
  das gewählte Modell sie unterstützt.
- Eine optionale lokale Textkorrektur benötigt ein zusätzliches Modell. Lass
  Korrektur und Übersetzung ausgeschaltet, wenn du den reinen erkannten Text
  verwenden möchtest.

Nur der Modellkatalog der installierten App bestimmt, welche Dateien direkt
zum Download angeboten werden. Parakeet-Dateien für ONNX gehören zu einem
anderen Laufzeitsystem und sind mit der Whisper-Schnittstelle inkompatibel.
