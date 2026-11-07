mod inference;

use std::{
    io::{self, Read, Write},
    path::PathBuf,
    process::ExitCode,
};

use serde::{Deserialize, Serialize};

const MAX_REQUEST_BYTES: usize = 256 * 1024;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    model: PathBuf,
    system: String,
    transcript: String,
}

#[derive(Serialize)]
#[serde(untagged)]
enum Response {
    Text { text: String },
    Error { error: &'static str },
}

fn read_request(input: impl Read) -> Result<Request, &'static str> {
    let mut input = input.take(MAX_REQUEST_BYTES as u64 + 1);
    let mut bytes = Vec::new();
    input
        .read_to_end(&mut bytes)
        .map_err(|_| "Anfrage konnte nicht gelesen werden.")?;
    if bytes.len() > MAX_REQUEST_BYTES {
        return Err("Anfrage zu groß.");
    }
    serde_json::from_slice(&bytes).map_err(|_| "Ungültige Anfrage.")
}

fn main() -> ExitCode {
    let response = match read_request(io::stdin().lock()).and_then(inference::cleanup) {
        Ok(text) => Response::Text { text },
        Err(error) => Response::Error { error },
    };
    let mut output = io::stdout().lock();
    if serde_json::to_writer(&mut output, &response).is_err() || output.flush().is_err() {
        return ExitCode::FAILURE;
    }
    ExitCode::SUCCESS
}
