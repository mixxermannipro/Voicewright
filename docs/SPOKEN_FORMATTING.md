# Gesprochene Textformatierung (Issue #34)

Die optionale Formatierung wandelt **ausdrücklich gesprochene Wörter**
in Satzzeichen oder Zeilenumbrüche um. Standardmäßig bleibt die Funktion
**deaktiviert**. Aktiviere sie unter **Einstellungen → Aufnahmeverhalten →
Gesprochene Satzzeichen und Zeilenumbrüche erkennen** und speichere.
Die Einstellung wirkt ab dem nächsten Diktat und gilt gleichermaßen
für lokale und optionale Cloud-Textkorrektur.

Die Umsetzung verwendet eine kleine lokale, deterministische Wortliste.
Es werden **keine Tastaturbefehle, Fenstersteuerungen oder Systemaktionen**
aus einem Diktat ausgeführt.

## Unterstützte Wörter

| Deutsch | Englisch | Geschriebener Text |
| --- | --- | --- |
| `Komma` | `comma` | `,` |
| `Punkt` | `period` oder `full stop` | `.` |
| `Fragezeichen` | `question mark` | `?` |
| `Ausrufezeichen` | `exclamation mark` | `!` |
| `Doppelpunkt` | `colon` | `:` |
| `Semikolon` | `semicolon` | `;` |
| `neue Zeile` | `new line` oder `line break` | Zeilenumbruch |
| `neuer Absatz` | `new paragraph` | Leerzeile zwischen Absätzen |
| `Anführungszeichen auf` | `open quote` | öffnendes `"` |
| `Anführungszeichen zu` | `close quote` | schließendes `"` |
| `Literalmodus an` | `literal mode on` | wörtliche Textpassage beginnt |
| `Literalmodus aus` | `literal mode off` | wörtliche Textpassage endet |

Alle Vergleiche beachten Wortgrenzen und Groß-/Kleinschreibung wird
ignoriert. Ein Begriff wie `Punktland` bleibt erhalten.
Text zwischen bereits erkannten Anführungszeichen (`"…"`,
`„…“`) oder Backticks (``…``) bleibt wörtlich.
Ein gesprochener Öffnungsbefehl schützt die Passage bis zu seinem
gesprochenen Schließbefehl. Mit `Literalmodus an` und
`Literalmodus aus` lassen sich auch unzitierte Passagen schützen.

Beispiel: **„Hallo Komma Welt Ausrufezeichen neuer Absatz München Punkt“**
ergibt `Hallo, Welt!\n\nMünchen.`.

## Bewusste Grenzen

- **Zahlen, Datumsangaben und Währung** werden nicht automatisch
  umgerechnet oder interpretiert, weil das Modell dabei Bedeutungen
  verändern könnte. Bereits erkannte Zahlen bleiben erhalten.
- Nur genau definierte Wörter werden umgewandelt. Unbekannte
  Kommandos wie „alles löschen“ bleiben normaler Text.
- Ungenaue Spracherkennung kann ein Befehlswort versehentlich erkennen
  oder auslassen. Im Zweifel Funktion deaktivieren.
- Sprachliche Zitate ohne tatsächlich erkannte Anführungszeichen
  müssen mit `Literalmodus` geschützt oder wörtlich diktiert werden.
- Die optionale KI-Textkorrektur kann Formatierung anschließend ändern.
  Die lokale Kommandobehandlung findet vor ihr statt.
- Die Funktion sendet selbst nichts ins Internet. Bereits vorhandene
  optionale Cloud-Korrektur überträgt den erkannten, nun formatierten
  Text wie in der Datenschutzerklärung beschrieben.

## Noch ausstehende Abnahme

Die Parser-Unit-Tests decken Deutsch/Englisch, Umlaute, Satzzeichen,
Zeilenumbrüche, Literalpassagen, Quotierung, Dialektwörter und
unveränderte Zahlen/Datumsangaben ab. Ihre Ausführung sowie
Whisper-Sprechtests und die praktische Prüfung in Windows/macOS/Linux
sind für die finale Testphase vorgesehen. **Der Code ist nicht als
bereits erfolgreich getestet zu betrachten.**
