from __future__ import annotations

import base64
import json
import os
import re
import secrets
import stat
import tempfile
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path


class ConfigError(RuntimeError):
    pass


def app_home() -> Path:
    override = os.environ.get("ONIONCALL_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".config" / "onioncall"


def ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)


def atomic_private_write(path: Path, data: bytes) -> None:
    ensure_private_dir(path.parent)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        os.chmod(path, 0o600)
    except BaseException:
        with suppress(FileNotFoundError):
            os.unlink(tmp_name)
        raise


@dataclass(slots=True)
class Config:
    listen_port: int = 17777
    socks_port: int = 19050
    tor_binary: str = "tor"
    max_audio_seconds: int = 120
    last_address: str | None = None

    def validate(self) -> None:
        for name, value in (("listen_port", self.listen_port), ("socks_port", self.socks_port)):
            if not isinstance(value, int) or not 1024 <= value <= 65535:
                raise ConfigError(f"{name} muss zwischen 1024 und 65535 liegen")
        if self.listen_port == self.socks_port:
            raise ConfigError("Listen- und SOCKS-Port müssen verschieden sein")
        if not 1 <= self.max_audio_seconds <= 300:
            raise ConfigError("max_audio_seconds muss zwischen 1 und 300 liegen")
        if self.last_address is not None and (
            not isinstance(self.last_address, str) or not re.fullmatch(r"[a-z2-7]{56}\.onion", self.last_address)
        ):
            raise ConfigError("last_address muss eine gültige Onion-v3-Adresse sein")


def config_path(home: Path | None = None) -> Path:
    return (home or app_home()) / "config.json"


def secret_path(home: Path | None = None) -> Path:
    return (home or app_home()) / "conversation.key"


def load_config(home: Path | None = None) -> Config:
    path = config_path(home)
    if not path.exists():
        return Config()
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
        config = Config(**values)
        config.validate()
        return config
    except (OSError, ValueError, TypeError) as exc:
        raise ConfigError(f"Ungültige Konfiguration {path}: {exc}") from exc


def save_config(config: Config, home: Path | None = None) -> None:
    config.validate()
    payload = json.dumps(asdict(config), indent=2, sort_keys=True).encode() + b"\n"
    atomic_private_write(config_path(home), payload)


def generate_secret(home: Path | None = None, *, replace: bool = False) -> bytes:
    path = secret_path(home)
    if path.exists() and not replace:
        raise ConfigError(f"Schlüssel existiert bereits: {path}")
    key = secrets.token_bytes(32)
    atomic_private_write(path, base64.urlsafe_b64encode(key) + b"\n")
    return key


def parse_secret(value: str) -> bytes:
    value = value.strip()
    if value.lower().endswith(".onion"):
        raise ConfigError(
            "Das ist eine Onion-Adresse, kein Verbindungsschlüssel. "
            "Hier die mit `onioncall:v2:` beginnende Schlüsselzeile einfügen."
        )
    if value.startswith("onioncall:v2:"):
        value = value.removeprefix("onioncall:v2:")
    try:
        key = base64.b64decode(value.encode("ascii"), altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise ConfigError("Der Verbindungsschlüssel ist kein gültiges Base64") from exc
    if len(key) != 32:
        raise ConfigError("Der Verbindungsschlüssel muss genau 256 Bit lang sein")
    return key


def import_secret(value: str, home: Path | None = None, *, replace: bool = False) -> bytes:
    path = secret_path(home)
    if path.exists() and not replace:
        raise ConfigError(f"Schlüssel existiert bereits: {path}; --replace verwenden")
    key = parse_secret(value)
    atomic_private_write(path, base64.urlsafe_b64encode(key) + b"\n")
    return key


def load_secret(home: Path | None = None) -> bytes:
    path = secret_path(home)
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & 0o077:
            raise ConfigError(f"Unsichere Rechte für {path}: {mode:o}; erwartet 600")
        return parse_secret(path.read_text(encoding="ascii"))
    except FileNotFoundError as exc:
        raise ConfigError("Kein Verbindungsschlüssel vorhanden; zuerst `onioncall init` ausführen") from exc


def secret_token(key: bytes) -> str:
    if len(key) != 32:
        raise ConfigError("Ungültige Schlüssellänge")
    return "onioncall:v2:" + base64.urlsafe_b64encode(key).decode("ascii")
