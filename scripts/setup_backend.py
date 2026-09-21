#!/usr/bin/env python3
"""Sicheres Python-Setup für BRZ – OnionCall.

OnionCall bleibt ein Python-Projekt. Das Setup erstellt eine lokale virtuelle
Python-Umgebung, erzeugt keine OnionCall-.exe-Anwendung und lädt fehlende
Python-Pakete standardmäßig nur über Tor. Clearnet ist nur mit
--allow-clearnet möglich.
"""
from __future__ import annotations

import argparse
import os
import platform
import hashlib
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import venv
import tarfile
import urllib.request
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
PYTHON_DEPENDENCIES = ("cryptography>=42,<51", "prompt-toolkit>=3.0.52,<4")
PRIVATE_SOCKS_PORT = 19052

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOR_BUNDLE_VERSION = "15.0.23"
TOR_BUNDLE_URL = (
    "https://dist.torproject.org/torbrowser/15.0.23/"
    "tor-expert-bundle-windows-x86_64-15.0.23.tar.gz"
)
TOR_BUNDLE_SHA256 = "231dad6b9cb401a54c260db7046965ef04e4f72ff071b140d423fb5da281ab1e"


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
        request = urllib.request.Request(TOR_BUNDLE_URL, headers={"User-Agent": "OnionCall-Setup/2.7.3"})
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


def wait_socks(port: int, process: subprocess.Popen[bytes], log: Path, timeout: float = 180.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            detail = log.read_text(encoding="utf-8", errors="replace")[-1200:] if log.exists() else ""
            raise SystemExit("Tor wurde beim privaten Setup beendet. " + detail)
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                if log.exists() and "Bootstrapped 100%" in log.read_text(encoding="utf-8", errors="replace"):
                    return
        except OSError:
            pass
        time.sleep(0.25)
    raise SystemExit("Tor wurde für das private Setup nicht rechtzeitig bereit.")


def _load_tor_http_proxy():
    import importlib.util

    module_path = PROJECT_ROOT / "scripts" / "tor_http_proxy.py"
    spec = importlib.util.spec_from_file_location("onioncall_tor_http_proxy", module_path)
    if spec is None or spec.loader is None:
        raise SystemExit("Interner Tor-HTTP-Proxy konnte nicht geladen werden.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pip_install_over_tor(python: Path) -> None:
    tor = find_tor()
    if not tor:
        raise SystemExit(
            "Fehlende Python-Pakete müssen geladen werden, aber Tor wurde nicht gefunden.\n"
            "Installiere Tor/Tor Browser oder setze ONIONCALL_TOR_BINARY auf tor.exe.\n"
            "Es gibt absichtlich keinen automatischen Clearnet-Fallback. Alternativ explizit --allow-clearnet verwenden."
        )
    with tempfile.TemporaryDirectory(prefix="onioncall-setup-tor-") as tmp:
        tmp_path = Path(tmp)
        data = tmp_path / "data"
        data.mkdir(mode=0o700)
        log = tmp_path / "tor.log"
        torrc = tmp_path / "torrc"
        torrc.write_text(
            f"DataDirectory {data}\nSocksPort 127.0.0.1:{PRIVATE_SOCKS_PORT}\n"
            f"SafeSocks 1\nTestSocks 1\nSafeLogging 1\nLog notice file {log}\n",
            encoding="utf-8",
        )
        process = subprocess.Popen(
            [tor, "-f", str(torrc)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        bridge = None
        bridge_thread = None
        try:
            wait_socks(PRIVATE_SOCKS_PORT, process, log)
            proxy_module = _load_tor_http_proxy()
            bridge = proxy_module.TorHttpProxy(PRIVATE_SOCKS_PORT)
            bridge_thread = threading.Thread(target=bridge.serve_forever, name="onioncall-tor-http-proxy", daemon=True)
            bridge_thread.start()
            print(
                f"Lokaler Installations-Proxy: http://127.0.0.1:{bridge.port} -> Tor SOCKS 127.0.0.1:{PRIVATE_SOCKS_PORT}",
                flush=True,
            )
            print("Python-Abhängigkeiten werden ausschließlich über Tor geladen …", flush=True)
            run([
                str(python), "-m", "pip", "install",
                "--isolated",
                "--disable-pip-version-check",
                "--no-warn-script-location",
                "--proxy", f"http://127.0.0.1:{bridge.port}",
                "--index-url", "https://pypi.org/simple",
                *PYTHON_DEPENDENCIES,
            ])
        finally:
            if bridge is not None:
                bridge.shutdown()
                bridge.server_close()
            if bridge_thread is not None:
                bridge_thread.join(timeout=3)
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()


def dependencies_missing(python: Path) -> bool:
    return subprocess.run([str(python), "-c", "import cryptography, prompt_toolkit"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0


def install_dependencies(python: Path, *, allow_clearnet: bool) -> None:
    if not dependencies_missing(python):
        print("Python-Abhängigkeiten sind bereits vorhanden.")
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
    parser = argparse.ArgumentParser(description="BRZ – OnionCall Sicherheits-Setup")
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
    progress(68, "OnionCall wird initialisiert …")
    initialize(root, python)
    persist_tor_path(root, python)
    progress(82, "Betriebssystem-Killswitch wird eingerichtet …")
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
