//! Manual X11 integration probe for the insertion module.
//!
//! This example is not part of the app bundle. It types a test string into the
//! currently focused X11 window and is used by `scripts/linux-smoke/x11-insertion.sh`
//! together with a GTK multiline probe. It refuses to run outside an X11
//! session so it can never type into a Wayland or headless target by mistake.

#[cfg(target_os = "linux")]
#[path = "../src/insertion.rs"]
mod insertion;

#[cfg(target_os = "linux")]
fn main() {
    use std::sync::atomic::AtomicBool;

    if !insertion::automatic_supported() {
        eprintln!(
            "X11 insertion is not available: {}",
            insertion::unavailable_reason().unwrap_or("unknown reason")
        );
        std::process::exit(2);
    }
    let text = std::env::args()
        .nth(1)
        .unwrap_or_else(|| "Grüße aus Köln.\nZweiter Absatz 😀 🇩🇪👨‍👩‍👧‍👦 – ß, é, €.".to_owned());
    let Some(target) = insertion::target() else {
        eprintln!("no verified editable X11 text field");
        std::process::exit(1);
    };
    // Test-only barrier lets the isolated harness switch widgets *after* capture.
    if let Some(marker) = std::env::var_os("VOICEWRIGHT_PROBE_CAPTURED") {
        std::fs::write(marker, b"captured").expect("write capture marker");
        let release = std::env::var_os("VOICEWRIGHT_PROBE_RELEASE").expect("release marker");
        let started = std::time::Instant::now();
        while !std::path::Path::new(&release).exists() {
            if started.elapsed() > std::time::Duration::from_secs(5) {
                std::process::exit(3);
            }
            std::thread::sleep(std::time::Duration::from_millis(10));
        }
    }
    if let Err(error) = insertion::insert(target, &text, &AtomicBool::new(false)) {
        eprintln!("insertion failed: {error}");
        std::process::exit(1);
    }
    println!("inserted");
}

#[cfg(not(target_os = "linux"))]
fn main() {
    eprintln!("This probe is only available on Linux X11.");
    std::process::exit(2);
}
