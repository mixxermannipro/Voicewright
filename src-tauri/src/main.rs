#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod app;
mod audio;
mod cleanup;
mod desktop_integration;
#[cfg(target_os = "linux")]
mod eis_text;
mod guard;
mod hotkeys;
mod insertion;
mod models;
mod providers;
mod session;
mod settings;
mod settings_portable;
mod speech;
mod spoken_format;
mod wayland_output;

fn main() {
    app::run();
}
