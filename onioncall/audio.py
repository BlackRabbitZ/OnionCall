from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
import time
import wave
from pathlib import Path


class AudioError(RuntimeError):
    pass


def is_termux() -> bool:
    return "com.termux" in os.environ.get("PREFIX", "") or "TERMUX_VERSION" in os.environ


def required_audio_commands() -> list[str]:
    if is_termux():
        return ["termux-microphone-record", "ffmpeg", "opusenc", "opusdec", "play"]
    if platform.system() == "Darwin":
        return ["rec", "play", "opusenc", "opusdec"]
    return ["arecord", "aplay", "opusenc", "opusdec"]


def missing_audio_commands() -> list[str]:
    return [command for command in required_audio_commands() if shutil.which(command) is None]


class AudioBackend:
    MAX_COMPRESSED = 8 * 1024 * 1024
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

    def record_opus(self, seconds: int) -> bytes:
        if not 1 <= seconds <= self.max_seconds:
            raise AudioError(f"Aufnahmedauer muss zwischen 1 und {self.max_seconds} Sekunden liegen")
        missing = missing_audio_commands()
        if missing:
            raise AudioError("Fehlende Audioprogramme: " + ", ".join(missing))
        raw = self._private_temp(".raw")
        encoded = self._private_temp(".opus")
        source = raw
        mobile: Path | None = None
        try:
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
            elif platform.system() == "Darwin":
                self._run(
                    [
                        "rec", "-q", "-t", "raw", "-r", "16000", "-e", "signed", "-b", "16", "-c", "1",
                        str(raw), "trim", "0", str(seconds),
                    ],
                    timeout=seconds + 10,
                )
            else:
                self._run(
                    [
                        "arecord", "-q", "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "raw", "-d",
                        str(seconds), str(raw),
                    ],
                    timeout=seconds + 10,
                )
            self._run(
                [
                    "opusenc", "--raw", "--raw-rate", "16000", "--raw-chan", "1", "--bitrate", "20",
                    "--framesize", "40", "--speech", "--quiet", str(source), str(encoded),
                ],
                timeout=seconds + 20,
            )
            data = encoded.read_bytes()
            if not data or len(data) > self.MAX_COMPRESSED:
                raise AudioError("Die erzeugte Audiodatei ist leer oder zu groß")
            return data
        finally:
            raw.unlink(missing_ok=True)
            encoded.unlink(missing_ok=True)
            if mobile is not None:
                mobile.unlink(missing_ok=True)

    @staticmethod
    def _looks_like_opus(payload: bytes) -> bool:
        # Opus-in-Ogg muss mit OggS beginnen und sehr früh einen OpusHead tragen.
        return payload.startswith(b"OggS") and b"OpusHead" in payload[:512]

    def _max_wav_size(self) -> int:
        # PCM 16 kHz / mono / 16 Bit + großzügiger Header-/Containerpuffer.
        return self.max_seconds * self.RATE * self.CHANNELS * self.SAMPLE_WIDTH + 1024 * 1024

    def _decoder_command(self, encoded: Path, wav: Path) -> list[str]:
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
        if not payload or len(payload) > self.MAX_COMPRESSED:
            raise AudioError("Ungültiges Audiopaket")
        if not self._looks_like_opus(payload):
            raise AudioError("Audiopaket ist kein gültiger Ogg/Opus-Container")
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
                    duration = frames / rate if rate else self.max_seconds + 1
                    if duration > self.max_seconds + 1:
                        raise AudioError("Dekodierte Audiodauer überschreitet das Sicherheitslimit")
            except (wave.Error, EOFError) as exc:
                raise AudioError("Dekodierte Audiodatei ist ungültig") from exc
            if is_termux() or platform.system() == "Darwin":
                self._run(["play", "-q", str(wav)], timeout=self.max_seconds + 20)
            else:
                self._run(["aplay", "-q", str(wav)], timeout=self.max_seconds + 20)
        finally:
            encoded.unlink(missing_ok=True)
            wav.unlink(missing_ok=True)

    def _run(self, command: list[str], *, timeout: float) -> None:
        env = {"PATH": os.environ.get("PATH", ""), "HOME": str(Path.home()), "LANG": "C"}
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
                start_new_session=True,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise AudioError(f"Audiobefehl fehlgeschlagen: {command[0]}") from exc
