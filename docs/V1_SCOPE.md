# Voicewright V1 – verbindlicher Umfang und Definition of Done

**Gültig ab 12.11.2026 · Status: Alpha `0.1.0-alpha.1`, keine fertige V1.**
**Einziger Arbeitsauftrag:** [Issue #76](https://github.com/mixxermannipro/Voicewright/issues/76). Historische #39/#47 und alle 35 ehemals offenen Issues sind unter [ISSUE_TRIAGE.md](ISSUE_TRIAGE.md) archiviert.

## Ziel

Eine **leise, ressourcenschonende Hintergrund-Diktier-App**: Tastenkombination → lokale Aufnahme/Spracherkennung → sicheres Einfügen oder expliziter Copy-Fallback. Einstellungen statt Dauer-Dashboard. Ohne Cloudkonto arbeitsfähig; externe Textanbieter nur optional. UI-Ziel sind die [freigegebenen minimalistischen Mockups](design/VOICEWRIGHT_UI_CONCEPT.md).

## Verbindlicher V1-Kern

| Bereich | Verpflichtung |
| --- | --- |
| Diktat | echte lokale Whisper-ASR für DE/EN, nachweisbarer Modellimport/Download und Integrität, Aufnahme/Stop/Abbruch, brauchbarer Text |
| Hintergrund | globaler Hotkey (Hold/Toggle), Sitzungsautomat, Tray/Menu bar, opt-in Autostart, minimales Recording-HUD ohne Fokusdiebstahl |
| Sichere Textausgabe | Original-Ziel soweit technisch erkennbar validieren, Unicode/Emoji/Absätze, kein blindes Tippen in andere/protected Felder; Ergebnis bei Fehler verfügbar, bewusster Copy-Fallback ohne zerstörte Zwischenablage |
| Einstellungen | General, Dictation, Models, Shortcuts, Privacy; deutsch/englisch, Dark/Light/System, funktionsfähige Schalter, einfache Ersteinrichtung, keine falschen Berechtigungs-/Erfolgsmeldungen |
| Offline, Privacy | Modellimport + Offline-Erkennung ohne Account; lokale Textkorrektur optional und nur bei belegter semantischer Sicherheit; bestehende Cloudprovider standardmäßig **aus**, keine Erweiterung/Live-Key-Pflicht; Secrets im System-Keyring |
| Plattform | Virtuelle Linux-X11-/Wayland-Testumgebungen priorisieren (Fedora/Linux zuerst); Windows x64 und macOS ARM64 über native CI-Runner bauen und soweit virtualisierbar testen. Plattformen ohne echte Zustimmungs-/Fokustests **nicht** als umfassend real unterstützt ausgeben |
| Lieferung | Unveröffentlichte, herunterladbare V1-Testpakete/Checksummen/Versionen, Linux AppImage/DEB, Windows NSIS und macOS DMG soweit erfolgreiche CI. Fehlende Signaturen/Notarisierung ehrlich benennen |
| Sicherheit | Lizenz/SBOM/Modellherkunft, kein Key-/Audio-/Text-Leak, Dateirechte, Sidecar-/Prozesskontrolle, sichere OS-Permissions und Rollback/Fallback |

## Wichtig: **kein Nutzergerät während der Entwicklung**

Die vollständige Entwicklungsprüfung erfolgt **autonom und virtuell**. Für die Coding-Agenten sind **keine** persönlichen Mikrofon-, Bildschirm-, Wayland-, Windows- oder macOS-Freigaben des Eigentümers nötig. Stattdessen:

1. **Headless und virtuelle Integrationsprüfungen:** GitHub-hosted Linux/Windows/macOS-Runner, Xvfb, Testeditoren, virtuelle Audio-Quellen, synthetische DE/EN-WAVs, simulierte Fokus-/Portal-/Berechtigungsfälle, OS-spezifische Pakete.
2. **Echte Engines getrennt von Mocks:** Whisper mit hash-/lizenzgeprüftem Modell und künstlicher Sprache durchlaufen lassen; Provider-APIs mit Mockservern, 401/429/Timeout/Test-Keys, niemals persönliche Schlüssel. Echte Modellgewichte dürfen heruntergeladen/gecached werden, **nicht** unberechtigt aus Git bezogen oder ungeprüft eingebettet.
3. **Reproduzierbare Reports:** Commit/Runner/Paket-SHA, getestete Matrix, vorbestehende Baseline, Fehlermeldungen, Latenz/RAM und exakte nicht testbare Szenarien in [VIRTUAL_TESTING.md](VIRTUAL_TESTING.md).
4. **Keine Rechteumgehung:** Wenn OS-Freigaben notwendig wären, nur Zustände `allowed/denied/timeout/revoked` virtuell testen; im realen Produkt klare Erklärung und sicherer Fallback. Ein Mock der Wayland-Portal-Freigabe beweist **nicht** die Funktion einer echten Wayland-Einfügung.
5. **Einzige persönliche Testphase:** Erst nachdem alle automatisierbaren Gates bestanden und Kandidatenpakete vorhanden sind, erhält der Eigentümer eine V1-Testversion. Er prüft sie selbst, gibt „funktioniert / nicht funktioniert“-Feedback und nur **dieses** Feedback startet gezielte Fehlerbehebungs-PRs. **Keine öffentliche Stable-Freigabe ohne sein finales Sign-off.**

## Verbindliche autonome Test- und Abnahmematrix

- [ ] `npm ci && npm run check && npm run lint && npm test && npm run build`; `npm audit` plus separate dokumentierte Security-Entscheidung.
- [ ] Beide Cargo-Projekte: `cargo fmt --all -- --check`, `cargo clippy --locked --all-targets -- -D warnings`, `cargo test --locked --all-targets` (mit `--manifest-path`).
- [ ] Virtueller Linux-X11-Test **im CI-Pflichtcheck**: echter Insertionsadapter in externes GTK-Mehrzeilen-Widget, Vergleich von Unicode/Emoji/Absatz/Cancel.
- [ ] Modelltests in eigener CI-Stufe einschließlich realer synthetischer Whisper-/Qwen-Audios, Gewichtsdaten mit Hash/Lizenz dokumentiert; Mock-only-Tests nicht als reale ASR werten.
- [ ] OS-Simulationen: Hotkey/Start-Stop/Fokuswechsel, Copy-Fallback, verweigerte Mikrofon-/TCC-/Portalzustände, Keyring-Fehler, Modell fehlt/defekt, Netz offline/Cloud aus; automatisierte Regressionen.
- [ ] Windows/macOS auf GitHub-Runnern: buildbare und validierte Testpakete; nicht testbare echte OS-Dialoge im Bericht als *offen* kennzeichnen, keine Nutzerinteraktion während der Entwicklung.
- [ ] 100+ synthetische Start-/Stop-Zyklen, Fehler-/Crash-/Timeout-/Ressourcenprüfungen ohne private Audios/Secrets.
- [ ] Codesign/Notarisierung: Falls Eigentümer bereits reguläre, geschützte Signaturdaten bereitgestellt hat, CI nutzen; sonst nur als **unsignierte Testpakete** liefern, keine unsicheren Gatekeeper-/SmartScreen-Bypasses empfehlen.
- [ ] Vergleichbare CI-Reports pro Runner/Commit/Paket und alle nötigen Fehlerbehebungen in kleinen PRs.
- [ ] **V1-Testkandidat** als nicht veröffentlichte Artefakte bereit. Keine lokalen Handtests durch Eigentümer vorher.
- [ ] **Erst danach** Eigentümerfeedback gesammelt, Fehler reproduziert, erneut virtuell getestet, finales Freigabeprotokoll in #76.

## Nicht Bestandteil des ersten Testkandidaten

Parakeet als zweite ASR-Engine, komplexe GPU-Backends, viele neue Cloudanbieter, vollautomatische Updates, umfangreiche Format-/Übersetzungs-KI, aufwändige Animationen/Designvarianten und unbestätigte systemweite „alles einfügen“-Versprechen. Bereits vorhandene sichere Funktionen bleiben nutzbar und dürfen nicht ohne Grund entfernt werden.

## Geprüfter Ausgangsstand

`main` besitzt bereits die Tauri/Rust/React-Alpha, ein aktives CI mit `check`-Sammeljob, eine Linux-AppImage/DEB-Paketstufe, einen virtuellen X11-Einfügeprobe-Baustein und einen Draft [#75](https://github.com/mixxermannipro/Voicewright/pull/75) für Wayland. Die realen Systemfreigaben/physische Mikrofone sowie echte Windows/macOS-E2E sind **nicht** automatisch durch grüne Builds bestätigt.

## Workflow

Jede Teilaufgabe: aktuelles `main` → eigener Branch → Code/Tests → PR mit `Part of #76`, eindeutigen Befunden und verbleibenden OS-Lücken → grüner Pflichtcheck `check` → Review/Konfliktlösung → Squash-Merge. Kein direkter main-Push, keine unüberprüften Draft-Merges, `Closes #76` nur bei echter Schlussabnahme.
