# Voicewright V1 für Fedora – Entwurf

Datum: 11. November 2026. Status: **Vom Anwender zur Umsetzung freigegeben**.
Ausgangsstand: `a62cd8467b97964fcb77f957ac5f0642ee9d13a4` auf `main`.
Arbeitszweig: `feat/v1-fedora-release`.

## Auftrag und verbindliche Entscheidung

Eine alltagstaugliche V1 der vorhandenen lokalen Diktat-App bauen und für
Fedora veröffentlichen. Der Anwender verlangt ausdrücklich **automatisches
Einfügen auch unter Fedora Wayland**. Ein Produkt, das dort ausschließlich
Kopieren anbietet, erfüllt diesen Auftrag nicht.

Weitere ausdrückliche Entscheidungen des Anwenders:

- Bei einem Fokuswechsel darf in das **im Ausgabezeitpunkt aktive Feld**
  eingefügt werden. Das ursprüngliche Feld muss auf Wayland nicht festgehalten
  werden. Die fehlende allgemeine Passwortfeld-Erkennung bleibt sichtbar.
- Die kostenlosen, festgelegten Modellgewichte Whisper Base (147.951.465
  Bytes) und Qwen3-0.6B-Q8_0 (639.446.688 Bytes) dürfen für die lokalen Tests
  heruntergeladen werden. Prüfsummen prüfen und außerhalb von Git speichern.
- Wenn eine dauerhafte Portal-Freigabe nicht möglich ist, ist ein erneuter
  Dialog beim App-Start akzeptiert. Nicht erst nach einem Diktat fragen.

Der Auftrag umfasst PR, Merge und Release sowie das nachträgliche Schließen
tatsächlich behobener Issues. Issues dienen ausdrücklich nicht zur Auswahl
oder Priorisierung der V1-Arbeit. Bis zum Abschluss wird keine Issue-Liste
abgerufen. Vorhandene Verweise in der Projektdokumentation sind kein Auftrag,
die jeweilige gesamte Anforderung als erledigt zu behandeln.

## Ziel und Grenze

Freigabeziel ist `1.0.0` für **Fedora 45, Linux x64, KDE Plasma Wayland**.
Das ist die vorhandene lokale Testumgebung. Die App bleibt auf Tauri 2,
Rust, React und TypeScript aufgebaut. Die bewährte CPU-Erkennung mit
Whisper bleibt erhalten; keine Neuentwicklung der Erkennungsengine.

GNOME Wayland erhält nur dann einen Unterstützungsnachweis, wenn dort
tatsächlich getestet wurde. Gleiches gilt für X11. Windows und macOS werden
nicht als praktisch geprüft ausgegeben; bestehende Funktionen dürfen nicht
absichtlich beschädigt werden. Ein Fedora-Release soll nicht von der
praktischen Freigabe anderer Betriebssysteme abhängen.

Keine neuen GPU-/Parakeet-Engines, keine Diktat-Historie, keine automatische
Cloud-Nutzung, kein Updater und keine Zertifikatsbeschaffung in dieser V1.
Nicht geprüfte Funktionen/Modelle werden erkennbar so bezeichnet.

## Betrachtete Wege

1. **Vorhandenen Kern vervollständigen – Empfehlung des Haupt-Agenten.**
   Bestehende Aufnahme, Erkennung, Korrektur und sichere Abbruchlogik behalten.
   Wayland-Ausgabe ergänzen, das freigegebene UI-Konzept umsetzen und den
   Fedora-Release technisch und praktisch absichern. Weniger Risiko als ein
   Neubau, aber echte Integrations- und Desktop-Tests bleiben erforderlich.
2. **Nur den bisherigen Stand verpacken.** Kleinerer Aufwand, erfüllt aber
   weder das verbindliche UI-Ziel noch das verlangte Wayland-Einfügen.
3. **App/Erkennung neu schreiben.** Verwirft bereits getestete Kernlogik ohne
   belegten Nutzen und erweitert die Fehlerfläche. Nicht vorgesehen.

## Alltagspfad

Nach der bewussten Einrichtung bleibt Voicewright im Hintergrund:

```text
Textfeld wählen → globale Taste → sprechen → Taste loslassen/erneut drücken
→ lokal erkennen → optional korrigieren → Text am Cursor einfügen
```

Keine permanente Mikrofonaufnahme. Das Mikrofon läuft nur während eines
bewusst gestarteten Diktats. Ein Abbruch verhindert spätere Ausgabe.
Ablehnung einer Berechtigung, Verlust der Portal-Sitzung oder Einfügefehler
bleiben sichtbar; Text geht nicht verloren. Kopieren ist dann eine
Fehler-Rückfallebene, nicht der normale Wayland-Ausgabemodus.

## Wayland-Einfügen: zunächst technischer Nachweis

Den offiziellen XDG-RemoteDesktop-Weg mit ausdrücklicher Nutzerfreigabe
untersuchen und minimal praktisch nachweisen. Nur benötigte Eingaberechte
anfordern, keine Bildschirmaufnahme und keine Maussteuerung. Auf dem
Zielrechner sind RemoteDesktop v2, Clipboard v1 und GlobalShortcuts v2
vorhanden; ihre Anwesenheit beweist keine erfolgreiche Texteingabe.

Der Implementierer entscheidet nach API- und Desktop-Prüfung zwischen
Unicode-Texteingabe und Portal-Zwischenablage mit Einfügetaste. Entscheidung
und Restrisiken vor Integration dokumentieren. Kein Root-Dienst, kein
`uinput`-Umbau, keine heimliche KDE-Sonderfreigabe und kein XWayland-Trick als
Ersatz für echte Wayland-Unterstützung.

Erforderliche Eigenschaften:

- Berechtigungen während der Einrichtung anfordern, nicht nach dem Diktat
  über dem Zielfenster; Ablehnung/Widerruf sauber behandeln.
- Aufnahme-/Abbruch-Snapshot und Sitzungsidentität bis zur Ausgabe erhalten.
  Keine verspätete Ausgabe nach Abbruch, Pause oder neuer Sitzung.
- Gehaltene Steuertasten dürfen den Text nicht in Tastaturbefehle verwandeln.
- Unicode einschließlich Umlauten, ß, Emoji und Absätzen erhalten. Keine
  Enter-Tastendrücke, die statt Text ein Formular unbeabsichtigt absenden.
- Bei Zwischenablagenutzung bestehende Daten nicht stillschweigend verlieren
  und zwischenzeitliche Nutzeränderungen nicht überschreiben. Kann ein Format
  nicht sicher behandelt werden, darf die App nicht trotzdem Erfolg melden.
- Fokus-/Passwortfeld-Erkennung unter Wayland nicht versprechen, wenn der
  Desktop sie nicht bereitstellt. Der Anwender hat die Ausgabe ins aktuell
  aktive Feld bestätigt. Vor dem Aktivieren darüber informieren, dass ein
  Fokuswechsel das Ausgabeziel ändert und Passwortfelder nicht allgemein
  erkannt werden. Einfügen nur nach bewusst gestartetem Diktat und mit
  erklärter Berechtigung; keine Garantie für das ursprüngliche Feld behaupten.

**Stoppregel:** Ist eine tragfähige automatische Ausgabe nicht nachweisbar,
keine Copy-only-Version als fertige V1 veröffentlichen. Blocker und möglichen
anderen Weg dem Anwender zur Entscheidung vorlegen. Keine zusätzlichen
Systemrechte oder Installationen ohne Zustimmung.

## Oberfläche und Hintergrundbetrieb

Visuelle Autorität bleibt `docs/design/VOICEWRIGHT_UI_CONCEPT.md` samt
Mockups. Keine neue Gestaltungsdiskussion und kein neues Dashboard.

```text
Einstellungen
├─ Allgemein: Hintergrundbetrieb, bewusster Autostart, System/Hell/Dunkel
├─ Diktat: Mikrofon, Sprache, Ausgabe, optionale Korrektur
├─ Modelle: aktives Modell, Verwaltung und bewusste Downloads
├─ Tastenkürzel: Aufnahme, Halten/Umschalten, Abbruch, Freigaben
└─ Datenschutz: lokale Verarbeitung, Cloud-Opt-in, Berechtigungen
```

Die Ersteinrichtung führt zu einem echten externen Einfügetest. Erststart und
fehlende Einrichtung bleiben erreichbar; nach Einrichtung öffnet ein normaler
Hintergrundstart kein Dashboard. Autostart bleibt standardmäßig aus.
Fehlt ein funktionsfähiges Tray, darf die App nicht unerreichbar verschwinden.
Das Tray bietet Status, Pause/Fortsetzen, Einstellungen und Beenden.

Ein abschaltbares kleines Aufnahme-/Verarbeitungs-HUD darf keinen Fokus
stehlen und keine privaten Transkripte ungefragt anzeigen. Wenn ein Desktop
ein solches Overlay nicht sicher erlaubt, bleibt es dort aus und der Status
ist anderweitig erreichbar. Das automatische Einfügen bleibt Pflicht.

Alle sichtbaren Texte und relevanten Fehler in DE/EN. Tastaturbedienung,
sichtbarer Fokus, Screenreader-Beschriftungen, 200%-Skalierung, Kontrast und
reduzierte Bewegung berücksichtigen. Keine dekorativen Zusatzbibliotheken.

## Daten und Sicherheit

Bestehende Settings-/Modellmigration erhalten. Neue Einstellungen erhalten
rückwärtsverträgliche Standardwerte und Tests; Exporte bleiben ohne Schlüssel.
Portal-Zugangsdaten/Restore-Tokens nicht in exportierbare Einstellungen oder
Logs schreiben. Fehlerdiagnosen enthalten keine Diktate oder Zugangsdaten.
Keine vorhandenen Nutzermodelle/-einstellungen für Tests verändern.

Automatische Einfügung bleibt eine ausdrücklich sichtbare Funktion. Eine
gesprochene Formatierungsanweisung führt selbst keine Betriebssystemaktion
aus. Cloud-Korrektur bleibt opt-in mit eigener Konfiguration; keine echten
kostenpflichtigen Cloud-Aufrufe für die Freigabe.

## Pakete und Veröffentlichung

Vorschlag des Haupt-Agenten: **RPM für Fedora und AppImage** veröffentlichen.
RPM erhält vollständige Laufzeitabhängigkeiten, Desktop-Eintrag, Icon,
AppStream-Metadaten und Lizenzdateien. Installation/Upgrade/Entfernung zuerst
isoliert testen; keine Systeminstallation auf dem Nutzerrechner ohne Freigabe.
AppImage mit enthaltener Cleanup-Engine aus dem portablen Linux-Bau liefern.
Die bestehende GLIBC-Obergrenze 2.35 nicht heimlich für einen lokalen
Fedora-Bau aufweichen.

Der stabile Fedora-Ablauf akzeptiert `v1.0.0`, prüft konsistente App-Versionen
einschließlich Lockdateien, Herkunft aus dem freigegebenen `main` und grüne
Prüfungen. Vorab-Tags bleiben korrekt als Vorabversionen markiert.
Keine Annahme einer starren plattformübergreifenden Zahl von Installern.
Prüfsummen und Linux-Paketprüfbericht dauerhaft zum Release legen.

Pakete ohne Herstellerzertifikat ausdrücklich als unsigniert kennzeichnen.
SHA-256 prüft Dateiübereinstimmung, ersetzt aber keine Herausgebersignatur.
Keine Windows-/macOS-Freigabe behaupten, nur weil Fedora veröffentlicht wurde.

## Abnahme: Beleg statt Versionsnummer

1. Projektprüfungen aus `AGENTS.md`: TypeScript, Lint, Vitest, Web-Build,
   beide Rust-Formatprüfungen, Clippy und Tests mit `--locked`, npm-Audit.
   Zusätzliche Paket-/Release-Gate-Tests für RPM und stabile Tags.
2. Neue Regressionstests für Portalzustände, Abbruch vor/während Ausgabe,
   verlorene Freigabe, Unicode, Clipboard-Konflikte, Pause, Settingsmigration
   und UI-Berechtigungszustände. Simulierte Tests als solche kennzeichnen.
3. Echte lokale DE-/EN-Modelltests mit den ausdrücklich zum Download
   freigegebenen Whisper-Base-/Qwen-Gewichten; SHA-256 aus dem festen Katalog
   prüfen. Andere Downloads/Installationen nur nach Zustimmung. Keine stumme
   Umdeutung übersprungener Tests in bestandene Tests.
4. Endgültige Pakete auf Fedora KDE Wayland starten und DE/EN von Mikrofon
   bis zur automatischen Ausgabe in native Qt-, GTK- und Browser-Textfelder
   nachweisen. Hotkey Hold/Toggle, Abbruch, Freigabe/Ablehnung/Widerruf,
   Fokuswechsel, Unicode/Absätze und zwischenzeitliche Zwischenablageänderung
   prüfen. Physisches Mikrofon und notwendige Systemdialoge erfordern ggf.
   Mithilfe des Anwenders; künstliches Audio ersetzt diesen Nachweis nicht.
5. Ersteinrichtung, Download/Abbruch/Fortsetzung, Offline-Neustart,
   fehlendes Modell/Mikrofon, Gerätewechsel, Kopier-Rückfall, Pause, Theme,
   Hintergrundbetrieb, Autostart und Paket-Upgrade prüfen.
6. Pro Nachweis Datum, Quellstand, Paket-SHA-256, Fedora-/Desktopversion und
   echte Ergebnisse dokumentieren. Offene Pflichtprüfungen blockieren den
   stabilen Release; kein stilles Herabstufen des Wayland-Ziels.

## Zusammenarbeit, Git und Rücknahme

DeepSeek V4.1 Flash Free von OpenCode für die beauftragten Helfer verwenden.
Helfer recherchieren/prüfen parallel in getrennten Bereichen; der Haupt-Agent
integriert Änderungen in kleinen überprüfbaren Schritten. Die vorhandene
unversionierte `.github/workflows/platforms.yml` bleibt Nutzerarbeit und
wird weder gelöscht noch ungefragt in einen Commit aufgenommen.

Drei DeepSeek-Prüfberichte wurden erfolgreich geliefert. Bei zwei weiteren
Wayland-Recherchen meldete OpenCode das ausgeschöpfte Gratis-Kontingent.
Diese Recherchen übernimmt der Haupt-Agent selbst. Kein kostenpflichtiges
Ersatzmodell und kein Abonnement ohne ausdrücklichen Auftrag.

Nach Designfreigabe einen konkreten Implementierungsplan mit Dateien,
Schritten, Befehlen, Tests und Risiken erstellen. Erst danach Produktcode.
Die integrierte Änderung lokal und in CI prüfen, PR öffnen und nur einen
grünen, inhaltlich geprüften Stand gemäß ausdrücklichem Merge-/Release-Auftrag
zusammenführen. Tag und Release erst nach bestandener Zielabnahme.

Erst anschließend offene Issues lesen und einzeln gegen tatsächlich gelieferte
Funktion und Nachweise abgleichen. Nur vollständig erfüllte Anforderungen mit
Begründung und Verweisen schließen; Teilfortschritte kommentieren, nicht als
erledigt schließen.

Fehlerhafte Änderungen durch nachvollziehbare Folge-/Revert-PRs zurücknehmen,
keine geteilte Historie umschreiben. Persönliche Daten bleiben erhalten.

## Freigabe

Der Anwender hat den vollständigen Umfang mit „Ja, so umsetzen“ freigegeben:
Fedora 45 KDE Wayland, automatische Ausgabe ins aktive Feld, die vorhandene
Fünf-Bereiche-UI-Vorgabe, Hintergrundbetrieb, Theme, bewusster Autostart,
Tray-Pause, RPM/AppImage und die beschriebenen Abnahmebedingungen. PR, Merge
und stabiler Release sind beauftragt, aber erst nach bestandenen Prüfungen.
Ein Versionssprung allein ist keine Funktionsabnahme.
