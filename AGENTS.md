# Voicewright

Desktop-App für lokales Diktat (Tauri 2, React, TypeScript; Rust steuert
Aufnahme, Erkennung und Einfügen). Die Oberfläche ist zweisprachig (DE/EN).
Cloud-Dienste laufen nur mit ausdrücklicher eigener Konfiguration.

## Struktur

- `src/` — Oberfläche und TypeScript-Tests (Vitest).
- `src-tauri/` — Hauptprozess (Rust). `src-tauri/binaries/` hält das
  Engine-Binary, gitignored.
- `engines/cleanup/` — lokale Textkorrektur als separates Programm
  (llama.cpp-Sidecar). **Kein Workspace-Mitglied** von `src-tauri`: zwei
  unabhängige Cargo-Projekte mit eigenen `Cargo.lock`. Jeder cargo-Befehl
  braucht `--manifest-path <pfad> --locked`; `cargo` im Repo-Root funktioniert
  nicht.
- `docs/TESTING.md` — vollständige Prüfliste. `docs/PROGRESS.md` — aktueller
  Stand, bei Änderungen aktualisieren.

## Befehle

Toolchain: Node 24 und Rust 1.99.1 (CI-Pins), dazu CMake und Clang/libclang —
die Korrektur kompiliert llama.cpp aus dem Quellcode, der erste Build dauert
lange.

```sh
npm ci
npm run prepare:engine   # baut engines/cleanup, kopiert nach src-tauri/binaries/
npm run tauri -- dev     # oder: npm run tauri -- build
```

Ohne `prepare:engine` schlagen `tauri dev` und `tauri build` fehl
(Tauri `externalBin`). Das Skript nimmt optional einen Target-Triplet an:
`npm run prepare:engine -- x86_64-unknown-linux-gnu`.

Alle Prüfungen in CI-Reihenfolge (auch in docs/TESTING.md):

```sh
npm run check && npm run lint && npm test && npm run build
cargo fmt --manifest-path src-tauri/Cargo.toml --all -- --check
cargo fmt --manifest-path engines/cleanup/Cargo.toml --all -- --check
cargo clippy --manifest-path src-tauri/Cargo.toml --locked --all-targets -- -D warnings
cargo test --manifest-path src-tauri/Cargo.toml --locked
cargo clippy --manifest-path engines/cleanup/Cargo.toml --locked --all-targets -- -D warnings
cargo test --manifest-path engines/cleanup/Cargo.toml --locked
npm audit --audit-level=high
```

Einzeltests:

- TypeScript: `npm test -- src/domain.test.ts` (Datei) oder
  `npm test -- -t "Testname"`.
- Rust: `cargo test --manifest-path <pfad> --locked <Testname>`.

## Tests

- `src-tauri/tests/speech.rs` und `engines/cleanup/tests/protocol.rs` sind
  `#[ignore]`: Sie brauchen echte Modellgewichte
  (`VOICEWRIGHT_WHISPER_MODEL` bzw. `VOICEWRIGHT_TEST_GGUF`) und WAV-Fixtures
  aus espeak-ng plus ffmpeg. Setup steht in docs/TESTING.md. Das normale
  `cargo test` läuft ohne sie.
- Sidecar-Protokoll: JSON über stdin/stdout zwischen App und
  `voicewright-cleanup` (`engines/cleanup`), maximal 256 KB pro Request. Zur
  Laufzeit liegt das Binary neben der Haupt-EXE; Tauri kopiert es im Dev-Modus
  aus `src-tauri/binaries/`.
- `scripts/linux-smoke/run.sh` (DEB, Xvfb, künstliche Mikrofoneingabe) läuft
  nur in einem isolierten Linux-Container ohne Netzwerk; Details in
  docs/TESTING.md.

## Fallback ohne Rust-Toolchain

Ohne lokale Rust-Toolchain mit Systembibliotheken laufen die Rust-Prüfungen in
den lokal gebauten Podman-Images: `localhost/voxtakt-build:latest` für
Build/Prüfungen und `localhost/voxtakt-smoke` für den DEB-Smoke. Die
`voxtakt`-Namen sind **keine Tippfehler** — das Projekt heißt früher so und
wurde zu Voicewright umbenannt; die Namen nicht „korrigieren“.

```sh
podman run --rm -v "$PWD":/work:Z -w /work localhost/voxtakt-build:latest
# im Container: export PATH=/usr/local/cargo/bin:$PATH
# für engines/cleanup: CARGO_TARGET_DIR=/work/target setzen
```

## Regeln

- Zweisprachig: sichtbare Texte immer in Deutsch und Englisch aktualisieren.
- API-Schlüssel nur im System-Schlüsselspeicher; der Einstellungen-Export
  enthält bewusst keine Schlüssel.
- Modelle, Rohaufnahmen, private Diktate, `src-tauri/binaries/` und `target/`
  bleiben außerhalb von Git.
- Eigener Zweig von `main`; lokale Prüfungen vor dem Push; Pull Requests nie
  selbst mergen.
- Gesprochene Diktatbefehle lösen niemals OS-Aktionen aus (Parser ist
  Text-only, opt-in, standardmäßig aus); siehe docs/SPOKEN_FORMATTING.md.
- Ungeprüfte Plattformfunktionen ausdrücklich kennzeichnen.
- Veröffentlichungen laufen über den Ablauf in docs/RELEASE.md.
