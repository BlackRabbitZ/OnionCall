from __future__ import annotations

import os
import socket
import threading
import unittest

from onioncall.crypto import AuthenticationError
from onioncall.protocol import (
    FRAME_VERSION,
    HEADER,
    MessageType,
    ProtocolError,
    SecureChannel,
    perform_client_handshake,
    perform_server_handshake,
)


class RecordingSocket:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.writes: list[bytes] = []

    def sendall(self, data: bytes) -> None:
        self.writes.append(data)
        self.sock.sendall(data)

    def __getattr__(self, name: str):
        return getattr(self.sock, name)


class ProtocolTests(unittest.TestCase):
    def test_authenticated_handshake_and_bidirectional_messages(self) -> None:
        left, right = socket.socketpair()
        psk = os.urandom(32)
        result: dict[str, object] = {}

        def server() -> None:
            channel = perform_server_handshake(left, psk)
            result["message"] = channel.receive()
            channel.send(MessageType.TEXT, b"antwort")

        thread = threading.Thread(target=server)
        thread.start()
        client = perform_client_handshake(right, psk)
        client.send(MessageType.TEXT, b"hallo")
        response = client.receive()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result["message"].payload, b"hallo")
        self.assertEqual(response.payload, b"antwort")
        left.close()
        right.close()

    def test_wrong_secret_is_rejected(self) -> None:
        left, right = socket.socketpair()
        result: dict[str, BaseException] = {}

        def server() -> None:
            try:
                perform_server_handshake(left, b"a" * 32, timeout=1)
            except BaseException as exc:
                result["error"] = exc

        thread = threading.Thread(target=server)
        thread.start()
        with self.assertRaises(AuthenticationError):
            perform_client_handshake(right, b"b" * 32, timeout=1)
        right.close()
        thread.join(timeout=2)
        self.assertIsInstance(result.get("error"), AuthenticationError)
        left.close()

    def test_tampering_is_rejected(self) -> None:
        left, right = socket.socketpair()
        key = os.urandom(32)
        recording = RecordingSocket(left)
        sender = SecureChannel(recording, key, key)
        sender.send(MessageType.TEXT, b"unveraendert")
        wire = bytearray(recording.writes[0])
        wire[-1] ^= 1
        # Discard the original frame and inject the modified copy into a fresh pair.
        right.recv(len(wire))
        left2, right2 = socket.socketpair()
        receiver = SecureChannel(right2, key, key)
        left2.sendall(wire)
        with self.assertRaisesRegex(ProtocolError, "Manipuliertes"):
            receiver.receive()
        left.close()
        right.close()
        left2.close()
        right2.close()

    def test_replay_is_rejected(self) -> None:
        left, right = socket.socketpair()
        key = os.urandom(32)
        recording = RecordingSocket(left)
        sender = SecureChannel(recording, key, key)
        receiver = SecureChannel(right, key, key)
        sender.send(MessageType.PING, b"")
        self.assertEqual(receiver.receive().kind, MessageType.PING)
        left.sendall(recording.writes[0])
        with self.assertRaisesRegex(ProtocolError, "Replay"):
            receiver.receive()
        left.close()
        right.close()

    def test_type_specific_size_limit_is_enforced_before_body_read(self) -> None:
        left, right = socket.socketpair()
        key = os.urandom(32)
        receiver = SecureChannel(right, key, key)
        left.sendall(HEADER.pack(FRAME_VERSION, int(MessageType.TEXT), 0, 9000))
        with self.assertRaisesRegex(ProtocolError, "zu groß"):
            receiver.receive()
        left.close()
        right.close()

    def test_sender_rejects_oversized_text(self) -> None:
        left, right = socket.socketpair()
        channel = SecureChannel(left, os.urandom(32), os.urandom(32))
        with self.assertRaises(ProtocolError):
            channel.send(MessageType.TEXT, b"x" * (8192 + 1))
        left.close()
        right.close()


if __name__ == "__main__":
    unittest.main()
