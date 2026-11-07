import { copyFileSync, mkdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { execFileSync } from 'node:child_process';

const cargo = process.env.CARGO || 'cargo';
const host = execFileSync('rustc', ['-vV'], { encoding: 'utf8' }).match(/^host: (.+)$/m)?.[1].trim();
const target = process.argv[2] || host;
if (!target || !/^[\w-]+$/.test(target)) throw new Error('Invalid target triple');
const targetDir = resolve('engines/cleanup/target');
execFileSync(cargo, ['build', '--locked', '--release', '--manifest-path', 'engines/cleanup/Cargo.toml',
  '--target-dir', targetDir, '--target', target], { stdio: 'inherit' });
const suffix = target.includes('windows') ? '.exe' : '';
mkdirSync('src-tauri/binaries', { recursive: true });
copyFileSync(resolve(targetDir, target, 'release', 'voxtakt-cleanup' + suffix),
  'src-tauri/binaries/voxtakt-cleanup-' + target + suffix);
