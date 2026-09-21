from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path

from onioncall.identity import load_or_create_identity
from onioncall.listener import accept_authenticated
from onioncall.protocol import perform_client_handshake


class ListenerTests(unittest.TestCase):
    def test_bad_first_client_does_not_consume_listener(self):
        psk = os.urandom(32)
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            sid = load_or_create_identity(Path(a))
            cid = load_or_create_identity(Path(b))
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
            result = {}

            def server():
                result['channel'] = accept_authenticated(listener, psk, sid, handshake_timeout=.5)

            thread = threading.Thread(target=server)
            thread.start()
            bad = socket.create_connection(('127.0.0.1', port))
            bad.sendall(b'garbage')
            bad.close()
            time.sleep(.3)
            good = socket.create_connection(('127.0.0.1', port))
            channel = perform_client_handshake(good, psk, cid, timeout=2)
            thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertIsNotNone(result.get('channel'))
            channel.close(); result['channel'].close(); listener.close()


if __name__ == '__main__':
    unittest.main()
