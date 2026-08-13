from __future__ import annotations

import enum
import socket
import struct
import threading
from contextlib import suppress
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from .crypto import (
    HELLO_SIZE,
    PROOF_SIZE,
    AuthenticationError,
    derive_keys,
    make_hello,
    new_key_pair,
    parse_hello,
    proof,
    verify_proof,
)

HEADER = struct.Struct("!BBQI")
FRAME_VERSION = 1
TAG_SIZE = 16
MAX_WIRE_PAYLOAD = 8 * 1024 * 1024 + TAG_SIZE


class ProtocolError(RuntimeError):
    pass


class MessageType(enum.IntEnum):
    TEXT = 1
    AUDIO_OPUS = 2
    CLOSE = 3
    PING = 4


TYPE_LIMITS = {
    MessageType.TEXT: 8 * 1024,
    MessageType.AUDIO_OPUS: 8 * 1024 * 1024,
    MessageType.CLOSE: 256,
    MessageType.PING: 64,
}


@dataclass(frozen=True, slots=True)
class Message:
    kind: MessageType
    payload: bytes


def recv_exact(sock: socket.socket, amount: int) -> bytes:
    if amount < 0 or amount > MAX_WIRE_PAYLOAD:
        raise ProtocolError("Ungültige Paketgröße")
    chunks: list[bytes] = []
    remaining = amount
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise EOFError("Verbindung geschlossen")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def perform_client_handshake(sock: socket.socket, psk: bytes, timeout: float = 20.0) -> SecureChannel:
    previous_timeout = sock.gettimeout()
    sock.settimeout(timeout)
    try:
        pair = new_key_pair()
        client_hello = make_hello(1, pair.public_bytes)
        sock.sendall(client_hello)
        server_hello = recv_exact(sock, HELLO_SIZE)
        _, server_public = parse_hello(server_hello, 2)
        transcript = client_hello + server_hello
        server_proof = recv_exact(sock, PROOF_SIZE)
        verify_proof(psk, b"server-proof", transcript, server_proof)
        sock.sendall(proof(psk, b"client-proof", transcript))
        keys = derive_keys(pair.private, server_public, psk, transcript, client=True)
        return SecureChannel(sock, keys.send_key, keys.receive_key)
    except (OSError, EOFError, ValueError) as exc:
        raise AuthenticationError("Handshake fehlgeschlagen") from exc
    finally:
        sock.settimeout(previous_timeout)


def perform_server_handshake(sock: socket.socket, psk: bytes, timeout: float = 20.0) -> SecureChannel:
    previous_timeout = sock.gettimeout()
    sock.settimeout(timeout)
    try:
        client_hello = recv_exact(sock, HELLO_SIZE)
        _, client_public = parse_hello(client_hello, 1)
        pair = new_key_pair()
        server_hello = make_hello(2, pair.public_bytes)
        transcript = client_hello + server_hello
        sock.sendall(server_hello + proof(psk, b"server-proof", transcript))
        client_proof = recv_exact(sock, PROOF_SIZE)
        verify_proof(psk, b"client-proof", transcript, client_proof)
        keys = derive_keys(pair.private, client_public, psk, transcript, client=False)
        return SecureChannel(sock, keys.send_key, keys.receive_key)
    except (OSError, EOFError, ValueError) as exc:
        raise AuthenticationError("Handshake fehlgeschlagen") from exc
    finally:
        sock.settimeout(previous_timeout)


class SecureChannel:
    def __init__(self, sock: socket.socket, send_key: bytes, receive_key: bytes):
        self.sock = sock
        self._sender = ChaCha20Poly1305(send_key)
        self._receiver = ChaCha20Poly1305(receive_key)
        self._send_sequence = 0
        self._receive_sequence = 0
        self._send_lock = threading.Lock()

    @staticmethod
    def _nonce(sequence: int) -> bytes:
        return struct.pack("!IQ", 0, sequence)

    def send(self, kind: MessageType, payload: bytes = b"") -> None:
        try:
            limit = TYPE_LIMITS[kind]
        except KeyError as exc:
            raise ProtocolError("Unbekannter Nachrichtentyp") from exc
        if len(payload) > limit:
            raise ProtocolError(f"Nachricht überschreitet das Limit von {limit} Bytes")
        with self._send_lock:
            sequence = self._send_sequence
            ciphertext_size = len(payload) + TAG_SIZE
            header = HEADER.pack(FRAME_VERSION, int(kind), sequence, ciphertext_size)
            ciphertext = self._sender.encrypt(self._nonce(sequence), payload, header)
            self.sock.sendall(header + ciphertext)
            self._send_sequence += 1

    def receive(self) -> Message:
        header = recv_exact(self.sock, HEADER.size)
        version, raw_kind, sequence, ciphertext_size = HEADER.unpack(header)
        if version != FRAME_VERSION:
            raise ProtocolError("Nicht unterstützte Frame-Version")
        if sequence != self._receive_sequence:
            raise ProtocolError("Replay oder falsche Paketreihenfolge erkannt")
        if ciphertext_size < TAG_SIZE or ciphertext_size > MAX_WIRE_PAYLOAD:
            raise ProtocolError("Ungültige Paketgröße")
        try:
            kind = MessageType(raw_kind)
        except ValueError as exc:
            raise ProtocolError("Unbekannter Nachrichtentyp") from exc
        expected_limit = TYPE_LIMITS[kind] + TAG_SIZE
        if ciphertext_size > expected_limit:
            raise ProtocolError("Nachricht ist für diesen Typ zu groß")
        ciphertext = recv_exact(self.sock, ciphertext_size)
        try:
            payload = self._receiver.decrypt(self._nonce(sequence), ciphertext, header)
        except InvalidTag as exc:
            raise ProtocolError("Manipuliertes oder beschädigtes Paket") from exc
        self._receive_sequence += 1
        return Message(kind, payload)

    def close(self) -> None:
        with suppress(OSError):
            self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
