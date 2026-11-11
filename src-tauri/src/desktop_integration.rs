//! Managed Linux autostart and conservative initial window visibility.
use std::{fs, io::Write, path::Path};

pub fn should_show_main(
    complete: bool,
    background: bool,
    tray: bool,
    error: bool,
    explicit: bool,
) -> bool {
    !complete || !background || !tray || error || explicit
}

pub fn set_autostart(config: &Path, executable: &Path, enabled: bool) -> Result<bool, String> {
    const MARKER: &str = "# Managed by Voicewright\n";
    let folder = config.join("autostart");
    let entry = folder.join("de.voicewright.desktop");
    let existing = match fs::symlink_metadata(&entry) {
        Ok(meta) => {
            if !meta.is_file() || meta.file_type().is_symlink() || meta.len() > 65_536 {
                return Err("Refusing to replace an unmanaged autostart entry.".into());
            }
            if !fs::read_to_string(&entry)
                .map_err(|_| "Could not read autostart entry.")?
                .starts_with(MARKER)
            {
                return Err("Refusing to replace an unmanaged autostart entry.".into());
            }
            true
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => false,
        Err(_) => return Err("Could not inspect autostart entry.".into()),
    };
    if !enabled {
        if existing {
            fs::remove_file(entry).map_err(|_| "Could not remove the managed autostart entry.")?;
        }
        return Ok(false);
    }
    let executable = executable
        .canonicalize()
        .map_err(|_| "The autostart executable is missing.")?;
    let path = executable
        .to_str()
        .ok_or("Autostart needs a UTF-8 executable path.")?;
    if !executable.is_file()
        || path.contains("/.mount_")
        || path
            .chars()
            .any(|c| c.is_control() || matches!(c, '"' | '\\' | '$' | '`' | '%'))
    {
        return Err("The executable path cannot be used safely for autostart.".into());
    }
    fs::create_dir_all(&folder).map_err(|_| "Could not create the autostart directory.")?;
    let text = format!("{MARKER}[Desktop Entry]\nType=Application\nName=Voicewright\nExec=\"{path}\" --background\nTerminal=false\nX-GNOME-Autostart-enabled=true\n");
    let mut temp = tempfile::NamedTempFile::new_in(&folder)
        .map_err(|_| "Could not prepare autostart entry.")?;
    temp.write_all(text.as_bytes())
        .and_then(|_| temp.flush())
        .and_then(|_| temp.as_file().sync_all())
        .map_err(|_| "Could not write autostart entry.")?;
    temp.persist(entry)
        .map_err(|_| "Could not install autostart entry.")?;
    Ok(true)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn setup_errors_explicit_requests_and_missing_tray_remain_reachable() {
        for args in [
            (false, true, true, false, false),
            (true, true, false, false, false),
            (true, true, true, true, false),
            (true, true, true, false, true),
            (true, false, true, false, false),
        ] {
            assert!(should_show_main(args.0, args.1, args.2, args.3, args.4));
        }
        assert!(!should_show_main(true, true, true, false, false));
    }

    #[test]
    fn only_owned_autostart_entries_are_written_or_removed() {
        let root = tempfile::tempdir().unwrap();
        let executable = root.path().join("Voicewright AppImage");
        fs::write(&executable, b"test").unwrap();
        assert!(set_autostart(root.path(), &executable, true).unwrap());
        let entry = root.path().join("autostart/de.voicewright.desktop");
        let text = fs::read_to_string(&entry).unwrap();
        assert!(text.starts_with("# Managed by Voicewright\n"));
        assert!(text.contains(" --background\n"));
        assert!(!set_autostart(root.path(), &executable, false).unwrap());
        assert!(!entry.exists());
        fs::write(&entry, b"other user's entry").unwrap();
        assert!(set_autostart(root.path(), &executable, true).is_err());
        assert!(set_autostart(root.path(), &executable, false).is_err());
        assert_eq!(fs::read(entry).unwrap(), b"other user's entry");
    }

    #[test]
    fn a_missing_or_unsafe_executable_cannot_enable_autostart() {
        let root = tempfile::tempdir().unwrap();
        assert!(set_autostart(root.path(), &root.path().join("missing"), true).is_err());
        let path = root.path().join("unsafe%path");
        fs::write(&path, b"test").unwrap();
        assert!(set_autostart(root.path(), &path, true).is_err());
    }
}
