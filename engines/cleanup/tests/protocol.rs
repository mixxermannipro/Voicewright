use std::{
    io::Write,
    path::Path,
    process::{Command, Stdio},
};

use serde_json::{json, Value};

fn run(request: &[u8]) -> Value {
    let mut child = Command::new(env!("CARGO_BIN_EXE_voxtakt-cleanup"))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    child.stdin.take().unwrap().write_all(request).unwrap();
    let output = child.wait_with_output().unwrap();
    assert!(output.status.success());
    assert!(output.stderr.is_empty());
    serde_json::from_slice(&output.stdout).unwrap()
}

#[test]
fn rejects_invalid_json_without_echoing_the_input() {
    let response = run(br#"{ "transcript": "TEST SECRET" } garbage"#);
    assert!(response["error"].is_string());
    assert!(!response.to_string().contains("TEST SECRET"));
    assert!(response.get("text").is_none());
}

#[test]
fn rejects_oversized_input() {
    let response = run(&vec![b' '; 256 * 1024 + 1]);
    assert_eq!(response["error"], "Anfrage zu groß.");
}

#[test]
fn rejects_relative_paths() {
    let request = json!({"model": "not-absolute.gguf", "system": "Edit.", "transcript": "Hello"});
    let response = run(request.to_string().as_bytes());
    assert_eq!(response["error"], "Wähle eine lokale GGUF-Datei aus.");
}

#[test]
#[ignore = "requires the pinned Qwen3-0.6B-Q8_0.gguf via VOXTAKT_TEST_GGUF"]
fn cleans_english_and_german_with_local_weights() {
    let model = std::env::var_os("VOXTAKT_TEST_GGUF").expect("provide absolute model path");
    for (transcript, expected) in [
        (
            "um Berlin is the capital of Germany",
            "Berlin is the capital of Germany",
        ),
        (
            "äh München ist eine Stadt in Bayern",
            "München ist eine Stadt in Bayern",
        ),
    ] {
        let request = json!({
            "model": Path::new(&model),
            "system": "Correct this dictated text and remove filler words. Preserve its original language and names. Return only the corrected text.",
            "transcript": transcript
        });
        let response = run(request.to_string().as_bytes());
        let text = response["text"]
            .as_str()
            .unwrap_or_else(|| panic!("{response}"));
        assert!(text.contains(expected), "{text}");
        let start = text.trim_start().to_lowercase();
        assert!(
            !start.starts_with("um ") && !start.starts_with("äh "),
            "{text}"
        );
    }
}
