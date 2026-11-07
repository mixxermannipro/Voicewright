import { describe, expect, it } from 'vitest';
import { canAdvanceSetup, formatDuration, shortcutFromKey } from './domain';

describe('shortcut capture', () => {
  const base = { altKey: false, ctrlKey: false, shiftKey: false, metaKey: false, repeat: false };
  it('captures physical shortcuts, excluding repeats and modifier-only presses', () => {
    expect(shortcutFromKey({ ...base, ctrlKey: true, shiftKey: true, code: 'Space' })).toBe('Ctrl+Shift+Space');
    expect(shortcutFromKey({ ...base, altKey: true, code: 'KeyU' })).toBe('Alt+U');
    expect(shortcutFromKey({ ...base, ctrlKey: true, code: 'ControlLeft' })).toBeNull();
    expect(shortcutFromKey({ ...base, repeat: true, code: 'Escape' })).toBeNull();
  });
  it('supports an unmodified cancel key and suppresses unsupported keys', () => {
    expect(shortcutFromKey({ ...base, code: 'Escape' })).toBe('Escape');
    expect(shortcutFromKey({ ...base, code: 'NumpadAdd' })).toBeNull();
  });
});

it('formats a recording clock without negative durations', () => {
  expect(formatDuration(65_200)).toBe('01:05');
  expect(formatDuration(-500)).toBe('00:00');
});


describe('first-run progress gates', () => {
  it('does not require a cloud account or network access for the privacy step', () => {
    expect(canAdvanceSetup(0, false, undefined)).toBe(true);
  });
  it('waits for a ready model and a completed non-empty microphone dictation', () => {
    expect(canAdvanceSetup(1, false, undefined)).toBe(false);
    expect(canAdvanceSetup(1, true, undefined)).toBe(true);
    expect(canAdvanceSetup(2, true, { phase: 'recording', transcript: 'test' })).toBe(false);
    expect(canAdvanceSetup(2, true, { phase: 'failed', transcript: 'test' })).toBe(false);
    expect(canAdvanceSetup(2, true, { phase: 'completed', transcript: ' ' })).toBe(false);
    expect(canAdvanceSetup(2, true, { phase: 'completed', transcript: 'Hallo Welt' })).toBe(true);
  });
  it('never claims an external shortcut test without explicit acknowledgement', () => {
    expect(canAdvanceSetup(3, true, undefined, false)).toBe(false);
    expect(canAdvanceSetup(3, true, undefined, true)).toBe(true);
    expect(canAdvanceSetup(99, true, undefined, true)).toBe(false);
  });
});
