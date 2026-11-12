"""Offline regression tests for the real-model CI gate (never load weights)."""
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

import model_gate as gate


class ModelGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = b"synthetic test model"
        self.entry = {"file": "fixture.bin", "bytes": len(self.data),
                      "sha256": hashlib.sha256(self.data).hexdigest(),
                      "url": "https://example.invalid/fixture.bin", "license": "MIT"}

    def test_revalidates_cached_weights_without_download(self):
        path = self.root / self.entry["file"]
        path.write_bytes(self.data)
        with patch("model_gate.subprocess.run") as download:
            self.assertEqual(gate.fetch_model(self.root, self.entry), path)
            download.assert_not_called()

    def test_rejects_corrupted_cache_before_inference(self):
        path = self.root / self.entry["file"]
        for data in (b"short", b"X" * len(self.data)):
            path.write_bytes(data)
            with self.assertRaises(ValueError):
                gate.fetch_model(self.root, self.entry)
            self.assertEqual(path.read_bytes(), data)

    def test_download_is_verified_before_atomic_promotion(self):
        def download(command, **_kwargs):
            Path(command[command.index("--output") + 1]).write_bytes(self.data)
        with patch("model_gate.subprocess.run", side_effect=download):
            path = gate.fetch_model(self.root, self.entry)
        self.assertEqual(path.read_bytes(), self.data)
        self.assertEqual(list(self.root.iterdir()), [path])

    def test_failed_or_corrupt_download_never_becomes_cache_entry(self):
        def corrupt(command, **_kwargs):
            Path(command[command.index("--output") + 1]).write_bytes(b"bad")
        for effect in (OSError("network unavailable"), corrupt):
            with patch("model_gate.subprocess.run", side_effect=effect):
                with self.assertRaises((OSError, ValueError)):
                    gate.fetch_model(self.root, self.entry)
            self.assertEqual(list(self.root.iterdir()), [])

    def write_wav(self, name="fixture.wav", rate=16000, value=1000, channels=1):
        path = self.root / name
        with wave.open(str(path), "wb") as out:
            out.setnchannels(channels)
            out.setsampwidth(2)
            out.setframerate(rate)
            out.writeframes(struct.pack("<h", value) * rate * channels)
        return path

    def test_validates_synthetic_wav_and_records_hash(self):
        path = self.write_wav()
        result = gate.validate_wav(path)
        self.assertEqual(result["duration_seconds"], 1)
        self.assertEqual(result["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_rejects_wrong_rate_channels_and_silence(self):
        for kwargs in ({"rate": 22050}, {"channels": 2}, {"value": 0}):
            with self.assertRaises(ValueError):
                gate.validate_wav(self.write_wav(**kwargs))

    def test_process_result_and_timeout_are_recorded(self):
        report = {"checks": []}
        gate.run_check("success", [sys.executable, "-c", "print('ok')"],
                       os.environ.copy(), report, self.root, 10)
        self.assertEqual(report["checks"][-1]["status"], "passed")
        for name, code, timeout in [("failure", "raise SystemExit(3)", 10),
                                    ("timeout", "import time; time.sleep(60)", 0.1)]:
            with self.assertRaises(RuntimeError):
                gate.run_check(name, [sys.executable, "-c", code],
                               os.environ.copy(), report, self.root, timeout)
            self.assertEqual(report["checks"][-1]["status"], "failed")
        self.assertEqual(report["checks"][1]["exit_code"], 3)
        self.assertTrue(report["checks"][2]["timed_out"])

    def test_zero_selected_rust_tests_cannot_report_success(self):
        with self.assertRaises(RuntimeError):
            gate.run_check("empty", [sys.executable, "-c", "print('0 passed')"],
                           os.environ.copy(), {"checks": []}, self.root, 10,
                           rust_test=True)

    def test_early_failure_still_writes_honest_report(self):
        report = gate.new_report()
        with patch("model_gate.fetch_model", side_effect=ValueError("damaged cache")):
            status = gate.execute(self.root / "cache", self.root / "out", report)
        saved = json.loads((self.root / "out" / "report.json").read_text())
        self.assertEqual(status, 1)
        self.assertEqual(saved["status"], "failed")
        self.assertEqual(saved["engine"], "real-local-cpu")
        self.assertIn("commit", saved)
        self.assertIn("runner", saved)
        self.assertTrue(saved["not_tested"])
        self.assertEqual(saved["checks"], [])

    def test_malformed_catalog_and_non_wav_failure_are_reported(self):
        for error in (wave.Error("invalid WAV"), IndexError("empty catalog")):
            with patch("model_gate.fetch_model", side_effect=error):
                status = gate.execute(self.root / "cache", self.root / "out",
                                      gate.new_report())
            self.assertEqual(status, 1)
            saved = json.loads((self.root / "out/report.json").read_text())
            self.assertIn(str(error), saved["error"])

    def test_missing_source_commit_is_explicit_not_a_traceback(self):
        with patch("model_gate.subprocess.check_output", side_effect=OSError("git missing")):
            report = gate.new_report()
        self.assertIsNone(report["commit"])
        status = gate.execute(self.root / "cache", self.root / "out", report)
        self.assertEqual(status, 1)

    def test_check_report_records_actual_time_budget(self):
        report = {"checks": []}
        gate.run_check("budget", [sys.executable, "-c", "pass"],
                       os.environ.copy(), report, self.root, 10)
        self.assertEqual(report["checks"][0]["timeout_seconds"], 10)

    def test_model_pins_match_production_catalog_and_documented_licenses(self):
        catalog = (gate.ROOT / "src-tauri/src/models.rs").read_text()
        docs = (gate.ROOT / "docs/MODELS.md").read_text()
        entries = gate.load_models()
        self.assertEqual(len(entries), 2)
        for entry in entries:
            for value in (entry["file"], str(entry["bytes"]), entry["sha256"],
                          entry["url"].split("/resolve/")[1].split("/")[0]):
                self.assertIn(value, catalog)
            self.assertIn(entry["license"], catalog)
            self.assertIn(entry["license"], docs)
            self.assertTrue(entry["url"].startswith("https://huggingface.co/"))


if __name__ == "__main__":
    unittest.main()
