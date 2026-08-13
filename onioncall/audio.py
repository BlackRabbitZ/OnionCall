from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
import time
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
    def __init__(self, runtime_dir: Path, max_seconds: int = 120):
        self.runtime_dir = runtime_dir
        self.max_seconds = max_seconds
        runtime_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(runtime_dir, 0o700)

    def _private_temp(self, suffix: str) -> Path:
        fd, name = tempfile.mkstemp(prefix="audio-", suffix=suffix, dir=self.runtime_dir)
        os.fchmod(fd, 0o600)
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
        try:
            if is_termux():
                mobile = self._private_temp(".m4a")
                source = raw
                try:
                    subprocess.run(
                        ["termux-microphone-record", "-l", str(seconds), "-f", str(mobile)],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    time.sleep(seconds + 0.5)
                    subprocess.run(
                        ["termux-microphone-record", "-q"],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    self._run(["ffmpeg", "-y", "-i", str(mobile), "-f", "s16le", "-ar", "16000", "-ac", "1", str(raw)])
                finally:
                    mobile.unlink(missing_ok=True)
            elif platform.system() == "Darwin":
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
                    ]
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
                    ]
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
                    str(source),
                    str(encoded),
                ]
            )
            data = encoded.read_bytes()
            if not data or len(data) > 8 * 1024 * 1024:
                raise AudioError("Die erzeugte Audiodatei ist leer oder zu groß")
            return data
        finally:
            raw.unlink(missing_ok=True)
            encoded.unlink(missing_ok=True)

    def play_opus(self, payload: bytes) -> None:
        if not payload or len(payload) > 8 * 1024 * 1024:
            raise AudioError("Ungültiges Audiopaket")
        encoded = self._private_temp(".opus")
        wav = self._private_temp(".wav")
        try:
            encoded.write_bytes(payload)
            os.chmod(encoded, 0o600)
            self._run(["opusdec", "--quiet", str(encoded), str(wav)])
            if is_termux() or platform.system() == "Darwin":
                self._run(["play", "-q", str(wav)])
            else:
                self._run(["aplay", "-q", str(wav)])
        finally:
            encoded.unlink(missing_ok=True)
            wav.unlink(missing_ok=True)

    @staticmethod
    def _run(command: list[str]) -> None:
        try:
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=180)
        except (OSError, subprocess.SubprocessError) as exc:
            raise AudioError(f"Audiobefehl fehlgeschlagen: {command[0]}") from exc
