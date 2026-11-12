# Repository-Karte – Voicewright

**Stichtag 12.11.2026**, 137 Git-Tree-Einträge im main-Stand `a62cd8467b97964fcb77f957ac5f0642ee9d13a4`. Die vorhandene Tauri-/Rust-/React-Struktur ist sinnvoll und wird **nicht** ohne Anlass großflächig verschoben.

```text
Voicewright/
├── .github/
│   ├── workflows/ci.yml               # aktive Pflicht-CI, Sammelcheck „check“
│   ├── workflows/linux-package.yml    # AppImage/DEB, Paketprüfung
│   ├── workflows/release.yml          # Tag-basierter Paket-/Releaseprozess
│   ├── workflows/audit.yml            # periodische Sicherheitsprüfung
│   └── workflows/automerge.yml        # Auto-Merge-Regelung
├── src/                                # React/TypeScript-Einstellungen, Frontend-Tests
├── src-tauri/
│   ├── src/                            # Rust-Hauptprozess, Audio, ASR, Sitzung, Einfügen
│   ├── tests/                          # Rust-Integration/Modeltests
│   ├── examples/                       # X11-Testadapter
│   ├── capabilities/                   # Tauri-Berechtigungen
│   ├── linux/                          # Linux Desktop/AppStream Assets
│   ├── icons/                          # plattformspezifische Icons
│   └── Cargo.toml, Cargo.lock, tauri.conf.json
├── engines/cleanup/                    # lokales llama.cpp-Cleanup-Sidecar, EIGENES Cargo-Projekt
├── scripts/
│   ├── linux-smoke/                    # Xvfb, virtuelle Audioquelle, GTK-Testeditor
│   ├── prepare-engine.mjs              # Sidecar-Build
│   └── check-linux-bundle.py           # Paket-, ABI- und Lizenzprüfung
├── docs/
│   ├── V1_SCOPE.md                     # einziger verbindlicher V1-Scope
│   ├── VIRTUAL_TESTING.md              # Autonomie-/CI-Testmatrix
│   ├── ISSUE_TRIAGE.md                 # 35 frühere Issues mit Entscheidung
│   ├── REPOSITORY_MAP.md               # diese Übersicht
│   ├── design/VOICEWRIGHT_UI_CONCEPT.md # freigegebene minimalistische UI-Mockups
│   ├── ARCHITECTURE.md, TESTING.md, RELEASE.md, PLATFORM_SUPPORT.md
│   ├── PROGRESS.md                     # chronologisches historisches Testjournal
│   └── github-workflows/              # alte Vorlagen, NICHT die aktive CI
├── README.md, AGENTS.md, CONTRIBUTING.md
└── PRIVACY.md, SECURITY.md, LICENSE, CHANGELOG.md
```

## Nicht verwechseln

1. **Projekt-/Produktname Voicewright**; historische `voxtakt`-Namen in manchen lokalen Podman-Images sind alte interne Bezeichner und nicht automatisch zu löschen. `identifier = de.voicewright.desktop` ist migrationsrelevant.
2. **Zwei unabhängige Cargo-Projekte**: `src-tauri` und `engines/cleanup`. Nicht versuchen, sie durch bloßes `cargo test` im Git-Root als gemeinsamen Workspace zu behandeln.
3. Tauri benötigt vor einem Paketbuild `npm run prepare:engine` für das `src-tauri/binaries`-Sidecar; Binärdateien/Modelle gehören nicht ins Git.
4. Aktiver Pflichtcheck in `.github/workflows/ci.yml` heißt **`check`** (nicht das alte `Build`). Virtuelle Testjobs müssen in dessen `needs`-Gate eingebunden oder als klar benannte Pflichtchecks verwendet werden.
5. [Design-Mockups](design/VOICEWRIGHT_UI_CONCEPT.md) sind **Referenzen**, keine bereits implementierten Screens. Kein zweites paralleles Dashboard entwerfen.
6. [PR #75](https://github.com/mixxermannipro/Voicewright/pull/75) ist ein **Draft**, keine geprüfte Wayland-Lösung. Seine Permission-Probes nur nach separatem Review übernehmen; niemals normale Nutzerrechte umgehen.

## Arbeitsstart

[Issue #76](https://github.com/mixxermannipro/Voicewright/issues/76) → [V1_SCOPE.md](V1_SCOPE.md) → [VIRTUAL_TESTING.md](VIRTUAL_TESTING.md) → [AGENTS.md](../AGENTS.md) → [ARCHITECTURE.md](ARCHITECTURE.md) / [TESTING.md](TESTING.md). Ältere Issue-Texte sind in [ISSUE_TRIAGE.md](ISSUE_TRIAGE.md) verfügbar.
