from __future__ import annotations

import threading
from collections.abc import Callable
from contextlib import suppress

from .audio import AudioBackend, AudioError
from .protocol import MessageType, ProtocolError, SecureChannel
from .session import safe_display

EventCallback = Callable[[str, str], None]


class GuiSession:
    """Thread-safe bridge between a SecureChannel and the local web interface."""

    def __init__(self, channel: SecureChannel, audio: AudioBackend, emit: EventCallback):
        self.channel = channel
        self.audio = audio
        self.emit = emit
        self.finished = threading.Event()
        self.receiver = threading.Thread(target=self._receive_loop, name="onioncall-gui-receiver", daemon=True)

    def run(self) -> None:
        self.receiver.start()
        self.finished.wait()
        self.channel.close()
        if threading.current_thread() is not self.receiver:
            self.receiver.join(timeout=2)

    def send_text(self, text: str) -> None:
        text = text.strip()
        if not text:
            raise ValueError("Nachricht darf nicht leer sein")
        payload = text.encode("utf-8")
        if len(payload) > 8 * 1024:
            raise ValueError("Nachricht ist zu lang (maximal 8192 UTF-8-Bytes)")
        try:
            self.channel.send(MessageType.TEXT, payload)
        except (OSError, ProtocolError) as exc:
            self.finished.set()
            raise RuntimeError(f"Senden fehlgeschlagen: {exc}") from exc
        self.emit("self", safe_display(text))

    def send_audio(self, seconds: int) -> None:
        self.emit("system", f"Aufnahme läuft für {seconds} Sekunden …")
        try:
            payload = self.audio.record_opus(seconds)
            self.channel.send(MessageType.AUDIO_OPUS, payload)
        except (AudioError, OSError, ProtocolError) as exc:
            raise RuntimeError(f"Audio konnte nicht gesendet werden: {exc}") from exc
        self.emit("self_audio", f"Sprachnachricht gesendet ({seconds} Sekunden)")

    def close(self, *, notify_peer: bool = True) -> None:
        if self.finished.is_set():
            return
        if notify_peer:
            with suppress(OSError, ProtocolError):
                self.channel.send(MessageType.CLOSE, b"normal")
        self.finished.set()
        self.channel.close()

    def _receive_loop(self) -> None:
        try:
            while not self.finished.is_set():
                message = self.channel.receive()
                if message.kind == MessageType.TEXT:
                    text = message.payload.decode("utf-8", errors="replace")
                    self.emit("peer", safe_display(text))
                elif message.kind == MessageType.AUDIO_OPUS:
                    self.emit("peer_audio", f"Sprachnachricht empfangen ({len(message.payload)} Bytes)")
                    try:
                        self.audio.play_opus(message.payload)
                    except AudioError as exc:
                        self.emit("error", f"Wiedergabe fehlgeschlagen: {exc}")
                elif message.kind == MessageType.CLOSE:
                    self.emit("system", "Die Gegenstelle hat die Sitzung beendet.")
                    return
        except EOFError:
            if not self.finished.is_set():
                self.emit("system", "Verbindung geschlossen.")
        except (OSError, ProtocolError) as exc:
            if not self.finished.is_set():
                self.emit("error", f"Sitzung aus Sicherheitsgründen beendet: {exc}")
        finally:
            self.finished.set()
