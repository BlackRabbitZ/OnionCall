#!/usr/bin/env python3
"""Startet die vorhandene OnionCall-Terminalmenü direkt mit Python."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


_configure_utf8_stdio()

ROOT = Path(__file__).resolve().parent
VENV_PYTHON = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
if VENV_PYTHON.exists() and os.environ.get("ONIONCALL_VENV_ACTIVE") != "1":
    env = os.environ.copy(); env["ONIONCALL_VENV_ACTIVE"] = "1"; env["PYTHONIOENCODING"] = "utf-8"; env["PYTHONUTF8"] = "1"
    raise SystemExit(subprocess.call([str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]], env=env))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from onioncall.cli import run_terminal
if __name__ == "__main__":
    raise SystemExit(run_terminal())
