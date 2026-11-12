# Sicherheitslücken melden

Nutze auf GitHub unter **Security → Report a vulnerability** die private
Meldung, sofern sie verfügbar ist. Falls die Schaltfläche fehlt, bitte in einem
Issue ohne technische Details um einen vertraulichen Kontaktweg.

Nenne betroffene Version, Betriebssystem, Auswirkungen und die kleinsten
Schritte zur Wiederholung. Verwende dafür Testdaten. Lass API-Schlüssel,
persönliche Daten, echte Aufnahmen und vertrauliche Diktate aus der Meldung.

## Verantwortungsvolle Meldung

Bitte melde Schwachstellen, die einen unbemerkten Cloud-Datenabfluss,
API-Schlüsselzugriff, eine ungewollte Texteingabe in eine andere App,
manipulierte Modellgewichte oder die Installation nicht vertrauenswürdiger
Programme ermöglichen könnten, **privat**. Eröffne keine öffentlichen
Issues mit Exploit-Details, echten Zugangsdaten oder privaten Beispieldiktaten.
Gib an, ob du den Fehler nur in einer Testumgebung nachgestellt hast.
Für die private Meldung gibt es keine zugesagte Reaktionszeit oder Bug-Bounty.

## Sicherheitsmodell

Voicewright kopiert Diktate in die System-Zwischenablage. Cloud-Korrektur und lokaler Verlauf sind standardmäßig ausgeschaltet. Das Fedora-Paket ist unsigniert. Prüfe vor der Installation die SHA-256-Datei aus dem GitHub-Release.

Die Projektlizenz steht in [LICENSE](LICENSE). Der Umgang mit Nutzerdaten steht in [PRIVACY.md](PRIVACY.md).
