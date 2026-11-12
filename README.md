# Voicewright

**Lokale Desktop-Diktier-App · Windows, macOS und Linux · Open Source**

Voicewright ist eine kompakte, datensparsame Desktop-Anwendung auf Basis von **Tauri 2, Rust, React und Whisper**. Sie läuft im Hintergrund: Tastenkombination drücken, diktieren, Text sicher am Ziel einfügen – **sofern die Plattform es erlaubt** – oder über einen bewussten Copy-Fallback übernehmen. Das Hauptfenster dient nur Einrichtung und Einstellungen. Das [reduzierte Designkonzept](docs/design/VOICEWRIGHT_UI_CONCEPT.md) nutzt fünf Bereiche, ruhige Dark-/Light-Ansichten und ein unaufdringliches Aufnahme-HUD.

> **Stand 12.11.2026: `0.1.0-alpha.1` – keine fertige V1.** Der verbindliche Auftrag ist [V1-Issue #76](https://github.com/mixxermannipro/Voicewright/issues/76). Bis zur fertigen Testversion werden alle Entwicklungsprüfungen **autonom in virtuellen Umgebungen** ausgeführt; persönliche Geräte- und Funktionstests folgen **erst danach** durch den Projekteigentümer.

## Was aktuell implementiert oder geprüft ist

| Bereich | Stand |
| --- | --- |
| Offline-Diktat | Lokale Whisper-basierte Audio-/Speech-Architektur vorhanden, einzelne synthetische Modell-/X11-Tests dokumentiert. Noch keine plattformübergreifende V1-Abnahme |
| Textkorrektur | Optionaler lokaler Cleanup-Sidecar und freiwillige Providerkonfiguration vorhanden. Cloud nur nach bewusster Konfiguration |
| Hotkey/Hintergrund/Tray | Wesentliche Funktionen in der Alpha implementiert. Plattform-/Berechtigungstests und V1-End-to-End noch offen |
| Linux X11 | Virtueller Test mit Xvfb + GTK belegt sichere Unicode- und mehrzeilige Eingabe in einem synthetischen Testfeld |
| Linux Wayland | GlobalShortcuts-Portal soweit vorhanden; reale Portal-Freigabe und automatisches Fremd-App-Einfügen **nicht** freigegeben/nachgewiesen. Sicherer manueller Copy-Fallback |
| Windows | Native Grundlagen vorhanden; NSIS und echte/virtuelle End-to-End-Abnahme noch nicht vollständig belegt |
| macOS | Bisher manueller Copy-Fallback; DMG, native Permissions und tatsächliche globale Textinsertion sind nicht vollständig nachgewiesen |
| V1-Verteilung | Linux-AppImage/DEB-Paketprüfungen vorhanden; Windows/macOS-Pakete und alle Sicherheits-/Nutzerabnahme-Gates noch offen |

**Keine falschen Versprechen:** Eine grüne CI beweist noch keine echte Mikrofonfreigabe, ein tatsächliches macOS-Accessibility-Dialogverhalten oder systemweite Wayland-Einfügung. Die App zeigt solche Grenzen transparent und bietet einen Fallback.

## Entwicklungsumgebung & Tests

Benötigt: **Node.js 24**, **Rust 1.99.1**, CMake, Clang/libclang und je nach Plattform die Tauri-Systembibliotheken. Zwei unabhängige Cargo-Projekte: `src-tauri/` und `engines/cleanup/`. Für das Cleanup-Sidecar gilt vor Tauri-Builds `npm run prepare:engine`.

```bash
npm ci
npm run check && npm run lint && npm test && npm run build
cargo fmt --manifest-path src-tauri/Cargo.toml --all -- --check
cargo test --manifest-path src-tauri/Cargo.toml --locked --all-targets
cargo test --manifest-path engines/cleanup/Cargo.toml --locked --all-targets
npm run prepare:engine
npm run tauri -- build
```

Die vollständigen Anforderungen inklusive Clippy, Audits, virtueller Audio-/X11-Tests und OS-Pakete stehen in [VIRTUAL_TESTING.md](docs/VIRTUAL_TESTING.md) und [TESTING.md](docs/TESTING.md). Ein grüner Check für einen bestimmten Commit ist **kein** Nachweis für alle dort geplanten Gates.

## Installation / Systemberechtigungen

[Installation](docs/INSTALLATION.md) · [Modellverwaltung](docs/MODELS.md) · [Plattformgrenzen](docs/PLATFORM_SUPPORT.md). Voicewright benötigt bei echten Nutzern je nach OS Mikrofon-, Hotkey-/Portal- oder Accessibility-Freigaben. **Diese werden nicht umgangen**. Das autonome Testsystem simuliert freigegebene und abgelehnte Zustände; die echte Erteilung erfolgt **ausschließlich beim späteren freiwilligen Praxistest**.

## Projektsteuerung & Sicherheit

- [**V1-Issue #76 – einziger aktiver Arbeitsauftrag**](https://github.com/mixxermannipro/Voicewright/issues/76)
- [V1-Produktumfang](docs/V1_SCOPE.md) · [virtuelle Teststrategie](docs/VIRTUAL_TESTING.md) · [Repository-Karte](docs/REPOSITORY_MAP.md)
- [Archiv/Entscheidung aller 35 bisherigen offenen Issues](docs/ISSUE_TRIAGE.md) · [UI-Mockups](docs/design/VOICEWRIGHT_UI_CONCEPT.md)
- [Tests](docs/TESTING.md) · [Release/Signaturen](docs/RELEASE.md) · [Historische Entwicklung](docs/PROGRESS.md)
- [Mitwirken](CONTRIBUTING.md) · [Agenten-Anleitung](AGENTS.md) · [Datenschutz](PRIVACY.md) · [Sicherheit](SECURITY.md)

Quellcode: [MIT-Lizenz](LICENSE); Drittbibliotheken und Modelle haben ihre [eigenen Lizenzbedingungen](docs/THIRD_PARTY_LICENSES.md). Keine Telemetrie oder Ads. Modelle werden lokal verwendet; Downloads kontaktieren die angegebene Quelle. Externe Textkorrektur ist freiwillig und kann Daten zum gewählten Anbieter senden.

---

### English

Voicewright is an open-source, offline-first desktop dictation app using Tauri, Rust, React, and local Whisper speech recognition. The **`0.1.0-alpha.1`** version is **not yet a validated V1**. The app aims for global hotkey dictation, a lightweight background tray, safe text insertion when supported and a transparent copy fallback. Privacy-sensitive cloud cleanup is optional. Development and CI must use **autonomous virtual tests without accessing or requesting permissions on the owner's devices**. Physical testing and user feedback happen only **after** a testable V1 candidate exists. See [V1 scope](docs/V1_SCOPE.md), [virtual test matrix](docs/VIRTUAL_TESTING.md), and [tracking issue #76](https://github.com/mixxermannipro/Voicewright/issues/76).
