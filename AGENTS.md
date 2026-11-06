# VoxTakt

VoxTakt ist eine Desktop-App für lokales Diktat. Die Oberfläche verwendet
Tauri 2, React und TypeScript. Rust steuert Aufnahme und Verarbeitung.

## Struktur

- `src/` enthält die Oberfläche und ihre Tests.
- `src-tauri/` enthält den Hauptprozess und die Paket-Einstellungen.
- `engines/cleanup/` enthält den separaten Prozess für lokale Textkorrektur.
- `docs/` enthält Architektur, Testanleitung und Stand der Arbeiten.

## Befehle

- Vorbereitung und Start stehen in [INSTALLATION.md](docs/INSTALLATION.md).
- Oberfläche: `npm run check`, `npm run lint`, `npm test`, `npm run build`.
- Rust: `cargo fmt`, `cargo clippy --locked` und `cargo test --locked` in
  beiden Rust-Projekten. Vorher den Korrekturprozess bauen.

## Regeln

- Mikrofonaufnahmen bleiben lokal. Externe Textkorrektur ist freiwillig.
- Schlüssel gehören in den Systemspeicher für Zugangsdaten. Modelle, Rohaufnahmen,
  private Diktate und Build-Dateien bleiben außerhalb von Git.
- Halte beide Sprachfassungen und die Dokumentation bei sichtbaren Änderungen
  aktuell. Kennzeichne ungeprüfte Plattformfunktionen ausdrücklich.
- Arbeite auf einem eigenen Zweig. Führe lokale Prüfungen vor dem Push aus.
  Aktualisiere [PROGRESS.md](docs/PROGRESS.md) bei Änderungen am Stand.
- Veröffentlichungen laufen über den Ablauf in [RELEASE.md](docs/RELEASE.md).
