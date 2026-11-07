# Datenschutz

Voicewright benötigt kein Konto. Es sind keine Analyse- oder Werbedienste
vorgesehen. Mikrofonaufnahmen dienen der lokalen Spracherkennung. Der
optionale Korrekturprozess auf dem eigenen Rechner verarbeitet den erkannten
Text ebenfalls lokal.

## Netzwerk

- Ein Modelldownload verbindet sich mit dem in der Modellübersicht genannten
  Downloadserver. Der Server kann die üblichen Verbindungsdaten sehen.
- Eine bewusst aktivierte externe Textkorrektur sendet den erkannten Text,
  die Bearbeitungsanweisung, die Modellkennung und gegebenenfalls den
  API-Schlüssel zur Anmeldung an den gewählten Dienst. Der Dienst verarbeitet
  den Text nach seinen eigenen Bedingungen.
- Ein Abruf der Modellliste oder ein Verbindungstest kann den gewählten Dienst
  kontaktieren. Die jeweilige Aktion soll mit Testdaten durchgeführt werden.
- Eine lokale Adresse für Ollama oder LM Studio verbindet Voicewright mit einem
  separaten Programm. Dessen Einstellungen bestimmen seine weiteren Verbindungen.

## Speicherung

Einstellungen und geladene Modelle liegen in den Anwendungsdaten des
angemeldeten Betriebssystemkontos. API-Schlüssel gehören in dessen
Zugangsdaten-Speicher. Ein über die Oberfläche kopierter Text landet in der
System-Zwischenablage. Je nach Betriebssystem können Zwischenablage-Verlauf
und geräteübergreifende Synchronisierung den kopierten Text übernehmen.

## Exportierte Einstellungen

Mit der optionalen Funktion „Gespeicherte Einstellungen exportieren“
erzeugt die App eine lokale JSON-Datei mit Einstellungen, persönlichen
Vorlagen und Wörtern, Modellreferenzen und konfigurierten
Provider-Adressen. Diese Datei enthält keine API-Schlüssel aus dem
OS-Passwortspeicher, keine Audiodateien und keine Diktattexte.
Eigene Wörterlisten oder Prompts können trotzdem private Inhalte haben.
Der Import zeigt eine Vorschau und deaktiviert die Cloud-Korrektur,
bis sie ausdrücklich wieder eingeschaltet wird. Siehe
[Einstellungs-Backup](docs/SETTINGS_BACKUP.md).

## Wichtige Grenzen und Benutzerkontrolle

- **Lokale Diktate:** Für reine Audioerkennung und lokale Textkorrektur ist
  kein Cloud-Korrekturanbieter nötig. Der bewusste Modelldownload benötigt
  allerdings Internet, sofern Modelle nicht importiert werden.
- **Cloud-Opt-in:** Bei aktivierter externer Textkorrektur gelangen Transkript
  und Bearbeitungsanweisung (einschließlich eventueller Wörterlisten und
  Übersetzungsziele) an den gewählten Anbieter. Dort können Speicherung,
  Verarbeitung, Abrechnung und eigene Datenschutzbedingungen gelten.
  Keine privaten Inhalte zu Testzwecken in externe Provider senden.
- **Einstellungen und Ergebnisse:** Die App speichert Modelle und Konfiguration
  im Benutzerprofil, jedoch keinen dauerhaften Diktatverlauf. Das letzte
  Ergebnis bleibt während der App-Sitzung abrufbar, bis es gelöscht oder
  ersetzt wird. „Letztes Ergebnis leeren“ ist **keine** Löschung aus der
  Zwischenablage, fremden Textfeldern oder dem Verlauf anderer Programme.
- **Eigene Server:** Ein selbst eingetragener kompatibler Endpoint ist eine
  Vertrauensentscheidung. Auch HTTPS garantiert nicht, dass der Betreiber
  vertrauenswürdig ist. Lokale LLM-Server können unabhängig von Voicewright
  weitere Netzwerkanfragen ausführen.
- **API-Schlüssel:** Voicewright legt Schlüssel im OS-Zugangsdaten-Speicher
  statt in den normalen JSON-Einstellungen ab. Das löscht weder mögliche
  Protokolle beim Provider noch Kopien im OS-Backup.
- **Kein Sicherheitsversprechen:** Details über Grenzen, bekannte Risiken
  und noch ungetestete Szenarien beschreibt das
  [Bedrohungsmodell](docs/THREAT_MODEL.md). Eine Releasefreigabe folgt daraus
  nicht automatisch.
