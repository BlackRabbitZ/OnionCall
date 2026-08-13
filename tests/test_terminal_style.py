from __future__ import annotations

import os
import unittest
from unittest import mock

from onioncall.terminal_style import BOLD, CYAN, brand, paint, status


class FakeStream:
    def __init__(self, interactive: bool):
        self.interactive = interactive

    def isatty(self) -> bool:
        return self.interactive


class TerminalStyleTests(unittest.TestCase):
    def test_interactive_terminal_uses_ansi_colors(self) -> None:
        stream = FakeStream(True)
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIn("\x1b[", paint("Text", BOLD, CYAN, stream=stream))
            self.assertIn("BRZ", brand("2.5.0", stream=stream))
            self.assertIn("\x1b[", status(True, stream=stream))

    def test_redirected_output_has_no_ansi_codes(self) -> None:
        self.assertEqual(paint("Text", BOLD, stream=FakeStream(False)), "Text")

    def test_no_color_environment_variable_is_honored(self) -> None:
        with mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
            self.assertEqual(paint("Text", BOLD, stream=FakeStream(True)), "Text")


if __name__ == "__main__":
    unittest.main()
