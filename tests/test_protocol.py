from __future__ import annotations

import socket
import tempfile
import threading
import unittest
from pathlib import Path

from onioncall.identity import load_or_create_identity
from onioncall.protocol import MessageType, ProtocolError, perform_client_handshake, perform_server_handshake


class ProtocolTests(unittest.TestCase):
    def test_authenticated_roundtrip_and_identity(self) -> None:
        psk = b"K" * 32
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            server_identity = load_or_create_identity(root / "server")
            client_identity = load_or_create_identity(root / "client")
            left, right = socket.socketpair()
            result = []
            def server():
                result.append(perform_server_handshake(left, psk, server_identity, timeout=2))
            thread = threading.Thread(target=server); thread.start()
            client = perform_client_handshake(right, psk, client_identity, timeout=2)
            thread.join(timeout=2); server_channel = result[0]
            client.send(MessageType.TEXT, b"hallo")
            msg = server_channel.receive()
            self.assertEqual(msg.kind, MessageType.TEXT); self.assertEqual(msg.payload, b"hallo")
            server_channel.send(MessageType.PING, b"x")
            self.assertEqual(client.receive().payload, b"x")
            client.close(); server_channel.close()

    def test_wrong_psk_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); server_id=load_or_create_identity(root/'s'); client_id=load_or_create_identity(root/'c')
            left,right=socket.socketpair(); errors=[]
            def server():
                try: perform_server_handshake(left,b"A"*32,server_id,timeout=1)
                except BaseException as exc: errors.append(exc)
            t=threading.Thread(target=server); t.start()
            with self.assertRaises(Exception): perform_client_handshake(right,b"B"*32,client_id,timeout=1)
            t.join(timeout=2); left.close(); right.close(); self.assertTrue(errors)

    def test_frame_type_limit(self) -> None:
        # A secure channel rejects oversized plaintext before sending it.
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); s=load_or_create_identity(root/'s'); c=load_or_create_identity(root/'c'); left,right=socket.socketpair(); out=[]
            t=threading.Thread(target=lambda: out.append(perform_server_handshake(left,b"P"*32,s,timeout=2))); t.start()
            ch=perform_client_handshake(right,b"P"*32,c,timeout=2); t.join(timeout=2)
            with self.assertRaises(ProtocolError): ch.send(MessageType.TEXT,b"x"*(8192+1))
            ch.close(); out[0].close()


if __name__ == "__main__": unittest.main()
