#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod app;
mod audio;
mod cleanup;
mod guard;
mod insertion;
mod models;
mod providers;
mod session;
mod settings;
mod settings_portable;
mod speech;
mod spoken_format;

fn main() {
    app::run();
}
