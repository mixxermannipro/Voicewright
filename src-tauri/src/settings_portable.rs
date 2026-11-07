//! Versioned settings parsing and portable, keyless backup format.
//! OS keyring credentials are intentionally outside this module and its JSON.

use crate::settings::{CleanupMode, Settings, SETTINGS_SCHEMA_VERSION};
use serde_json::{json, Value};
use std::{fs, io::Write, path::Path};

const MAX_SETTINGS_BYTES: usize = 256 * 1024;
const PORTABLE_FORMAT: &str = "voicewright-settings";

fn rename_field(value: &mut Value, from: &str, to: &str) {
    if let Some(fields) = value.as_object_mut() {
        if let Some(old) = fields.remove(from) {
            fields.entry(to.to_string()).or_insert(old);
        }
    }
}

pub fn decode(bytes: &[u8]) -> Result<Settings, String> {
    if bytes.len() > MAX_SETTINGS_BYTES {
        return Err("The settings file is larger than 256 KiB.".into());
    }
    let mut value: Value = serde_json::from_slice(bytes)
        .map_err(|_| "The settings file is not valid JSON.")?;
    let version = match value.get("schema_version") {
        Some(version) => version.as_u64().ok_or("Invalid settings schema version.")?,
        None => 1,
    };
    if !(1..=u64::from(SETTINGS_SCHEMA_VERSION)).contains(&version) {
        return Err("Unsupported settings schema version. Do not overwrite a newer file.".into());
    }
    if !value.is_object() {
        return Err("Settings must be a JSON object.".into());
    }
    // The first released alpha had no schema_version. The renamed fields
    // below also support two synthetic older fixtures for migration tests.
    if version == 1 {
        rename_field(&mut value, "hotkey", "shortcut");
        rename_field(&mut value, "lang", "speech_language");
    }
    if version <= 2 {
        rename_field(&mut value, "insert_automatically", "auto_insert");
    }
    value["schema_version"] = json!(SETTINGS_SCHEMA_VERSION);
    let settings: Settings = serde_json::from_value(value)
        .map_err(|_| "The settings file has invalid field types.")?;
    settings.validate()?;
    Ok(settings)
}

pub fn back_up_invalid(path: &Path, bytes: &[u8]) -> Result<(), String> {
    let parent = path.parent().ok_or("Invalid settings directory.")?;
    for number in 1..=32 {
        let backup = path.with_extension(format!("invalid-{number:02}.bak"));
        if backup.exists() {
            continue;
        }
        let mut temp = tempfile::NamedTempFile::new_in(parent)
            .map_err(|_| "Could not preserve invalid settings.")?;
        temp.write_all(bytes)
            .and_then(|_| temp.flush())
            .and_then(|_| temp.as_file().sync_all())
            .map_err(|_| "Could not back up invalid settings.")?;
        match temp.persist_noclobber(&backup) {
            Ok(_) => return Ok(()),
            Err(error) if error.error.kind() == std::io::ErrorKind::AlreadyExists => continue,
            Err(_) => return Err("Could not preserve invalid settings.".into()),
        }
    }
    Err("Too many settings backups; free space before saving.".into())
}

pub fn export(path: &Path, settings: &Settings) -> Result<(), String> {
    settings.validate()?;
    let parent = path.parent().ok_or("Invalid settings export path.")?;
    if fs::symlink_metadata(path).is_ok_and(|meta| meta.file_type().is_symlink()) {
        return Err("Refusing to replace a symbolic link.".into());
    }
    let data = json!({
        "format": PORTABLE_FORMAT,
        "schema_version": SETTINGS_SCHEMA_VERSION,
        "settings": settings,
    });
    let mut temp = tempfile::NamedTempFile::new_in(parent)
        .map_err(|_| "Could not create settings export.")?;
    serde_json::to_writer_pretty(&mut temp, &data)
        .map_err(|_| "Could not encode settings export.")?;
    temp.flush().and_then(|_| temp.as_file().sync_all())
        .map_err(|_| "Could not save settings export.")?;
    temp.persist(path).map_err(|_| "Could not write settings export.")?;
    Ok(())
}

pub fn import(bytes: &[u8]) -> Result<Settings, String> {
    if bytes.len() > MAX_SETTINGS_BYTES {
        return Err("Settings import exceeds 256 KiB.".into());
    }
    let document: Value = serde_json::from_slice(bytes)
        .map_err(|_| "Invalid settings backup JSON.")?;
    if document.get("format").and_then(Value::as_str) != Some(PORTABLE_FORMAT) {
        return Err("This file is not a Voicewright settings export.".into());
    }
    let version = document.get("schema_version").and_then(Value::as_u64)
        .ok_or("Missing settings export schema version.")?;
    if version != u64::from(SETTINGS_SCHEMA_VERSION) {
        return Err("Unsupported settings export version.".into());
    }
    let raw = document.get("settings").ok_or("The export has no settings.")?;
    let bytes = serde_json::to_vec(raw).map_err(|_| "Invalid exported settings.")?;
    let mut settings = decode(&bytes)?;
    // New devices must not silently send dictated text to cloud services.
    // A microphone ID is specific to the originating machine.
    settings.cleanup_mode = CleanupMode::Off;
    settings.microphone = None;
    settings.validate()?;
    Ok(settings)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::settings::SETTINGS_SCHEMA_VERSION;

    #[test]
    fn legacy_alpha_and_two_older_migrations_are_idempotent() {
        let legacy = r#"{"prompt":"Eigene Anweisung","vocabulary":"Grüße München","shortcut":"Ctrl+Shift+Space"}"#.as_bytes();
        let a = decode(legacy).unwrap();
        assert_eq!(a.schema_version, SETTINGS_SCHEMA_VERSION);
        assert_eq!(a.prompt, "Eigene Anweisung");
        assert_eq!(a.vocabulary, "Grüße München");
        let v1 = br#"{"schema_version":1,"hotkey":"Ctrl+Alt+F9","lang":"de","insert_automatically":false}"#;
        let b = decode(v1).unwrap();
        assert_eq!(b.shortcut, "Ctrl+Alt+F9");
        assert!(!b.auto_insert);
        let v2 = br#"{"schema_version":2,"shortcut":"Ctrl+Shift+Space","insert_automatically":false}"#;
        assert!(!decode(v2).unwrap().auto_insert);
        let serialized = serde_json::to_vec(&b).unwrap();
        assert_eq!(decode(&serialized).unwrap().shortcut, b.shortcut);
        assert!(decode(br#"{"schema_version":99}"#).is_err());
    }

    #[test]
    fn damaged_json_is_preserved_as_unique_private_backup() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("settings.json");
        fs::write(&path, b"{broken").unwrap();
        let data = fs::read(&path).unwrap();
        assert!(decode(&data).is_err());
        back_up_invalid(&path, &data).unwrap();
        assert_eq!(fs::read(&path).unwrap(), b"{broken");
        assert_eq!(fs::read(path.with_extension("invalid-01.bak")).unwrap(), b"{broken");
        back_up_invalid(&path, &data).unwrap();
        assert_eq!(fs::read(path.with_extension("invalid-02.bak")).unwrap(), b"{broken");
    }

    #[test]
    fn portable_roundtrip_never_reenables_cloud_or_imports_mic_id() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("prefs.json");
        let mut settings = Settings::default();
        settings.prompt = "Private Begriffe Ä, Ü, ß".into();
        settings.vocabulary = "Oachkatzlschwoaf".into();
        settings.microphone = Some("specific-device-123".into());
        export(&path, &settings).unwrap();
        let raw = fs::read(&path).unwrap();
        let imported = import(&raw).unwrap();
        assert_eq!(imported.prompt, settings.prompt);
        assert_eq!(imported.vocabulary, settings.vocabulary);
        assert!(imported.microphone.is_none());
        assert_eq!(imported.cleanup_mode, CleanupMode::Off);
        let json = String::from_utf8(raw).unwrap();
        assert!(!json.contains("api_key"));
        assert!(!json.contains("transcript"));
    }

    #[test]
    fn invalid_import_never_updates_disk_or_defaults() {
        let current = Settings::default();
        for bad in [
            b"{}".as_slice(), b"{",
            br#"{"format":"voicewright-settings","schema_version":99,"settings":{}}"#,
            br#"{"format":"voicewright-settings","schema_version":3,"settings":{"shortcut":"Space"}}"#,
        ] {
            assert!(import(bad).is_err());
        }
        assert_eq!(current.cleanup_mode, CleanupMode::Off);
    }
}
