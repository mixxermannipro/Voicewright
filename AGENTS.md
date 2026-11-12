# Voicewright – Regeln für Coding-Agenten

## Einziger aktueller Auftrag

**[Issue #76: funktionierende Voicewright V1 mit autonomer virtueller Vorprüfung](https://github.com/mixxermannipro/Voicewright/issues/76).**
Lies [docs/V1_SCOPE.md](docs/V1_SCOPE.md), [docs/VIRTUAL_TESTING.md](docs/VIRTUAL_TESTING.md), [docs/REPOSITORY_MAP.md](docs/REPOSITORY_MAP.md), dann die betroffenen Komponenten. Die früheren 35 offenen Tickets sind in [docs/ISSUE_TRIAGE.md](docs/ISSUE_TRIAGE.md) dokumentiert und archiviert. Die alten Masterpläne #39/#47 gelten **nicht** mehr als Arbeitsreihenfolge.

**Keine Feature-Flut:** Eine stabile Hintergrund-Diktier-App mit lokaler DE/EN-Whisper-Erkennung, Hotkey/Tray, sicherer Textausgabe/Copy-Fallback, Modellverwaltung und ruhigen DE/EN-Einstellungen. UI nach [festgelegten Mockups](docs/design/VOICEWRIGHT_UI_CONCEPT.md) (General, Dictation, Models, Shortcuts, Privacy). Keine neue umfangreiche KI-, Provider- oder Theme-Initiative vor V1.

## Verbotene Blocker während der Entwicklungsphase

- **Nicht** den Eigentümer um Zugriff auf persönliche Mikrofone, Bildschirmfreigaben, Wayland-Portale, Apple Accessibility, Windows-UI, Testgeräte oder lokale Testausführung bitten.
- Alle Entwicklungs- und Funktionstests in **GitHub CI, VMs, Containern, Xvfb/virtuellem Compositor und synthetischer Audio-/Eingabeumgebung** automatisieren, mit korrekten CI-Nachweisen.
- Ein realer OS-Permissiondialog darf weder umgangen noch als automatisch genehmigt vorgetäuscht werden. Stattdessen `granted/denied/revoked/timeout/unavailable` isoliert simulieren; sicherer Copy-Fallback.
- Wenn Signatur-/Notarisierungsdaten oder Cloud-Keys nicht bereitstehen: keine persönlichen Geheimnisse anfordern, **unsignierten Testkandidaten** mit klarer Kennzeichnung vorbereiten. Kein öffentliches Stable-Release.
- **Nur am Ende:** Eigentümer installiert einen virtuell geprüften Kandidaten und liefert „funktioniert / funktioniert nicht“-Feedback. Negative Fälle als automatisierte Regressionen ergänzen, PRs erstellen, erneut prüfen. Vor seiner abschließenden Zustimmung kein öffentlicher Stable-Tag.

## Architektur

- `src/` = React/TypeScript UI und Vitest.
- `src-tauri/src/` = Rust: Audio/ASR/Session/Hotkeys/Insertion, Betriebssystemintegration.
- `engines/cleanup/` = eigenständiges Rust-Projekt, llama.cpp-Sidecar, **kein Cargo-Workspace** mit `src-tauri`. Beide mit `--manifest-path` und `--locked` testen.
- `src-tauri/binaries/` ist generiert/ignoriert, nach `npm run prepare:engine` bereit; keine Modellgewichte oder privaten Samples in Git.
- `scripts/linux-smoke/` = echte automatisierbare Testkette mit Xvfb, GTK, virtueller Audioquelle; `.github/workflows/ci.yml` hat den Pflichtcheck **`check`**, nicht `Build`. Weitere aktive Workflows unter `.github/workflows/`.
- Aktuelle Version `0.1.0-alpha.1` (Node/Tauri/Cargo synchron). `de.voicewright.desktop` ist migrationsrelevant, historische Podman-Image-Namen `voxtakt` nicht blind umbenennen.

## Toolchain und lokale/virtuelle Gates

**Node 24, Rust 1.99.1**, CMake, Clang/libclang, Tauri-Plattformbibliotheken. Vor Tauri-Build `npm run prepare:engine`.

```bash
npm ci
npm run check && npm run lint && npm test && npm run build
cargo fmt --manifest-path src-tauri/Cargo.toml --all -- --check
cargo fmt --manifest-path engines/cleanup/Cargo.toml --all -- --check
cargo clippy --manifest-path src-tauri/Cargo.toml --locked --all-targets -- -D warnings
cargo clippy --manifest-path engines/cleanup/Cargo.toml --locked --all-targets -- -D warnings
cargo test --manifest-path src-tauri/Cargo.toml --locked --all-targets
cargo test --manifest-path engines/cleanup/Cargo.toml --locked --all-targets
npm audit --audit-level=high
git diff --check
```

Echte Modellintegration **mit synthetischen** DE/EN-Files und verifizierten Gewichten separat im virtuellen CI-Gate ausführen. Ignore-/Mock-Tests nie als echte Whisper/Audio-End-to-End-Prüfung bezeichnen. Paket- und GUI-Smokes eigenständig automatisieren; keine Desktop-Freigabe des Eigentümers. Ungetestete Grenzen im Bericht kennzeichnen. `docs/TESTING.md` und `docs/VIRTUAL_TESTING.md` beachten.

## Workflow mit autonomen PRs

1. Aktuelles `main` lesen, nur für die kleinste V1-Teilaufgabe frischen `feature/*`-/`fix/*`-/`chore/*`-Branch anlegen. Keine direkten main-Commits, keine Force-Pushes, keine fremden PR-Branches überschreiben.
2. Neue Tests vor/mit Fix, bekannte Lücken erfassen, vollständige lokale Tests wo verfügbar und virtuelle CI laufen lassen. Falls ein Test mangels Runner/OS-Lizenz nicht möglich ist: nicht „grün“ melden, sondern als reales Rest-Risiko dokumentieren.
3. PR gegen `main` mit `Part of #76`, Messungen/Log-Links/Artefakten, Feature-Freeze-, Sicherheits-/Lizenz- und Konfliktprüfung. **Nicht** `Closes #76` schreiben.
4. Vor Merge: Diff/reale Changes überprüfen, `main` auf neue Commits prüfen, Konflikte korrekt lösen, Pflichtcheck **`check`** muss erfolgreich sein. Fertige kleine PRs können nach bestandenen Checks autonom gesquasht werden; **Drafts oder ungeprüfte Sicherheitsänderungen niemals**. Kein Bypass von Branch-Schutz.
5. Nach Merge nur belegte Kriterien in #76 abhaken. Dokumentation, [PLATFORM_SUPPORT.md](docs/PLATFORM_SUPPORT.md), [TESTING.md](docs/TESTING.md) und historische [PROGRESS.md](docs/PROGRESS.md) sorgfältig aktuell halten.

## Datenschutz/Sicherheit

- Keine echten Transkripte, Audios, Passwörter oder API-Keys in Tests, Logs oder Git. Nur synthetische freie Fixtures.
- OS-Keyring für Keys, Cloud nur bei Opt-in; keine heimliche Übertragung. Fremdcode-/Modell-/Binary-Lizenzen und Hashes/NOTICE prüfen.
- Keine Blind-Insertion bei gewechseltem Fokus, sicherem Feld oder verweigertem Portal; Text im Recovery erhalten. Keine Root-/uinput-/Permission-Umgehung.
- Große Daten-/Modell-/ABI-/Rechtslücken nicht zu kosmetischen Tests herunterstufen. Ein grüner Mock-Build ist kein Nachweis für eine freigegebene physische Installation.

**V1-Kandidat ≠ öffentliche Freigabe.** Owner prüft einmal am Ende praktisch und gibt gezieltes Feedback, das danach abgearbeitet wird.
