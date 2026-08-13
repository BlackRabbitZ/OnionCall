from __future__ import annotations

import queue
import threading
import time
import unittest

from prompt_toolkit import PromptSession
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from onioncall.protocol import Message, MessageType
from onioncall.session import InteractiveSession


class FakeChannel:
    def __init__(self) -> None:
        self.incoming: queue.Queue[Message | BaseException] = queue.Queue()
        self.sent: list[tuple[MessageType, bytes]] = []
        self.received = threading.Event()

    def send(self, kind: MessageType, payload: bytes = b"") -> None:
        self.sent.append((kind, payload))

    def receive(self) -> Message:
        item = self.incoming.get(timeout=2)
        if isinstance(item, BaseException):
            raise item
        self.received.set()
        return item

    def close(self) -> None:
        self.incoming.put(EOFError("geschlossen"))


class FakeAudio:
    def record_opus(self, seconds: int) -> bytes:
        return b"audio"

    def play_opus(self, payload: bytes) -> None:
        pass


class SessionTests(unittest.TestCase):
    @staticmethod
    def _wait_for_prompt(prompt: PromptSession[str]) -> bool:
        for _ in range(200):
            if prompt.app.is_running:
                return True
            time.sleep(0.01)
        return False

    def test_incoming_message_does_not_destroy_partially_typed_text(self) -> None:
        channel = FakeChannel()
        with create_pipe_input() as pipe_input:
            prompt = PromptSession(input=pipe_input, output=DummyOutput())
            session = InteractiveSession(channel, FakeAudio(), prompt)
            thread = threading.Thread(target=session.run)
            thread.start()

            pipe_input.send_text("Hal")
            channel.incoming.put(Message(MessageType.TEXT, b"Nachricht waehrend der Eingabe"))
            self.assertTrue(channel.received.wait(timeout=2))
            pipe_input.send_text("lo\nq\n")

            thread.join(timeout=3)
            self.assertFalse(thread.is_alive())
            self.assertIn((MessageType.TEXT, b"Hallo"), channel.sent)
            self.assertIn((MessageType.CLOSE, b"normal"), channel.sent)

    def test_remote_close_stops_active_prompt(self) -> None:
        channel = FakeChannel()
        with create_pipe_input() as pipe_input:
            prompt = PromptSession(input=pipe_input, output=DummyOutput())
            session = InteractiveSession(channel, FakeAudio(), prompt)
            thread = threading.Thread(target=session.run)
            thread.start()

            self.assertTrue(self._wait_for_prompt(prompt))
            channel.incoming.put(Message(MessageType.CLOSE, b"normal"))

            thread.join(timeout=3)
            self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
