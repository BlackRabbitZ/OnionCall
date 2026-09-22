from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class WindowsEncodingTests(unittest.TestCase):
    def _run_legacy_encoding(self, encoding: str, code: str) -> str:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = encoding
        env.pop("PYTHONUTF8", None)
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env=env,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        return result.stdout.decode("utf-8")

    def test_setup_backend_overrides_cp1252(self) -> None:
        output = self._run_legacy_encoding(
            "cp1252",
            "import scripts.setup_backend; print('UTF8-TEST → …')",
        )
        self.assertIn("UTF8-TEST → …", output)

    def test_cli_overrides_cp1252(self) -> None:
        output = self._run_legacy_encoding(
            "cp1252",
            "import onioncall.cli; print('UTF8-TEST → …')",
        )
        self.assertIn("UTF8-TEST → …", output)


if __name__ == "__main__":
    unittest.main()
