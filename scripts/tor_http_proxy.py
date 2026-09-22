#!/usr/bin/env python3
"""Lokaler HTTP-CONNECT-zu-Tor-SOCKS-Proxy fuer das OnionCall-Setup.

Der Proxy lauscht ausschliesslich auf 127.0.0.1. pip verbindet sich per normalem
HTTP CONNECT mit diesem lokalen Endpunkt. Die Zielverbindung wird anschliessend
ueber den lokalen Tor-SOCKS-Port aufgebaut. Hostnamen werden als SOCKS5-Domain
uebergeben und daher nicht lokal per DNS aufgeloest.
"""
from __future__ import annotations

import ipaddress
import select
import socket
import socketserver
import struct
from contextlib import suppress

MAX_HEADER = 16 * 1024
RELAY_BUFFER = 64 * 1024
CONNECT_TIMEOUT = 30.0


class ProxyError(RuntimeError):
    pass


def _recv_exact(sock: socket.socket, amount: int) -> bytes:
    data = bytearray()
    while len(data) < amount:
        chunk = sock.recv(amount - len(data))
        if not chunk:
            raise ProxyError("SOCKS-Verbindung wurde unerwartet geschlossen")
        data.extend(chunk)
    return bytes(data)


def tor_socks_connect(host: str, port: int, socks_port: int) -> socket.socket:
    if not (1 <= port <= 65535):
        raise ProxyError("Ungueltiger Zielport")
    sock = socket.create_connection(("127.0.0.1", socks_port), timeout=CONNECT_TIMEOUT)
    try:
        sock.sendall(b"\x05\x01\x00")
        if _recv_exact(sock, 2) != b"\x05\x00":
            raise ProxyError("Tor-SOCKS verweigert die Verbindung")
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            encoded = host.encode("idna")
            if not encoded or len(encoded) > 253:
                raise ProxyError("Ungueltiger Zielhostname") from None
            address = b"\x03" + bytes((len(encoded),)) + encoded
        else:
            address = b"\x01" + ip.packed if ip.version == 4 else b"\x04" + ip.packed
        sock.sendall(b"\x05\x01\x00" + address + struct.pack("!H", port))
        head = _recv_exact(sock, 4)
        if head[0] != 5 or head[1] != 0:
            raise ProxyError(f"Tor-SOCKS-Verbindung fehlgeschlagen (Code {head[1]})")
        if head[3] == 1:
            _recv_exact(sock, 4)
        elif head[3] == 3:
            _recv_exact(sock, _recv_exact(sock, 1)[0])
        elif head[3] == 4:
            _recv_exact(sock, 16)
        else:
            raise ProxyError("Ungueltige SOCKS-Antwort")
        _recv_exact(sock, 2)
        sock.settimeout(None)
        return sock
    except Exception:
        sock.close()
        raise


def parse_connect_target(target: str) -> tuple[str, int]:
    target = target.strip()
    if target.startswith("["):
        end = target.find("]")
        if end <= 1 or end + 1 >= len(target) or target[end + 1] != ":":
            raise ProxyError("Ungueltiges CONNECT-Ziel")
        host = target[1:end]
        port_text = target[end + 2 :]
    else:
        if ":" not in target:
            raise ProxyError("CONNECT-Ziel ohne Port")
        host, port_text = target.rsplit(":", 1)
    if not host:
        raise ProxyError("CONNECT-Ziel ohne Host")
    try:
        port = int(port_text, 10)
    except ValueError as exc:
        raise ProxyError("Ungueltiger CONNECT-Port") from exc
    return host, port


def _read_header(sock: socket.socket) -> bytes:
    data = bytearray()
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > MAX_HEADER:
            raise ProxyError("HTTP-Header zu gross")
    return bytes(data)


def _relay(left: socket.socket, right: socket.socket) -> None:
    sockets = [left, right]
    while sockets:
        readable, _, _ = select.select(sockets, [], [], 60.0)
        if not readable:
            return
        for source in readable:
            try:
                chunk = source.recv(RELAY_BUFFER)
            except OSError:
                return
            if not chunk:
                return
            target = right if source is left else left
            try:
                target.sendall(chunk)
            except OSError:
                return


class _ConnectHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        self.request.settimeout(CONNECT_TIMEOUT)
        remote: socket.socket | None = None
        try:
            header = _read_header(self.request)
            first_line = header.split(b"\r\n", 1)[0].decode("ascii", errors="strict")
            parts = first_line.split()
            if len(parts) != 3 or parts[0].upper() != "CONNECT":
                self.request.sendall(b"HTTP/1.1 405 Method Not Allowed\r\nConnection: close\r\n\r\n")
                return
            host, port = parse_connect_target(parts[1])
            if port != 443:
                self.request.sendall(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n")
                return
            remote = tor_socks_connect(host, port, self.server.socks_port)  # type: ignore[attr-defined]
            self.request.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            self.request.settimeout(None)
            _relay(self.request, remote)
        except (OSError, UnicodeError, ProxyError):
            with suppress(OSError):
                self.request.sendall(b"HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n")
        finally:
            if remote is not None:
                remote.close()


class TorHttpProxy(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, socks_port: int):
        super().__init__(("127.0.0.1", 0), _ConnectHandler)
        self.socks_port = socks_port

    @property
    def port(self) -> int:
        return int(self.server_address[1])
