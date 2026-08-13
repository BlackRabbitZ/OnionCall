from __future__ import annotations

import os
import re
import shutil
import socket
import struct
import subprocess
import time
from pathlib import Path

from .config import Config, app_home, ensure_private_dir

ONION_RE = re.compile(r"^[a-z2-7]{56}\.onion$")


class TorError(RuntimeError):
    pass


def validate_onion(address: str) -> str:
    address = address.strip().lower()
    if address.startswith("onioncall:v2:"):
        raise TorError(
            "Das ist ein Verbindungsschlüssel, keine Onion-Adresse. "
            "Zum Anrufen die beim Empfänger angezeigte Adresse mit `.onion` verwenden."
        )
    address = address.removeprefix("http://").removeprefix("https://")
    address = address.rstrip("/")
    if not ONION_RE.fullmatch(address):
        raise TorError("Erwartet wird eine gültige Onion-v3-Adresse mit 56 Zeichen")
    return address


class TorProcess:
    def __init__(self, config: Config, home: Path | None = None):
        self.config = config
        self.home = home or app_home()
        self.tor_dir = self.home / "tor"
        self.data_dir = self.tor_dir / "data"
        self.hidden_dir = self.tor_dir / "onion_service"
        self.torrc = self.tor_dir / "torrc"
        self.log_path = self.tor_dir / "tor.log"
        self.process: subprocess.Popen[bytes] | None = None
        self._log_handle = None

    def _write_torrc(self) -> None:
        for directory in (self.home, self.tor_dir, self.data_dir, self.hidden_dir):
            ensure_private_dir(directory)
        content = (
            f"DataDirectory {self.data_dir}\n"
            f"SocksPort 127.0.0.1:{self.config.socks_port}\n"
            f"HiddenServiceDir {self.hidden_dir}\n"
            "HiddenServiceVersion 3\n"
            f"HiddenServicePort {self.config.listen_port} 127.0.0.1:{self.config.listen_port}\n"
            f"Log notice file {self.log_path}\n"
            "SafeLogging 1\n"
        )
        fd = os.open(self.torrc, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.chmod(self.torrc, 0o600)

    def start(self, timeout: float = 180.0) -> str:
        binary = shutil.which(self.config.tor_binary)
        if not binary:
            raise TorError("Tor wurde nicht gefunden; `onioncall doctor` ausführen")
        self._write_torrc()
        log_fd = os.open(self.log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        self._log_handle = os.fdopen(log_fd, "ab", buffering=0)
        os.chmod(self.log_path, 0o600)
        self.process = subprocess.Popen(
            [binary, "-f", str(self.torrc)],
            stdin=subprocess.DEVNULL,
            stdout=self._log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        hostname = self.hidden_dir / "hostname"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise TorError(f"Tor wurde unerwartet beendet; Logdatei: {self.log_path}")
            if hostname.exists() and self._socks_ready():
                address = hostname.read_text(encoding="ascii").strip()
                return validate_onion(address)
            time.sleep(0.25)
        self.stop()
        raise TorError(f"Tor war nach {int(timeout)} Sekunden nicht bereit; Logdatei: {self.log_path}")

    def _socks_ready(self) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", self.config.socks_port), timeout=0.2):
                return True
        except OSError:
            return False

    def stop(self) -> None:
        process = self.process
        self.process = None
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        if self._log_handle is not None:
            self._log_handle.close()
            self._log_handle = None

    def __enter__(self) -> TorProcess:
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()


def socks5_connect(host: str, port: int, socks_port: int, timeout: float = 60.0) -> socket.socket:
    host = validate_onion(host)
    encoded_host = host.encode("ascii")
    sock = socket.create_connection(("127.0.0.1", socks_port), timeout=timeout)
    try:
        sock.sendall(b"\x05\x01\x00")
        if _recv_exact(sock, 2) != b"\x05\x00":
            raise TorError("Der Tor-SOCKS-Proxy akzeptiert keine anonyme Verbindung")
        request = b"\x05\x01\x00\x03" + bytes((len(encoded_host),)) + encoded_host + struct.pack("!H", port)
        sock.sendall(request)
        head = _recv_exact(sock, 4)
        if head[0] != 5 or head[1] != 0:
            raise TorError(f"Tor konnte die Onion-Adresse nicht verbinden (SOCKS-Code {head[1]})")
        address_type = head[3]
        if address_type == 1:
            _recv_exact(sock, 4)
        elif address_type == 3:
            _recv_exact(sock, _recv_exact(sock, 1)[0])
        elif address_type == 4:
            _recv_exact(sock, 16)
        else:
            raise TorError("Ungültige SOCKS-Antwort")
        _recv_exact(sock, 2)
        sock.settimeout(None)
        return sock
    except BaseException:
        sock.close()
        raise


def _recv_exact(sock: socket.socket, amount: int) -> bytes:
    result = bytearray()
    while len(result) < amount:
        chunk = sock.recv(amount - len(result))
        if not chunk:
            raise TorError("Tor-SOCKS-Verbindung wurde geschlossen")
        result.extend(chunk)
    return bytes(result)
