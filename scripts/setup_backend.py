#!/usr/bin/env python3
"""Sicheres Python-Setup für BRZ – OnionCall.

OnionCall bleibt ein Python-Projekt. Das Setup erstellt eine lokale virtuelle
Python-Umgebung, erzeugt keine OnionCall-.exe-Anwendung und lädt fehlende
Python-Pakete standardmäßig nur über Tor. Clearnet ist nur mit
--allow-clearnet möglich.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import socket
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import venv
import zipfile
from pathlib import Path

def _configure_utf8_stdio() -> None:
    """Force UTF-8 even when Windows inherits a legacy charmap/code page."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


_configure_utf8_stdio()
MIN_PYTHON = (3, 10)
PINNED_DISTRIBUTIONS = {
    "cryptography": "50.0.1",
    "prompt-toolkit": "3.0.53",
    "wcwidth": "0.8.4",
}
PYTHON_DEPENDENCIES = tuple(f"{name}=={version}" for name, version in PINNED_DISTRIBUTIONS.items())

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOR_BUNDLE_VERSION = "15.0.23"
TOR_BUNDLE_URL = (
    "https://dist.torproject.org/torbrowser/15.0.23/"
    "tor-expert-bundle-windows-x86_64-15.0.23.tar.gz"
)
TOR_BUNDLE_SHA256 = "231dad6b9cb401a54c260db7046965ef04e4f72ff071b140d423fb5da281ab1e"

FFMPEG_VERSION = "9.0.2"
FFMPEG_WINDOWS_URL = (
    "https://www.gyan.dev/ffmpeg/builds/packages/"
    "ffmpeg-9.0.2-essentials_build.zip"
)
FFMPEG_WINDOWS_SHA256 = "60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba"


def progress(value: int, message: str) -> None:
    print(f"::progress::{value}::{message}", flush=True)


def run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    child_env = os.environ.copy()
    if env:
        child_env.update(env)
    child_env["PYTHONIOENCODING"] = "utf-8"
    child_env["PYTHONUTF8"] = "1"
    result = subprocess.run(command, cwd=cwd, env=child_env)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def ensure_supported_python() -> None:
    if sys.version_info < MIN_PYTHON:
        raise SystemExit(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} oder neuer wird benötigt.")


def venv_python(root: Path) -> Path:
    return root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def ensure_venv(root: Path) -> Path:
    python = venv_python(root)
    if python.exists():
        return python
    print("Lokale Python-Umgebung .venv wird eingerichtet …")
    venv.EnvBuilder(with_pip=True, clear=False, symlinks=os.name != "nt").create(root / ".venv")
    if not python.exists():
        raise SystemExit("Die lokale Python-Umgebung konnte nicht erstellt werden.")
    return python


def find_tor() -> str | None:
    configured = os.environ.get("ONIONCALL_TOR_BINARY")
    if configured and Path(configured).is_file():
        return str(Path(configured).resolve())

    bundled = PROJECT_ROOT / "tools" / "tor"
    if bundled.is_dir():
        candidates = sorted(bundled.rglob("tor.exe" if os.name == "nt" else "tor"))
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate.resolve())
    found = shutil.which("tor")
    if found:
        return found
    if os.name == "nt":
        candidates: list[Path] = []
        for base in (os.environ.get("PROGRAMFILES"), os.environ.get("LOCALAPPDATA"), os.environ.get("USERPROFILE")):
            if base:
                b = Path(base)
                candidates.extend([
                    b / "Tor Browser" / "Browser" / "TorBrowser" / "Tor" / "tor.exe",
                    b / "Programs" / "Tor Browser" / "Browser" / "TorBrowser" / "Tor" / "tor.exe",
                    b / "Desktop" / "Tor Browser" / "Browser" / "TorBrowser" / "Tor" / "tor.exe",
                ])
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate.resolve())
    return None


def find_ffmpeg_executable(name: str) -> str | None:
    """Find FFmpeg tools, preferring OnionCall's project-local bundle."""
    if name not in {"ffmpeg", "ffplay", "ffprobe"}:
        raise ValueError("Unbekanntes FFmpeg-Werkzeug")

    configured = os.environ.get("ONIONCALL_FFMPEG_DIR", "").strip()
    executable = name + (".exe" if os.name == "nt" else "")
    if configured:
        candidate = Path(configured) / executable
        if candidate.is_file():
            return str(candidate.resolve())

    bundled = PROJECT_ROOT / "tools" / "ffmpeg"
    if bundled.is_dir():
        candidates = sorted(bundled.rglob(executable))
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate.resolve())

    found = shutil.which(name)
    return str(Path(found).resolve()) if found else None


def _safe_extract_tar(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with tarfile.open(archive, "r:gz") as handle:
        members = handle.getmembers()
        for member in members:
            target = (destination / member.name).resolve()
            if root != target and root not in target.parents:
                raise SystemExit("Tor-Archiv enthält einen unsicheren Dateipfad.")
            if member.issym() or member.islnk():
                raise SystemExit("Tor-Archiv enthält unerwartete symbolische Links.")
        handle.extractall(destination, members=members)


def _safe_extract_zip(archive: Path, destination: Path) -> None:
    """Extract a ZIP without path traversal or symlink entries."""
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive) as handle:
        for info in handle.infolist():
            target = (destination / info.filename).resolve()
            if root != target and root not in target.parents:
                raise RuntimeError("FFmpeg-Archiv enthält einen unsicheren Dateipfad.")
            mode = (info.external_attr >> 16) & 0xFFFF
            if mode and stat.S_ISLNK(mode):
                raise RuntimeError("FFmpeg-Archiv enthält unerwartete symbolische Links.")
        handle.extractall(destination)


def _download_verified(
    url: str,
    expected_sha256: str,
    destination: Path,
    *,
    proxy: str | None = None,
    progress_start: int = 62,
    progress_end: int = 76,
    label: str = "Datei wird geladen …",
) -> None:
    handlers = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    opener = urllib.request.build_opener(*handlers)
    request = urllib.request.Request(url, headers={"User-Agent": "OnionCall-Setup/2.7.6"})
    digest = hashlib.sha256()
    try:
        with opener.open(request, timeout=90) as response, destination.open("wb") as out:
            total = int(response.headers.get("Content-Length", "0") or 0)
            received = 0
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                out.write(chunk)
                digest.update(chunk)
                received += len(chunk)
                if total:
                    span = max(0, progress_end - progress_start)
                    pct = progress_start + min(span, int(received / total * span))
                    progress(pct, label)
    except Exception as exc:
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"Download fehlgeschlagen: {url}") from exc
    if digest.hexdigest().lower() != expected_sha256.lower():
        destination.unlink(missing_ok=True)
        raise RuntimeError("Download wurde wegen falscher SHA-256-Prüfsumme abgebrochen.")


def bootstrap_windows_tor() -> str | None:
    existing = find_tor()
    if existing:
        print(f"Tor gefunden: {existing}", flush=True)
        return existing
    if os.name != "nt":
        return None
    progress(18, "Tor fehlt – Windows Expert Bundle wird einmalig vom Tor Project geladen …")
    print(
        "Hinweis: Da noch kein Tor vorhanden ist, erfolgt ausschließlich dieser Tor-Bootstrap "
        "einmalig direkt per HTTPS vom Tor Project. Danach werden Python-Pakete über Tor geladen.",
        flush=True,
    )
    tools = PROJECT_ROOT / "tools" / "tor"
    tools.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="onioncall-tor-bootstrap-") as tmp:
        archive = Path(tmp) / f"tor-expert-bundle-{TOR_BUNDLE_VERSION}.tar.gz"
        request = urllib.request.Request(TOR_BUNDLE_URL, headers={"User-Agent": "OnionCall-Setup/2.7.6"})
        try:
            with urllib.request.urlopen(request, timeout=90) as response, archive.open("wb") as out:
                digest = hashlib.sha256()
                total = int(response.headers.get("Content-Length", "0") or 0)
                received = 0
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    out.write(chunk)
                    digest.update(chunk)
                    received += len(chunk)
                    if total:
                        pct = 18 + min(12, int(received / total * 12))
                        progress(pct, "Tor Expert Bundle wird geladen …")
        except Exception as exc:
            raise SystemExit(
                "Tor konnte nicht automatisch vom offiziellen Tor Project geladen werden. "
                "Prüfe die Internetverbindung und starte das Setup erneut."
            ) from exc
        if digest.hexdigest().lower() != TOR_BUNDLE_SHA256:
            raise SystemExit("Tor-Download wurde wegen falscher SHA-256-Prüfsumme abgebrochen.")
        progress(31, "Tor-Download geprüft – Expert Bundle wird entpackt …")
        _safe_extract_tar(archive, tools)
    tor = find_tor()
    if not tor:
        raise SystemExit("Tor wurde entpackt, aber tor.exe konnte nicht gefunden werden.")
    print(f"Tor lokal eingerichtet: {tor}", flush=True)
    return tor


def _free_loopback_port() -> int:
    """Reserve a currently unused local TCP port and return it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _tor_log_text(log: Path) -> str:
    try:
        return log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    except OSError:
        return ""


def _tor_bootstrap_percent(text: str) -> int | None:
    import re
    matches = re.findall(r"Bootstrapped\s+(\d{1,3})%", text)
    if not matches:
        return None
    return max(0, min(100, int(matches[-1])))


def _wait_tcp_port(port: int, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.35):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def wait_tor_ready(
    socks_port: int,
    http_port: int,
    process: subprocess.Popen[bytes],
    log: Path,
    *,
    timeout: float = 180.0,
    ui_start: int = 41,
    ui_span: int = 16,
    ui_label: str = "Tor wird für den privaten Paketdownload aufgebaut",
) -> None:
    """Wait until Tor has fully bootstrapped and both local proxy ports listen.

    Merely seeing a listening SocksPort is not enough: Tor opens its listener
    before a usable circuit exists. The setup therefore waits for Tor's own
    `Bootstrapped 100%` notice and then verifies the local SOCKS and HTTP tunnel
    listeners. Bootstrap progress is forwarded to the browser installer.
    """
    deadline = time.monotonic() + timeout
    last_reported = -1
    while time.monotonic() < deadline:
        if process.poll() is not None:
            detail = _tor_log_text(log)[-2000:]
            raise RuntimeError("Tor wurde beim privaten Setup beendet.\n" + detail)

        text = _tor_log_text(log)
        pct = _tor_bootstrap_percent(text)
        if pct is not None and pct != last_reported:
            ui_pct = ui_start + int(pct * ui_span / 100)
            progress(ui_pct, f"{ui_label} … {pct} %")
            last_reported = pct

        if pct == 100:
            if _wait_tcp_port(socks_port, 1.5) and _wait_tcp_port(http_port, 1.5):
                progress(ui_start + ui_span + 1, f"{ui_label}: verbunden")
                return
        time.sleep(0.25)

    text = _tor_log_text(log)
    pct = _tor_bootstrap_percent(text)
    stage = f"Letzter Tor-Bootstrap-Stand: {pct} %." if pct is not None else "Tor meldete keinen Bootstrap-Fortschritt."
    detail = text[-2200:].strip()
    message = (
        "Tor wurde für den privaten Paketdownload nicht rechtzeitig vollständig verbunden. "
        + stage
        + " Der Installer wechselt aus Sicherheitsgründen nicht automatisch auf Clearnet."
    )
    if detail:
        message += "\n\nLetzte Tor-Meldungen:\n" + detail
    raise TimeoutError(message)


def _run_tor_install_attempt(python: Path, tor: str, attempt: int) -> None:
    with tempfile.TemporaryDirectory(prefix=f"onioncall-setup-tor-{attempt}-") as tmp:
        tmp_path = Path(tmp)
        data = tmp_path / "data"
        data.mkdir(mode=0o700)
        log = tmp_path / "tor.log"
        torrc = tmp_path / "torrc"
        socks_port = _free_loopback_port()
        http_port = _free_loopback_port()
        while http_port == socks_port:
            http_port = _free_loopback_port()

        # HTTPTunnelPort is Tor's native local HTTP CONNECT proxy.  pip only
        # contacts HTTPS endpoints here, so using Tor's own tunnel removes the
        # additional custom HTTP->SOCKS bridge and its timing/race surface.
        torrc.write_text(
            f"DataDirectory {data}\n"
            f"SocksPort 127.0.0.1:{socks_port}\n"
            f"HTTPTunnelPort 127.0.0.1:{http_port}\n"
            "ClientOnly 1\n"
            "SafeSocks 1\n"
            "TestSocks 1\n"
            "SafeLogging 1\n"
            "AvoidDiskWrites 1\n"
            f"Log notice file {log}\n",
            encoding="utf-8",
        )

        progress(41, f"Privater Tor-Paketkanal wird gestartet (Versuch {attempt}/2) …")
        process = subprocess.Popen(
            [tor, "-f", str(torrc)],
            cwd=str(Path(tor).resolve().parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            wait_tor_ready(socks_port, http_port, process, log, timeout=180.0)
            print(
                f"Lokaler Tor-Installationsproxy: http://127.0.0.1:{http_port} "
                f"(SOCKS 127.0.0.1:{socks_port})",
                flush=True,
            )
            print("Python-Abhängigkeiten werden ausschließlich über Tor geladen …", flush=True)
            run([
                str(python), "-m", "pip", "install",
                "--isolated",
                "--disable-pip-version-check",
                "--no-warn-script-location",
                "--retries", "5",
                "--timeout", "60",
                "--proxy", f"http://127.0.0.1:{http_port}",
                "--index-url", "https://pypi.org/simple",
                *PYTHON_DEPENDENCIES,
            ])
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)


def pip_install_over_tor(python: Path) -> None:
    tor = find_tor()
    if not tor:
        raise SystemExit(
            "Fehlende Python-Pakete müssen geladen werden, aber Tor wurde nicht gefunden.\n"
            "Installiere Tor/Tor Browser oder setze ONIONCALL_TOR_BINARY auf tor.exe.\n"
            "Es gibt absichtlich keinen automatischen Clearnet-Fallback. Alternativ explizit --allow-clearnet verwenden."
        )

    errors: list[str] = []
    for attempt in (1, 2):
        try:
            _run_tor_install_attempt(python, tor, attempt)
            return
        except (RuntimeError, TimeoutError, OSError) as exc:
            errors.append(str(exc))
            print(f"Tor-Paketkanal Versuch {attempt}/2 fehlgeschlagen: {exc}", flush=True)
            if attempt == 1:
                progress(43, "Tor-Paketkanal wird sauber neu gestartet …")
                time.sleep(1.0)

    raise SystemExit(
        "Der private Paketdownload über Tor konnte nach zwei sauberen Startversuchen nicht aufgebaut werden.\n"
        + "\n\n".join(errors[-2:])
        + "\n\nWenn dein Netzwerk Tor blockiert, kannst du entweder Tor/Bridges außerhalb des Setups konfigurieren "
          "oder den direkten Paketdownload im Browser-Installer ausdrücklich aktivieren."
    )


def _run_ffmpeg_tor_download_attempt(archive: Path, tor: str, attempt: int) -> None:
    with tempfile.TemporaryDirectory(prefix=f"onioncall-ffmpeg-tor-{attempt}-") as tmp:
        tmp_path = Path(tmp)
        data = tmp_path / "data"
        data.mkdir(mode=0o700)
        log = tmp_path / "tor.log"
        torrc = tmp_path / "torrc"
        socks_port = _free_loopback_port()
        http_port = _free_loopback_port()
        while http_port == socks_port:
            http_port = _free_loopback_port()
        torrc.write_text(
            f"DataDirectory {data}\n"
            f"SocksPort 127.0.0.1:{socks_port}\n"
            f"HTTPTunnelPort 127.0.0.1:{http_port}\n"
            "ClientOnly 1\nSafeSocks 1\nTestSocks 1\nSafeLogging 1\nAvoidDiskWrites 1\n"
            f"Log notice file {log}\n",
            encoding="utf-8",
        )
        progress(62, f"Tor für den privaten FFmpeg-Download wird gestartet (Versuch {attempt}/2) …")
        process = subprocess.Popen(
            [tor, "-f", str(torrc)],
            cwd=str(Path(tor).resolve().parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            wait_tor_ready(
                socks_port, http_port, process, log, timeout=180.0,
                ui_start=62, ui_span=5, ui_label="Tor wird für FFmpeg aufgebaut",
            )
            _download_verified(
                FFMPEG_WINDOWS_URL,
                FFMPEG_WINDOWS_SHA256,
                archive,
                proxy=f"http://127.0.0.1:{http_port}",
                progress_start=68,
                progress_end=76,
                label=f"FFmpeg {FFMPEG_VERSION} wird privat über Tor geladen …",
            )
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)


def install_windows_ffmpeg(*, allow_clearnet: bool) -> str | None:
    """Install a verified project-local FFmpeg bundle on Windows."""
    ffmpeg = find_ffmpeg_executable("ffmpeg")
    ffplay = find_ffmpeg_executable("ffplay")
    if ffmpeg and ffplay:
        print(f"FFmpeg/ffplay gefunden: {ffmpeg}", flush=True)
        return ffmpeg
    if os.name != "nt":
        return ffmpeg

    tools_root = PROJECT_ROOT / "tools"
    target = tools_root / "ffmpeg"
    tools_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="onioncall-ffmpeg-download-") as tmp:
        archive = Path(tmp) / f"ffmpeg-{FFMPEG_VERSION}-essentials.zip"
        if allow_clearnet:
            progress(62, f"FFmpeg {FFMPEG_VERSION} wird direkt per HTTPS geladen …")
            _download_verified(
                FFMPEG_WINDOWS_URL, FFMPEG_WINDOWS_SHA256, archive,
                progress_start=62, progress_end=76,
                label=f"FFmpeg {FFMPEG_VERSION} wird geladen …",
            )
        else:
            tor = find_tor()
            if not tor:
                raise RuntimeError("FFmpeg kann privat nicht geladen werden, weil Tor fehlt.")
            errors: list[str] = []
            for attempt in (1, 2):
                try:
                    _run_ffmpeg_tor_download_attempt(archive, tor, attempt)
                    break
                except (RuntimeError, TimeoutError, OSError) as exc:
                    errors.append(str(exc))
                    archive.unlink(missing_ok=True)
                    if attempt == 1:
                        progress(63, "FFmpeg-Tor-Download wird mit frischem Tor-Prozess wiederholt …")
                        time.sleep(1.0)
            else:
                raise RuntimeError(
                    "FFmpeg konnte nach zwei Versuchen nicht über Tor geladen werden.\n"
                    + "\n\n".join(errors[-2:])
                )

        progress(77, "FFmpeg-Download geprüft – wird projektlokal entpackt …")
        staging = tools_root / f".ffmpeg-install-{os.getpid()}"
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=False)
        try:
            _safe_extract_zip(archive, staging)
            exe_name = "ffmpeg.exe"
            play_name = "ffplay.exe"
            ffmpeg_candidates = list(staging.rglob(exe_name))
            ffplay_candidates = list(staging.rglob(play_name))
            if not ffmpeg_candidates or not ffplay_candidates:
                raise RuntimeError("FFmpeg-Archiv enthält ffmpeg.exe/ffplay.exe nicht wie erwartet.")
            shutil.rmtree(target, ignore_errors=True)
            staging.replace(target)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    ffmpeg = find_ffmpeg_executable("ffmpeg")
    ffplay = find_ffmpeg_executable("ffplay")
    if not ffmpeg or not ffplay:
        raise RuntimeError("FFmpeg wurde entpackt, aber die Programme konnten nicht gefunden werden.")
    for binary in (ffmpeg, ffplay):
        result = subprocess.run(
            [binary, "-version"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=12, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg-Funktionstest fehlgeschlagen: {binary}")
    progress(79, f"FFmpeg {FFMPEG_VERSION} ist für OnionCall-Audio bereit")
    print(f"FFmpeg projektlokal eingerichtet: {ffmpeg}", flush=True)
    return ffmpeg


def dependencies_missing(python: Path) -> bool:
    expected = repr(PINNED_DISTRIBUTIONS)
    code = (
        "import importlib.metadata as m, sys\n"
        f"expected={expected}\n"
        "bad=[]\n"
        "for name,want in expected.items():\n"
        "    try: got=m.version(name)\n"
        "    except m.PackageNotFoundError: got=None\n"
        "    if got != want: bad.append((name,got,want))\n"
        "sys.exit(1 if bad else 0)\n"
    )
    return subprocess.run(
        [str(python), "-c", code],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode != 0


def install_dependencies(python: Path, *, allow_clearnet: bool) -> None:
    if not dependencies_missing(python):
        print("Python-Abhängigkeiten sind bereits vorhanden und stimmen exakt mit den gepinnten Versionen überein.")
        return
    if allow_clearnet:
        print("Python-Abhängigkeiten werden direkt geladen (--allow-clearnet) …")
        run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "--no-warn-script-location", *PYTHON_DEPENDENCIES])
    else:
        pip_install_over_tor(python)


def initialize(root: Path, python: Path) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    run([str(python), "-m", "onioncall.cli", "init"], cwd=root, env=env)


def persist_tor_path(root: Path, python: Path) -> None:
    tor = find_tor()
    if not tor:
        return
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    code = f"from onioncall.config import load_config,save_config; c=load_config(); c.tor_binary={tor!r}; save_config(c)"
    run([str(python), "-c", code], cwd=root, env=env)


def install_windows_killswitch(root: Path, *, skip: bool) -> None:
    if os.name != "nt" or skip:
        return
    script = root / "scripts" / "onioncall-killswitch-windows.ps1"
    print("Windows-Killswitch wird eingerichtet. Windows kann eine UAC-Bestätigung anzeigen …")
    result = subprocess.run([
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(script), "install",
    ])
    if result.returncode != 0:
        raise SystemExit(
            "Windows-Killswitch konnte nicht eingerichtet werden oder UAC wurde abgebrochen. "
            "Mit --skip-killswitch kannst du bewusst ohne OS-Killswitch testen."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="BRZ – OnionCall Sicherheits-Setup 2.7.6")
    parser.add_argument("--allow-clearnet", action="store_true", help="fehlende Pakete ausdrücklich direkt laden")
    parser.add_argument("--skip-killswitch", action="store_true", help="Windows-Killswitch bewusst überspringen")
    args = parser.parse_args()
    root = PROJECT_ROOT
    ensure_supported_python()
    progress(5, "Python wird geprüft …")
    python = ensure_venv(root)
    progress(12, "Lokale Python-Umgebung ist bereit")
    if os.name == "nt" and not find_tor():
        bootstrap_windows_tor()
    elif find_tor():
        print(f"Tor gefunden: {find_tor()}", flush=True)
    progress(40, "Python-Abhängigkeiten werden geprüft …")
    install_dependencies(python, allow_clearnet=args.allow_clearnet)
    progress(61, "FFmpeg / Audio wird geprüft …")
    if os.name == "nt":
        try:
            install_windows_ffmpeg(allow_clearnet=args.allow_clearnet)
        except (RuntimeError, TimeoutError, OSError) as exc:
            print(f"WARNUNG: FFmpeg konnte nicht automatisch eingerichtet werden: {exc}", flush=True)
            print("Text/Chat bleibt nutzbar. Audio kann später durch erneutes Setup nachinstalliert werden.", flush=True)
            progress(79, "FFmpeg fehlt weiterhin – Text/Chat bleibt nutzbar")
    progress(80, "OnionCall wird initialisiert …")
    initialize(root, python)
    persist_tor_path(root, python)
    progress(88, "Betriebssystem-Killswitch wird eingerichtet …")
    install_windows_killswitch(root, skip=args.skip_killswitch)
    progress(100, "DONE – OnionCall ist vollständig eingerichtet")
    print("\nOnionCall wurde eingerichtet.")
    print("Start der GUI:      py Start-OnionCall.py")
    print("Terminal-Menü:      py Start-OnionCall-Terminal.py")
    print(f"Lokales Python:      {python}")
    if platform.system() == "Linux":
        print("Linux-Killswitch:    scripts/onioncall-killswitch-linux.sh --help")
    elif platform.system() == "Windows":
        print(r"Windows-Killswitch:  powershell -File scripts\onioncall-killswitch-windows.ps1 status")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
