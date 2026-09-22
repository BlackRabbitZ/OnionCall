from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import tempfile
import time
import wave
from pathlib import Path

class AudioError(RuntimeError):
    pass


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_audio_command(command: str) -> str | None:
    """Resolve audio tools, preferring OnionCall's project-local FFmpeg on Windows."""
    if platform.system() == "Windows" and command in {"ffmpeg", "ffplay", "ffprobe"}:
        configured = os.environ.get("ONIONCALL_FFMPEG_DIR", "").strip()
        if configured:
            candidate = Path(configured) / f"{command}.exe"
            if candidate.is_file():
                return str(candidate.resolve())
        bundled = PROJECT_ROOT / "tools" / "ffmpeg"
        if bundled.is_dir():
            for candidate in sorted(bundled.rglob(f"{command}.exe")):
                if candidate.is_file():
                    return str(candidate.resolve())
    found = shutil.which(command)
    return str(Path(found).resolve()) if found else None


def is_termux() -> bool:
    return "com.termux" in os.environ.get("PREFIX", "") or "TERMUX_VERSION" in os.environ


def required_audio_commands() -> list[str]:
    if is_termux():
        return ["termux-microphone-record", "ffmpeg", "opusenc", "opusdec", "play"]
    system = platform.system()
    if system == "Windows":
        return ["ffmpeg", "ffplay"]
    if system == "Darwin":
        return ["rec", "play", "opusenc", "opusdec"]
    return ["arecord", "aplay", "opusenc", "opusdec"]


def missing_audio_commands() -> list[str]:
    return [command for command in required_audio_commands() if resolve_audio_command(command) is None]


def _make_crc_table() -> tuple[int, ...]:
    values: list[int] = []
    for index in range(256):
        value = index << 24
        for _ in range(8):
            value = ((value << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if value & 0x80000000 else (value << 1) & 0xFFFFFFFF
        values.append(value)
    return tuple(values)


_OGG_CRC_TABLE = _make_crc_table()


def _ogg_crc(data: bytes | bytearray) -> int:
    crc = 0
    for value in data:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ _OGG_CRC_TABLE[((crc >> 24) & 0xFF) ^ value]
    return crc


class AudioBackend:
    MAX_COMPRESSED = 8 * 1024 * 1024
    MAX_OGG_PAGES = 4096
    MAX_PACKET = 256 * 1024
    RATE = 16000
    CHANNELS = 1
    SAMPLE_WIDTH = 2

    def __init__(self, runtime_dir: Path, max_seconds: int = 120):
        self.runtime_dir = runtime_dir
        self.max_seconds = max_seconds
        runtime_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(runtime_dir, 0o700)
        except OSError:
            pass

    def _private_temp(self, suffix: str) -> Path:
        fd, name = tempfile.mkstemp(prefix="audio-", suffix=suffix, dir=self.runtime_dir)
        try:
            os.fchmod(fd, 0o600)
        except OSError:
            pass
        os.close(fd)
        return Path(name)

    def _windows_audio_device(self) -> str:
        configured = os.environ.get("ONIONCALL_AUDIO_DEVICE", "").strip()
        if configured:
            return configured
        try:
            result = subprocess.run(
                [resolve_audio_command("ffmpeg") or "ffmpeg", "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise AudioError("Windows-Audiogeräte konnten nicht ermittelt werden") from exc
        devices = re.findall(r'"([^"\r\n]+)"\s*\(audio\)', result.stderr or "", flags=re.IGNORECASE)
        if not devices:
            raise AudioError(
                "Kein Windows-Mikrofon gefunden. Optional ONIONCALL_AUDIO_DEVICE auf den FFmpeg-Gerätenamen setzen."
            )
        return devices[0]

    def record_opus(self, seconds: int) -> bytes:
        if not 1 <= seconds <= self.max_seconds:
            raise AudioError(f"Aufnahmedauer muss zwischen 1 und {self.max_seconds} Sekunden liegen")
        missing = missing_audio_commands()
        if missing:
            raise AudioError("Fehlende Audioprogramme: " + ", ".join(missing))

        system = platform.system()
        raw = self._private_temp(".raw")
        encoded = self._private_temp(".opus")
        mobile: Path | None = None
        try:
            if system == "Windows":
                device = self._windows_audio_device()
                self._run(
                    [
                        "ffmpeg",
                        "-nostdin",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-y",
                        "-f",
                        "dshow",
                        "-t",
                        str(seconds),
                        "-i",
                        f"audio={device}",
                        "-vn",
                        "-sn",
                        "-dn",
                        "-ac",
                        "1",
                        "-ar",
                        str(self.RATE),
                        "-c:a",
                        "libopus",
                        "-b:a",
                        "20k",
                        "-application",
                        "voip",
                        "-frame_duration",
                        "40",
                        "-f",
                        "opus",
                        str(encoded),
                    ],
                    timeout=seconds + 20,
                )
            else:
                if is_termux():
                    mobile = self._private_temp(".m4a")
                    subprocess.run(
                        ["termux-microphone-record", "-l", str(seconds), "-f", str(mobile)],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=seconds + 10,
                    )
                    time.sleep(seconds + 0.5)
                    subprocess.run(
                        ["termux-microphone-record", "-q"],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=5,
                    )
                    self._run(
                        ["ffmpeg", "-y", "-i", str(mobile), "-f", "s16le", "-ar", "16000", "-ac", "1", str(raw)],
                        timeout=seconds + 20,
                    )
                elif system == "Darwin":
                    self._run(
                        [
                            "rec",
                            "-q",
                            "-t",
                            "raw",
                            "-r",
                            "16000",
                            "-e",
                            "signed",
                            "-b",
                            "16",
                            "-c",
                            "1",
                            str(raw),
                            "trim",
                            "0",
                            str(seconds),
                        ],
                        timeout=seconds + 10,
                    )
                else:
                    self._run(
                        [
                            "arecord",
                            "-q",
                            "-f",
                            "S16_LE",
                            "-r",
                            "16000",
                            "-c",
                            "1",
                            "-t",
                            "raw",
                            "-d",
                            str(seconds),
                            str(raw),
                        ],
                        timeout=seconds + 10,
                    )
                self._run(
                    [
                        "opusenc",
                        "--raw",
                        "--raw-rate",
                        "16000",
                        "--raw-chan",
                        "1",
                        "--bitrate",
                        "20",
                        "--framesize",
                        "40",
                        "--speech",
                        "--quiet",
                        str(raw),
                        str(encoded),
                    ],
                    timeout=seconds + 20,
                )
            data = encoded.read_bytes()
            if not data or len(data) > self.MAX_COMPRESSED:
                raise AudioError("Die erzeugte Audiodatei ist leer oder zu groß")
            self._validate_ogg_opus(data)
            return data
        finally:
            raw.unlink(missing_ok=True)
            encoded.unlink(missing_ok=True)
            if mobile is not None:
                mobile.unlink(missing_ok=True)

    @classmethod
    def _validate_ogg_opus(cls, payload: bytes) -> None:
        """Strictly validate the Ogg framing before handing bytes to a native decoder."""
        if not payload or len(payload) > cls.MAX_COMPRESSED:
            raise AudioError("Ungültiges Audiopaket")

        offset = 0
        page_count = 0
        serial: int | None = None
        expected_sequence = 0
        pending = bytearray()
        packets: list[bytes] = []
        audio_packets = 0
        saw_eos = False

        while offset < len(payload):
            page_count += 1
            if page_count > cls.MAX_OGG_PAGES or len(payload) - offset < 27:
                raise AudioError("Ungültiger oder zu komplexer Ogg-Container")
            if payload[offset : offset + 4] != b"OggS" or payload[offset + 4] != 0:
                raise AudioError("Ungültiger Ogg-Seitenkopf")

            header_type = payload[offset + 5]
            if header_type & ~0x07:
                raise AudioError("Ungültige Ogg-Header-Flags")
            current_serial = int.from_bytes(payload[offset + 14 : offset + 18], "little")
            sequence = int.from_bytes(payload[offset + 18 : offset + 22], "little")
            segment_count = payload[offset + 26]
            table_end = offset + 27 + segment_count
            if table_end > len(payload):
                raise AudioError("Abgeschnittene Ogg-Segmenttabelle")
            lacing = payload[offset + 27 : table_end]
            body_size = sum(lacing)
            page_end = table_end + body_size
            if page_end > len(payload):
                raise AudioError("Abgeschnittene Ogg-Seite")

            page = bytearray(payload[offset:page_end])
            stored_crc = int.from_bytes(page[22:26], "little")
            page[22:26] = b"\x00\x00\x00\x00"
            if _ogg_crc(page) != stored_crc:
                raise AudioError("Ogg-Prüfsumme ist ungültig")

            if serial is None:
                serial = current_serial
                if sequence != 0 or not (header_type & 0x02) or header_type & 0x01:
                    raise AudioError("Ungültiger Ogg-Streambeginn")
            else:
                if current_serial != serial:
                    raise AudioError("Mehrere oder verkettete Ogg-Streams sind nicht erlaubt")
                if header_type & 0x02:
                    raise AudioError("Unerwarteter zweiter Ogg-Streambeginn")
                if bool(header_type & 0x01) != bool(pending):
                    raise AudioError("Ungültige Ogg-Paketfortsetzung")
            if sequence != expected_sequence:
                raise AudioError("Ogg-Seitenreihenfolge ist ungültig")
            expected_sequence += 1

            body_offset = table_end
            for size in lacing:
                pending.extend(payload[body_offset : body_offset + size])
                body_offset += size
                if len(pending) > cls.MAX_PACKET:
                    raise AudioError("Ogg-Paket überschreitet das Sicherheitslimit")
                if size < 255:
                    packet = bytes(pending)
                    pending.clear()
                    if len(packets) < 2:
                        packets.append(packet)
                    else:
                        if not packet or len(packet) > 1275:
                            raise AudioError("Ungültige Opus-Paketgröße")
                        audio_packets += 1

            if header_type & 0x04:
                if page_end != len(payload):
                    raise AudioError("Daten nach dem Ogg-Streamende sind nicht erlaubt")
                saw_eos = True
            offset = page_end

        if pending or not saw_eos or len(packets) < 2 or audio_packets < 1:
            raise AudioError("Unvollständiger Ogg/Opus-Stream")

        head = packets[0]
        if len(head) != 19 or not head.startswith(b"OpusHead"):
            raise AudioError("Ungültiger OpusHead")
        version = head[8]
        channels = head[9]
        mapping_family = head[18]
        if version != 1 or channels not in {1, 2} or mapping_family != 0:
            raise AudioError("Nicht unterstützte Opus-Streamparameter")
        tags = packets[1]
        if len(tags) < 16 or not tags.startswith(b"OpusTags"):
            raise AudioError("OpusTags fehlen oder sind ungültig")
        vendor_length = int.from_bytes(tags[8:12], "little")
        cursor = 12 + vendor_length
        if cursor + 4 > len(tags):
            raise AudioError("OpusTags sind abgeschnitten")
        comment_count = int.from_bytes(tags[cursor : cursor + 4], "little")
        cursor += 4
        if comment_count > 1024:
            raise AudioError("Zu viele Opus-Kommentare")
        for _ in range(comment_count):
            if cursor + 4 > len(tags):
                raise AudioError("OpusTags sind abgeschnitten")
            length = int.from_bytes(tags[cursor : cursor + 4], "little")
            cursor += 4
            if length > cls.MAX_PACKET or cursor + length > len(tags):
                raise AudioError("Ungültiger Opus-Kommentar")
            cursor += length
        if cursor != len(tags):
            raise AudioError("Unerwartete Daten in OpusTags")

    @staticmethod
    def _looks_like_opus(payload: bytes) -> bool:
        try:
            AudioBackend._validate_ogg_opus(payload)
            return True
        except AudioError:
            return False

    def _max_wav_size(self) -> int:
        return self.max_seconds * self.RATE * self.CHANNELS * self.SAMPLE_WIDTH + 1024 * 1024

    def _decoder_command(self, encoded: Path, wav: Path) -> list[str]:
        if platform.system() == "Windows":
            return [
                "ffmpeg",
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "ogg",
                "-i",
                str(encoded),
                "-map",
                "0:a:0",
                "-vn",
                "-sn",
                "-dn",
                "-ac",
                "1",
                "-ar",
                str(self.RATE),
                "-t",
                str(self.max_seconds + 1),
                "-f",
                "wav",
                str(wav),
            ]
        base = ["opusdec", "--quiet", str(encoded), str(wav)]
        if platform.system() == "Linux" and shutil.which("prlimit"):
            cpu = max(10, self.max_seconds + 10)
            return [
                "prlimit",
                f"--as={256 * 1024 * 1024}",
                f"--cpu={cpu}",
                f"--fsize={self._max_wav_size()}",
                "--",
                *base,
            ]
        return base

    def play_opus(self, payload: bytes) -> None:
        self._validate_ogg_opus(payload)
        encoded = self._private_temp(".opus")
        wav = self._private_temp(".wav")
        try:
            encoded.write_bytes(payload)
            try:
                os.chmod(encoded, 0o600)
            except OSError:
                pass
            self._run(self._decoder_command(encoded, wav), timeout=self.max_seconds + 20)
            if not wav.exists() or wav.stat().st_size > self._max_wav_size():
                raise AudioError("Dekodierte Audiodatei überschreitet das Sicherheitslimit")
            try:
                with wave.open(str(wav), "rb") as handle:
                    rate = handle.getframerate()
                    frames = handle.getnframes()
                    if handle.getnchannels() != 1 or handle.getsampwidth() != self.SAMPLE_WIDTH or rate != self.RATE:
                        raise AudioError("Dekodierte Audiodatei hat unerwartete PCM-Parameter")
                    duration = frames / rate if rate else self.max_seconds + 1
                    if duration > self.max_seconds + 1:
                        raise AudioError("Dekodierte Audiodauer überschreitet das Sicherheitslimit")
            except (wave.Error, EOFError) as exc:
                raise AudioError("Dekodierte Audiodatei ist ungültig") from exc
            if platform.system() == "Windows":
                self._run(
                    ["ffplay", "-nodisp", "-autoexit", "-loglevel", "error", "-nostdin", str(wav)],
                    timeout=self.max_seconds + 20,
                )
            elif is_termux() or platform.system() == "Darwin":
                self._run(["play", "-q", str(wav)], timeout=self.max_seconds + 20)
            else:
                self._run(["aplay", "-q", str(wav)], timeout=self.max_seconds + 20)
        finally:
            encoded.unlink(missing_ok=True)
            wav.unlink(missing_ok=True)

    def _run(self, command: list[str], *, timeout: float) -> None:
        resolved = resolve_audio_command(command[0])
        if not resolved:
            raise AudioError(f"Audiobefehl fehlt: {command[0]}")
        command = [resolved, *command[1:]]
        path_value = os.environ.get("PATH", "")
        resolved_parent = str(Path(resolved).resolve().parent)
        if resolved_parent not in path_value.split(os.pathsep):
            path_value = resolved_parent + os.pathsep + path_value
        env = {
            "PATH": path_value,
            "HOME": str(Path.home()),
            "LANG": "C",
            "SystemRoot": os.environ.get("SystemRoot", ""),
            "WINDIR": os.environ.get("WINDIR", ""),
        }
        kwargs: dict[str, object] = {}
        if platform.system() == "Windows":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        else:
            kwargs["start_new_session"] = True
        try:
            subprocess.run(
                command,
                check=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=timeout,
                cwd=self.runtime_dir,
                env=env,
                close_fds=True,
                **kwargs,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise AudioError(f"Audiobefehl fehlgeschlagen: {command[0]}") from exc
