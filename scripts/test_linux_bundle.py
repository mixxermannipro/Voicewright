import importlib.util
import tempfile
import unittest
import shutil
from pathlib import Path


spec = importlib.util.spec_from_file_location("bundle", Path(__file__).with_name("check-linux-bundle.py"))
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)


class BundleTests(unittest.TestCase):
    def fixture(self, root):
        for name in ['voicewright', 'voicewright-cleanup']:
            binary = root / 'usr/bin' / name
            binary.parent.mkdir(parents=True, exist_ok=True)
            binary.write_text('fixture')
            binary.chmod(0o755)
        for destination, source in {
            'usr/share/metainfo/de.voicewright.desktop.metainfo.xml': 'src-tauri/linux/de.voicewright.desktop.metainfo.xml',
            'usr/share/doc/voicewright/LICENSE': 'LICENSE',
            'usr/share/doc/voicewright/THIRD_PARTY_LICENSES.md': 'docs/THIRD_PARTY_LICENSES.md',
            'usr/share/icons/hicolor/32x32/apps/voicewright.png': 'src-tauri/icons/32x32.png',
        }.items():
            target = root / destination
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        desktop = root / 'usr/share/applications/Voicewright.desktop'
        desktop.parent.mkdir(parents=True)
        desktop.write_text('[Desktop Entry]\nType=Application\nName=Voicewright\nExec=voicewright\nIcon=voicewright\nTerminal=false\n')

    def test_glibc_limit_is_numeric_not_lexicographic(self):
        self.assertEqual(bundle.glibc_versions("GLIBC_2.9 GLIBC_2.35 GLIBC_2.9"), [(2, 9), (2, 35)])
        with self.assertRaisesRegex(ValueError, "2.36"):
            bundle.check_glibc("GLIBC_2.36", (2, 35))

    def test_missing_sidecar_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / 'usr/bin/voicewright-cleanup').unlink()
            with self.assertRaisesRegex(ValueError, "voicewright-cleanup"):
                bundle.check_layout(root, False)

    def test_complete_unprivileged_layout_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            bundle.check_layout(root, False)

    def test_privileged_sidecar_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / 'usr/bin/voicewright-cleanup').chmod(0o4755)
            with self.assertRaisesRegex(ValueError, 'privileged'):
                bundle.check_layout(root, False)

    def test_missing_apprun_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "AppRun"):
                bundle.check_layout(Path(directory), True)


if __name__ == "__main__":
    unittest.main()
