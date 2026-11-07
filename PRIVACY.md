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
