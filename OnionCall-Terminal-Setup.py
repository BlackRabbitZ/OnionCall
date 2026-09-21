#!/usr/bin/env python3
"""Terminal-Setup für OnionCall ohne Browseroberfläche."""
from __future__ import annotations
import runpy
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

if __name__ == "__main__":
    backend = Path(__file__).resolve().parent / "scripts" / "setup_backend.py"
    ns = runpy.run_path(str(backend))
    raise SystemExit(ns["main"]())
