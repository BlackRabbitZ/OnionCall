from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from onioncall.webgui import HTML, ICON_PNG, GuiController, create_server


class WebGuiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_home = tempfile.TemporaryDirectory()
        self.previous_home = os.environ.get("ONIONCALL_HOME")
        os.environ["ONIONCALL_HOME"] = self.temp_home.name
        self.server = create_server(0, GuiController())
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        if self.previous_home is None:
            os.environ.pop("ONIONCALL_HOME", None)
        else:
            os.environ["ONIONCALL_HOME"] = self.previous_home
        self.temp_home.cleanup()

    def request(self, path: str, *, token: str | None = None, method: str = "POST") -> tuple[int, dict]:
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["X-OnionCall-Token"] = token
        request = urllib.request.Request(
            self.origin + path,
            data=b"{}" if method == "POST" else None,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            return exc.code, json.load(exc)

    def test_gui_contains_no_remote_assets_or_legacy_crypto(self) -> None:
        self.assertNotIn("http://", HTML)
        self.assertNotIn("https://", HTML)
        self.assertNotIn("AES-256-CBC", HTML)
        self.assertIn("BRZ – OnionCall", HTML)
        self.assertIn("/icon.png", HTML)
        self.assertTrue(ICON_PNG.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_render_script_has_no_multiline_single_quote_regression(self) -> None:
        self.assertIn("Noch nicht erstellt. Starte „Empfangen“.';", HTML)
        self.assertNotIn("Noch nicht erstellt.\nStarte „Empfangen“.';", HTML)

    def test_gui_serves_application_icon(self) -> None:
        with urllib.request.urlopen(self.origin + "/icon.png", timeout=5) as response:
            icon = response.read()
        self.assertEqual(response.headers.get_content_type(), "image/png")
        self.assertEqual(icon, ICON_PNG)

    def test_post_requires_random_session_token(self) -> None:
        status, body = self.request("/api/disconnect")
        self.assertEqual(status, 403)
        self.assertIn("error", body)
        status, body = self.request("/api/disconnect", token=self.server.token)
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])

    def test_status_requires_token(self) -> None:
        status, body = self.request("/api/status", method="GET")
        self.assertEqual(status, 403)
        self.assertIn("error", body)
        status, body = self.request("/api/status", token=self.server.token, method="GET")
        self.assertEqual(status, 200)
        self.assertIn("tor_found", body)
        self.assertIn("key_ok", body)


if __name__ == "__main__":
    unittest.main()
