# Issue #76 – native Runner und unveröffentlichte Pakete

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Windows-x64-/macOS-ARM64-Code vor einem Tag nativ bauen, testen und als nicht veröffentlichte NSIS-/DMG-Artefakte mit prüfbarem Bericht bereitstellen.

**Spec:** `docs/V1_SCOPE.md`, `docs/VIRTUAL_TESTING.md`, Issue #76 Phasen 1/3.
**Architecture:** Reusable native CI-Matrix (Windows 2022, macOS 15 ARM64), im Pflichtcheck `check`. Ein Node-Standardbibliothek-Prüfer extrahiert nur die eigens gebauten Installer bzw. mountet das DMG read-only, prüft enthaltene Haupt-/Sidecar-Architektur und Lizenzhinweise, schreibt SHA256 und einen ehrlichen Ergebnis-/Signaturbericht. Der Tag-Workflow verwendet dieselben bereits geprüften CI-Artefakte, ohne Doppelbau. Kein Tag und kein Release während dieser Aufgabe.
**Constraints:** Node 24, Rust 1.99.1, beide Cargo-Projekte `--locked --all-targets`; nur Standardrunner, keine Secrets/Signaturdaten oder Nutzergeräte. Dieser PR baut auf dem separaten Textfeldschutz #79 auf, um dessen Windows-Code tatsächlich zu kompilieren. Kein „V1 fertig“ allein aus Paketbau.

## Review Focus

- Falsche Architektur oder fehlender Sidecar/NOTICE muss blockieren.
- Versionen in npm/Lockfile/Tauri/Cargo müssen übereinstimmen.
- Fehler und frühe Abbrüche dürfen keinen erfolgreichen Bericht erzeugen.
- Signaturstatus ist Beobachtung, keine Gatekeeper-/SmartScreen-/Notarisierungszusage.
- Native Unit-/Pakettests sind kein Test echter globaler Hotkeys, Mikrofone, Benutzer-OS-Dialoge oder aller Fremdprogramme.

## Umsetzung

- [ ] `scripts/native-packaging.test.mjs` zuerst: synthetische PE-/Mach-O-Header und Versionsabweichung rot→grün.
- [ ] `scripts/check-native-bundle.mjs`: echte Paket-/Payload-Prüfung, Lizenzdateien, Checksummen und Fehlerbericht.
- [ ] `.github/workflows/native-package.yml`: native fmt/Clippy/Tests beider Projekte, Sidecar und Paketbau, Artefakte ohne Veröffentlichung.
- [ ] CI-`check.needs` ergänzen; Tag-Workflow auf dieselben geprüften Artefakte umstellen.
- [ ] Lokale Web-/Script-/Workflow-Prüfungen; DeepSeek-Review; eigener kleiner PR auf #79, echte native CI auswerten und nötige Plattformfehler korrigieren.
- [ ] Issue #76 und Plattform-/Testjournal nur mit tatsächlichen Nachweisen aktualisieren. Kein Nutzerzwischen-Gate.
