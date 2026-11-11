import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const config = JSON.parse(readFileSync('src-tauri/tauri.conf.json', 'utf8'));

describe('Linux package contract', () => {
  it('declares native libraries for the application and cleanup sidecar', () => {
    const dependencies = config.bundle.linux.deb.depends.join(' ');
    for (const dependency of ['libwebkit2gtk-4.1-0', 'libgtk-3-0', 'libayatana-appindicator3-1', 'libasound2']) {
      expect(dependencies).toContain(dependency);
    }
    expect(dependencies).not.toContain('libxdo3');
    expect(dependencies).not.toContain('libxkbcommon0');
  });

  it('ships AppStream and legal notices in both Linux formats', () => {
    for (const format of ['appimage', 'deb']) {
      const files = config.bundle.linux[format].files;
      expect(files['/usr/share/metainfo/de.voicewright.desktop.metainfo.xml'])
        .toBe('linux/de.voicewright.desktop.metainfo.xml');
      expect(files['/usr/share/doc/voicewright/LICENSE']).toBe('../LICENSE');
      expect(files['/usr/share/doc/voicewright/THIRD_PARTY_LICENSES.md'])
        .toBe('../docs/THIRD_PARTY_LICENSES.md');
    }
  });

  it('uses an explicit desktop entry without root or automatic autostart', () => {
    expect(config.bundle.linux.deb.desktopTemplate).toBe('linux/voicewright.desktop');
    const desktop = readFileSync('src-tauri/linux/voicewright.desktop', 'utf8');
    expect(desktop).toContain('Terminal=false');
    expect(desktop).toContain('Exec={{exec}}');
    expect(desktop).not.toMatch(/sudo|pkexec|X-GNOME-Autostart-enabled=true/);
  });

  it('disables host-specific and AVX instructions for both GGML builds', () => {
    const cargo = readFileSync('.cargo/config.toml', 'utf8');
    for (const flag of ['NATIVE', 'AVX', 'AVX2', 'FMA', 'F16C', 'AVX512', 'BMI2']) {
      expect(cargo).toContain(`GGML_${flag} = "OFF"`);
    }
  });

  it('does not reuse the old AVX-enabled packaging cache', () => {
    expect(readFileSync('scripts/prepare-engine.mjs', 'utf8'))
      .toContain("resolve('engines/cleanup/target/portable')");
  });

  it('does not invent a published release version or date in AppStream', () => {
    expect(readFileSync('src-tauri/linux/de.voicewright.desktop.metainfo.xml', 'utf8'))
      .not.toContain('<release ');
  });
});
