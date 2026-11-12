## V1-Bezug

**Part of #76**

**Teilfunktion / V1-Gate:** <!-- Konkretes Kriterium aus docs/V1_SCOPE.md -->

## Änderungen

<!-- Technischer Scope, vorher/nachher, betroffene OS/Privacy-Lizenz/Fallback -->

## Automatisch ausgeführte Tests (keine Besitzergeräte)

- [ ] Node 24: npm ci, check, lint, test, build
- [ ] Rust 1.99.1: cargo fmt, clippy --all-targets, tests beider Cargo-Projekte
- [ ] Virtueller Linux-X11-Einfügetest (Xvfb + GTK)
- [ ] Echte lokale ASR auf synthetischer DE/EN-Audiodatei mit verifiziertem Modell, sofern betroffen
- [ ] Wayland/D-Bus-/Permission-Mocks, sofern betroffen
- [ ] Windows-/macOS-Runner-Build/Test, sofern betroffen
- [ ] AppImage/DEB/NSIS/DMG inklusive Sidecar und SHA, sofern betroffen
- [ ] Keine Key-/Audio-/Text-Leaks; Licenses/Hash/Offline/Retry/Abbruch geprüft
- [ ] `git diff --check`, Konflikte mit aktuellem main ausgeschlossen

Nicht ausgeführte Tests **mit Grund** angeben, niemals als bestanden markieren.

## Nachweise

**CI-Workflow / Commit / Artefakte / Runner:**
**Reale Engine oder Testdouble:**
**Fehlerfälle / Metriken:**
**Verbleibende OS-/Permission-Grenzen:**

## V1-Workflow

Nur Feature-Branch → PR → grüner Pflichtcheck `check` → Review → Squash-Merge. Nicht `Closes #76`, solange Owner-Abnahme fehlt. Keine physischen Besitzergeräte, Mikrofon-/Portal-/TCC-Freigaben während Entwicklung. **Finaler realer Nutzer-Test erst nach CI-geprüftem Kandidaten.**
