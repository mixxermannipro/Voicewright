import assert from 'node:assert/strict';
import { Buffer } from 'node:buffer';
import { execFileSync, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { copyFileSync, mkdirSync, mkdtempSync, openSync,
  readSync, closeSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir, release, arch } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { parseArgs } from 'node:util';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

export function executableTarget(data) {
  assert(data.length >= 8, 'Executable header is too short');
  if (data.readUInt32LE(0) === 0xfeedfacf) {
    assert.equal(data.readUInt32LE(4), 0x0100000c, 'Expected ARM64 Mach-O');
    return 'aarch64-apple-darwin';
  }
  assert(data.length >= 64 && data.toString('ascii', 0, 2) === 'MZ', 'Expected PE or Mach-O');
  const offset = data.readUInt32LE(60);
  assert(offset >= 64 && offset + 6 <= data.length, 'Invalid PE header offset');
  assert.equal(data.toString('ascii', offset, offset + 4), 'PE\0\0', 'Invalid PE signature');
  assert.equal(data.readUInt16LE(offset + 4), 0x8664, 'Expected x64 PE');
  return 'x86_64-pc-windows-msvc';
}

export function assertVersions(versions) {
  assert(versions.length >= 3 && versions.every(value => typeof value === 'string'
    && value.length > 0 && value === versions[0]), 'Application versions disagree');
}

function run(command, args, options = {}) {
  return execFileSync(command, args, { encoding: 'utf8', timeout: 120_000, ...options }).trim();
}

function files(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? files(path) : entry.isFile() ? [path] : [];
  });
}

function exactlyOne(paths, description) {
  assert.equal(paths.length, 1, `Expected exactly one ${description}, found ${paths.length}`);
  return paths[0];
}

export function checkPayload(directory, mainName, sidecarName, target) {
  const payload = files(directory);
  for (const name of [mainName, sidecarName]) {
    const path = exactlyOne(payload.filter(file => basename(file).toLowerCase() === name.toLowerCase()), name);
    const descriptor = openSync(path, 'r');
    const header = Buffer.alloc(4096);
    let length;
    try { length = readSync(descriptor, header); } finally { closeSync(descriptor); }
    // Check payloads, not the possibly x86 NSIS launcher stub.
    assert.equal(executableTarget(header.subarray(0, length)), target);
  }
  for (const name of ['LICENSE', 'THIRD_PARTY_LICENSES.md']) {
    assert(payload.some(path => basename(path) === name && readFileSync(path).length > 0),
      `Missing bundled notice: ${name}`);
  }
}

export function checkBundle(target, bundleDirectory, output) {
  mkdirSync(output, { recursive: true });
  const report = {
    schema_version: 1, status: 'failed', target,
    commit: process.env.GITHUB_SHA ?? run('git', ['rev-parse', 'HEAD']),
    workflow_url: process.env.GITHUB_RUN_ID
      ? `${process.env.GITHUB_SERVER_URL}/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}` : null,
    runner: { os: process.platform, release: release(), arch: arch(), image: process.env.ImageVersion ?? null },
    not_tested: ['installer installation/upgrade', 'physical microphone/global hotkey/tray',
      'native editor/secure-field integration', 'TCC/Accessibility/portal user consent',
      'Gatekeeper/SmartScreen/notarization trust', 'real-model inference on this OS'],
  };
  let temp;
  let mount;
  try {
    const pkg = JSON.parse(readFileSync(join(root, 'package.json')));
    const lock = JSON.parse(readFileSync(join(root, 'package-lock.json')));
    const config = JSON.parse(readFileSync(join(root, 'src-tauri/tauri.conf.json')));
    const cargo = readFileSync(join(root, 'src-tauri/Cargo.toml'), 'utf8').match(/^version = "([^"]+)"/m)?.[1];
    assertVersions([pkg.version, lock.version, lock.packages[''].version, config.version, cargo]);
    report.version = pkg.version;
    const windows = target === 'x86_64-pc-windows-msvc';
    assert(windows || target === 'aarch64-apple-darwin', 'Unsupported native target');
    assert.equal(process.platform, windows ? 'win32' : 'darwin', 'Use a native OS runner');
    assert.equal(arch(), windows ? 'x64' : 'arm64', 'Use a native architecture runner');
    const installerDirectory = join(bundleDirectory, windows ? 'nsis' : 'dmg');
    const installer = exactlyOne(readdirSync(installerDirectory, { withFileTypes: true })
      .filter(entry => entry.isFile() && entry.name.toLowerCase().endsWith(windows ? '.exe' : '.dmg'))
      .map(entry => join(installerDirectory, entry.name)), 'installer');
    temp = mkdtempSync(join(tmpdir(), 'voicewright-native-'));
    if (windows) {
      run('7z', ['x', '-y', `-o${temp}`, installer]);
      checkPayload(temp, 'voicewright.exe', 'voicewright-cleanup.exe', target);
      report.signature = run('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command',
        '(Get-AuthenticodeSignature -LiteralPath $env:VOICEWRIGHT_INSTALLER).Status.ToString()'],
      { env: { ...process.env, VOICEWRIGHT_INSTALLER: installer } });
    } else {
      run('hdiutil', ['verify', installer]);
      mount = join(temp, 'mount');
      mkdirSync(mount);
      run('hdiutil', ['attach', '-readonly', '-nobrowse', '-mountpoint', mount, installer]);
      const app = exactlyOne(readdirSync(mount).filter(name => name.endsWith('.app')).map(name => join(mount, name)), 'app bundle');
      const plist = join(app, 'Contents/Info.plist');
      const property = key => run('plutil', ['-extract', key, 'raw', '-o', '-', plist]);
      assert.equal(property('CFBundleIdentifier'), config.identifier);
      assert.equal(property('CFBundleShortVersionString'), pkg.version.split('-')[0]);
      checkPayload(join(app, 'Contents'), property('CFBundleExecutable'), 'voicewright-cleanup', target);
      const signature = spawnSync('codesign', ['-dv', '--verbose=2', app], { encoding: 'utf8', timeout: 30_000 });
      report.signature = signature.status === 0
        ? (signature.stderr.includes('Signature=adhoc') ? 'ad-hoc (not notarized)' : 'present (trust not tested)')
        : 'not verified (unsigned or invalid)';
    }
    report.installer = { file: basename(installer), sha256: createHash('sha256').update(readFileSync(installer)).digest('hex') };
    copyFileSync(installer, join(output, basename(installer)));
    writeFileSync(join(output, 'SHA256SUMS.txt'), `${report.installer.sha256}  ${basename(installer)}\n`);
    report.status = 'passed';
  } catch (error) {
    report.error = String(error);
  } finally {
    // Detach before removing our own temporary extraction directory. Never delete
    // mounted contents or an unrelated directory after a failed detach.
    let detached = !mount;
    if (mount) {
      const result = spawnSync('hdiutil', ['detach', mount], { encoding: 'utf8', timeout: 30_000 });
      detached = result.status === 0;
      if (!detached) { report.status = 'failed'; report.error = 'Could not detach test DMG'; }
    }
    if (temp && detached) rmSync(temp, { recursive: true, force: true });
    writeFileSync(join(output, 'report.json'), `${JSON.stringify(report, null, 2)}\n`);
  }
  console.log(`Native package validation: ${report.status}`);
  return report.status === 'passed' ? 0 : 1;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const { values } = parseArgs({ options: {
    target: { type: 'string' }, 'bundle-dir': { type: 'string' }, output: { type: 'string' },
  } });
  assert(values.target && values['bundle-dir'] && values.output, 'Supply --target, --bundle-dir and --output');
  process.exitCode = checkBundle(values.target, resolve(values['bundle-dir']), resolve(values.output));
}
