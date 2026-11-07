# Plattformen

Die Tabelle nennt die vorgesehenen Pakete. Ob sie aktuell gebaut und
veröffentlicht wurden, steht in [PROGRESS.md](PROGRESS.md) und auf
[GitHub Releases](https://github.com/mixxermannipro/Voicewright/releases).

| System | Paket | Wichtige Prüfungen |
| --- | --- | --- |
| Windows x64 | NSIS-EXE | Mikrofon in den Datenschutzeinstellungen, Kürzel, Text im externen Fenster, Programm im Infobereich |
| macOS mit Apple Silicon | DMG | Mikrofon, Kürzel und Menüleistensymbol. Das Ergebnis kann manuell kopiert werden. |
| Linux x64 mit X11 | AppImage, DEB | Mikrofon, Kürzel und Text im externen Fenster, Statussymbol abhängig vom Desktop |
| Linux x64 mit Wayland | Dieselben Linux-Pakete | Diktat über die App. Kopiere das Ergebnis manuell. Globale Kürzel und direkte Texteingabe sind in dieser Sitzung deaktiviert. |
| macOS mit Intel | Kein Paket im aktuellen Ablauf | Eigenen Build und praktische Prüfung nachholen |

Für die direkte Texteingabe unter Windows und X11 prüft Voicewright
vor dem Tippen den Fokus. Bei Fokuswechsel, Steuerzeichen oder mehrzeiligem
Text bleibt das Ergebnis zum Kopieren in der App. Voicewright verwendet für die
direkte Eingabe keinen automatischen Zugriff auf die Zwischenablage.

Autostart verwendet die Anmeldeobjekte des Systems. Beim Autostart bleibt das
Hauptfenster verborgen, wenn ein Statussymbol verfügbar ist; ohne Statussymbol
öffnet es sich. Unter Wayland ist der globale Shortcut derzeit deaktiviert.
Autostart führt dort also nur zum Tray-Symbol, über das das Fenster geöffnet
werden muss. Ob das Tray-Symbol auf dem jeweiligen Desktop erscheint, hängt von
der Desktop-Umgebung und der Installation der AppIndicator-Unterstützung ab.
Vor einer Deinstallation Autostart in den Einstellungen ausschalten, damit kein
Anmeldeeintrag zurückbleibt.

Eine erfolgreiche Paketerstellung prüft keine Geräte und keine
Berechtigungen. Für den manuellen Durchlauf siehe [TESTING.md](TESTING.md).
Fenster mit erhöhten Rechten und geschützte Eingabefelder fallen außerhalb
der vorgesehenen Unterstützung. Der Veröffentlichungsablauf sieht Ubuntu 24.04 für den Linux-Paketbau vor.
Der bisherige DEB-Test lief in Debian 12. Ältere Distributionen können an neueren Systembibliotheken scheitern.
