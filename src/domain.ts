type Key = Pick<KeyboardEvent, 'altKey' | 'ctrlKey' | 'shiftKey' | 'metaKey' | 'repeat' | 'code'>;

export function shortcutFromKey(key: Key): string | null {
  if (key.repeat) return null;
  const name = /^(Key[A-Z]|Digit[0-9])$/.test(key.code) ? key.code.slice(-1) : key.code;
  if (!/^(?:[A-Z0-9]|Space|Escape|Enter|Backspace|Delete|Home|End|PageUp|PageDown|Arrow(?:Up|Down|Left|Right)|F(?:[1-9]|1[0-9]|2[0-4]))$/.test(name)) {
    return null;
  }
  return [key.ctrlKey && 'Ctrl', key.altKey && 'Alt', key.shiftKey && 'Shift', key.metaKey && 'Super', name]
    .filter(Boolean).join('+');
}

export function formatDuration(ms: number): string {
  const seconds = Math.floor(Math.max(0, ms) / 1000);
  return [Math.floor(seconds / 60), seconds % 60].map((part) => String(part).padStart(2, '0')).join(':');
}

export const providers = {
  open_ai: 'OpenAI', gemini: 'Google Gemini', anthropic: 'Anthropic Claude', xai: 'xAI',
  open_router: 'OpenRouter', mistral: 'Mistral', groq: 'Groq', deep_seek: 'DeepSeek',
  together: 'Together AI', fireworks: 'Fireworks AI', cerebras: 'Cerebras', compatible: 'OpenAI-compatible',
};

export type Provider = keyof typeof providers;
export type ProviderConfig = { provider: Provider; endpoint: string | null; model: string };
export type Kind = 'speech' | 'cleanup';
export type Model = {
  id: string; name: string; kind: Kind; url: string; bytes: number; sha256: string; license: string; ram_gib: number;
};
export type Settings = {
  schema_version: number;
  locale: 'de' | 'en';
  speech_language: string;
  speech_model: string;
  cleanup_model: string;
  cleanup_mode: 'off' | 'local' | 'cloud';
  providers: Partial<Record<Provider, ProviderConfig>>;
  active_provider: Provider;
  prompt: string;
  presets: Record<string, string>;
  translation: string;
  vocabulary: string;
  fallback: boolean;
  auto_insert: boolean;
  shortcut: string;
  cancel_shortcut: string;
  recording_mode: 'hold' | 'toggle';
  microphone: string | null;
};
export type Initial = {
  settings: Settings; catalog: Model[];
  hardware: { cpu: string; threads: number; ram: number };
  global_supported: boolean; tray_available: boolean; model_path: string; default_prompt: string;
};
export type Phase = 'idle' | 'recording' | 'transcribing' | 'cleaning' | 'inserting' | 'completed' | 'cancelled' | 'failed';
export type Status = {
  phase: Phase; elapsed_ms: number; level: number; transcript: string | null; warning: string | null;
  inserted: boolean; shortcut_error: string | null; shortcut_active: boolean; installed: string[];
  download: { id: string; received: number; total: number; active: boolean; error: string | null } | null;
};

export const inProgress = (status: Status | undefined) => status
  ? ['recording', 'transcribing', 'cleaning', 'inserting'].includes(status.phase) : false;
