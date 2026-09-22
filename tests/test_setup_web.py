from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request

from scripts.setup_web import create_server


class BrowserSetupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.token = "test-token-123"
        self.server = create_server(self.token)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = self.server.origin

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def request(self, path: str, *, method: str = "GET", token: str | None = None, origin: str | None = None):
        headers = {}
        if token is not None:
            headers["X-OnionCall-Token"] = token
        if origin is not None:
            headers["Origin"] = origin
        data = None
        if method == "POST":
            headers["Content-Type"] = "application/json"
            data = b"{}"
        return urllib.request.urlopen(
            urllib.request.Request(self.origin + path, method=method, headers=headers, data=data),
            timeout=5,
        )

    def test_page_is_browser_installer(self) -> None:
        with self.request("/") as response:
            body = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
            self.assertIn("BRZ – OnionCall Setup", body)
            self.assertIn("Installation starten", body)
            self.assertEqual(response.headers.get("Cache-Control"), "no-store, max-age=0")
            self.assertIn("nonce-", response.headers.get("Content-Security-Policy", ""))
            self.assertNotIn("'unsafe-inline'", response.headers.get("Content-Security-Policy", ""))
            self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_status_requires_token(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.request("/api/status")
        self.assertEqual(ctx.exception.code, 403)

        with self.request("/api/status", token=self.token) as response:
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertIn("checks", payload)
            self.assertIn("platform", payload)

    def test_write_requires_same_origin_and_token(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.request("/api/refresh", method="POST", token=self.token, origin="https://example.invalid")
        self.assertEqual(ctx.exception.code, 403)

        with self.request("/api/refresh", method="POST", token=self.token, origin=self.origin) as response:
            self.assertEqual(response.status, 200)
            self.assertTrue(json.loads(response.read().decode("utf-8"))["ok"])

    def test_wrong_token_is_rejected(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.request("/api/status", token="wrong")
        self.assertEqual(ctx.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
