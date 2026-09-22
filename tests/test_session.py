from __future__ import annotations

import unittest

from onioncall.session import safe_display


class SessionTests(unittest.TestCase):
    def test_terminal_escape_is_sanitized(self) -> None:
        self.assertNotIn("\x1b", safe_display("hi\x1b[31mred"))
        self.assertIn("�", safe_display("x\x00y"))


if __name__ == "__main__":
    unittest.main()
