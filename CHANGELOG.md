# Änderungen

## Unveröffentlicht

- Produktname, Paketkennungen, Programme und Dokumentation auf **Voicewright**
  vereinheitlicht (Issue #2).
- Hotkey-Zustandsmaschine gegen Burst-, Repeat- und verlorene
  Tastenlöse-Ereignisse gehärtet; Abbruch invalidiert die laufende Sitzung und
  verhindert spätes Einfügen (Issue #7).
- Optionaler Autostart beim Anmelden über das offizielle Tauri-Plugin. Der
  Start bleibt im Statussymbol, solange eines verfügbar ist; ohne Statussymbol
  öffnet sich das Hauptfenster. Das Tray-Menü zeigt Status, Start, Stop,
  Abbruch, Kopieren und den Autostart-Schalter. Beenden bricht eine laufende
  Sitzung ab und beendet den Korrekturprozess (Issue #8).
- Vorhandene Einstellungen und Modelle aus dem alten Datenordner
  `de.voxtakt.desktop` werden beim ersten Start übernommen.
- API-Schlüssel aus dem alten Schlüsselbund-Dienst bleiben lesbar und werden
  beim nächsten Speichern unter dem neuen Dienstnamen abgelegt.
- Alpha-Grundlage aus PR #1 nach `main` integriert.

## 0.1.0-alpha.1

Stand der Umsetzung und Prüfergebnisse stehen in [PROGRESS.md](docs/PROGRESS.md).
