//! Global shortcut capability detection and the XDG Desktop Portal backend.
//!
//! On X11 (and on Windows/macOS) the Tauri global-shortcut plugin owns the
//! registration. On Wayland a global key grab is not possible for ordinary
//! applications; the XDG GlobalShortcuts portal is the only supported path.
//! The portal may be missing, may require explicit user approval, or may deny
//! a binding. All of those states are surfaced to the UI instead of claiming
//! that shortcuts work.

use serde::Serialize;
use tauri_plugin_global_shortcut::{Code, Modifiers, Shortcut};
use tokio::sync::mpsc;

use crate::insertion::{self, SessionKind};

/// Which component is responsible for global shortcuts in this session.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Backend {
    /// Tauri's native global-shortcut plugin (Windows, macOS).
    #[cfg_attr(target_os = "linux", allow(dead_code))]
    Native,
    /// X11 key grabs through Tauri's global-shortcut plugin.
    X11,
    /// XDG Desktop Portal GlobalShortcuts (Wayland).
    Portal,
    /// No supported global shortcut path.
    Unsupported,
}

/// Runtime state of the shortcut binding, separate from text insertion.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ShortcutStatus {
    Unknown,
    /// Portal request is waiting for the user to approve the shortcuts.
    Pending,
    Active,
    /// The user declined the portal approval or a required shortcut is absent.
    Denied,
    /// The portal interface is missing or not reachable.
    Unavailable,
    Error,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Binding {
    pub id: &'static str,
    pub description: String,
    pub trigger: String,
}

#[derive(Debug)]
pub enum Event {
    Status(ShortcutStatus, Option<String>),
    Pressed(&'static str),
    Released(&'static str),
}

#[derive(Debug)]
pub enum Command {
    Rebind(Vec<Binding>),
}

/// Handle used by the app to replace bindings without restarting.
#[derive(Clone, Debug)]
pub struct Controller {
    commands: mpsc::UnboundedSender<Command>,
}

impl Controller {
    pub fn rebind(&self, bindings: Vec<Binding>) {
        let _ = self.commands.send(Command::Rebind(bindings));
    }
}

pub fn backend() -> Backend {
    match insertion::session_kind() {
        SessionKind::X11 => Backend::X11,
        SessionKind::Wayland => Backend::Portal,
        SessionKind::Other => {
            #[cfg(any(target_os = "windows", target_os = "macos"))]
            {
                Backend::Native
            }
            #[cfg(not(any(target_os = "windows", target_os = "macos")))]
            {
                Backend::Unsupported
            }
        }
    }
}

/// Converts a Tauri shortcut into the freedesktop shortcut trigger syntax.
///
/// The identifiers come from xkbcommon-keysyms.h without the `XKB_KEY_`
/// prefix. Only the keys that the settings UI can capture are accepted; an
/// unsupported key becomes `None` and the portal binding is skipped instead of
/// guessing a different key.
pub fn trigger(shortcut: &Shortcut) -> Option<String> {
    let key = key_name(shortcut.key)?;
    let mut parts = Vec::with_capacity(5);
    if shortcut.mods.contains(Modifiers::CONTROL) {
        parts.push("CTRL");
    }
    if shortcut.mods.contains(Modifiers::ALT) {
        parts.push("ALT");
    }
    if shortcut.mods.contains(Modifiers::SHIFT) {
        parts.push("SHIFT");
    }
    // Tauri normalizes Meta to Super; both mean the logo/windows key.
    if shortcut.mods.intersects(Modifiers::SUPER | Modifiers::META) {
        parts.push("LOGO");
    }
    parts.push(key);
    Some(parts.join("+"))
}

fn key_name(code: Code) -> Option<&'static str> {
    Some(match code {
        Code::KeyA => "a",
        Code::KeyB => "b",
        Code::KeyC => "c",
        Code::KeyD => "d",
        Code::KeyE => "e",
        Code::KeyF => "f",
        Code::KeyG => "g",
        Code::KeyH => "h",
        Code::KeyI => "i",
        Code::KeyJ => "j",
        Code::KeyK => "k",
        Code::KeyL => "l",
        Code::KeyM => "m",
        Code::KeyN => "n",
        Code::KeyO => "o",
        Code::KeyP => "p",
        Code::KeyQ => "q",
        Code::KeyR => "r",
        Code::KeyS => "s",
        Code::KeyT => "t",
        Code::KeyU => "u",
        Code::KeyV => "v",
        Code::KeyW => "w",
        Code::KeyX => "x",
        Code::KeyY => "y",
        Code::KeyZ => "z",
        Code::Digit0 => "0",
        Code::Digit1 => "1",
        Code::Digit2 => "2",
        Code::Digit3 => "3",
        Code::Digit4 => "4",
        Code::Digit5 => "5",
        Code::Digit6 => "6",
        Code::Digit7 => "7",
        Code::Digit8 => "8",
        Code::Digit9 => "9",
        Code::Space => "space",
        Code::Escape => "Escape",
        Code::Enter => "Return",
        Code::Backspace => "BackSpace",
        Code::Delete => "Delete",
        Code::Home => "Home",
        Code::End => "End",
        Code::PageUp => "Page_Up",
        Code::PageDown => "Page_Down",
        Code::ArrowUp => "Up",
        Code::ArrowDown => "Down",
        Code::ArrowLeft => "Left",
        Code::ArrowRight => "Right",
        Code::F1 => "F1",
        Code::F2 => "F2",
        Code::F3 => "F3",
        Code::F4 => "F4",
        Code::F5 => "F5",
        Code::F6 => "F6",
        Code::F7 => "F7",
        Code::F8 => "F8",
        Code::F9 => "F9",
        Code::F10 => "F10",
        Code::F11 => "F11",
        Code::F12 => "F12",
        Code::F13 => "F13",
        Code::F14 => "F14",
        Code::F15 => "F15",
        Code::F16 => "F16",
        Code::F17 => "F17",
        Code::F18 => "F18",
        Code::F19 => "F19",
        Code::F20 => "F20",
        Code::F21 => "F21",
        Code::F22 => "F22",
        Code::F23 => "F23",
        Code::F24 => "F24",
        _ => return None,
    })
}

#[cfg(not(target_os = "linux"))]
pub fn bindings(_settings: &crate::settings::Settings) -> Vec<Binding> {
    Vec::new()
}

#[cfg(target_os = "linux")]
pub fn bindings(settings: &crate::settings::Settings) -> Vec<Binding> {
    let mut result = Vec::new();
    if let Ok(shortcut) = settings.shortcut.parse::<Shortcut>() {
        if let Some(trigger) = trigger(&shortcut) {
            result.push(Binding {
                id: "dictation",
                description: "Voicewright: Diktat starten/stoppen · Start/stop dictation".into(),
                trigger,
            });
        }
    }
    if !settings.cancel_shortcut.is_empty() {
        if let Ok(shortcut) = settings.cancel_shortcut.parse::<Shortcut>() {
            if let Some(trigger) = trigger(&shortcut) {
                result.push(Binding {
                    id: "cancel",
                    description: "Voicewright: Diktat abbrechen · Cancel dictation".into(),
                    trigger,
                });
            }
        }
    }
    result
}

/// Starts the portal worker. The worker returns status changes and key events
/// through the receiver; it never panics the app when the portal is missing.
#[cfg(target_os = "linux")]
pub fn start(bindings: Vec<Binding>) -> (Controller, mpsc::UnboundedReceiver<Event>) {
    let (command_tx, command_rx) = mpsc::unbounded_channel();
    let (event_tx, event_rx) = mpsc::unbounded_channel();
    let controller = Controller {
        commands: command_tx,
    };
    tauri::async_runtime::spawn(async move {
        worker(bindings, command_rx, event_tx).await;
    });
    (controller, event_rx)
}

#[cfg(not(target_os = "linux"))]
pub fn start(bindings: Vec<Binding>) -> (Controller, mpsc::UnboundedReceiver<Event>) {
    let _ = bindings;
    let (command_tx, command_rx) = mpsc::unbounded_channel();
    let (event_tx, event_rx) = mpsc::unbounded_channel();
    drop(command_rx);
    tauri::async_runtime::spawn(async move {
        let _ = event_tx.send(Event::Status(
            ShortcutStatus::Unavailable,
            Some("Global shortcuts use the native backend.".into()),
        ));
    });
    (
        Controller {
            commands: command_tx,
        },
        event_rx,
    )
}

#[cfg(target_os = "linux")]
async fn worker(
    mut desired: Vec<Binding>,
    mut commands: mpsc::UnboundedReceiver<Command>,
    events: mpsc::UnboundedSender<Event>,
) {
    loop {
        match run_session(&desired, &mut commands, &events).await {
            Outcome::Rebind(next) => {
                desired = next;
            }
            Outcome::Retry => {
                let _ = events.send(Event::Status(
                    ShortcutStatus::Unavailable,
                    Some(
                        "The desktop shortcut portal is not available or was closed. \
                         Use the app window and copy the result."
                            .into(),
                    ),
                ));
                // Wait for an explicit retry or a settings change rather than
                // opening approval dialogs in a loop.
                match commands.recv().await {
                    Some(Command::Rebind(next)) => desired = next,
                    None => break,
                }
            }
            Outcome::Denied => {
                // A denied request is a deliberate user decision. Do not ask
                // again until the user retries or changes the shortcuts.
                match commands.recv().await {
                    Some(Command::Rebind(next)) => desired = next,
                    None => break,
                }
            }
        }
    }
}

#[cfg(target_os = "linux")]
enum Outcome {
    Rebind(Vec<Binding>),
    Retry,
    Denied,
}

/// Waits for the next item if the portal exposes the optional stream. When
/// the stream is absent the future stays pending forever, so `select!` keeps
/// the other branches usable.
#[cfg(target_os = "linux")]
async fn next_optional<S>(stream: &mut Option<S>) -> Option<S::Item>
where
    S: futures_util::Stream + Unpin,
{
    match stream {
        Some(stream) => futures_util::StreamExt::next(stream).await,
        None => std::future::pending().await,
    }
}

#[cfg(target_os = "linux")]
async fn run_session(
    desired: &[Binding],
    commands: &mut mpsc::UnboundedReceiver<Command>,
    events: &mpsc::UnboundedSender<Event>,
) -> Outcome {
    use ashpd::desktop::{
        global_shortcuts::{BindShortcutsOptions, GlobalShortcuts, NewShortcut},
        CreateSessionOptions,
    };
    use futures_util::StreamExt;

    let portal = match GlobalShortcuts::new().await {
        Ok(portal) if portal.version() >= 1 => portal,
        Ok(_) => return Outcome::Retry,
        Err(_) => return Outcome::Retry,
    };
    let session = match portal.create_session(CreateSessionOptions::default()).await {
        Ok(session) => session,
        Err(_) => return Outcome::Retry,
    };
    let mut activated = match portal.receive_activated().await {
        Ok(stream) => stream,
        Err(_) => return Outcome::Retry,
    };
    let mut deactivated = match portal.receive_deactivated().await {
        Ok(stream) => stream,
        Err(_) => return Outcome::Retry,
    };
    // Older portals may not expose the changed signal. Missing it must not
    // disable shortcuts that were granted correctly.
    let mut changed = portal.receive_shortcuts_changed().await.ok();
    let mut closed = match session.receive_closed().await {
        Ok(stream) => stream,
        Err(_) => return Outcome::Retry,
    };

    let _ = events.send(Event::Status(
        ShortcutStatus::Pending,
        Some("Waiting for the desktop shortcut approval.".into()),
    ));
    let requested: Vec<NewShortcut> = desired
        .iter()
        .map(|binding| {
            NewShortcut::new(binding.id, binding.description.clone())
                .preferred_trigger(binding.trigger.as_str())
        })
        .collect();
    let request = match portal
        .bind_shortcuts(&session, &requested, None, BindShortcutsOptions::default())
        .await
    {
        Ok(request) => request,
        Err(error) => {
            let (status, detail) = classify_error(&error);
            let _ = events.send(Event::Status(status, Some(detail)));
            let _ = session.close().await;
            return if status == ShortcutStatus::Unavailable {
                Outcome::Retry
            } else {
                Outcome::Denied
            };
        }
    };
    let bound = match request.response() {
        Ok(bound) => bound,
        Err(error) => {
            let (status, detail) = classify_error(&error);
            let _ = events.send(Event::Status(status, Some(detail)));
            let _ = session.close().await;
            return Outcome::Denied;
        }
    };
    let (status, detail) = evaluate(desired, bound.shortcuts());
    let _ = events.send(Event::Status(status, detail));
    if status != ShortcutStatus::Active {
        let _ = session.close().await;
        return Outcome::Denied;
    }

    loop {
        tokio::select! {
            event = activated.next() => match event {
                Some(event) => {
                    let id = match event.shortcut_id() {
                        "dictation" => "dictation",
                        "cancel" => "cancel",
                        _ => continue,
                    };
                    let _ = events.send(Event::Pressed(id));
                }
                None => return Outcome::Retry,
            },
            event = deactivated.next() => match event {
                Some(event) => {
                    let id = match event.shortcut_id() {
                        "dictation" => "dictation",
                        "cancel" => "cancel",
                        _ => continue,
                    };
                    let _ = events.send(Event::Released(id));
                }
                None => return Outcome::Retry,
            },
            event = next_optional(&mut changed) => match event {
                Some(event) => {
                    // A desktop settings change can revoke or restore a
                    // binding. Surface the new state instead of keeping a
                    // stale "active" claim in the UI.
                    let (status, detail) = evaluate(desired, event.shortcuts());
                    let _ = events.send(Event::Status(status, detail));
                }
                None => return Outcome::Retry,
            },
            event = closed.next() => match event {
                Some(_) => return Outcome::Retry,
                None => return Outcome::Retry,
            },
            command = commands.recv() => match command {
                Some(Command::Rebind(next)) => {
                    let _ = session.close().await;
                    return Outcome::Rebind(next);
                }
                None => {
                    let _ = session.close().await;
                    return Outcome::Retry;
                }
            },
        }
    }
}

#[cfg(target_os = "linux")]
fn classify_error(error: &ashpd::Error) -> (ShortcutStatus, String) {
    use ashpd::{desktop::ResponseError, Error};
    match error {
        Error::Response(ResponseError::Cancelled) => (
            ShortcutStatus::Denied,
            "The desktop shortcut approval was declined. Use the app window and copy the result."
                .into(),
        ),
        Error::PortalNotFound(_) => (
            ShortcutStatus::Unavailable,
            "The desktop global-shortcuts portal is missing. Use the app window and copy the result."
                .into(),
        ),
        Error::RequiresVersion(_, _) => (
            ShortcutStatus::Unavailable,
            "The desktop portal is too old for global shortcuts. Use the app window and copy the result."
                .into(),
        ),
        Error::Zbus(_) => (
            ShortcutStatus::Unavailable,
            "The desktop portal could not be reached. Use the app window and copy the result."
                .into(),
        ),
        _ => (
            ShortcutStatus::Error,
            "The desktop shortcut request failed. Use the app window and copy the result.".into(),
        ),
    }
}

#[cfg(target_os = "linux")]
fn evaluate(
    desired: &[Binding],
    bound: &[ashpd::desktop::global_shortcuts::Shortcut],
) -> (ShortcutStatus, Option<String>) {
    evaluate_ids(desired, bound.iter().map(|shortcut| shortcut.id()))
}

#[cfg(target_os = "linux")]
fn evaluate_ids<'a>(
    desired: &[Binding],
    bound: impl IntoIterator<Item = &'a str>,
) -> (ShortcutStatus, Option<String>) {
    let bound: Vec<&str> = bound.into_iter().collect();
    let has_dictation = bound.contains(&"dictation");
    if !has_dictation {
        return (
            ShortcutStatus::Denied,
            Some(
                "The desktop did not grant the dictation shortcut. Use the app window and copy the result."
                    .into(),
            ),
        );
    }
    let missing_cancel =
        desired.iter().any(|binding| binding.id == "cancel") && !bound.contains(&"cancel");
    if missing_cancel {
        return (
            ShortcutStatus::Active,
            Some(
                "The dictation shortcut is active, but the cancel shortcut was not granted.".into(),
            ),
        );
    }
    (ShortcutStatus::Active, None)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn shortcut(text: &str) -> Shortcut {
        text.parse().unwrap()
    }

    #[test]
    fn portal_trigger_uses_xkb_keysym_names() {
        assert_eq!(
            trigger(&shortcut("Ctrl+Shift+Space")).as_deref(),
            Some("CTRL+SHIFT+space")
        );
        assert_eq!(trigger(&shortcut("Alt+F12")).as_deref(), Some("ALT+F12"));
        assert_eq!(
            trigger(&shortcut("Super+Enter")).as_deref(),
            Some("LOGO+Return")
        );
        assert_eq!(
            trigger(&shortcut("Ctrl+PageDown")).as_deref(),
            Some("CTRL+Page_Down")
        );
        assert_eq!(
            trigger(&shortcut("Ctrl+Backspace")).as_deref(),
            Some("CTRL+BackSpace")
        );
        assert_eq!(
            trigger(&shortcut("Ctrl+ArrowLeft")).as_deref(),
            Some("CTRL+Left")
        );
    }

    #[test]
    fn unsupported_keys_are_not_guessed() {
        let unsupported = Shortcut {
            mods: Modifiers::CONTROL,
            key: Code::IntlBackslash,
            id: 0,
        };
        assert_eq!(trigger(&unsupported), None);
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn binding_list_skips_an_empty_cancel_shortcut() {
        let settings = crate::settings::Settings::default();
        let result = bindings(&settings);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].id, "dictation");
        assert_eq!(result[0].trigger, "CTRL+SHIFT+space");
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn evaluate_requires_the_dictation_shortcut_and_reports_a_missing_cancel() {
        let desired = vec![
            Binding {
                id: "dictation",
                description: String::new(),
                trigger: "CTRL+SHIFT+space".into(),
            },
            Binding {
                id: "cancel",
                description: String::new(),
                trigger: "CTRL+SHIFT+Escape".into(),
            },
        ];
        let denied = evaluate_ids(&desired, std::iter::empty());
        assert_eq!(denied.0, ShortcutStatus::Denied);
        assert!(denied.1.is_some());

        let partial = evaluate_ids(&desired, ["dictation"]);
        assert_eq!(partial.0, ShortcutStatus::Active);
        assert!(partial.1.is_some());

        let active = evaluate_ids(&desired, ["dictation", "cancel"]);
        assert_eq!(active.0, ShortcutStatus::Active);
        assert!(active.1.is_none());
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn classify_missing_portal_and_cancelled_request() {
        use ashpd::{desktop::ResponseError, Error};
        let cancelled = Error::Response(ResponseError::Cancelled);
        assert_eq!(classify_error(&cancelled).0, ShortcutStatus::Denied);
        let old = Error::RequiresVersion(2, 1);
        assert_eq!(classify_error(&old).0, ShortcutStatus::Unavailable);
    }
}
