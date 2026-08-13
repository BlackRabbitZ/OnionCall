#!/usr/bin/env python3
"""One-file graphical installer for OnionCall.

Requires Python 3.10 or newer. The installer binds only to 127.0.0.1 and opens
its progress interface in the local browser.
"""

from __future__ import annotations

import base64
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
MIN_REPOSITORY_VERSION = (2, 5, 0)
MAX_REQUEST = 16 * 1024
ICON_PNG = base64.b64decode(
    "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"
)


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
        self.emit("BRZ – OnionCall GUI wurde gestartet.", "step")


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
            ],
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
        raise InstallerError("Das GitHub-Repository ist älter als BRZ – OnionCall 2.5.0 und muss aktualisiert werden")
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
    launcher_text = f'#!/bin/sh\ncd {shlex.quote(str(source))}\nexec {shlex.quote(str(onioncall))} gui "$@"\n'
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
        icon = source / "onioncall" / "assets" / "onioncall-icon.png"
        private_write(
            desktop,
            "[Desktop Entry]\nType=Application\nName=BRZ - OnionCall\nComment=Sicherer Text und Sprache über Tor\n"
            f"Exec={onioncall} gui\nIcon={icon}\nTerminal=false\nCategories=Network;Chat;Security;\n",
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


INSTALL_HTML = r"""<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" type="image/png" href="/icon.png"><title>BRZ – OnionCall Setup</title><style nonce="__NONCE__">
:root{--bg:#090b10;--panel:#121722;--line:#30394b;--text:#f1f4f8;--muted:#96a2b3;--purple:#a98cff;--green:#68de91;--red:#ff7b84}*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(circle at 15% 0,#211a39,transparent 42%),var(--bg);color:var(--text);font:15px/1.55 system-ui,sans-serif;display:grid;place-items:center}.card{width:min(790px,calc(100% - 24px));background:#111620ee;border:1px solid var(--line);border-radius:20px;padding:26px;box-shadow:0 30px 90px #0009}.head{display:flex;align-items:center;gap:15px}.logo{width:62px;height:62px;object-fit:contain;filter:drop-shadow(0 10px 16px #8d6cff55)}.head h1{margin:0;font-size:24px}.head p{margin:2px 0;color:var(--muted)}.system{margin:20px 0 8px;color:var(--muted)}.bar{height:12px;border-radius:99px;background:#080b10;overflow:hidden;border:1px solid var(--line)}.fill{height:100%;width:0;background:linear-gradient(90deg,#7255dd,var(--purple),#70dfbe);transition:.35s}.detail{display:flex;justify-content:space-between;margin:9px 0 16px}.detail span:last-child{color:var(--muted)}.log{height:270px;overflow:auto;background:#090c12;border:1px solid var(--line);border-radius:12px;padding:13px;font:12px/1.5 ui-monospace,monospace;white-space:pre-wrap}.log .error{color:#ff9da4}.log .step{color:#8ce6c2}.buttons{display:flex;gap:10px;justify-content:flex-end;margin-top:18px}button{border:1px solid #4a5570;background:#202737;color:var(--text);padding:12px 17px;border-radius:11px;font:inherit;font-weight:700;cursor:pointer}button.primary{background:linear-gradient(135deg,#8668ee,#6547ce);border-color:#b29cff}button:disabled{opacity:.45;cursor:not-allowed}.notice{margin-top:14px;color:var(--muted);font-size:12px}.done{color:var(--green);font-weight:800}.failure{color:var(--red);font-weight:800}@media(max-width:600px){.card{padding:18px}.log{height:230px}.buttons{flex-direction:column}button{width:100%}}
</style></head><body><main class="card"><div class="head"><img class="logo" src="/icon.png" alt="BlackRabbitZ OnionChat"><div><h1>BRZ – OnionCall Setup</h1><p>Geführte Installation für Linux, macOS und Android/Termux</p></div></div><div class="system" id="system">System wird erkannt …</div><div class="bar"><div class="fill" id="fill"></div></div><div class="detail"><strong id="detail">Bereit</strong><span id="percent">0 %</span></div><div class="log" id="log"></div><div class="buttons"><button class="primary" id="install">Installation starten</button><button class="primary" id="launch" disabled>BRZ – OnionCall öffnen</button></div><div class="notice">Die Oberfläche läuft ausschließlich lokal auf diesem Gerät. Administratorfreigaben erfolgen über den Systemdialog oder das Terminal; dein Passwort wird nicht von OnionCall gelesen oder gespeichert.</div></main><script nonce="__NONCE__">
const TOKEN='__TOKEN__';let last=0;const $=x=>document.getElementById(x);async function api(p){const r=await fetch(p,{method:'POST',headers:{'Content-Type':'application/json','X-OnionCall-Token':TOKEN},body:'{}'});const j=await r.json();if(!r.ok)throw Error(j.error||'Fehler');return j}function add(e){const n=document.createElement('div');n.className=e.kind;n.textContent=e.message;$('log').append(n);$('log').scrollTop=$('log').scrollHeight}async function poll(){try{const r=await fetch('/api/status?after='+last,{cache:'no-store'}),s=await r.json();$('system').textContent='Erkannt: '+s.platform+' · Ziel: '+s.install_dir;$('fill').style.width=s.progress+'%';$('percent').textContent=s.progress+' %';$('detail').textContent=s.detail;$('detail').className=s.status==='done'?'done':s.status==='error'?'failure':'';s.events.forEach(add);last=s.last_event;$('install').disabled=s.status==='running'||s.status==='done';$('launch').disabled=s.status!=='done'}catch(e){}setTimeout(poll,650)}$('install').onclick=()=>api('/api/install').catch(e=>add({kind:'error',message:e.message}));$('launch').onclick=()=>api('/api/launch').catch(e=>add({kind:'error',message:e.message}));poll();
</script></body></html>"""


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
            f"script-src 'nonce-{self.server.nonce}'; connect-src 'self'; img-src 'self'; "
            "base-uri 'none'; frame-ancestors 'none'",
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
        if parsed.path in {"/icon.png", "/favicon.ico"}:
            self.send_bytes(ICON_PNG, "image/png")
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
        print("BRZ – OnionCall Setup benötigt Python 3.10 oder neuer.", file=sys.stderr)
        return 1
    state = InstallState()
    server = SetupServer(state)
    print(f"BRZ – OnionCall Setup läuft lokal unter {server.origin}")
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
