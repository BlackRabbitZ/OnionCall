#!/usr/bin/env python3
"""One-file graphical installer for OnionCall.

Requires Python 3.10 or newer. The installer binds only to 127.0.0.1 and opens
its progress interface in the local browser.
"""

from __future__ import annotations

import json
import os
import platform
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import threading
import webbrowser
from collections import deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

REPOSITORY = "https://github.com/BlackRabbitZ/OnionCall.git"
MIN_PYTHON = (3, 10)
MIN_REPOSITORY_VERSION = (2, 2, 0)
MAX_REQUEST = 16 * 1024


def is_termux() -> bool:
    return "com.termux" in os.environ.get("PREFIX", "") or "TERMUX_VERSION" in os.environ


def install_root() -> Path:
    override = os.environ.get("ONIONCALL_INSTALL_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "OnionCall"
    return Path.home() / ".local" / "share" / "onioncall"


class InstallerError(RuntimeError):
    pass


class InstallState:
    def __init__(self):
        self.lock = threading.RLock()
        self.events: deque[dict[str, object]] = deque(maxlen=800)
        self.event_id = 0
        self.status = "ready"
        self.progress = 0
        self.detail = "Bereit zur Installation"
        self.error: str | None = None
        self.worker: threading.Thread | None = None
        self.root = install_root()

    def emit(self, message: str, kind: str = "log") -> None:
        with self.lock:
            self.event_id += 1
            self.events.append({"id": self.event_id, "message": message, "kind": kind})

    def step(self, progress: int, detail: str) -> None:
        with self.lock:
            self.progress = progress
            self.detail = detail
        self.emit(detail, "step")

    def snapshot(self, after: int = 0) -> dict[str, object]:
        with self.lock:
            return {
                "status": self.status,
                "progress": self.progress,
                "detail": self.detail,
                "error": self.error,
                "install_dir": str(self.root / "source"),
                "events": [event for event in self.events if int(event["id"]) > after],
                "last_event": self.event_id,
                "platform": platform_label(),
            }

    def start(self) -> None:
        with self.lock:
            if self.worker and self.worker.is_alive():
                raise InstallerError("Die Installation läuft bereits")
            self.status = "running"
            self.error = None
            self.progress = 1
            self.worker = threading.Thread(target=self._install, name="onioncall-installer", daemon=True)
            self.worker.start()

    def _install(self) -> None:
        try:
            if sys.version_info < MIN_PYTHON:
                raise InstallerError("OnionCall benötigt Python 3.10 oder neuer")
            self.step(5, f"System erkannt: {platform_label()}")
            install_system_packages(self)
            self.step(35, "Repository wird geladen oder aktualisiert …")
            source = clone_or_update(self)
            self.step(55, "Abgeschlossene Python-Umgebung wird eingerichtet …")
            venv = create_venv(source, self)
            self.step(70, "OnionCall und Python-Abhängigkeiten werden installiert …")
            install_python_package(source, venv, self)
            self.step(85, "Starter werden eingerichtet …")
            create_launchers(source, venv, self)
            self.step(93, "Installation wird geprüft …")
            verify_install(venv, self)
            self.step(100, "DONE – OnionCall ist vollständig installiert")
            with self.lock:
                self.status = "done"
        except (InstallerError, OSError, subprocess.SubprocessError) as exc:
            with self.lock:
                self.status = "error"
                self.error = str(exc)
                self.detail = "Installation fehlgeschlagen"
            self.emit(str(exc), "error")

    def launch(self) -> None:
        executable = venv_executable(self.root / "venv", "onioncall")
        if not executable.exists():
            raise InstallerError("OnionCall ist noch nicht installiert")
        subprocess.Popen(
            [str(executable), "gui"],
            cwd=self.root / "source",
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        self.emit("OnionCall GUI wurde gestartet.", "step")


def platform_label() -> str:
    if is_termux():
        return "Android / Termux"
    if platform.system() == "Darwin":
        return "macOS"
    manager = package_manager()
    names = {"dnf": "Fedora", "apt-get": "Debian / Ubuntu / Raspberry Pi OS", "pacman": "Arch Linux"}
    return names.get(manager, platform.system())


def package_manager() -> str | None:
    if is_termux():
        return "pkg"
    if platform.system() == "Darwin":
        return "brew" if shutil.which("brew") else None
    for manager in ("dnf", "apt-get", "pacman"):
        if shutil.which(manager):
            return manager
    return None


def required_commands() -> list[str]:
    if is_termux():
        return ["git", "tor", "opusenc", "opusdec", "ffmpeg", "termux-microphone-record", "play"]
    if platform.system() == "Darwin":
        return ["git", "tor", "opusenc", "opusdec", "rec", "play"]
    return ["git", "tor", "opusenc", "opusdec", "arecord", "aplay"]


def package_command(manager: str) -> list[list[str]]:
    if manager == "pkg":
        return [
            ["pkg", "update", "-y"],
            [
                "pkg",
                "install",
                "-y",
                "git",
                "python",
                "python-cryptography",
                "tor",
                "opus-tools",
                "sox",
                "ffmpeg",
                "termux-api",
            ]
        ]
    if manager == "dnf":
        return [["dnf", "install", "-y", "git", "python3", "python3-pip", "tor", "opus-tools", "alsa-utils"]]
    if manager == "apt-get":
        return [
            ["apt-get", "update"],
            [
                "apt-get",
                "install",
                "-y",
                "git",
                "python3",
                "python3-venv",
                "python3-pip",
                "tor",
                "opus-tools",
                "alsa-utils",
            ],
        ]
    if manager == "pacman":
        return [["pacman", "-S", "--needed", "--noconfirm", "git", "python", "tor", "opus-tools", "alsa-utils"]]
    if manager == "brew":
        return [["brew", "install", "git", "python", "tor", "opus-tools", "sox"]]
    raise InstallerError("Nicht unterstützter Paketmanager")


def elevated(command: list[str]) -> list[str]:
    if is_termux() or platform.system() == "Darwin" or (hasattr(os, "geteuid") and os.geteuid() == 0):
        return command
    if shutil.which("pkexec"):
        return ["pkexec", *command]
    if shutil.which("sudo") and sys.stdin.isatty():
        return ["sudo", *command]
    raise InstallerError(
        "Für die Systempakete ist eine Administratorfreigabe nötig. "
        "Starte die Setup-Datei aus einem Terminal oder installiere `pkexec`."
    )


def run(command: list[str], state: InstallState, *, cwd: Path | None = None, elevate: bool = False) -> None:
    actual = elevated(command) if elevate else command
    state.emit("$ " + shlex.join(command))
    process = subprocess.Popen(
        actual,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    assert process.stdout is not None
    for line in process.stdout:
        text = line.rstrip()
        if text:
            state.emit(text)
    if process.wait() != 0:
        raise InstallerError(f"Befehl fehlgeschlagen: {shlex.join(command)}")


def install_system_packages(state: InstallState) -> None:
    missing = [command for command in required_commands() if shutil.which(command) is None]
    if not missing:
        state.step(25, "Tor, Git und Audio-Werkzeuge sind bereits installiert")
        return
    manager = package_manager()
    if manager is None and platform.system() == "Darwin":
        raise InstallerError(
            "Homebrew fehlt. Installiere zuerst Homebrew von https://brew.sh und starte diese Datei danach erneut. "
            "Das Setup führt aus Sicherheitsgründen kein ungeprüftes Internetskript mit Administratorrechten aus."
        )
    if manager is None:
        raise InstallerError("Kein unterstützter Paketmanager gefunden (dnf, apt, pacman, Homebrew oder Termux pkg)")
    state.step(12, "Fehlende Systempakete werden installiert: " + ", ".join(missing))
    for command in package_command(manager):
        run(command, state, elevate=manager in {"dnf", "apt-get", "pacman"})
    still_missing = [command for command in required_commands() if shutil.which(command) is None]
    if still_missing:
        raise InstallerError("Nach der Paketinstallation fehlen weiterhin: " + ", ".join(still_missing))
    state.step(25, "Systempakete vollständig")


def clone_or_update(state: InstallState) -> Path:
    source = state.root / "source"
    state.root.mkdir(parents=True, exist_ok=True)
    if (source / ".git").is_dir():
        try:
            origin = subprocess.run(
                ["git", "-C", str(source), "remote", "get-url", "origin"],
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            ).stdout.strip()
        except subprocess.SubprocessError as exc:
            raise InstallerError("Vorhandenes Repository konnte nicht geprüft werden") from exc
        if origin.rstrip("/") != REPOSITORY.rstrip("/"):
            raise InstallerError(f"Unerwartete Repository-Quelle im Installationsordner: {origin}")
        run(["git", "-C", str(source), "pull", "--ff-only"], state)
    elif source.exists() and any(source.iterdir()):
        raise InstallerError(f"Installationsordner ist nicht leer und kein Git-Repository: {source}")
    else:
        source.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--depth", "1", REPOSITORY, str(source)], state)
    if not (source / "pyproject.toml").is_file():
        raise InstallerError("Das geladene Repository enthält keine pyproject.toml")
    if not (source / "onioncall" / "webgui.py").is_file():
        raise InstallerError(
            "Das GitHub-Repository enthält noch nicht die neue OnionCall-GUI. "
            "Lade zuerst den aktuellen Repository-Download in GitHub hoch und starte das Setup danach erneut."
        )
    project_text = (source / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"(\d+)\.(\d+)\.(\d+)"', project_text, re.MULTILINE)
    version = tuple(int(part) for part in match.groups()) if match else (0, 0, 0)
    if version < MIN_REPOSITORY_VERSION:
        raise InstallerError("Das GitHub-Repository ist älter als OnionCall 2.2.0 und muss zuerst aktualisiert werden")
    return source


def venv_executable(venv: Path, name: str) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / (name + ".exe")
    return venv / "bin" / name


def create_venv(source: Path, state: InstallState) -> Path:
    venv = state.root / "venv"
    if not venv_executable(venv, "python").exists():
        command = [sys.executable, "-m", "venv"]
        if is_termux():
            command.append("--system-site-packages")
        command.append(str(venv))
        run(command, state, cwd=source)
    return venv


def install_python_package(source: Path, venv: Path, state: InstallState) -> None:
    python = venv_executable(venv, "python")
    if not is_termux():
        run([str(python), "-m", "pip", "install", "--upgrade", "pip"], state, cwd=source)
    run([str(python), "-m", "pip", "install", "--upgrade", "."], state, cwd=source)


def private_write(path: Path, text: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o700 if executable else 0o600)


def create_launchers(source: Path, venv: Path, state: InstallState) -> None:
    onioncall = venv_executable(venv, "onioncall")
    launcher = Path.home() / ".local" / "bin" / "onioncall-gui"
    launcher_text = (
        f"#!/bin/sh\ncd {shlex.quote(str(source))}\n"
        f"exec {shlex.quote(str(onioncall))} gui \"$@\"\n"
    )
    private_write(launcher, launcher_text, True)
    state.emit(f"Starter erstellt: {launcher}")
    if is_termux():
        shortcut_dir = Path.home() / ".shortcuts"
        if shortcut_dir.exists():
            private_write(shortcut_dir / "OnionCall", f"#!/bin/sh\nexec {shlex.quote(str(onioncall))} gui\n", True)
    elif platform.system() == "Darwin":
        command = Path.home() / "Applications" / "OnionCall.command"
        private_write(command, f"#!/bin/sh\nexec {shlex.quote(str(onioncall))} gui\n", True)
        state.emit(f"macOS-Starter erstellt: {command}")
    else:
        desktop = Path.home() / ".local" / "share" / "applications" / "onioncall.desktop"
        private_write(
            desktop,
            "[Desktop Entry]\nType=Application\nName=OnionCall\nComment=Sicherer Text und Sprache über Tor\n"
            f"Exec={onioncall} gui\nTerminal=false\nCategories=Network;Chat;Security;\n",
        )
        desktop.chmod(0o644)
        state.emit(f"Anwendungsstarter erstellt: {desktop}")


def verify_install(venv: Path, state: InstallState) -> None:
    onioncall = venv_executable(venv, "onioncall")
    run([str(onioncall), "--version"], state)
    process = subprocess.run([str(onioncall), "doctor"], text=True, capture_output=True)
    for line in (process.stdout + process.stderr).splitlines():
        state.emit(line)
    # Ein noch nicht erzeugter Verbindungsschlüssel ist vor dem ersten GUI-Start normal.
    if "[FEHLT]" in process.stdout:
        raise InstallerError("Die Diagnose meldet fehlende Systemprogramme")


INSTALL_HTML = r'''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>OnionCall Setup</title><style nonce="__NONCE__">
:root{--bg:#090b10;--panel:#121722;--line:#30394b;--text:#f1f4f8;--muted:#96a2b3;--purple:#a98cff;--green:#68de91;--red:#ff7b84}*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(circle at 15% 0,#211a39,transparent 42%),var(--bg);color:var(--text);font:15px/1.55 system-ui,sans-serif;display:grid;place-items:center}.card{width:min(790px,calc(100% - 24px));background:#111620ee;border:1px solid var(--line);border-radius:20px;padding:26px;box-shadow:0 30px 90px #0009}.head{display:flex;align-items:center;gap:15px}.logo{width:54px;height:54px;border-radius:16px;background:linear-gradient(135deg,var(--purple),#6548d3);display:grid;place-items:center;color:#100b1b;font-size:28px;font-weight:900}.head h1{margin:0;font-size:24px}.head p{margin:2px 0;color:var(--muted)}.system{margin:20px 0 8px;color:var(--muted)}.bar{height:12px;border-radius:99px;background:#080b10;overflow:hidden;border:1px solid var(--line)}.fill{height:100%;width:0;background:linear-gradient(90deg,#7255dd,var(--purple),#70dfbe);transition:.35s}.detail{display:flex;justify-content:space-between;margin:9px 0 16px}.detail span:last-child{color:var(--muted)}.log{height:270px;overflow:auto;background:#090c12;border:1px solid var(--line);border-radius:12px;padding:13px;font:12px/1.5 ui-monospace,monospace;white-space:pre-wrap}.log .error{color:#ff9da4}.log .step{color:#8ce6c2}.buttons{display:flex;gap:10px;justify-content:flex-end;margin-top:18px}button{border:1px solid #4a5570;background:#202737;color:var(--text);padding:12px 17px;border-radius:11px;font:inherit;font-weight:700;cursor:pointer}button.primary{background:linear-gradient(135deg,#8668ee,#6547ce);border-color:#b29cff}button:disabled{opacity:.45;cursor:not-allowed}.notice{margin-top:14px;color:var(--muted);font-size:12px}.done{color:var(--green);font-weight:800}.failure{color:var(--red);font-weight:800}@media(max-width:600px){.card{padding:18px}.log{height:230px}.buttons{flex-direction:column}button{width:100%}}
</style></head><body><main class="card"><div class="head"><div class="logo">O</div><div><h1>OnionCall Setup</h1><p>Geführte Installation für Linux, macOS und Android/Termux</p></div></div><div class="system" id="system">System wird erkannt …</div><div class="bar"><div class="fill" id="fill"></div></div><div class="detail"><strong id="detail">Bereit</strong><span id="percent">0 %</span></div><div class="log" id="log"></div><div class="buttons"><button class="primary" id="install">Installation starten</button><button class="primary" id="launch" disabled>OnionCall öffnen</button></div><div class="notice">Die Oberfläche läuft ausschließlich lokal auf diesem Gerät. Administratorfreigaben erfolgen über den Systemdialog oder das Terminal; dein Passwort wird nicht von OnionCall gelesen oder gespeichert.</div></main><script nonce="__NONCE__">
const TOKEN='__TOKEN__';let last=0;const $=x=>document.getElementById(x);async function api(p){const r=await fetch(p,{method:'POST',headers:{'Content-Type':'application/json','X-OnionCall-Token':TOKEN},body:'{}'});const j=await r.json();if(!r.ok)throw Error(j.error||'Fehler');return j}function add(e){const n=document.createElement('div');n.className=e.kind;n.textContent=e.message;$('log').append(n);$('log').scrollTop=$('log').scrollHeight}async function poll(){try{const r=await fetch('/api/status?after='+last,{cache:'no-store'}),s=await r.json();$('system').textContent='Erkannt: '+s.platform+' · Ziel: '+s.install_dir;$('fill').style.width=s.progress+'%';$('percent').textContent=s.progress+' %';$('detail').textContent=s.detail;$('detail').className=s.status==='done'?'done':s.status==='error'?'failure':'';s.events.forEach(add);last=s.last_event;$('install').disabled=s.status==='running'||s.status==='done';$('launch').disabled=s.status!=='done'}catch(e){}setTimeout(poll,650)}$('install').onclick=()=>api('/api/install').catch(e=>add({kind:'error',message:e.message}));$('launch').onclick=()=>api('/api/launch').catch(e=>add({kind:'error',message:e.message}));poll();
</script></body></html>'''


class SetupServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, state: InstallState):
        super().__init__(("127.0.0.1", 0), SetupHandler)
        self.state = state
        self.token = secrets.token_urlsafe(32)
        self.nonce = secrets.token_urlsafe(18)
        self.origin = f"http://127.0.0.1:{self.server_address[1]}"


class SetupHandler(BaseHTTPRequestHandler):
    server: SetupServer
    protocol_version = "HTTP/1.1"

    def log_message(self, _format, *_args) -> None:
        pass

    def send_bytes(self, data: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            f"default-src 'none'; style-src 'nonce-{self.server.nonce}'; "
            f"script-src 'nonce-{self.server.nonce}'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, value: object, status: int = 200) -> None:
        self.send_bytes(json.dumps(value, ensure_ascii=False).encode(), "application/json; charset=utf-8", status)

    def valid_host(self) -> bool:
        return self.headers.get("Host", "").split(":", 1)[0] in {"127.0.0.1", "localhost"}

    def do_GET(self) -> None:
        if not self.valid_host():
            self.send_json({"error": "Ungültiger Host"}, 403)
            return
        parsed = urlparse(self.path)
        if parsed.path == "/":
            html = INSTALL_HTML.replace("__TOKEN__", self.server.token).replace("__NONCE__", self.server.nonce).encode()
            self.send_bytes(html, "text/html; charset=utf-8")
            return
        if parsed.path == "/api/status":
            try:
                after = int((parsed.query.split("after=", 1)[1] if "after=" in parsed.query else "0").split("&", 1)[0])
            except ValueError:
                after = 0
            self.send_json(self.server.state.snapshot(max(0, after)))
            return
        self.send_json({"error": "Nicht gefunden"}, 404)

    def do_POST(self) -> None:
        if not self.valid_host() or not secrets.compare_digest(
            self.headers.get("X-OnionCall-Token", ""), self.server.token
        ):
            self.send_json({"error": "Nicht autorisiert"}, 403)
            return
        origin = self.headers.get("Origin")
        if origin and not self.valid_origin(origin):
            self.send_json({"error": "Ungültiger Ursprung"}, 403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = MAX_REQUEST + 1
        if not 0 <= length <= MAX_REQUEST:
            self.send_json({"error": "Anfrage zu groß"}, 413)
            return
        self.rfile.read(length)
        try:
            path = urlparse(self.path).path
            if path == "/api/install":
                self.server.state.start()
            elif path == "/api/launch":
                self.server.state.launch()
                threading.Timer(1.0, self.server.shutdown).start()
            else:
                raise InstallerError("Unbekannte Aktion")
            self.send_json({"ok": True})
        except InstallerError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def valid_origin(self, origin: str) -> bool:
        try:
            parsed = urlparse(origin)
            return (
                parsed.scheme == "http"
                and parsed.hostname in {"127.0.0.1", "localhost"}
                and parsed.port == self.server.server_address[1]
            )
        except ValueError:
            return False


def open_browser(url: str) -> None:
    if is_termux() and shutil.which("termux-open-url"):
        subprocess.Popen(["termux-open-url", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif not webbrowser.open(url, new=1):
        print(f"Öffne diese Adresse im Browser: {url}")


def main() -> int:
    if sys.version_info < MIN_PYTHON:
        print("OnionCall Setup benötigt Python 3.10 oder neuer.", file=sys.stderr)
        return 1
    state = InstallState()
    server = SetupServer(state)
    print(f"OnionCall Setup läuft lokal unter {server.origin}")
    threading.Timer(0.4, open_browser, args=(server.origin,)).start()
    try:
        server.serve_forever(poll_interval=0.4)
    except KeyboardInterrupt:
        print("\nSetup beendet.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
