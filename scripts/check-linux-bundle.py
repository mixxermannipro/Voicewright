#!/usr/bin/env python3
"""Validate locally/CI-built packages, not untrusted third-party executables."""
import argparse
import hashlib
import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path


def run(*args, **kwargs):
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, **kwargs)
    except subprocess.CalledProcessError as error:
        raise ValueError(f"{' '.join(args)} failed ({error.returncode}):\n{error.output}") from error


def declared_glibc(dependencies):
    match = re.search(r'\blibc6\s*\(>=\s*(\d+)\.(\d+)', dependencies)
    if not match:
        raise ValueError('Missing versioned libc6 minimum in DEB dependencies')
    return tuple(map(int, match.groups()))


def glibc_versions(text):
    return sorted({tuple(map(int, version.split('.'))) for version in re.findall(r'\bGLIBC_(\d+\.\d+)\b', text)})


def check_glibc(text, maximum):
    versions = glibc_versions(text)
    if versions and versions[-1] > maximum:
        raise ValueError(f"GLIBC {'.'.join(map(str, versions[-1]))} exceeds {maximum}")
    return versions[-1] if versions else None


def check_layout(root, appimage):
    for relative in (['AppRun'] if appimage else []) + ['usr/bin/voicewright', 'usr/bin/voicewright-cleanup']:
        path = root / relative
        if not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError(f"Missing executable: {relative}")
    for relative in ['usr/share/metainfo/de.voicewright.desktop.metainfo.xml',
                     'usr/share/doc/voicewright/LICENSE',
                     'usr/share/doc/voicewright/THIRD_PARTY_LICENSES.md']:
        if not (root / relative).is_file():
            raise ValueError(f"Missing package file: {relative}")
    desktops = list((root / 'usr/share/applications').glob('*.desktop'))
    icons = list((root / 'usr/share/icons').rglob('*.png'))
    if not desktops or not icons:
        raise ValueError('Missing desktop entry or PNG icon')
    for desktop in desktops:
        run('desktop-file-validate', str(desktop))
    metadata = root / 'usr/share/metainfo/de.voicewright.desktop.metainfo.xml'
    # The launchable ID must refer to the actual generated desktop filename.
    import xml.etree.ElementTree as ET
    launchable = ET.parse(metadata).findtext('launchable')
    if launchable not in {path.name for path in desktops}:
        raise ValueError(f'AppStream launchable not packaged: {launchable}')
    run('appstreamcli', 'validate', '--no-net', str(metadata))
    for path in root.rglob('*'):
        if not path.is_symlink() and path.stat().st_mode & (stat.S_ISUID | stat.S_ISGID):
            raise ValueError(f'Unexpected privileged file: {path}')


def validate(artifact, maximum):
    with tempfile.TemporaryDirectory(prefix='voicewright-package-') as directory:
        root = Path(directory)
        appimage = artifact.suffix == '.AppImage'
        if appimage:
            run(str(artifact), '--appimage-extract', cwd=root)
            root /= 'squashfs-root'
        elif artifact.suffix == '.deb':
            run('dpkg-deb', '-x', str(artifact), str(root))
            dependencies = run('dpkg-deb', '-f', str(artifact), 'Depends')
            for name in ['libc6', 'libwebkit2gtk-4.1-0', 'libgtk-3-0', 'libasound2']:
                if name not in dependencies:
                    raise ValueError(f'Missing DEB dependency: {name}')
            # Never let --max-glibc conceal an understated DEB libc6 requirement.
            maximum = min(maximum, declared_glibc(dependencies))
            print(f'Depends: {dependencies.strip()}')
        else:
            raise ValueError('Expected .deb or .AppImage')
        check_layout(root, appimage)
        count = 0
        for path in root.rglob('*'):
            if not path.is_file() or path.is_symlink():
                continue
            with path.open('rb') as stream:
                if stream.read(4) != b'\x7fELF':
                    continue
            versions = run('readelf', '--version-info', str(path))
            try:
                check_glibc(versions, maximum)
            except ValueError as error:
                raise ValueError(f'{path.relative_to(root)}: {error}') from error
            count += 1
        if count < 2:
            raise ValueError('Application and sidecar must be ELF binaries')
        for name in ['voicewright', 'voicewright-cleanup']:
            env = dict(os.environ)
            if appimage:
                env['LD_LIBRARY_PATH'] = ':'.join(str(path) for path in [root / 'usr/lib', root / 'usr/lib/x86_64-linux-gnu'])
            linked = run('ldd', str(root / 'usr/bin' / name), env=env)
            if 'not found' in linked:
                raise ValueError(f'Unresolved runtime for {name}:\n{linked}')
        print(f'{artifact.name}: layout, permissions, metadata, runtime and {count} ELF ABI checks passed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-glibc', default='2.35')
    parser.add_argument('artifacts', nargs='+', type=Path)
    args = parser.parse_args()
    maximum = tuple(map(int, args.max_glibc.split('.')))
    for artifact in args.artifacts:
        validate(artifact.resolve(), maximum)
        digest = hashlib.sha256()
        with artifact.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        print(f'SHA256 {digest.hexdigest()}  {artifact.name}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(str(error)) from error
