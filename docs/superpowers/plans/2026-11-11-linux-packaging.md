# Linux-Paketierung – Umsetzung für #32

Ziel: Den vorhandenen Tauri-Bau für AppImage (Fedora zuerst) und DEB härten.
Keine zweite Paketverwaltung, keine automatische Systeminstallation und keine
Änderung an der parallelen Arbeit für #16. Die bestehenden Wayland-Portale
und der Copy-Fallback aus #72 bleiben erhalten.

## Schritte

1. Paketvertrag zuerst testen: explizite DEB-Abhängigkeiten, AppStream,
   Desktop-Eintrag, Lizenzdateien und konservative GGML-CPU-Einstellungen.
2. Tauri-Konfiguration und CPU-Basis korrigieren. Der Linux-Releasebau nutzt
   Ubuntu 22.04 statt 24.04, um die GLIBC-Basis niedrig zu halten.
3. Extrahierte DEB-/AppImage-Inhalte prüfen: ausführbare App und Sidecar,
   Desktop/Icon/Metadaten/Lizenzen, ELF-Abhängigkeiten und GLIBC-Anforderungen.
   Checksummen erzeugen. Derselbe Bau läuft in PRs ohne Veröffentlichung.
4. Vorhandene npm-/Rust-Prüfungen und erreichbare Paketprüfungen ausführen.
   Installation, Update und physisches Mikrofon auf fremden Desktops nur als
   bestanden dokumentieren, wenn tatsächlich durchgeführt.
5. Diff prüfen, committen, pushen, PR mit Auto-Merge erstellen. #32 und #16
   nur mit ehrlicher Abgrenzung erfüllter und nicht geprüfter Kriterien behandeln.

## Risiken und Prüfbefehle

AppImage bündelt nicht GLIBC, Kernel, Audio-/Desktopdienste. Ein erfolgreicher
Bau ersetzt daher keinen Distributions-/Hardwaretest. Bit-identische Builds
sind ohne vollständig fixierte Systempakete und Bundler-Werkzeuge nicht zugesagt.

`npm run check`, `npm run lint`, `npm test`, `npm run build`,
beide Cargo-fmt/Clippy/Test-Suiten mit `--manifest-path` und `--locked`,
`npm audit --audit-level=high`, Paketvalidator und Metadatenvalidatoren.
