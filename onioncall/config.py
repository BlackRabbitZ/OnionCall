from __future__ import annotations

import base64
import json
import os
import secrets
import stat
import tempfile
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path

from .validation import validate_onion_v3

DPAPI_MAGIC = b"ONIONCALL-DPAPI-V1\n"
TOKEN_PREFIX = "onioncall:v2:"


class ConfigError(RuntimeError):
    pass


def app_home() -> Path:
    override = os.environ.get("ONIONCALL_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".config" / "onioncall"


def ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    with suppress(OSError):
        os.chmod(path, 0o700)


def check_private_file(path: Path) -> None:
    """Reject symlinks/non-files and unsafe POSIX permissions for private material."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        raise
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ConfigError(f"Unsichere private Datei: {path}")
    if os.name != "nt":
        mode = stat.S_IMODE(info.st_mode)
        if mode & 0o077:
            raise ConfigError(f"Unsichere Rechte für {path}: {mode:o}; erwartet höchstens 600")


def atomic_private_write(path: Path, data: bytes) -> None:
    ensure_private_dir(path.parent)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with suppress(OSError):
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        with suppress(OSError):
            os.chmod(path, 0o600)
    except BaseException:
        with suppress(FileNotFoundError):
            os.unlink(tmp_name)
        raise


def _dpapi_transform(data: bytes, *, protect: bool) -> bytes:
    if os.name != "nt":
        raise ConfigError("DPAPI ist nur unter Windows verfügbar")
    import ctypes
    from ctypes import wintypes

    class DataBlob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.c_void_p)]

    source_buffer = ctypes.create_string_buffer(data, max(1, len(data)))
    source = DataBlob(len(data), ctypes.cast(source_buffer, ctypes.c_void_p))
    result = DataBlob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(DataBlob),
        wintypes.LPCWSTR,
        ctypes.POINTER(DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(DataBlob),
    ]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(DataBlob),
        ctypes.c_void_p,
        ctypes.POINTER(DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(DataBlob),
    ]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    flags = 0x1  # CRYPTPROTECT_UI_FORBIDDEN

    if protect:
        func = crypt32.CryptProtectData
        ok = func(
            ctypes.byref(source),
            "OnionCall private material",
            None,
            None,
            None,
            flags,
            ctypes.byref(result),
        )
    else:
        func = crypt32.CryptUnprotectData
        ok = func(
            ctypes.byref(source),
            None,
            None,
            None,
            None,
            flags,
            ctypes.byref(result),
        )
    if not ok:
        error = ctypes.get_last_error()
        raise ConfigError(f"Windows-DPAPI fehlgeschlagen (Fehler {error})")
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        if result.pbData:
            kernel32.LocalFree(result.pbData)


def atomic_secret_write(path: Path, plaintext: bytes) -> None:
    """Persist private app material; Windows uses per-user DPAPI encryption."""
    data = plaintext
    if os.name == "nt":
        encrypted = _dpapi_transform(plaintext, protect=True)
        data = DPAPI_MAGIC + base64.b64encode(encrypted) + b"\n"
    atomic_private_write(path, data)


def read_secret_file(path: Path, *, migrate_windows: bool = True) -> bytes:
    check_private_file(path)
    raw = path.read_bytes()
    if raw.startswith(DPAPI_MAGIC):
        if os.name != "nt":
            raise ConfigError(f"{path} ist mit Windows-DPAPI geschützt und auf diesem System nicht lesbar")
        try:
            encrypted = base64.b64decode(raw[len(DPAPI_MAGIC) :].strip(), validate=True)
        except ValueError as exc:
            raise ConfigError(f"Beschädigter DPAPI-Datensatz: {path}") from exc
        return _dpapi_transform(encrypted, protect=False)
    if os.name == "nt" and migrate_windows:
        # Transparente Migration bestehender OnionCall-Klartext-Schlüssel in den DPAPI-Speicher.
        atomic_secret_write(path, raw)
    return raw


@dataclass(slots=True)
class Config:
    listen_port: int = 17777
    socks_port: int = 19050
    tor_binary: str = "tor"
    max_audio_seconds: int = 120
    last_address: str | None = None
    temporary_onion: bool = False

    def validate(self) -> None:
        for name, value in (("listen_port", self.listen_port), ("socks_port", self.socks_port)):
            if not isinstance(value, int) or not 1024 <= value <= 65535:
                raise ConfigError(f"{name} muss zwischen 1024 und 65535 liegen")
        if self.listen_port == self.socks_port:
            raise ConfigError("Listen- und SOCKS-Port müssen verschieden sein")
        if not 1 <= self.max_audio_seconds <= 300:
            raise ConfigError("max_audio_seconds muss zwischen 1 und 300 liegen")
        if self.last_address is not None:
            if not isinstance(self.last_address, str):
                raise ConfigError("last_address muss eine gültige Onion-v3-Adresse sein")
            try:
                validate_onion_v3(self.last_address)
            except ValueError as exc:
                raise ConfigError("last_address muss eine gültige Onion-v3-Adresse sein") from exc
        if not isinstance(self.temporary_onion, bool):
            raise ConfigError("temporary_onion muss true oder false sein")


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
    atomic_secret_write(path, base64.urlsafe_b64encode(key) + b"\n")
    return key


def _weak_secret_reason(key: bytes) -> str | None:
    # Diese Prüfungen erkennen offensichtliche manuell konstruierte Schlüssel. Sie können
    # nicht beweisen, dass ein äußerlich zufällig wirkender 32-Byte-Wert echte Entropie hat.
    if len(set(key)) < 8:
        return "zu wenige unterschiedliche Bytewerte"
    if all(32 <= value <= 126 for value in key):
        return "Schlüssel besteht vollständig aus druckbarem Text"
    for size in (1, 2, 4, 8, 16):
        if key == key[:size] * (32 // size):
            return "wiederholtes Byte-Muster"
    return None


def parse_secret(value: str, *, require_token: bool = False) -> bytes:
    value = value.strip()
    if value.lower().endswith(".onion"):
        raise ConfigError(
            "Das ist eine Onion-Adresse, kein Verbindungsschlüssel. "
            "Hier die mit `onioncall:v2:` beginnende Schlüsselzeile einfügen."
        )
    has_prefix = value.startswith(TOKEN_PREFIX)
    if require_token and not has_prefix:
        raise ConfigError("Nur vollständige, von OnionCall erzeugte `onioncall:v2:`-Tokens dürfen importiert werden")
    if has_prefix:
        value = value.removeprefix(TOKEN_PREFIX)
    try:
        key = base64.b64decode(value.encode("ascii"), altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise ConfigError("Der Verbindungsschlüssel ist kein gültiges Base64") from exc
    if len(key) != 32:
        raise ConfigError("Der Verbindungsschlüssel muss genau 256 Bit lang sein")
    if require_token:
        weak = _weak_secret_reason(key)
        if weak:
            raise ConfigError(
                f"Der importierte Verbindungsschlüssel wirkt unsicher ({weak}); "
                "neuen OnionCall-Key erzeugen"
            )
    return key


def import_secret(value: str, home: Path | None = None, *, replace: bool = False) -> bytes:
    path = secret_path(home)
    if path.exists() and not replace:
        raise ConfigError(f"Schlüssel existiert bereits: {path}; --replace verwenden")
    key = parse_secret(value, require_token=True)
    atomic_secret_write(path, base64.urlsafe_b64encode(key) + b"\n")
    return key


def load_secret(home: Path | None = None) -> bytes:
    path = secret_path(home)
    try:
        raw = read_secret_file(path)
        return parse_secret(raw.decode("ascii"))
    except FileNotFoundError as exc:
        raise ConfigError("Kein Verbindungsschlüssel vorhanden; zuerst `onioncall init` ausführen") from exc
    except UnicodeDecodeError as exc:
        raise ConfigError(f"Ungültiger Verbindungsschlüssel in {path}") from exc


def secret_token(key: bytes) -> str:
    if len(key) != 32:
        raise ConfigError("Ungültige Schlüssellänge")
    return TOKEN_PREFIX + base64.urlsafe_b64encode(key).decode("ascii")
