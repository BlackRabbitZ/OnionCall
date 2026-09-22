#!/usr/bin/env python3
"""Lokaler Browser-Installer für BRZ – OnionCall.

Die Weboberfläche bindet ausschließlich an 127.0.0.1. Schreibende API-Aufrufe
benötigen einen zufälligen, nur im URL-Fragment an den Browser übergebenen Token
und einen passenden Same-Origin-Header. Die eigentliche Installationslogik bleibt
in scripts/setup_backend.py und wird ohne Shell als Unterprozess ausgeführt.
"""
from __future__ import annotations

import json
import os
import platform
import secrets
import subprocess
import sys
import threading
import time
import webbrowser
from collections import deque
from contextlib import suppress
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from scripts import setup_backend

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAX_BODY = 16 * 1024
MAX_LOG_LINES = 500

HTML = r'''<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BRZ – OnionCall Setup</title>
<style nonce="__NONCE__">
:root{color-scheme:dark;--bg:#08080b;--panel:#111116;--panel2:#17171e;--line:#292934;--text:#f4f4f6;--muted:#9a9aa8;--red:#e33a46;--purple:#8e55ff;--green:#35d07f;--yellow:#f2be4b;--blue:#52a7ff}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 18% 0%,#251027 0,transparent 32%),radial-gradient(circle at 82% 8%,#16112d 0,transparent 28%),var(--bg);font-family:Inter,Segoe UI,system-ui,sans-serif;color:var(--text);min-height:100vh}
.wrap{max-width:1100px;margin:0 auto;padding:32px 22px 50px}.hero{display:flex;gap:18px;align-items:center;margin-bottom:24px}.logo{width:58px;height:58px;border-radius:18px;display:grid;place-items:center;background:linear-gradient(135deg,#301017,#1b122f);border:1px solid #4a2434;box-shadow:0 0 38px #9b244333;font-size:27px}.hero h1{margin:0;font-size:29px;letter-spacing:-.5px}.hero p{margin:6px 0 0;color:var(--muted)}
.grid{display:grid;grid-template-columns:1.35fr .65fr;gap:18px}@media(max-width:850px){.grid{grid-template-columns:1fr}}
.card{background:linear-gradient(180deg,#121217e8,#0d0d12e8);border:1px solid var(--line);border-radius:18px;padding:20px;box-shadow:0 15px 45px #0005}.card h2{font-size:16px;margin:0 0 16px}.checks{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:620px){.checks{grid-template-columns:1fr}}.check{display:flex;align-items:center;gap:11px;background:var(--panel2);border:1px solid #25252f;border-radius:12px;padding:12px 13px;min-height:58px}.dot{width:11px;height:11px;border-radius:50%;background:#555;box-shadow:0 0 0 4px #5552;flex:0 0 auto}.dot.ok{background:var(--green);box-shadow:0 0 0 4px #35d07f20,0 0 14px #35d07f66}.dot.warn{background:var(--yellow);box-shadow:0 0 0 4px #f2be4b20}.dot.bad{background:var(--red);box-shadow:0 0 0 4px #e33a4620}.dot.work{background:var(--blue);box-shadow:0 0 0 4px #52a7ff20;animation:pulse 1.2s infinite}@keyframes pulse{50%{opacity:.4}}.ct{min-width:0}.ct b{display:block;font-size:13px}.ct span{display:block;font-size:12px;color:var(--muted);margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.progressOuter{height:12px;background:#20202a;border-radius:999px;overflow:hidden;border:1px solid #2c2c36;margin:18px 0 9px}.progressInner{height:100%;width:0;background:linear-gradient(90deg,var(--red),var(--purple));transition:width .35s ease}.progressRow{display:flex;justify-content:space-between;gap:14px;color:var(--muted);font-size:12px}.opts{display:grid;gap:9px;margin-top:17px}.opt{display:flex;gap:10px;align-items:flex-start;color:#c5c5cf;font-size:13px}.opt input{margin-top:3px;accent-color:var(--purple)}.actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}.btn{border:0;border-radius:11px;padding:11px 16px;font-weight:700;cursor:pointer;color:white;background:linear-gradient(135deg,#b52c3d,#7138d4);box-shadow:0 8px 22px #6e284a35}.btn.secondary{background:#24242e;color:#e9e9ee;box-shadow:none;border:1px solid #343440}.btn:disabled{opacity:.45;cursor:not-allowed}.note{margin-top:14px;color:var(--muted);font-size:12px;line-height:1.5}.log{height:335px;overflow:auto;background:#07070a;border:1px solid #24242d;border-radius:12px;padding:13px;font:12px/1.5 Consolas,ui-monospace,monospace;color:#c8c8d1;white-space:pre-wrap;word-break:break-word}.tag{font-size:11px;padding:4px 8px;border-radius:999px;background:#262630;color:#babac6}.topline{display:flex;align-items:center;justify-content:space-between;gap:10px}.success{display:none;margin-top:15px;border:1px solid #2a6548;background:#0d281b;padding:12px;border-radius:12px;color:#aaf1c9}.error{display:none;margin-top:15px;border:1px solid #6d2c35;background:#2b0f14;padding:12px;border-radius:12px;color:#ffb7bd}.tiny{font-size:11px;color:#777784;margin-top:18px}
</style>
</head>
<body><div class="wrap">
<div class="hero"><div class="logo">◈</div><div><h1>BRZ – OnionCall Setup</h1><p>Sicherer lokaler Browser-Installer · nur 127.0.0.1 · OnionCall 2.7.6</p></div></div>
<div class="grid">
<section class="card"><div class="topline"><h2>System & Komponenten</h2><span id="platform" class="tag">Prüfe…</span></div><div id="checks" class="checks"></div>
<div class="progressOuter"><div id="bar" class="progressInner"></div></div><div class="progressRow"><span id="message">Bereit</span><span id="percent">0 %</span></div>
<div class="opts"><label class="opt"><input id="clearnet" type="checkbox"> <span><b>Direkten Paketdownload erlauben</b><br>Standardmäßig lädt OnionCall fehlende Python-Pakete und FFmpeg über Tor. Nur aktivieren, wenn du Clearnet ausdrücklich möchtest.</span></label><label class="opt"><input id="skipks" type="checkbox"> <span><b>Windows-Killswitch überspringen</b><br>Nicht empfohlen. Ohne Killswitch fehlt eine zusätzliche Betriebssystem-Schutzschicht.</span></label></div>
<div class="actions"><button id="install" class="btn">Installation starten</button><button id="refresh" class="btn secondary">Neu prüfen</button><button id="launch" class="btn secondary" disabled>OnionCall starten</button><button id="close" class="btn secondary">Installer schließen</button></div>
<div id="success" class="success">✓ OnionCall wurde vollständig eingerichtet und ist startbereit.</div><div id="error" class="error"></div>
<div class="note">FFmpeg ist für Audio notwendig und wird unter Windows automatisch projektlokal eingerichtet. Fehlt FFmpeg weiterhin, bleibt Text/Chat nutzbar; der Audio-Status bleibt dann gelb.</div></section>
<section class="card"><div class="topline"><h2>Installationsprotokoll</h2><span id="state" class="tag">idle</span></div><div id="log" class="log">Noch keine Installation gestartet.</div><div class="tiny">Das Protokoll bleibt lokal auf diesem Computer. Die Weboberfläche wird nicht im LAN freigegeben.</div></section>
</div></div>
<script nonce="__NONCE__">
'use strict';
const token=(location.hash||'').slice(1); history.replaceState(null,'',location.pathname);
const $=id=>document.getElementById(id); let lastLog='';
function esc(s){return String(s??'')}
async function api(path,opts={}){opts.headers=Object.assign({'X-OnionCall-Token':token},opts.headers||{});const r=await fetch(path,opts);let data={};try{data=await r.json()}catch(e){}if(!r.ok)throw new Error(data.error||('HTTP '+r.status));return data}
function renderCheck(c){const d=document.createElement('div');d.className='check';const dot=document.createElement('span');dot.className='dot '+(c.state||'warn');const t=document.createElement('div');t.className='ct';const b=document.createElement('b');b.textContent=c.label;const s=document.createElement('span');s.textContent=c.detail||'';t.append(b,s);d.append(dot,t);return d}
async function poll(){if(!token){$('error').style.display='block';$('error').textContent='Setup-Token fehlt. Starte OnionCall-Setup.py erneut.';return}try{const s=await api('/api/status');$('platform').textContent=s.platform;$('state').textContent=s.state;$('bar').style.width=(s.progress||0)+'%';$('percent').textContent=(s.progress||0)+' %';$('message').textContent=s.message||'Bereit';const box=$('checks');box.replaceChildren();(s.checks||[]).forEach(c=>box.appendChild(renderCheck(c)));const lg=(s.logs||[]).join('\n');if(lg!==lastLog){$('log').textContent=lg||'Noch keine Installation gestartet.';$('log').scrollTop=$('log').scrollHeight;lastLog=lg}const running=s.state==='running';$('install').disabled=running;$('refresh').disabled=running;$('clearnet').disabled=running;$('skipks').disabled=running;$('launch').disabled=!s.ready||running;$('success').style.display=s.state==='done'?'block':'none';$('error').style.display=s.state==='error'?'block':'none';if(s.state==='error')$('error').textContent=s.error||'Installation fehlgeschlagen.'}catch(e){$('error').style.display='block';$('error').textContent=e.message}finally{setTimeout(poll,750)}}
$('install').onclick=async()=>{try{$('error').style.display='none';await api('/api/install',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({allow_clearnet:$('clearnet').checked,skip_killswitch:$('skipks').checked})})}catch(e){$('error').style.display='block';$('error').textContent=e.message}};
$('refresh').onclick=async()=>{try{await api('/api/refresh',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})}catch(e){}};
$('launch').onclick=async()=>{try{await api('/api/launch',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});$('message').textContent='OnionCall wurde gestartet.'}catch(e){$('error').style.display='block';$('error').textContent=e.message}};
$('close').onclick=async()=>{try{await api('/api/shutdown',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});document.body.innerHTML='<div style="font-family:Segoe UI,sans-serif;background:#08080b;color:#eee;min-height:100vh;display:grid;place-items:center"><div><h2>Installer geschlossen</h2><p>Dieses Browserfenster kann jetzt geschlossen werden.</p></div></div>'}catch(e){window.close()}};
poll();
</script></body></html>'''


class InstallState:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.state = "idle"
        self.progress = 0
        self.message = "Bereit zur Installation"
        self.error = ""
        self.logs: deque[str] = deque(maxlen=MAX_LOG_LINES)
        self.process: subprocess.Popen[str] | None = None
        self.skip_killswitch = False
        self.refreshed_at = 0.0
        self.cached_checks: list[dict[str, str]] = []

    def log(self, line: str) -> None:
        clean = line.rstrip("\r\n")
        if clean:
            with self.lock:
                self.logs.append(clean)


STATE = InstallState()


def _venv_python() -> Path:
    return setup_backend.venv_python(PROJECT_ROOT)


def _has_exact_dependencies() -> bool:
    python = _venv_python()
    return python.is_file() and not setup_backend.dependencies_missing(python)


def _ffmpeg_detail() -> tuple[str, str]:
    ffmpeg = setup_backend.find_ffmpeg_executable("ffmpeg")
    ffplay = setup_backend.find_ffmpeg_executable("ffplay")
    if ffmpeg and ffplay:
        location = "projektlokal" if str(PROJECT_ROOT / "tools" / "ffmpeg") in ffmpeg else "System"
        return "ok", f"FFmpeg + ffplay bereit ({location})"
    if ffmpeg:
        return "warn", "FFmpeg gefunden, ffplay fehlt – wird beim Setup ergänzt"
    if os.name == "nt":
        return "warn", "Nicht gefunden – wird beim Setup automatisch installiert"
    return "warn", "Nicht gefunden – für Audio erforderlich"


def _killswitch_status() -> tuple[str, str]:
    if os.name != "nt":
        return "ok", "Unter diesem System nicht über den Windows-Killswitch verwaltet"
    script = PROJECT_ROOT / "scripts" / "onioncall-killswitch-windows.ps1"
    if not script.is_file():
        return "bad", "Killswitch-Skript fehlt"
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "status"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=7,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "warn", "Status konnte nicht automatisch geprüft werden"
    if result.returncode == 0:
        return "ok", "Aktiv – schützt die .venv dieses Projektordners"
    if result.returncode == 2:
        return "warn", "Veraltete Regel für einen anderen Projektordner – wird beim Setup ersetzt"
    return "warn", "Noch nicht aktiv – wird beim Setup eingerichtet"


def collect_checks(force: bool = False) -> list[dict[str, str]]:
    now = time.monotonic()
    with STATE.lock:
        if not force and STATE.cached_checks and now - STATE.refreshed_at < 6.0:
            return list(STATE.cached_checks)

    checks: list[dict[str, str]] = []
    py_ok = sys.version_info >= setup_backend.MIN_PYTHON
    checks.append({"label": "Python", "state": "ok" if py_ok else "bad", "detail": platform.python_version()})

    vp = _venv_python()
    checks.append({"label": "Virtuelle Umgebung", "state": "ok" if vp.is_file() else "warn", "detail": ".venv bereit" if vp.is_file() else "Wird beim Setup erstellt"})

    tor = setup_backend.find_tor()
    checks.append({"label": "Tor", "state": "ok" if tor else "warn", "detail": tor or ("Wird unter Windows automatisch eingerichtet" if os.name == "nt" else "Tor muss installiert sein")})

    dep_ok = False
    try:
        dep_ok = _has_exact_dependencies()
    except OSError:
        dep_ok = False
    checks.append({"label": "Python-Pakete", "state": "ok" if dep_ok else "warn", "detail": "Gepinnte Versionen vorhanden" if dep_ok else "Werden geprüft/installiert"})

    ff_state, ff_detail = _ffmpeg_detail()
    checks.append({"label": "FFmpeg / Audio", "state": ff_state, "detail": ff_detail})

    try:
        from onioncall.config import config_path
        cfg = config_path()
        cfg_ok = cfg.is_file()
        cfg_detail = str(cfg) if cfg_ok else "Wird beim Setup initialisiert"
    except Exception:
        cfg_ok = False
        cfg_detail = "Wird beim Setup initialisiert"
    checks.append({"label": "OnionCall-Konfiguration", "state": "ok" if cfg_ok else "warn", "detail": cfg_detail})

    ks_state, ks_detail = _killswitch_status()
    checks.append({"label": "OS-Killswitch", "state": ks_state, "detail": ks_detail})

    with STATE.lock:
        STATE.cached_checks = list(checks)
        STATE.refreshed_at = now
    return checks


def _run_install(allow_clearnet: bool, skip_killswitch: bool) -> None:
    with STATE.lock:
        STATE.state = "running"
        STATE.progress = 1
        STATE.message = "Installation wird gestartet …"
        STATE.error = ""
        STATE.logs.clear()
        STATE.skip_killswitch = skip_killswitch

    cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "setup_backend.py")]
    if allow_clearnet:
        cmd.append("--allow-clearnet")
    if skip_killswitch:
        cmd.append("--skip-killswitch")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    creationflags = 0
    startupinfo = None
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=creationflags,
            startupinfo=startupinfo,
        )
        with STATE.lock:
            STATE.process = proc
        assert proc.stdout is not None
        for line in proc.stdout:
            stripped = line.rstrip("\r\n")
            if stripped.startswith("::progress::"):
                parts = stripped.split("::", 3)
                try:
                    pct = max(0, min(100, int(parts[2])))
                    msg = parts[3] if len(parts) > 3 else "Installation läuft …"
                except (ValueError, IndexError):
                    STATE.log(stripped)
                else:
                    with STATE.lock:
                        STATE.progress = pct
                        STATE.message = msg
                    STATE.log(msg)
            else:
                STATE.log(stripped)
        rc = proc.wait()
        if rc == 0:
            with STATE.lock:
                STATE.state = "done"
                STATE.progress = 100
                STATE.message = "DONE – OnionCall ist vollständig eingerichtet"
                STATE.error = ""
        else:
            raise RuntimeError(f"Setup-Prozess wurde mit Exit-Code {rc} beendet.")
    except Exception as exc:
        STATE.log(f"FEHLER: {exc}")
        with STATE.lock:
            STATE.state = "error"
            STATE.error = str(exc)
            if not STATE.message:
                STATE.message = "Installation fehlgeschlagen"
    finally:
        with STATE.lock:
            STATE.process = None
            STATE.cached_checks = []
            STATE.refreshed_at = 0.0
        collect_checks(force=True)


def launch_onioncall() -> None:
    python = _venv_python()
    launcher = PROJECT_ROOT / "Start-OnionCall.py"
    if not python.is_file():
        raise RuntimeError("Lokales OnionCall-Python fehlt. Führe zuerst die Installation aus.")
    if not launcher.is_file():
        raise RuntimeError("Start-OnionCall.py fehlt.")
    kwargs: dict[str, Any] = {"cwd": PROJECT_ROOT, "stdin": subprocess.DEVNULL}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL
    subprocess.Popen([str(python), str(launcher)], **kwargs)


class SetupHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, server_address: tuple[str, int], token: str):
        self.token = token
        super().__init__(server_address, SetupHandler)

    @property
    def origin(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}"


class SetupHandler(BaseHTTPRequestHandler):
    server_version = "OnionCallSetup/2.7.6"

    def log_message(self, fmt: str, *args: object) -> None:
        return

    @property
    def app(self) -> SetupHTTPServer:
        return self.server  # type: ignore[return-value]

    def _secure_headers(self, content_type: str = "application/json; charset=utf-8") -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")

    def _host_ok(self) -> bool:
        expected = {f"127.0.0.1:{self.app.server_address[1]}", f"localhost:{self.app.server_address[1]}"}
        return self.headers.get("Host", "").lower() in expected

    def _client_ok(self) -> bool:
        return self.client_address[0] in {"127.0.0.1", "::1"}

    def _token_ok(self) -> bool:
        got = self.headers.get("X-OnionCall-Token", "")
        return bool(got) and secrets.compare_digest(got, self.app.token)

    def _origin_ok(self) -> bool:
        return self.headers.get("Origin", "") == self.app.origin

    def _authorized(self, *, write: bool = False) -> bool:
        return self._client_ok() and self._host_ok() and self._token_ok() and (not write or self._origin_ok())

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._secure_headers()
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict[str, Any]:
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Ungültige Content-Length") from exc
        if size < 0 or size > MAX_BODY:
            raise ValueError("Request ist zu groß")
        raw = self.rfile.read(size) if size else b"{}"
        obj = json.loads(raw.decode("utf-8"))
        if not isinstance(obj, dict):
            raise ValueError("JSON-Objekt erwartet")
        return obj

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            if not self._client_ok() or not self._host_ok():
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            nonce = secrets.token_urlsafe(18)
            data = HTML.replace("__NONCE__", nonce).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self._secure_headers("text/html; charset=utf-8")
            self.send_header(
                "Content-Security-Policy",
                f"default-src 'none'; style-src 'nonce-{nonce}'; script-src 'nonce-{nonce}'; "
                "connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
            )
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if self.path == "/api/status":
            if not self._authorized():
                self._json(HTTPStatus.FORBIDDEN, {"error": "Nicht autorisiert"})
                return
            checks = collect_checks()
            with STATE.lock:
                install_state = STATE.state
                skipped = STATE.skip_killswitch
                payload = {
                    "state": install_state,
                    "progress": STATE.progress,
                    "message": STATE.message,
                    "error": STATE.error,
                    "logs": list(STATE.logs),
                    "platform": f"{platform.system()} {platform.release()} · Python {platform.python_version()}",
                }
            by_label = {item["label"]: item["state"] for item in checks}
            critical = ["Python", "Virtuelle Umgebung", "Tor", "Python-Pakete", "OnionCall-Konfiguration"]
            ready = all(by_label.get(label) == "ok" for label in critical)
            if os.name == "nt" and not skipped and install_state != "done":
                ready = ready and by_label.get("OS-Killswitch") == "ok"
            payload["ready"] = ready and install_state != "running"
            payload["checks"] = checks
            self._json(HTTPStatus.OK, payload)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if not self._authorized(write=True):
            self._json(HTTPStatus.FORBIDDEN, {"error": "Nicht autorisiert"})
            return
        try:
            body = self._read_json()
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if self.path == "/api/install":
            with STATE.lock:
                if STATE.state == "running":
                    self._json(HTTPStatus.CONFLICT, {"error": "Installation läuft bereits"})
                    return
            allow = body.get("allow_clearnet", False)
            skip = body.get("skip_killswitch", False)
            if not isinstance(allow, bool) or not isinstance(skip, bool):
                self._json(HTTPStatus.BAD_REQUEST, {"error": "Ungültige Optionen"})
                return
            threading.Thread(target=_run_install, args=(allow, skip), name="onioncall-setup", daemon=True).start()
            self._json(HTTPStatus.ACCEPTED, {"ok": True})
            return

        if self.path == "/api/refresh":
            with STATE.lock:
                STATE.cached_checks = []
                STATE.refreshed_at = 0.0
            collect_checks(force=True)
            self._json(HTTPStatus.OK, {"ok": True})
            return

        if self.path == "/api/launch":
            try:
                launch_onioncall()
            except Exception as exc:
                self._json(HTTPStatus.CONFLICT, {"error": str(exc)})
                return
            self._json(HTTPStatus.OK, {"ok": True})
            return

        if self.path == "/api/shutdown":
            self._json(HTTPStatus.OK, {"ok": True})
            threading.Timer(0.2, self.app.shutdown).start()
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self._secure_headers()
        self.end_headers()


def create_server(token: str | None = None) -> SetupHTTPServer:
    return SetupHTTPServer(("127.0.0.1", 0), token or secrets.token_urlsafe(32))


def main() -> int:
    setup_backend.ensure_supported_python()
    server = create_server()
    url = f"{server.origin}/#{server.token}"
    if sys.stdout is not None:
        print(f"OnionCall Browser-Setup: {server.origin}/", flush=True)
        print("Die Installation wird im Browser durchgeführt. Dieses Fenster kann im Hintergrund bleiben.", flush=True)
    with suppress(Exception):
        webbrowser.open(url, new=1, autoraise=True)
    with suppress(KeyboardInterrupt):
        server.serve_forever(poll_interval=0.25)
    server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
