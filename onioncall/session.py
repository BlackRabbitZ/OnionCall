from __future__ import annotations

import re
import threading
from contextlib import suppress

from .audio import AudioBackend, AudioError
from .protocol import MessageType, ProtocolError, SecureChannel

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def safe_display(text: str) -> str:
    return CONTROL_CHARS.sub("�", text.replace("\x1b", "�"))


HELP = "Text direkt eingeben | a = 5 Sekunden Audio | q = Ende | /help = alle Befehle"
FULL_HELP = (
    "Kurz: Text direkt eingeben, a = 5 Sekunden Audio, q = Ende. "
    "Erweitert: /say SEKUNDEN, /text NACHRICHT, /quit"
)


class InteractiveSession:
    def __init__(self, channel: SecureChannel, audio: AudioBackend):
        self.channel = channel
        self.audio = audio
        self.finished = threading.Event()
        self.receiver = threading.Thread(target=self._receive_loop, name="onioncall-receiver", daemon=True)

    def run(self) -> None:
        print("Sichere Sitzung hergestellt. " + HELP, flush=True)
        self.receiver.start()
        try:
            while not self.finished.is_set():
                try:
                    line = input("onioncall> ")
                except EOFError:
                    line = "/quit"
                if not line.strip():
                    continue
                if line in ("q", "/quit"):
                    with suppress(OSError, ProtocolError):
                        self.channel.send(MessageType.CLOSE, b"normal")
                    break
                if line == "/help":
                    print(FULL_HELP)
                    continue
                if line == "a":
                    self._send_audio("/say 5")
                    continue
                if line.startswith("/say"):
                    self._send_audio(line)
                    continue
                if line.startswith("/text "):
                    self._send_text(line[6:])
                    continue
                if line.startswith("/"):
                    print("Unbekannter Befehl. " + FULL_HELP)
                    continue
                self._send_text(line)
        finally:
            self.finished.set()
            self.channel.close()
            self.receiver.join(timeout=2)

    def _send_text(self, text: str) -> None:
        payload = text.encode("utf-8")
        if len(payload) > 8 * 1024:
            print("Nachricht ist zu lang (maximal 8192 UTF-8-Bytes).")
            return
        try:
            self.channel.send(MessageType.TEXT, payload)
            print("[gesendet] " + safe_display(text))
        except (OSError, ProtocolError) as exc:
            print(f"Senden fehlgeschlagen: {exc}")
            self.finished.set()

    def _send_audio(self, line: str) -> None:
        parts = line.split()
        if len(parts) != 2 or not parts[1].isdigit():
            print("Verwendung: /say SEKUNDEN")
            return
        seconds = int(parts[1])
        try:
            print(f"Aufnahme läuft für {seconds} Sekunden …", flush=True)
            payload = self.audio.record_opus(seconds)
            self.channel.send(MessageType.AUDIO_OPUS, payload)
            print(f"Sprachnachricht gesendet ({len(payload)} Bytes).")
        except (AudioError, OSError, ProtocolError) as exc:
            print(f"Audio konnte nicht gesendet werden: {exc}")

    def _receive_loop(self) -> None:
        try:
            while not self.finished.is_set():
                message = self.channel.receive()
                if message.kind == MessageType.TEXT:
                    text = message.payload.decode("utf-8", errors="replace")
                    print("\n[Nachricht] " + safe_display(text), flush=True)
                elif message.kind == MessageType.AUDIO_OPUS:
                    print(f"\n[Audio] {len(message.payload)} Bytes – Wiedergabe …", flush=True)
                    try:
                        self.audio.play_opus(message.payload)
                    except AudioError as exc:
                        print(f"Wiedergabe fehlgeschlagen: {exc}", flush=True)
                elif message.kind == MessageType.CLOSE:
                    print("\nDie Gegenstelle hat die Sitzung beendet.", flush=True)
                    self.finished.set()
                    return
        except EOFError:
            if not self.finished.is_set():
                print("\nVerbindung geschlossen.", flush=True)
        except (OSError, ProtocolError) as exc:
            if not self.finished.is_set():
                print(f"\nSitzung aus Sicherheitsgründen beendet: {exc}", flush=True)
        finally:
            self.finished.set()
