//! Explicit, keyboard-only Wayland output probe. Not used by the app.

#[cfg(target_os = "linux")]
#[path = "../src/eis_text.rs"]
mod eis_text;

#[cfg(target_os = "linux")]
mod linux {
    use ashpd::desktop::{
        remote_desktop::{DeviceType, KeyState, RemoteDesktop, SelectDevicesOptions},
        PersistMode,
    };
    use std::{
        path::Path,
        sync::atomic::{AtomicBool, Ordering},
        time::Duration,
    };

    const LINE: &str = "Grüße aus Köln, ÄÖÜ äöü ß 🙂";

    fn requested_devices() -> DeviceType {
        DeviceType::KEYBOARD
    }

    fn ensure_test_target(marker: Option<&Path>) -> Result<(), &'static str> {
        use std::io::Read;
        let Some(marker) = marker else {
            return Ok(());
        };
        let mut bytes = Vec::new();
        let ready = std::fs::File::open(marker)
            .and_then(|file| file.take(16).read_to_end(&mut bytes))
            .is_ok()
            && bytes == b"ready\n";
        if ready {
            Ok(())
        } else {
            Err("Isolated test field is not focused; input stopped")
        }
    }

    fn symbol_events(
        text: &str,
        cancelled: &AtomicBool,
    ) -> Result<Vec<(i32, KeyState)>, &'static str> {
        if cancelled.load(Ordering::Relaxed) {
            return Err("cancelled");
        }
        if text.chars().any(char::is_control) {
            return Err("control characters require a safe paste transport");
        }
        Ok(text
            .chars()
            .flat_map(|character| {
                let value = u32::from(character);
                let keysym = if value <= 0xff {
                    value
                } else {
                    value | 0x0100_0000
                } as i32;
                [(keysym, KeyState::Pressed), (keysym, KeyState::Released)]
            })
            .collect())
    }

    pub async fn run() -> Result<(), &'static str> {
        let mode = std::env::args().nth(1).unwrap_or_default();
        if !matches!(mode.as_str(), "permission" | "keysym" | "utf8") {
            return Err("Use permission (no input), keysym or utf8 (fixed public test). Clipboard transport is not verified yet.");
        }
        if mode == "utf8" {
            crate::eis_text::available()?;
        }
        let remote = RemoteDesktop::new()
            .await
            .map_err(|_| "RemoteDesktop portal unavailable")?;
        let session = remote
            .create_session(Default::default())
            .await
            .map_err(|_| "Could not create portal session")?;
        let result = async {
            remote
                .select_devices(
                    &session,
                    SelectDevicesOptions::default()
                        .set_devices(requested_devices())
                        .set_persist_mode(PersistMode::DoNot),
                )
                .await
                .map_err(|_| "Could not select keyboard-only access")?
                .response()
                .map_err(|_| "Keyboard selection was rejected")?;
            println!("Waiting for desktop approval: keyboard only, no screen or pointer.");
            let started = tokio::time::timeout(
                Duration::from_secs(60),
                remote.start(&session, None, Default::default()),
            )
            .await
            .map_err(|_| "Desktop approval timed out; no input sent")?
            .map_err(|_| "Could not start keyboard portal session")?
            .response()
            .map_err(|_| "Desktop approval was denied or cancelled; no input sent")?;
            if started.devices() != requested_devices() {
                return Err("Desktop did not grant precisely keyboard-only access");
            }
            println!("Keyboard-only session approved.");
            if mode == "permission" {
                println!("Permission probe complete; no input sent.");
                return Ok(());
            }
            if mode == "utf8" {
                let fd = remote
                    .connect_to_eis(&session, Default::default())
                    .await
                    .map_err(|_| "Could not connect to the approved EIS session")?;
                println!("Fixed Unicode text with paragraph in 5 seconds; no keys or clipboard.");
                tokio::time::sleep(Duration::from_secs(5)).await;
                let marker = std::env::var_os("VOICEWRIGHT_PROBE_TARGET");
                return tokio::task::spawn_blocking(move || {
                    let mut client = crate::eis_text::Client::new(fd)?;
                    client.send_text(
                        "Grüße aus Köln, ÄÖÜ äöü ß 🙂\nSecond paragraph.",
                        &AtomicBool::new(false),
                        || ensure_test_target(marker.as_deref().map(Path::new)).is_ok(),
                    )
                })
                .await
                .map_err(|_| "Unicode text worker stopped")?;
            }
            println!(
                "Fixed single-line test in 5 seconds; paragraphs are not tested by keysym mode."
            );
            tokio::time::sleep(Duration::from_secs(5)).await;
            let target_marker = std::env::var_os("VOICEWRIGHT_PROBE_TARGET");
            for (symbol, key_state) in symbol_events(LINE, &AtomicBool::new(false))? {
                if key_state == KeyState::Pressed {
                    ensure_test_target(target_marker.as_deref().map(Path::new))?;
                }
                if remote
                    .notify_keyboard_keysym(&session, symbol, key_state, Default::default())
                    .await
                    .is_err()
                {
                    // Release a possibly pressed key before closing the session.
                    let _ = remote
                        .notify_keyboard_keysym(
                            &session,
                            symbol,
                            KeyState::Released,
                            Default::default(),
                        )
                        .await;
                    return Err("Desktop rejected a keyboard event; output may be partial");
                }
            }
            println!("Keyboard events dispatched; target text must be checked separately.");
            Ok(())
        }
        .await;
        let closed = session.close().await;
        result?;
        closed.map_err(|_| "Could not confirm portal session closure")
    }

    #[cfg(test)]
    mod tests {
        use super::*;

        #[test]
        fn keyboard_only_request() {
            assert_eq!(requested_devices().bits(), 1);
        }

        #[test]
        fn an_unfocused_test_target_prevents_dispatch() {
            let directory = tempfile::tempdir().unwrap();
            let marker = directory.path().join("target");
            assert!(ensure_test_target(Some(&marker)).is_err());
            std::fs::write(&marker, b"not focused\n").unwrap();
            assert!(ensure_test_target(Some(&marker)).is_err());
            std::fs::write(&marker, b"ready\n").unwrap();
            assert_eq!(ensure_test_target(Some(&marker)), Ok(()));
            assert_eq!(ensure_test_target(None), Ok(()));
        }

        #[test]
        fn unicode_symbols_preserve_scalars() {
            assert_eq!(
                symbol_events("Äß🙂", &AtomicBool::new(false)).unwrap(),
                vec![
                    (0xc4, KeyState::Pressed),
                    (0xc4, KeyState::Released),
                    (0xdf, KeyState::Pressed),
                    (0xdf, KeyState::Released),
                    (0x0101_f642, KeyState::Pressed),
                    (0x0101_f642, KeyState::Released),
                ]
            );
        }

        #[test]
        fn cancelled_probe_sends_no_keys() {
            assert_eq!(
                symbol_events("Grüße", &AtomicBool::new(true)),
                Err("cancelled")
            );
        }

        #[test]
        fn paragraphs_and_controls_never_become_keyboard_commands() {
            for text in ["one\ntwo", "one\rtwo", "one\ttwo", "\u{1b}"] {
                assert_eq!(
                    symbol_events(text, &AtomicBool::new(false)),
                    Err("control characters require a safe paste transport")
                );
            }
        }
    }
}

#[cfg(target_os = "linux")]
#[tokio::main(flavor = "current_thread")]
async fn main() {
    if let Err(error) = linux::run().await {
        eprintln!("{error}");
        std::process::exit(1);
    }
}

#[cfg(not(target_os = "linux"))]
fn main() {
    eprintln!("This probe requires a Linux Wayland session; no input sent.");
    std::process::exit(1);
}
