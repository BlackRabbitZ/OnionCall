from __future__ import annotations

import base64
import re
from contextlib import suppress
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from .config import ConfigError, app_home, atomic_private_write, ensure_private_dir

AUTH_TOKEN_PREFIX = "onioncall:tor-auth:v1:"
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
ONION_RE = re.compile(r"^[a-z2-7]{56}\.onion$")
B32_RE = re.compile(r"^[A-Z2-7]{52}$")


def _safe_name(name: str) -> str:
    name = name.strip()
    if not NAME_RE.fullmatch(name):
        raise ConfigError("Name darf nur Buchstaben, Zahlen, Punkt, Unterstrich und Bindestrich enthalten")
    return name


def _b32(raw: bytes) -> str:
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _decode_b32(value: str) -> bytes:
    value = value.strip().upper()
    if not B32_RE.fullmatch(value):
        raise ConfigError("Ungültiger Tor-Client-Authorization-Schlüssel")
    try:
        raw = base64.b32decode(value + "=" * ((8 - len(value) % 8) % 8), casefold=False)
    except ValueError as exc:
        raise ConfigError("Ungültiger Tor-Client-Authorization-Schlüssel") from exc
    if len(raw) != 32:
        raise ConfigError("Tor-Client-Authorization-Schlüssel muss 32 Byte lang sein")
    return raw


def tor_auth_root(home: Path | None = None) -> Path:
    path = (home or app_home()) / "tor_auth"
    ensure_private_dir(path)
    return path


def server_auth_dir(home: Path | None = None) -> Path:
    path = tor_auth_root(home) / "server"
    ensure_private_dir(path)
    return path


def client_auth_dir(home: Path | None = None) -> Path:
    path = tor_auth_root(home) / "client"
    ensure_private_dir(path)
    return path


def generate_authorized_client(name: str, home: Path | None = None, *, replace: bool = False) -> str:
    name = _safe_name(name)
    path = server_auth_dir(home) / f"{name}.auth"
    if path.exists() and not replace:
        raise ConfigError(f"Tor-Autorisierung existiert bereits: {name}")
    private = X25519PrivateKey.generate()
    private_raw = private.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    public_raw = private.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    atomic_private_write(path, f"descriptor:x25519:{_b32(public_raw)}\n".encode("ascii"))
    return AUTH_TOKEN_PREFIX + _b32(private_raw)


def parse_private_token(token: str) -> str:
    token = token.strip()
    if token.startswith(AUTH_TOKEN_PREFIX):
        token = token[len(AUTH_TOKEN_PREFIX):]
    _decode_b32(token)
    return token.upper()


def import_client_authorization(
    onion: str,
    token: str,
    *,
    name: str = "service",
    home: Path | None = None,
    replace: bool = True,
) -> Path:
    onion = onion.strip().lower()
    if not ONION_RE.fullmatch(onion):
        raise ConfigError("Ungültige Onion-v3-Adresse für Tor Client Authorization")
    name = _safe_name(name)
    private_b32 = parse_private_token(token)
    path = client_auth_dir(home) / f"{name}.auth_private"
    if path.exists() and not replace:
        raise ConfigError(f"Private Tor-Autorisierung existiert bereits: {name}")
    content = f"{onion[:-6]}:descriptor:x25519:{private_b32}\n".encode("ascii")
    atomic_private_write(path, content)
    return path


def list_server_authorizations(home: Path | None = None) -> list[str]:
    return sorted(path.stem for path in server_auth_dir(home).glob("*.auth") if path.is_file())


def list_client_authorizations(home: Path | None = None) -> list[str]:
    return sorted(path.name.removesuffix(".auth_private") for path in client_auth_dir(home).glob("*.auth_private"))


def revoke_server_authorization(name: str, home: Path | None = None) -> bool:
    path = server_auth_dir(home) / f"{_safe_name(name)}.auth"
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False


def remove_client_authorization(name: str, home: Path | None = None) -> bool:
    path = client_auth_dir(home) / f"{_safe_name(name)}.auth_private"
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False


def prepare_service_authorizations(hidden_dir: Path, home: Path | None = None) -> int:
    source = server_auth_dir(home)
    target = hidden_dir / "authorized_clients"
    existing = list(target.glob("*.auth")) if target.exists() else []
    for stale in existing:
        with suppress(OSError):
            stale.unlink()
    files = sorted(source.glob("*.auth"))
    if not files:
        with suppress(OSError):
            target.rmdir()
        return 0
    ensure_private_dir(target)
    for src in files:
        atomic_private_write(target / src.name, src.read_bytes())
    return len(files)


def client_authorization_available(home: Path | None = None) -> bool:
    return any(client_auth_dir(home).glob("*.auth_private"))
