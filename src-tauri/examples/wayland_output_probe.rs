//! Explicit, keyboard-only Wayland output probe. Not used by the app.

#[cfg(target_os = "linux")]
mod linux {
    use ashpd::desktop::{
        remote_desktop::{DeviceType, KeyState, RemoteDesktop, SelectDevicesOptions},
        PersistMode,
    };
    use std::{
        sync::atomic::{AtomicBool, Ordering},
        time::Duration,
    };

    const LINE: &str = "Grüße aus Köln, ÄÖÜ äöü ß 🙂";

    fn requested_devices() -> DeviceType {
        DeviceType::KEYBOARD
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
        if !matches!(mode.as_str(), "permission" | "keysym") {
            return Err("Use permission (no input) or keysym (fixed single-line test). Clipboard transport is not verified yet.");
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
            println!(
                "Fixed single-line test in 5 seconds; paragraphs are not tested by keysym mode."
            );
            tokio::time::sleep(Duration::from_secs(5)).await;
            for (symbol, key_state) in symbol_events(LINE, &AtomicBool::new(false))? {
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
