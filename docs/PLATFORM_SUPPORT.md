# Plattformen

> **V1-Teststatus ab 12.11.2026:** Vor der persönlichen Feedbackrunde gelten nur in [VIRTUAL_TESTING.md](VIRTUAL_TESTING.md) belegt automatisierte Tests auf CI-/virtuellen OS-Runners als Kandidatengates. Die unten genannten Plattformfähigkeiten sind teilweise **geplant, implementiert oder lokal eingeschränkt geprüft**, aber keine pauschale Zusage für alle nativen Anwendungen. Echte Portal-/TCC-/Mikrofon- und Accessibility-Freigaben werden **erst beim späteren freiwilligen Eigentümer-Praxistest** geprüft; bis dahin den sicheren Copy-Fallback nutzen und Ungeprüftes markieren. Niemals Systemrechte automatisiert umgehen.


Die Tabelle nennt die vorgesehenen Pakete. Ob sie aktuell gebaut und
veröffentlicht wurden, steht in [PROGRESS.md](PROGRESS.md) und auf
[GitHub Releases](https://github.com/mixxermannipro/Voicewright/releases).

| System | Paket | Globale Taste | Automatisches Einfügen | Wichtige Prüfungen |
| --- | --- | --- | --- | --- |
| Windows x64 | NSIS-EXE | native Tauri-Taste | nur native Unicode-Editfelder, einzeilig; nativ noch zu prüfen | Mikrofon in den Datenschutzeinstellungen, Kürzel, Text im externen Fenster, Programm im Infobereich |
| macOS mit Apple Silicon | DMG | native Tauri-Taste | nein, bewusst kopieren | Mikrofon, Kürzel und Menüleistensymbol. Das Ergebnis wird manuell kopiert. |
| Linux x64 mit X11 | AppImage, DEB | X11-Tastenbelegung | nur verifiziertes bearbeitbares AT-SPI-Textfeld; sonst Copy | Mikrofon, Kürzel und Text im externen Fenster, Statussymbol abhängig vom Desktop |
| Linux x64 mit Wayland | Dieselben Linux-Pakete | XDG-Desktop-Portal, nur nach Freigabe | nein, bewusst kopieren | Portal vorhanden und freigegeben, Kürzel außerhalb des Fensters, Kopierweg |
| macOS mit Intel | Kein Paket im aktuellen Ablauf | native Tauri-Taste | nein, bewusst kopieren | Eigenen Build und praktische Prüfung nachholen |

## Hotkey und Texteingabe sind getrennte Fähigkeiten

Voicewright behandelt globale Tasten und automatisches Einfügen als zwei
unabhängige Funktionen. Ein funktionierendes Kürzel bedeutet nicht, dass
die App auch in ein fremdes Textfeld tippen darf.

| System | Globale Taste | Automatisches Einfügen |
| --- | --- | --- |
| Linux X11 | Tauri-Plugin mit X11-Tastenbelegung | Literaler AT-SPI-Textaufruf an das erfasste bearbeitbare Feld, keine Return-Taste |
| Linux Wayland | XDG `GlobalShortcuts`-Portal | nicht verfügbar; Text bleibt zum Kopieren |
| Windows | natives Tauri-Plugin | native Edit-Whitelist, keine Passwort-/Readonly-Felder; Absätze Copy-only; nativ ungeprüft |
| macOS | natives Tauri-Plugin | nein; Text bleibt zum Kopieren |

## Wayland: GlobalShortcuts-Portal

Unter Wayland kann eine normale Anwendung keine globale Taste exklusiv
belegen. Voicewright fragt deshalb das standardisierte Portal
`org.freedesktop.portal.GlobalShortcuts` mit Version 1 oder neuer an. Ob
das Portal existiert, welche Tasten es erlaubt und ob der Desktop eine
Freigabe verlangt, entscheidet die jeweilige Desktop-Umgebung zur Laufzeit.
Es gibt keine fest eingebaute Liste „GNOME kann dies, KDE kann das“: Die
App fragt die tatsächliche Schnittstelle und zeigt das Ergebnis an.

Die App fordert zwei Bindungen an:

- `dictation` für Start und Stopp des Diktats,
- `cancel` nur, wenn in den Einstellungen eine Abbruchtaste gesetzt ist.

Der Desktop zeigt in der Regel einen Freigabedialog. Die Oberfläche
unterscheidet diese Zustände:

| Zustand | Bedeutung | Verhalten in der App |
| --- | --- | --- |
| `pending` | Der Freigabedialog läuft oder die Antwort fehlt noch. | Aufnahme im App-Fenster bleibt möglich. |
| `active` | Das Portal hat mindestens die Diktattaste freigegeben. | Kürzel funktioniert außerhalb des Fensters. |
| `denied` | Der Nutzer hat abgelehnt oder eine Pflicht-Taste wurde nicht vergeben. | Aufnahme im Fenster und Kopieren; „Freigabe erneut anfragen“ ist sichtbar. |
| `unavailable` | Portal fehlt, ist zu alt, nicht erreichbar oder wurde geschlossen. | Aufnahme im Fenster und Kopieren. |
| `error` | Die Portalanfrage ist aus einem anderen Grund gescheitert. | Aufnahme im Fenster und Kopieren. |

Wird die Abbruchtaste nicht freigegeben, bleibt die Diktattaste aktiv und
die App weist auf die fehlende Abbruchtaste hin. Ändert der Nutzer die
Tasten in den Einstellungen, wird die Portal-Sitzung geschlossen und mit
den neuen Bindungen neu angefragt. Meldet der Desktop eine Änderung der
freigegebenen Bindungen, aktualisiert die App den angezeigten Zustand.

**Bewusste Grenze:** Voicewright fragt weder das `Input`- noch das
`RemoteDesktop`-Portal an. Beide würden eine breite Fernsteuerungs-
Berechtigung verlangen, die weit über das Einfügen eines Diktats
hinausgeht. Es gibt keine Root-, `uinput`-, `sudo`- oder Keylogging-
Umgehung. Wenn der Desktop keine globale Taste oder keine Texteingabe
erlaubt, bleibt der Weg über das App-Fenster und die Zwischenablage.

## Wayland: Warum kein automatisches Einfügen

Ein normaler Wayland-Client kann keine Tastendrücke in ein fremdes Fenster
senden. Voicewright behauptet das deshalb nicht. Der erkannte Text wird
nach der Aufnahme in der App angezeigt und bleibt dort, bis der Nutzer ihn
bewusst kopiert. Die Zwischenablage wird nicht im Hintergrund verändert
und nicht gelöscht. Ein fehlgeschlagenes Einfügen führt nie dazu, dass das
Ergebnis verloren geht.

## X11: Fokusprüfung, Unicode und Absätze

Unter X11 prüft Voicewright vor dem Tippen und vor jedem kurzen Stück:

- das Eingabefokus-Fenster,
- das aktive Fenster (`_NET_ACTIVE_WINDOW`),
- die Prozesskennung (`_NET_WM_PID`),
- ob das Fenster sichtbar ist,
- ob Shift, Strg, Alt, Super oder AltGr gehalten werden.
- die eindeutige AT-SPI-Feldidentität im selben Prozess und aktiven Fenster,
- ob Rolle/Zustände ein sichtbares, fokussiertes, bearbeitbares Textfeld melden;
  Passwort-, Terminal-, Read-only-, unbekannte und mehrdeutige Ziele blockieren.

Zwischen zwei Proben liegt eine kurze Stabilitätswartezeit. Dadurch wird
ein Fensterwechsel während der Vorbereitung erkannt. Linux schreibt den
vollständigen UTF-8-Text mit `EditableText.InsertText` direkt an das erfasste
Feld. Dabei wird keine Return-/Enter-Taste gedrückt; Absätze können dadurch
nicht allein als Tastaturaktion „Senden“ auslösen. Vorhandene Textselektion
wird nicht ersetzt: in diesem Fall bleibt der Kopierweg. CRLF und einzelne CR werden vorher
zu LF normalisiert. Steuerzeichen außer Zeilenumbruch, mehr als 400
Zeichen und leerer Text bleiben beim Kopieren.

**Grenzen:** Die Zielanwendung muss korrekte AT-SPI-Metadaten und die
Text-/EditableText-Schnittstellen anbieten. Ohne Bus/Bridge, bei unbekanntem
Widget, falschen Metadaten oder Zeitlimit gibt es keine automatische Ausgabe.
Es werden keine Zieltexte gelesen, nur Feld-/Fokusmetadaten und Zeichenanzahl.
Die Prüfungen sind keine atomare Betriebssystem-Sperre gegen jedes denkbare
Fokus-/App-Rennen. Bei unbestätigter Ausgabe nach einem Aufruf erfolgt kein
automatischer zweiter Versuch; der Text bleibt mit Warnung verfügbar. Eine
Wayland-Sitzung wird auch dann als Wayland behandelt, wenn XWayland ein
`DISPLAY` bereitstellt; dort bleibt es beim Kopierweg.

**English:** X11 insertion is field-addressed literal UTF-8 through AT-SPI,
never a Return event. Missing/ambiguous/protected field metadata or selections
mean copy-only. No target text is read. Windows currently allows only verified
native `Edit` controls and keeps paragraphs copy-only; its native OS behavior
still needs CI evidence. Neither route is a universal guarantee for custom apps.

Der AT-SPI-Vertrag verwendet Zeichenpositionen für Caret/Zeichenanzahl und
UTF-8-**Bytes** für die `InsertText`-Länge, siehe
[offizielle EditableText-Schnittstelle](https://gitlab.gnome.org/GNOME/at-spi2-core/-/blob/main/xml/EditableText.xml).
Voicewright prüft das Zeichenanzahl-Delta ohne Text auszulesen. Eine
abweichende Toolkit-Implementierung führt nach dem Aufruf zu „nicht bestätigt“,
nicht zu blindem Wiederholen. Beobachtbare Cursor-/Selektionsänderungen während
der Vorbereitung blockieren; ein atomarer Ausschluss aller Rennen ist nicht
Teil des Protokolls.

## Getestete Kombinationen

Stand 10. November 2026. „Bestanden“ bedeutet nur den genannten Test, keine
Freigabe für alle Anwendungen.

| Umgebung | Ergebnis | Beleg |
| --- | --- | --- |
| Linux X11, Xvfb, GTK-TextView/Entry, privater AT-SPI-Bus | **Lokal virtuell bestanden am 12.11.2026:** Unicode/Emoji/Absatz exakt ohne Return; Passwort, Selektion, Feldwechsel, fehlender Bus und Absatz im Einzeilenfeld blockiert. Noch kein nativer All-App-Nachweis. | `scripts/linux-smoke/x11-insertion.sh` mit dem echten Einfüge-Modul, netzloser Container |
| KDE Plasma Wayland, Portal 2 | **Teilweise:** Portal erreichbar, Sitzung anlegen und schließen über `ashpd` bestanden. Freigabedialog und echte Tastenbindung nicht automatisiert. | Manueller Lauf am 10. November 2026 in dieser Sitzung |
| Linux X11, vollständiges DEB, GTK | **Bestanden am 6. November 2026 mit älterem Stand:** deutsches Diktat, Halten und Umschalten, lokale Korrektur. Mit diesem Branch nicht erneut als DEB geprüft. | [PROGRESS.md](PROGRESS.md), [TESTING.md](TESTING.md) |
| GNOME Wayland | **Offen:** in dieser Umgebung nicht vorhanden. Die App nutzt denselben Portalweg; Freigabe und Tastenbindung müssen auf GNOME geprüft werden. | Offener Plattformtest |
| wlroots Wayland (z. B. Sway/Hyprland) | **Offen:** nicht vorhanden. Ob das Portal GlobalShortcuts anbietet, hängt von der installierten Portal-Implementierung ab. | Offener Plattformtest |
| XWayland in einer Wayland-Sitzung | **Nicht getestet:** wird bewusst als Wayland behandelt und fügt nicht automatisch ein. | Offener Plattformtest |
| Qt und Browser unter X11 | **Offen:** im Testcontainer nicht vorhanden. GTK ist abgedeckt; Qt und Browser brauchen einen eigenen Lauf. | Offener Plattformtest |
| Windows und macOS | **Nicht in dieser Umgebung getestet.** | Offener Plattformtest |

Eine erfolgreiche Paketerstellung prüft keine Geräte und keine
Berechtigungen. Für den manuellen Durchlauf siehe [TESTING.md](TESTING.md).
Fenster mit erhöhten Rechten und geschützte Eingabefelder fallen außerhalb
der vorgesehenen Unterstützung. Der Linux-Paketbau läuft auf Ubuntu 22.04;
der Paketprüfer begrenzt enthaltene ELF-Dateien auf GLIBC 2.35. Fedora nutzt
AppImage. Der bisherige DEB-Test lief in Debian 12. Das ist kein Nachweis für
die neuen Releasepakete. Testziele, Paketupdates und tatsächliche Abnahmen
stehen im [Linux-Testprotokoll](LINUX_RELEASE_TESTS.md).
