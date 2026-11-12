import type { InsertionState } from './domain';

type Props = {
  state: InsertionState;
  enabled: boolean;
  busy?: boolean;
  t: (de: string, en: string) => string;
  onRequest: () => void;
};

export function WaylandPermission({ state, enabled, busy, t, onRequest }: Props) {
  const messages: Record<InsertionState, string> = {
    disabled: t('Speichere die Einwilligung, um automatisches Einfügen zu aktivieren.', 'Save consent to enable automatic insertion.'),
    pending: t('Bestätige die Tastaturfreigabe im Systemdialog.', 'Confirm the keyboard permission in the desktop dialog.'),
    ready: t('Automatisches Einfügen ist bereit.', 'Automatic insertion is ready.'),
    denied: t('Der Desktop hat die Tastaturfreigabe abgelehnt.', 'The desktop denied keyboard permission.'),
    error: t('Die Verbindung für die Tastatureingabe wurde unterbrochen.', 'The connection for keyboard input was interrupted.'),
    unavailable: t('Automatisches Einfügen ist auf diesem Wayland-Desktop nicht verfügbar.', 'Automatic insertion is unavailable on this Wayland desktop.'),
  };
  const current = enabled ? state : 'disabled';
  return <div>
    <p role="status">{messages[current]}</p>
    {current !== 'ready' && current !== 'unavailable' && <button type="button" disabled={!enabled || busy || current === 'pending'} onClick={onRequest}>
      {t('Tastaturfreigabe anfragen', 'Request keyboard permission')}
    </button>}
  </div>;
}
