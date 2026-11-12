"""Check offline speech recognition and Qt clipboard output on synthetic audio."""
import hashlib
import os
import subprocess
import tempfile
import urllib.request
from pathlib import Path

REVISION = "d90ca5fe260221311c53c58e660288d3deb8d356"
BASE = f"https://huggingface.co/Systran/faster-whisper-tiny/resolve/{REVISION}"
CHECKSUMS = {
    "config.json": "a73a28cdfe1c43ccc7202fa333d1f89c202477271407ae9a7f19afa52039cac8",
    "model.bin": "dcb76c6586fc06cbdac6dd21f14cfd129cc4cdd9dce19bf4ffa62e59cbe6e6d1",
    "tokenizer.json": "fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab",
    "vocabulary.txt": "34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913",
}
PHRASES = (
    ("de", "de", "Das ist ein einfacher Test. Wir sprechen heute über das Wetter.", "wetter"),
    ("en", "en-us", "This is a simple test. Today we are talking about the weather.", "weather"),
)


def main() -> None:
    from faster_whisper.audio import decode_audio
    from PySide6.QtWidgets import QApplication

    from voicewright.config import Config
    from voicewright.injector import Injector
    from voicewright.transcriber import Transcriber

    with tempfile.TemporaryDirectory(prefix="voicewright-whisper-") as scratch:
        directory = Path(scratch)
        os.environ["VOICEWRIGHT_DATA_DIR"] = scratch
        model = directory / "models" / "tiny"
        model.mkdir(parents=True)
        cache = os.environ.get("VOICEWRIGHT_TEST_MODEL")
        for name, expected in CHECKSUMS.items():
            if cache:
                payload = (Path(cache) / name).read_bytes()
            else:
                with urllib.request.urlopen(f"{BASE}/{name}?download=true", timeout=90) as response:
                    payload = response.read()
            if hashlib.sha256(payload).hexdigest() != expected:
                raise RuntimeError(f"Checksum mismatch for {name}")
            (model / name).write_bytes(payload)

        app = QApplication([])
        config = Config(directory / "config.json")
        config.set("whisper_model", "tiny")
        config.set("whisper_device", "cpu")
        config.set("add_trailing_space", False)
        transcriber = Transcriber(config)
        output = Injector(config)
        for language, voice, phrase, expected_word in PHRASES:
            wav = directory / f"{language}.wav"
            subprocess.run(["espeak-ng", "-v", voice, "-s", "140", "-w", str(wav), phrase], check=True)
            config.set("language", language)
            text, detected_language = transcriber.transcribe(decode_audio(str(wav)))
            assert detected_language == language
            assert expected_word in text.casefold(), (language, text)
            output.insert(text)
            assert app.clipboard().text() == text
            print(f"{language}: {text}")


if __name__ == "__main__":
    main()
