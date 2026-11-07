# Bedrohungsmodell und Sicherheits-Freigabegates

**Stand:** 7. November 2026 · **Gültigkeit:** Code auf main vor PR #42 · **Status:** statische Architekturprüfung und Testplan, **keine** unabhängige Sicherheitszertifizierung oder abgeschlossene Penetrationsprüfung.

Dieses Dokument konkretisiert Issue #27. Aussagen über implementierte Schutzmaßnahmen beziehen sich auf die genannten Dateien; sie sind **keine Nachweise**, dass diese Schutzmaßnahmen auf allen Zielplattformen tatsächlich funktionieren. Neue KI-Ausgabeprüfungen werden separat in [PR #42](https://github.com/mixxermannipro/Voicewright/pull/42) vorgeschlagen und sind zum Zeitpunkt dieser Analyse **nicht Teil von main**.

## 1. Ziel, Geltungsbereich und schützenswerte Werte

Voicewright ist ein Desktop-Diktierprogramm: globaler Hotkey bzw. Schaltfläche → Mikrofon → lokale Whisper-ASR → optional lokale Qwen3- oder BYOK-Cloud-Textkorrektur → Zieltextfeld bzw. Kopieren. Es benötigt kein Benutzerkonto.

| Asset | Schutzbedarf | Warum |
| --- | --- | --- |
| Roh-Audio und Transkript | Vertraulichkeit hoch; Integrität hoch | Kann private Gespräche, Kunden- oder Zugangsdaten enthalten |
| Zielanwendung und Editorinhalt | Integrität hoch | Falsches Fenster oder falsches Feld kann Daten offenlegen bzw. verändern |
| API-Schlüssel | Vertraulichkeit sehr hoch | Ermöglichen kostenpflichtige Requests und Missbrauch |
| Konfiguration inkl. Systemprompt und Provider-URLs | Integrität hoch | Steuert, ob Text das Gerät verlassen darf |
| Modellgewichte und Parser-Prozess | Integrität/Verfügbarkeit hoch | Unvertrauenswürdige Dateien treffen auf native Bibliotheken |
| Installationspakete und Updates | Integrität sehr hoch | Werden mit den Rechten des angemeldeten Kontos ausgeführt |
| Zwischenablage und Debug-/Supportdaten | Vertraulichkeit hoch | Andere Programme, Verlauf oder Gerätesynchronisierung können Zugriff haben |

**Bedrohungsakteure:** fremde Prozesse und Webseiten auf demselben Gerät; nicht vertrauenswürdige Audioinhalte, Modelle oder Remote-Provider; kompromittierte Downloadquelle; manipulierte Installationspakete; versehentlich falsche Bedienung. Ein vollständig kompromittiertes Betriebssystem bzw. Administrator-Konto kann nicht durch die App isoliert werden.

**Nicht im Scope:** allgemeine Sicherheit des OS-Keyrings und der Remote-Provider, Malware-Entfernung, Rechtssicherheit des Datenschutztexts und Schutz vor physischen Angreifern mit entsperrtem Rechner.

## 2. Vertrauensgrenzen und Datenfluss

| Schritt / Grenze | Daten | Implementierter Mechanismus (Code) | Verbleibender Prüfbedarf |
| --- | --- | --- | --- |
| Mikrofon → nativer Prozess | PCM-/Audio-Samples | src-tauri/src/audio.rs, session.rs; Aufnahme im RAM, Abbruch-/Sitzungssteuerung | Betriebssystem-Berechtigung, Gerätewechsel, exklusive Sessions, Abbruch/Suspend und Speicherschranken physisch testen |
| Audio → Whisper-Engine | Audio + Sprach-/Modellwahl | src-tauri/src/speech.rs; lokale Verarbeitung | Fehlerhafte Audiodaten/Modelle, native Bibliotheken und Ressourcenverbrauch prüfen |
| Whisper → Textkorrektur | Unvertrauenswürdiger Transkripttext + Systemprompt | src-tauri/src/app.rs und settings.rs | KI-Ausgabe kann Fakten verändern oder Audio-Befehle als Aufforderungen deuten; PR #42 ist nur eine zusätzliche Heuristik |
| Hauptprozess → lokale Qwen3-Sidecar | JSON über stdin/stdout, Modellpfad | src-tauri/src/cleanup.rs; fester Programmname, ohne Shell, begrenzte Ausgabe, Timeout, kill_on_drop | Manipuliertes Sidecar/Modell, Crash, Hänger und TOCTOU auf Modelldatei testen |
| Hauptprozess → Cloud-/kompatibler Server | Transkript, Systemprompt, Modellkennung, Authentisierung | src-tauri/src/providers.rs; nur nach Cloud-Opt-in, TLS für Remote-Ziele, Redirects abgelehnt, Keyring | Provider-Policies, DNS-Auflösung, interne IP-Ziele über HTTPS, Proxy-/Netzwerkgrenzen und Fehlerausgabe prüfen |
| Modellserver/Datei → Modellordner | Große Binärgewichte | src-tauri/src/models.rs; fester Katalog, SHA-256, Größenprüfung, geprüfte Redirects; Import mit Strukturprüfung | SHA sichert Download-Identität, **nicht** Vertrauenswürdigkeit des nativen Parsers oder importierter Dateien |
| Hauptprozess → fremdes Textfeld | Bearbeiteter Text | src-tauri/src/insertion.rs; Win-Fokusfeld/X11-Fensterprüfung, Abbruch, begrenzte Einfügelänge | X11-Feldwechsel innerhalb desselben Fensters, Passwortfelder, Race-Conditions, AutoFill und Tastaturtreiber |
| Hauptprozess → OS-Zwischenablage | Ergebnis | src-tauri/src/app.rs; explizites Kopieren | Clipboard-History, Drittapps und Cloud-Synchronisierung liegen außerhalb der App-Kontrolle |
| Webview → Tauri IPC | Kommando-Parameter | src-tauri/capabilities/default.json (keine allgemeinen Frontend-Berechtigungen), tauri.conf.json (CSP) | Alle #[tauri::command]-Eingaben, eventuelle neue Plugins, XSS und Build-CSP regelmäßig prüfen |
| Konfiguration → Dateisystem/Keyring | Settings / API-Key getrennt | src-tauri/src/settings.rs (Validierung, atomare JSON-Ablage), providers.rs (System-Keyring) | Dateiberechtigungen, beschädigte JSON, Legacy-Keys, Reset/Backups, Symlinks und OS-Datenschutz prüfen |

## 3. Priorisierte Bedrohungen und Restrisiken

**Bewertung:** Hoch = mögliches Sicherheits-/Datenschutz-Release-Gate; Mittel = mit dokumentierter Einschränkung und nachgewiesener Behandlung prüfbar; Niedrig = normaler Qualitätscheck. Die Priorisierung ist eine Arbeitshypothese ohne formale CVSS-Bewertung.

| ID / Risiko | Pfad / aktuelle Kontrolle | Restrisiko / notwendige Maßnahme | Prio |
| --- | --- | --- | --- |
| T01: Text gelangt unbemerkt an Cloud-Endpoint | settings.rs CleanupMode, app.rs Cloud-Zweig, providers.rs | Off/Local darf **niemals** Provider-Requests erzeugen. Netzwerk-Mitschnitt in jeder Betriebsart, auch Vorschau, Modellsuche und Fehlersituationen; UI vor Cloud-Vorschau informieren. | Hoch |
| T02: Geheimnisse/Diktat in Logs oder Crashdump | providers.rs generische Fehlertexte, cleanup.rs stderr verworfen | Kein systematischer Audit aller Fehlerpfade, Prozessumgebungen, Panics, Bibliothekslogs und Support-Exports belegt. Test-Secrets und Test-Transkripte in Negativtests injizieren; Log-Scan. | Hoch |
| T03: Falsches Feld/Ziel oder Passwortfeld | insertion.rs focus(), Win-Subwindow und X11-Windows, 64-Zeichen-Chunks | X11 erkennt Wechsel zwischen Feldern desselben Fensters nicht verlässlich; macOS/Wayland direktes Einfügen nicht implementiert. Bei Zweifel **nur Copy-Fallback**, nie blindes Tippen. Passwort-/geschützte Felder real prüfen. Siehe #3–#6. | Hoch |
| T04: Bösartige Modellgewichte/Parser-Memory-Safety | models.rs SHA-256 bei Katalog, Importprüfung | SHA-256 bestätigt den erwarteten Katalogstand, aber keine vollständige Integrität/Quellenprüfung importierter Modelle. Untrusted GGUF/GGML-Dateien können nativen Parser angreifen. Import-Fuzzing, Dateiberechtigungen, Symlinks, Sandbox-Möglichkeiten und Security-Advisories bewerten. | Hoch |
| T05: Missbrauch eigener Provider-URLs / SSRF | providers.rs HTTPS remote, HTTP nur Loopback, keine Redirects, kein HTTP-Proxy | Auch HTTPS-DNS-Namen können intern auflösbar sein; bewusst konfigurierte kompatible URLs sind eine Vertrauensentscheidung des Users. Netzziel vor Verbindung/bei DNS-Wechsel und private/Link-local/Metadata-IP-Adressen gezielt testen; Policy für Remote-Custom-Endpoints festlegen. | Hoch |
| T06: Prompt Injection / falsche KI-Korrektur | settings.rs Promptregeln, Cloud-Request-Systemrolle, Qwen-Chattemplate | Sprachinhalt ist untrusted DATA. Keine Anweisung aus Transkript ausführen, keine neue Information ergänzen. Heuristische Ausgabeprüfung in PR #42 fängt keine semantisch subtilen Änderungen. DE/EN-Golden-Korpus #17 nötig. | Hoch |
| T07: Manipulierte Installation/Updates | tauri.conf.json Paketmetadaten | Keine nachgewiesene Signierung/Notarisierung und kein signierter Updatekanal. Für öffentliche Releases SHA-256, Herkunft, Signatur, Signing-Key-Schutz und Installertest verlangen (#30–#33). | Hoch |
| T08: Missbrauch Tauri/Webview | capabilities/default.json leer; tauri.conf.json CSP | Neue Plugins, Remote-Inhalte oder generische Dateisystem-/Shell-Berechtigungen können Sicherheitsgrenzen verändern. CSP und Permission-Diff in PR prüfen; keine fremden Webseiten in privilegierte Webview. | Mittel |
| T09: Beschädigte/manipulierte Settings | settings.rs validiert JSON und schreibt atomar | Ungültige Einstellungen erzeugen beim Start einen Warnstatus und Defaults; der ursprüngliche Datenstand bleibt untersuchbar. Migrations-, Symlink-, Pfad- und Rechteprüfungen fehlen (#26); Cloud-Modus nach Restore sicher deaktivieren. | Mittel |
| T10: Unkontrollierte Sidecar-Ressourcen | cleanup.rs 240s-Timeout, begrenzter stdio-Puffer, child.kill_on_drop | RAM/CPU und Dateihandles können trotz Timeout wachsen; große Modelle und native Crashes testen. Unterbrechung muss Prozess terminieren und neue Sitzung erlauben (#36). | Mittel |
| T11: Clipboard/Overlay-Datenabfluss | app.rs explizite Kopie statt stiller History | Text kann durch Clipboard-History, andere Apps und geräteübergreifendes Sync weitergegeben werden. Warnung, keine automatische Cloud-Synchronisierung behaupten; Clear-Result löscht nicht zwangsläufig die OS-Zwischenablage. | Mittel |
| T12: Manipulierter Download/Redirect/Part-File | models.rs HTTPS, vertrauenswürdige Redirects, Prüfsumme, .part | Redirect-, Resume-, Range-, 206/200- und Symlink-Races sowie vollgelaufene Platte mit Mockserver testen; keine ungeprüfte Modelldatei ausführen (#11). | Mittel |
| T13: Hotkey- oder Cancel-Race | session.rs Generation/Abbruch, app.rs State | Tatsächlicher OS-Hotkey, Sleep/Wake, Keyboard-Loss und konkurrierende Sessions müssen auf echten Zielplattformen geprüft werden (#7/#35/#36). | Mittel |
| T14: Unklare Lizenz- und Lieferkette | dokumentierte THIRD_PARTY_LICENSES, zwei Cargo.lock, package-lock | Aktuelle SBOM, Sicherheitswarnungen, Rechte von Modellen/Sidecars und Build-Reproduzierbarkeit bis zum Installer nachweisen (#28/#29). | Mittel |

## 4. Konkrete Sicherheits-Regressionen (Release-Gates)

| Test | Vorgehen mit synthetischen Daten | Erfolgskriterium |
| --- | --- | --- |
| S01 – Cloud nur bei Opt-in | Off und Local, Vorschau, Fehlerfall, Modellwechsel, optionaler Connection-Test; Netzwerkverkehr beobachten | Keine Korrektur-Requests zu Cloud-Anbietern ohne bewusste Aktivierung. Modell-Downloads/Provider-Tests separat kennzeichnen |
| S02 – Provider-Ziele | Userinfo, Fragmente, Query, HTTP zu öffentlichem Host, Loopback-HTTP, HTTPS, 3xx, DNS/Proxy-Fall und IP-Literale prüfen | Ungültige Ziele/Redirects abgewiesen; interne und Metadata-Ziele gemäß festzulegender Policy geschützt |
| S03 – Test-Secrets | Testkey (kein echter Schlüssel) und markierten Testtext durch alle Fehlerpfade schicken | Weder Schlüssel noch Testdiktat erscheinen in App-Logs, Panics, CI-Artefakten oder Support-Ausgabe |
| S04 – Manipulierte Modelle | Falscher Hash, abgeschnittene Datei, GGUF mit beschädigten Längen/Headers, .part/Symlink, falscher Dateityp | Auswahl/Download scheitert sicher ohne nativen Crash, ungesicherten Pfad oder unendliche Speicherbelegung |
| S05 – Konflikt zwischen Feldern | Texteditor mit zwei Feldern, Passwortfeld, Fensterwechsel während Wiedergabe, Sondertasten | Keine automatische Eingabe im falschen/sensiblen Feld. Bei Unsicherheit Text in der App verfügbar und Copy-Fallback |
| S06 – Unicode/Steuerzeichen | Umlaute, ß, Emoji, RTL, Nullbyte, CR/LF, Unicode-Kombinationszeichen | Keine Crashs/unsichtbare Kommandoausführung; korrektes Copy-Verhalten bei nicht sicher einfügbaren Texten |
| S07 – KI-Gegenprobe | Gesprochene „ignore previous instructions“, URLs, Kontonummern nur als Fiktivdaten, Zahlen/Negation, sehr lange Antworten | Keine Ausführung gesprochener Befehle; Ausgabe/Ablehnung/Fallback reproduzierbar und dokumentiert (#17) |
| S08 – Berechtigungen | Mic verweigern/entziehen, OS-Keyring sperren, Leserechte/App-Daten entziehen | Verständlicher Fehler; kein stiller Cloud-Fallback, kein Datenverlust, keine privilegierte Umgehung |
| S09 – Child-Lifecycle | Qwen-Engine abbrechen, Beendigung erzwingen, 240s-Timeout, App-Ende | Keine Zombie-Prozesse; weitere Aufnahme nutzbar; keine falsche Einfügung |
| S10 – Release-Integrität | Testinstaller frisch herunterladen; Prüfsummen, Bundle-Sidecar, Signatur und Windows/macOS/Linux-Warnungen prüfen | Plattform erst als unterstützt bezeichnen, wenn Schutzmechanismen real nachgewiesen |

**Belege pro Test:** Branch/Commit-SHA, OS/Version, Modellversion, Netzwerk-/Systembedingungen, Testdateien (keine Secrets), erwartetes und tatsächliches Ergebnis, verantwortliche Person, Datum. Release-Blocker dürfen nicht nur mit „per Unit-Test abgedeckt“ geschlossen werden, wenn der Angriff an einer OS-/Netzwerk-Grenze stattfindet.

## 5. Maßnahmenliste und Verantwortungsbereiche

- **Backend/Rust – P0:** Cloud-Opt-in und SSRF-/DNS-Policy prüfen (T01/T05), Log-/Secret-Audit (T02), Modellparser und Race-Risiken (T04/T12), Fokusvalidierung/Paswortfelder (T03).
- **Produkt/UI – P0:** Vor Cloud-Korrektur klare Übertragungsinformation und vor einzelnen Vorschautests Bestätigung; bei unsicherem Einfügen transparenten Copy-Fallback; eindeutige DE/EN-Fehlertexte.
- **QA – P0:** S01–S10 inklusive manueller Tests auf unterstützten Betriebssystemen dokumentieren; CI- und hardwarebasierte Ergebnisse unterscheiden (#35/#36).
- **Release/DevOps – P0:** SBOM, Paket-Signierung, Notarisierung, Installer-Berechtigungen und reproduzierbare Checks nachweisen (#28–#33).
- **Datenschutz/Dokumentation:** PRIVACY.md und SECURITY.md mit den realen Datenwegen und Meldeverfahren konsistent halten. Keine rechtliche Freigabe implizieren.

## 6. Freigabestatus

Zum Stand dieses Dokuments sind die Risiken dokumentiert, aber **nicht abschließend behoben oder getestet**. Insbesondere bleiben fehlende OS-E2E-Tests, Modellimport-Sicherheit, Endpoint-Richtlinie, Fehlereinfügungen, Log-Leaks und signierte Releasepakete echte Freigabegates. Issue #27 bleibt offen, bis implementierte Maßnahmen und reale Testbelege vorliegen.

Siehe außerdem [Architektur](ARCHITECTURE.md), [Tests](TESTING.md), [Plattformstatus](PLATFORM_SUPPORT.md), [Fortschritt](PROGRESS.md), [Privatsphäre](../PRIVACY.md) und [Sicherheitsmeldungen](../SECURITY.md).
