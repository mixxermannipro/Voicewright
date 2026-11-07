# Installation

Falls eine Vorabversion verfügbar ist, findest du ihre Dateien in
[GitHub Releases](https://github.com/mixxermannipro/Voicewright/releases).
Die [Plattformübersicht](PLATFORM_SUPPORT.md) zeigt, welche Pakete der
Veröffentlichungsablauf erzeugt und welche Prüfungen erforderlich sind.

## Einstellungen übernehmen und wiederherstellen

Die App kann Einstellungen lokal als JSON-Datei exportieren und mit
Vorschau wieder importieren. Exportierte Dateien enthalten keine
API-Schlüssel und keine Aufnahme; eigene Begriffe und Prompts können
aber vertrauliche Informationen enthalten. Details zu Schema-Migration,
Backup beschädigter Dateien und dem sicheren Wiederherstellen stehen
unter [Einstellungs-Backup](SETTINGS_BACKUP.md).

## Optionale Diktatbefehle

Unter **Einstellungen → Aufnahmeverhalten** kannst du explizite
gesprochene Satzzeichen und Zeilenumbrüche einschalten. Standardmäßig
bleibt die Funktion aus, und bei Aktivierung werden ausschließlich
Textzeichen umgewandelt, keine Betriebssystembefehle ausgeführt.
Liste, Beispiele und Grenzen: [Gesprochene Textformatierung](SPOKEN_FORMATTING.md).

## Für Nutzer

1. Wähle ein Paket für dein Betriebssystem und deine Prozessorart. Vergleiche
   die Prüfsumme der Datei mit `SHA256SUMS.txt` aus derselben Veröffentlichung.
2. Starte unter Windows die EXE-Datei. Öffne auf einem Apple-Silicon-Mac die
   DMG-Datei und ziehe die App nach **Programme**. Unter Ubuntu kannst du das
   DEB-Paket über die Paketverwaltung installieren. Eine AppImage-Datei kannst
   du mit `chmod +x <Dateiname.AppImage>` ausführbar machen und starten.
3. Gib den Mikrofonzugriff frei. Auf dem Mac verwendest du die App zum
   Aufnehmen und kopierst das Ergebnis bei Bedarf selbst.
4. Lade in der App ein Sprachmodell herunter. Probiere anschließend ein kurzes
   Diktat mit einem leeren Testdokument.

Für veröffentlichte Pakete sind Node.js, Python und Rust zur Nutzung
entbehrlich. Windows verwendet die WebView2-Laufzeit. Linux nutzt
Systembibliotheken, die je nach Paket und Distribution vorhanden sein müssen.
Für Paketwarnungen und Signaturen siehe [RELEASE.md](RELEASE.md).

## Aus Quellcode starten

Der Paketbau verwendet Node.js 24 und Rust 1.99.1. Zusätzlich brauchst du
CMake und Clang mit libclang.
Beachte außerdem die [Tauri-Voraussetzungen](https://v2.tauri.app/start/prerequisites/).
Auf Windows werden die C++-Werkzeuge von Visual Studio und WebView2 gebraucht,
auf macOS die Xcode-Werkzeuge. Unter Ubuntu 24.04 werden diese zusätzlichen
Pakete gebraucht:

```sh
sudo apt-get install build-essential cmake clang libclang-dev \
  libwebkit2gtk-4.1-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev \
  libasound2-dev libdbus-1-dev libx11-dev libxdo-dev
```

Führe die Befehle aus dem Hauptordner des Projekts aus:

```sh
npm ci
npm run prepare:engine
npm run tauri -- dev
```

`prepare:engine` baut die mitgelieferte Textkorrektur für deinen Rechner.
Für ein Installationspaket nutze `npm run tauri -- build`.
