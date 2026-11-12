# Vorabversion veröffentlichen

> **Neue V1-Regel 12.11.2026:** Nicht vorab öffentlich veröffentlichen oder einen V1-Stable-Tag setzen. Zuerst aus grüner, **vollständig autonomer virtueller** CI installierbare Kandidatenpakete als **private/unveröffentlichte GitHub-Actions-Artefakte** mit SHA-256 bereitstellen. **Keine persönliche Gerät-/Mikrofon-/Wayland-/Accessibility-Freigabe als Zwischen-Gate verlangen.** Erst der Eigentümer testet den fertigen Kandidaten auf seinem eigenen Rechner und gibt „funktioniert / funktioniert nicht“-Feedback. Danach Fehler beheben und **nur mit ausdrücklichem Sign-off** veröffentlichten Release erzeugen. [V1_SCOPE.md](V1_SCOPE.md) · [VIRTUAL_TESTING.md](VIRTUAL_TESTING.md) · [#76](https://github.com/mixxermannipro/Voicewright/issues/76).

Die nachfolgende bisherige **taggetriggerte** Alpha-Release-Anleitung bleibt technische Referenz, nicht eine Aufforderung, jetzt einen Tag zu pushen. Ohne Herstellerzertifikate sind Windows/macOS-Pakete möglicherweise unsigniert bzw. nicht notarisiert; deren Risiken und die später ggf. nötige normale OS-Freigabe gehören in die Nutzeranleitung, niemals in einen automatisierten Berechtigungs-Bypass.


Aktiviere zuerst die [GitHub-Workflows](github-workflows/README.md).

Die GitHub-Pipeline akzeptiert Tags (benannte Versionsstände) der Form
`v0.1.0-alpha.1`, `v0.1.0-beta.1` oder `v0.1.0-rc.1`. Ein Tag muss auf einem
Commit in `main` liegen. `package.json`, `src-tauri/Cargo.toml` und
`src-tauri/tauri.conf.json` müssen dieselbe Versionsnummer enthalten.
Aktualisiere die Abhängigkeitslisten und den Änderungsverlauf zusammen mit
der Versionsnummer.

1. Führe die [Prüfungen](TESTING.md) aus. Führe den Änderungsvorschlag
   erst nach bestandenen Prüfungen mit `main` zusammen.
2. Erstelle und übertrage den Tag für den freigegebenen Commit:

   ```sh
   git switch main
   git pull --ff-only
   git tag -a v0.1.0-alpha.1 -m 'Voicewright 0.1.0-alpha.1'
   git push origin v0.1.0-alpha.1
   ```

3. Prüfe den Ablauf **Package and release** in GitHub Actions. Er prüft
   den Quellstand und baut NSIS-EXE, DMG, AppImage und DEB auf getrennten
   Rechnern. Erst nach allen erfolgreichen Builds und Prüfungen veröffentlicht
   er die vier Dateien und ihre SHA-256-Prüfsummen.
    Alle vier Pakete werden bereits im wiederverwendeten CI-Check gebaut:
    Linux auf Ubuntu 22.04, Windows x64 auf Windows 2022, macOS ARM64 auf
    macOS 15. Der Releasejob verwendet genau diese geprüften Artefakte, keinen
    zweiten Build. In PRs werden sie nur als zeitlich begrenzte Testartefakte
    hochgeladen; dabei wird weder ein Tag noch eine GitHub-Veröffentlichung erstellt.
   Das [Linux-Testprotokoll](LINUX_RELEASE_TESTS.md) trennt Paketprüfungen von
   noch ausstehenden echten Desktop-/Update-Tests.
4. Öffne die Vorabversion auf GitHub. Vergleiche die Paketliste und prüfe
   nach einem Download mindestens die Prüfsummen. Nenne den getesteten
   Quellstand und die Ergebnisse der Installationsprüfungen im Projektstand.

## Signaturen

Der native Paketbericht `report.json` protokolliert beobachtete
Authenticode-/Codesign-Zustände. Eine Ad-hoc-Signatur ist kein
Herstellerzertifikat und keine Notarisierung. Native Struktur-/Architekturtests
sind keine praktische Installer-/Gatekeeper-/SmartScreen-Abnahme.

**English:** PR CI builds unpublished native test artifacts, checks main/sidecar
architecture and bundled notices, and records SHA256 and observed signature
status. Release publication reuses those exact gated artifacts only after an
explicitly authorized tag. CI does not prove OS consent, installer upgrades,
trusted signing or real-device behavior.

Die Pakete werden ohne Herstellerzertifikate gebaut. Windows kann eine
SmartScreen-Warnung anzeigen. macOS kann beim Öffnen aus dem Internet eine
Warnung anzeigen oder den Start blockieren. Die App enthält keine
automatische Aktualisierung. SHA-256 dient dem Vergleich der Dateien. Eine
Prüfsumme allein belegt keine Identität des Herausgebers.

Für einen signierten Veröffentlichungsablauf siehe
[Tauri für macOS](https://v2.tauri.app/distribute/sign/macos/) und
[Tauri für Windows](https://v2.tauri.app/distribute/sign/windows/). Für macOS
sind Herstellerzertifikat und Notarisierung einzuplanen. Hinterlege künftige
Signaturdaten ausschließlich im geschützten Speicher des
Veröffentlichungsablaufs. Eine stabile Freigabe benötigt außerdem belegte
Praxistests aus [TESTING.md](TESTING.md).
