//! Golden-Tests für die gesprochene Textformatierung (Issue #34).
//!
//! Die erwarteten Werte stammen aus der Spezifikation (docs/SPOKEN_FORMATTING.md
//! und dem Abnahme-Protokoll von Issue #34), nicht aus der Implementierung.
//! Der Parser ist rein textuell: Er verändert nur den Textpuffer und kann
//! keine Tastendrücke, Fenstersteuerungen oder Systemaktionen auslösen.

#[path = "../src/spoken_format.rs"]
mod spoken_format;

use spoken_format::format;

fn fmt(text: &str) -> String {
    format(text, true)
}

#[test]
fn feature_off_preserves_everything_byte_for_byte() {
    let raw = "Hallo Komma neue Zeile neuer Absatz Punkt Fragezeichen Ausrufezeichen \
               Doppelpunkt Semikolon comma question mark exclamation mark period \
               full stop colon semicolon new line line break open quote close quote \
               literalmodus an literalmodus aus Äpfel Straße 42 12.04.2026 \
               2026-11-07 Oachkatzlschwoaf `punkt` \"neue Zeile\" Enter alles \
               löschen sudo rm -rf /";
    assert_eq!(format(raw, false).as_bytes(), raw.as_bytes());
    assert_eq!(format("", false).as_bytes(), b"");
    assert_eq!(format("", true).as_bytes(), b"");
}

#[test]
fn german_punctuation_golden() {
    assert_eq!(fmt("Hallo komma Welt ausrufezeichen"), "Hallo, Welt!");
    assert_eq!(fmt("Guten Morgen fragezeichen"), "Guten Morgen?");
    assert_eq!(fmt("Preis 99 Euro punkt"), "Preis 99 Euro.");
    assert_eq!(
        fmt("Ergebnis doppelpunkt Semikolon Ende"),
        "Ergebnis:; Ende"
    );
    assert_eq!(fmt("fertig KOMMA"), "fertig,");
}

#[test]
fn english_punctuation_golden() {
    assert_eq!(fmt("Hello comma world question mark"), "Hello, world?");
    assert_eq!(
        fmt("Price is fifty Euro exclamation mark"),
        "Price is fifty Euro!"
    );
    assert_eq!(
        fmt("Note colon details semicolon end"),
        "Note: details; end"
    );
    assert_eq!(fmt("Stop full stop Go period"), "Stop. Go.");
}

#[test]
fn lines_and_paragraphs_golden() {
    assert_eq!(
        fmt("Erster Absatz neuer Absatz Zweiter Absatz"),
        "Erster Absatz\n\nZweiter Absatz"
    );
    assert_eq!(
        fmt("Zeile eins neue Zeile Zeile zwei"),
        "Zeile eins\nZeile zwei"
    );
    assert_eq!(fmt("first line break second"), "first\nsecond");
    assert_eq!(fmt("A new paragraph B new paragraph C"), "A\n\nB\n\nC");
    assert_eq!(fmt("Text   punkt"), "Text.");
    assert_eq!(fmt("Text neue Zeile   Fortsetzung"), "Text\nFortsetzung");
}

#[test]
fn numbers_and_currency_preserved() {
    assert_eq!(
        fmt("Bestellung 123 kostet 49,90 Euro"),
        "Bestellung 123 kostet 49,90 Euro"
    );
    assert_eq!(
        fmt("Ticket 4B kostet 50, nicht 15 Euro"),
        "Ticket 4B kostet 50, nicht 15 Euro"
    );
    assert_eq!(fmt("Version 2.1.3 von 1.2.3"), "Version 2.1.3 von 1.2.3");
    assert_eq!(fmt("50 Prozent Rabatt"), "50 Prozent Rabatt");
    assert_eq!(fmt("15 punkt"), "15.");
    assert_eq!(fmt("5punkt"), "5punkt");
}

#[test]
fn dates_preserved() {
    assert_eq!(fmt("am 12.04.2026 war ich da"), "am 12.04.2026 war ich da");
    assert_eq!(
        fmt("Termin 2026-11-07 um 14:30"),
        "Termin 2026-11-07 um 14:30"
    );
    assert_eq!(fmt("am 21.11.2005 geboren"), "am 21.11.2005 geboren");
    assert_eq!(fmt("12. April 2026"), "12. April 2026");
    assert_eq!(fmt("Datum 12.04.2026 punkt"), "Datum 12.04.2026.");
}

#[test]
fn umlauts_and_eszett_preserved() {
    assert_eq!(fmt("Grüße aus München"), "Grüße aus München");
    assert_eq!(fmt("Straße mit Äpfel und Öle"), "Straße mit Äpfel und Öle");
    assert_eq!(fmt("über groß schön"), "über groß schön");
    assert_eq!(fmt("Pünktlichkeit KOMMA wichtig"), "Pünktlichkeit, wichtig");
    assert_eq!(fmt("ẞ"), "ẞ");
}

#[test]
fn dialect_preserved() {
    assert_eq!(fmt("Oachkatzlschwoaf"), "Oachkatzlschwoaf");
    assert_eq!(fmt("I hob a komma Gschicht"), "I hob a, Gschicht");
    assert_eq!(fmt("S'war a schena Tag"), "S'war a schena Tag");
    assert_eq!(fmt("Des is a komma lustig"), "Des is a, lustig");
}

#[test]
fn repetitions_each_fire() {
    assert_eq!(fmt("A punkt punkt B"), "A.. B");
    assert_eq!(fmt("komma komma komma"), ",,,");
    // Der Abstand vor dem Befehlswort gehört zum Befehl und wird mit
    // umgewandelt; nach dem Umbruch folgt der Text ohne Leerzeichen.
    assert_eq!(fmt("Text neue Zeile neue Zeile Ende"), "Text\n\nEnde");
    assert_eq!(fmt("A new paragraph new paragraph B"), "A\n\n\n\nB");
}

#[test]
fn word_boundaries_protect_words() {
    assert_eq!(fmt("Punktland"), "Punktland");
    assert_eq!(fmt("Kommaplatz und newline"), "Kommaplatz und newline");
    assert_eq!(fmt("linebreak Periodisch"), "linebreak Periodisch");
    assert_eq!(fmt("a punkt B punkt C"), "a. B. C");
    assert_eq!(fmt("punkt_land"), "punkt_land");
    assert_eq!(fmt("questionnaire"), "questionnaire");
}

#[test]
fn proper_nouns_preserved() {
    assert_eq!(fmt("München Zürich Wien"), "München Zürich Wien");
    assert_eq!(
        fmt("Frau Müller und d'Artagnan"),
        "Frau Müller und d'Artagnan"
    );
    assert_eq!(fmt("Die Münchner Straße"), "Die Münchner Straße");
    // Doku: Groß-/Kleinschreibung wird ignoriert, daher werden auch
    // satzanfängliche Befehlswörter umgewandelt (bewusste Grenze).
    // Der Abstand vor dem Befehlswort gehört zum Befehl und wird
    // umgewandelt, daher klebt das Zeichen an den vorherigen Wortbestand.
    assert_eq!(fmt("Punkt gesagt, Punkt getan"), ". gesagt,. getan");
}

#[test]
fn quoted_spans_are_protected() {
    assert_eq!(
        fmt("Er sagte \"neue Zeile\" laut"),
        "Er sagte \"neue Zeile\" laut"
    );
    assert_eq!(
        fmt("Zitat „neuer Absatz“ Ende"),
        "Zitat „neuer Absatz“ Ende"
    );
    assert_eq!(fmt("sagt 'punkt' hier"), "sagt 'punkt' hier");
    assert_eq!(fmt("Er sagte \"punkt"), "Er sagte \"punkt");
    assert_eq!(
        fmt("Zitat \"'neue Zeile' und Punkt\" komma Ende"),
        "Zitat \"'neue Zeile' und Punkt\", Ende"
    );
}

#[test]
fn code_spans_are_protected() {
    assert_eq!(fmt("Nutze `punkt` jetzt"), "Nutze `punkt` jetzt");
    assert_eq!(fmt("`neue Zeile` und `komma`"), "`neue Zeile` und `komma`");
    assert_eq!(
        fmt("```\npunkt neue Zeile\n```"),
        "```\npunkt neue Zeile\n```"
    );
    assert_eq!(
        fmt("anführungszeichen auf `punkt` anführungszeichen zu"),
        "\"`punkt`\""
    );
}

#[test]
fn literal_mode_protects_spans() {
    assert_eq!(
        fmt("Anfang literalmodus an neue Zeile komma literalmodus aus Punkt Ende"),
        "Anfang neue Zeile komma. Ende"
    );
    assert_eq!(
        fmt("start literal mode on new line comma literal mode off period end"),
        "start new line comma. end"
    );
    assert_eq!(fmt("text literalmodus an neue Zeile"), "text neue Zeile");
    assert_eq!(
        fmt("text literalmodus aus Ende"),
        "text literalmodus aus Ende"
    );
    assert_eq!(fmt("anführungszeichen auf neue Zeile"), "\"neue Zeile");
}

#[test]
fn spoken_text_never_triggers_os_actions() {
    assert_eq!(fmt("Drücke Enter jetzt"), "Drücke Enter jetzt");
    assert_eq!(fmt("Alt F4 und Strg C"), "Alt F4 und Strg C");
    assert_eq!(fmt("alles löschen"), "alles löschen");
    assert_eq!(fmt("sudo rm -rf /"), "sudo rm -rf /");
    // Ein Zeilenumbruch ist nur ein Zeichen im Textpuffer, keine Aktion.
    assert_eq!(fmt("lösche alles neue Zeile sudo"), "lösche alles\nsudo");
    let out = fmt("Enter alles löschen sudo rm -rf /");
    assert!(!out.contains(|c: char| c.is_control() && c != '\n'));
}

#[test]
fn full_german_and_english_sentences() {
    assert_eq!(
        fmt("Hallo komma wie geht es Ihnen fragezeichen neuer Absatz Ich wohne in München Punkt"),
        "Hallo, wie geht es Ihnen?\n\nIch wohne in München."
    );
    assert_eq!(
        fmt(
            "Die Bestellung 123 kostet 49,90 Euro am 12.04.2026 neue Zeile Versand nach Wien punkt"
        ),
        "Die Bestellung 123 kostet 49,90 Euro am 12.04.2026\nVersand nach Wien."
    );
    assert_eq!(
        fmt(
            "Hello comma this is a test question mark new paragraph The price is fifty Euro period"
        ),
        "Hello, this is a test?\n\nThe price is fifty Euro."
    );
    assert_eq!(
        fmt("Meeting on 2026-11-09 line break room 4B period"),
        "Meeting on 2026-11-09\nroom 4B."
    );
}
