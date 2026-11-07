//! Pure, opt-in formatting of explicit spoken punctuation.
//! This module only rewrites a text buffer. No keypresses or OS commands.

#[derive(Clone, Copy, PartialEq, Eq)]
enum Command {
    Mark(char),
    Line,
    Paragraph,
    QuoteOpen,
    QuoteClose,
    LiteralOn,
    LiteralOff,
}

// Deliberately small dictionary. Never add general-purpose or destructive actions.
// Each match requires Unicode word boundaries; case folding is Unicode-aware.
const COMMANDS: &[(&str, Command)] = &[
    ("anführungszeichen auf", Command::QuoteOpen),
    ("anführungszeichen zu", Command::QuoteClose),
    ("literalmodus an", Command::LiteralOn),
    ("literalmodus aus", Command::LiteralOff),
    ("literal mode on", Command::LiteralOn),
    ("literal mode off", Command::LiteralOff),
    ("new paragraph", Command::Paragraph),
    ("neuer absatz", Command::Paragraph),
    ("neue zeile", Command::Line),
    ("new line", Command::Line),
    ("line break", Command::Line),
    ("open quote", Command::QuoteOpen),
    ("close quote", Command::QuoteClose),
    ("ausrufezeichen", Command::Mark('!')),
    ("exclamation mark", Command::Mark('!')),
    ("fragezeichen", Command::Mark('?')),
    ("question mark", Command::Mark('?')),
    ("doppelpunkt", Command::Mark(':')),
    ("semicolon", Command::Mark(';')),
    ("semikolon", Command::Mark(';')),
    ("full stop", Command::Mark('.')),
    ("period", Command::Mark('.')),
    ("komma", Command::Mark(',')),
    ("comma", Command::Mark(',')),
    ("punkt", Command::Mark('.')),
    ("colon", Command::Mark(':')),
];

fn word(c: char) -> bool {
    c.is_alphanumeric() || c == '_'
}

fn rule_at(text: &str, at: usize) -> Option<(usize, Command)> {
    let before = text[..at].chars().next_back();
    if before.is_some_and(word) {
        return None;
    }
    COMMANDS.iter().find_map(|(phrase, action)| {
        let end = at.checked_add(phrase.len())?;
        let candidate = text.get(at..end)?;
        if candidate.to_lowercase() != *phrase || text[end..].chars().next().is_some_and(word) {
            return None;
        }
        Some((end, *action))
    })
}

fn trim_inline_space(output: &mut String) {
    while output.ends_with(' ') || output.ends_with('\t') {
        output.pop();
    }
}

fn skip_inline_space(text: &str, mut at: usize) -> usize {
    while let Some(next) = text[at..].chars().next() {
        if next != ' ' && next != '\t' {
            break;
        }
        at += next.len_utf8();
    }
    at
}

/// Returns the input unchanged unless the user enabled spoken formatting.
/// Quoted and backtick-delimited spans are preserved. Explicit literal-mode
/// markers additionally protect a span of normal text until its closing marker.
pub fn format(text: &str, enabled: bool) -> String {
    if !enabled || text.is_empty() {
        return text.to_owned();
    }
    let mut result = String::with_capacity(text.len());
    let mut pos = 0;
    let mut in_code = false;
    // Track the expected closing character so nested quotes do not expose
    // text to command replacement.
    let mut in_quote: Option<char> = None;
    let mut in_spoken_quote = false;
    let mut in_literal = false;

    while pos < text.len() {
        let current = text[pos..].chars().next().expect("char boundary");
        let prev = text[..pos].chars().next_back();
        let next = text[pos + current.len_utf8()..].chars().next();

        // Inline code and fenced Markdown use backtick parity. Both are literal.
        if current == '`' && in_quote.is_none() && !in_spoken_quote && !in_literal {
            in_code = !in_code;
            result.push(current);
            pos += current.len_utf8();
            continue;
        }
        // Treat straight/smart quotes and stand-alone single quotes as literal.
        // Apostrophes inside words (don't / d'Artagnan) do not toggle quoting.
        let quote_delimiter = matches!(current, '"' | '„' | '“' | '”')
            || (current == '\'' && !(prev.is_some_and(word) && next.is_some_and(word)));
        if quote_delimiter && !in_code && !in_spoken_quote && !in_literal {
            match in_quote {
                Some(closer) if current == closer => in_quote = None,
                None => {
                    in_quote = Some(match current {
                        '„' => '“',
                        '“' => '”',
                        other => other,
                    });
                }
                _ => {}
            }
            result.push(current);
            pos += current.len_utf8();
            continue;
        }

        if !in_code && in_quote.is_none() {
            if let Some((end, command)) = rule_at(text, pos) {
                if in_literal {
                    if command == Command::LiteralOff {
                        trim_inline_space(&mut result);
                        pos = end;
                        in_literal = false;
                        continue;
                    }
                } else if in_spoken_quote {
                    if command == Command::QuoteClose {
                        trim_inline_space(&mut result);
                        result.push('"');
                        pos = end;
                        in_spoken_quote = false;
                        continue;
                    }
                } else {
                    match command {
                        Command::Mark(mark) => {
                            trim_inline_space(&mut result);
                            result.push(mark);
                            pos = end;
                            continue;
                        }
                        Command::Line | Command::Paragraph => {
                            trim_inline_space(&mut result);
                            result.push('\n');
                            if command == Command::Paragraph {
                                result.push('\n');
                            }
                            pos = skip_inline_space(text, end);
                            continue;
                        }
                        Command::QuoteOpen => {
                            result.push('"');
                            pos = skip_inline_space(text, end);
                            in_spoken_quote = true;
                            continue;
                        }
                        Command::LiteralOn => {
                            pos = skip_inline_space(text, end);
                            in_literal = true;
                            continue;
                        }
                        Command::QuoteClose | Command::LiteralOff => {
                            // A closing marker with no opening marker is literal.
                        }
                    }
                }
            }
        }

        result.push(current);
        pos += current.len_utf8();
    }
    result
}

#[cfg(test)]
mod tests {
    use super::format;

    #[test]
    fn feature_is_off_by_default_and_preserves_exact_text() {
        let raw = "Hallo Komma neue Zeile Äpfel 12.04.2026, Oachkatzlschwoaf";
        assert_eq!(format(raw, false), raw);
        assert_eq!(format("", true), "");
    }

    #[test]
    fn german_punctuation_and_paragraphs() {
        assert_eq!(
            format("Hallo komma Welt ausrufezeichen neuer Absatz München punkt", true),
            "Hallo, Welt!\n\nMünchen."
        );
        assert_eq!(
            format("Betrag 50 Euro doppelpunkt neue Zeile 12.04.2026 fragezeichen", true),
            "Betrag 50 Euro:\n12.04.2026?"
        );
    }

    #[test]
    fn english_commands_and_mixed_language() {
        assert_eq!(
            format("Hello comma Welt exclamation mark new paragraph Grüße full stop", true),
            "Hello, Welt!\n\nGrüße."
        );
        assert_eq!(format("Yes semicolon no colon maybe", true), "Yes; no: maybe");
    }

    #[test]
    fn boundaries_dont_rewrite_words_names_or_numbers() {
        let source = "Punktland, Kommaplatz, newline, 42, 2026-11-07 und München";
        assert_eq!(format(source, true), source);
        assert_eq!(format("A punkt B punkt C", true), "A. B. C");
    }

    #[test]
    fn quotations_code_and_literal_mode_are_protected() {
        assert_eq!(
            format("Er sagt \"neue Zeile\" und schreibt `punkt` komma fertig", true),
            "Er sagt \"neue Zeile\" und schreibt `punkt`, fertig"
        );
        assert_eq!(
            format("Zitat „neuer Absatz“ neue Zeile Text", true),
            "Zitat „neuer Absatz“\nText"
        );
        assert_eq!(
            format("Zitat \"'neue Zeile' und Punkt\" komma Ende", true),
            "Zitat \"'neue Zeile' und Punkt\", Ende"
        );
        assert_eq!(
            format("Code literalmodus an neue Zeile komma literalmodus aus Punkt", true),
            "Code neue Zeile komma."
        );
        assert_eq!(
            format("Er sagt anführungszeichen auf neue Zeile komma anführungszeichen zu punkt", true),
            "Er sagt \"neue Zeile komma\"."
        );
    }

    #[test]
    fn no_os_actions_and_no_numeric_rewrites() {
        assert_eq!(
            format("lösche alles Enter Alt F4 sudo rm -rf /", true),
            "lösche alles Enter Alt F4 sudo rm -rf /"
        );
        assert_eq!(
            format("Ticket 4B kostet 50, nicht 15 Euro, am 21.11.2005", true),
            "Ticket 4B kostet 50, nicht 15 Euro, am 21.11.2005"
        );
    }
}
