# Testanleitung

Die konkreten Ergebnisse stehen in [PROGRESS.md](PROGRESS.md). Führe nach
den [Installationsschritten](INSTALLATION.md) diese Prüfungen aus:

```sh
npm run check
npm run lint
npm test
npm run build
cargo fmt --manifest-path src-tauri/Cargo.toml --all -- --check
cargo fmt --manifest-path engines/cleanup/Cargo.toml --all -- --check
cargo clippy --manifest-path src-tauri/Cargo.toml --locked --all-targets -- -D warnings
cargo clippy --manifest-path engines/cleanup/Cargo.toml --locked --all-targets -- -D warnings
cargo test --manifest-path src-tauri/Cargo.toml --locked
cargo test --manifest-path engines/cleanup/Cargo.toml --locked
npm audit --audit-level=high
```

Der GitHub-Ablauf prüft zusätzlich beide Rust-Abhängigkeitslisten mit
`cargo audit`. Dafür wird `cargo-audit` aus RustSec benötigt.

## Modelltests mit echten Gewichten

Diese Tests laufen getrennt von den Standardprüfungen. Verwende das
Whisper-Base- und das Qwen3-0.6B-Q8_0-Modell aus dem [Katalog](MODELS.md).
Setze die beiden Modellpfade auf deine lokalen, geprüften Dateien.

Für den Sprachtest kann man unter Linux mit eSpeak NG und FFmpeg
künstliche Sprachaufnahmen erzeugen. Das Testprogramm erwartet
Mono-WAV-Dateien mit 16 kHz und 16 Bit. Die Texte hier sind kurze Testsätze.

```sh
export VOXTAKT_FIXTURES="$(mktemp -d)"
espeak-ng -v de --stdout 'Guten Morgen. Das ist ein Diktat auf Deutsch.' |
  ffmpeg -loglevel error -i pipe:0 -ac 1 -ar 16000 -c:a pcm_s16le "$VOXTAKT_FIXTURES/de.wav"
espeak-ng -v en-us --stdout 'Good morning. This is a dictation test in English.' |
  ffmpeg -loglevel error -i pipe:0 -ac 1 -ar 16000 -c:a pcm_s16le "$VOXTAKT_FIXTURES/en.wav"

VOXTAKT_WHISPER_MODEL=/absoluter/pfad/ggml-base.bin \
  cargo test --manifest-path src-tauri/Cargo.toml --locked --test speech -- --ignored
VOXTAKT_TEST_GGUF=/absoluter/pfad/Qwen3-0.6B-Q8_0.gguf \
  cargo test --manifest-path engines/cleanup/Cargo.toml --locked --test protocol -- --ignored
```

Mit vorab bereitgestellten Modellen und gebauten Testprogrammen kannst du
den Testlauf auch ohne Netz wiederholen.

## Praktischer Durchlauf pro Plattform

1. Installiere das veröffentlichte Paket. Starte die App erstmals und gib
   Mikrofonzugriff. Lade ein Sprachmodell und bei Bedarf ein Korrekturmodell.
2. Schalte das Netzwerk ab. Diktiere je einen deutschen und englischen Satz
   mit „ä“, „ß“ und einem Zeilenumbruch. Prüfe die lokale Korrektur separat.
3. Starte mit einem leeren Textfeld in einer anderen App. Prüfe Halten und
   Umschalten, Wiederholung der Taste, Fokuswechsel während der Verarbeitung
   und Abbruch. Prüfe, wie der Text nach gescheiterter Einfügung abrufbar bleibt.
4. Prüfe mit Text und Bild in der Zwischenablage, was die Einfügung
   verändert. Prüfe Aufnahme bei geschlossenem Hauptfenster und den
   Wiedereinstieg über das Statussymbol.
5. Teste die Geräteauswahl mit zwei Mikrofonen. Trenne das aktive Mikrofon
   während einer Aufnahme. Simuliere verweigerten Mikrofonzugriff.
6. Unterbrich einen Download. Prüfe die Auswahl von unvollständigen
   Dateien und den Wechsel zwischen zwei fertigen Sprachmodellen.
7. Teste Anbieter getrennt und freiwillig mit kurzen Testtexten und
   Testschlüsseln. Prüfe Fehler für abgelehnten Schlüssel, überschrittenes
   Limit, Zeitüberschreitung und Verbindungsabbruch.

Notiere Version, Prozessor, RAM, Betriebssystem, Desktop-Sitzung, Modell und
Audiodauer. Miss Zeit bis zum nutzbaren Start, Arbeitsspeicher im Leerlauf,
Transkriptions- und Korrekturzeit sowie Zeit vom Aufnahmeende bis zum
Ergebnis. Gib an, ob die Modelle bereits geladen waren. Verwende für
Vergleiche dieselbe Aufnahme. Behandle Kompilierung, automatisierte Tests und
diesen praktischen Durchlauf als getrennte Nachweise.
