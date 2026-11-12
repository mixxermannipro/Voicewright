# Plattformen

> **V1-Teststatus ab 12.11.2026:** Vor der persönlichen Feedbackrunde gelten nur in [VIRTUAL_TESTING.md](VIRTUAL_TESTING.md) belegt automatisierte Tests auf CI-/virtuellen OS-Runners als Kandidatengates. Die unten genannten Plattformfähigkeiten sind teilweise **geplant, implementiert oder lokal eingeschränkt geprüft**, aber keine pauschale Zusage für alle nativen Anwendungen. Echte Portal-/TCC-/Mikrofon- und Accessibility-Freigaben werden **erst beim späteren freiwilligen Eigentümer-Praxistest** geprüft; bis dahin den sicheren Copy-Fallback nutzen und Ungeprüftes markieren. Niemals Systemrechte automatisiert umgehen.


Die Tabelle nennt die vorgesehenen Pakete. Ob sie aktuell gebaut und
veröffentlicht wurden, steht in [PROGRESS.md](PROGRESS.md) und auf
[GitHub Releases](https://github.com/mixxermannipro/Voicewright/releases).

| System | Paket | Globale Taste | Automatisches Einfügen | Wichtige Prüfungen |
| --- | --- | --- | --- | --- |
| Windows x64 | NSIS-EXE | native Tauri-Taste | ja, mit Fokusprüfung | Mikrofon in den Datenschutzeinstellungen, Kürzel, Text im externen Fenster, Programm im Infobereich |
| macOS mit Apple Silicon | DMG | native Tauri-Taste | nein, bewusst kopieren | Mikrofon, Kürzel und Menüleistensymbol. Das Ergebnis wird manuell kopiert. |
| Linux x64 mit X11 | AppImage, DEB | X11-Tastenbelegung | ja, mit Fokusprüfung | Mikrofon, Kürzel und Text im externen Fenster, Statussymbol abhängig vom Desktop |
| Linux x64 mit Wayland | Dieselben Linux-Pakete | XDG-Desktop-Portal, nur nach Freigabe | nein, bewusst kopieren | Portal vorhanden und freigegeben, Kürzel außerhalb des Fensters, Kopierweg |
| macOS mit Intel | Kein Paket im aktuellen Ablauf | native Tauri-Taste | nein, bewusst kopieren | Eigenen Build und praktische Prüfung nachholen |

## Hotkey und Texteingabe sind getrennte Fähigkeiten

Voicewright behandelt globale Tasten und automatisches Einfügen als zwei
unabhängige Funktionen. Ein funktionierendes Kürzel bedeutet nicht, dass
die App auch in ein fremdes Textfeld tippen darf.

| System | Globale Taste | Automatisches Einfügen |
| --- | --- | --- |
| Linux X11 | Tauri-Plugin mit X11-Tastenbelegung | XTest über Enigo, Zielfenster geprüft |
| Linux Wayland | XDG `GlobalShortcuts`-Portal | nicht verfügbar; Text bleibt zum Kopieren |
| Windows | natives Tauri-Plugin | ja, Zielfenster geprüft |
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

Zwischen zwei Proben liegt eine kurze Stabilitätswartezeit. Dadurch wird
ein Fensterwechsel während der Vorbereitung erkannt. Der Text wird in
Graphem-Clustern (Zeichen, die zusammengehören) getippt, damit Flaggen,
Familien-Emoji und kombinierte Zeichen nicht zerteilt werden. Absätze
werden mit der Eingabetaste eingefügt. CRLF und einzelne CR werden vorher
zu LF normalisiert. Steuerzeichen außer Zeilenumbruch, mehr als 400
Zeichen und leerer Text bleiben beim Kopieren.

**Grenzen:** Ein Wechsel zwischen zwei Feldern desselben X11-Fensters ist
nicht zuverlässig erkennbar, wenn das Fenster seine X11-Kennung nicht
ändert. Passwort- und geschützte Felder werden nicht erkannt. In Feldern,
die die Eingabetaste als „Senden“ deuten, kann ein mehrzeiliges Diktat
eine Aktion auslösen; die App weist in den Einstellungen darauf hin. Eine
Wayland-Sitzung wird auch dann als Wayland behandelt, wenn XWayland ein
`DISPLAY` bereitstellt; dort bleibt es beim Kopierweg.

## Getestete Kombinationen

Stand 10. November 2026. „Bestanden“ bedeutet nur den genannten Test, keine
Freigabe für alle Anwendungen.

| Umgebung | Ergebnis | Beleg |
| --- | --- | --- |
| Linux X11, Xvfb, GTK-TextView | **Bestanden:** deutscher Text mit Umlauten, ß, Emoji, Flagge, Familien-Emoji, Gedankenstrich und zwei Absätzen kam exakt an. | `scripts/linux-smoke/x11-insertion.sh` mit dem echten Einfüge-Modul |
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
