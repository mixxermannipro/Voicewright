#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod app;
mod audio;
mod cleanup;
mod insertion;
mod models;
mod providers;
mod session;
mod settings;
mod speech;

fn main() {
    app::run();
}
