import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { WaylandPermission } from './WaylandPermission';

describe('Wayland output permission', () => {
  const t = (_de: string, en: string) => en;
  const onRequest = () => {};

  it('requires saved consent before retrying the desktop permission', () => {
    const html = renderToStaticMarkup(
      <WaylandPermission state="disabled" enabled={false} t={t} onRequest={onRequest} />,
    );
    expect(html).toContain('Save consent to enable automatic insertion.');
    expect(html).toMatch(/<button[^>]+disabled/);
  });

  it('reports a pending request and prevents duplicate requests', () => {
    const html = renderToStaticMarkup(
      <WaylandPermission state="pending" enabled t={t} onRequest={onRequest} />,
    );
    expect(html).toContain('Confirm the keyboard permission in the desktop dialog.');
    expect(html).toMatch(/<button[^>]+disabled/);
  });

  it('offers a retry when the desktop denied permission', () => {
    const html = renderToStaticMarkup(
      <WaylandPermission state="denied" enabled t={t} onRequest={onRequest} />,
    );
    expect(html).toContain('The desktop denied keyboard permission.');
    expect(html).not.toMatch(/<button[^>]+disabled/);
  });

  it('shows the active state after permission is granted', () => {
    const html = renderToStaticMarkup(
      <WaylandPermission state="ready" enabled t={t} onRequest={onRequest} />,
    );
    expect(html).toContain('Automatic insertion is ready.');
    expect(html).not.toContain('<button');
  });
});
