# Voicewright

Voicewright ist eine Desktop-App für lokales Diktat. Die Oberfläche verwendet
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
- Wenn auf dem Rechner kein Rust-Toolchain mit Systembibliotheken vorhanden
  ist, lassen sich die Rust-Prüfungen im vorhandenen Podman-Image ausführen:
  `podman run --rm -v "$PWD":/work:Z -w /work localhost/voxtakt-build:latest`.
  Im Container `PATH=/usr/local/cargo/bin:$PATH` setzen. Für das
  Korrekturprojekt `CARGO_TARGET_DIR=/work/target` verwenden, damit der
  Testpfad zum eingebetteten Programm passt.

## Arbeitsablauf: Issues und Pull Requests

- Aufgaben stehen in den GitHub-Issues. Issue #47 ist die verbindliche
  Gesamt-Übersicht mit allen Prioritäten. Wähle daraus das passende offene
  Issue: den kritischen Pfad und P0 zuerst. Nenne im Pull Request die
  Issue-Nummer, an der du arbeitest.
- Nennt der Eigentümer eine Aufgabe in eigenen Worten, ordne sie dem
  passenden Issue aus #47 zu. Gibt es kein passendes Issue, arbeite nur,
  wenn die Aufgabe klein und klar ist; sonst halte Rückfrage.
- Arbeite ausschließlich auf einem eigenen Zweig und reiche die Arbeit als
  Pull Request gegen `main` ein. Pushe nie direkt auf `main` und verwende
  keine Force-Pushes. Fremde oder laufende Zweige anderer Assistenten nicht
  anfassen.
- Verlinke das Issue im Pull Request: `Closes #Nr.` nur bei vollständiger
  Lösung, sonst `Teil von #Nr.`.
- Die CI (Auftrag `check`) muss grün sein, bevor der Pull Request gemergt
  wird. Bei roter CI den Fehler beheben und erneut prüfen lassen, niemals
  mit roter CI mergen. Hinweis: Reine Markdown-Änderungen lösen die CI
  derzeit nicht aus (Pfadfilter in `.github/workflows/ci.yml`).
- Aktiviere am fertigen Pull Request Auto-Merge (Squash), falls die
  Schaltfläche vorhanden ist. Ob Auto-Merge im Repository freigeschaltet
  ist, ist nicht belegt; die Einstellung liegt beim Eigentümer.
- Bleibe beim Umfang des gewählten Issues. Neue Ideen und Nebenbefunde
  gehören als Kommentar an das Issue, nicht in denselben Pull Request.

## Regeln

- Mikrofonaufnahmen bleiben lokal. Externe Textkorrektur ist freiwillig.
- Schlüssel gehören in den Systemspeicher für Zugangsdaten. Modelle, Rohaufnahmen,
  private Diktate und Build-Dateien bleiben außerhalb von Git.
- Halte beide Sprachfassungen und die Dokumentation bei sichtbaren Änderungen
  aktuell. Kennzeichne ungeprüfte Plattformfunktionen ausdrücklich.
- Führe lokale Prüfungen vor dem Push aus.
  Aktualisiere [PROGRESS.md](docs/PROGRESS.md) bei Änderungen am Stand.
- Veröffentlichungen laufen über den Ablauf in [RELEASE.md](docs/RELEASE.md).
