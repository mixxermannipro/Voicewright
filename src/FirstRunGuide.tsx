import { useState } from 'react';
import type { Initial, Settings, Status } from './domain';

type Copy = (de: string, en: string) => string;
type Destination = 'models' | 'cleanup' | 'settings' | 'privacy';

type Props = {
  settings: Settings;
  status?: Status;
  catalog: Initial['catalog'];
  globalSupported: boolean;
  trayAvailable: boolean;
  saving: boolean;
  canSaveProgress: boolean;
  t: Copy;
  onNavigate: (page: Destination) => void;
  onExecute: (command: string, args?: Record<string, unknown>) => Promise<void>;
  onProgress: (step: number, complete: boolean) => Promise<void>;
};

export function FirstRunGuide({
  settings, status, catalog, globalSupported, trayAvailable, saving, canSaveProgress,
  t, onNavigate, onExecute, onProgress,
}: Props) {
  const [confirmedExternal, setConfirmedExternal] = useState(false);
  const step = settings.onboarding_step;
  const installed = status?.installed ?? [];
  const ready = installed.includes(settings.speech_model);
  const recording = status?.phase === 'recording';
  const dictating = ['recording', 'transcribing', 'cleaning', 'inserting'].includes(status?.phase ?? '');
  const tested = status?.phase === 'completed' && Boolean(status.transcript?.trim());
  const downloading = status?.download?.active === true;
  const selected = catalog.find((item) => item.id === settings.speech_model);
  const base = catalog.find((item) => item.id === 'whisper-base');
  const operatingSystem = typeof navigator === 'undefined' ? 'other' :
    /windows/i.test(navigator.userAgent) ? 'windows' :
      /macintosh|mac os/i.test(navigator.userAgent) ? 'mac' :
        /linux/i.test(navigator.userAgent) ? 'linux' : 'other';
  const steps = [
    t('Datenschutz', 'Privacy'),
    t('Modell', 'Model'),
    t('Mikrofon', 'Microphone'),
    t('Tastenkürzel', 'Shortcut'),
  ];
  const blocked = !canSaveProgress || saving || dictating;
  const next = (newStep: number, complete = false) => { void onProgress(newStep, complete); };

  return <section className="panel first-run-guide" aria-label={t('Ersteinrichtung', 'First-run setup')}>
    <p className="kicker">{t('DEIN ERSTES DIKTAT', 'YOUR FIRST DICTATION')}</p>
    <h2>{t('Ersteinrichtung', 'First-run setup')}</h2>
    <p className="muted">{t(
      'Vier Schritte ohne Cloud-Konto. Dein Fortschritt bleibt gespeichert; du kannst jederzeit in einen anderen Bereich wechseln.',
      'Four steps without a cloud account. Progress is saved; you can switch to another section anytime.',
    )}</p>
    <ol className="setup-steps" aria-label={t('Einrichtungsschritte', 'Setup steps')}>
      {steps.map((title, index) => <li key={title} aria-current={step === index ? 'step' : undefined}
        className={step === index ? 'active' : index < step ? 'done' : ''}>
        <span aria-hidden="true">{index + 1}</span>{title}
      </li>)}
    </ol>
    {step === 0 && <>
      <h3>{t('Privat starten – Cloud bleibt freiwillig', 'Start privately – cloud is optional')}</h3>
      <p>{t(
        'Spracherkennung läuft lokal. Ohne aktivierte Textkorrektur werden keine Diktate an KI-Anbieter übertragen. Modellgewichte werden nur heruntergeladen, wenn du dies ausdrücklich auswählst.',
        'Speech recognition runs locally. Without cloud editing, dictations are not sent to AI providers. Model weights download only after you explicitly request them.',
      )}</p>
      <p>{t('Aktuelle Textkorrektur:', 'Current text editing:')} <strong>{
        settings.cleanup_mode === 'off' ? t('Aus (empfohlen)', 'Off (recommended)') :
          settings.cleanup_mode === 'local' ? t('Lokal', 'Local') : t('Cloud – Text wird übertragen', 'Cloud – text is transmitted')
      }</strong></p>
      {settings.cleanup_mode === 'cloud' && <p className="message error" role="alert">{t(
        'Cloud-Korrektur ist bereits eingeschaltet. Für einen rein lokalen Mikrofontest bitte unter „Textkorrektur“ auf „Aus“ umstellen und speichern. So entstehen keine Cloud-Anfragen.',
        'Cloud editing is already enabled. For a local-only microphone test, switch editing to “Off” under Text editing and save. This avoids cloud requests.',
      )}</p>}
      <div className="actions">
        <button type="button" onClick={() => onNavigate('privacy')}>{t('Datenschutz ansehen', 'View privacy')}</button>
        <button type="button" onClick={() => onNavigate('cleanup')}>{t('Textkorrektur einstellen', 'Configure text editing')}</button>
      </div>
    </>}
    {step === 1 && <>
      <h3>{t('Sprachmodell auswählen und laden', 'Choose and download a speech model')}</h3>
      <p>{t(
        'Empfohlen: Whisper Base, mehrsprachig und vollständig lokal nach dem Download. Der Download läuft von Hugging Face und wird per SHA-256 geprüft. Du kannst ihn jederzeit abbrechen.',
        'Recommended: Whisper Base, multilingual and fully local after downloading. Files come from Hugging Face and are checked with SHA-256. You can cancel any time.',
      )}</p>
      <p>{t('Gewähltes Modell', 'Selected model')}: <strong>{selected?.name ?? settings.speech_model}</strong>
        {' · '}{ready ? t('Installiert', 'Installed') : t('Noch nicht verfügbar', 'Not installed yet')}</p>
      {base && <p className="muted small">{t('Whisper Base Downloadgröße', 'Whisper Base download size')}: {(base.bytes / 1_000_000).toFixed(0)} MB · {base.ram_gib} GB RAM {t('empfohlen', 'recommended')}</p>}
      {!ready && settings.speech_model === 'whisper-base' && !downloading && <button type="button"
        disabled={dictating || saving}
        onClick={() => void onExecute('download_model', { id: 'whisper-base' })}>
        {t('Whisper Base laden', 'Download Whisper Base')}
      </button>}
      {downloading && status?.download && <>
        <p role="status">{t('Download läuft', 'Downloading')}: {status.download.id}</p>
        <progress aria-label={t('Modelldownload', 'Model download')}
          max={Math.max(status.download.total, 1)} value={status.download.received} />
        <button type="button" onClick={() => void onExecute('cancel_download')}>{t('Download abbrechen', 'Cancel download')}</button>
      </>}
      <div className="actions">
        <button type="button" onClick={() => onNavigate('models')}>{t('Alle Modelle ansehen', 'Browse models')}</button>
      </div>
      <p className="muted small">{t(
        'Falls Speicherplatz, Verbindung oder Download fehlen, bleibt die Einrichtung an diesem Schritt. Nach Wiederherstellung kannst du fortfahren.',
        'If storage, connection or the model download is missing, setup stays on this step. Continue when the issue is resolved.',
      )}</p>
    </>}
    {step === 2 && <>
      <h3>{t('Mikrofon prüfen und ersten Text erkennen', 'Check the microphone and recognize your first text')}</h3>
      <p>{t(
        'Erlaube der App Mikrofonzugriff im Betriebssystem. Sage zum Beispiel „Heute teste ich Voicewright“ und beende die Aufnahme. Der erkannte Text bleibt in der App.',
        'Grant microphone access in your operating system. Say “Today I am testing Voicewright” and stop the recording. The recognized text stays in the app.',
      )}</p>
      <p className="muted small">{operatingSystem === 'windows' ?
        t('Windows: Einstellungen → Datenschutz und Sicherheit → Mikrofon. Zugriff für Desktop-Apps erlauben.',
          'Windows: Settings → Privacy & security → Microphone. Allow access for desktop apps.') :
        operatingSystem === 'mac' ?
          t('macOS: Systemeinstellungen → Datenschutz & Sicherheit → Mikrofon. Voicewright erlauben.',
            'macOS: System Settings → Privacy & Security → Microphone. Allow Voicewright.') :
          operatingSystem === 'linux' ?
            t('Linux: Mikrofon in der Audioverwaltung auswählen. Auf Wayland erfolgt das Diktat über das App-Fenster.',
              'Linux: Select the microphone in your audio controls. On Wayland, dictate using the app window.') :
            t('Prüfe in den Systemeinstellungen, ob die App auf das Mikrofon zugreifen darf.',
              'Check your OS privacy settings to allow microphone access.')}</p>
      {settings.cleanup_mode === 'cloud' && <p className="message error" role="alert">{t(
        'Zum Schutz vor unbeabsichtigten Cloud-Kosten ist der Test hier deaktiviert. Schalte Cloud-Korrektur erst aus und speichere.',
        'To prevent unexpected cloud costs this test is disabled. Switch cloud editing off and save first.',
      )}</p>}
      <div className="actions">
        {recording ? <button type="button" className="primary" onClick={() => void onExecute('stop')}>
          {t('Aufnahme beenden', 'Stop recording')}</button>
          : <button type="button" className="primary"
            disabled={dictating || !ready || settings.cleanup_mode === 'cloud'}
            onClick={() => void onExecute('start_test')}>
            {t('Lokales Testdiktat starten', 'Start local test dictation')}</button>}
        {dictating && <button type="button" onClick={() => void onExecute('cancel')}>
          {t('Abbrechen', 'Cancel')}</button>}
        <button type="button" onClick={() => onNavigate('settings')}>{t('Mikrofon wechseln', 'Change microphone')}</button>
      </div>
      {recording && <label className="meter">{t('Mikrofonpegel', 'Microphone level')}
        <progress max={1} value={Math.max(0, Math.min(1, status?.level ?? 0))} />
      </label>}
      {tested && <p className="message" role="status">{t('Diktat erkannt:', 'Dictation recognized:')}
        {' '}<strong>{status?.transcript}</strong></p>}
      {status?.phase === 'failed' && <p className="message error" role="alert">
        {t('Erkennung fehlgeschlagen. Prüfe Mikrofonrechte, das gewählte Gerät und das Modell.',
          'Recognition failed. Check microphone access, input device and selected model.')}
      </p>}
    </>}
    {step === 3 && <>
      <h3>{t('Tastenkürzel oder manuelles Kopieren', 'Shortcut or manual copying')}</h3>
      <p>{t('Diktat-Tastenkürzel', 'Dictation shortcut')}: <kbd>{settings.shortcut}</kbd>
        {' · '}{settings.recording_mode === 'hold' ? t('Halten', 'Hold') : t('Umschalten', 'Toggle')}</p>
      {globalSupported && status?.shortcut_active ? <p>{t(
        'Öffne ein beliebiges normales Textfeld in einer anderen App. Setze den Cursor dort und diktiere per globalem Tastenkürzel. Bei fehlender Einfügeunterstützung kannst du das Ergebnis in Voicewright kopieren.',
        'Open a normal text field in another app. Focus it and dictate with the global shortcut. If automatic insertion is unavailable, copy the result from Voicewright.',
      )}</p> : <p>{t(
        'Globale Diktate sind auf diesem System aktuell nicht verfügbar. Starte Aufnahmen in Voicewright und kopiere das Ergebnis manuell in die Zielanwendung.',
        'Global dictation is currently unavailable on this system. Start recording inside Voicewright and copy the result manually into the target app.',
      )}</p>}
      {status?.shortcut_error && <p className="message error" role="alert">{t(
        'Tastenkürzel-Konflikt: Passe die Tasten unter Einstellungen an oder nutze den Kopierweg.',
        'Shortcut conflict: change the keys in Settings or use manual copy.',
      )}</p>}
      <p className="muted small">{trayAvailable ? t(
        'Beim Schließen des Fensters bleibt die App im System-Tray. Autostart ist nicht automatisch aktiviert.',
        'When you close the window, the app stays in the system tray. Autostart is not enabled automatically.',
      ) : t(
        'Ein Tray-Symbol ist auf diesem System nicht verfügbar. Die App über das Fenster bedienen.',
        'No tray icon is available here. Use the app window.',
      )}</p>
      <label className="check"><input type="checkbox" checked={confirmedExternal}
        onChange={(event) => setConfirmedExternal(event.target.checked)} />
        {t('Ich habe einen externen Textversuch gemacht oder verwende bewusst das Kopieren.',
          'I tried dictating into another app or deliberately use manual copying.')}</label>
    </>}
    {!canSaveProgress && <p className="message" role="status">{t(
      'Speichere zuerst offene Änderungen, bevor du den Einrichtungsfortschritt übernimmst.',
      'Save pending settings changes before saving setup progress.',
    )}</p>}
    <div className="actions setup-navigation">
      {step > 0 && <button type="button" disabled={blocked} onClick={() => next(step - 1)}>
        {t('Zurück', 'Back')}</button>}
      {step < 3 ? <button type="button" className="primary"
        disabled={blocked || (step === 1 && !ready) || (step === 2 && !tested)}
        onClick={() => next(step + 1)}>
        {saving ? t('Speichert …', 'Saving…') : t('Weiter', 'Continue')}
      </button> : <button type="button" className="primary"
        disabled={blocked || !confirmedExternal}
        onClick={() => next(3, true)}>
        {t('Einrichtung abschließen', 'Finish setup')}
      </button>}
    </div>
    <p className="muted small">{t(
      'Keine Veröffentlichungsgarantie: Die Ersteinrichtung ersetzt keine Tests auf deinem Betriebssystem.',
      'This guide does not replace platform-specific testing of the app.',
    )}</p>
  </section>;
}
