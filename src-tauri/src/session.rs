use serde::Serialize;
use std::time::Instant;

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
pub enum Action {
    Start,
    Stop,
}

#[derive(Default)]
pub struct ShortcutPress {
    down: bool,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hold_stops_only_on_matching_release() {
        let mut key = ShortcutPress::default();
        assert_eq!(key.change(false, true, Phase::Idle), None);
        assert_eq!(key.change(true, true, Phase::Idle), Some(Action::Start));
        assert_eq!(key.change(true, true, Phase::Recording), None);
        assert_eq!(
            key.change(false, true, Phase::Recording),
            Some(Action::Stop)
        );
        assert_eq!(key.change(false, true, Phase::Recording), None);
    }

    #[test]
    fn toggle_ignores_repeat_and_processing() {
        let mut key = ShortcutPress::default();
        assert_eq!(key.change(true, false, Phase::Idle), Some(Action::Start));
        assert_eq!(key.change(true, false, Phase::Recording), None);
        assert_eq!(key.change(false, false, Phase::Recording), None);
        assert_eq!(
            key.change(true, false, Phase::Recording),
            Some(Action::Stop)
        );
        assert_eq!(key.change(false, false, Phase::Transcribing), None);
        assert_eq!(key.change(true, false, Phase::Cleaning), None);
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

impl ShortcutPress {
    pub fn change(&mut self, pressed: bool, hold: bool, phase: Phase) -> Option<Action> {
        if std::mem::replace(&mut self.down, pressed) == pressed {
            return None;
        }
        match (pressed, hold, phase) {
            (true, _, phase) if !phase.busy() => Some(Action::Start),
            (true, false, Phase::Recording) | (false, true, Phase::Recording) => Some(Action::Stop),
            _ => None,
        }
    }
}
