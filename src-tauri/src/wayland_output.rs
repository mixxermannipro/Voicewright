//! Explicit permission and bounded, cancellable Wayland text output.

use crate::audio::Capture;
use serde::Serialize;
use std::sync::{
    atomic::{AtomicU64, Ordering},
    mpsc::{sync_channel, SyncSender},
    Arc, Mutex,
};
use tokio::sync::{mpsc, oneshot, watch};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum OutputState {
    Unavailable,
    Disabled,
    Pending,
    Ready,
    Denied,
    Error,
}

#[derive(Clone, Debug, Serialize)]
pub struct Snapshot {
    pub state: OutputState,
    pub detail: Option<String>,
}

struct Job {
    text: String,
    cancelled: Arc<Capture>,
    reply: oneshot::Sender<Result<(), String>>,
}
struct Inner {
    snapshot: Snapshot,
    available: bool,
    output: Option<SyncSender<Job>>,
}
struct Shared {
    inner: Mutex<Inner>,
    epoch: AtomicU64,
    changes: watch::Sender<u64>,
    events: mpsc::UnboundedSender<Snapshot>,
}

#[derive(Clone)]
pub struct Controller {
    shared: Arc<Shared>,
}

fn controller(available: bool, events: mpsc::UnboundedSender<Snapshot>) -> Controller {
    let (changes, _) = watch::channel(0);
    Controller {
        shared: Arc::new(Shared {
            inner: Mutex::new(Inner {
                snapshot: Snapshot {
                    state: if available {
                        OutputState::Disabled
                    } else {
                        OutputState::Unavailable
                    },
                    detail: None,
                },
                available,
                output: None,
            }),
            epoch: AtomicU64::new(0),
            changes,
            events,
        }),
    }
}

impl Controller {
    pub fn snapshot(&self) -> Snapshot {
        self.shared.inner.lock().unwrap().snapshot.clone()
    }
    fn begin_permission(&self) -> Option<u64> {
        let mut inner = self.shared.inner.lock().unwrap();
        if !inner.available
            || matches!(
                inner.snapshot.state,
                OutputState::Pending | OutputState::Ready
            )
        {
            return None;
        }
        let epoch = self
            .shared
            .epoch
            .fetch_add(1, Ordering::SeqCst)
            .wrapping_add(1);
        inner.output = None;
        inner.snapshot = Snapshot {
            state: OutputState::Pending,
            detail: None,
        };
        let _ = self.shared.events.send(inner.snapshot.clone());
        self.shared.changes.send_replace(epoch);
        Some(epoch)
    }
    pub fn request_permission(&self) {
        if let Some(epoch) = self.begin_permission() {
            #[cfg(target_os = "linux")]
            {
                let output = self.clone();
                tauri::async_runtime::spawn(async move {
                    linux::connect(output, epoch).await;
                });
            }
            #[cfg(not(target_os = "linux"))]
            let _ = epoch;
        }
    }
    pub fn disconnect(&self) {
        let mut inner = self.shared.inner.lock().unwrap();
        let epoch = self
            .shared
            .epoch
            .fetch_add(1, Ordering::SeqCst)
            .wrapping_add(1);
        inner.output = None;
        inner.snapshot = Snapshot {
            state: if inner.available {
                OutputState::Disabled
            } else {
                OutputState::Unavailable
            },
            detail: None,
        };
        self.shared.changes.send_replace(epoch);
        let _ = self.shared.events.send(inner.snapshot.clone());
    }
    pub async fn insert(&self, text: String, cancelled: Arc<Capture>) -> Result<(), String> {
        if cancelled.cancelled.load(Ordering::SeqCst) {
            return Err("Text output cancelled".into());
        }
        let output = {
            let inner = self.shared.inner.lock().unwrap();
            if inner.snapshot.state != OutputState::Ready {
                return Err("Wayland output permission is not ready".into());
            }
            inner
                .output
                .clone()
                .ok_or("Desktop text connection is unavailable")?
        };
        let (reply, receiver) = oneshot::channel();
        output
            .try_send(Job {
                text,
                cancelled,
                reply,
            })
            .map_err(|_| "Desktop text output is busy or disconnected")?;
        receiver
            .await
            .map_err(|_| "Desktop text worker stopped".to_owned())?
    }

    #[cfg(target_os = "linux")]
    fn update(
        &self,
        epoch: u64,
        state: OutputState,
        detail: Option<String>,
        output: Option<SyncSender<Job>>,
    ) {
        let mut inner = self.shared.inner.lock().unwrap();
        if self.shared.epoch.load(Ordering::SeqCst) != epoch {
            return;
        }
        inner.output = output;
        inner.snapshot = Snapshot { state, detail };
        let _ = self.shared.events.send(inner.snapshot.clone());
    }
}

pub fn start() -> (Controller, mpsc::UnboundedReceiver<Snapshot>) {
    let (sender, receiver) = mpsc::unbounded_channel();
    let available = {
        #[cfg(target_os = "linux")]
        {
            crate::insertion::session_kind() == crate::insertion::SessionKind::Wayland
                && crate::eis_text::available().is_ok()
        }
        #[cfg(not(target_os = "linux"))]
        {
            false
        }
    };
    (controller(available, sender), receiver)
}

#[cfg(target_os = "linux")]
mod linux {
    use super::*;
    use ashpd::desktop::{
        remote_desktop::{DeviceType, RemoteDesktop, SelectDevicesOptions},
        PersistMode,
    };
    use futures_util::{pin_mut, StreamExt};
    use std::{sync::mpsc::RecvTimeoutError, time::Duration};

    enum WorkerEvent {
        Ready,
        Failed(String),
    }

    pub async fn connect(output: Controller, epoch: u64) {
        let result = connection(&output, epoch).await;
        if let Err(error) = result {
            let state = if error == "Desktop output permission was denied or cancelled" {
                OutputState::Denied
            } else {
                OutputState::Error
            };
            output.update(epoch, state, Some(error), None);
        }
    }

    async fn connection(output: &Controller, epoch: u64) -> Result<(), String> {
        let remote = tokio::time::timeout(Duration::from_secs(10), RemoteDesktop::new())
            .await
            .map_err(|_| "Desktop portal timed out")?
            .map_err(|_| "Desktop output portal unavailable")?;
        let session = tokio::time::timeout(
            Duration::from_secs(10),
            remote.create_session(Default::default()),
        )
        .await
        .map_err(|_| "Desktop session creation timed out")?
        .map_err(|_| "Could not create desktop output session")?;
        let mut changes = output.shared.changes.subscribe();
        let result: Result<(), String> = async {
            if output.shared.epoch.load(Ordering::SeqCst) != epoch { return Ok(()); }
            let closed = session.receive_closed().await.map_err(|_| "Could not monitor desktop permission")?;
            pin_mut!(closed);
            remote.select_devices(&session, SelectDevicesOptions::default().set_devices(DeviceType::KEYBOARD).set_persist_mode(PersistMode::DoNot))
                .await.map_err(|_| "Could not request keyboard-only permission")?.response().map_err(|_| "Keyboard request was rejected")?;
            let started = tokio::select! {
                _ = changes.changed() => return Ok(()),
                value = tokio::time::timeout(Duration::from_secs(120), remote.start(&session, None, Default::default())) => {
                    value.map_err(|_| "Desktop output permission timed out")?
                        .map_err(|_| "Desktop output portal failed")?.response().map_err(|_| "Desktop output permission was denied or cancelled")?
                }
            };
            if started.devices() != DeviceType::KEYBOARD { return Err("Desktop did not grant keyboard-only access".into()); }
            if output.shared.epoch.load(Ordering::SeqCst) != epoch { return Ok(()); }
            let fd = remote.connect_to_eis(&session, Default::default()).await.map_err(|_| "Could not open approved desktop text connection")?;
            let (sender, receiver) = sync_channel::<Job>(1);
            let (events, mut worker_events) = mpsc::unbounded_channel();
            let shared = output.shared.clone();
            std::thread::Builder::new().name("voicewright-text".into()).spawn(move || {
                let work = || -> Result<(), String> {
                    let mut client = crate::eis_text::Client::new(fd)?;
                    let cancelled = std::sync::atomic::AtomicBool::new(false);
                    client.wait_ready(&cancelled)?;
                    let _ = events.send(WorkerEvent::Ready);
                    while shared.epoch.load(Ordering::SeqCst) == epoch {
                        match receiver.recv_timeout(Duration::from_millis(150)) {
                            Ok(job) => {
                                let result = if job.cancelled.cancelled.load(Ordering::SeqCst) || shared.epoch.load(Ordering::SeqCst) != epoch {
                                    Err("Text output cancelled".to_owned())
                                } else {
                                    client.send_text(&job.text, &job.cancelled.cancelled, || shared.epoch.load(Ordering::SeqCst) == epoch).map_err(str::to_owned)
                                };
                                let failed = result.is_err();
                                let _ = job.reply.send(result);
                                if failed { return Err("Desktop text output stopped; check permission before retrying".into()); }
                            }
                            Err(RecvTimeoutError::Timeout) => {
                                client.poll()?;
                                if !client.is_ready() { return Err("Desktop text input was paused".into()); }
                            }
                            Err(RecvTimeoutError::Disconnected) => return Ok(()),
                        }
                    }
                    Ok(())
                };
                if let Err(error) = work() { let _ = events.send(WorkerEvent::Failed(error)); }
            }).map_err(|_| "Could not start desktop text worker")?;
            loop {
                tokio::select! {
                    _ = changes.changed() => return Ok(()),
                    _ = closed.next() => return Err("Desktop output permission was revoked".into()),
                    event = worker_events.recv() => match event {
                        Some(WorkerEvent::Ready) => output.update(epoch, OutputState::Ready, None, Some(sender.clone())),
                        Some(WorkerEvent::Failed(error)) => return Err(error),
                        None => return Err("Desktop text worker stopped".into()),
                    }
                }
            }
        }.await;
        let _ = session.close().await;
        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::Ordering;

    fn controller(available: bool) -> Controller {
        let (sender, _) = mpsc::unbounded_channel();
        super::controller(available, sender)
    }

    #[test]
    fn no_consent_never_starts_a_permission_request() {
        let output = controller(true);
        assert_eq!(output.snapshot().state, OutputState::Disabled);
        assert_eq!(output.shared.epoch.load(Ordering::SeqCst), 0);
    }

    #[test]
    fn duplicate_pending_requests_do_not_open_multiple_dialogs() {
        let output = controller(true);
        assert!(output.begin_permission().is_some());
        assert_eq!(output.snapshot().state, OutputState::Pending);
        assert_eq!(output.begin_permission(), None);
    }

    #[test]
    fn disabling_invalidates_queued_output_and_permission_generation() {
        let output = controller(true);
        let epoch = output.begin_permission().unwrap();
        output.disconnect();
        assert_eq!(output.snapshot().state, OutputState::Disabled);
        assert_ne!(epoch, output.shared.epoch.load(Ordering::SeqCst));
    }

    #[tokio::test]
    async fn not_ready_never_dispatches_text() {
        let output = controller(true);
        assert!(output
            .insert("Private text".into(), Arc::new(Capture::default()))
            .await
            .is_err());
    }

    #[tokio::test]
    async fn cancelled_capture_is_rejected_before_queueing() {
        let output = controller(true);
        let capture = Arc::new(Capture::default());
        capture.cancelled.store(true, Ordering::SeqCst);
        assert!(output.insert("Private text".into(), capture).await.is_err());
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn revoked_permission_cannot_become_ready_from_an_old_request() {
        let output = controller(true);
        let epoch = output.begin_permission().unwrap();
        output.disconnect();
        let (sender, _) = sync_channel(1);
        output.update(epoch, OutputState::Ready, None, Some(sender));
        assert_eq!(output.snapshot().state, OutputState::Disabled);
    }

    #[tokio::test]
    async fn a_pending_permission_never_enqueues_text_even_with_a_sender() {
        let output = controller(true);
        output.begin_permission();
        let (sender, receiver) = sync_channel(1);
        output.shared.inner.lock().unwrap().output = Some(sender);
        assert!(output
            .insert("Private text".into(), Arc::new(Capture::default()))
            .await
            .is_err());
        assert!(receiver.try_recv().is_err());
    }
}
