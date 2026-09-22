from __future__ import annotations

import queue
import socket
import threading
from contextlib import suppress

from .crypto import AuthenticationError
from .identity import LocalIdentity
from .protocol import perform_server_handshake, SecureChannel

DEFAULT_HANDSHAKE_TIMEOUT = 5.0
DEFAULT_MAX_PENDING = 6


def accept_authenticated(
    listener: socket.socket,
    psk: bytes,
    identity: LocalIdentity,
    expected_fingerprint: str | None = None,
    *,
    stop_event=None,
    handshake_timeout: float = DEFAULT_HANDSHAKE_TIMEOUT,
    max_pending: int = DEFAULT_MAX_PENDING,
) -> SecureChannel:
    """Accept one authenticated peer without letting one idle socket monopolize the listener.

    Pre-authentication handshakes run in a small bounded worker set. Excess sockets are
    rejected immediately. As soon as one peer authenticates, all other pending sockets are
    closed so their workers terminate.
    """
    if not 1.0 <= handshake_timeout <= 30.0:
        raise ValueError("handshake_timeout muss zwischen 1 und 30 Sekunden liegen")
    if not 1 <= max_pending <= 32:
        raise ValueError("max_pending muss zwischen 1 und 32 liegen")

    listener.listen(max(8, max_pending * 2))
    listener.settimeout(0.25)
    result: queue.SimpleQueue[SecureChannel] = queue.SimpleQueue()
    active: set[socket.socket] = set()
    lock = threading.Lock()
    winner_lock = threading.Lock()
    done = threading.Event()

    def close_pending(except_socket: socket.socket | None = None) -> None:
        with lock:
            sockets = [sock for sock in active if sock is not except_socket]
        for sock in sockets:
            with suppress(OSError):
                sock.shutdown(socket.SHUT_RDWR)
            with suppress(OSError):
                sock.close()

    def worker(connection: socket.socket) -> None:
        try:
            channel = perform_server_handshake(
                connection,
                psk,
                identity,
                expected_fingerprint=expected_fingerprint,
                timeout=handshake_timeout,
            )
            with winner_lock:
                if done.is_set():
                    channel.close()
                    return
                done.set()
                result.put(channel)
        except (AuthenticationError, OSError, EOFError):
            with suppress(OSError):
                connection.close()
        finally:
            with lock:
                active.discard(connection)

    try:
        while True:
            try:
                channel = result.get_nowait()
            except queue.Empty:
                channel = None
            if channel is not None:
                done.set()
                close_pending(except_socket=channel.sock)
                return channel
            if stop_event is not None and stop_event.is_set():
                done.set()
                close_pending()
                raise OSError("Listener wurde beendet")

            try:
                connection, _ = listener.accept()
            except socket.timeout:
                continue

            with lock:
                if len(active) >= max_pending:
                    reject = True
                else:
                    active.add(connection)
                    reject = False
            if reject:
                with suppress(OSError):
                    connection.close()
                continue
            threading.Thread(
                target=worker,
                args=(connection,),
                name="onioncall-preauth",
                daemon=True,
            ).start()
    finally:
        done.set()
        close_pending()
