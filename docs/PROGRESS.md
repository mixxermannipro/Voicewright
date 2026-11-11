# Arbeitsstand und Übergabe

## V1 für Fedora – Planung am 11. November 2026

`main` wurde auf `a62cd84` aktualisiert; die neue Aufgabe läuft auf
`feat/v1-fedora-release`. Der Anwender fordert automatisches Einfügen auch
unter Fedora Wayland ausdrücklich als Pflichtfunktion. Der
[V1-Entwurf](superpowers/specs/2026-11-11-v1-fedora-design.md) ist vom Anwender
freigegeben; der [Implementierungsplan](superpowers/plans/2026-11-11-v1-fedora.md)
ist ebenfalls bestätigt und wird ohne weitere Umfangsfragen umgesetzt.
Ein isolierter Wayland-Prüfer ist implementiert, aber noch kein
V1-Ausgabebackend in die App integriert und kein Release erstellt.
Issues werden erst nach der Umsetzung abgeglichen, nicht zur
Arbeitsauswahl verwendet. Die vorhandene unversionierte
`.github/workflows/platforms.yml` bleibt unangetastet.

**Ausgangsstand lokal geprüft:** `npm run check`, `npm run lint`, `npm test`
(12 Tests), `npm run build` und `npm audit --audit-level=high` (0 Treffer)
bestanden. Beide Cargo-Projekte bestanden Formatierung und Clippy mit
`--all-targets -- -D warnings`; App/Parser: 96 Tests bestanden, zwei
Modelltests übersprungen; Cleanup/Protokoll: 9 bestanden, ein Modelltest
übersprungen. 7 Python-Paketprüfertests und die 6 gezielt erneut ausgeführten
Vitest-Paketvertragstests bestanden. Ein vorheriger Aufruf der Vitest-Datei
mit dem Node-Testläufer war ein falscher Prüfaufruf, kein Produktfehler.

**Umgebung:** Fedora 45 KDE Plasma 6.8.2, Wayland. Das lokale Desktop-Portal
meldet RemoteDesktop v2, Clipboard v1 und GlobalShortcuts v2. Nur die
Schnittstellen wurden ausgelesen; keine neue Berechtigung erteilt und kein
automatisches Einfügen nachgewiesen. GitHub-CI-Lauf
[43030588241](https://github.com/mixxermannipro/Voicewright/actions/runs/43030588241)
ist für `a62cd84` erfolgreich. Das ist keine praktische V1-/Fedora-Abnahme.

**Bestätigte Produktentscheidungen:** Ausgabe unter Wayland ins aktuell aktive
Feld; erneute Freigabe beim App-Start ist akzeptiert. Die beiden kostenlosen
Katalogmodelle dürfen außerhalb Git heruntergeladen und geprüft werden.
RPM/AppImage, Fünf-Bereiche-Oberfläche und die Abnahmebedingungen sind
freigegeben. Drei DeepSeek-Helferprüfungen wurden geliefert; zwei weitere
Wayland-Recherchen scheiterten am kostenlosen Nutzungslimit. Diese Prüfung
übernimmt der Haupt-Agent ohne bezahltes Ersatzmodell.

**Echte Modelltests dieses Ausgangsstands:** Beide Kataloggewichte wurden
nach ausdrücklicher Zustimmung außerhalb Git geladen; Dateigröße und SHA-256
stimmen. Der Whisper-Test mit synthetischen DE/EN-WAVs (7,87 s), der
Qwen-DE/EN-Protokolltest (8,10 s) und der 19-Fälle-Guard-Vergleich (24,81 s)
bestanden. Keine echte Mikrofon-/Wayland-Ausgabeabnahme und kein Nachweis
eines allgemeinen Korrekturvorteils daraus ableiten.

**Wayland-Vorprüfung:** `src-tauri/examples/wayland_output_probe.rs` fordert
explizit nur Keyboard-Portalrechte an und kann einen festen öffentlichen
Einzeiler ausgeben. Vier Unit-Tests wurden erst rot, dann grün nachgewiesen.
Die echte Prüfung im Modus `permission` endete nach 60 Sekunden ohne
bestätigte Desktopfreigabe. Es wurde kein Text eingegeben; der Prüfer beendet
die Sitzung. Einzelheiten und ausstehende Tests: [WAYLAND_OUTPUT.md](WAYLAND_OUTPUT.md).
Dieser ursprüngliche Blocker wurde nach erneuter Freigabe überwunden:
Keyboard-only-Sitzung geöffnet/geschlossen; direkte EIS-UTF8-Ausgabe in ein
natives GTK-Wayland-Testfeld kam exakt an (45 Zeichen, inklusive Umlaute,
ß, Emoji, Absatz und korrekter Groß-/Kleinschreibung). Der Keysym-Versuch
bestand den exakten Vergleich nicht und wird nicht der V1-Transport.
Der gewählte Weg benötigt `libei >= 1.6`, fordert nur Textfähigkeit an und
fasst die Zwischenablage nicht an. Acht Prüfer-/Texttests bestanden.
Die App-Integration verwendet nun denselben EIS-Textkanal mit gesonderter
Einwilligung (Standard aus), begrenzter Warteschlange, Abbruchflag und
Sitzungsgeneration. Veraltete Freigaben dürfen Ausgabe nicht wieder aktivieren;
Imports übernehmen keine Einwilligung. Pending/Ready/Denied/Error werden
an die Oberfläche gemeldet. Mikrofontests geben niemals extern aus.
Die vollständige Paket-/Desktopabnahme ist noch offen;
kein Copy-only-Release und keine Issue-Schließung aus der Vorprüfung ableiten.

**Abschlussprüfung des Zwischenstands:** 107 App-/Beispieltests und 10
Cleanup-Tests mit `--all-targets -- --include-ignored` einschließlich echter
Gewichte bestanden, ohne übersprungene Tests. Beide fmt-/Clippy-Prüfungen,
12 npm-Tests, Typprüfung, Lint, Web-Build, npm-Audit (0 Treffer) und 7
Python-Paketprüfertests bestanden. CI und gesicherte CI-Vorlage verwenden
für die App jetzt `--all-targets`, da der vorherige Aufruf die vier neuen
Example-Tests nicht ausführte. Eine unabhängige Codeprüfung war wegen des
DeepSeek-Gratislimits nicht verfügbar; nur Selbstprüfung, keine unabhängige
Merge-Freigabe. Der anschließende GitHub-Lauf scheiterte vor dem Codebau an
Timeouts beim Azure-Ubuntu-Paketserver; das ist kein nachgewiesener Rustfehler.

Der Alpha-Stand aus [PR #1](https://github.com/mixxermannipro/Voicewright/pull/1)
wurde am 7. November 2026 nach `main` integriert. Der Zweig
`feat/dictation-foundation` ist damit abgeschlossen. Die nächsten Aufgaben
laufen über eigene Zweige und Pull Requests gegen `main`.

Produktname und Repository heißen jetzt **Voicewright**. Die Anwendung
übernimmt vorhandene Einstellungen und Modelle aus dem alten Datenordner
`de.voxtakt.desktop` beim ersten Start. Bereits gespeicherte API-Schlüssel
werden weiterhin gelesen; beim nächsten Speichern werden sie unter dem neuen
Dienstnamen abgelegt. Für diese Version gibt es noch kein veröffentlichtes
Installationspaket.

## Linux: X11-Härtung und Wayland-Portale (Issue #6)

Die Linux-Anbindung trennt globale Tasten und Texteingabe jetzt sauber:

- **X11:** Das Zielfenster wird über Fokus-Fenster, aktives Fenster,
  Prozesskennung, Sichtbarkeit und gehaltene Sondertasten geprüft. Die
  Prüfung läuft vor dem Tippen und vor jedem Graphem-Block. Mehrzeilige
  Ergebnisse werden mit der Eingabetaste eingefügt; CRLF/CR wird zu LF.
  Steuerzeichen außer Zeilenumbruch, leerer Text und mehr als 400 Zeichen
  bleiben beim Kopieren. Emoji, Flaggen, Familien-Emoji und kombinierte
  Zeichen werden nicht zerteilt.
- **Wayland:** Globale Tasten laufen über das XDG-Desktop-Portal
  `GlobalShortcuts`, wenn es vorhanden ist und der Nutzer die Freigabe
  erteilt. Die Oberfläche zeigt `pending`, `active`, `denied`,
  `unavailable` oder `error` und bietet bei Ablehnung eine erneute Anfrage.
  Automatisches Einfügen bleibt bewusst aus; der Text bleibt in der App
  und wird nur auf ausdrücklichen Klick kopiert.
- **Keine Umgehungen:** kein Root, `uinput`, `sudo`, Keylogging oder
  pauschales `Input`-/`RemoteDesktop`-Portal. Die Zwischenablage wird
  nicht im Hintergrund verändert.

**Geprüft am 10. November 2026 (Linux x64, dieser Branch):**

- `npm run check`, `npm run lint`, `npm test` (6 Tests) und
  `npm run build` bestanden.
- `cargo fmt --check`, `cargo clippy --locked --all-targets -- -D warnings`
  und `cargo test --locked` bestanden: 56 Unit-Tests plus 22 Golden-Tests,
  darunter neue Tests für Sitzungserkennung, Graphem-Chunking, Steuerzeichen,
  Portal-Trigger und Portal-Zustände.
- Der echte X11-Einfügetest mit Xvfb und einem GTK-TextView bestand:
  deutscher Text mit Umlauten, ß, Emoji, Flagge, Familien-Emoji,
  Gedankenstrich und zwei Absätzen kam exakt an
  (`scripts/linux-smoke/x11-insertion.sh`).
- Auf der KDE-Plasma-Wayland-Sitzung dieser Umgebung meldet das Portal
  Version 2. Sitzung anlegen und schließen über `ashpd` bestanden. Der
  Freigabedialog und eine echte Tastenbindung wurden nicht automatisiert.

**Noch offen:** echte Freigabe und Tastenbindung auf GNOME Wayland, KDE
Plasma Wayland und wlroots, Qt und Browser unter X11, XWayland sowie ein
vollständiger DEB-Durchlauf mit diesem Branch. Die Ergebnisse stehen in
[PLATFORM_SUPPORT.md](PLATFORM_SUPPORT.md); die manuellen Schritte in
[TESTING.md](TESTING.md).

## Linux-Paketierung (Issue #32, 11. November 2026)

Der Paketbau bleibt bei Tauri und läuft als zusätzlicher Pflicht-Check bereits
für PRs auf Ubuntu 22.04. AppImage (für Fedora priorisiert) und DEB enthalten
AppStream-Metadaten, Desktop-Eintrag, Icons, Cleanup-Sidecar und Lizenzhinweise.
Der Prüfer kontrolliert Layout, Dateirechte, dynamische Bibliotheken und
GLIBC ≤ 2.35 für enthaltene ELF-Dateien. SHA-256 und Prüfbericht liegen beim
Actions-Artefakt. Der Releaseablauf übernimmt dieselben geprüften Linux-Pakete.
GGML baut ohne native/AVX-Anforderungen; der Sidecar-Paketcache ist von alten
AVX-Builds getrennt. Der X11-Smoke unterstützt nun auch AppImage.

**Lokal nachgewiesen:** npm-Typprüfung, Lint, 12 Tests, Webbuild und Audit (0
Schwachstellen); beide Rust-fmt-/Clippy-Prüfungen, 78 App-/Parser-Tests und
6 Engine-/Protokolltests; je ein echter Modelltest blieb ohne Gewichte
übersprungen. 7 Python-Paketprüfertests, AppStream und actionlint bestanden. Release-DEB
und AppImage wurden auf Fedora 45 gebaut. Das Fedora-AppImage benötigt GLIBC
2.44; der Prüfer hat die portable Grenze korrekt abgewiesen. Mit expliziter
lokaler Grenze 2.44 bestanden Layout, Laufzeiten und 202 ELF-Prüfungen.
Dies ist **kein** Distributionsnachweis für Ubuntu/Debian. Endgültige Ergebnisse
und Prüfsummen werden im [Linux-Protokoll](LINUX_RELEASE_TESTS.md) ergänzt.

**GitHub-Nachweis:** Lauf `43026604832` für Stand `b8245f1` hat alle
Pflichtchecks bestanden, einschließlich Release-DEB/AppImage auf Ubuntu
22.04 mit GLIBC ≤ 2.35 (2 bzw. 180 ELF-Dateien). Prüfsummen und Link stehen
im Linux-Protokoll. Nach Integration von #73 werden die Checks erneut ausgeführt.

**Nach Integration von #73 lokal erneut geprüft:** 12 npm- und 7 Python-Tests,
96 App-/Parser-Tests (10 vollständige Durchläufe) und 9 Engine-/Protokolltests;
fmt/Clippy für beide Cargo-Projekte bestanden. Zwei App-Modelltests und ein
Engine-Modelltest blieben ohne Gewichte übersprungen. Dabei wurde zunächst
ein sporadischer Linux-Startfehler `ETXTBSY` reproduziert. Ausschließlich
dieser Fehler erhält jetzt bis zu fünf Wiederholungen mit jeweils 10 ms;
Abbruch und dauerhafte Fehler bleiben kontrolliert. Ein echter Schreibhandle
reproduziert im neuen Test sowohl vorübergehend als auch dauerhaft belegte
Programmdateien. Der Test war vor der Korrektur rot, danach grün.

**Offen:** reale Installation/Updates auf fremden Distributionen, physisches
Mikrofon, GNOME/KDE-/Wayland-Abnahme und vollständige Lizenzprüfung aller
gebündelten Systembibliotheken. Kein bit-identisches Buildversprechen.
Die separate Cleanup-Arbeit für #16 ist inzwischen über PR #73 integriert;
ihre Ergebnisse und Grenzen stehen im folgenden Abschnitt.

## Lokale Korrektur und Fallbacks (Issue #16, 11. November 2026)

Die vorhandene Vorarbeit wurde gesichert und mit aktuellem `main` verbunden.
Lokale Qwen3-Korrektur verwendet Greedy-Decoding, explizite Eingabe-/Ausgabe-
und Zeitgrenzen sowie eine weiche RSS-Speicherüberwachung. Prozessfehler,
Abbruch und Zeitüberschreitung erhalten kontrollierte Fehler; der eigene
Kindprozess wird beendet und abgeholt. Alte Einstellungen bekommen den Stil
Minimal. Natürlich/Formal sind opt-in, eigene Anweisungen bleiben editierbar.

Der Standardmodus schützt Wörter und Reihenfolge, Negationen, Namen, Zahlen,
Datumsangaben, URLs, Code und Kennungen. Neue Fakten werden ebenso geprüft
wie entfernte; Zahlen/Kennungen müssen ohne Übersetzung in Reihenfolge bleiben.
Das ist bewusst konservativ: Allgemeine Rechtschreib-/Grammatikänderungen
können auf das Original zurückfallen. Eigene Prompts, Stilmodi und Übersetzung
haben schwächere Wortprüfungen, aber weiterhin harte Fakten-/Codeprüfungen.
Es gibt keine vollständige semantische Garantie.

**Geprüft:** npm Typecheck/Lint, 6 Vitest-Tests, Produktionsbuild und Audit
(0 Schwachstellen); Cargo fmt/Clippy für beide Projekte; 73 App-Unit-Tests
plus 22 Golden-Tests, 9 Engine-/Protokolltests. Zusätzlich echter Qwen3-
Protokolltest, 19-Fälle-Modellvergleich (13 akzeptiert, 6 sicher verworfen)
und echte Whisper-Base-Erkennung mit synthetischen DE/EN-Stimmen bestanden.
Die zuvor reproduzierten Schutzlücken haben Regressionstests.

**Einordnung:** Der Kleinmodell-Vergleich belegt keinen Netto-Nutzen gegenüber
Korrektur aus. Kein pauschales Empfehlungsversprechen; Korrektur bleibt
standardmäßig aus. Menschlich gesprochene E2E-Diktate, echter OOM,
Windows/macOS und der harte netzlose Containerlauf sind nicht abgenommen.
Die Schließung von #16 erfolgt auf ausdrücklichen Wunsch mit diesen
offengelegten Grenzen; eine plattformweite Release-Freigabe folgt daraus nicht.
Bedienung: [LOCAL_CLEANUP.md](LOCAL_CLEANUP.md).
Prüffälle und Ergebnisse: [LOCAL_CLEANUP_EVALUATION.md](LOCAL_CLEANUP_EVALUATION.md).

## Prompt-Härtung – Implementierung in Issue #17

Auf einem separaten Feature-Branch liegt eine erweiterte Standardanweisung,
ein opt-in-Vorschautest mit noch nicht gespeicherten Einstellungen und eine
konservative Ausgabevalidierung. Beim normalen Diktat greift bei abgewiesenen
KI-Ausgaben der vorhandene Original-Fallback (sofern aktiviert). Für
Cloud-Vorschauen ist ein ausdrücklicher Klick mit Bestätigung erforderlich;
dabei werden Testtext und Anweisung an den gewählten Anbieter gesendet,
keine Mikrofonaufnahme.

**Noch ausstehend:** vollständige npm-/Cargo-Prüfungen und echte
Modell-Evaluation in Windows/macOS/Linux. Die Golden-Fälle in
[TESTING.md](TESTING.md) sind eine manuelle Checkliste, kein bereits
bestandener Qualitätsnachweis. Der Validator erkennt keine subtilen
Bedeutungsänderungen oder Halluzinationen.

## Sichere Einstellungsverwaltung (Issue #26)

Ein neuer Branch ergänzt Schema-Versionierung, Migration alter Alpha-Settings,
atomare Datenspeicherung mit Backup unlesbarer Konfiguration, lokalen
JSON-Export ohne API-Schlüssel, Import mit Vorschau, Zurücksetzen als
Entwurf und sicheres Abschalten des Cloud-Modus bei Import.
Die [Anleitung](SETTINGS_BACKUP.md) beschreibt die Datenarten,
Rollback-Möglichkeit und bewusst nicht implementierte vollständige
Löschung persönlicher Modell-/Keyringdaten.

**Teststatus:** Rust/npm, Dateidialoge und reale Plattform-Tests sind
vereinbarungsgemäß für die spätere Abnahme ausstehend. Ein gemergter
Code-PR bedeutet noch keine bestätigte Funktionsfähigkeit. Issue #26
bleibt für vollständige Löschroutine und Tests offen.

## Gesprochene Textformatierung (Issue #34)

Ein isolierter, opt-in-Parser wandelt definierte deutsche und englische
Satzzeichenwörter sowie Zeilen- und Absatzbefehle in reine Textformatierung
um. Im Auslieferungszustand bleibt die Funktion aus. Zitierter Text,
Backtick-Code und explizite Literalpassagen werden geschützt.
Gesprochene Befehle lösen **keine** OS-Aktionen aus.
Die Verarbeitung findet nach Whisper und vor optionaler KI-Korrektur
auf dem aktiven Sitzungs-Snapshot statt. Die
[Benutzeranleitung](SPOKEN_FORMATTING.md) dokumentiert Vokabular
und Grenzen. Zahlen/Datum werden nicht umgerechnet.

**Teststatus:** Am 8. November 2026 ausgeführt und bestanden: 22
Parser-Tests (6 bestehende Unit-Tests plus 16 neue Golden-Tests für
Satzzeichen DE/EN, Zeilen und Absätze, Zahlen, Daten, Umlaute und ß,
Dialekt, Wiederholungen, Wortgrenzen, Eigennamen, Zitate, Code,
Literalmodus, byte-identischer Aus-Zustand und keine OS-Aktionen) sowie
beide Pipeline-Tests mit echten, lokal geprüften Gewichten
(Whisper-Base-Sprechtest, Cleanup-Protokolltest mit Qwen3-0.6B-Q8_0).
Issue #34 ist mit dieser Abnahme abgeschlossen. Ausstehend bleiben die
praktische Plattformabnahme mit physischem Mikrofon und veröffentlichten
Paketen sowie fortgeschrittene Zahlen-/Datumsformatierung.

## Ersteinrichtung (Issue #22)

Ein neuer, optional erneut aufrufbarer vierstufiger Assistent integriert
den vorhandenen Modell-Download, die Mikrofonaufnahme und die
Tastenkürzel-/Kopierwege. Jeder Schritt wird im lokalen
`Settings`-Objekt gespeichert. Der Fortschritt lässt sich nach
Neustart fortsetzen; nach Abschluss ist die Führung ausgeblendet.
Alte Settings bleiben kompatibel und auf einem neuen Gerät importierte
Settings setzen die Ersteinrichtung zurück.

Die Funktion **startet weder automatisch Downloads noch
Cloud-Requests**. Der angeleitete Mikrofontest ist bei aktivierter
Cloud-Korrektur gesperrt. Deutsche und englische Hinweise zu
Berechtigungen, Tray und fehlender globaler Einfügung stehen in
[ONBOARDING.md](ONBOARDING.md).

**Teststatus:** UI-/Rust-Tests sind erstellt, aber nicht ausgeführt;
reale Windows/macOS/Linux-Installationen, echte Mikrofonrechte,
Downloads, globales Einfügen und Screenreader bleiben zu prüfen.
Issue #22 bleibt bis zur plattformspezifischen Abnahme offen.

## Was vorhanden ist

- Deutsch-englische Tauri-Oberfläche mit Übersicht, Kurzanleitung, Mikrofonwahl, konfigurierbarem Tastenkürzel, Halten und Umschalten, Aufnahmepegel, Abbruch, Statussymbol und Kopiermöglichkeit. Einstellungen bleiben nach Neustart erhalten. Die App speichert keinen Diktatverlauf.
- Lokale Whisper-Erkennung auf der CPU. Der Katalog enthält die mehrsprachigen Modelle Tiny, Base, Small, Medium, Large-v3 und Large-v3 Turbo. Downloads verwenden feste Modellversionen, Größen und SHA-256-Prüfsummen. Es gibt Abbruch, Fortsetzen, Löschen und Import. Beim Import prüft die App Formatkennung, GGUF-Version und Grundstruktur; vertauschte Formate sowie beschädigte oder unvollständige Dateien werden abgelehnt. Nur Whisper Base ist praktisch getestet.
- Lokale Textkorrektur mit mitgeliefertem llama.cpp-Programm und Qwen3-0.6B-Q8_0. Eigene dichte Qwen3-GGUF-Modelle können importiert werden. Anweisungen, Vorlagen, Wörterliste und Ziel für Übersetzung sind einstellbar. Bei Fehlern bleibt der Originaltext verfügbar.
- Optionale Cloud-Korrektur mit OpenAI, Gemini, Anthropic, xAI, OpenRouter, Mistral, Groq, DeepSeek, Together AI, Fireworks, Cerebras und eigenen kompatiblen Servern. Die App sendet Text nur im aktivierten Cloud-Modus. Schlüssel werden im Passwortspeicher des Betriebssystems abgelegt.
- Direkte Texteingabe unter Windows und X11 mit Prüfung des Zielfensters. Bei abweichendem Fokus, gehaltenen Sondertasten, Steuerzeichen außer Zeilenumbruch oder mehr als 400 Zeichen bleibt der Text zum Kopieren in der App. Mehrzeilige Texte werden unter X11 mit der Eingabetaste eingefügt; Emoji und kombinierte Zeichen werden nicht zerteilt. macOS nutzt Kopieren. Unter Wayland laufen globale Tasten über das XDG-GlobalShortcuts-Portal, sofern der Desktop es anbietet und der Nutzer zustimmt; automatisches Einfügen bleibt dort aus, der Text ist über die App kopierbar.
- Vollständige [Vorlagen für die GitHub-Automatisierung](github-workflows/README.md). GitHub hat das Schreiben nach `.github/workflows/` abgelehnt, da der verwendeten Anmeldung die Berechtigung `workflow` fehlt. Die Dateien bleiben unter `docs/github-workflows/` gesichert, bis ein Token mit dieser Berechtigung verfügbar ist.

## Geprüft am 6. November 2026

| Prüfung | Ergebnis |
| --- | --- |
| Oberfläche am 7. November 2026 | TypeScript, ESLint, 3 Vitest-Tests und Vite-Produktionsbuild nach dem Branding-Wechsel bestanden. |
| Rust-App am 7. November 2026 | Formatierung, Clippy mit `-D warnings` und 30 Standardtests im Podman-Build-Image bestanden. Darunter neue Tests für Burst-Ereignisse, verlorene Tastenlöse-Ereignisse, Abbruch während jeder Phase und Shortcut-Rollback. |
| Korrekturprozess am 7. November 2026 | Formatierung, Clippy mit `-D warnings`, 3 Standardtests und 3 Protokolltests bestanden; der Modelltest bleibt ohne Gewichte übersprungen. |
| Oberfläche am 6. November 2026 | TypeScript, ESLint, 3 Vitest-Tests, Vite-Produktionsbuild und npm-Audit bestanden. npm meldet 0 Schwachstellen. |
| Rust-App auf Linux x64 | Formatierung, Clippy und 22 Standardtests bestanden. Davon 11 für Anbieter mit nachgebildeten Antworten. Keine bezahlten oder echten Cloud-Aufrufe. |
| Whisper Base | SHA-256 geprüft. Je eine künstliche deutsche und englische WAV-Datei wurde in einem Container ohne Netzwerk erkannt. Zusammen 2,08 s für beide Aufrufe inklusive Laden. |
| Qwen3-0.6B-Q8_0 | SHA-256 geprüft. Formatierung, Clippy und 6 Standardtests bestanden. Je eine deutsche und englische Textkorrektur im Container ohne Netzwerk. Einzellauf ab Prozessstart inklusive Laden 0,714 s bzw. 0,698 s. |
| Linux-DEB und Fensterwechsel | Debug-DEB gebaut und in Debian 12 ohne Systeminstallation entpackt. App startete unter X11 im virtuellen Bildschirm. In zwei netzlosen Durchläufen speiste PulseAudio künstliches deutsches Mikrofon-Audio ein. Halten führte zu einem deutschen Satz im externen GTK-Textfeld. Umschalten mit lokalem Qwen3 übersetzte den Text und fügte ihn auf Englisch ein. Die Tests prüfen den Ablauf und ein Stichwort. Beim Beispieldiktat gab es Erkennungsfehler. |
| Start und Speicher | AMD Ryzen 7 7800X3D, 30 GiB System-RAM. Debug-Paket bis zum sichtbaren Fenster etwa 0,50 s. App-Hauptprozess im Leerlauf etwa 169 MiB RSS (belegter physischer Speicher), ohne getrennte WebKit-Prozesse. Keine Messung bis zur ersten nutzbaren Eingabe und keine vollständige Latenzmessung. |
| RustSec | Beide Abhängigkeitslisten gescannt. Keine als Schwachstelle eingestuften Treffer. App-Liste mit 8 Warnungen zu nicht gepflegten Bibliotheken und einer unsicheren GLib-Schnittstelle in dieser Warnungszahl. Engine-Liste ohne Warnung. Warnungen vor Freigabe bewerten. |

Der virtuelle Linux-Test verwendet künstliche Eingabe und kein physisches
Mikrofon. Windows, macOS und Linux Wayland wurden nicht vollständig
praktisch geprüft; auf KDE Wayland wurde am 10. November 2026 nur die
Portal-Sitzung angelegt und geschlossen, nicht die Tastenfreigabe. NSIS,
DMG und AppImage sind noch nicht gebaut. Die aktuelle
x64-Build-Konfiguration der lokalen Korrektur verwendet AVX2 und verwandte
Prozessorfunktionen. Ein Starttest auf älteren Prozessoren fehlt. Die
Hotkey-Zustandsmaschine ist durch Unit-Tests abgedeckt; echte Tastaturtests
auf Windows, macOS und X11 sowie Sleep/Wake- und RDP-Tests stehen aus.

## Nächste Schritte

1. **Prüfungen auf GitHub aktivieren.** Folge [github-workflows/README.md](github-workflows/README.md). Prüfe den Änderungsvorschlag auf Ubuntu und baue NSIS, DMG und AppImage. Prüfe, ob jedes Paket das Korrekturprogramm und alle nötigen Systembibliotheken enthält. Das lokale DEB ist ein Debug-Testpaket. Die Erstfreigabe braucht einen optimierten Paketbau.
2. **Echte Desktop-Tests nachholen.** Prüfe physisches Mikrofon, Gerätewechsel und Trennung, Tastenkürzel und Abbruch während jeder Phase, Fokuswechsel, Sonderzeichen, Kopieren, Statussymbol bei geschlossenem Fenster und Installationsstart. Prüfe Passwortspeicher und Anbieter freiwillig mit eigenen Testschlüsseln. Wiederhole den automatisierten [Linux-Test](TESTING.md) mit dem endgültigen Paket.
3. **Einfügen und Wayland praktisch abnehmen.** Die Portal-Anbindung und das mehrzeilige X11-Einfügen sind implementiert. Prüfe jetzt die echte Freigabe und Tastenbindung auf GNOME Wayland, KDE Plasma Wayland und wlroots, außerdem Qt und Browser unter X11 sowie XWayland. Die X11-Prüfung kennt Fensterwechsel, aber nicht zuverlässig einen Feldwechsel innerhalb desselben Fensters; Passwortfelder bleiben ein Restrisiko. Baue zusätzlich die macOS-Zugriffshilfe für fokussierte Elemente und Texteingabe. Prüfe beim Kopieren den Erhalt von Bild- und Textdaten in der Zwischenablage.
4. **Modelle und Leistung vervollständigen.** Prüfe echte Downloads inklusive Unterbrechung, Bereichsantwort, Prüfsummenfehler und freien Speicher. Ergänze bessere Stille-Erkennung, robustere Modellimport-Prüfung, Parakeet V3 mit geprüftem sherpa-onnx-Modell, GPU-Erkennung und Beschleunigung mit CPU-Rückfall. Teste portable x64-Builds auf älteren CPUs. Dokumentiere Ende-zu-Ende-Zeiten, Spitzen-RAM und GPU-Verhalten auf echter Hardware.
5. **Restliche Bedienung und Veröffentlichung.** Ergänze Systemstart, optionale Audiosignale und Diagnose. Manche System- und Anbieterfehler sind nur einsprachig. Prüfe die Lizenzhinweise der tatsächlich ausgelieferten Bibliotheken und RustSec-Warnungen. Führe den Arbeitszweig mit `main` zusammen, wenn die Prüfungen passen. Folge dann [RELEASE.md](RELEASE.md). Signierung, macOS-Notarisierung und authentifizierte Updates sind offen.

Für den Einstieg in den Quellcode siehe [ARCHITECTURE.md](ARCHITECTURE.md).
Die Befehle stehen in [INSTALLATION.md](INSTALLATION.md) und
[TESTING.md](TESTING.md). Die beiden Cargo-Lockdateien und
`package-lock.json` gehören zum Stand.

---

## Sicherheitsreview (Issue #27)

Das [Bedrohungsmodell](THREAT_MODEL.md) dokumentiert die Vertrauensgrenzen
zwischen Mikrofon, nativem ASR/LLM-Prozess, optionalem Cloud-Anbieter,
Modellserver, Tauri-Webview, OS-Zwischenablage und fremdem Editor.
Es enthält konkrete Restrisiken und Sicherheits-Regressionen S01–S10.
**Dies ist ein Dokumentations- und Planungsstand, kein bestandener
Security-Test oder abgeschlossener Audit.** Ohne reale OS-/Netzwerktests,
Paket-Signierung und Nachweise für Hochrisiken bleibt Issue #27 ein
Release-Blocker.
