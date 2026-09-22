from __future__ import annotations

import socket
import tempfile
import threading
import unittest
from pathlib import Path

from onioncall.identity import load_or_create_identity
from onioncall.listener import accept_authenticated
from onioncall.protocol import perform_client_handshake


class ListenerDosTests(unittest.TestCase):
    def test_idle_client_does_not_block_legitimate_handshake(self) -> None:
        psk = b"P" * 32
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            server_identity = load_or_create_identity(home / "server")
            client_identity = load_or_create_identity(home / "client")
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.bind(("127.0.0.1", 0))
            # Put the socket into listening state synchronously.  The original
            # test used sleep(0.1) to wait for the server thread, which is not a
            # reliable synchronization primitive on loaded CI runners.
            listener.listen(16)
            port = listener.getsockname()[1]
            result: list[object] = []
            errors: list[BaseException] = []

            def serve() -> None:
                try:
                    result.append(
                        accept_authenticated(
                            listener,
                            psk,
                            server_identity,
                            handshake_timeout=10.0,
                            max_pending=4,
                        )
                    )
                except BaseException as exc:  # pragma: no cover - debugging aid
                    errors.append(exc)

            thread = threading.Thread(target=serve, daemon=True)
            thread.start()
            stalled = socket.create_connection(("127.0.0.1", port), timeout=5)
            client_sock = socket.create_connection(("127.0.0.1", port), timeout=5)
            client_channel = perform_client_handshake(client_sock, psk, client_identity, timeout=5.0)
            thread.join(timeout=5)

            stalled.close()
            client_channel.close()
            listener.close()
            if result:
                result[0].close()

            self.assertFalse(errors, errors)
            self.assertTrue(result, "Server hat keinen authentifizierten Kanal zurückgegeben")


if __name__ == "__main__":
    unittest.main()
