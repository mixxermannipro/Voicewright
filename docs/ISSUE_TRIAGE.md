# Voicewright: Triage aller 35 bisherigen offenen Issues

**Stand 12.11.2026.** [Einziger aktiver V1-Auftrag: #76](https://github.com/mixxermannipro/Voicewright/issues/76). Frühere **35 offene Issues** werden nach dieser Bestandsaufnahme geschlossen (**not planned**, als eigenständige Arbeitseinheiten), nicht aus dem Repository gelöscht. Sie bleiben vollständig lesbar und nach einer abgeschlossenen V1 bei Bedarf wieder aktivierbar. Geschlossen **heißt nicht umgesetzt**.

## Regeln

- **V1-Referenz**: die V1-relevanten Kernanforderungen, Tests und Risiken gehen in [V1_SCOPE.md](V1_SCOPE.md) sowie Issue #76 über, gegebenenfalls mit reduziertem Umfang.
- **Post-V1**: Wünsche/Optimierungen blockieren **nicht** den ersten virtuell geprüften Kandidaten; keine ungeprüften Versprechen. Insbesondere alternative ASR, GPU-Optimierung, Multi-Provider-Ausbau und fortgeschrittene KI-Stile.
- **Abgelöster Masterplan**: die alten Steuerungsissues #39 und #47 gelten als archivierte Historie, nicht als neue Arbeitsanweisungen.
- **PR #75** (Wayland-Portale) bleibt **Draft** zur separaten Prüfung. Es hat noch keinen echten GUI-Berechtigungsnachweis, daher keine automatische Freigabe.
- **Externe Hardware- und Portaltests** sind **einmal ganz am Ende** als Nutzerfeedback vorgesehen, nicht als während der Entwicklung zu beschaffende Gerätestests oder Besitzerfreigaben. Sicherheitsgrenzen werden nicht umgangen.

| Issue | Ursprüngliche Aufgabe | Entscheidung |
| --- | --- | --- |
| [#3](https://github.com/mixxermannipro/Voicewright/issues/3) | [P0][Core] Sichere, zuverlässige Texteingabe in fremde Anwendungen mit Unicode, Mehrzeilentext und Fokusvalidierung | V1-Referenz (soweit nötig, virtualisieren) |
| [#4](https://github.com/mixxermannipro/Voicewright/issues/4) | [P0][Windows] Fokus-/Editor-Erkennung und zuverlässiges Unicode-Einfügen systemweit | V1-Referenz (soweit nötig, virtualisieren) |
| [#5](https://github.com/mixxermannipro/Voicewright/issues/5) | [P0][macOS] Native globale Diktate mit Accessibility-Fokus, Textinsertion und Berechtigungs-Onboarding | V1-Referenz (soweit nötig, virtualisieren) |
| [#7](https://github.com/mixxermannipro/Voicewright/issues/7) | [P0][Hotkeys] Push-to-talk, Umschaltmodus, Escape/Abbruch und Zustandsautomat gegen Race Conditions härten | V1-Referenz (soweit nötig, virtualisieren) |
| [#8](https://github.com/mixxermannipro/Voicewright/issues/8) | [P0][Desktop] Autostart bei Anmeldung, echter Hintergrundbetrieb, Tray-Menü und sofortige Diktierbereitschaft | V1-Referenz (soweit nötig, virtualisieren) |
| [#9](https://github.com/mixxermannipro/Voicewright/issues/9) | [P0][Audio] Mikrofon-Capture, VAD, Geräteaustausch und Sprachende-Erkennung produktionsreif machen | V1-Referenz (soweit nötig, virtualisieren) |
| [#10](https://github.com/mixxermannipro/Voicewright/issues/10) | [P0][Modelle] Evidenzbasiertes ASR-Benchmark und ein empfohlenes Standardmodell je Hardwareklasse | V1-Referenz (soweit nötig, virtualisieren) |
| [#11](https://github.com/mixxermannipro/Voicewright/issues/11) | [P0][Modelle] Modellmanager mit Hardware-Erkennung, Empfehlung, sicheren Downloads und Erstinstallation | V1-Referenz (soweit nötig, virtualisieren) |
| [#12](https://github.com/mixxermannipro/Voicewright/issues/12) | [P0][Performance] Portable Builds, CPU-Fallback, Idle-Ressourcen und Kaltstart optimieren | V1-Referenz (soweit nötig, virtualisieren) |
| [#13](https://github.com/mixxermannipro/Voicewright/issues/13) | [P1][ASR] Parakeet TDT 0.6B v3 als alternative lokale Spracherkennungs-Engine integrieren | Post-V1 / kein erstes Release-Gate |
| [#14](https://github.com/mixxermannipro/Voicewright/issues/14) | [P1][ASR] Hardwarebeschleunigung für Whisper/Parakeet mit Auto-Detection und sicherem CPU-Fallback | Post-V1 / kein erstes Release-Gate |
| [#15](https://github.com/mixxermannipro/Voicewright/issues/15) | [P1][Latenz] Diktat-Ende bis eingefügtem Text beschleunigen und optional inkrementelle ASR evaluieren | V1-Referenz (soweit nötig, virtualisieren) |
| [#17](https://github.com/mixxermannipro/Voicewright/issues/17) | [P0][Prompts] Hochwertiger editierbarer Standard-Systemprompt mit Tests, Vorschau und Reset | V1-Referenz (soweit nötig, virtualisieren) |
| [#18](https://github.com/mixxermannipro/Voicewright/issues/18) | [P1][Wörterbuch] Eigenes mehrsprachiges Vokabular, Fachwörter und Dialekte importieren/exportieren | V1-Referenz (soweit nötig, virtualisieren) |
| [#19](https://github.com/mixxermannipro/Voicewright/issues/19) | [P0][Cloud] OpenAI, Google AI Studio, Anthropic, xAI, OpenRouter und weitere Provider vollständig testen und härten | V1-Referenz (soweit nötig, virtualisieren) |
| [#20](https://github.com/mixxermannipro/Voicewright/issues/20) | [P1][Provider] Ollama/LM Studio und eigene OpenAI-kompatible Endpoints lokal und sicher integrieren | Post-V1 / kein erstes Release-Gate |
| [#21](https://github.com/mixxermannipro/Voicewright/issues/21) | [P1][KI-Modi] Sinnvolle auswählbare Diktier-Stile, Formatierung und Übersetzung ohne Bedeutungsschäden | Post-V1 / kein erstes Release-Gate |
| [#22](https://github.com/mixxermannipro/Voicewright/issues/22) | [P0][Onboarding] Erste 2 Minuten: Berechtigungen, empfohlenes Modell, lokaler Modus und Testdiktat | V1-Referenz (soweit nötig, virtualisieren) |
| [#23](https://github.com/mixxermannipro/Voicewright/issues/23) | [P1][UI/UX] Schlankes modernes Liquid-Glass-inspiriertes Desktop-Design, priorisiert nach Funktion und Performance | V1-Referenz (soweit nötig, virtualisieren) |
| [#24](https://github.com/mixxermannipro/Voicewright/issues/24) | [P1][Accessibility] Vollständige deutsche/englische Lokalisierung, Screenreader und Keyboard-Navigation | V1-Referenz (soweit nötig, virtualisieren) |
| [#25](https://github.com/mixxermannipro/Voicewright/issues/25) | [P1][Feedback] Leichtgewichtiges Aufnahme-Overlay, Tray-Status, optionales Audiofeedback und Wiederherstellungsansicht | V1-Referenz (soweit nötig, virtualisieren) |
| [#26](https://github.com/mixxermannipro/Voicewright/issues/26) | [P1][Konfiguration] Settings-Versionierung, sichere Migration, Export/Import und Wiederherstellung | V1-Referenz (soweit nötig, virtualisieren) |
| [#27](https://github.com/mixxermannipro/Voicewright/issues/27) | [P0][Security] Threat-Model für Mikrofon, Clipboard, Prozessstart, Modell-Downloads und API-Keys | V1-Referenz (soweit nötig, virtualisieren) |
| [#28](https://github.com/mixxermannipro/Voicewright/issues/28) | [P0][Recht] Lizenzen, Urhebernachweise, SBOM, Modellgewichte und Marken-/Namensprüfung vor Veröffentlichung | V1-Referenz (soweit nötig, virtualisieren) |
| [#29](https://github.com/mixxermannipro/Voicewright/issues/29) | [P0][CI/CD] Vorhandene GitHub-Workflow-Vorlagen aktivieren, absichern und Release-Gates automatisieren | V1-Referenz (soweit nötig, virtualisieren) |
| [#30](https://github.com/mixxermannipro/Voicewright/issues/30) | [P0][Release Windows] Produktionsreife signierbare NSIS-Installation und echte Windows-E2E-Prüfung | V1-Referenz (soweit nötig, virtualisieren) |
| [#31](https://github.com/mixxermannipro/Voicewright/issues/31) | [P0][Release macOS] DMG, Universal-/ARM64-Build, Accessibility-Permissions, Signierung und Notarisierung | V1-Referenz (soweit nötig, virtualisieren) |
| [#33](https://github.com/mixxermannipro/Voicewright/issues/33) | [P1][Distribution] Authentifizierte automatische Updates, Signaturen, Rollback und sichere Release-Kanäle | V1-Referenz (soweit nötig, virtualisieren) |
| [#35](https://github.com/mixxermannipro/Voicewright/issues/35) | [P0][QA] Vollständige reale End-to-End-Testmatrix für Windows, macOS, Linux und Cloud/Offline | V1-Referenz (soweit nötig, virtualisieren) |
| [#36](https://github.com/mixxermannipro/Voicewright/issues/36) | [P0][Stabilität] Langzeittest, Ressourcenleck-, Absturz- und Sitzungserholungs-Tests | V1-Referenz (soweit nötig, virtualisieren) |
| [#37](https://github.com/mixxermannipro/Voicewright/issues/37) | [P1][Diagnose] Lokale Datenschutz-schonende Fehlerdiagnose, Performance-Protokoll und Support-Export | V1-Referenz (soweit nötig, virtualisieren) |
| [#38](https://github.com/mixxermannipro/Voicewright/issues/38) | [P0][Dokumentation] Release-fähige README, Installationsanleitung, Nutzerhandbuch, Troubleshooting und Datenschutztext | V1-Referenz (soweit nötig, virtualisieren) |
| [#39](https://github.com/mixxermannipro/Voicewright/issues/39) | [P0][EPIC] Release 1.0: vollständige Diktier-App auf Windows, macOS und Linux – Roadmap und Abnahme | Abgelöster Masterplan |
| [#47](https://github.com/mixxermannipro/Voicewright/issues/47) | [P0][PLAN] Persönliche Priorisierung aller Issues: schnellster Weg zur produktiven Nutzung auf Fedora (Stand 7.11.2026) | Abgelöster Masterplan |
| [#70](https://github.com/mixxermannipro/Voicewright/issues/70) | [P1][UI/UX] Verbindliches Minimal-Design für Voicewright: Settings, Hotkey, Tray und Aufnahme-HUD | V1-Referenz (soweit nötig, virtualisieren) |

## Integrierte V1-Achsen
- Desktop: #3 #4 #5 #7 #8 #9 #11 #12 #22 #25 #26; Fokus/Clipboard/Shortcut, Hintergrundbetrieb, lokales Diktat, Modellinstallation, Einstellungen.
- Qualität: #10 #15 #17 #18 #24 #35 #36 #37; nur relevante DE/EN-, ASR-, Datenschutz-, Fehler- und Stresstests auf **virtuellen** Runnern.
- Sicherheit/Distribution: #19 (nur bereits vorhandene Anbieter absichern, keine echten Keys), #27 #28 #29 #30 #31 #33 #38; Windows/macOS/Linux-Paketintegrität, sichere Datenflüsse, Dokumentation.
- UI: #23 #70; [unveränderte vereinbarte Mockups](design/VOICEWRIGHT_UI_CONCEPT.md) als Ziel, keine parallel konkurrierende Design-Sprache.

## Alte bereits geschlossene Tickets
#2, #6, #16, #32, #34 bleiben geschlossen und als technische Historie erhalten; das ist kein Beleg, dass jede darin beschriebene Fähigkeit auf allen Plattformen fertig ist.

## Was bedeutet „virtuell bestanden“?
Die CI testet Quellcode, echte/virtuelle Audio-Samples, GUI-Probes in isolierten Xvfb/X11-/Wayland-Testumgebungen, Modellgewichte soweit autorisiert, Vertrags-Mocks und plattformspezifische Packager. **Echte TCC-/Mikrofon-/Shortcut-/Portal-Freigaben und physische Nutzerhardware lassen sich dadurch nicht vollständig nachweisen.** Die V1-Vorabversion darf autonom bereitgestellt werden; **öffentliche stabile Freigabe erst nach Nutzerfeedback.** [Testplan](VIRTUAL_TESTING.md).
