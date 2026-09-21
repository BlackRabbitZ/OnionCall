from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from onioncall.audio import AudioBackend, AudioError


class AudioSecurityTests(unittest.TestCase):
    def test_non_opus_payload_rejected_before_decoder(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = AudioBackend(Path(tmp), 10)
            with self.assertRaisesRegex(AudioError, 'Ogg/Opus'):
                backend.play_opus(b'not-an-opus-file')

    def test_size_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = AudioBackend(Path(tmp), 10)
            with self.assertRaises(AudioError):
                backend.play_opus(b'X' * (backend.MAX_COMPRESSED + 1))


if __name__ == '__main__':
    unittest.main()
