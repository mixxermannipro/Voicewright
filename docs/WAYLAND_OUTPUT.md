# Wayland-Ausgabe / Wayland output

## Stand / Status

**Nativer Unicode-Einfügenachweis bestanden; App-Integration folgt.**
Der Modus `utf8` überträgt über eine ausdrücklich freigegebene EIS-Sitzung
reinen Text. Ein natives GTK-Wayland-Testfeld erhielt den öffentlichen
45-Zeichen-Test inklusive Groß-/Kleinschreibung, Umlauten, ß, Emoji und Absatz
exakt. Die normale App ist damit noch nicht vollständig abgenommen.

**Native Unicode insertion proven; app integration is next.** A native GTK
Wayland field received the exact 45-character public test including case,
umlauts, ß, emoji and a paragraph. This is not full app acceptance.

## Rechte und Verhalten / Permission and behavior

Der Prüfer nutzt den offiziellen XDG-RemoteDesktop-Weg. Er fordert nur
Tastaturzugriff an, ohne Bildschirmaufnahme, Maussteuerung, Root-Rechte oder
Änderungen an Desktop-Einstellungen. Der Nutzer muss den Desktopdialog selbst
bestätigen. Eine Sitzung bleibt nicht über das Programmende hinweg erhalten;
Restore-Tokens werden weder angefordert noch gespeichert.

The probe requests keyboard-only RemoteDesktop access, with no screen capture,
pointer control, root access or desktop configuration changes. The user must
approve the native dialog. No persistent grant or restore token is requested.

`ashpd` 0.14 benötigt zum Kompilieren des RemoteDesktop-Moduls zusätzlich das
Feature `screencast`, weil es dessen `Stream`-Typ importiert. Das aktiviert
keine Bildschirmaufnahme; der Prüfer ruft keine ScreenCast-Methode auf.
`serde_repr` war bereits in der Lockdatei vorhanden; nur die ashpd-Zuordnung
kommt hinzu. Keine Abhängigkeit wurde auf eine andere Version aktualisiert.

## Prüfung / Running the probe

Zunächst nur den Dialog testen, **ohne Texteingabe**:

```sh
cargo run --manifest-path src-tauri/Cargo.toml --locked \
  --example wayland_output_probe -- permission
```

Nach Freigabe prüft der Prozess, dass exakt Tastaturzugriff gewährt wurde,
und schließt die Sitzung. Die Freigabe hat ein Zeitlimit von 60 Sekunden;
bei Zeitüberschreitung, Ablehnung oder Fehler wird kein Text eingegeben.

The permission-only mode sends no keyboard events, verifies the granted device
mask and closes the session. Approval times out after 60 seconds.

Der Modus `keysym` ist ausschließlich für ein bewusst geöffnetes, isoliertes
**natives Wayland-Testfeld** vorgesehen. Er wartet nach Freigabe fünf Sekunden
und sendet diesen festen öffentlichen Testtext an das **dann aktive Feld**:

```text
Grüße aus Köln, ÄÖÜ äöü ß 🙂
```

Keine Steuer-/Sondertasten halten, kein privates oder produktives Feld wählen.
Ein Fensterwechsel ändert das Ziel. Passwortfelder werden nicht erkannt.
Erfolgreiche D-Bus-Aufrufe beweisen nicht, dass der Zieltext exakt angekommen
ist. Das muss im Testfeld gesondert geprüft werden.

The keysym mode waits five seconds after approval, then sends the fixed line
above to the currently focused field. Use only an isolated native Wayland
test field, release modifiers and verify the actual text. It cannot detect
password fields or guarantee the original target. Dispatch is not proof that
the target accepted the complete text.

Der Keysym-Pfad lehnt Steuerzeichen einschließlich Zeilenumbruch ab. Er
simuliert keine Eingabetaste, um versehentliches Absenden zu vermeiden.
Absätze und Zwischenablagenutzung sind noch nicht implementiert bzw.
praktisch geprüft. Der Modus `clipboard` wird deshalb bewusst abgewiesen.

Control characters, including newlines, are rejected rather than simulated
as Enter. Paragraphs and clipboard preservation are not implemented or
verified; the probe deliberately rejects the `clipboard` mode.

### Gewählter Weg: EIS UTF-8 / Selected transport

```sh
cargo run --manifest-path src-tauri/Cargo.toml --locked \
  --example wayland_output_probe -- utf8
```

Nach Keyboard-only-Freigabe verbindet sich dieser Modus über `ConnectToEIS`
mit dem Desktop. `libei` ab 1.6 bindet ausschließlich die Textfähigkeit und
sendet `ei_device_text_utf8`, keine Keycodes/Keysyms, Eingabetasten,
Mausereignisse oder Zwischenablagezugriffe. Dadurch werden Absätze als Text
übertragen und sämtliche Zwischenablageformate bleiben unangetastet.
Die Rückmeldung per EIS-Ping bestätigt den Transport, nicht den Inhalt eines
beliebigen Zielfelds. Ein Abbruch vor Ausgabe sendet keinen Text; nach
begonnener atomarer Ausgabe darf bei unsicherem Ergebnis nicht automatisch
wiederholt werden.

This mode uses the keyboard-approved EIS descriptor and libei 1.6+ TEXT
capability only. UTF-8 paragraphs are text, not Enter keystrokes. Clipboard
contents are never read or changed. Transport acknowledgement is not a
general target-content guarantee. Never automatically retry uncertain output.

Die Bibliothek wird zur Laufzeit geprüft. Ohne die erforderlichen Symbole
bleibt Ausgabe gesperrt; es gibt keinen ungeprüften Tastatur-Fallback.
AppImage muss die geprüfte Bibliothek enthalten; RPM benötigt `libei >= 1.6`.
Es wurde kein neues Systempaket auf dem Nutzerrechner installiert.

Missing libei Unicode symbols cause an explicit failure, not a guessed
keyboard fallback. AppImage must bundle libei; RPM must declare libei >=1.6.

## Nachweise am 11. November 2026 / Evidence

- Fedora 45 KDE Plasma 6.8.2, Wayland; Desktop-Portal 1.22.1,
  KDE-Portal 6.8.2. RemoteDesktop v2 vorhanden.
- Vier Tests zuerst fehlgeschlagen und nach Implementierung bestanden:
  Keyboard-only-Rechte, Unicode-Scalars, Abbruch vor Ausgabe und Ablehnung
  von Steuerzeichen/Absätzen als Tastaturbefehle. Das sind Unit-Tests,
  keine echten Einfügetests.
- Echter Aufruf mit `permission`: Desktopfreigabe nach 60 Sekunden nicht
  bestätigt, kontrollierter Abbruch. Kein Eingabeereignis gesendet.
- Erneute ausdrückliche Freigabe: Keyboard-only-Sitzung erfolgreich geöffnet
  und geschlossen. Keysym-Ausgabe im GTK-Testfeld veränderte Groß-/
  Kleinschreibung und Sonderzeichen; deshalb nicht der V1-Transport.
- EIS-UTF8-Ausgabe: **exakter GTK-Wayland-Vergleich bestanden**, 45 Zeichen
  inklusive Absatz; Prozess-Rückgabewert 0. Kein Zugriff auf Zwischenablage.
- Acht Unit-Tests einschließlich Unicode-Textgrenzen/Abbruch und Schutz des
  isolierten Testziels bestanden (neue Tests jeweils zuerst rot nachgewiesen).
- **Offen:** vollständige App-Ausgabe in native Qt-/GTK-/Browserfelder, gehaltene
  Sondertasten, sichere Absätze, Erhalt aller Zwischenablageformate,
  Widerruf und vollständiger Mikrofon-bis-Einfügen-Test.

The first run timed out without approval; a later explicitly approved run
succeeded. Keysym output failed exact matching. EIS UTF-8 passed the exact
native GTK test with a paragraph. Full application acceptance remains open.

Die CI führt App-Tests mit `--all-targets` aus, damit auch die vier
Example-Tests tatsächlich laufen. Lokal gezielt:

```sh
cargo test --manifest-path src-tauri/Cargo.toml --locked \
  --example wayland_output_probe
```

CI uses `--all-targets` so the example tests run, rather than merely compile.
The final local run included all model tests: 107 app/example tests and
10 cleanup tests passed, with no ignored tests skipped. This is still not
a successful native Wayland insertion test.

## Quellen / Sources

- [RemoteDesktop: Lifecycle, Keyboard, Persistenz](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.RemoteDesktop.html)
- [Clipboard: Freigabe, MIME-Formate und Transfer](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.Clipboard.html)
- [libei: direkte UTF-8-Textübertragung seit 1.6](https://libinput.pages.freedesktop.org/libei/api/group__libei-sender.html)
- [Freigegebener V1-Umfang](superpowers/specs/2026-11-11-v1-fedora-design.md)
- [Implementierungsplan](superpowers/plans/2026-11-11-v1-fedora.md)
