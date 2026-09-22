from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .config import app_home, atomic_secret_write, ConfigError, read_secret_file

@dataclass(frozen=True, slots=True)
class LocalIdentity:
    private: Ed25519PrivateKey
    public_bytes: bytes

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.public_bytes)


def identity_path(home: Path | None = None) -> Path:
    return (home or app_home()) / "identity.key"


def _private_bytes(key: Ed25519PrivateKey) -> bytes:
    return key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _public_bytes(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def load_or_create_identity(home: Path | None = None) -> LocalIdentity:
    path = identity_path(home)
    if path.exists():
        try:
            encoded = read_secret_file(path).decode("ascii").strip().encode("ascii")
            raw = base64.urlsafe_b64decode(encoded)
        except (ConfigError, OSError, UnicodeError, ValueError) as exc:
            raise RuntimeError("Ungültiger lokaler Identitätsschlüssel") from exc
        if len(raw) != 32:
            raise RuntimeError("Ungültiger lokaler Identitätsschlüssel")
        private = Ed25519PrivateKey.from_private_bytes(raw)
    else:
        private = Ed25519PrivateKey.generate()
        atomic_secret_write(path, base64.urlsafe_b64encode(_private_bytes(private)) + b"\n")
    return LocalIdentity(private=private, public_bytes=_public_bytes(private))


def fingerprint(public_bytes: bytes) -> str:
    if len(public_bytes) != 32:
        raise ValueError("Ungültiger Ed25519-Schlüssel")
    digest = hashlib.sha256(public_bytes).hexdigest().upper()
    groups = [digest[i : i + 4] for i in range(0, 32, 4)]
    return "BRZ-" + "-".join(groups)


def verify_signature(public_bytes: bytes, signature: bytes, data: bytes) -> None:
    Ed25519PublicKey.from_public_bytes(public_bytes).verify(signature, data)
