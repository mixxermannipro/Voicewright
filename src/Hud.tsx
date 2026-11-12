import { invoke } from '@tauri-apps/api/core';
import { useEffect, useState } from 'react';
import type { Status } from './domain';

export function Hud() {
  const [status, setStatus] = useState<Status>();
  useEffect(() => {
    let active = true;
    const update = () => { void invoke<Status>('status').then(value => { if (active) setStatus(value); }).catch(() => {}); };
    update();
    const timer = window.setInterval(update, 180);
    return () => { active = false; window.clearInterval(timer); };
  }, []);
  const label = status?.phase === 'recording' ? 'Aufnahme / Recording' :
    status?.phase === 'failed' ? 'Einstellungen prüfen / Check settings' : 'Verarbeitung / Processing';
  return <main className="hud" aria-live="polite"><span className="recording-dot" aria-hidden="true" /><div><strong>Voicewright</strong><p>{label}</p></div>
    {status?.phase === 'recording' && <progress aria-label="Mikrofonpegel / Microphone level" max={1} value={Math.max(0, Math.min(1, status.level))} />}</main>;
}
