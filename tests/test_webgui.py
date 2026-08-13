from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request

from onioncall.webgui import HTML, ICON_PNG, GuiController, GuiHttpServer


class WebGuiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = GuiHttpServer(("127.0.0.1", 0), GuiController())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, path: str, *, token: str | None = None) -> tuple[int, dict]:
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["X-OnionCall-Token"] = token
        request = urllib.request.Request(
            self.server.origin + path,
            data=b"{}",
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
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

    def test_gui_serves_application_icon(self) -> None:
        with urllib.request.urlopen(self.server.origin + "/icon.png", timeout=2) as response:
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

    def test_status_is_available_only_on_loopback_server(self) -> None:
        with urllib.request.urlopen(self.server.origin + "/api/status", timeout=2) as response:
            body = json.load(response)
        self.assertEqual(response.status, 200)
        self.assertIn("tor_found", body)
        self.assertIn("key_ok", body)


if __name__ == "__main__":
    unittest.main()
