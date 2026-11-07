use enigo::{Enigo, Keyboard, Settings};
use std::sync::atomic::{AtomicBool, Ordering};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Target(usize, usize);

pub fn global_supported() -> bool {
    #[cfg(target_os = "linux")]
    {
        std::env::var_os("DISPLAY").is_some()
            && std::env::var_os("WAYLAND_DISPLAY").is_none()
            && std::env::var("XDG_SESSION_TYPE").as_deref() != Ok("wayland")
    }
    #[cfg(not(target_os = "linux"))]
    {
        true
    }
}

#[cfg(target_os = "linux")]
fn x11_focus(check_modifiers: bool) -> Option<Target> {
    use x11rb::{
        connection::Connection,
        protocol::xproto::{AtomEnum, ConnectionExt, KeyButMask},
    };
    if !global_supported() {
        return None;
    }
    let (connection, screen) = x11rb::connect(None).ok()?;
    let root = connection.setup().roots.get(screen)?.root;
    let focus = connection.get_input_focus().ok()?.reply().ok()?.focus;
    if focus <= 1 || focus == root {
        return None;
    }
    if check_modifiers {
        let mask = connection.query_pointer(root).ok()?.reply().ok()?.mask;
        if mask.intersects(
            KeyButMask::SHIFT | KeyButMask::CONTROL | KeyButMask::MOD1 | KeyButMask::MOD4,
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
    Some(Target(focus as usize, active as usize))
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
        let thread = GetWindowThreadProcessId(foreground, std::ptr::null_mut());
        let mut info: GUITHREADINFO = std::mem::zeroed();
        info.cbSize = std::mem::size_of::<GUITHREADINFO>() as u32;
        if thread == 0 || GetGUIThreadInfo(thread, &mut info) == 0 || info.hwndFocus.is_null() {
            return None;
        }
        Some(Target(foreground as usize, info.hwndFocus as usize))
    }
}

fn focus(_check_modifiers: bool) -> Option<Target> {
    #[cfg(target_os = "linux")]
    {
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

fn direct_safe(text: &str) -> bool {
    !text.is_empty() && text.chars().count() <= 400 && !text.chars().any(char::is_control)
}

fn chunks(text: &str, size: usize) -> Vec<String> {
    text.chars()
        .collect::<Vec<_>>()
        .chunks(size)
        .map(|chunk| chunk.iter().collect())
        .collect()
}

pub fn insert(target: Target, text: &str, cancelled: &AtomicBool) -> Result<(), &'static str> {
    if !direct_safe(text) {
        return Err("Copy long or multiline text manually.");
    }
    let mut input = Enigo::new(&Settings::default()).map_err(|_| "Could not open system input.")?;
    for chunk in chunks(text, 64) {
        if cancelled.load(Ordering::Relaxed) {
            return Err("Insertion was cancelled. The result is available to copy.");
        }
        if focus(true) != Some(target) {
            return Err("The target changed or a modifier is held. Copy the result manually.");
        }
        input.text(&chunk).map_err(|_| {
            "Text insertion could not be confirmed. The result is available to copy."
        })?;
    }
    if cancelled.load(Ordering::Relaxed) {
        return Err("Insertion was cancelled. The result is available to copy.");
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unicode_is_eligible_but_control_characters_are_not_typed() {
        assert!(direct_safe("Grüße aus Köln."));
        assert!(!direct_safe("run\ncommand"));
        assert!(!direct_safe("a\tb"));
        assert!(!direct_safe(&"a".repeat(401)));
    }

    #[test]
    fn chunking_preserves_unicode_without_splitting_a_scalar_value() {
        let text = "Grüße 😀 aus München – ß, é, €.";
        let parts = chunks(text, 4);
        assert!(parts.len() > 1);
        assert!(parts.iter().all(|part| part.chars().count() <= 4));
        assert_eq!(parts.concat(), text);
    }
}
