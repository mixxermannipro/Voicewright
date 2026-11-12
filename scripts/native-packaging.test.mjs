import { Buffer } from 'node:buffer';
import { mkdtempSync, readFileSync, rmSync, unlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { executableTarget, assertVersions, checkPayload, checkBundle } from './check-native-bundle.mjs';

describe('native payload verification', () => {
  it('accepts x64 PE payloads but rejects x86 and malformed headers', () => {
    const pe = Buffer.alloc(256);
    pe.write('MZ');
    pe.writeUInt32LE(128, 60);
    pe.write('PE\0\0', 128);
    pe.writeUInt16LE(0x8664, 132);
    expect(executableTarget(pe)).toBe('x86_64-pc-windows-msvc');
    pe.writeUInt16LE(0x14c, 132);
    expect(() => executableTarget(pe)).toThrow();
    pe.writeUInt32LE(1000, 60);
    expect(() => executableTarget(pe)).toThrow();
  });

  it('accepts thin ARM64 Mach-O and rejects x64, text and short payloads', () => {
    const macho = Buffer.alloc(32);
    macho.writeUInt32LE(0xfeedfacf, 0);
    macho.writeUInt32LE(0x0100000c, 4);
    expect(executableTarget(macho)).toBe('aarch64-apple-darwin');
    macho.writeUInt32LE(0x01000007, 4);
    expect(() => executableTarget(macho)).toThrow();
    expect(() => executableTarget(Buffer.from('not an executable'))).toThrow();
    expect(() => executableTarget(Buffer.alloc(0))).toThrow();
  });

  it('requires exact application version agreement, including the npm lockfile', () => {
    expect(() => assertVersions(['0.1.0-alpha.1', '0.1.0-alpha.1', '0.1.0-alpha.1'])).not.toThrow();
    expect(() => assertVersions(['0.1.0-alpha.1', '0.1.0', '0.1.0-alpha.1'])).toThrow();
    expect(() => assertVersions(['0.1.0-alpha.1', undefined])).toThrow();
  });

  it('requires a matching sidecar architecture and bundled license notices', () => {
    const directory = mkdtempSync(join(tmpdir(), 'voicewright-payload-test-'));
    try {
      const pe = Buffer.alloc(256);
      pe.write('MZ'); pe.writeUInt32LE(128, 60); pe.write('PE\0\0', 128); pe.writeUInt16LE(0x8664, 132);
      for (const name of ['voicewright.exe', 'voicewright-cleanup.exe']) writeFileSync(join(directory, name), pe);
      for (const name of ['LICENSE', 'THIRD_PARTY_LICENSES.md']) writeFileSync(join(directory, name), 'synthetic notice');
      const check = () => checkPayload(directory, 'voicewright.exe', 'voicewright-cleanup.exe', 'x86_64-pc-windows-msvc');
      expect(check).not.toThrow();
      unlinkSync(join(directory, 'voicewright-cleanup.exe'));
      expect(check).toThrow('voicewright-cleanup.exe');
      writeFileSync(join(directory, 'voicewright-cleanup.exe'), pe);
      unlinkSync(join(directory, 'THIRD_PARTY_LICENSES.md'));
      expect(check).toThrow('Missing bundled notice');
    } finally { rmSync(directory, { recursive: true, force: true }); }
  });

  it('writes a failure report instead of claiming a package passed on an unsupported target', () => {
    const directory = mkdtempSync(join(tmpdir(), 'voicewright-report-test-'));
    try {
      expect(checkBundle('unsupported-target', directory, directory)).toBe(1);
      const report = JSON.parse(readFileSync(join(directory, 'report.json')));
      expect(report.status).toBe('failed');
      expect(report.not_tested.length).toBeGreaterThan(0);
      expect(report.commit).toBeTruthy();
    } finally { rmSync(directory, { recursive: true, force: true }); }
  });
});
