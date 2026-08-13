from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

PROTOCOL_MAGIC = b"OCH2"
PROTOCOL_VERSION = 2
HELLO_SIZE = 70
PROOF_SIZE = 32


class AuthenticationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class KeyPair:
    private: X25519PrivateKey
    public_bytes: bytes


@dataclass(frozen=True, slots=True)
class SessionKeys:
    send_key: bytes
    receive_key: bytes


def new_key_pair() -> KeyPair:
    private = X25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return KeyPair(private, public)


def make_hello(role: int, public_key: bytes, nonce: bytes | None = None) -> bytes:
    if role not in (1, 2) or len(public_key) != 32:
        raise ValueError("Ungültige Hello-Parameter")
    nonce = nonce or secrets.token_bytes(32)
    if len(nonce) != 32:
        raise ValueError("Ungültige Nonce")
    return PROTOCOL_MAGIC + bytes((PROTOCOL_VERSION, role)) + nonce + public_key


def parse_hello(data: bytes, expected_role: int) -> tuple[bytes, bytes]:
    if len(data) != HELLO_SIZE:
        raise AuthenticationError("Ungültiger Handshake")
    if data[:4] != PROTOCOL_MAGIC or data[4] != PROTOCOL_VERSION or data[5] != expected_role:
        raise AuthenticationError("Inkompatibles oder ungültiges Protokoll")
    return data[6:38], data[38:70]


def proof(psk: bytes, label: bytes, transcript: bytes) -> bytes:
    return hmac.new(psk, label + b"\x00" + transcript, hashlib.sha256).digest()


def verify_proof(psk: bytes, label: bytes, transcript: bytes, candidate: bytes) -> None:
    if not hmac.compare_digest(proof(psk, label, transcript), candidate):
        raise AuthenticationError("Authentifizierung fehlgeschlagen")


def derive_keys(
    private: X25519PrivateKey,
    peer_public: bytes,
    psk: bytes,
    transcript: bytes,
    *,
    client: bool,
) -> SessionKeys:
    if len(psk) != 32:
        raise AuthenticationError("Ungültiger Verbindungsschlüssel")
    try:
        shared = private.exchange(X25519PublicKey.from_public_bytes(peer_public))
    except ValueError as exc:
        raise AuthenticationError("Ungültiger öffentlicher Schlüssel") from exc
    salt = hashlib.sha256(transcript).digest()
    material = HKDF(
        algorithm=hashes.SHA256(),
        length=64,
        salt=salt,
        info=b"OnionCall-v2/session-keys",
    ).derive(shared + psk)
    client_to_server, server_to_client = material[:32], material[32:]
    if client:
        return SessionKeys(client_to_server, server_to_client)
    return SessionKeys(server_to_client, client_to_server)
