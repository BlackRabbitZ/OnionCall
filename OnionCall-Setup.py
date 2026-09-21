#!/usr/bin/env python3
"""Lokaler grafischer Installer für BRZ – OnionCall.

Der Installer läuft ausschließlich auf 127.0.0.1. Die eigentliche
Installationslogik liegt in scripts/setup_backend.py. Die OnionCall-Haupt-GUI
wird dadurch nicht verändert.
"""
from __future__ import annotations

import json
import os
import platform
import secrets
import subprocess
import sys
import threading
import webbrowser
from collections import deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse



def _configure_utf8_stdio() -> None:
    """Use deterministic UTF-8 for redirected Windows console/pipe output."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


_configure_utf8_stdio()

MIN_PYTHON = (3, 10)
MAX_REQUEST = 16 * 1024
ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "scripts" / "setup_backend.py"


class InstallerError(RuntimeError):
    pass


def platform_label() -> str:
    if "com.termux" in os.environ.get("PREFIX", "") or "TERMUX_VERSION" in os.environ:
        return "Android / Termux"
    name = platform.system()
    return {"Windows": "Windows", "Darwin": "macOS", "Linux": "Linux"}.get(name, name)


class InstallState:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.events: deque[dict[str, object]] = deque(maxlen=1200)
        self.event_id = 0
        self.status = "ready"
        self.progress = 0
        self.detail = "Bereit zur Installation"
        self.error: str | None = None
        self.worker: threading.Thread | None = None

    def emit(self, message: str, kind: str = "log") -> None:
        if not message:
            return
        with self.lock:
            self.event_id += 1
            self.events.append({"id": self.event_id, "message": message, "kind": kind})

    def step(self, progress: int, detail: str) -> None:
        with self.lock:
            self.progress = max(0, min(100, progress))
            self.detail = detail
        self.emit(detail, "step")

    def snapshot(self, after: int = 0) -> dict[str, object]:
        with self.lock:
            return {
                "status": self.status,
                "progress": self.progress,
                "detail": self.detail,
                "error": self.error,
                "install_dir": str(ROOT),
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
            self.detail = "Installation wird vorbereitet …"
            self.worker = threading.Thread(target=self._install, name="onioncall-installer", daemon=True)
            self.worker.start()

    def _install(self) -> None:
        try:
            if sys.version_info < MIN_PYTHON:
                raise InstallerError("OnionCall benötigt Python 3.10 oder neuer")
            if not BACKEND.is_file():
                raise InstallerError("Setup-Backend fehlt: scripts/setup_backend.py")
            self.step(3, f"System erkannt: {platform_label()}")
            command = [sys.executable, "-u", str(BACKEND)]
            child_env = os.environ.copy()
            child_env["PYTHONIOENCODING"] = "utf-8"
            child_env["PYTHONUTF8"] = "1"
            process = subprocess.Popen(
                command,
                cwd=ROOT,
                env=child_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            assert process.stdout is not None
            try:
                for raw in process.stdout:
                    line = raw.rstrip("\r\n")
                    if line.startswith("::progress::"):
                        try:
                            _, _, value, message = line.split("::", 3)
                            self.step(int(value), message)
                        except (ValueError, IndexError):
                            self.emit(line)
                    else:
                        self.emit(line)
            finally:
                process.stdout.close()
            code = process.wait()
            if code != 0:
                raise InstallerError(f"Installation wurde mit Fehlercode {code} beendet")
            self.step(100, "DONE – OnionCall ist vollständig eingerichtet")
            with self.lock:
                self.status = "done"
        except (InstallerError, OSError, subprocess.SubprocessError) as exc:
            with self.lock:
                self.status = "error"
                self.error = str(exc)
                self.detail = "Installation fehlgeschlagen"
            self.emit(str(exc), "error")

    def launch(self) -> None:
        start = ROOT / "Start-OnionCall.py"
        if not start.is_file():
            raise InstallerError("Start-OnionCall.py wurde nicht gefunden")
        subprocess.Popen(
            [sys.executable, str(start)],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        self.emit("BRZ – OnionCall wurde gestartet.", "step")


INSTALL_HTML = r"""<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BRZ – OnionCall Setup</title><style nonce="__NONCE__">
:root{--bg:#090b10;--panel:#121722;--line:#30394b;--text:#f1f4f8;--muted:#96a2b3;--purple:#a98cff;--green:#68de91;--red:#ff7b84}*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(circle at 15% 0,#211a39,transparent 42%),var(--bg);color:var(--text);font:15px/1.55 system-ui,sans-serif;display:grid;place-items:center}.card{width:min(820px,calc(100% - 24px));background:#111620ee;border:1px solid var(--line);border-radius:20px;padding:26px;box-shadow:0 30px 90px #0009}.head{display:flex;align-items:center;gap:15px}.mark{width:62px;height:62px;border:1px solid #4a5570;border-radius:17px;display:grid;place-items:center;font-weight:900;font-size:20px;background:#191f2c}.head h1{margin:0;font-size:24px}.head p{margin:2px 0;color:var(--muted)}.system{margin:20px 0 8px;color:var(--muted)}.bar{height:12px;border-radius:99px;background:#080b10;overflow:hidden;border:1px solid var(--line)}.fill{height:100%;width:0;background:linear-gradient(90deg,#7255dd,var(--purple),#70dfbe);transition:.35s}.detail{display:flex;justify-content:space-between;margin:9px 0 16px}.detail span:last-child{color:var(--muted)}.log{height:300px;overflow:auto;background:#090c12;border:1px solid var(--line);border-radius:12px;padding:13px;font:12px/1.5 ui-monospace,monospace;white-space:pre-wrap}.log .error{color:#ff9da4}.log .step{color:#8ce6c2}.buttons{display:flex;gap:10px;justify-content:flex-end;margin-top:18px}button{border:1px solid #4a5570;background:#202737;color:var(--text);padding:12px 17px;border-radius:11px;font:inherit;font-weight:700;cursor:pointer}button.primary{background:linear-gradient(135deg,#8668ee,#6547ce);border-color:#b29cff}button:disabled{opacity:.45;cursor:not-allowed}.notice{margin-top:14px;color:var(--muted);font-size:12px}.done{color:var(--green);font-weight:800}.failure{color:var(--red);font-weight:800}@media(max-width:600px){.card{padding:18px}.log{height:240px}.buttons{flex-direction:column}button{width:100%}}
</style></head><body><main class="card"><div class="head"><div class="mark">BRZ</div><div><h1>BRZ – OnionCall Setup</h1><p>Geführte Installation für Windows, Linux, macOS und Android/Termux</p></div></div><div class="system" id="system">System wird erkannt …</div><div class="bar"><div class="fill" id="fill"></div></div><div class="detail"><strong id="detail">Bereit</strong><span id="percent">0 %</span></div><div class="log" id="log"></div><div class="buttons"><button class="primary" id="install">Installation starten</button><button class="primary" id="launch" disabled>BRZ – OnionCall öffnen</button></div><div class="notice">Wenn unter Windows noch kein Tor vorhanden ist, lädt das Setup einmalig das offizielle Tor Expert Bundle direkt vom Tor Project und prüft dessen SHA-256. Danach werden fehlende Python-Pakete über Tor geladen. Die OnionCall-Haupt-GUI wird nicht verändert.</div></main><script nonce="__NONCE__">
const TOKEN='__TOKEN__';let last=0;const $=x=>document.getElementById(x);async function api(p){const r=await fetch(p,{method:'POST',headers:{'Content-Type':'application/json','X-OnionCall-Token':TOKEN},body:'{}'});const j=await r.json();if(!r.ok)throw Error(j.error||'Fehler');return j}function add(e){const n=document.createElement('div');n.className=e.kind;n.textContent=e.message;$('log').append(n);$('log').scrollTop=$('log').scrollHeight}async function poll(){try{const r=await fetch('/api/status?after='+last,{cache:'no-store',headers:{'X-OnionCall-Token':TOKEN}}),s=await r.json();$('system').textContent='Erkannt: '+s.platform+' · Projekt: '+s.install_dir;$('fill').style.width=s.progress+'%';$('percent').textContent=s.progress+' %';$('detail').textContent=s.detail;$('detail').className=s.status==='done'?'done':s.status==='error'?'failure':'';s.events.forEach(add);last=s.last_event;$('install').disabled=s.status==='running'||s.status==='done';$('launch').disabled=s.status!=='done'}catch(e){}setTimeout(poll,650)}$('install').onclick=()=>api('/api/install').catch(e=>add({kind:'error',message:e.message}));$('launch').onclick=()=>api('/api/launch').catch(e=>add({kind:'error',message:e.message}));poll();
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

    def log_message(self, _format: str, *_args: object) -> None:
        pass

    def send_bytes(self, data: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header(
            "Content-Security-Policy",
            f"default-src 'none'; style-src 'nonce-{self.server.nonce}'; script-src 'nonce-{self.server.nonce}'; "
            "connect-src 'self'; base-uri 'none'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, value: object, status: int = 200) -> None:
        self.send_bytes(json.dumps(value, ensure_ascii=False).encode(), "application/json; charset=utf-8", status)

    def valid_host(self) -> bool:
        return self.headers.get("Host", "").split(":", 1)[0] in {"127.0.0.1", "localhost"}

    def authorized(self) -> bool:
        return secrets.compare_digest(self.headers.get("X-OnionCall-Token", ""), self.server.token)

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
            if not self.authorized():
                self.send_json({"error": "Nicht autorisiert"}, 403)
                return
            try:
                after = int(parse_qs(parsed.query).get("after", ["0"])[0])
            except ValueError:
                after = 0
            self.send_json(self.server.state.snapshot(max(0, after)))
            return
        self.send_json({"error": "Nicht gefunden"}, 404)

    def do_POST(self) -> None:
        if not self.valid_host() or not self.authorized():
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
            else:
                raise InstallerError("Unbekannte Aktion")
            self.send_json({"ok": True})
        except InstallerError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def valid_origin(self, origin: str) -> bool:
        try:
            parsed = urlparse(origin)
            return parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"} and parsed.port == self.server.server_address[1]
        except ValueError:
            return False


def open_browser(url: str) -> None:
    if not webbrowser.open(url, new=1):
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
