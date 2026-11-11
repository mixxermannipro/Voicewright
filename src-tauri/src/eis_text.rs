//! UTF-8 text through a keyboard-authorized EIS connection, never key commands.

use libloading::Library;
use std::{
    ffi::{c_char, c_int, c_uint, c_void, CString},
    os::fd::{IntoRawFd, OwnedFd},
    ptr,
    sync::atomic::{AtomicBool, Ordering},
    time::{Duration, Instant},
};

fn prepare_text(text: &str, cancelled: &AtomicBool) -> Result<CString, &'static str> {
    if cancelled.load(Ordering::Relaxed) {
        return Err("Text output cancelled");
    }
    if text.is_empty() || text.len() > 16_384 || text.chars().any(|c| c != '\n' && c.is_control()) {
        return Err("Unsupported text for automatic output");
    }
    CString::new(text).map_err(|_| "Unsupported text for automatic output")
}

type Object = *mut c_void;
const CAP_TEXT: c_uint = 1 << 6;
const DISCONNECTED: &str = "Desktop text connection was revoked or disconnected";

// Signatures and event/capability values are from the public libei 1.6 ABI.
// Only TEXT is bound. No keycode, keysym, pointer or clipboard function is loaded.
struct Api {
    new_sender: unsafe extern "C" fn(Object) -> Object,
    unref: unsafe extern "C" fn(Object) -> Object,
    configure_name: unsafe extern "C" fn(Object, *const c_char),
    setup_fd: unsafe extern "C" fn(Object, c_int) -> c_int,
    dispatch: unsafe extern "C" fn(Object),
    get_event: unsafe extern "C" fn(Object) -> Object,
    event_type: unsafe extern "C" fn(Object) -> c_int,
    event_unref: unsafe extern "C" fn(Object) -> Object,
    event_device: unsafe extern "C" fn(Object) -> Object,
    event_seat: unsafe extern "C" fn(Object) -> Object,
    seat_has: unsafe extern "C" fn(Object, c_uint) -> bool,
    seat_bind: unsafe extern "C" fn(Object, ...),
    device_has: unsafe extern "C" fn(Object, c_uint) -> bool,
    device_ref: unsafe extern "C" fn(Object) -> Object,
    device_unref: unsafe extern "C" fn(Object) -> Object,
    start_emulating: unsafe extern "C" fn(Object, u32),
    frame: unsafe extern "C" fn(Object, u64),
    now: unsafe extern "C" fn(Object) -> u64,
    text_utf8: unsafe extern "C" fn(Object, *const c_char),
    new_ping: unsafe extern "C" fn(Object) -> Object,
    ping: unsafe extern "C" fn(Object),
    ping_unref: unsafe extern "C" fn(Object) -> Object,
    event_ping: unsafe extern "C" fn(Object) -> Object,
    _library: Library,
}

impl Api {
    fn load() -> Result<Self, &'static str> {
        // SAFETY: load the platform libei ABI by its versioned soname. Every
        // symbol is checked before use; Library remains alive with the pointers.
        unsafe {
            let library = Library::new("libei.so.1")
                .map_err(|_| "libei 1.6 or newer is required for direct Wayland text")?;
            macro_rules! symbol {
                ($name:literal) => {
                    *library
                        .get(concat!($name, "\0").as_bytes())
                        .map_err(|_| "Installed libei lacks Unicode text support (requires 1.6+)")?
                };
            }
            Ok(Self {
                new_sender: symbol!("ei_new_sender"),
                unref: symbol!("ei_unref"),
                configure_name: symbol!("ei_configure_name"),
                setup_fd: symbol!("ei_setup_backend_fd"),
                dispatch: symbol!("ei_dispatch"),
                get_event: symbol!("ei_get_event"),
                event_type: symbol!("ei_event_get_type"),
                event_unref: symbol!("ei_event_unref"),
                event_device: symbol!("ei_event_get_device"),
                event_seat: symbol!("ei_event_get_seat"),
                seat_has: symbol!("ei_seat_has_capability"),
                seat_bind: symbol!("ei_seat_bind_capabilities"),
                device_has: symbol!("ei_device_has_capability"),
                device_ref: symbol!("ei_device_ref"),
                device_unref: symbol!("ei_device_unref"),
                start_emulating: symbol!("ei_device_start_emulating"),
                frame: symbol!("ei_device_frame"),
                now: symbol!("ei_now"),
                text_utf8: symbol!("ei_device_text_utf8"),
                new_ping: symbol!("ei_new_ping"),
                ping: symbol!("ei_ping"),
                ping_unref: symbol!("ei_ping_unref"),
                event_ping: symbol!("ei_event_pong_get_ping"),
                _library: library,
            })
        }
    }
}

/// Thread-confined: create, poll, output and drop on the same worker thread.
/// Deliberately not Send/Sync. Only the portal-provided descriptor is accepted.
pub struct Client {
    api: Api,
    context: Object,
    device: Object,
    pending_ping: Object,
    ready: bool,
    sequence: u32,
}

impl Client {
    pub fn new(fd: OwnedFd) -> Result<Self, &'static str> {
        let api = Api::load()?;
        // SAFETY: signatures match libei.h; context is checked before use. The
        // owned fd is consumed by libei and closed by ei_unref on all paths.
        unsafe {
            let context = (api.new_sender)(ptr::null_mut());
            if context.is_null() {
                return Err("Could not allocate desktop text context");
            }
            let client = Self {
                api,
                context,
                device: ptr::null_mut(),
                pending_ping: ptr::null_mut(),
                ready: false,
                sequence: 0,
            };
            (client.api.configure_name)(context, c"Voicewright".as_ptr());
            if (client.api.setup_fd)(context, fd.into_raw_fd()) != 0 {
                return Err("Could not connect to desktop text input");
            }
            Ok(client)
        }
    }

    pub fn poll(&mut self) -> Result<(), &'static str> {
        // SAFETY: all objects originate from this owned, thread-confined
        // context. Transient events are unreferenced after handling; retained
        // devices and pings have their own refs and are released exactly once.
        unsafe {
            (self.api.dispatch)(self.context);
            for _ in 0..512 {
                let event = (self.api.get_event)(self.context);
                if event.is_null() {
                    return Ok(());
                }
                let device = (self.api.event_device)(event);
                let mut error = None;
                match (self.api.event_type)(event) {
                    2 | 4 => error = Some(DISCONNECTED),
                    3 => {
                        let seat = (self.api.event_seat)(event);
                        if seat.is_null() || !(self.api.seat_has)(seat, CAP_TEXT) {
                            error = Some("Desktop does not offer direct Unicode text input");
                        } else {
                            (self.api.seat_bind)(seat, CAP_TEXT, ptr::null::<c_void>());
                        }
                    }
                    5 if !device.is_null()
                        && self.device.is_null()
                        && (self.api.device_has)(device, CAP_TEXT) =>
                    {
                        self.device = (self.api.device_ref)(device);
                    }
                    6 if device == self.device && !self.device.is_null() => {
                        (self.api.device_unref)(self.device);
                        self.device = ptr::null_mut();
                        self.ready = false;
                        error = Some(DISCONNECTED);
                    }
                    7 if device == self.device => self.ready = false,
                    8 if device == self.device && !self.device.is_null() => {
                        self.sequence = self.sequence.wrapping_add(1);
                        (self.api.start_emulating)(self.device, self.sequence);
                        self.ready = true;
                    }
                    90 if !self.pending_ping.is_null()
                        && (self.api.event_ping)(event) == self.pending_ping =>
                    {
                        (self.api.ping_unref)(self.pending_ping);
                        self.pending_ping = ptr::null_mut();
                    }
                    _ => {}
                }
                (self.api.event_unref)(event);
                if let Some(error) = error {
                    self.ready = false;
                    return Err(error);
                }
            }
        }
        Err("Desktop text input exceeded its event budget")
    }

    pub fn send_text(
        &mut self,
        text: &str,
        cancelled: &AtomicBool,
        target_ready: impl Fn() -> bool,
    ) -> Result<(), &'static str> {
        let text = prepare_text(text, cancelled)?;
        let deadline = Instant::now() + Duration::from_secs(5);
        while !self.ready {
            self.poll()?;
            if cancelled.load(Ordering::Relaxed) {
                return Err("Text output cancelled");
            }
            if Instant::now() >= deadline {
                return Err("Desktop Unicode text device was not ready");
            }
            std::thread::sleep(Duration::from_millis(5));
        }
        self.poll()?;
        if !self.ready || cancelled.load(Ordering::Relaxed) || !target_ready() {
            return Err("Text output cancelled or test target not focused");
        }
        // SAFETY: the retained device has TEXT capability and received RESUMED;
        // CString contains validated UTF-8 and lives through the synchronous call.
        // One text/frame transaction, no simulated keys or clipboard changes.
        unsafe {
            (self.api.text_utf8)(self.device, text.as_ptr());
            (self.api.frame)(self.device, (self.api.now)(self.context));
            self.pending_ping = (self.api.new_ping)(self.context);
            if self.pending_ping.is_null() {
                return Err(
                    "Output dispatched but acknowledgement unavailable; do not retry automatically",
                );
            }
            (self.api.ping)(self.pending_ping);
        }
        let deadline = Instant::now() + Duration::from_secs(2);
        while !self.pending_ping.is_null() {
            self.poll()?;
            if Instant::now() >= deadline || cancelled.load(Ordering::Relaxed) {
                return Err("Output may already be present; acknowledgement interrupted");
            }
            std::thread::sleep(Duration::from_millis(5));
        }
        Ok(())
    }
}

impl Drop for Client {
    fn drop(&mut self) {
        // SAFETY: release only refs owned by this client, before Library unload.
        unsafe {
            if !self.pending_ping.is_null() {
                (self.api.ping_unref)(self.pending_ping);
            }
            if !self.device.is_null() {
                (self.api.device_unref)(self.device);
            }
            (self.api.unref)(self.context);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn utf8_preserves_case_emoji_and_paragraphs_without_enter_events() {
        let text = "Grüße ÄÖÜ äöü ß 🙂\nSecond paragraph.";
        assert_eq!(
            prepare_text(text, &AtomicBool::new(false))
                .unwrap()
                .to_bytes(),
            text.as_bytes()
        );
    }

    #[test]
    fn cancellation_is_checked_before_accepting_any_text() {
        assert_eq!(
            prepare_text("valid", &AtomicBool::new(true)),
            Err("Text output cancelled")
        );
    }

    #[test]
    fn unsupported_controls_and_oversized_text_are_not_dispatched() {
        for text in ["", "\0", "one\ttwo", "one\rtwo", "\u{1b}"] {
            assert_eq!(
                prepare_text(text, &AtomicBool::new(false)),
                Err("Unsupported text for automatic output")
            );
        }
        assert_eq!(
            prepare_text(&"a".repeat(16_385), &AtomicBool::new(false)),
            Err("Unsupported text for automatic output")
        );
    }
}
