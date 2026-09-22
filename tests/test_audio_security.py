from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from onioncall.audio import AudioBackend, AudioError, _ogg_crc


def ogg_page(packets: list[bytes]) -> bytes:
    lacing = bytearray()
    body = bytearray()
    for packet in packets:
        if len(packet) >= 255:
            raise ValueError("test helper only supports short packets")
        lacing.append(len(packet))
        body.extend(packet)
    header = bytearray()
    header += b"OggS"
    header += b"\x00"
    header += b"\x06"  # BOS + EOS
    header += (0).to_bytes(8, "little")
    header += (1).to_bytes(4, "little")
    header += (0).to_bytes(4, "little")
    header += b"\x00\x00\x00\x00"
    header += bytes((len(lacing),))
    page = header + lacing + body
    page[22:26] = _ogg_crc(page).to_bytes(4, "little")
    return bytes(page)


def minimal_opus() -> bytes:
    head = (
        b"OpusHead"
        + bytes((1, 1))
        + (312).to_bytes(2, "little")
        + (16000).to_bytes(4, "little")
        + b"\x00\x00"
        + b"\x00"
    )
    tags = b"OpusTags" + (0).to_bytes(4, "little") + (0).to_bytes(4, "little")
    return ogg_page([head, tags, b"\xf8\xff\xfe"])


class AudioSecurityTests(unittest.TestCase):
    def test_strict_container_accepts_minimal_framing(self) -> None:
        AudioBackend._validate_ogg_opus(minimal_opus())

    def test_bad_crc_is_rejected_before_decoder(self) -> None:
        payload = bytearray(minimal_opus())
        payload[-1] ^= 1
        with self.assertRaises(AudioError):
            AudioBackend._validate_ogg_opus(bytes(payload))

    def test_appended_data_is_rejected(self) -> None:
        with self.assertRaises(AudioError):
            AudioBackend._validate_ogg_opus(minimal_opus() + b"junk")

    def test_windows_resolver_prefers_project_local_ffmpeg(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            binary = root / "tools" / "ffmpeg" / "ffmpeg-9.0.2" / "bin" / "ffmpeg.exe"
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b"MZ")
            with mock.patch("onioncall.audio.platform.system", return_value="Windows"), \
                 mock.patch("onioncall.audio.PROJECT_ROOT", root):
                from onioncall.audio import resolve_audio_command
                self.assertEqual(resolve_audio_command("ffmpeg"), str(binary.resolve()))



if __name__ == "__main__":
    unittest.main()
