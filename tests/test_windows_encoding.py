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
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        return result.stdout.decode("utf-8")

    def test_setup_backend_overrides_cp1252(self) -> None:
        output = self._run_legacy_encoding(
            "cp1252",
            "import importlib.util, pathlib; "
            "p=pathlib.Path('scripts/setup_backend.py'); "
            "s=importlib.util.spec_from_file_location('setup_backend_test', p); "
            "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
            "print('UTF8: x → y … – ═')",
        )
        self.assertIn("x → y", output)
        self.assertIn("═", output)

    def test_terminal_setup_overrides_cp850(self) -> None:
        output = self._run_legacy_encoding(
            "cp850",
            "import runpy; runpy.run_path('OnionCall-Terminal-Setup.py', run_name='not_main'); "
            "print('UTF8: x → y … – ═')",
        )
        self.assertIn("x → y", output)
        self.assertIn("═", output)

    def test_gui_installer_reads_backend_as_utf8(self) -> None:
        source = (ROOT / "OnionCall-Setup.py").read_text(encoding="utf-8")
        self.assertIn('child_env["PYTHONIOENCODING"] = "utf-8"', source)
        self.assertIn('encoding="utf-8"', source)


    def test_gui_installer_consumes_utf8_backend_output(self) -> None:
        import importlib.util
        import tempfile

        installer_path = ROOT / "OnionCall-Setup.py"
        spec = importlib.util.spec_from_file_location("onioncall_setup_test", installer_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            backend = Path(tmp) / "backend.py"
            backend.write_text(
                "print('::progress::40::UTF8 x → y … – ═', flush=True)\n"
                "print('Backend Unicode: ✓', flush=True)\n",
                encoding="utf-8",
            )
            old_backend = module.BACKEND
            try:
                module.BACKEND = backend
                state = module.InstallState()
                state._install()
            finally:
                module.BACKEND = old_backend
            snap = state.snapshot()
            self.assertEqual(snap["status"], "done", snap)
            messages = "\n".join(str(event["message"]) for event in snap["events"])
            self.assertIn("UTF8 x → y", messages)
            self.assertIn("Backend Unicode: ✓", messages)

    def test_setup_status_line_uses_ascii_arrow(self) -> None:
        source = (ROOT / "scripts" / "setup_backend.py").read_text(encoding="utf-8")
        self.assertNotIn(" → Tor SOCKS", source)
        self.assertIn(" -> Tor SOCKS", source)


if __name__ == "__main__":
    unittest.main()
