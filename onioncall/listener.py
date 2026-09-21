from __future__ import annotations

import socket
import time
from contextlib import suppress

from .crypto import AuthenticationError
from .identity import LocalIdentity
from .protocol import SecureChannel, perform_server_handshake


def accept_authenticated(
    listener: socket.socket,
    psk: bytes,
    identity: LocalIdentity,
    expected_fingerprint: str | None = None,
    *,
    stop_event=None,
    handshake_timeout: float = 20.0,
) -> SecureChannel:
    """Keep the listener alive until a peer actually authenticates.

    Failed/idle connections are closed and do not consume the onion listener. A
    small capped delay makes blind authentication flooding more expensive while
    keeping legitimate retries responsive.
    """
    failures = 0
    listener.listen(8)
    listener.settimeout(1.0)
    while True:
        if stop_event is not None and stop_event.is_set():
            raise OSError("Listener wurde beendet")
        try:
            connection, _ = listener.accept()
        except socket.timeout:
            continue
        try:
            channel = perform_server_handshake(
                connection,
                psk,
                identity,
                expected_fingerprint=expected_fingerprint,
                timeout=handshake_timeout,
            )
            return channel
        except AuthenticationError:
            failures += 1
            with suppress(OSError):
                connection.close()
            time.sleep(min(2.0, 0.15 * failures))
        except (OSError, EOFError):
            with suppress(OSError):
                connection.close()
            if stop_event is not None and stop_event.is_set():
                raise
