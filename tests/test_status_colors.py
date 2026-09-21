from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StatusColorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "onioncall" / "webgui.py").read_text(encoding="utf-8")

    def test_tor_active_is_green(self):
        self.assertIn("dot('torDot',s.tor_active?'green':'red')", self.source)

    def test_key_state_is_green_or_red(self):
        self.assertIn("dot('keyDot',s.key_ok?'green':'red')", self.source)

    def test_audio_busy_is_yellow(self):
        self.assertIn("dot('audioDot',s.audio_busy?'yellow':s.audio_ok?'green':'red')", self.source)

    def test_connection_semantics(self):
        self.assertIn("dot('linkDot',s.connected?'green':['starting','connecting','authenticating','listening','stopping'].includes(s.state)?'yellow':'red')", self.source)

    def test_css_mapping_remains_unchanged(self):
        self.assertIn('.dot.ok{background:var(--green)}', self.source)
        self.assertIn('.dot.busy{background:var(--amber)}', self.source)
        self.assertIn('.dot{width:9px;height:9px;border-radius:50%;background:var(--red)', self.source)


if __name__ == '__main__':
    unittest.main()
