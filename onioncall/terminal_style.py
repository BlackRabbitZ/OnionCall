from __future__ import annotations

import os
import sys
from typing import TextIO

RESET = "\x1b[0m"
BOLD = "1"
DIM = "2"
RED = "31"
GREEN = "32"
YELLOW = "33"
BLUE = "34"
MAGENTA = "35"
CYAN = "36"
WHITE = "37"


def colors_enabled(stream: TextIO | None = None) -> bool:
    """Use colors only for an interactive terminal and honor NO_COLOR."""
    stream = stream or sys.stdout
    return "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb" and stream.isatty()


def paint(text: str, *codes: str, stream: TextIO | None = None) -> str:
    if not codes or not colors_enabled(stream):
        return text
    return f"\x1b[{';'.join(codes)}m{text}{RESET}"


def brand(version: str | None = None, *, stream: TextIO | None = None) -> str:
    name = f"{paint('BRZ', BOLD, MAGENTA, stream=stream)} {paint('–', DIM, WHITE, stream=stream)} "
    name += paint("OnionCall", BOLD, CYAN, stream=stream)
    if version:
        name += " " + paint(version, DIM, WHITE, stream=stream)
    return name


def status(value: bool, *, stream: TextIO | None = None) -> str:
    if value:
        return paint("[OK]", BOLD, GREEN, stream=stream)
    return paint("[FEHLT]", BOLD, RED, stream=stream)
