from __future__ import annotations

import importlib.util
import socket
import threading
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("tor_http_proxy", ROOT / "scripts" / "tor_http_proxy.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class TorHttpProxyTests(unittest.TestCase):
    def test_parse_domain(self):
        self.assertEqual(MODULE.parse_connect_target("pypi.org:443"), ("pypi.org", 443))

    def test_parse_ipv6(self):
        self.assertEqual(MODULE.parse_connect_target("[::1]:443"), ("::1", 443))

    def test_domain_is_sent_to_socks_without_local_dns(self):
        client, server = socket.socketpair()
        recorded = {}

        def fake_socks():
            self.assertEqual(server.recv(3), b"\x05\x01\x00")
            server.sendall(b"\x05\x00")
            head = server.recv(5)
            self.assertEqual(head[:4], b"\x05\x01\x00\x03")
            length = head[4]
            host = server.recv(length).decode("ascii")
            port = int.from_bytes(server.recv(2), "big")
            recorded.update(host=host, port=port)
            server.sendall(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")

        t = threading.Thread(target=fake_socks)
        t.start()
        with mock.patch.object(MODULE.socket, "create_connection", return_value=client):
            out = MODULE.tor_socks_connect("files.pythonhosted.org", 443, 19052)
        t.join(timeout=2)
        self.assertEqual(recorded, {"host": "files.pythonhosted.org", "port": 443})
        out.close()
        server.close()

    def test_full_connect_tunnel_via_fake_socks(self):
        socks_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socks_listener.bind(("127.0.0.1", 0))
        socks_listener.listen(1)
        socks_port = socks_listener.getsockname()[1]
        seen = {}

        def fake_socks_server():
            conn, _ = socks_listener.accept()
            with conn:
                self.assertEqual(conn.recv(3), b"\x05\x01\x00")
                conn.sendall(b"\x05\x00")
                head = conn.recv(5)
                self.assertEqual(head[:4], b"\x05\x01\x00\x03")
                length = head[4]
                host = conn.recv(length).decode("ascii")
                port = int.from_bytes(conn.recv(2), "big")
                seen.update(host=host, port=port)
                conn.sendall(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
                payload = conn.recv(5)
                conn.sendall(payload)

        socks_thread = threading.Thread(target=fake_socks_server, daemon=True)
        socks_thread.start()
        proxy = MODULE.TorHttpProxy(socks_port)
        proxy_thread = threading.Thread(target=proxy.serve_forever, daemon=True)
        proxy_thread.start()
        try:
            with socket.create_connection(("127.0.0.1", proxy.port), timeout=2) as client:
                client.sendall(b"CONNECT example.invalid:443 HTTP/1.1\r\nHost: example.invalid:443\r\n\r\n")
                response = client.recv(4096)
                self.assertIn(b"200 Connection Established", response)
                client.sendall(b"hello")
                self.assertEqual(client.recv(5), b"hello")
            self.assertEqual(seen, {"host": "example.invalid", "port": 443})
        finally:
            proxy.shutdown()
            proxy.server_close()
            socks_listener.close()
            proxy_thread.join(timeout=2)
            socks_thread.join(timeout=2)

    def test_proxy_binds_loopback_only(self):
        proxy = MODULE.TorHttpProxy(19052)
        try:
            self.assertEqual(proxy.server_address[0], "127.0.0.1")
            self.assertGreater(proxy.port, 0)
        finally:
            proxy.server_close()


if __name__ == "__main__":
    unittest.main()
