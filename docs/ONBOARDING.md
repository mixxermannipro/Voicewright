# Ersteinrichtung / First-run setup

**Status:** Entwicklungsstand für Issue #22. Die folgenden Schritte werden in
der Anwendung angeboten, ersetzen aber **noch keine erfolgreich
abgeschlossenen Windows-/macOS-/Linux-Release-Tests**.

## Deutsch: Von der Installation zum ersten Diktat

Nach einer frischen Installation erscheint auf der **Übersicht** die
vierstufige Ersteinrichtung. Die App speichert jeden abgeschlossenen Schritt
in den lokalen Einstellungen. Ein Seitenwechsel oder Neustart löscht den
Fortschritt nicht. Unter **Einstellungen → Ersteinrichtung** lässt sich
der Ablauf jederzeit erneut starten. Bereits installierte Modelle und
API-Schlüssel bleiben dabei erhalten.

1. **Datenschutz.** Die Spracherkennung arbeitet mit einem lokalen Modell.
   Die Textkorrektur ist anfangs ausgeschaltet. Ein Cloud-Konto oder
   API-Schlüssel ist nicht erforderlich. Wenn Cloud-Korrektur bereits
   eingeschaltet wurde, zeigt der Assistent die Datenübertragung deutlich
   an; für den Mikrofontest muss sie vorher deaktiviert und gespeichert
   werden. Ein Download erfolgt erst nach einem expliziten Klick.
2. **Sprachmodell.** Empfohlen wird das mehrsprachige **Whisper Base**
   (rund 148 MB Download, rund 2 GiB RAM empfohlen). Der Download erfolgt
   auf ausdrücklichen Klick von Hugging Face; die App prüft die hinterlegte
   SHA-256-Prüfsumme. Die Fortschrittsanzeige bietet Abbrechen.
   Ist das gewählte Modell noch nicht verfügbar, bleibt **Weiter** gesperrt.
   Unter **Modelle** können andere kompatible Modelle ausgewählt werden.
3. **Mikrofon.** Zugriff im Betriebssystem erlauben und mit dem
   Startknopf der App eine kurze Probe aufnehmen. Das Diktat bleibt lokal,
   solange Cloud-Korrektur nicht aktiviert ist. **Weiter** wird erst nach
   einem abgeschlossenen, nicht leeren Erkennungsergebnis freigegeben.
   Falls es nicht funktioniert, unter **Einstellungen** ein anderes Mikrofon
   auswählen oder Rechte und Modell prüfen.
4. **Tastenkürzel / Einfügen.** Das aktive Kürzel ausprobieren, indem ein
   normales Textfeld in einer anderen Anwendung fokussiert wird. Wird
   globale Einfügung nicht unterstützt, in der App aufnehmen und das
   Ergebnis **manuell kopieren**. Die App verlangt eine ausdrückliche
   Bestätigung, dass der Versuch stattgefunden hat oder der manuelle
   Kopierweg bewusst gewählt wurde.

Das erfolgreiche Abschließen des Assistenten bedeutet **nicht**, dass
globale Hotkeys oder automatisches Einfügen auf einem bestimmten
Betriebssystem automatisch erfolgreich getestet wurden. Der letzte
Schritt ist eine **Bestätigung durch den Nutzer**, kein automatischer
Nachweis über andere Anwendungen.

### Systemhinweise

- **Windows:** *Einstellungen → Datenschutz und Sicherheit → Mikrofon*;
  Desktop-App-Zugriff erlauben. Bei belegtem Tastenkürzel unter
  **Einstellungen** eine andere Kombination wählen. In geschützten
  Eingabefeldern und Fenstern mit höheren Rechten kann automatische
  Einfügung scheitern.
- **macOS:** *Systemeinstellungen → Datenschutz & Sicherheit → Mikrofon*.
  Der Stand der nativen globalen Einfügung wird noch entwickelt;
  der Kopierweg bleibt verfügbar.
- **Linux X11:** Audioeingang in der Audioverwaltung prüfen; globale
  Kürzel und Einfügung sind derzeit nur teilweise praktisch erprobt.
- **Linux Wayland:** Aufnahme innerhalb der App und manuelles Kopieren.
  Globale Hotkeys und automatische Texteingabe sind nicht zugesichert.

Das Statusbereichs-/Tray-Symbol wird nur angezeigt, wenn das System es
bereitstellt. Autostart wird durch diese Anleitung **nicht** aktiviert;
die übergreifende Autostart-Unterstützung ist Gegenstand eines anderen
Issues. Das Fenster kann für ein Testdiktat geöffnet bleiben.

### Fehlerbehandlung

| Symptom | Vorgehen |
| --- | --- |
| Modell kann nicht heruntergeladen werden | Netzwerk, freien Speicher und Modell-URL prüfen; Download erneut starten oder kompatible Datei über Modelle importieren |
| Mikrofontest bleibt leer | Betriebssystem-Mikrofonrecht, anderes Eingabegerät und Aufnahmepegel prüfen |
| Kein globales Kürzel | Verfügbarkeit und Konflikte unter Einstellungen prüfen; Aufnahme über App-Fenster |
| Kein Text in der Zielanwendung | Normales nicht geschütztes Textfeld fokussieren, anschließend sonst Ergebnis in Voicewright kopieren |
| Cloud-Anfrage unerwünscht | Unter Textkorrektur **Aus** auswählen und speichern; der Mikrofontest im Assistenten ist bei Cloud-Modus gesperrt |
| Assistent unterbrochen | Übersicht erneut öffnen; zuletzt gespeicherter Schritt bleibt erhalten |
| Gerät gewechselt / Settings importiert | Sicherheitsbedingt beginnt die Ersteinrichtung erneut; Mikrofonkennung und Cloud-Modus werden zurückgesetzt |

Die App führt keine kostenpflichtige Cloud-Anfrage aus, um den Assistenten
zu starten. Jeder echte Modell-Download benötigt jedoch eine
Internetverbindung, sofern die Gewichte nicht bereits lokal vorhanden sind.

## English: First two minutes

On a clean installation, open **Overview** and follow the four steps.
Progress is saved in local preferences after each step; resume later or
restart from **Settings → First-run setup**.

1. **Privacy:** Offline speech recognition by default. Editing is off until
   explicitly enabled. Cloud credentials are not required, and model
   downloads require a deliberate click. If cloud editing is enabled,
   switch it off and save before running the guided microphone test.
2. **Model:** Select or download **Whisper Base** (about 148 MB) or another
   supported speech model. A model must be installed before proceeding.
   Downloads use a pinned source and SHA-256 verification.
3. **Microphone:** Grant OS microphone permission and record a short test.
   The guide advances only after a completed, non-empty transcript.
   Use Settings to change the microphone if nothing is recognized.
4. **Shortcut:** Test the configured shortcut in another application's
   ordinary text field. On platforms without supported global insertion,
   use the app window and **Copy**. Confirm which route you tried.

For microphone permissions, check **Windows Settings → Privacy & security
→ Microphone** or **macOS System Settings → Privacy & Security →
Microphone**. On Linux, choose an input source in the desktop audio
controls. Wayland requires app-based recording and manual copying in
the current implementation.

Finishing the guide is a user acknowledgement, **not an automated
cross-application or multi-platform test**. The tray icon may be absent,
and autostart is not silently activated.

See [Platform support](PLATFORM_SUPPORT.md), [Testing](TESTING.md),
[Settings backups](SETTINGS_BACKUP.md), and [Privacy](../PRIVACY.md).
