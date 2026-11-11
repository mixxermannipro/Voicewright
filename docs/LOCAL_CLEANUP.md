# Lokale Textkorrektur / Local editing

## Deutsch

Die Korrektur ist optional und standardmäßig **aus**. **Minimal** ist der
Standardstil. **Natürlich** und **Formal** ergänzen Stilhinweise; eine eigene
Anweisung bleibt editierbar. Stilhinweise sind keine Qualitätsgarantie.
Die Vorschau berücksichtigt auch noch nicht gespeicherte Einstellungen.

Bei abgewiesenen Ausgaben oder Prozessfehlern verwendet die App mit aktiviertem
Fallback den Originaltext und zeigt eine Warnung. Ohne Fallback bleibt das
Original zum Kopieren verfügbar und wird nicht automatisch eingefügt.
Die Vorschau meldet Fehler statt einen erfolgreichen Modelltext vorzutäuschen.
Minimal mit Standardanweisung erhält die Wörter und ihre Reihenfolge, erlaubt
aber Großschreibung, Interpunktion, definierte Fülllaute und direkte Dopplungen.
Allgemeine Rechtschreib- oder Grammatikänderungen können deshalb am Schutz
scheitern und das Original behalten. Natürlich/Formal, Übersetzung und eigene
Anweisungen lockern sprachabhängige Prüfungen;
Zahlen, technische Kennungen, URLs und Code bleiben geschützt.
Die Prüfungen beweisen keine vollständige Bedeutungsgleichheit. Prüfe wichtige
Diktate vor der Verwendung, besonders medizinische oder rechtliche Inhalte.

### Grenzen und Ablauf

- Eine lokale Qwen3-GGUF-Datei, höchstens 2 GiB; keine Dateiauswahl aus Diktattext.
- Eigener Prozess ohne Shell und ohne lokalen HTTP-Server. Nach Installation
  der Gewichte ist kein Konto oder Netzwerk nötig.
- Qwen3-Chatrollen mit deaktiviertem Thinking, getrennte Systemanweisung und
  Diktatdaten, deterministische Greedy-Auswahl statt Zufalls-Sampling.
- 4.096 Kontexttokens, höchstens 1.536 Ausgabetokens und 12 KiB Ausgabe;
  zu lange Eingaben werden abgewiesen, nicht still abgeschnitten.
- Anweisung höchstens 32 KiB, Diktat höchstens 128 KiB, gesamte JSON-Anfrage
  höchstens 256 KiB, Prozessantwort höchstens 128 KiB.
- 180 Sekunden Generierungsbudget, 240 Sekunden für den gesamten Prozess.
- Überwachung des belegten Prozessspeichers alle 250 ms: Modellgröße plus
  3 GiB, begrenzt auf 3–8 GiB. Dies ist **kein hartes Betriebssystemlimit**:
  kurzzeitige Spitzen und ein früherer OOM-Abbruch bleiben möglich.
- Abbruch, Zeitüberschreitung, Speicherüberschreitung, ungültige Antwort und
  fehlerhafter Exit beenden den Prozess kontrolliert; der Elternprozess
  wartet das Ende ab. Es werden keine Diktate dauerhaft gespeichert.

Ein kleines Modell wird nicht allein wegen schneller Laufzeit empfohlen.
Vergleiche es mit **Korrektur aus**; unnötige Änderungen können schlechter
als das unveränderte Transkript sein. Ergebnisse und Grenzen stehen im
[Prüfprotokoll](LOCAL_CLEANUP_EVALUATION.md).

## English

Editing is optional and **off by default**. **Minimal** is the default style;
**Natural** and **Formal** add style guidance, not a quality guarantee.
Custom instructions remain editable. Preview uses unsaved settings too.

Rejected output and engine failures retain the original with a warning when
fallback is enabled. Without fallback, the original remains available to copy
and is not inserted automatically. Preview reports errors explicitly.
Minimal with the default prompt preserves words and order, allowing case,
punctuation, defined fillers and adjacent stutters. General spelling or grammar
changes may therefore fall back to the original. Natural/Formal, translation
and custom instructions relax language-specific checks, but numbers,
technical identifiers, URLs and code remain protected. Validation cannot prove
semantic equivalence. Review important dictation before use.

Local editing uses a separate process, no shell, no local server and no account
or network after downloading the weights. Only single-file Qwen3 GGUF models
up to 2 GiB are supported. Qwen3 roles separate instructions from dictation;
thinking is disabled and decoding is greedy, not random. The context is 4,096
tokens; output is capped at 1,536 tokens / 12 KiB. Oversized inputs fail instead
of being silently truncated. Instructions/transcripts are capped at 32/128 KiB;
the JSON request/response limits are 256/128 KiB. Generation/process timeouts
are 180/240 seconds. RSS is checked every 250 ms against model size plus 3 GiB
(3–8 GiB range). This is **not a hard OS memory limit**; spikes and earlier
OOM termination are possible. Cancellation and failures terminate and reap the
child process. Dictation is not persisted.

Compare small models against editing disabled; fast execution alone is not a
recommendation. See the [evaluation record](LOCAL_CLEANUP_EVALUATION.md) for
actual results, negative examples and untested platforms.
