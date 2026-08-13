from __future__ import annotations

import importlib.util
import json
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path


def load_setup_module():
    path = Path(__file__).parents[1] / "OnionCall-Setup.py"
    spec = importlib.util.spec_from_file_location("onioncall_setup", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Setup-Modul konnte nicht geladen werden")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


setup = load_setup_module()


def load_terminal_setup_module():
    path = Path(__file__).parents[1] / "OnionCall-Terminal-Setup.py"
    spec = importlib.util.spec_from_file_location("onioncall_terminal_setup", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Terminal-Setup-Modul konnte nicht geladen werden")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


terminal_setup = load_terminal_setup_module()


class SetupScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = setup.SetupServer(setup.InstallState())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_setup_page_is_local_and_self_contained(self) -> None:
        with urllib.request.urlopen(self.server.origin, timeout=2) as response:
            html = response.read().decode()
        self.assertEqual(response.status, 200)
        self.assertNotIn('<script src="', html)
        self.assertNotIn('<link rel="stylesheet"', html)
        self.assertIn("Installation starten", html)

    def test_setup_actions_require_session_token(self) -> None:
        request = urllib.request.Request(self.server.origin + "/api/install", data=b"{}", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=2)
        self.assertEqual(caught.exception.code, 403)
        self.assertIn("error", json.load(caught.exception))

    def test_supported_package_managers_have_commands(self) -> None:
        for manager in ("pkg", "dnf", "apt-get", "pacman", "brew"):
            with self.subTest(manager=manager):
                commands = setup.package_command(manager)
                self.assertTrue(commands)
                self.assertEqual(commands[0][0], manager)

    def test_terminal_setup_has_no_web_server_dependency(self) -> None:
        source = (Path(__file__).parents[1] / "OnionCall-Terminal-Setup.py").read_text(encoding="utf-8")
        self.assertNotIn("http.server", source)
        self.assertNotIn("webbrowser", source)
        self.assertEqual(terminal_setup.MIN_REPOSITORY_VERSION, (2, 3, 0))


if __name__ == "__main__":
    unittest.main()
