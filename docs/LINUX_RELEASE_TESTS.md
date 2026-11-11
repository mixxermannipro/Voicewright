# Linux-Paketabnahme / Linux package acceptance (#32)

## Paketvertrag / Package contract

Linux-AppImage und DEB werden im Pflicht-Check auf Ubuntu 22.04 gebaut.
`scripts/check-linux-bundle.py` entpackt **selbst gebaute, vertrauenswürdige**
Pakete und prüft App, ausführbaren Cleanup-Sidecar, Icons, Desktop-Eintrag,
AppStream-Verknüpfung, Lizenzhinweise, fehlende Laufzeiten und GLIBC ≤ 2.35
für alle enthaltenen ELF-Dateien. Dateien mit Setuid/Setgid werden abgelehnt.
Die AppImage-Extraktion führt ihren Runtime-Stub aus; den Prüfer nicht für
unbekannte Drittanbieter-Dateien verwenden.

AppImage and DEB are built on Ubuntu 22.04 in CI. The validator checks layout,
permissions, desktop metadata, notices, dynamic dependencies and GLIBC ≤ 2.35.
Only use it on trusted builds: AppImage extraction executes its runtime stub.

```sh
python3 -m unittest discover -s scripts -p 'test_linux_bundle.py'
python3 scripts/check-linux-bundle.py path/to/Voicewright.deb path/to/Voicewright.AppImage
```

Der Workflow speichert Pakete, `linux-package-checks.txt` und
`SHA256SUMS-linux.txt` für sieben Tage als Actions-Artefakt. Ein Tag-Release
veröffentlicht zusätzlich die gemeinsame `SHA256SUMS.txt`. Keine Release-Tags
oder Veröffentlichungen werden für die Arbeit an #32 erzeugt.
Builds are repeatable from locked sources; bit-for-bit reproducibility is
**not claimed** because system packages and downloaded bundler tools are not
fully pinned. `SOURCE_DATE_EPOCH` uses the source commit timestamp.

## Reales Testprotokoll / Real desktop test record

**Lokaler Lauf, 11. November 2026, Fedora 45 KDE Wayland, Linux x64:**
Release-DEB und AppImage gebaut; AppImage-Layout/Metadaten/Laufzeiten und
202 ELF-Dateien mit lokaler GLIBC-Grenze 2.44 geprüft. Die portable Grenze
2.35 wird für diesen Fedora-Bau absichtlich nicht erfüllt. AppImage mit
isoliertem HOME/XDG-Datenordner gestartet; Prozess blieb bis zum Testende
nach 12 Sekunden aktiv. Kein Mikrofon-/Diktat-/Update-Nachweis. Eine harmlose
GTK-Meldung zum fehlenden `appmenu-gtk-module` trat auf.
Both formats built locally; AppImage package validation passed against the
local GLIBC 2.44 baseline, not the portable 2.35 target. An isolated launch
survived 12 seconds. Audio, dictation and upgrades were not exercised.

SHA-256 der lokalen Fedora-Pakete (nicht veröffentlicht; nach Neu-Bau anders):

```text
542705c86e3771c4bc7435a3debe0d1712c563cb0dcf3c280231e8e4e7a27b41  Voicewright_0.1.0-alpha.1_amd64.deb
a143e3716d556d6178e44494a274bfa33e08845abf35148df371c7eba34cba29  Voicewright_0.1.0-alpha.1_amd64.AppImage
```

Eine bestandene Paketprüfung ersetzt diese Tests nicht. Pro Paket und Umgebung
SHA-256, Commit, Datum, CPU, Desktop und Sitzung ergänzen. „Offen“ ist kein Erfolg.
A passing packaging check does not certify these manual tests. Record the
artifact hash, commit, date, CPU, desktop and session for every actual run.

| Umgebung / Environment | Installation/Update | Audio/Download/offline DE+EN | Taste/Einfügen/Kopieren | Keyring/Modell löschen |
| --- | --- | --- | --- | --- |
| Fedora 45 KDE Wayland, AppImage (Priorität) | Offen / pending | Offen / pending | Portal + Copy: offen / pending | Offen / pending |
| Ubuntu 22.04 GNOME X11, AppImage + DEB | Offen / pending | Offen / pending | X11: offen / pending | Offen / pending |
| Ubuntu 24.04 GNOME Wayland, AppImage + DEB | Offen / pending | Offen / pending | Portal + Copy: offen / pending | Offen / pending |
| Debian 12/13, X11, AppImage + DEB | Offen / pending | Offen / pending | X11: offen / pending | Offen / pending |

1. Prüfsumme kontrollieren, ohne Node/Rust starten, Icons und Desktop-Eintrag
   prüfen. App als normaler Nutzer starten. Kein automatischer Systemstart.
2. Synthetisches DE/EN-Diktat, Modelldownload/Abbruch/Fortsetzen und anschließend
   Offline-Diktat testen. Audio-Gerätewechsel und verweigerte Rechte prüfen.
3. Unter X11 externes GTK-/Qt-/Browserfeld testen; Wayland zeigt keinen
   automatischen Einfügeweg. Portal ablehnen, erneut freigeben, Kopieren prüfen.
4. Ohne Secret Service starten; keine Klartextschlüssel, kein Absturz. Modelle
   importieren/löschen, App neustarten; fehlgeschlagene Löschung sichtbar.
5. Upgrade mit vorhandenen Settings/Modellen und erneuter Erkennung prüfen;
   Deinstallation entfernt Pakete, nicht ungefragt persönliche Daten.

Für die isolierte künstliche X11-Abnahme akzeptiert
`scripts/linux-smoke/run.sh` nun **DEB und AppImage** mit denselben Argumenten.
Sie ersetzt kein physisches Mikrofon und keine Wayland-Abnahme.
The isolated synthetic X11 smoke accepts both formats; it is not a physical
microphone or Wayland certification. See [TESTING.md](TESTING.md).
