from __future__ import annotations

import os
import socket
import tempfile
import threading
import unittest
from pathlib import Path

from onioncall.identity import load_or_create_identity
from onioncall.listener import accept_authenticated
from onioncall.protocol import perform_client_handshake


class ListenerTests(unittest.TestCase):
    def test_bad_first_client_does_not_consume_listener(self) -> None:
        psk = os.urandom(32)
        with tempfile.TemporaryDirectory() as server_tmp, tempfile.TemporaryDirectory() as client_tmp:
            server_identity = load_or_create_identity(Path(server_tmp))
            client_identity = load_or_create_identity(Path(client_tmp))
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.bind(("127.0.0.1", 0))
            # Listen synchronously before starting the worker thread.  This removes
            # a scheduler race where CI could attempt the first connection before
            # accept_authenticated() had called listen().
            listener.listen(16)
            port = listener.getsockname()[1]
            result = {}

            def server() -> None:
                result["channel"] = accept_authenticated(
                    listener,
                    psk,
                    server_identity,
                    handshake_timeout=10.0,
                )

            thread = threading.Thread(target=server)
            thread.start()
            bad = socket.create_connection(("127.0.0.1", port))
            bad.sendall(b"garbage")
            bad.close()
            good = socket.create_connection(("127.0.0.1", port))
            channel = perform_client_handshake(good, psk, client_identity, timeout=5)
            thread.join(5)

            self.assertFalse(thread.is_alive())
            self.assertIsNotNone(result.get("channel"))
            channel.close()
            result["channel"].close()
            listener.close()


if __name__ == "__main__":
    unittest.main()
