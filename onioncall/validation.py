from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import re

ONION_V3_RE = re.compile(r"^[a-z2-7]{56}\.onion$")
ONION_CHECKSUM_PREFIX = b".onion checksum"


def validate_onion_v3(value: str, *, allow_url: bool = False) -> str:
    """Return a canonical Onion v3 hostname after checking checksum and version."""
    address = value.strip().lower()
    if allow_url:
        address = address.removeprefix("http://").removeprefix("https://").rstrip("/")
    if not ONION_V3_RE.fullmatch(address):
        raise ValueError("Erwartet wird eine gültige Onion-v3-Adresse mit 56 Zeichen")

    try:
        decoded = base64.b32decode(address[:-6].upper().encode("ascii"), casefold=False)
    except (ValueError, UnicodeEncodeError) as exc:
        raise ValueError("Ungültige Onion-v3-Base32-Kodierung") from exc
    if len(decoded) != 35:
        raise ValueError("Ungültige Onion-v3-Länge")

    public_key = decoded[:32]
    checksum = decoded[32:34]
    version = decoded[34]
    if version != 3:
        raise ValueError("Nicht unterstützte Onion-Service-Version")
    expected = hashlib.sha3_256(ONION_CHECKSUM_PREFIX + public_key + bytes((version,))).digest()[:2]
    if not hmac.compare_digest(checksum, expected):
        raise ValueError("Ungültige Onion-v3-Prüfsumme")
    return address


def validate_exact_loopback(value: str) -> str:
    """Accept exactly the two loopback literals documented for OnionCall."""
    try:
        address = ipaddress.ip_address(value.strip())
    except ValueError as exc:
        raise ValueError("Erlaubt sind ausschließlich 127.0.0.1 oder ::1") from exc
    canonical = str(address)
    if canonical not in {"127.0.0.1", "::1"}:
        raise ValueError("Erlaubt sind ausschließlich 127.0.0.1 oder ::1")
    return canonical
