# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Voicewright (Windows, macOS, Linux).
# Build:  pyinstaller --noconfirm voicewright.spec
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

ROOT = Path(SPECPATH)
ASSETS = ROOT / "src" / "voicewright" / "assets"
sys.path.insert(0, str(ROOT / "src"))
from voicewright import __version__  # noqa: E402

datas = [(str(ASSETS), "assets")]
datas += collect_data_files("faster_whisper")          # Silero VAD model
binaries = collect_dynamic_libs("ctranslate2")
hiddenimports = (
    collect_submodules("pynput")
    + collect_submodules("keyring.backends")
    + ["voicewright.main", "voicewright.app"]
)

if sys.platform in ("win32", "darwin"):
    datas += collect_data_files("_sounddevice_data")   # bundled PortAudio
if sys.platform.startswith("linux"):
    hiddenimports += ["evdev"]

icon = str(ASSETS / ("icon.ico" if sys.platform == "win32" else "icon.icns" if sys.platform == "darwin" else "icon.png"))

a = Analysis(
    [str(ROOT / "scripts" / "launcher.py")],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    # Optional imports of dependencies that would bloat the bundle
    excludes=["tkinter", "matplotlib", "IPython", "PyQt5", "PyQt6", "torch", "tensorflow",
              "pandas", "pyarrow", "scipy", "numba", "llvmlite", "sklearn", "botocore", "boto3",
              "fiona", "pyogrio", "geopandas", "PIL", "jupyter", "notebook", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Voicewright" if sys.platform != "linux" else "voicewright",
    console=False,
    icon=icon,
    upx=False,
    target_arch=None,
)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Voicewright")

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Voicewright.app",
        icon=icon,
        bundle_identifier="io.github.voicewright",
        version=__version__,
        info_plist={
            "CFBundleName": "Voicewright",
            "CFBundleDisplayName": "Voicewright",
            "CFBundleShortVersionString": __version__,
            "CFBundleVersion": __version__,
            "NSMicrophoneUsageDescription": "Voicewright records your voice to transcribe it locally.",
            "NSAppleEventsUsageDescription": "Voicewright inserts dictated text into the active app.",
            "LSUIElement": True,              # menu-bar app, no Dock icon
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
        },
    )
