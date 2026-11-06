# Plattformen

Die Tabelle nennt die vorgesehenen Pakete. Ob sie aktuell gebaut und
veröffentlicht wurden, steht in [PROGRESS.md](PROGRESS.md) und auf
[GitHub Releases](https://github.com/mixxermannipro/speechy/releases).

| System | Paket | Wichtige Prüfungen |
| --- | --- | --- |
| Windows x64 | NSIS-EXE | Mikrofon in den Datenschutzeinstellungen, Kürzel, Text im externen Fenster, Programm im Infobereich |
| macOS mit Apple Silicon | DMG | Mikrofon, Kürzel und Menüleistensymbol. Das Ergebnis kann manuell kopiert werden. |
| Linux x64 mit X11 | AppImage, DEB | Mikrofon, Kürzel und Text im externen Fenster, Statussymbol abhängig vom Desktop |
| Linux x64 mit Wayland | Dieselben Linux-Pakete | Diktat über die App. Kopiere das Ergebnis manuell. Globale Kürzel und direkte Texteingabe sind in dieser Sitzung deaktiviert. |
| macOS mit Intel | Kein Paket im aktuellen Ablauf | Eigenen Build und praktische Prüfung nachholen |

Für die geplante direkte Texteingabe unter Windows und X11 prüft VoxTakt
vor dem Tippen den Fokus. Bei Fokuswechsel, Steuerzeichen oder mehrzeiligem
Text bleibt das Ergebnis zum Kopieren in der App. VoxTakt verwendet für die
direkte Eingabe keinen automatischen Zugriff auf die Zwischenablage.

Eine erfolgreiche Paketerstellung prüft keine Geräte und keine
Berechtigungen. Für den manuellen Durchlauf siehe [TESTING.md](TESTING.md).
Fenster mit erhöhten Rechten und geschützte Eingabefelder fallen außerhalb
der vorgesehenen Unterstützung. Linux-Pakete werden auf Ubuntu 24.04
gebaut. Ältere Distributionen können an neueren Systembibliotheken scheitern.
