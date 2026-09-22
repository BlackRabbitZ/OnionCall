from __future__ import annotations

import http.client
import os
import tempfile
import threading
import unittest
from unittest.mock import patch

from onioncall.webgui import GuiController, create_server


class WebSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"ONIONCALL_HOME": self.tmp.name})
        self.env.start()
        self.controller = GuiController()
        self.server = create_server(0, self.controller)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.env.stop()
        self.tmp.cleanup()

    def test_security_headers_present(self) -> None:
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        connection.request("GET", "/", headers={"Host": f"127.0.0.1:{self.server.server_port}"})
        response = connection.getresponse()
        response.read()
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader("X-Frame-Options"), "DENY")
        self.assertEqual(response.getheader("Cross-Origin-Opener-Policy"), "same-origin")
        self.assertIn("geolocation=()", response.getheader("Permissions-Policy"))
        connection.close()

    def test_status_requires_token(self) -> None:
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        connection.request(
            "GET",
            "/api/status",
            headers={"Host": f"127.0.0.1:{self.server.server_port}"},
        )
        response = connection.getresponse()
        response.read()
        self.assertEqual(response.status, 403)
        connection.close()


if __name__ == "__main__":
    unittest.main()
