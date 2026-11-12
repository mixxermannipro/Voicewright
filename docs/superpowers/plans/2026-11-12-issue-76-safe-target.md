# Issue #76 – sichere Textfeldprüfung

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Kein automatisches Tippen in unbekannte, geschützte oder seit Aufnahmestart gewechselte Textfelder.

**Architecture:** Linux-X11 ergänzt die Fensterprüfung um die eindeutige AT-SPI-Textfeldidentität und frische Metadaten (Fokus, editierbar, Rolle, Prozess). Die bereits vorhandene ashpd/zbus-Abhängigkeit genügt. Fehlender Bus, Zeitlimit oder unbekanntes Widget bedeuten Copy-Fallback. Windows akzeptiert nur nachweisbare native Unicode-Editfelder ohne Passwort-/Read-only-Stil; unbekannte Browser-/Custom-Felder bleiben Copy-only. Mehrzeilentext darf keine Return-Ereignisse in ein Einzeilenfeld schicken.

**Spec:** `docs/V1_SCOPE.md`, Issue #76 sichere Ausgabe.
**Tech Stack:** Rust 1.99.1, ashpd/zbus, Win32, GTK3, Xvfb, privater D-Bus.

**Verifizierte Plananpassung:** Der virtuelle Test reproduzierte Return als
potenzielles „Senden“ auch in einem mehrzeiligen Feld. Linux verwendet deshalb
einen einzigen literalen `EditableText.InsertText`-Aufruf an das erfasste Feld,
nicht mehr Tastatur-Chunks. UTF-8-Byte-Länge und Zeichenoffsets folgen dem
offiziellen AT-SPI-Vertrag; das Zeichenanzahl-Delta wird geprüft, ohne Inhalt
zu lesen. Bestehende Selektion wird nicht ersetzt. Beobachtbare Cursoränderungen
blockieren. Timeout nach Dispatch ist unbestätigt und wird nie wiederholt.
Windows-Absätze bleiben bis zum nativen literalen Nachweis Copy-only.

## Grenzen und Review Focus

- Keine Texte aus Zielanwendungen lesen, keine Clipboardänderung, keine Nutzerdesktoptests.
- AT-SPI ist ein Sicherheitsindikator des Zielprogramms, keine atomare OS-Sperre gegen jeden Fokuswechsel; deshalb vor jedem Chunk erneut prüfen.
- Unbekannte/fehlerhafte Metadaten und Zeitlimits blockieren; fremde Prozesse nicht nach Text durchsuchen.
- Passwort, readonly, Terminal, derselbe Fenster-/anderer Feldfokus und einzeilige Felder brauchen Negativtests.
- Benutzerdefinierte Widgets/Browser ohne verifizierbare Metadaten verlieren Auto-Insertion, behalten aber das vollständige Ergebnis.

## Task 1: Metadaten und Zielbindung

- [x] Unit-Tests zuerst: erlaubte Textrolle + notwendige Zustände, abgelehnte Passwort-/Terminal-/unbekannte Rollen, readonly/defunct/unvollständige Zustände.
- [x] `src-tauri/src/insertion/atspi.rs`: begrenzte Suche nur innerhalb der erkannten Prozess-PID; eindeutige Bus-/Objektidentität; erneute Prüfung; hartes Zeit-/Knotenlimit.
- [x] `src-tauri/src/insertion.rs`: Feldidentität am Start speichern, Fenster-PID korrekt über Fokus-Vorfahren bestimmen, Feld erneut prüfen; Zeilenumbrüche nur literal in Linux-Multilinefeldern; native Windows-Edit-Whitelist (nativ ungeprüft).
- [x] Unit-Tests, fmt, Clippy und beide Rust-Suiten ausführen.

## Task 2: Virtuelle GTK-Regressionen und Dokumentation

- [x] X11-Smoke in privater D-Bus-Sitzung mit AT-SPI-Bridge laufen lassen; vorhandene Unicode-/Multiline-Prüfung erhalten.
- [x] Passwortfeld, gleicher Fenster-/anderer Feldfokus und fehlende A11y-Schnittstelle blockieren, ohne Nutzerdaten oder reale OS-Freigaben.
- [x] `docs/PLATFORM_SUPPORT.md`, `docs/TESTING.md`, `docs/PROGRESS.md` und Issue #76 mit tatsächlichen Ergebnissen aktualisieren.
- [ ] Unabhängiger DeepSeek-Review, kleiner eigener PR, CI auswerten. Kein Release und keine vorgezogene Nutzerabnahme.
