from __future__ import annotations

import socket
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts import setup_backend

class SetupBackendTests(unittest.TestCase):
    def test_bootstrap_percent_uses_latest_value(self) -> None:
        text = (
            "Sep 22 07:00:00 Bootstrapped 5% (conn): Connecting to a relay\n"
            "Sep 22 07:00:02 Bootstrapped 55% (loading_descriptors): Loading relay descriptors\n"
            "Sep 22 07:00:04 Bootstrapped 100% (done): Done\n"
        )
        self.assertEqual(setup_backend._tor_bootstrap_percent(text), 100)

    def test_bootstrap_percent_handles_missing_progress(self) -> None:
        self.assertIsNone(setup_backend._tor_bootstrap_percent("Tor starting\n"))

    def test_free_loopback_port_is_bindable(self) -> None:
        port = setup_backend._free_loopback_port()
        self.assertGreaterEqual(port, 1)
        self.assertLessEqual(port, 65535)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))

    def test_old_fixed_private_port_was_removed(self) -> None:
        self.assertFalse(hasattr(setup_backend, "PRIVATE_SOCKS_PORT"))

    def test_ffmpeg_download_is_version_and_hash_pinned(self) -> None:
        self.assertIn("ffmpeg-9.0.2-essentials_build.zip", setup_backend.FFMPEG_WINDOWS_URL)
        self.assertEqual(len(setup_backend.FFMPEG_WINDOWS_SHA256), 64)
        int(setup_backend.FFMPEG_WINDOWS_SHA256, 16)

    def test_safe_zip_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "bad.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("../escape.txt", "no")
            with self.assertRaises(RuntimeError):
                setup_backend._safe_extract_zip(archive, root / "out")
            self.assertFalse((root / "escape.txt").exists())

    def test_safe_zip_extracts_normal_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "ok.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("ffmpeg/bin/ffmpeg.exe", "x")
                zf.writestr("ffmpeg/bin/ffplay.exe", "x")
            out = root / "out"
            setup_backend._safe_extract_zip(archive, out)
            self.assertTrue((out / "ffmpeg" / "bin" / "ffmpeg.exe").is_file())
            self.assertTrue((out / "ffmpeg" / "bin" / "ffplay.exe").is_file())


if __name__ == "__main__":
    unittest.main()
