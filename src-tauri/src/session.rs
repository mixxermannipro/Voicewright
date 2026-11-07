use serde::Serialize;
use std::time::{Duration, Instant};

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Phase {
    #[default]
    Idle,
    Recording,
    Transcribing,
    Cleaning,
    Inserting,
    Completed,
    Cancelled,
    Failed,
}

impl Phase {
    pub fn busy(self) -> bool {
        matches!(
            self,
            Self::Recording | Self::Transcribing | Self::Cleaning | Self::Inserting
        )
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ShortcutKind {
    Dictation,
    Cancel,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Action {
    Start,
    Stop,
    Cancel,
}

/// A key press older than this is treated as a fresh press even when the
/// matching release was lost. Auto-repeat updates the timestamp, so a key
/// that is actually held down is never mistaken for a stale event.
const STALE_KEY_EVENT: Duration = Duration::from_secs(2);

#[derive(Default)]
pub struct HotkeyState {
    dictation_down: bool,
    cancel_down: bool,
    dictation_at: Option<Instant>,
    cancel_at: Option<Instant>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hold_stops_only_on_matching_release() {
        let mut key = HotkeyState::default();
        let now = Instant::now();
        assert_eq!(
            key.change_at(ShortcutKind::Dictation, false, true, Phase::Idle, now),
            None
        );
        assert_eq!(
            key.change_at(ShortcutKind::Dictation, true, true, Phase::Idle, now),
            Some(Action::Start)
        );
        assert_eq!(
            key.change_at(ShortcutKind::Dictation, true, true, Phase::Recording, now),
            None
        );
        assert_eq!(
            key.change_at(ShortcutKind::Dictation, false, true, Phase::Recording, now),
            Some(Action::Stop)
        );
        assert_eq!(
            key.change_at(ShortcutKind::Dictation, false, true, Phase::Recording, now),
            None
        );
    }

    #[test]
    fn toggle_ignores_repeat_and_processing() {
        let mut key = HotkeyState::default();
        let now = Instant::now();
        assert_eq!(
            key.change_at(ShortcutKind::Dictation, true, false, Phase::Idle, now),
            Some(Action::Start)
        );
        assert_eq!(
            key.change_at(ShortcutKind::Dictation, true, false, Phase::Recording, now),
            None
        );
        assert_eq!(
            key.change_at(ShortcutKind::Dictation, false, false, Phase::Recording, now),
            None
        );
        assert_eq!(
            key.change_at(ShortcutKind::Dictation, true, false, Phase::Recording, now),
            Some(Action::Stop)
        );
        assert_eq!(
            key.change_at(
                ShortcutKind::Dictation,
                false,
                false,
                Phase::Transcribing,
                now
            ),
            None
        );
        assert_eq!(
            key.change_at(ShortcutKind::Dictation, true, false, Phase::Cleaning, now),
            None
        );
    }

    #[test]
    fn burst_events_start_and_stop_at_most_once() {
        let mut key = HotkeyState::default();
        let now = Instant::now();
        let mut phase = Phase::Idle;
        let mut starts = 0;
        let mut stops = 0;
        for pressed in [true, true, false, false, true, true, false, false] {
            match key.change_at(ShortcutKind::Dictation, pressed, true, phase, now) {
                Some(Action::Start) => {
                    starts += 1;
                    phase = Phase::Recording;
                }
                Some(Action::Stop) => {
                    stops += 1;
                    phase = Phase::Transcribing;
                }
                Some(Action::Cancel) => panic!("dictation must not cancel"),
                None => {}
            }
        }
        assert_eq!(starts, 1);
        assert_eq!(stops, 1);
    }

    #[test]
    fn cancel_is_idempotent_and_only_active_while_busy() {
        let mut key = HotkeyState::default();
        let now = Instant::now();
        assert_eq!(
            key.change_at(ShortcutKind::Cancel, true, true, Phase::Idle, now),
            None
        );
        assert_eq!(
            key.change_at(ShortcutKind::Cancel, false, true, Phase::Idle, now),
            None
        );
        assert_eq!(
            key.change_at(ShortcutKind::Cancel, true, true, Phase::Recording, now),
            Some(Action::Cancel)
        );
        assert_eq!(
            key.change_at(ShortcutKind::Cancel, true, true, Phase::Cleaning, now),
            None
        );
        assert_eq!(
            key.change_at(ShortcutKind::Cancel, false, true, Phase::Cleaning, now),
            None
        );
        assert_eq!(
            key.change_at(ShortcutKind::Cancel, true, true, Phase::Cleaning, now),
            Some(Action::Cancel)
        );
    }

    #[test]
    fn a_lost_release_recovers_after_the_stale_window() {
        let mut key = HotkeyState::default();
        let start = Instant::now();
        assert_eq!(
            key.change_at(ShortcutKind::Dictation, true, true, Phase::Idle, start),
            Some(Action::Start)
        );
        // The release never arrives. A repeat press shortly after is ignored.
        assert_eq!(
            key.change_at(
                ShortcutKind::Dictation,
                true,
                true,
                Phase::Completed,
                start + Duration::from_millis(50)
            ),
            None
        );
        // After the stale window the next press is treated as a fresh press.
        assert_eq!(
            key.change_at(
                ShortcutKind::Dictation,
                true,
                true,
                Phase::Completed,
                start + Duration::from_millis(50) + STALE_KEY_EVENT + Duration::from_millis(1)
            ),
            Some(Action::Start)
        );
    }

    #[test]
    fn shortcut_changes_roll_back_when_registration_fails() {
        use std::cell::RefCell;
        let registered = RefCell::new(vec![1]);
        let register = |value: u32| {
            if value == 2 {
                return false;
            }
            registered.borrow_mut().push(value);
            true
        };
        let unregister = |value: u32| {
            registered.borrow_mut().retain(|item| *item != value);
            true
        };
        let result = apply_shortcut_changes(&[1], &[2], &register, &unregister);
        assert!(result.is_err());
        assert_eq!(*registered.borrow(), vec![1]);
    }

    #[test]
    fn shortcut_changes_restore_the_previous_binding_when_release_fails() {
        use std::cell::RefCell;
        let registered = RefCell::new(vec![1, 2]);
        let register = |value: u32| {
            registered.borrow_mut().push(value);
            true
        };
        let unregister = |value: u32| {
            if value == 1 {
                return false;
            }
            registered.borrow_mut().retain(|item| *item != value);
            true
        };
        let result = apply_shortcut_changes(&[1, 2], &[2], &register, &unregister);
        assert!(result.is_err());
        let mut current = registered.borrow().clone();
        current.sort_unstable();
        assert_eq!(current, vec![1, 2]);
    }

    #[test]
    fn shortcut_changes_apply_additions_and_removals() {
        use std::cell::RefCell;
        let registered = RefCell::new(vec![1, 2]);
        let register = |value: u32| {
            registered.borrow_mut().push(value);
            true
        };
        let unregister = |value: u32| {
            registered.borrow_mut().retain(|item| *item != value);
            true
        };
        apply_shortcut_changes(&[1, 2], &[2, 3], &register, &unregister).unwrap();
        let mut current = registered.borrow().clone();
        current.sort_unstable();
        assert_eq!(current, vec![2, 3]);
    }
}

#[derive(Default)]
pub struct Status {
    pub phase: Phase,
    pub recording_since: Option<Instant>,
    pub transcript: Option<String>,
    pub warning: Option<String>,
    pub inserted: bool,
}

impl HotkeyState {
    pub fn change(
        &mut self,
        kind: ShortcutKind,
        pressed: bool,
        hold: bool,
        phase: Phase,
    ) -> Option<Action> {
        self.change_at(kind, pressed, hold, phase, Instant::now())
    }

    fn change_at(
        &mut self,
        kind: ShortcutKind,
        pressed: bool,
        hold: bool,
        phase: Phase,
        now: Instant,
    ) -> Option<Action> {
        let (down, last) = match kind {
            ShortcutKind::Dictation => (&mut self.dictation_down, &mut self.dictation_at),
            ShortcutKind::Cancel => (&mut self.cancel_down, &mut self.cancel_at),
        };
        let stale = last.is_none_or(|previous| now.duration_since(previous) >= STALE_KEY_EVENT);
        let changed = std::mem::replace(down, pressed) != pressed || (pressed && stale);
        *last = Some(now);
        if !changed {
            return None;
        }
        match (kind, pressed, hold, phase) {
            (ShortcutKind::Cancel, true, _, phase) if phase.busy() => Some(Action::Cancel),
            (ShortcutKind::Dictation, true, _, phase) if !phase.busy() => Some(Action::Start),
            (ShortcutKind::Dictation, true, false, Phase::Recording)
            | (ShortcutKind::Dictation, false, true, Phase::Recording) => Some(Action::Stop),
            _ => None,
        }
    }

    pub fn reset(&mut self) {
        *self = Self::default();
    }
}

/// Applies a shortcut change with rollback. Additions are registered first so
/// a conflict leaves the previous binding untouched. If releasing an old
/// binding fails, the new bindings are removed and already released old ones
/// are restored.
pub fn apply_shortcut_changes<T: Copy + PartialEq>(
    previous: &[T],
    next: &[T],
    register: &dyn Fn(T) -> bool,
    unregister: &dyn Fn(T) -> bool,
) -> Result<(), String> {
    let mut added = Vec::new();
    for shortcut in next.iter().filter(|item| !previous.contains(item)) {
        if !register(*shortcut) {
            for item in added.iter().rev() {
                let _ = unregister(*item);
            }
            return Err("This shortcut is unavailable or is already assigned.".into());
        }
        added.push(*shortcut);
    }
    let mut removed = Vec::new();
    for shortcut in previous.iter().filter(|item| !next.contains(item)) {
        if !unregister(*shortcut) {
            let mut restored = true;
            for item in removed.iter().rev() {
                restored &= register(*item);
            }
            for item in added.iter().rev() {
                restored &= unregister(*item);
            }
            return Err(if restored {
                "Could not release the previous shortcut.".into()
            } else {
                "Could not restore the previous shortcut. Reopen the app.".into()
            });
        }
        removed.push(*shortcut);
    }
    Ok(())
}
