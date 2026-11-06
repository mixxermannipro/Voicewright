use reqwest::{header, redirect, Client, StatusCode};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    fs::{self, File},
    io::{self, Read, Write},
    path::{Path, PathBuf},
    sync::atomic::{AtomicBool, Ordering},
    time::Duration,
};
use tokio::io::AsyncWriteExt;

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum Kind {
    Speech,
    Cleanup,
}

#[derive(Clone, Copy, Serialize)]
pub struct Model {
    id: &'static str,
    name: &'static str,
    kind: Kind,
    file: &'static str,
    url: &'static str,
    bytes: u64,
    sha256: &'static str,
    license: &'static str,
    ram_gib: u8,
}

macro_rules! whisper {
    ($id:literal, $name:literal, $file:literal, $bytes:literal, $hash:literal, $ram:literal) => {
        Model { id: $id, name: $name, kind: Kind::Speech, file: $file, bytes: $bytes, sha256: $hash,
            url: concat!("https://huggingface.co/ggerganov/whisper.cpp/resolve/5359861c739e955e79d9a303bcbc70fb988958b1/", $file),
            license: "MIT", ram_gib: $ram }
    };
}

pub const CATALOG: &[Model] = &[
    whisper!("whisper-tiny", "Whisper Tiny", "ggml-tiny.bin", 77691713, "be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21", 2),
    whisper!("whisper-base", "Whisper Base", "ggml-base.bin", 147951465, "60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe", 2),
    whisper!("whisper-small", "Whisper Small", "ggml-small.bin", 487601967, "1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b", 3),
    whisper!("whisper-medium", "Whisper Medium", "ggml-medium.bin", 1533763059, "6c14d5adee5f86394037b4e4e8b59f1673b6cee10e3cf0b11bbdbee79c156208", 5),
    whisper!("whisper-turbo", "Whisper Large-v3 Turbo", "ggml-large-v3-turbo.bin", 1624555275, "1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69", 5),
    whisper!("whisper-large", "Whisper Large-v3", "ggml-large-v3.bin", 3095033483, "64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2", 8),
    Model {
        id: "qwen3-0.6b-q8", name: "Qwen3 0.6B Q8_0", kind: Kind::Cleanup,
        file: "Qwen3-0.6B-Q8_0.gguf",
        url: "https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/resolve/23749fefcc72300e3a2ad315e1317431b06b590a/Qwen3-0.6B-Q8_0.gguf",
        bytes: 639446688, sha256: "9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031",
        license: "Apache-2.0", ram_gib: 3,
    },
];

pub fn catalog_entry(id: &str) -> Result<&'static Model, String> {
    CATALOG
        .iter()
        .find(|entry| entry.id == id)
        .ok_or_else(|| "Unknown catalog model.".into())
}

fn imported(kind: Kind) -> (&'static str, &'static str, &'static [u8; 4], u64) {
    match kind {
        Kind::Speech => (
            "imported-speech",
            "imported-whisper.bin",
            b"lmgg",
            4 * 1024 * 1024 * 1024,
        ),
        Kind::Cleanup => (
            "imported-cleanup",
            "imported-cleanup.gguf",
            b"GGUF",
            2 * 1024 * 1024 * 1024,
        ),
    }
}

fn kind_of(id: &str) -> Result<Kind, String> {
    for kind in [Kind::Speech, Kind::Cleanup] {
        if imported(kind).0 == id {
            return Ok(kind);
        }
    }
    catalog_entry(id).map(|entry| entry.kind)
}

pub fn valid_id(id: &str, kind: Kind) -> bool {
    kind_of(id).is_ok_and(|current| current == kind)
}

const HEADER_BYTES: usize = 24;
const MIN_MODEL_BYTES: u64 = 1024;
const MAX_HEADER_ENTRIES: u64 = 1_000_000;

fn invalid_model(message: &str) -> String {
    format!("{message} Download or import the model again.")
}

fn validate_header(kind: Kind, header: &[u8; HEADER_BYTES], size: u64) -> Result<(), String> {
    let magic = &header[..4];
    match kind {
        Kind::Speech => {
            if magic != b"lmgg" {
                return Err(if magic == b"GGUF" {
                    "This is a GGUF file. Whisper needs a GGML model.".into()
                } else {
                    "The model has the wrong file format.".into()
                });
            }
            let vocabulary = i32::from_le_bytes(header[4..8].try_into().unwrap());
            if !(1_000..=1_000_000).contains(&vocabulary) {
                return Err("The Whisper model header is invalid.".into());
            }
        }
        Kind::Cleanup => {
            if magic != b"GGUF" {
                return Err(if magic == b"lmgg" {
                    "This is a Whisper GGML file. Local cleanup needs a GGUF model.".into()
                } else {
                    "The model has the wrong file format.".into()
                });
            }
            let version = u32::from_le_bytes(header[4..8].try_into().unwrap());
            if !(1..=3).contains(&version) {
                return Err("The GGUF model version is not supported.".into());
            }
            let tensors = u64::from_le_bytes(header[8..16].try_into().unwrap());
            let metadata = u64::from_le_bytes(header[16..24].try_into().unwrap());
            if tensors == 0 || tensors > MAX_HEADER_ENTRIES || metadata > MAX_HEADER_ENTRIES {
                return Err("The GGUF model header is invalid.".into());
            }
            let minimum = (HEADER_BYTES as u64)
                .saturating_add(tensors.saturating_mul(24))
                .saturating_add(metadata.saturating_mul(12));
            if size < minimum {
                return Err("The model file is incomplete or truncated.".into());
            }
        }
    }
    Ok(())
}

fn final_path(root: &Path, id: &str) -> Result<PathBuf, String> {
    for kind in [Kind::Speech, Kind::Cleanup] {
        let (imported_id, file, _, _) = imported(kind);
        if imported_id == id {
            return Ok(root.join(file));
        }
    }
    Ok(root.join(catalog_entry(id)?.file))
}

pub fn ready(root: &Path, id: &str) -> Result<PathBuf, String> {
    let path = final_path(root, id)?;
    let metadata =
        fs::symlink_metadata(&path).map_err(|_| "Download or import the selected model first.")?;
    if !metadata.is_file() {
        return Err(invalid_model("The model file is invalid."));
    }
    let kind = kind_of(id)?;
    if let Ok(entry) = catalog_entry(id) {
        if metadata.len() != entry.bytes {
            return Err(invalid_model("The model file is invalid."));
        }
    } else {
        let (_, _, _, limit) = imported(kind);
        if !(MIN_MODEL_BYTES..=limit).contains(&metadata.len()) {
            return Err(invalid_model("The model file is invalid."));
        }
    }
    let mut file = File::open(&path).map_err(|_| invalid_model("The model file is invalid."))?;
    let mut header = [0; HEADER_BYTES];
    file.read_exact(&mut header)
        .map_err(|_| invalid_model("The model file is invalid."))?;
    validate_header(kind, &header, metadata.len())?;
    Ok(path)
}

pub fn installed(root: &Path) -> Vec<String> {
    CATALOG
        .iter()
        .map(|entry| entry.id)
        .chain([imported(Kind::Speech).0, imported(Kind::Cleanup).0])
        .filter(|id| ready(root, id).is_ok())
        .map(str::to_owned)
        .collect()
}

pub fn remove(root: &Path, id: &str) -> Result<(), String> {
    let path = final_path(root, id)?;
    for file in [path.clone(), path.with_extension("part")] {
        match fs::remove_file(file) {
            Ok(()) => {}
            Err(error) if error.kind() == io::ErrorKind::NotFound => {}
            Err(_) => return Err("Could not delete the model file.".into()),
        }
    }
    Ok(())
}

pub fn import(root: &Path, source: &Path, kind: Kind) -> Result<(), String> {
    let (_, file, _, limit) = imported(kind);
    let metadata = fs::metadata(source).map_err(|_| "Could not open the model file.")?;
    if !metadata.is_file() || !(MIN_MODEL_BYTES..=limit).contains(&metadata.len()) {
        return Err("Model size is outside the supported range.".into());
    }
    let mut input = File::open(source).map_err(|_| "Could not open the model file.")?;
    let mut header = [0; HEADER_BYTES];
    input
        .read_exact(&mut header)
        .map_err(|_| "Could not read the model header.")?;
    validate_header(kind, &header, metadata.len())?;
    fs::create_dir_all(root).map_err(|_| "Could not create the model folder.")?;
    let mut destination =
        tempfile::NamedTempFile::new_in(root).map_err(|_| "Could not write the imported model.")?;
    destination
        .write_all(&header)
        .map_err(|_| "Could not write the imported model.")?;
    let bytes = io::copy(
        &mut input.take(limit - HEADER_BYTES as u64),
        &mut destination,
    )
    .map_err(|_| "Could not copy the model.")?;
    if bytes + HEADER_BYTES as u64 != metadata.len() {
        return Err("The imported file changed while copying.".into());
    }
    destination
        .as_file()
        .sync_all()
        .map_err(|_| "Could not save the imported model.")?;
    destination
        .persist(root.join(file))
        .map_err(|_| "Could not install the imported model.")?;
    Ok(())
}

fn trusted_url(url: &reqwest::Url) -> bool {
    url.scheme() == "https"
        && url.host_str().is_some_and(|host| {
            host == "huggingface.co"
                || host.ends_with(".huggingface.co")
                || host.ends_with(".hf.co")
        })
}

fn matches_hash(input: impl Read, model: &Model, cancel: &AtomicBool) -> Result<bool, String> {
    let mut input = input.take(model.bytes + 1);
    let mut hash = Sha256::new();
    let mut bytes = 0_u64;
    let mut buffer = vec![0; 128 * 1024];
    loop {
        if cancel.load(Ordering::Relaxed) {
            return Err("Download cancelled.".into());
        }
        let count = input
            .read(&mut buffer)
            .map_err(|_| "Could not read the downloaded model.")?;
        if count == 0 {
            break;
        }
        bytes += count as u64;
        hash.update(&buffer[..count]);
    }
    Ok(bytes == model.bytes && format!("{:x}", hash.finalize()) == model.sha256)
}

pub async fn download(
    root: &Path,
    id: &str,
    cancel: std::sync::Arc<AtomicBool>,
    progress: impl Fn(u64, u64),
) -> Result<(), String> {
    let model = catalog_entry(id)?;
    tokio::fs::create_dir_all(root)
        .await
        .map_err(|_| "Could not create the model folder.")?;
    let destination = root.join(model.file);
    let partial = destination.with_extension("part");
    let existing = tokio::fs::symlink_metadata(&partial).await.ok();
    if existing
        .as_ref()
        .is_some_and(|metadata| !metadata.is_file())
    {
        return Err("The partial model path is invalid.".into());
    }
    let mut offset = existing.map_or(0, |metadata| metadata.len());
    if offset > model.bytes {
        offset = 0;
    }
    progress(offset, model.bytes);
    if offset != model.bytes {
        let client = Client::builder()
            .https_only(true)
            .connect_timeout(Duration::from_secs(15))
            .read_timeout(Duration::from_secs(25))
            .redirect(redirect::Policy::custom(|attempt| {
                if attempt.previous().len() < 6 && trusted_url(attempt.url()) {
                    attempt.follow()
                } else {
                    attempt.error("Untrusted model redirect")
                }
            }))
            .build()
            .map_err(|_| "Could not create a model connection.")?;
        let mut request = client.get(model.url);
        if offset > 0 {
            request = request.header(header::RANGE, format!("bytes={offset}-"));
        }
        let mut response = request
            .send()
            .await
            .map_err(|_| "Could not connect to the model server.")?;
        match response.status() {
            StatusCode::OK => offset = 0,
            StatusCode::PARTIAL_CONTENT if offset > 0 => {
                let expected = format!("bytes {}-{}/{}", offset, model.bytes - 1, model.bytes);
                if response
                    .headers()
                    .get(header::CONTENT_RANGE)
                    .and_then(|value| value.to_str().ok())
                    != Some(expected.as_str())
                {
                    return Err("The model server returned an unexpected range.".into());
                }
            }
            _ => return Err("The model server did not accept the download.".into()),
        }
        let mut output = tokio::fs::OpenOptions::new()
            .write(true)
            .create(true)
            .append(offset > 0)
            .truncate(offset == 0)
            .open(&partial)
            .await
            .map_err(|_| "Could not write the model. Check disk space.")?;
        loop {
            if cancel.load(Ordering::Relaxed) {
                return Err("Download cancelled.".into());
            }
            let Some(chunk) = response
                .chunk()
                .await
                .map_err(|_| "The model download was interrupted. Restart it to resume.")?
            else {
                break;
            };
            offset += chunk.len() as u64;
            if offset > model.bytes {
                return Err("The model server exceeded the expected size.".into());
            }
            output
                .write_all(&chunk)
                .await
                .map_err(|_| "Could not write the model. Check disk space.")?;
            progress(offset, model.bytes);
        }
        output
            .sync_all()
            .await
            .map_err(|_| "Could not save the model download.")?;
    }
    if offset != model.bytes {
        return Err("The model download is incomplete. Restart it to resume.".into());
    }
    let checked_file = partial.clone();
    let check_cancel = cancel.clone();
    let valid = tokio::task::spawn_blocking(move || {
        let input = File::open(checked_file).map_err(|_| "Could not open the downloaded model.")?;
        matches_hash(input, model, &check_cancel)
    })
    .await
    .map_err(|_| "The checksum check stopped unexpectedly.")??;
    if !valid {
        tokio::fs::remove_file(&partial)
            .await
            .map_err(|_| "Checksum mismatch. Could not remove the partial file.")?;
        return Err("The downloaded model failed its checksum check.".into());
    }
    if cancel.load(Ordering::Relaxed) {
        return Err("Download cancelled.".into());
    }
    tokio::fs::rename(&partial, &destination)
        .await
        .map_err(|_| "Could not install the verified model.")?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn only_recognizes_known_model_ids_and_exact_integrity() {
        let model = Model {
            bytes: 3,
            sha256: "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            ..CATALOG[0]
        };
        let cancel = AtomicBool::new(false);
        assert!(matches_hash(&b"abc"[..], &model, &cancel).unwrap());
        assert!(!matches_hash(&b"abx"[..], &model, &cancel).unwrap());
        assert!(!matches_hash(&b"abcd"[..], &model, &cancel).unwrap());
        assert!(!valid_id("../../secret", Kind::Speech));
        assert!(!valid_id(CATALOG[0].id, Kind::Cleanup));
    }

    #[test]
    fn partial_model_is_never_available() {
        let root = tempfile::tempdir().unwrap();
        fs::write(root.path().join("ggml-tiny.part"), b"partial").unwrap();
        assert!(installed(root.path()).is_empty());
    }

    fn gguf_header(version: u32, tensors: u64, metadata: u64) -> Vec<u8> {
        let mut header = b"GGUF".to_vec();
        header.extend_from_slice(&version.to_le_bytes());
        header.extend_from_slice(&tensors.to_le_bytes());
        header.extend_from_slice(&metadata.to_le_bytes());
        header
    }

    fn ggml_header(vocabulary: i32) -> Vec<u8> {
        let mut header = b"lmgg".to_vec();
        header.extend_from_slice(&vocabulary.to_le_bytes());
        header
    }

    fn write_source(path: &Path, header: &[u8], size: usize) {
        let mut bytes = vec![0_u8; size];
        bytes[..header.len()].copy_from_slice(header);
        fs::write(path, bytes).unwrap();
    }

    #[test]
    fn imports_models_with_a_valid_structure() {
        let directory = tempfile::tempdir().unwrap();
        let root = directory.path().join("models");
        let speech = directory.path().join("speech.bin");
        write_source(&speech, &ggml_header(51_865), 4096);
        import(&root, &speech, Kind::Speech).unwrap();
        assert!(ready(&root, "imported-speech").is_ok());

        let cleanup = directory.path().join("cleanup.gguf");
        write_source(&cleanup, &gguf_header(3, 1, 1), 4096);
        import(&root, &cleanup, Kind::Cleanup).unwrap();
        assert!(ready(&root, "imported-cleanup").is_ok());
        assert_eq!(
            installed(&root),
            vec!["imported-speech".to_owned(), "imported-cleanup".to_owned()]
        );
    }

    #[test]
    fn rejects_invalid_or_truncated_import_headers() {
        let directory = tempfile::tempdir().unwrap();
        let root = directory.path().join("models");
        let source = directory.path().join("source.gguf");

        for (name, header) in [
            ("version", gguf_header(99, 1, 1)),
            ("tensor count", gguf_header(3, 0, 1)),
            ("metadata count", gguf_header(3, 1, MAX_HEADER_ENTRIES + 1)),
        ] {
            write_source(&source, &header, 4096);
            assert!(import(&root, &source, Kind::Cleanup).is_err(), "{name}");
            assert!(!root.join("imported-cleanup.gguf").exists());
        }

        write_source(&source, &gguf_header(3, 1_000, 1_000), 4096);
        assert!(import(&root, &source, Kind::Cleanup)
            .unwrap_err()
            .contains("truncated"));

        write_source(&source, b"nope", 4096);
        assert!(import(&root, &source, Kind::Cleanup).is_err());

        write_source(&source, &gguf_header(3, 1, 1), 4096);
        let error = import(&root, &source, Kind::Speech).unwrap_err();
        assert!(error.contains("GGUF") && error.contains("GGML"));

        write_source(&source, &ggml_header(51_865), 4096);
        let error = import(&root, &source, Kind::Cleanup).unwrap_err();
        assert!(error.contains("GGML") && error.contains("GGUF"));
    }

    #[test]
    fn damaged_files_are_not_offered_as_installed() {
        let root = tempfile::tempdir().unwrap();
        fs::write(root.path().join("imported-cleanup.gguf"), vec![0_u8; 4096]).unwrap();
        assert!(ready(root.path(), "imported-cleanup").is_err());
        assert!(installed(root.path()).is_empty());

        write_source(
            &root.path().join("imported-whisper.bin"),
            &ggml_header(51_865),
            4096,
        );
        assert!(ready(root.path(), "imported-speech").is_ok());
    }
}
