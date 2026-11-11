use crate::{
    audio::{self, Capture},
    cleanup, guard, hotkeys, insertion, models, providers,
    session::{apply_shortcut_changes, Action, HotkeyState, Phase, ShortcutKind, Status},
    settings::{self, CleanupMode, RecordingMode, Settings},
    settings_portable, speech, spoken_format, wayland_output,
};
use serde::Serialize;
use std::{
    fs,
    path::{Path, PathBuf},
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc, Mutex,
    },
    time::Instant,
};
use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    AppHandle, Emitter, Manager, State, WindowEvent,
};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_global_shortcut::{GlobalShortcutExt, Shortcut, ShortcutState};

struct AppState {
    root: PathBuf,
    hardware: Hardware,
    tray_available: AtomicBool,
    clipboard: Mutex<Option<arboard::Clipboard>>,
    output: wayland_output::Controller,
    inner: Mutex<Inner>,
}

const LEGACY_APP_IDENTIFIER: &str = "de.voxtakt.desktop";

fn migrate_legacy_data(root: &Path) {
    if root.exists() {
        return;
    }
    let Some(parent) = root.parent() else {
        return;
    };
    let legacy = parent.join(LEGACY_APP_IDENTIFIER);
    if !legacy.is_dir() {
        return;
    }
    let _ = fs::create_dir_all(parent);
    let _ = fs::rename(legacy, root);
}

struct Inner {
    settings: Settings,
    status: Status,
    capture: Option<Arc<Capture>>,
    shortcut_error: Option<String>,
    shortcut_active: bool,
    shortcut_state: hotkeys::ShortcutStatus,
    shortcut_detail: Option<String>,
    portal: Option<hotkeys::Controller>,
    press: HotkeyState,
    session: u64,
    started_from_hotkey: bool,
    transfer: Option<Arc<AtomicBool>>,
    download: Option<Download>,
}

#[derive(Clone, Serialize)]
struct Download {
    id: String,
    received: u64,
    total: u64,
    active: bool,
    error: Option<String>,
}

#[derive(Clone, Serialize)]
struct Hardware {
    cpu: String,
    threads: usize,
    ram: u64,
}

#[derive(Serialize)]
struct StatusView {
    phase: Phase,
    elapsed_ms: u64,
    level: f32,
    transcript: Option<String>,
    warning: Option<String>,
    inserted: bool,
    shortcut_error: Option<String>,
    shortcut_detail: Option<String>,
    shortcut_active: bool,
    shortcut_state: hotkeys::ShortcutStatus,
    insertion_state: wayland_output::OutputState,
    insertion_detail: Option<String>,
    download: Option<Download>,
    installed: Vec<String>,
}

impl AppState {
    fn models(&self) -> PathBuf {
        self.root.join("models")
    }
    fn settings(&self) -> PathBuf {
        self.root.join("settings.json")
    }
}

#[derive(Serialize)]
struct Initial {
    settings: Settings,
    catalog: &'static [models::Model],
    hardware: Hardware,
    shortcut_backend: hotkeys::Backend,
    shortcut_state: hotkeys::ShortcutStatus,
    insertion_supported: bool,
    insertion_detail: Option<String>,
    insertion_state: wayland_output::OutputState,
    session_type: insertion::SessionKind,
    tray_available: bool,
    model_path: PathBuf,
    default_prompt: &'static str,
}

#[tauri::command]
fn initial(state: State<'_, AppState>) -> Initial {
    let inner = state.inner.lock().unwrap();
    let output = output_status(&state);
    Initial {
        settings: inner.settings.clone(),
        catalog: models::CATALOG,
        hardware: state.hardware.clone(),
        shortcut_backend: hotkeys::backend(),
        shortcut_state: inner.shortcut_state,
        insertion_supported: output.state == wayland_output::OutputState::Ready,
        insertion_detail: output.detail,
        insertion_state: output.state,
        session_type: insertion::session_kind(),
        tray_available: state.tray_available.load(Ordering::Relaxed),
        model_path: state.models(),
        default_prompt: settings::DEFAULT_PROMPT,
    }
}

#[tauri::command]
fn status(state: State<'_, AppState>) -> StatusView {
    let inner = state.inner.lock().unwrap();
    let output = output_status(&state);
    StatusView {
        phase: inner.status.phase,
        elapsed_ms: inner
            .status
            .recording_since
            .map_or(0, |start| start.elapsed().as_millis() as u64),
        level: inner.capture.as_ref().map_or(0.0, |capture| {
            f32::from_bits(capture.level.load(Ordering::Relaxed))
        }),
        transcript: inner.status.transcript.clone(),
        warning: inner.status.warning.clone(),
        inserted: inner.status.inserted,
        shortcut_error: inner.shortcut_error.clone(),
        shortcut_detail: inner.shortcut_detail.clone(),
        shortcut_active: inner.shortcut_active,
        shortcut_state: inner.shortcut_state,
        insertion_state: output.state,
        insertion_detail: output.detail,
        download: inner.download.clone(),
        installed: models::installed(&state.models()),
    }
}

fn output_status(state: &AppState) -> wayland_output::Snapshot {
    if insertion::session_kind() == insertion::SessionKind::Wayland {
        state.output.snapshot()
    } else {
        wayland_output::Snapshot {
            state: if insertion::automatic_supported() {
                wayland_output::OutputState::Ready
            } else {
                wayland_output::OutputState::Unavailable
            },
            detail: insertion::unavailable_reason().map(str::to_owned),
        }
    }
}

#[tauri::command]
fn request_insertion_permission(state: State<'_, AppState>) -> Result<(), String> {
    let inner = state.inner.lock().unwrap();
    if inner.status.phase.busy() {
        return Err("Finish dictation before requesting desktop permission.".into());
    }
    if !inner.settings.wayland_insertion_consent {
        return Err("Enable and save explicit Wayland output consent first.".into());
    }
    drop(inner);
    state.output.request_permission();
    Ok(())
}

#[tauri::command]
fn disable_insertion_permission(state: State<'_, AppState>) {
    state.output.disconnect();
}

#[tauri::command]
async fn microphones() -> Result<Vec<audio::InputDevice>, String> {
    blocking(audio::devices).await
}

async fn blocking<T: Send + 'static>(
    task: impl FnOnce() -> Result<T, String> + Send + 'static,
) -> Result<T, String> {
    tokio::task::spawn_blocking(task)
        .await
        .map_err(|_| "A background operation stopped unexpectedly.")?
}

fn shortcuts(settings: &Settings) -> Vec<Shortcut> {
    [&settings.shortcut, &settings.cancel_shortcut]
        .iter()
        .filter_map(|text| text.parse().ok())
        .collect()
}

fn replace_shortcuts(
    app: &AppHandle,
    previous: &[Shortcut],
    next: &[Shortcut],
) -> Result<(), String> {
    match hotkeys::backend() {
        hotkeys::Backend::X11 | hotkeys::Backend::Native => apply_shortcut_changes(
            previous,
            next,
            &|shortcut| app.global_shortcut().register(shortcut).is_ok(),
            &|shortcut| app.global_shortcut().unregister(shortcut).is_ok(),
        ),
        hotkeys::Backend::Portal | hotkeys::Backend::Unsupported => Ok(()),
    }
}

#[tauri::command]
fn save_settings(
    app: AppHandle,
    state: State<'_, AppState>,
    value: Settings,
) -> Result<(), String> {
    value.validate()?;
    let mut inner = state.inner.lock().unwrap();
    if inner.status.phase.busy() {
        return Err("Finish the current dictation before saving settings.".into());
    }
    let backend = hotkeys::backend();
    let native = matches!(backend, hotkeys::Backend::X11 | hotkeys::Backend::Native);
    let rebind_portal = should_rebind_shortcuts(&inner.settings, &value);
    let previous = if native && inner.shortcut_active {
        shortcuts(&inner.settings)
    } else {
        Vec::new()
    };
    let next = shortcuts(&value);
    if native {
        replace_shortcuts(&app, &previous, &next)?;
    }
    if let Err(error) = settings::save(&state.settings(), &value) {
        if native {
            let rollback = replace_shortcuts(&app, &next, &previous);
            if rollback.is_err() {
                inner.shortcut_error = Some("Could not restore the previous shortcuts.".into());
                inner.shortcut_active = false;
                inner.shortcut_state = hotkeys::ShortcutStatus::Error;
            }
        }
        return Err(error);
    }
    let request_output = value.auto_insert
        && value.wayland_insertion_consent
        && !inner.settings.wayland_insertion_consent;
    let disable_output = !value.auto_insert || !value.wayland_insertion_consent;
    inner.settings = value;
    inner.press.reset();
    match backend {
        hotkeys::Backend::X11 | hotkeys::Backend::Native => {
            inner.shortcut_error = None;
            inner.shortcut_detail = None;
            inner.shortcut_active = true;
            inner.shortcut_state = hotkeys::ShortcutStatus::Active;
        }
        hotkeys::Backend::Portal => {
            if rebind_portal {
                if let Some(portal) = &inner.portal {
                    portal.rebind(hotkeys::bindings(&inner.settings));
                }
                inner.shortcut_error = None;
                inner.shortcut_detail = None;
                inner.shortcut_active = false;
                inner.shortcut_state = hotkeys::ShortcutStatus::Pending;
            }
        }
        hotkeys::Backend::Unsupported => {
            inner.shortcut_error = None;
            inner.shortcut_detail = None;
            inner.shortcut_active = false;
            inner.shortcut_state = hotkeys::ShortcutStatus::Unavailable;
        }
    }
    drop(inner);
    if disable_output {
        state.output.disconnect();
    } else if request_output {
        state.output.request_permission();
    }
    Ok(())
}

fn should_rebind_shortcuts(before: &Settings, after: &Settings) -> bool {
    hotkeys::bindings(before) != hotkeys::bindings(after)
}

#[tauri::command]
fn retry_shortcuts(state: State<'_, AppState>) -> Result<(), String> {
    if hotkeys::backend() != hotkeys::Backend::Portal {
        return Ok(());
    }
    let mut inner = state.inner.lock().unwrap();
    let Some(portal) = &inner.portal else {
        return Err("The desktop shortcut portal is not running.".into());
    };
    portal.rebind(hotkeys::bindings(&inner.settings));
    inner.shortcut_state = hotkeys::ShortcutStatus::Pending;
    inner.shortcut_active = false;
    inner.shortcut_detail = None;
    inner.shortcut_error = None;
    Ok(())
}

#[tauri::command]
async fn preview_cleanup(
    app: AppHandle,
    value: Settings,
    transcript: String,
) -> Result<String, String> {
    value.validate()?;
    if transcript.trim().is_empty() || transcript.len() > 8_192 {
        return Err("Enter a short, non-empty sample dictation.".into());
    }
    let state = app.state::<AppState>();
    {
        let inner = state.inner.lock().unwrap();
        if inner.status.phase.busy() || inner.transfer.is_some() {
            return Err("Finish dictation or model operations before testing the prompt.".into());
        }
    }
    let system = value.system_prompt();
    let cancelled = AtomicBool::new(false);
    let edited = match value.cleanup_mode {
        CleanupMode::Off => return Err("Enable local or cloud editing to test the prompt.".into()),
        CleanupMode::Local => {
            let model = models::ready(&state.models(), &value.cleanup_model)?;
            cleanup::local(&model, &system, &transcript, &cancelled).await?
        }
        CleanupMode::Cloud => {
            let provider = value
                .providers
                .get(&value.active_provider)
                .ok_or("Configure the chosen cloud provider first.")?;
            providers::cleanup(provider, &system, &transcript).await?
        }
    };
    let translated = !value.translation.trim().is_empty();
    guard::validate_with(
        &transcript,
        edited,
        value.requires_strict_cleanup() && !translated,
        translated,
    )
}

#[tauri::command]
fn default_settings() -> Settings {
    // Does not touch API keys, installed models, or the current on-disk config.
    Settings::default()
}

#[tauri::command]
async fn export_settings(app: AppHandle) -> Result<bool, String> {
    let current = {
        let state = app.state::<AppState>();
        let inner = state.inner.lock().unwrap();
        if inner.status.phase.busy() {
            return Err("Finish the current dictation before exporting settings.".into());
        }
        inner.settings.clone()
    };
    blocking(move || {
        let chosen = app
            .dialog()
            .file()
            .add_filter("JSON", &["json"])
            .blocking_save_file();
        let Some(file) = chosen else {
            return Ok(false);
        };
        let path = file
            .into_path()
            .map_err(|_| "Choose a local export destination.".to_owned())?;
        settings_portable::export(&path, &current)?;
        Ok(true)
    })
    .await
}

#[tauri::command]
async fn import_settings_preview(app: AppHandle) -> Result<Option<Settings>, String> {
    {
        let state = app.state::<AppState>();
        let inner = state.inner.lock().unwrap();
        if inner.status.phase.busy() || inner.transfer.is_some() {
            return Err("Finish dictation and model operations before importing settings.".into());
        }
    }
    blocking(move || {
        let chosen = app
            .dialog()
            .file()
            .add_filter("JSON", &["json"])
            .blocking_pick_file();
        let Some(file) = chosen else {
            return Ok(None);
        };
        let path = file
            .into_path()
            .map_err(|_| "Choose a local settings file.".to_owned())?;
        let metadata = fs::symlink_metadata(&path)
            .map_err(|_| "Could not inspect the settings import.".to_owned())?;
        if !metadata.is_file() || metadata.len() > 256 * 1024 {
            return Err("The import must be a regular JSON file under 256 KiB.".into());
        }
        let bytes = fs::read(&path)
            .map_err(|_| "Could not read the selected settings export.".to_owned())?;
        Ok(Some(settings_portable::import(&bytes)?))
    })
    .await
}

#[derive(Clone, Copy)]
enum OutputTarget {
    Native(insertion::Target),
    Wayland,
}

fn start_session(app: &AppHandle, from_hotkey: bool) -> Result<(), String> {
    let state = app.state::<AppState>();
    let mut inner = state.inner.lock().unwrap();
    if inner.status.phase.busy() {
        return Err("A dictation is already in progress.".into());
    }
    if inner.transfer.is_some() && !inner.download.as_ref().is_some_and(|item| item.active) {
        return Err("Finish importing the model before recording.".into());
    }
    let settings = inner.settings.clone();
    let root = state.models();
    let speech_model = models::ready(&root, &settings.speech_model)?;
    let target = if from_hotkey && settings.auto_insert {
        if insertion::session_kind() == insertion::SessionKind::Wayland {
            (settings.wayland_insertion_consent
                && state.output.snapshot().state == wayland_output::OutputState::Ready)
                .then_some(OutputTarget::Wayland)
        } else if insertion::automatic_supported() {
            insertion::target().map(OutputTarget::Native)
        } else {
            None
        }
    } else {
        None
    };
    let control = Arc::new(Capture::default());
    inner.session = inner.session.wrapping_add(1);
    let session = inner.session;
    inner.capture = Some(control.clone());
    inner.started_from_hotkey = from_hotkey;
    inner.status.phase = Phase::Recording;
    inner.status.recording_since = Some(Instant::now());
    inner.status.warning = None;
    inner.status.inserted = false;
    drop(inner);
    set_tray_status(app, Phase::Recording, false);
    let app = app.clone();
    tauri::async_runtime::spawn(async move {
        let result = pipeline(
            &app,
            &settings,
            &root,
            &speech_model,
            target,
            control.clone(),
            session,
        )
        .await;
        let state = app.state::<AppState>();
        let mut inner = state.inner.lock().unwrap();
        if inner.session != session {
            return;
        }
        inner.status.recording_since = None;
        inner.capture = None;
        if control.cancelled.load(Ordering::Relaxed) {
            inner.status.phase = Phase::Cancelled;
        } else {
            match result {
                Ok(()) => inner.status.phase = Phase::Completed,
                Err(error) => {
                    inner.status.phase = Phase::Failed;
                    inner.status.warning = Some(error);
                }
            }
        }
        let phase = inner.status.phase;
        let warning = inner.status.warning.is_some();
        drop(inner);
        set_tray_status(&app, phase, warning);
    });
    Ok(())
}

fn set_tray_status(app: &AppHandle, phase: Phase, has_warning: bool) {
    let Some(tray) = app.tray_by_id("main") else {
        return;
    };
    let text = match phase {
        Phase::Recording => "Voicewright · ● Aufnahme / Recording",
        Phase::Transcribing => "Voicewright · Spracherkennung / Transcribing",
        Phase::Cleaning => "Voicewright · Textkorrektur / Editing",
        Phase::Failed => "Voicewright · Fehler / Error",
        Phase::Completed if has_warning => "Voicewright · Text zum Kopieren / Text ready to copy",
        _ => "Voicewright",
    };
    let _ = tray.set_tooltip(Some(text));
    let image = if phase == Phase::Recording {
        Some(tauri::include_image!("icons/recording.png"))
    } else {
        app.default_window_icon().cloned()
    };
    let _ = tray.set_icon(image);
}

fn set_phase(app: &AppHandle, session: u64, phase: Phase) {
    let state = app.state::<AppState>();
    let mut inner = state.inner.lock().unwrap();
    if inner.session != session {
        return;
    }
    inner.status.phase = phase;
    inner.status.recording_since = None;
    drop(inner);
    set_tray_status(app, phase, false);
}

fn current_session(app: &AppHandle, session: u64) -> bool {
    app.state::<AppState>().inner.lock().unwrap().session == session
}

async fn pipeline(
    app: &AppHandle,
    settings: &Settings,
    model_root: &Path,
    speech_model: &Path,
    target: Option<OutputTarget>,
    control: Arc<Capture>,
    session: u64,
) -> Result<(), String> {
    let device = settings.microphone.clone();
    let capture = control.clone();
    let audio = blocking(move || audio::record(device.as_deref(), capture)).await?;
    if control.cancelled.load(Ordering::Relaxed) || !current_session(app, session) {
        return Ok(());
    }
    if !audio::has_voice(&audio) {
        return Err("No speech was detected.".into());
    }
    set_phase(app, session, Phase::Transcribing);
    let model = speech_model.to_owned();
    let language = settings.speech_language.clone();
    let vocabulary = settings.vocabulary.clone();
    let capture = control.clone();
    let transcript = blocking(move || {
        speech::transcribe(&model, &audio, &language, &vocabulary, &capture.cancelled)
    })
    .await?;
    if control.cancelled.load(Ordering::Relaxed) || !current_session(app, session) {
        return Ok(());
    }
    if transcript.is_empty() {
        return Err("No speech was detected.".into());
    }
    // Deterministic, local and opt-in; never interprets text as an OS action.
    // Captured settings belong to this session, so toggling cannot race a dictation.
    let transcript = spoken_format::format(&transcript, settings.spoken_formatting);

    let state = app.state::<AppState>();
    {
        let mut inner = state.inner.lock().unwrap();
        if inner.session != session {
            return Ok(());
        }
        inner.status.transcript = Some(transcript.clone());
    }
    let mut warning = None;
    let result = if settings.cleanup_mode == CleanupMode::Off {
        transcript
    } else {
        set_phase(app, session, Phase::Cleaning);
        let system = settings.system_prompt();
        let edited = match settings.cleanup_mode {
            CleanupMode::Local => match models::ready(model_root, &settings.cleanup_model) {
                Ok(model) => cleanup::local(&model, &system, &transcript, &control.cancelled).await,
                Err(error) => Err(error),
            },
            CleanupMode::Cloud => match settings.providers.get(&settings.active_provider) {
                Some(provider) => tokio::select! {
                    _ = cleanup::wait_for_cancel(&control.cancelled) => return Ok(()),
                    result = providers::cleanup(provider, &system, &transcript) => result,
                },
                None => Err("The selected cleanup provider is missing.".into()),
            },
            CleanupMode::Off => unreachable!(),
        };
        if control.cancelled.load(Ordering::Relaxed) || !current_session(app, session) {
            return Ok(());
        }
        let translated = !settings.translation.trim().is_empty();
        match edited.and_then(|text| {
            guard::validate_with(
                &transcript,
                text,
                settings.requires_strict_cleanup() && !translated,
                translated,
            )
        }) {
            Ok(text) => text,
            Err(error) if settings.fallback => {
                warning = Some(format!("Cleanup failed. Original text retained. {error}"));
                transcript
            }
            Err(error) => {
                return Err(format!(
                    "Cleanup failed. Original text is available to copy. {error}"
                ))
            }
        }
    };
    let from_hotkey = {
        let mut inner = state.inner.lock().unwrap();
        if inner.session != session {
            return Ok(());
        }
        inner.status.transcript = Some(result.clone());
        inner.started_from_hotkey
    };
    if let Some(target) = target {
        set_phase(app, session, Phase::Inserting);
        if !current_session(app, session) {
            return Ok(());
        }
        let capture = control.clone();
        let inserted = match target {
            OutputTarget::Native(target) => {
                blocking(move || {
                    insertion::insert(target, &result, &capture.cancelled).map_err(str::to_owned)
                })
                .await
            }
            OutputTarget::Wayland => state.output.insert(result.clone(), capture).await,
        };
        let mut inner = state.inner.lock().unwrap();
        if inner.session != session {
            return Ok(());
        }
        match inserted {
            Ok(()) => inner.status.inserted = true,
            Err(error) => append_warning(&mut warning, error),
        }
    } else if from_hotkey {
        let message = if !settings.auto_insert {
            "The result is available to copy in Voicewright."
        } else {
            if insertion::session_kind() == insertion::SessionKind::Wayland {
                "Wayland output permission is not ready. The result is available to copy."
            } else {
                insertion::unavailable_reason().unwrap_or(
                "The target window could not be verified. The result is available to copy in Voicewright.",
            )
            }
        };
        append_warning(&mut warning, message.into());
    }
    let mut inner = state.inner.lock().unwrap();
    if inner.session == session {
        inner.status.warning = warning;
    }
    Ok(())
}

fn append_warning(warning: &mut Option<String>, message: String) {
    if let Some(existing) = warning {
        existing.push(' ');
        existing.push_str(&message);
    } else {
        *warning = Some(message);
    }
}

fn fail_shortcut(app: &AppHandle, error: String) {
    let state = app.state::<AppState>();
    let mut inner = state.inner.lock().unwrap();
    if inner.status.phase.busy() {
        return;
    }
    inner.status.phase = Phase::Failed;
    inner.status.warning = Some(error);
    drop(inner);
    set_tray_status(app, Phase::Failed, true);
}

fn shortcut_kind(settings: &Settings, shortcut: &Shortcut) -> Option<ShortcutKind> {
    if settings
        .cancel_shortcut
        .parse::<Shortcut>()
        .is_ok_and(|cancel| cancel.id() == shortcut.id())
    {
        Some(ShortcutKind::Cancel)
    } else if settings
        .shortcut
        .parse::<Shortcut>()
        .is_ok_and(|current| current.id() == shortcut.id())
    {
        Some(ShortcutKind::Dictation)
    } else {
        None
    }
}

fn handle_shortcut(app: &AppHandle, shortcut: &Shortcut, state: ShortcutState) {
    let app_state = app.state::<AppState>();
    let kind = {
        let inner = app_state.inner.lock().unwrap();
        shortcut_kind(&inner.settings, shortcut)
    };
    if let Some(kind) = kind {
        handle_shortcut_kind(app, kind, state == ShortcutState::Pressed);
    }
}

fn portal_shortcut_kind(id: &str) -> Option<ShortcutKind> {
    match id {
        "dictation" => Some(ShortcutKind::Dictation),
        "cancel" => Some(ShortcutKind::Cancel),
        _ => None,
    }
}

fn set_shortcut_status(app: &AppHandle, state: hotkeys::ShortcutStatus, detail: Option<String>) {
    let app_state = app.state::<AppState>();
    let mut inner = app_state.inner.lock().unwrap();
    inner.shortcut_state = state;
    inner.shortcut_active = state == hotkeys::ShortcutStatus::Active;
    inner.shortcut_detail = detail.clone();
    inner.shortcut_error = match state {
        hotkeys::ShortcutStatus::Pending
        | hotkeys::ShortcutStatus::Active
        | hotkeys::ShortcutStatus::Unknown => None,
        _ => detail,
    };
}

fn handle_shortcut_kind(app: &AppHandle, kind: ShortcutKind, pressed: bool) {
    let app_state = app.state::<AppState>();
    let mut inner = app_state.inner.lock().unwrap();
    let hold = inner.settings.recording_mode == RecordingMode::Hold;
    let phase = inner.status.phase;
    match inner.press.change(kind, pressed, hold, phase) {
        Some(Action::Start) => {
            drop(inner);
            if let Err(error) = start_session(app, true) {
                fail_shortcut(app, error);
            }
        }
        Some(Action::Stop) if inner.started_from_hotkey => {
            if let Some(capture) = &inner.capture {
                capture.stop.store(true, Ordering::Relaxed);
            }
        }
        Some(Action::Cancel) => {
            drop(inner);
            cancel(app.clone());
        }
        _ => {}
    }
}

#[tauri::command]
fn start_test(app: AppHandle) -> Result<(), String> {
    start_session(&app, false)
}

#[tauri::command]
fn stop(state: State<'_, AppState>) {
    let inner = state.inner.lock().unwrap();
    if inner.status.phase == Phase::Recording {
        if let Some(capture) = &inner.capture {
            capture.stop.store(true, Ordering::Relaxed);
        }
    }
}

#[tauri::command]
fn cancel(app: AppHandle) {
    let state = app.state::<AppState>();
    let mut inner = state.inner.lock().unwrap();
    if !inner.status.phase.busy() {
        return;
    }
    if let Some(capture) = &inner.capture {
        capture.cancelled.store(true, Ordering::Relaxed);
        capture.stop.store(true, Ordering::Relaxed);
    }
    // Invalidate the running pipeline before releasing the lock. A late
    // result must neither overwrite this state nor insert text.
    inner.session = inner.session.wrapping_add(1);
    inner.capture = None;
    inner.status.recording_since = None;
    inner.status.phase = Phase::Cancelled;
    inner.status.inserted = false;
    drop(inner);
    set_tray_status(&app, Phase::Cancelled, false);
}

#[tauri::command]
fn clear_result(state: State<'_, AppState>) {
    let mut inner = state.inner.lock().unwrap();
    if !inner.status.phase.busy() {
        inner.status = Status::default();
    }
}

#[tauri::command]
async fn copy_result(app: AppHandle) -> Result<(), String> {
    blocking(move || {
        let state = app.state::<AppState>();
        let text = state
            .inner
            .lock()
            .unwrap()
            .status
            .transcript
            .clone()
            .ok_or("There is no result to copy.")?;
        let mut clipboard = state.clipboard.lock().unwrap();
        if clipboard.is_none() {
            *clipboard = Some(
                arboard::Clipboard::new().map_err(|_| "The system clipboard is unavailable.")?,
            );
        }
        clipboard
            .as_mut()
            .unwrap()
            .set_text(text)
            .map_err(|_| "Could not copy the result.".into())
    })
    .await
}

#[tauri::command]
fn download_model(app: AppHandle, id: String) -> Result<(), String> {
    let state = app.state::<AppState>();
    models::catalog_entry(&id)?;
    let root = state.models();
    let mut inner = state.inner.lock().unwrap();
    if inner.transfer.is_some() {
        return Err("A model operation is already in progress.".into());
    }
    if models::ready(&root, &id).is_ok() {
        return Ok(());
    }
    let cancel = Arc::new(AtomicBool::new(false));
    inner.transfer = Some(cancel.clone());
    inner.download = Some(Download {
        id: id.clone(),
        received: 0,
        total: 0,
        active: true,
        error: None,
    });
    drop(inner);
    tauri::async_runtime::spawn(async move {
        let result = models::download(&root, &id, cancel, |received, total| {
            let state = app.state::<AppState>();
            if let Some(download) = state.inner.lock().unwrap().download.as_mut() {
                download.received = received;
                download.total = total;
            };
        })
        .await;
        let state = app.state::<AppState>();
        let mut inner = state.inner.lock().unwrap();
        inner.transfer = None;
        if let Some(download) = inner.download.as_mut() {
            download.active = false;
            download.error = result.err();
        }
    });
    Ok(())
}

#[tauri::command]
fn cancel_download(state: State<'_, AppState>) {
    let inner = state.inner.lock().unwrap();
    if inner.download.as_ref().is_some_and(|item| item.active) {
        if let Some(cancel) = &inner.transfer {
            cancel.store(true, Ordering::Relaxed);
        }
    }
}

#[tauri::command]
fn delete_model(state: State<'_, AppState>, id: String) -> Result<(), String> {
    let inner = state.inner.lock().unwrap();
    if inner.status.phase.busy() || inner.transfer.is_some() {
        return Err("Wait for dictation and model operations to finish.".into());
    }
    models::remove(&state.models(), &id)
}

#[tauri::command]
async fn import_model(app: AppHandle, kind: models::Kind) -> Result<(), String> {
    blocking(move || {
        let state = app.state::<AppState>();
        {
            let mut inner = state.inner.lock().unwrap();
            if inner.transfer.is_some() || inner.status.phase.busy() {
                return Err("Wait for dictation and model operations to finish.".into());
            }
            inner.transfer = Some(Arc::new(AtomicBool::new(false)));
        }
        let (label, extension) = match kind {
            models::Kind::Speech => ("Whisper GGML", "bin"),
            models::Kind::Cleanup => ("Qwen3 GGUF", "gguf"),
        };
        let chosen = app
            .dialog()
            .file()
            .add_filter(label, &[extension])
            .blocking_pick_file();
        let result = match chosen {
            Some(file) => file
                .into_path()
                .map_err(|_| "The selected file is not local.".into())
                .and_then(|path| {
                    let inner = state.inner.lock().unwrap();
                    if inner.status.phase.busy() {
                        return Err("Finish dictation before importing a model.".into());
                    }
                    drop(inner);
                    models::import(&state.models(), &path, kind)
                }),
            None => Ok(()),
        };
        state.inner.lock().unwrap().transfer = None;
        result
    })
    .await
}

#[tauri::command]
async fn provider_key(
    config: providers::ProviderConfig,
    key: Option<String>,
) -> Result<bool, String> {
    blocking(move || {
        if let Some(key) = key {
            providers::set_key(&config, &key)?;
        }
        providers::has_key(&config)
    })
    .await
}

#[tauri::command]
async fn forget_key(config: providers::ProviderConfig) -> Result<(), String> {
    blocking(move || providers::delete_key(&config)).await
}

#[tauri::command]
async fn provider_models(config: providers::ProviderConfig) -> Result<Vec<String>, String> {
    providers::models(&config).await
}

#[tauri::command]
async fn provider_test(config: providers::ProviderConfig) -> Result<(), String> {
    providers::test_connection(&config).await
}

fn show(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.set_focus();
    }
}

fn tray(app: &AppHandle) -> tauri::Result<()> {
    let open = MenuItem::with_id(app, "open", "Voicewright öffnen / Open", true, None::<&str>)?;
    let stop_item = MenuItem::with_id(app, "stop", "Aufnahme beenden / Stop", true, None::<&str>)?;
    let cancel_item = MenuItem::with_id(
        app,
        "cancel",
        "Diktat abbrechen / Cancel",
        true,
        None::<&str>,
    )?;
    let copy = MenuItem::with_id(app, "copy", "Text kopieren / Copy", true, None::<&str>)?;
    let quit = MenuItem::with_id(app, "quit", "Beenden / Quit", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&open, &stop_item, &cancel_item, &copy, &quit])?;
    let mut tray = TrayIconBuilder::with_id("main")
        .menu(&menu)
        .tooltip("Voicewright")
        .on_menu_event(|app, event| match event.id().as_ref() {
            "open" => show(app),
            "stop" => stop(app.state()),
            "cancel" => cancel(app.clone()),
            "copy" => {
                let handle = app.clone();
                tauri::async_runtime::spawn(async move {
                    if copy_result(handle.clone()).await.is_err() {
                        show(&handle);
                    }
                });
            }
            "quit" => app.exit(0),
            _ => {}
        });
    if let Some(icon) = app.default_window_icon() {
        tray = tray.icon(icon.clone());
    }
    tray.build(app)?;
    Ok(())
}

pub fn run() {
    whisper_rs::install_logging_hooks();
    let backend = hotkeys::backend();
    let mut builder = tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _, _| show(app)))
        .plugin(tauri_plugin_dialog::init());
    if matches!(backend, hotkeys::Backend::X11 | hotkeys::Backend::Native) {
        builder = builder.plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_handler(|app, shortcut, event| {
                    let handle = app.clone();
                    let shortcut = *shortcut;
                    let _ = app.run_on_main_thread(move || {
                        handle_shortcut(&handle, &shortcut, event.state)
                    });
                })
                .build(),
        );
    }
    builder
        .setup(move |app| {
            let root = app.path().app_data_dir()?;
            migrate_legacy_data(&root);
            let mut status = Status::default();
            let settings = settings::load(&root.join("settings.json")).unwrap_or_else(|error| {
                status.warning = Some(error);
                Settings::default()
            });
            let next = shortcuts(&settings);
            let portal_bindings = if backend == hotkeys::Backend::Portal {
                Some(hotkeys::bindings(&settings))
            } else {
                None
            };
            let initial_shortcut_state = match backend {
                hotkeys::Backend::Portal => hotkeys::ShortcutStatus::Pending,
                hotkeys::Backend::Unsupported => hotkeys::ShortcutStatus::Unavailable,
                hotkeys::Backend::X11 | hotkeys::Backend::Native => {
                    hotkeys::ShortcutStatus::Unknown
                }
            };
            let system = sysinfo::System::new_all();
            let (output, mut output_events) = wayland_output::start();
            let request_output = settings.auto_insert && settings.wayland_insertion_consent;
            app.manage(AppState {
                root,
                hardware: Hardware {
                    cpu: system
                        .cpus()
                        .first()
                        .map_or_else(String::new, |cpu| cpu.brand().to_owned()),
                    threads: system.cpus().len(),
                    ram: system.total_memory(),
                },
                tray_available: AtomicBool::new(false),
                clipboard: Mutex::new(None),
                output,
                inner: Mutex::new(Inner {
                    settings,
                    status,
                    capture: None,
                    press: HotkeyState::default(),
                    session: 0,
                    shortcut_error: None,
                    shortcut_active: false,
                    shortcut_state: initial_shortcut_state,
                    shortcut_detail: None,
                    portal: None,
                    started_from_hotkey: false,
                    transfer: None,
                    download: None,
                }),
            });
            let state = app.state::<AppState>();
            let event_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                while let Some(snapshot) = output_events.recv().await {
                    let _ = event_handle.emit("insertion-status", snapshot);
                }
            });
            if request_output {
                state.output.request_permission();
            }
            state
                .tray_available
                .store(tray(app.handle()).is_ok(), Ordering::Relaxed);
            match backend {
                hotkeys::Backend::X11 | hotkeys::Backend::Native => {
                    let shortcut_result = replace_shortcuts(app.handle(), &[], &next);
                    let mut inner = state.inner.lock().unwrap();
                    inner.shortcut_active = shortcut_result.is_ok();
                    inner.shortcut_state = if shortcut_result.is_ok() {
                        hotkeys::ShortcutStatus::Active
                    } else {
                        hotkeys::ShortcutStatus::Error
                    };
                    inner.shortcut_error = shortcut_result.err();
                }
                hotkeys::Backend::Portal => {
                    let (controller, mut events) =
                        hotkeys::start(portal_bindings.unwrap_or_default());
                    state.inner.lock().unwrap().portal = Some(controller);
                    let handle = app.handle().clone();
                    tauri::async_runtime::spawn(async move {
                        while let Some(event) = events.recv().await {
                            match event {
                                hotkeys::Event::Status(status, detail) => {
                                    set_shortcut_status(&handle, status, detail);
                                }
                                hotkeys::Event::Pressed(id) => {
                                    if let Some(kind) = portal_shortcut_kind(id) {
                                        let target = handle.clone();
                                        let _ = handle.run_on_main_thread(move || {
                                            handle_shortcut_kind(&target, kind, true);
                                        });
                                    }
                                }
                                hotkeys::Event::Released(id) => {
                                    if let Some(kind) = portal_shortcut_kind(id) {
                                        let target = handle.clone();
                                        let _ = handle.run_on_main_thread(move || {
                                            handle_shortcut_kind(&target, kind, false);
                                        });
                                    }
                                }
                            }
                        }
                    });
                }
                hotkeys::Backend::Unsupported => {}
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                let state = window.state::<AppState>();
                if state.tray_available.load(Ordering::Relaxed) {
                    api.prevent_close();
                    let _ = window.hide();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            initial,
            status,
            microphones,
            save_settings,
            default_settings,
            export_settings,
            import_settings_preview,
            retry_shortcuts,
            request_insertion_permission,
            disable_insertion_permission,
            preview_cleanup,
            start_test,
            stop,
            cancel,
            clear_result,
            copy_result,
            download_model,
            cancel_download,
            delete_model,
            import_model,
            provider_key,
            forget_key,
            provider_models,
            provider_test
        ])
        .run(tauri::generate_context!())
        .expect("Voicewright desktop runtime failed");
}

#[cfg(test)]
mod tests {
    use super::*;

    const APP_IDENTIFIER: &str = "de.voicewright.desktop";

    #[test]
    fn saving_output_permission_does_not_reopen_shortcut_dialogs() {
        let before = Settings::default();
        let mut after = before.clone();
        after.wayland_insertion_consent = true;
        assert!(!should_rebind_shortcuts(&before, &after));
        after.shortcut = "Ctrl+Alt+D".into();
        assert!(should_rebind_shortcuts(&before, &after));
    }

    #[test]
    fn moves_legacy_app_data_only_when_the_new_directory_is_absent() {
        let directory = tempfile::tempdir().unwrap();
        let root = directory.path().join(APP_IDENTIFIER);
        let legacy = directory.path().join(LEGACY_APP_IDENTIFIER);
        fs::create_dir_all(&legacy).unwrap();
        fs::write(legacy.join("settings.json"), b"{}").unwrap();

        migrate_legacy_data(&root);
        assert!(root.join("settings.json").is_file());
        assert!(!legacy.exists());

        fs::write(root.join("settings.json"), b"{\"current\":true}").unwrap();
        fs::create_dir_all(&legacy).unwrap();
        fs::write(legacy.join("settings.json"), b"{\"legacy\":true}").unwrap();
        migrate_legacy_data(&root);
        assert_eq!(
            fs::read_to_string(root.join("settings.json")).unwrap(),
            "{\"current\":true}"
        );
        assert!(legacy.exists());
    }
}
