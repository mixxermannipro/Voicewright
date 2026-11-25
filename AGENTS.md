# Voicewright

Voicewright is the Python/PySide6 application in `src/voicewright`. Fedora Linux x86_64 is the release target. The earlier Rust/Tauri implementation is available in Git history.

- Keep speech recognition local. Cloud cleanup and dictation history require opt-in. Store API keys only in the system keyring.
- On Wayland, use the official desktop portals (`GlobalShortcuts` and `RemoteDesktop`) with explicit user consent, or a compositor-managed desktop shortcut (`voicewright --toggle`), with clipboard as fallback. Never require root, raw input device permissions, or `uinput` by default (`ydotool` remains opt-in).
- Use synthetic audio and virtual displays. Never access the owner's microphone or desktop during development.
- Run `python -m pytest -q`, the real Whisper smoke test and the installed-package smoke test documented in the README. Keep the GitHub `check` job required.
- Use a feature branch and a PR. Publish only a verified archive and checksum from the merged commit. Record the actual platform coverage and distinguish virtual testing from a desktop acceptance test.
