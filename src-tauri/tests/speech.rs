#[path = "../src/speech.rs"]
mod speech;

use std::{env, path::Path, sync::atomic::AtomicBool};

#[test]
#[ignore = "requires verified local model and generated fixtures; see docs/TESTING.md"]
fn recognizes_german_and_english_locally() {
    whisper_rs::install_logging_hooks();
    let model = env::var("VOICEWRIGHT_WHISPER_MODEL").unwrap();
    let fixtures = env::var("VOICEWRIGHT_FIXTURES").unwrap();
    for (language, expected) in [("de", "morgen"), ("en", "morning")] {
        let path = Path::new(&fixtures).join(format!("{language}.wav"));
        let mut reader = hound::WavReader::open(path).unwrap();
        assert_eq!(reader.spec().sample_rate, 16_000);
        assert_eq!(reader.spec().channels, 1);
        let samples: Vec<_> = reader
            .samples::<i16>()
            .map(|s| s.unwrap() as f32 / 32768.0)
            .collect();
        let text = speech::transcribe(
            Path::new(&model),
            &samples,
            language,
            "",
            &AtomicBool::new(false),
        )
        .unwrap();
        assert!(text.to_lowercase().contains(expected), "{language}: {text}");
    }
}
