# Vorabversion veröffentlichen

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
   git tag -a v0.1.0-alpha.1 -m 'VoxTakt 0.1.0-alpha.1'
   git push origin v0.1.0-alpha.1
   ```

3. Prüfe den Ablauf **Package and release** in GitHub Actions. Er prüft
   den Quellstand und baut NSIS-EXE, DMG, AppImage und DEB auf getrennten
   Rechnern. Erst nach allen erfolgreichen Builds und Prüfungen veröffentlicht
   er die vier Dateien und ihre SHA-256-Prüfsummen.
4. Öffne die Vorabversion auf GitHub. Vergleiche die Paketliste und prüfe
   nach einem Download mindestens die Prüfsummen. Nenne den getesteten
   Quellstand und die Ergebnisse der Installationsprüfungen im Projektstand.

## Signaturen

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
