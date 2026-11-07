//! Conservative validation of optional LLM-edited dictation.
//! Detects protocol leakage and obvious assistant responses, not semantic hallucinations.

const INVALID: &str = "The text editor returned an unsafe or unusable result.";

pub fn validate(source: &str, candidate: String) -> Result<String, String> {
    let trimmed = candidate.trim();
    let lower = trimmed.to_lowercase();
    let assistant_intro = [
        "here is the corrected text:",
        "here's the corrected text:",
        "here is your corrected text:",
        "hier ist der korrigierte text:",
        "hier ist dein korrigierter text:",
        "sure, here is the corrected",
    ];
    let protocol_markers = [
        "<|im_start|>", "<|im_end|>", "<|im_sep|>",
        "<tool_call>", "</tool_call>", "<think>", "</think>",
    ];
    if source.trim().is_empty()
        || trimmed.is_empty()
        || candidate.len() > 128 * 1024
        || candidate.len() > source.len().saturating_mul(4).saturating_add(512)
        || trimmed.starts_with("```")
        || assistant_intro.iter().any(|intro| lower.starts_with(intro))
        || protocol_markers.iter().any(|marker| lower.contains(marker))
        || candidate
            .chars()
            .any(|ch| ch.is_control() && !matches!(ch, '\n' | '\r' | '\t'))
    {
        return Err(INVALID.into());
    }
    Ok(candidate)
}

#[cfg(test)]
mod tests {
    use super::validate;

    #[test]
    fn accepts_multilingual_transcripts_without_rewriting_facts() {
        for (source, edited) in [
            ("äh ich habe nicht 15 sondern 50 Euro bezahlt", "Ich habe nicht 15, sondern 50 Euro bezahlt."),
            ("grüße aus münchen und köln", "Grüße aus München und Köln."),
            ("please do not send 30 dollars to alex", "Please do not send 30 dollars to Alex."),
            ("https://example.org/a?x=1 und ticket 4B", "https://example.org/a?x=1 und Ticket 4B."),
            ("Das ist ein Zitat mit ß und Äpfeln.", "Das ist ein Zitat mit ß und Äpfeln."),
            ("I did not say yes no I said no", "I did not say yes. No, I said no."),
        ] {
            assert_eq!(validate(source, edited.into()), Ok(edited.into()));
        }
    }

    #[test]
    fn rejects_empty_protocol_leakage_and_assistant_preambles() {
        for output in [
            "", "   \n ",
            "Here is the corrected text: Hello.",
            "Hier ist der korrigierte Text: Hallo.",
            "<|im_start|>assistant\nHello",
            "<think>internal</think>Hello",
            "<tool_call>run</tool_call>",
            "a\0b",
            "```markdown\nhello\n```",
        ] {
            assert!(validate("hallo", output.into()).is_err(), "{output:?}");
        }
    }

    #[test]
    fn rejects_runaway_expansion_but_keeps_normal_translations() {
        assert!(validate("hello", "word ".repeat(200)).is_err());
        assert_eq!(validate("Guten Morgen", "Good morning".into()), Ok("Good morning".into()));
    }
}
