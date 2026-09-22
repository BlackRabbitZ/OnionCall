from __future__ import annotations

import os
import re
import shutil
import socket
import struct
import subprocess
import time
from contextlib import suppress
from pathlib import Path

from .client_auth import client_auth_dir, client_authorization_available, prepare_service_authorizations
from .config import Config, app_home, ensure_private_dir
from .validation import validate_exact_loopback, validate_onion_v3


class TorError(RuntimeError):
    pass


def validate_onion(address: str) -> str:
    address = address.strip().lower()
    if address.startswith("onioncall:v2:"):
        raise TorError(
            "Das ist ein Verbindungsschlüssel, keine Onion-Adresse. "
            "Zum Anrufen die beim Empfänger angezeigte Adresse mit `.onion` verwenden."
        )
    try:
        return validate_onion_v3(address, allow_url=True)
    except ValueError as exc:
        raise TorError(str(exc)) from exc


def validate_loopback_host(host: str) -> str:
    try:
        return validate_exact_loopback(host)
    except ValueError as exc:
        raise TorError(
            "Direktmodus akzeptiert ausschließlich die literalen Loopback-Adressen 127.0.0.1 oder ::1"
        ) from exc


def loopback_connect(host: str, port: int, timeout: float = 20.0) -> socket.socket:
    return socket.create_connection((validate_loopback_host(host), port), timeout=timeout)


class TorProcess:
    def __init__(
        self,
        config: Config,
        home: Path | None = None,
        *,
        service: bool = True,
        temporary_service: bool = False,
    ):
        self.config = config
        self.home = home or app_home()
        self.service = service
        self.temporary_service = temporary_service and service
        self.tor_dir = self.home / "tor"
        self.data_dir = self.tor_dir / ("data-service" if service else "data-client")
        suffix = f"onion_service_tmp_{os.getpid()}_{int(time.time() * 1000)}" if self.temporary_service else "onion_service"
        self.hidden_dir = self.tor_dir / suffix
        self.torrc = self.tor_dir / ("torrc-service" if service else "torrc-client")
        self.log_path = self.tor_dir / ("tor-service.log" if service else "tor-client.log")
        self.process: subprocess.Popen[bytes] | None = None
        self._log_handle = None
        self._stop_requested = False

    def _write_torrc(self) -> None:
        for directory in (self.home, self.tor_dir, self.data_dir):
            ensure_private_dir(directory)
        if self.service:
            ensure_private_dir(self.hidden_dir)
            prepare_service_authorizations(self.hidden_dir, self.home)
        lines = [
            f"DataDirectory {self.data_dir}",
            f"SocksPort 127.0.0.1:{self.config.socks_port}",
            "SafeSocks 1",
            "TestSocks 1",
            f"Log notice file {self.log_path}",
            "SafeLogging 1",
        ]
        if not self.service and client_authorization_available(self.home):
            lines.append(f"ClientOnionAuthDir {client_auth_dir(self.home)}")
        if self.service:
            lines.extend(
                [
                    f"HiddenServiceDir {self.hidden_dir}",
                    "HiddenServiceVersion 3",
                    f"HiddenServicePort {self.config.listen_port} 127.0.0.1:{self.config.listen_port}",
                ]
            )
        content = "\n".join(lines) + "\n"
        fd = os.open(self.torrc, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        with suppress(OSError):
            os.chmod(self.torrc, 0o600)

    def start(self, timeout: float = 180.0) -> str | None:
        self._stop_requested = False
        binary = shutil.which(self.config.tor_binary)
        if not binary:
            raise TorError("Tor wurde nicht gefunden; `onioncall doctor` ausführen")
        self._ensure_socks_port_available()
        self._write_torrc()
        log_fd = os.open(self.log_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        self._log_handle = os.fdopen(log_fd, "ab", buffering=0)
        with suppress(OSError):
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
            if self._stop_requested:
                raise TorError("Tor-Start wurde abgebrochen")
            if self.process.poll() is not None:
                raise TorError(self._unexpected_exit_message())
            service_ready = not self.service or hostname.exists()
            if service_ready and self._socks_ready() and self._bootstrap_complete():
                if not self.service:
                    return None
                return validate_onion(hostname.read_text(encoding="ascii").strip())
            time.sleep(0.25)
        self.stop()
        raise TorError(f"Tor war nach {int(timeout)} Sekunden nicht bereit; Logdatei: {self.log_path}")

    def _bootstrap_complete(self) -> bool:
        try:
            return "Bootstrapped 100%" in self.log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False

    def _socks_ready(self) -> bool:
        try:
            with loopback_connect("127.0.0.1", self.config.socks_port, timeout=0.2):
                return True
        except OSError:
            return False

    def _ensure_socks_port_available(self) -> None:
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", self.config.socks_port))
        except OSError as exc:
            raise TorError(
                f"Tor-SOCKS-Port {self.config.socks_port} ist bereits belegt. "
                "Beende eine andere OnionCall-/Tor-Instanz oder ändere den SOCKS-Port."
            ) from exc
        finally:
            probe.close()

    def _unexpected_exit_message(self) -> str:
        try:
            lines = self.log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            lines = []
        markers = ("[warn]", "[err]", "failed", "error", "problem", "in use", "permission")
        relevant = [line.strip() for line in lines if any(marker in line.lower() for marker in markers)]
        detail = " | ".join(relevant[-3:])
        detail = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", detail)[:700]
        message = "Tor wurde unerwartet beendet"
        if detail:
            message += f". Ursache laut Tor: {detail}"
        return f"{message}; Logdatei: {self.log_path}"

    def stop(self) -> None:
        self._stop_requested = True
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
        if self.temporary_service:
            shutil.rmtree(self.hidden_dir, ignore_errors=True)

    def __enter__(self) -> "TorProcess":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()


def socks5_connect(host: str, port: int, socks_port: int, timeout: float = 60.0) -> socket.socket:
    host = validate_onion(host)
    encoded_host = host.encode("ascii")
    sock = loopback_connect("127.0.0.1", socks_port, timeout=timeout)
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
