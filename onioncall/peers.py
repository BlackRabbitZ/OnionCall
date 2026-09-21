from __future__ import annotations

import base64
import json
import re
import secrets
from dataclasses import dataclass
from pathlib import Path

from .config import (
    ConfigError,
    app_home,
    atomic_private_write,
    ensure_private_dir,
    load_secret,
    parse_secret,
    secret_token,
)

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
FINGERPRINT_RE = re.compile(r"^BRZ-(?:[0-9A-F]{4}-){7}[0-9A-F]{4}$")


@dataclass(slots=True)
class PeerProfile:
    name: str
    key: bytes
    onion: str | None = None
    fingerprint: str | None = None


def peers_dir(home: Path | None = None) -> Path:
    path = (home or app_home()) / "peers"
    ensure_private_dir(path)
    return path


def _validate_name(name: str) -> str:
    name = name.strip()
    if not NAME_RE.fullmatch(name):
        raise ConfigError("Kontaktname darf nur Buchstaben, Zahlen, Punkt, Unterstrich und Bindestrich enthalten")
    return name


def _meta_path(name: str, home: Path | None = None) -> Path:
    return peers_dir(home) / f"{_validate_name(name)}.json"


def _key_path(name: str, home: Path | None = None) -> Path:
    return peers_dir(home) / f"{_validate_name(name)}.key"


def list_peers(home: Path | None = None) -> list[str]:
    names = {p.stem for p in peers_dir(home).glob("*.key")}
    try:
        load_secret(home)
        names.add("default")
    except ConfigError:
        pass
    return sorted(names)


def create_peer(name: str, *, onion: str | None = None, key: bytes | None = None, home: Path | None = None) -> PeerProfile:
    name = _validate_name(name)
    if name == "default":
        raise ConfigError("`default` ist für den bisherigen Hauptschlüssel reserviert")
    key_path = _key_path(name, home)
    if key_path.exists():
        raise ConfigError(f"Kontakt existiert bereits: {name}")
    key = key or secrets.token_bytes(32)
    if len(key) != 32:
        raise ConfigError("Kontakt-Schlüssel muss 256 Bit lang sein")
    atomic_private_write(key_path, base64.urlsafe_b64encode(key) + b"\n")
    profile = PeerProfile(name=name, key=key, onion=onion)
    _save_meta(profile, home)
    return profile


def import_peer_secret(name: str, token: str, *, home: Path | None = None) -> PeerProfile:
    key = parse_secret(token)
    if name == "default":
        from .config import import_secret

        import_secret(token, home, replace=True)
        return load_peer(name, home)
    path = _key_path(name, home)
    if not path.exists():
        atomic_private_write(path, base64.urlsafe_b64encode(key) + b"\n")
        profile = PeerProfile(name=_validate_name(name), key=key)
        _save_meta(profile, home)
        return profile
    atomic_private_write(path, base64.urlsafe_b64encode(key) + b"\n")
    profile = load_peer(name, home)
    profile.key = key
    return profile


def load_peer(name: str = "default", home: Path | None = None) -> PeerProfile:
    name = _validate_name(name)
    if name == "default":
        key = load_secret(home)
        meta_path = _meta_path(name, home)
    else:
        path = _key_path(name, home)
        if not path.exists():
            raise ConfigError(f"Unbekannter Kontakt: {name}")
        try:
            key = base64.urlsafe_b64decode(path.read_text(encoding="ascii").strip().encode("ascii"))
        except (OSError, ValueError) as exc:
            raise ConfigError(f"Ungültiger Kontakt-Schlüssel für {name}") from exc
        if len(key) != 32:
            raise ConfigError(f"Ungültiger Kontakt-Schlüssel für {name}")
        meta_path = _meta_path(name, home)
    onion = None
    pinned = None
    if meta_path.exists():
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            onion = data.get("onion") or None
            pinned = data.get("fingerprint") or None
        except (OSError, ValueError, TypeError) as exc:
            raise ConfigError(f"Ungültige Kontakt-Metadaten für {name}") from exc
    if pinned is not None and not FINGERPRINT_RE.fullmatch(str(pinned)):
        raise ConfigError(f"Ungültiger gespeicherter Fingerprint für {name}")
    return PeerProfile(name=name, key=key, onion=onion, fingerprint=pinned)


def pin_peer_fingerprint(profile: PeerProfile, fingerprint: str, home: Path | None = None) -> None:
    if not FINGERPRINT_RE.fullmatch(fingerprint):
        raise ConfigError("Ungültiger Fingerprint")
    if profile.fingerprint and profile.fingerprint != fingerprint:
        raise ConfigError(
            f"Identitätswarnung für {profile.name}: gespeicherter Fingerprint stimmt nicht mit der Gegenstelle überein"
        )
    if profile.fingerprint == fingerprint:
        return
    profile.fingerprint = fingerprint
    _save_meta(profile, home)


def set_peer_onion(profile: PeerProfile, onion: str | None, home: Path | None = None) -> None:
    profile.onion = onion
    _save_meta(profile, home)


def peer_secret_token(profile: PeerProfile) -> str:
    return secret_token(profile.key)


def _save_meta(profile: PeerProfile, home: Path | None = None) -> None:
    payload = json.dumps(
        {"name": profile.name, "onion": profile.onion, "fingerprint": profile.fingerprint},
        indent=2,
        sort_keys=True,
    ).encode() + b"\n"
    atomic_private_write(_meta_path(profile.name, home), payload)
