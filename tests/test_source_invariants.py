from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SourceInvariantTests(unittest.TestCase):
    def test_direct_socket_creation_not_scattered(self):
        root = Path(__file__).resolve().parents[1] / 'onioncall'
        allowed = {'tor.py'}
        offenders = []
        for path in root.glob('*.py'):
            if path.name in allowed:
                continue
            if 'socket.create_connection' in path.read_text(encoding='utf-8'):
                offenders.append(path.name)
        self.assertEqual(offenders, [], f'Direkte Outbound-Sockets außerhalb tor.py: {offenders}')

    def test_windows_killswitch_script_exists(self):
        self.assertTrue((ROOT / "scripts" / "onioncall-killswitch-windows.ps1").is_file())

    def test_python_only_launchers(self):
        project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertNotIn("[project.scripts]", project)
        self.assertTrue((ROOT / "Start-OnionCall.py").is_file())


if __name__ == '__main__':
    unittest.main()
