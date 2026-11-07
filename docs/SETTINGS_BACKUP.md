# Einstellungen sichern, importieren und zurücksetzen

Stand: Feature-Branch zu Issue #26. **Nicht auf realen Zielplattformen getestet**.

## Sicherung exportieren

Öffne **Einstellungen → Sicherung und Wiederherstellung →
Gespeicherte Einstellungen exportieren** und wähle eine lokale JSON-Datei.
Der Export enthält die **bereits gespeicherten**, nicht die ungespeicherten
Entwurfseinstellungen. Enthalten sind u. a. Oberflächen-/Sprachauswahl,
Modellreferenzen, Tastenkürzel, Bearbeitungsanweisungen, eigene Vorlagen,
Wörterliste und Providerkonfigurationen einschließlich ggf. eigener
Serveradressen. Der Export enthält **keine** API-Schlüssel aus dem
Betriebssystem-Keyring, keine Roh-Audiodaten und keinen Diktatverlauf.
Behandle exportierte Prompts und Begriffe trotzdem als potenziell vertraulich.

Das Format heißt `voicewright-settings`, mit
`schema_version: 3`; die JSON-Daten enthalten einen Unterblock `settings`.
Das System speichert die Datei auf dem ausgewählten lokalen Laufwerk,
nicht in einem externen Cloudkonto. Eine vom Betriebssystem selbst
synchronisierte Ordnerablage kann natürlich trotzdem übertragene Dateien
enthalten.

## Import mit Vorschau und Rückgängig

1. **Einstellungen importieren** öffnet einen lokalen Dateidialog.
2. Die ausgewählte JSON-Datei wird auf eine Größe von höchstens 256 KiB,
   Formatkennung, Schemanummer, unterstützte Werte, Modellkennungen,
   Shortcuts und Provider-URLs geprüft.
3. Erst nach erfolgreicher Prüfung zeigt die App eine Vorschau der
   wichtigsten Daten. **Import verwerfen** ändert nichts.
4. **In Einstellungen übernehmen** lädt die Werte als **ungespeicherten
   Entwurf**. Über **Änderungen verwerfen** kannst du zum gespeicherten
   Zustand zurück.
5. Erst **Speichern** aktiviert die neuen Werte und schreibt sie atomar.
   Wenn ein Shortcut-Update oder die Speicherung fehlschlägt, bleibt die
   vorherige Einstellung in der Anwendung bzw. auf dem Datenträger erhalten.

**Sichere Voreinstellungen:** Cloud-Korrektur wird beim Import auf *Aus*
gesetzt; eine alte Mikrofon-Gerätekennung wird entfernt. API-Schlüssel
werden weder importiert noch automatisch aus dem Export rekonstruiert.
Installierte Modelle sind nicht Teil der JSON-Datei; fehlende Modelle
müssen separat heruntergeladen oder importiert werden. Provider-Endpunkte
und vorinstallierte Modelle müssen nach dem Import geprüft werden.

## Werkseinstellungen und individuelle Daten

**Werkseinstellungen vormerken** setzt ausschließlich den Entwurf
zurück. Der Vorgang ist erst nach **Speichern** dauerhaft und löscht
keine Modelle oder Schlüssel im OS-Keyring. Um persönliche Daten
vollständig zu löschen, sind bisher **separate** Schritte nötig:
über die Anbieteroberfläche jeden hinterlegten API-Schlüssel entfernen,
über die Modellübersicht Modelle löschen, Einstellungen ggf. entfernen
und OS-Zwischenablage/OS-Sicherungen gesondert überprüfen. Ein
globaler Löschknopf ist in diesem Arbeitspaket nicht implementiert;
die vollständige Umsetzung aus Issue #26 bleibt daher offen.

## Schema-Migration und beschädigte Datei

Die neue Version speichert `schema_version: 3`. Alte Alpha-Dateien
ohne Version werden beim Laden auf das neue Format abgebildet.
Zusätzliche Migrationspfade für synthetische Versionen 1 und 2
sind in Rust-Unit-Tests beschrieben. Ein späteres Schema als Version 3
wird nicht stillschweigend als kompatibel behandelt.

Wenn die Konfiguration nicht lesbar oder ungültig ist, erstellt die App
vor einer Rückmeldung eine **unveränderte** lokale Backup-Kopie im
Anwendungsdatenordner (`settings.invalid-01.bak`, fortlaufend nummeriert).
Der ursprüngliche Datenstand bleibt unangetastet, bis du neue
Einstellungen ausdrücklich speicherst. Vor dieser Speicherung wird die
Sicherung nötigenfalls erneut erstellt. Schlägt die Sicherung fehl,
wird nicht überschrieben.

**Noch zu testen:** npm/TypeScript-Build, Cargo fmt/clippy/tests
beider Rust-Projekte, Dateidialoge und Zugriffspfad auf Windows,
macOS, Linux, Wiederherstellung nach Crash, Read-only-Dateien,
Keyring-/Cloud-Konfiguration und Import auf einem zweiten Gerät.

Siehe außerdem [Installation](INSTALLATION.md), [Tests](TESTING.md)
und [Datenschutz](../PRIVACY.md).
