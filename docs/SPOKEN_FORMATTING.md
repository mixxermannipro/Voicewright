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
`„…“`) oder Backticks (z. B. `code`) bleibt wörtlich.
Ein gesprochener Öffnungsbefehl schützt die Passage bis zu seinem
gesprochenen Schließbefehl. Mit `Literalmodus an` und
`Literalmodus aus` lassen sich auch unzitierte Passagen schützen.

Beispiel: **„Hallo Komma Welt Ausrufezeichen neuer Absatz München Punkt“**
ergibt `Hallo, Welt!\n\nMünchen.`.

## Verhalten an Wortgrenzen

- Das Leerzeichen vor einem Befehlswort gehört zum Befehl und wird mit
  umgewandelt: „Text punkt“ ergibt „Text.“ (das Zeichen klebt an dem
  vorherigen Wort).
- Nach `neue Zeile` und `neuer Absatz` werden weitere Leerzeichen
  übersprungen, damit keine doppelten Leerzeichen entstehen:
  „Text neue Zeile   Fortsetzung“ ergibt `Text\nFortsetzung`. Zwei
  aufeinander folgende Zeilenbefehle ergeben eine Leerzeile:
  „Text neue Zeile neue Zeile Ende“ ergibt `Text\n\nEnde`.
- Die Erkennung ignoriert bewusst Groß-/Kleinschreibung, weil die
  Spracherkennung gemischte Schreibweisen liefert. Deshalb werden auch
  satzanfängliche Befehlswörter umgewandelt: „Punkt gesagt, Punkt
  getan“ ergibt „. gesagt,. getan“. Wer das vermeiden will, diktiert die
  Passage im Literalmodus oder deaktiviert die Funktion.

## Bewusste Grenzen

- **Zahlen, Datumsangaben und Währung** bleiben exakt so, wie sie von
  der Spracherkennung erkannt wurden (1:1). Der Parser rechnet sie weder
  in andere Schreibweisen um noch normalisiert er Daten, weil
  gesprochene Zahlen mehrdeutig sind (z. B. „49,90“ versus „49.90“
  oder „12.04.2026“ versus „12. April 2026“); eine automatische
  Umdeutung könnte Bedeutungen verändern.
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

## Abnahme-Status

Am 8. November 2026 auf Linux x64 ausgeführt und bestanden:

- 22 Parser-Tests: die 6 bestehenden Unit-Tests in
  `src-tauri/src/spoken_format.rs` plus 16 neue Golden-Tests in
  `src-tauri/tests/spoken_format_golden.rs` für Satzzeichen (DE/EN),
  Zeilen und Absätze, Zahlen, Daten, Umlaute und ß, Dialekt,
  Wiederholungen, Wortgrenzen, Eigennamen, Zitate, Code und
  Literalmodus. Der Aus-Zustand liefert den Originaltext byte-identisch,
  und kein Diktatwort löst eine OS-Aktion aus.
- Der Whisper-Sprechtest (`src-tauri/tests/speech.rs`) erkannte die
  künstlichen DE/EN-Testaufnahmen mit einem lokal geprüften
  Whisper-Base-Modell (SHA-256).
- Der Cleanup-Protokolltest (`engines/cleanup/tests/protocol.rs`) lief
  mit einem lokal geprüften Qwen3-0.6B-Q8_0-Modell.

Die praktische Abnahme mit physischem Mikrofon, veröffentlichten
Installationspaketen und Windows/macOS steht laut
[Testanleitung](TESTING.md) weiterhin aus.
