from __future__ import annotations

import os
import socket
import tempfile
import threading
import unittest
from pathlib import Path

from onioncall.crypto import AuthenticationError
from onioncall.identity import load_or_create_identity
from onioncall.protocol import MessageType, perform_client_handshake, perform_server_handshake


class ProtocolTests(unittest.TestCase):
    def identities(self):
        a = tempfile.TemporaryDirectory()
        b = tempfile.TemporaryDirectory()
        self.addCleanup(a.cleanup)
        self.addCleanup(b.cleanup)
        return load_or_create_identity(Path(a.name)), load_or_create_identity(Path(b.name))

    def test_authenticated_identity_bound_handshake(self):
        left, right = socket.socketpair()
        psk = os.urandom(32)
        client_id, server_id = self.identities()
        result = {}

        def server():
            channel = perform_server_handshake(left, psk, server_id)
            result['fp'] = channel.peer_fingerprint
            result['msg'] = channel.receive().payload
            channel.send(MessageType.TEXT, b'antwort')

        t = threading.Thread(target=server)
        t.start()
        client = perform_client_handshake(right, psk, client_id)
        client.send(MessageType.TEXT, b'hallo')
        self.assertEqual(client.receive().payload, b'antwort')
        t.join(2)
        self.assertEqual(result['msg'], b'hallo')
        self.assertTrue(str(result['fp']).startswith('BRZ-'))
        left.close(); right.close()

    def test_wrong_psk_rejected(self):
        left, right = socket.socketpair()
        client_id, server_id = self.identities()
        result = {}

        def server():
            try:
                perform_server_handshake(left, b'a'*32, server_id, timeout=1)
            except BaseException as exc:
                result['error'] = exc

        t = threading.Thread(target=server); t.start()
        with self.assertRaises(AuthenticationError):
            perform_client_handshake(right, b'b'*32, client_id, timeout=1)
        right.close(); t.join(2); left.close()
        self.assertIsInstance(result.get('error'), AuthenticationError)

    def test_changed_identity_rejected(self):
        left, right = socket.socketpair()
        psk = os.urandom(32)
        client_id, server_id = self.identities()
        fake_id, _ = self.identities()
        wrong_fp = fake_id.fingerprint

        def server():
            try:
                perform_server_handshake(left, psk, server_id, timeout=1)
            except BaseException:
                pass

        t = threading.Thread(target=server); t.start()
        with self.assertRaisesRegex(AuthenticationError, 'Fingerprint'):
            perform_client_handshake(right, psk, client_id, expected_fingerprint=wrong_fp, timeout=1)
        right.close(); t.join(2); left.close()


if __name__ == '__main__':
    unittest.main()
