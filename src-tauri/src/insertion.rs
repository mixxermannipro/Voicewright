use enigo::{Direction, Enigo, Key, Keyboard, Settings};
use std::{
    borrow::Cow,
    sync::atomic::{AtomicBool, Ordering},
    time::Duration,
};
use unicode_segmentation::UnicodeSegmentation;

/// The display server session that owns the focused window.
#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SessionKind {
    X11,
    Wayland,
    Other,
}

#[cfg(target_os = "linux")]
fn classify_session(xdg: &str, wayland_display: bool, x11_display: bool) -> SessionKind {
    // An explicit X11 session wins over a stray Wayland socket. Otherwise a
    // Wayland socket means the compositor owns the focused window, even when
    // XWayland also exposes a DISPLAY.
    if xdg == "wayland" || (xdg != "x11" && wayland_display) {
        SessionKind::Wayland
    } else if x11_display {
        SessionKind::X11
    } else {
        SessionKind::Other
    }
}

pub fn session_kind() -> SessionKind {
    #[cfg(target_os = "linux")]
    {
        classify_session(
            &std::env::var("XDG_SESSION_TYPE").unwrap_or_default(),
            std::env::var_os("WAYLAND_DISPLAY").is_some(),
            std::env::var_os("DISPLAY").is_some(),
        )
    }
    #[cfg(not(target_os = "linux"))]
    {
        SessionKind::Other
    }
}

/// Direct text insertion is only claimed where the app has a documented path.
/// Wayland is deliberately excluded: ordinary clients cannot inject keys, and
/// the RemoteDesktop/libei route requires a broad remote-control grant that is
/// not requested implicitly.
pub fn automatic_supported() -> bool {
    #[cfg(target_os = "linux")]
    {
        session_kind() == SessionKind::X11
    }
    #[cfg(target_os = "windows")]
    {
        true
    }
    #[cfg(not(any(target_os = "linux", target_os = "windows")))]
    {
        false
    }
}

pub fn unavailable_reason() -> Option<&'static str> {
    #[cfg(target_os = "linux")]
    {
        match session_kind() {
            SessionKind::X11 => None,
            SessionKind::Wayland => Some(
                "Wayland does not allow this app to inject text. The result stays in Voicewright for copying.",
            ),
            SessionKind::Other => Some(
                "No supported display server was detected. The result stays in Voicewright for copying.",
            ),
        }
    }
    #[cfg(target_os = "windows")]
    {
        None
    }
    #[cfg(not(any(target_os = "linux", target_os = "windows")))]
    {
        Some("Automatic insertion is not implemented on this platform. The result stays in Voicewright for copying.")
    }
}

/// Identity used to reject an insertion after a focus change.
///
/// A window or field can be replaced without the numeric id changing, so this
/// is a safety signal rather than proof of the same text field. The X11 path
/// additionally samples the target twice before typing and before every chunk.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Target {
    focus: u32,
    active: u32,
    pid: u32,
}

const TARGET_CHANGED: &str = "The target changed or a modifier is held. Copy the result manually.";
const CANCELLED: &str = "Insertion was cancelled. The result is available to copy.";
const PARTIAL: &str =
    "Insertion stopped after partial input. The full result is available to copy.";
const TOO_COMPLEX: &str =
    "The result is too long or contains unsupported control characters. Copy it manually.";
const FAILED: &str = "Text insertion could not be confirmed. The result is available to copy.";
const STABLE_WINDOW: Duration = Duration::from_millis(60);

#[cfg(target_os = "linux")]
fn x11_focus(check_modifiers: bool) -> Option<Target> {
    use x11rb::{
        connection::Connection,
        protocol::xproto::{AtomEnum, ConnectionExt, KeyButMask, MapState},
    };
    let (connection, screen) = x11rb::connect(None).ok()?;
    let root = connection.setup().roots.get(screen)?.root;
    let focus = connection.get_input_focus().ok()?.reply().ok()?.focus;
    if focus <= 1 || focus == root {
        return None;
    }
    // A destroyed or withdrawn window must not receive text.
    if connection
        .get_window_attributes(focus)
        .ok()?
        .reply()
        .ok()?
        .map_state
        != MapState::VIEWABLE
    {
        return None;
    }
    if check_modifiers {
        let mask = connection.query_pointer(root).ok()?.reply().ok()?.mask;
        if mask.intersects(
            KeyButMask::SHIFT
                | KeyButMask::CONTROL
                | KeyButMask::MOD1
                | KeyButMask::MOD4
                | KeyButMask::MOD5,
        ) {
            return None;
        }
    }
    let active_atom = connection
        .intern_atom(true, b"_NET_ACTIVE_WINDOW")
        .ok()?
        .reply()
        .ok()?
        .atom;
    let active = if active_atom == 0 {
        0
    } else {
        connection
            .get_property(false, root, active_atom, AtomEnum::WINDOW, 0, 1)
            .ok()?
            .reply()
            .ok()?
            .value32()
            .and_then(|mut value| value.next())
            .unwrap_or(0)
    };
    let pid_atom = connection
        .intern_atom(true, b"_NET_WM_PID")
        .ok()?
        .reply()
        .ok()?
        .atom;
    let pid = [active, focus]
        .into_iter()
        .find_map(|window| {
            if window <= 1 || pid_atom == 0 {
                return None;
            }
            connection
                .get_property(false, window, pid_atom, AtomEnum::CARDINAL, 0, 1)
                .ok()?
                .reply()
                .ok()?
                .value32()
                .and_then(|mut value| value.next())
        })
        .unwrap_or(0);
    Some(Target { focus, active, pid })
}

#[cfg(target_os = "windows")]
fn windows_focus(check_modifiers: bool) -> Option<Target> {
    use windows_sys::Win32::UI::{
        Input::KeyboardAndMouse::{
            GetAsyncKeyState, VK_CONTROL, VK_LWIN, VK_MENU, VK_RWIN, VK_SHIFT,
        },
        WindowsAndMessaging::{
            GetForegroundWindow, GetGUIThreadInfo, GetWindowThreadProcessId, GUITHREADINFO,
        },
    };
    unsafe {
        let foreground = GetForegroundWindow();
        if foreground.is_null() {
            return None;
        }
        if check_modifiers
            && [VK_CONTROL, VK_SHIFT, VK_MENU, VK_LWIN, VK_RWIN]
                .iter()
                .any(|key| GetAsyncKeyState(i32::from(*key)) < 0)
        {
            return None;
        }
        let mut pid = 0;
        let thread = GetWindowThreadProcessId(foreground, &mut pid);
        let mut info: GUITHREADINFO = std::mem::zeroed();
        info.cbSize = std::mem::size_of::<GUITHREADINFO>() as u32;
        if thread == 0 || GetGUIThreadInfo(thread, &mut info) == 0 || info.hwndFocus.is_null() {
            return None;
        }
        Some(Target {
            focus: info.hwndFocus as u32,
            active: foreground as u32,
            pid,
        })
    }
}

fn focus(_check_modifiers: bool) -> Option<Target> {
    #[cfg(target_os = "linux")]
    {
        if session_kind() != SessionKind::X11 {
            return None;
        }
        x11_focus(_check_modifiers)
    }
    #[cfg(target_os = "windows")]
    {
        windows_focus(_check_modifiers)
    }
    #[cfg(not(any(target_os = "linux", target_os = "windows")))]
    {
        None
    }
}

pub fn target() -> Option<Target> {
    focus(false)
}

fn ensure_target(target: Target, check_modifiers: bool) -> Result<(), &'static str> {
    if focus(check_modifiers) == Some(target) {
        Ok(())
    } else {
        Err(TARGET_CHANGED)
    }
}

/// Reject text that can trigger navigation or terminal actions. Newlines are
/// allowed because dictation supports paragraphs; tab and other control
/// characters remain copy-only. CRLF and lone CR are normalized to LF.
fn normalize(text: &str) -> Result<Cow<'_, str>, &'static str> {
    if text.is_empty() {
        return Err(TOO_COMPLEX);
    }
    let text = if text.contains('\r') {
        Cow::Owned(text.replace("\r\n", "\n").replace('\r', "\n"))
    } else {
        Cow::Borrowed(text)
    };
    if text.chars().count() > 400
        || text
            .chars()
            .any(|character| character != '\n' && character.is_control())
    {
        return Err(TOO_COMPLEX);
    }
    Ok(text)
}

#[derive(Clone, Debug, PartialEq, Eq)]
enum Piece {
    Text(String),
    Newline,
}

const CHUNK_GRAPHEMES: usize = 64;

/// Split on grapheme clusters, not scalar values. Splitting a flag, a family
/// emoji or a combining sequence between two keyboard events can produce
/// broken output in some applications.
fn pieces(text: &str) -> Vec<Piece> {
    let mut result = Vec::new();
    let mut current = String::new();
    let mut count = 0;
    for grapheme in text.graphemes(true) {
        if grapheme == "\n" {
            if !current.is_empty() {
                result.push(Piece::Text(std::mem::take(&mut current)));
                count = 0;
            }
            result.push(Piece::Newline);
            continue;
        }
        current.push_str(grapheme);
        count += 1;
        if count >= CHUNK_GRAPHEMES {
            result.push(Piece::Text(std::mem::take(&mut current)));
            count = 0;
        }
    }
    if !current.is_empty() {
        result.push(Piece::Text(current));
    }
    result
}

fn partial_error(typed: bool) -> &'static str {
    if typed {
        PARTIAL
    } else {
        TARGET_CHANGED
    }
}

pub fn insert(target: Target, text: &str, cancelled: &AtomicBool) -> Result<(), &'static str> {
    let text = normalize(text)?;
    if cancelled.load(Ordering::Relaxed) {
        return Err(CANCELLED);
    }
    let mut input = Enigo::new(&Settings::default()).map_err(|_| FAILED)?;
    // Two samples catch a focus change that happens while the result is being
    // prepared. The target is sampled again before every chunk below.
    ensure_target(target, true)?;
    std::thread::sleep(STABLE_WINDOW);
    ensure_target(target, true)?;
    let mut typed = false;
    for piece in pieces(&text) {
        if cancelled.load(Ordering::Relaxed) {
            return Err(if typed { PARTIAL } else { CANCELLED });
        }
        ensure_target(target, true).map_err(|_| partial_error(typed))?;
        match piece {
            Piece::Text(chunk) => input.text(&chunk).map_err(|_| partial_error(typed))?,
            Piece::Newline => input
                .key(Key::Return, Direction::Click)
                .map_err(|_| partial_error(typed))?,
        }
        typed = true;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[cfg(target_os = "linux")]
    #[test]
    fn session_classification_handles_xwayland_and_missing_variables() {
        assert_eq!(
            classify_session("wayland", true, true),
            SessionKind::Wayland
        );
        assert_eq!(
            classify_session("wayland", false, true),
            SessionKind::Wayland
        );
        assert_eq!(classify_session("x11", true, true), SessionKind::X11);
        assert_eq!(classify_session("x11", false, true), SessionKind::X11);
        assert_eq!(classify_session("", true, true), SessionKind::Wayland);
        assert_eq!(classify_session("", false, true), SessionKind::X11);
        assert_eq!(classify_session("tty", false, true), SessionKind::X11);
        assert_eq!(classify_session("", false, false), SessionKind::Other);
    }

    #[test]
    fn unicode_and_paragraphs_are_eligible_but_tabs_and_other_controls_are_not() {
        assert_eq!(
            normalize("Grüße aus Köln.\nZweiter Absatz 😀")
                .unwrap()
                .as_ref(),
            "Grüße aus Köln.\nZweiter Absatz 😀"
        );
        assert_eq!(normalize("a\r\nb\rc").unwrap().as_ref(), "a\nb\nc");
        assert!(normalize("run\tcommand").is_err());
        assert!(normalize("a\u{0}b").is_err());
        assert!(normalize("a\u{7}b").is_err());
        assert!(normalize(&"a".repeat(401)).is_err());
        assert!(normalize("").is_err());
    }

    #[test]
    fn chunking_preserves_grapheme_clusters_and_paragraph_breaks() {
        let text = "Grüße 🇩🇪👨‍👩‍👧‍👦 e\u{301} 😀 aus München – ß, é, €.\n\nNeuer Absatz.";
        let result = pieces(text);
        assert!(result.contains(&Piece::Newline));
        let joined: String = result
            .iter()
            .map(|piece| match piece {
                Piece::Text(value) => value.as_str(),
                Piece::Newline => "\n",
            })
            .collect();
        assert_eq!(joined, text);
        for piece in result {
            if let Piece::Text(value) = piece {
                assert!(value.graphemes(true).count() <= CHUNK_GRAPHEMES);
                // A flag or family emoji must never be split across chunks.
                assert!(!value.ends_with('\u{1F1E9}') || value.ends_with("🇩🇪"));
            }
        }
    }

    #[test]
    fn a_cancelled_insert_never_types() {
        let target = Target {
            focus: 1,
            active: 2,
            pid: 3,
        };
        let cancelled = AtomicBool::new(true);
        assert_eq!(insert(target, "Hallo", &cancelled), Err(CANCELLED));
    }

    #[test]
    fn unsupported_text_stops_before_opening_the_input_device() {
        let target = Target {
            focus: 1,
            active: 2,
            pid: 3,
        };
        let cancelled = AtomicBool::new(false);
        assert_eq!(insert(target, "run\tcommand", &cancelled), Err(TOO_COMPLEX));
    }
}
