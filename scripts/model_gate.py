#!/usr/bin/env python3
"""Real CPU-model CI tests. No microphone, desktop, cloud key or private data."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import signal
import struct
import subprocess
import tempfile
import time
import wave

ROOT = Path(__file__).resolve().parent.parent


def load_models():
    return json.loads((ROOT / "scripts/model-gate-models.json").read_text())


def sha256(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def verify_model(path, entry):
    if path.is_symlink() or path.stat().st_size != entry["bytes"]:
        raise ValueError(f"Wrong model size or symlink: {entry['file']}")
    if sha256(path) != entry["sha256"]:
        raise ValueError(f"Wrong model SHA256: {entry['file']}")


def fetch_model(cache, entry):
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / entry["file"]
    if path.exists() or path.is_symlink():
        verify_model(path, entry)  # Never trust even a successful Actions cache hit.
        return path
    fd, partial = tempfile.mkstemp(prefix="download-", dir=cache)
    os.close(fd)
    partial = Path(partial)
    try:
        subprocess.run([
            "curl", "--fail", "--silent", "--show-error", "--location",
            "--proto", "=https", "--proto-redir", "=https", "--retry", "1",
            "--connect-timeout", "30", "--max-time", "180",
            "--max-filesize", str(entry["bytes"]),
            "--output", str(partial), entry["url"],
        ], check=True, timeout=400)
        verify_model(partial, entry)
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)
    return path


def validate_wav(path):
    with wave.open(str(path), "rb") as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(),
                audio.getcomptype()) != (1, 2, 16000, "NONE"):
            raise ValueError("Fixtures must be 16 kHz mono PCM16 WAV")
        duration = audio.getnframes() / 16000
        if not 0.5 <= duration <= 30:
            raise ValueError("Synthetic fixture duration outside 0.5–30 seconds")
        raw = audio.readframes(audio.getnframes())
    samples = [sample[0] for sample in struct.iter_unpack("<h", raw)]
    rms = math.sqrt(sum(value * value for value in samples) / len(samples))
    if rms < 100:
        raise ValueError("Synthetic speech fixture is silent or too quiet")
    return {"file": path.name, "sha256": sha256(path),
            "duration_seconds": duration, "rms_pcm16": rms}


def run_check(name, command, env, report, output, timeout, rust_test=False):
    result = {"name": name, "status": "failed", "timed_out": False,
              "timeout_seconds": timeout}
    report["checks"].append(result)
    started = time.monotonic()
    try:
        with (output / f"{name}.log").open("wb") as log:
            with subprocess.Popen(command, cwd=ROOT, env=env, stdout=log,
                                  stderr=subprocess.STDOUT, start_new_session=True) as child:
                try:
                    result["exit_code"] = child.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    result["timed_out"] = True
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass  # The process group exited between timeout and kill.
                    result["exit_code"] = child.wait()
        if result["exit_code"] != 0 or result["timed_out"]:
            raise RuntimeError(f"{name} failed; see {name}.log")
        if rust_test and not re.search(
                r"test result: ok\. 1 passed; 0 failed; 0 ignored;",
                (output / f"{name}.log").read_text()):
            raise RuntimeError(f"{name} did not execute exactly one real-model test")
        result["status"] = "passed"
    finally:
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)


def new_report():
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                         text=True, timeout=10).strip()
    except (OSError, subprocess.SubprocessError):
        commit = None
    return {
        "schema_version": 1, "commit": commit,
        "workflow_url": (f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
                         f"{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/"
                         f"{os.environ['GITHUB_RUN_ID']}"
                         if os.environ.get("GITHUB_RUN_ID")
                         and os.environ.get("GITHUB_REPOSITORY") else None),
        "runner": {"os": platform.platform(), "arch": platform.machine(),
                   "name": os.environ.get("RUNNER_NAME", "local")},
        "engine": "real-local-cpu", "status": "failed", "checks": [],
        "not_tested": ["physical microphone or virtual microphone capture",
                       "desktop insertion, hotkey, tray and onboarding",
                       "Wayland portal grants or native Windows/macOS permissions",
                       "broad ASR accuracy, WER/CER, noisy/long audio and resource limits"],
    }


def execute(cache, output, report):
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    try:
        if not report.get("commit"):
            raise RuntimeError("Source commit unavailable; cannot attest the model run")
        entries = load_models()
        if len(entries) != 2:
            raise ValueError("Expected exactly the pinned Whisper and Qwen models")
        paths = [fetch_model(cache, entry).resolve() for entry in entries]
        report["models"] = entries
        env = os.environ.copy()
        # Ignore personal shell model selections; all weights must pass this gate.
        env["VOICEWRIGHT_WHISPER_MODEL"] = str(paths[0])
        env["VOICEWRIGHT_TEST_GGUF"] = str(paths[1])
        with tempfile.TemporaryDirectory(prefix="voicewright-synthetic-") as fixtures:
            env["VOICEWRIGHT_FIXTURES"] = fixtures
            report["fixtures"] = []
            for lang, voice, text in [
                ("de", "de", "Guten Morgen. Das ist ein Diktat auf Deutsch."),
                ("en", "en-us", "Good morning. This is a dictation test in English."),
            ]:
                source = Path(fixtures) / f"{lang}-source.wav"
                with source.open("wb") as audio:
                    subprocess.run(["espeak-ng", "-v", voice, "--stdout", text],
                                   stdout=audio, check=True, timeout=30)
                target = Path(fixtures) / f"{lang}.wav"
                subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i",
                                str(source), "-ac", "1", "-ar", "16000", "-c:a",
                                "pcm_s16le", str(target)], check=True, timeout=30)
                report["fixtures"].append(validate_wav(target))
            for tool, command in [
                ("rust", ["rustc", "--version"]),
                ("espeak", ["espeak-ng", "--version"]),
                ("ffmpeg", ["ffmpeg", "-version"]),
            ]:
                run_check(tool, command, env, report, output, 30)
            for name, manifest, suite, test in [
                ("whisper", "src-tauri/Cargo.toml", "speech",
                 "recognizes_german_and_english_locally"),
                ("qwen", "engines/cleanup/Cargo.toml", "protocol",
                 "cleans_english_and_german_with_local_weights"),
            ]:
                run_check(name, ["cargo", "test", "--manifest-path", manifest,
                                "--locked", "--test", suite, test, "--",
                                "--ignored", "--exact"], env, report, output,
                          300, rust_test=True)
        report["status"] = "passed"
    except Exception as error:
        # This is the top-level evidence boundary, including malformed WAV/catalog
        # failures. Never turn an unexpected exception into a successful check.
        report["error"] = str(error)
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Real-model gate: {report['status']}; report: {output / 'report.json'}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(execute(args.cache.resolve(), args.output.resolve(), new_report()))
