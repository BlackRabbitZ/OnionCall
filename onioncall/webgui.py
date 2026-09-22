from __future__ import annotations

import json
import platform
import secrets
import shutil
import socket
import threading
import time
import webbrowser
from collections import deque
from contextlib import suppress
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import parse_qs, urlparse

from . import __version__
from .audio import AudioBackend, AudioError, is_termux, missing_audio_commands
from .config import (
    app_home,
    ConfigError,
    ensure_private_dir,
    generate_secret,
    load_config,
    save_config,
)
from .gui_session import GuiSession
from .identity import load_or_create_identity
from .listener import accept_authenticated
from .peers import (
    import_peer_secret,
    list_peers,
    load_peer,
    peer_secret_token,
    pin_peer_fingerprint,
    set_peer_onion,
)
from .protocol import perform_client_handshake
from .tor import socks5_connect, TorError, TorProcess, validate_onion

MAX_REQUEST = 64 * 1024
ICON_PNG = files("onioncall").joinpath("assets/onioncall-icon.png").read_bytes()


class GuiController:
    def __init__(self):
        self.lock = threading.RLock()
        self.events: deque[dict[str, object]] = deque(maxlen=500)
        self.event_id = 0
        self.state = "idle"
        self.detail = "Bereit"
        self.own_address: str | None = None
        self.tor: TorProcess | None = None
        self.listener: socket.socket | None = None
        self.session: GuiSession | None = None
        self.worker: threading.Thread | None = None
        self.stop_requested = threading.Event()
        self.audio_busy = threading.Event()
        self._emit("system", "BRZ – OnionCall GUI ist bereit.")

    def ensure_initialized(self) -> None:
        home = app_home(); ensure_private_dir(home); save_config(load_config(home), home); load_or_create_identity(home)
        try:
            load_peer("default", home)
        except ConfigError:
            generate_secret(home)

    @staticmethod
    def _audio(config=None) -> AudioBackend:
        config = config or load_config(); runtime = app_home() / "runtime"; ensure_private_dir(runtime)
        return AudioBackend(runtime, config.max_audio_seconds)

    def _emit(self, kind: str, message: str) -> None:
        with self.lock:
            self.event_id += 1
            self.events.append({"id": self.event_id, "kind": kind, "message": message, "time": time.strftime("%H:%M:%S")})

    def _set_state(self, state: str, detail: str) -> None:
        with self.lock:
            self.state, self.detail = state, detail

    def status(self, after: int = 0) -> dict[str, object]:
        self.ensure_initialized(); config = load_config()
        try:
            load_peer("default"); key_ok = True
        except ConfigError:
            key_ok = False
        with self.lock:
            tor_active = bool(self.tor and self.tor.process and self.tor.process.poll() is None)
            active_session = self.session is not None and not self.session.finished.is_set()
            audio_missing = missing_audio_commands()
            return {
                "version": __version__,
                "state": self.state,
                "detail": self.detail,
                "busy": self.state not in {"idle", "error"},
                "connected": active_session,
                "tor_found": shutil.which(config.tor_binary) is not None,
                "tor_active": tor_active,
                "key_ok": key_ok,
                "audio_ok": not audio_missing,
                "audio_missing": audio_missing,
                "audio_busy": self.audio_busy.is_set(),
                "own_address": self.own_address,
                "last_address": config.last_address,
                "platform": "Android/Termux" if is_termux() else platform.system(),
                "peers": list_peers(),
                "events": [e for e in self.events if int(e["id"]) > after],
                "last_event": self.event_id,
            }

    def _busy_guard(self) -> None:
        with self.lock:
            if self.worker and self.worker.is_alive():
                raise RuntimeError("Eine Verbindungsaktion läuft bereits")
            if self.session and not self.session.finished.is_set():
                raise RuntimeError("Es besteht bereits eine Verbindung")

    def start_listen(self, peer_name: str = "default", temporary: bool = False) -> None:
        self.ensure_initialized(); self._busy_guard(); self.stop_requested.clear()
        def work() -> None:
            config = load_config(); peer = load_peer(peer_name); identity = load_or_create_identity()
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM); listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            tor = TorProcess(config, service=True, temporary_service=temporary or config.temporary_onion)
            with self.lock: self.listener, self.tor = listener, tor
            try:
                listener.bind(("127.0.0.1", config.listen_port)); self._set_state("starting", "Tor wird gestartet …")
                address = tor.start(180.0); self.own_address = address; self._set_state("waiting", "Warte auf authentifizierten Kontakt …")
                self._emit("system", f"Onion-Adresse bereit: {address}")
                channel = accept_authenticated(listener, peer.key, identity, peer.fingerprint, stop_event=self.stop_requested)
                if channel.peer_fingerprint: pin_peer_fingerprint(peer, channel.peer_fingerprint)
                session = GuiSession(channel, self._audio(config), self._emit)
                with self.lock: self.session = session
                self._set_state("connected", "Sichere Verbindung hergestellt"); session.run()
            except Exception as exc:
                if not self.stop_requested.is_set(): self._emit("error", str(exc))
            finally:
                with suppress(OSError): listener.close()
                tor.stop()
                with self.lock: self.listener = None; self.tor = None; self.session = None; self.own_address = None
                self._set_state("idle", "Bereit")
        self.worker = threading.Thread(target=work, name="onioncall-gui-listen", daemon=True); self.worker.start()

    def start_call(self, address: str, peer_name: str = "default") -> None:
        self.ensure_initialized(); self._busy_guard(); address = validate_onion(address); self.stop_requested.clear()
        def work() -> None:
            config = load_config()
            config.last_address = address
            save_config(config)
            peer = load_peer(peer_name)
            identity = load_or_create_identity()
            set_peer_onion(peer, address)
            tor = TorProcess(config, service=False)
            with self.lock: self.tor = tor
            try:
                self._set_state("starting", "Tor wird gestartet …"); tor.start(180.0); self._set_state("connecting", "Verbindung wird authentifiziert …")
                sock = socks5_connect(address, config.listen_port, config.socks_port); channel = perform_client_handshake(sock, peer.key, identity, peer.fingerprint)
                if channel.peer_fingerprint: pin_peer_fingerprint(peer, channel.peer_fingerprint)
                session = GuiSession(channel, self._audio(config), self._emit)
                with self.lock: self.session = session
                self._set_state("connected", "Sichere Verbindung hergestellt"); session.run()
            except Exception as exc:
                if not self.stop_requested.is_set(): self._emit("error", str(exc))
            finally:
                tor.stop()
                with self.lock: self.tor = None; self.session = None
                self._set_state("idle", "Bereit")
        self.worker = threading.Thread(target=work, name="onioncall-gui-call", daemon=True); self.worker.start()

    def disconnect(self) -> None:
        self.stop_requested.set()
        with self.lock: session, listener, tor = self.session, self.listener, self.tor
        if session: session.close()
        if listener:
            with suppress(OSError): listener.close()
        if tor: tor.stop()
        self._set_state("idle", "Bereit"); self._emit("system", "Verbindung beendet.")

    def send_text(self, text: str) -> None:
        with self.lock: session = self.session
        if not session or session.finished.is_set(): raise RuntimeError("Keine aktive Verbindung")
        session.send_text(text)

    def send_audio(self, seconds: int = 5) -> None:
        if not 1 <= seconds <= load_config().max_audio_seconds: raise ValueError("Ungültige Aufnahmedauer")
        with self.lock: session = self.session
        if not session or session.finished.is_set(): raise RuntimeError("Keine aktive Verbindung")
        if self.audio_busy.is_set(): raise RuntimeError("Audio ist bereits aktiv")
        self.audio_busy.set()
        def work():
            try: session.send_audio(seconds)
            except Exception as exc: self._emit("error", str(exc))
            finally: self.audio_busy.clear()
        threading.Thread(target=work, daemon=True).start()

    def test_audio(self) -> None:
        if self.audio_busy.is_set(): raise RuntimeError("Audio ist bereits aktiv")
        self.audio_busy.set()
        def work():
            try:
                payload = self._audio().record_opus(3); self._audio().play_opus(payload); self._emit("system", "Audiotest erfolgreich.")
            except Exception as exc: self._emit("error", f"Audiotest fehlgeschlagen: {exc}")
            finally: self.audio_busy.clear()
        threading.Thread(target=work, daemon=True).start()

    def show_secret(self, peer: str = "default") -> str:
        self.ensure_initialized(); return peer_secret_token(load_peer(peer))

    def set_secret(self, peer: str, secret: str) -> None:
        import_peer_secret(peer, secret); self._emit("system", f"Schlüssel für {peer} gespeichert.")

    def shutdown(self) -> None:
        self.disconnect()


HTML = r"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="dark">
  <link rel="icon" type="image/png" href="/icon.png">
  <title>BRZ – OnionCall</title>
  <style nonce="__NONCE__">
    :root{--bg:#090b10;--panel:#11151d;--line:#293141;--text:#eef2f7;--muted:#8e9bad;--purple:#b896ff;--cyan:#66e3d2;--green:#76e39a;--red:#ff7b84;--amber:#ffc66d}
    *{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 20% 0,#1b1830 0,transparent 38%),var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,sans-serif;min-height:100vh}
    button,input{font:inherit}.app{max-width:1180px;margin:auto;padding:22px}.top{display:flex;align-items:center;gap:15px;margin-bottom:18px}.logo{width:54px;height:54px;object-fit:contain;filter:drop-shadow(0 10px 16px #8d6cff44)}.title h1{font-size:23px;margin:0}.title p{margin:1px 0 0;color:var(--muted)}.version{margin-left:auto;color:var(--muted);font:13px ui-monospace,monospace}
    .statusbar{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px}.pill{background:#0e1219;border:1px solid var(--line);border-radius:12px;padding:11px 13px;display:flex;align-items:center;gap:9px}.dot{width:9px;height:9px;border-radius:50%;background:var(--red);box-shadow:0 0 12px currentColor}.dot.ok{background:var(--green)}.dot.busy{background:var(--amber)}.pill small{display:block;color:var(--muted)}
    .grid{display:grid;grid-template-columns:330px 1fr;gap:16px}.panel{background:var(--panel);background:color-mix(in srgb,var(--panel) 94%,transparent);border:1px solid var(--line);border-radius:16px;box-shadow:0 14px 40px #0005}.side{padding:16px}.side h2,.chathead h2{font-size:15px;margin:0 0 12px;color:var(--muted);text-transform:uppercase;letter-spacing:.09em}.side h2.spaced{margin-top:20px}.actions{display:grid;gap:9px}.btn{border:1px solid #374154;background:#191f2a;color:var(--text);padding:12px 13px;border-radius:11px;text-align:left;cursor:pointer;transition:.15s}.btn:hover{border-color:var(--purple);transform:translateY(-1px)}.btn.primary{background:linear-gradient(135deg,#7f62e9,#6042c9);border-color:#a48cff}.btn.danger{color:#ffb2b7}.btn:disabled{opacity:.45;cursor:not-allowed;transform:none}.btnrow{display:grid;grid-template-columns:1fr 1fr;gap:9px}.address{margin:14px 0;padding:12px;background:#0b0e14;border:1px solid var(--line);border-radius:11px;word-break:break-all;font:12px/1.45 ui-monospace,monospace;color:var(--cyan)}.address.empty{color:var(--muted)}
    .chat{min-height:665px;display:flex;flex-direction:column;overflow:hidden}.chathead{padding:16px 18px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:12px}.chathead h2{margin:0}.state{margin-left:auto;color:var(--muted)}.messages{flex:1;padding:18px;overflow:auto;min-height:390px;max-height:560px;display:flex;flex-direction:column;gap:10px}.msg{max-width:78%;border:1px solid var(--line);border-radius:14px;padding:10px 12px;background:#141923;white-space:pre-wrap;word-break:break-word}.msg.self{align-self:flex-end;background:#28204a;border-color:#55448a}.msg.peer{align-self:flex-start;background:#102322;border-color:#24534d}.msg.system,.msg.error,.msg.address{align-self:center;max-width:92%;font-size:13px;color:var(--muted);background:transparent;border-style:dashed;text-align:center}.msg.error{color:#ff9da4;border-color:#76373c}.msg.address{color:var(--cyan);font-family:ui-monospace,monospace}.meta{font-size:11px;color:var(--muted);margin-bottom:3px}.composer{border-top:1px solid var(--line);padding:13px;display:grid;grid-template-columns:1fr auto auto;gap:9px}.composer input{min-width:0;background:#0b0e14;border:1px solid var(--line);border-radius:11px;color:var(--text);padding:12px;outline:none}.composer input:focus{border-color:var(--purple)}.iconbtn{border:1px solid var(--line);border-radius:11px;background:#191f2a;color:var(--text);padding:0 16px;cursor:pointer}.iconbtn.send{background:var(--purple);color:#0b0712;font-weight:800}.hint{padding:0 16px 13px;color:var(--muted);font-size:12px}
    dialog{border:1px solid var(--line);border-radius:16px;background:#11151d;color:var(--text);width:min(610px,calc(100% - 30px));padding:0;box-shadow:0 24px 80px #000b}dialog::backdrop{background:#000a}.modal{padding:20px}.modal h3{margin:0 0 8px}.modal p{color:var(--muted)}.field{width:100%;background:#090c12;color:var(--text);border:1px solid var(--line);border-radius:10px;padding:12px;font-family:ui-monospace,monospace}.modalbuttons{display:flex;justify-content:flex-end;gap:9px;margin-top:14px}.copyhelper{position:fixed;opacity:0}.toast{position:fixed;right:20px;bottom:20px;background:#202735;border:1px solid #465167;border-radius:11px;padding:12px 15px;opacity:0;transform:translateY(10px);transition:.2s;pointer-events:none}.toast.show{opacity:1;transform:none}
    @media(max-width:800px){.app{padding:12px}.statusbar{grid-template-columns:1fr 1fr}.grid{grid-template-columns:1fr}.chat{min-height:600px}.messages{max-height:52vh}.top{align-items:flex-start}.version{display:none}}
  </style>
</head>
<body>
<main class="app">
  <header class="top"><img class="logo" src="/icon.png" alt="BRZ – OnionCall"><div class="title"><h1>BRZ – OnionCall</h1><p>Sicherer Text und Sprache über Tor</p></div><div class="version" id="version"></div></header>
  <section class="statusbar">
    <div class="pill"><span class="dot" id="torDot"></span><div><b>Tor</b><small id="torText">Prüfen …</small></div></div>
    <div class="pill"><span class="dot" id="keyDot"></span><div><b>Schlüssel</b><small id="keyText">Prüfen …</small></div></div>
    <div class="pill"><span class="dot" id="audioDot"></span><div><b>Audio</b><small id="audioText">Prüfen …</small></div></div>
    <div class="pill"><span class="dot" id="linkDot"></span><div><b>Verbindung</b><small id="linkText">Bereit</small></div></div>
  </section>
  <div class="grid">
    <aside class="panel side">
      <h2>Gespräch</h2>
      <div class="actions">
        <button class="btn primary" id="listenBtn">Empfangen</button>
        <button class="btn primary" id="callBtn">Onion-Adresse anrufen</button>
        <button class="btn danger" id="disconnectBtn">Verbindung beenden</button>
      </div>
      <h2 class="spaced">Meine Onion-Adresse</h2>
      <div class="address empty" id="ownAddress">Noch nicht erstellt. Starte „Empfangen“.</div>
      <button class="btn" id="copyAddressBtn">Adresse kopieren</button>
      <h2 class="spaced">Einrichtung</h2>
      <div class="actions">
        <div class="btnrow"><button class="btn" id="showSecretBtn">Schlüssel anzeigen</button><button class="btn" id="importSecretBtn">Schlüssel importieren</button></div>
        <button class="btn" id="audioTestBtn">Audio testen (3 Sekunden)</button>
        <button class="btn" id="refreshBtn">Status neu prüfen</button>
        <button class="btn danger" id="shutdownBtn">OnionCall beenden</button>
      </div>
    </aside>
    <section class="panel chat">
      <div class="chathead"><h2>Sicherer Chat</h2><span class="state" id="detail">Bereit</span></div>
      <div class="messages" id="messages"></div>
      <form class="composer" id="composer"><input id="messageInput" maxlength="8192" autocomplete="off" placeholder="Nachricht schreiben …"><button type="button" class="iconbtn" id="audioBtn">Audio 5 s</button><button class="iconbtn send">Senden</button></form>
      <div class="hint">Nachrichten und Audio sind erst nach erfolgreicher gegenseitiger Authentifizierung verfügbar.</div>
    </section>
  </div>
</main>
<dialog id="callDialog"><form class="modal" id="callForm"><h3>Empfänger anrufen</h3><p>Füge exakt die `.onion`-Adresse ein, die beim Empfänger angezeigt wird.</p><input class="field" id="callAddress" autocomplete="off" placeholder="56 Zeichen.onion"><div class="modalbuttons"><button type="button" class="btn" id="cancelCallBtn">Abbrechen</button><button class="btn primary" id="callConfirm">Verbinden</button></div></form></dialog>
<dialog id="secretDialog"><div class="modal"><h3>Geheimer Verbindungsschlüssel</h3><p>Nur über einen bereits sicheren Kanal teilen. Wer diesen Schlüssel besitzt, kann sich als Gesprächspartner ausgeben.</p><input class="field" id="secretValue" readonly><div class="modalbuttons"><button class="btn" id="copySecretBtn">Kopieren</button><button class="btn primary" id="closeSecretBtn">Schließen</button></div></div></dialog>
<dialog id="importDialog"><div class="modal"><h3>Verbindungsschlüssel importieren</h3><p>Füge die vollständige Zeile ein, die mit `onioncall:v2:` beginnt. Eine `.onion`-Adresse gehört hier nicht hinein.</p><input class="field" id="importValue" type="password" autocomplete="off" placeholder="onioncall:v2:…"><div class="modalbuttons"><button class="btn" id="cancelImportBtn">Abbrechen</button><button class="btn primary" id="saveImportBtn">Sicher speichern</button></div></div></dialog>
<div class="toast" id="toast"></div>
<script nonce="__NONCE__">
const TOKEN='__TOKEN__'; let lastEvent=0; let current={};
const $=id=>document.getElementById(id);
function toast(text){const t=$('toast');t.textContent=text;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2400)}
async function copyText(value){try{await navigator.clipboard.writeText(value)}catch(e){const area=document.createElement('textarea');area.value=value;area.className='copyhelper';document.body.append(area);area.select();document.execCommand('copy');area.remove()}}
async function api(path,data={}){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-OnionCall-Token':TOKEN},body:JSON.stringify(data)});const j=await r.json();if(!r.ok)throw new Error(j.error||'Aktion fehlgeschlagen');return j}
function dot(id,state){$(id).className='dot '+(state==='green'?'ok':state==='yellow'?'busy':'')}
function addEvent(e){const box=$('messages');const node=document.createElement('div');node.className='msg '+e.kind;const meta=document.createElement('div');meta.className='meta';const names={self:'Du',peer:'Gegenstelle',self_audio:'Du · Audio',peer_audio:'Gegenstelle · Audio',system:'System',error:'Fehler',address:'Onion-Adresse'};meta.textContent=(names[e.kind]||'System')+' · '+e.time;const text=document.createElement('div');text.textContent=e.message;node.append(meta,text);box.append(node);box.scrollTop=box.scrollHeight}
function render(s){current=s;$('version').textContent='v'+s.version+' · '+s.platform;dot('torDot',s.tor_active?'green':'red');$('torText').textContent=s.tor_active?'aktiv':s.tor_found?'installiert':'fehlt';dot('keyDot',s.key_ok?'green':'red');$('keyText').textContent=s.key_ok?'sicher gespeichert':'nicht eingerichtet';dot('audioDot',s.audio_busy?'yellow':s.audio_ok?'green':'red');$('audioText').textContent=s.audio_busy?'beschäftigt':s.audio_ok?'bereit':(s.audio_missing||[]).join(', ')+' fehlt';dot('linkDot',s.connected?'green':['starting','connecting','authenticating','listening','waiting','stopping'].includes(s.state)?'yellow':'red');$('linkText').textContent=s.connected?'verbunden':(s.state==='listening'||s.state==='waiting')?'wartet':s.state==='idle'?'bereit':s.state;$('detail').textContent=s.detail;const a=$('ownAddress');a.textContent=s.own_address||'Noch nicht erstellt. Starte „Empfangen“.';a.classList.toggle('empty',!s.own_address);$('callAddress').value=s.last_address||'';$('listenBtn').disabled=s.busy;$('callBtn').disabled=s.busy;$('disconnectBtn').disabled=!s.busy;$('showSecretBtn').disabled=s.busy;$('importSecretBtn').disabled=s.busy;$('audioTestBtn').disabled=s.busy||s.audio_busy;$('messageInput').disabled=!s.connected;$('audioBtn').disabled=!s.connected||s.audio_busy;for(const e of s.events)addEvent(e);lastEvent=s.last_event}
async function poll(){try{const r=await fetch('/api/status?after='+lastEvent,{cache:'no-store',headers:{'X-OnionCall-Token':TOKEN}});if(r.ok)render(await r.json())}catch(e){}setTimeout(poll,700)}
$('listenBtn').onclick=()=>api('/api/listen').catch(e=>toast(e.message));
$('callBtn').onclick=()=>{$('callDialog').showModal();$('callAddress').focus()};
$('cancelCallBtn').onclick=()=>$('callDialog').close();
$('callForm').onsubmit=e=>{e.preventDefault();api('/api/call',{address:$('callAddress').value}).then(()=>$('callDialog').close()).catch(x=>toast(x.message))};
$('disconnectBtn').onclick=()=>api('/api/disconnect').catch(e=>toast(e.message));
$('composer').onsubmit=e=>{e.preventDefault();const i=$('messageInput'),text=i.value;if(!text.trim())return;i.value='';api('/api/message',{text}).catch(x=>{i.value=text;toast(x.message)})};
$('audioBtn').onclick=()=>api('/api/audio',{seconds:5}).catch(e=>toast(e.message));
$('audioTestBtn').onclick=()=>api('/api/audio/test').then(()=>toast('Audiotest gestartet')).catch(e=>toast(e.message));
$('showSecretBtn').onclick=()=>api('/api/secret/show').then(j=>{$('secretValue').value=j.secret;$('secretDialog').showModal()}).catch(e=>toast(e.message));
$('closeSecretBtn').onclick=()=>{$('secretValue').value='';$('secretDialog').close()};
$('copySecretBtn').onclick=()=>copyText($('secretValue').value).then(()=>toast('Schlüssel kopiert'));
$('importSecretBtn').onclick=()=>{$('importValue').value='';$('importDialog').showModal();$('importValue').focus()};
$('cancelImportBtn').onclick=()=>{$('importValue').value='';$('importDialog').close()};
$('saveImportBtn').onclick=()=>api('/api/secret/import',{secret:$('importValue').value}).then(()=>{$('importValue').value='';$('importDialog').close();toast('Schlüssel gespeichert')}).catch(e=>toast(e.message));
$('copyAddressBtn').onclick=()=>{if(!current.own_address)return toast('Noch keine Adresse vorhanden');copyText(current.own_address).then(()=>toast('Adresse kopiert'))};
$('refreshBtn').onclick=()=>{lastEvent=Math.max(0,lastEvent-1);toast('Status wird aktualisiert')};
$('shutdownBtn').onclick=()=>{if(!confirm('OnionCall und die aktive Verbindung beenden?'))return;api('/api/shutdown').then(()=>{$('detail').textContent='OnionCall wurde beendet. Dieses Fenster kann geschlossen werden.'}).catch(e=>toast(e.message))};
poll();
</script>
</body></html>"""


class OnionHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    def __init__(self, address, controller):
        super().__init__(address, OnionRequestHandler)
        self.controller = controller
        self.token = secrets.token_urlsafe(32)
        self.nonce = secrets.token_urlsafe(18)


class OnionRequestHandler(BaseHTTPRequestHandler):
    server: OnionHTTPServer
    def log_message(self, *_): pass
    def _valid_local_request(self) -> bool:
        if self.client_address[0] not in {"127.0.0.1", "::1"}: return False
        host = self.headers.get("Host", "")
        return host in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
    def _security_headers(self) -> None:
        self.send_header("Cache-Control", "no-store"); self.send_header("X-Content-Type-Options", "nosniff"); self.send_header("X-Frame-Options", "DENY"); self.send_header("Referrer-Policy", "no-referrer"); self.send_header("Permissions-Policy", "camera=(), geolocation=(), usb=()"); self.send_header("Cross-Origin-Opener-Policy", "same-origin"); self.send_header("Cross-Origin-Resource-Policy", "same-origin"); self.send_header("Cross-Origin-Embedder-Policy", "require-corp"); self.send_header("Content-Security-Policy", f"default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-{self.server.nonce}'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
    def _send(self, body: bytes, content_type: str, status=HTTPStatus.OK) -> None:
        self.send_response(status); self._security_headers(); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def _json(self, data, status=HTTPStatus.OK) -> None: self._send(json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8", status)
    def _authorized(self) -> bool: return self._valid_local_request() and secrets.compare_digest(self.headers.get("X-OnionCall-Token", ""), self.server.token)
    def do_GET(self) -> None:
        if not self._valid_local_request(): self._json({"error":"Ungültiger Host"}, HTTPStatus.FORBIDDEN); return
        parsed=urlparse(self.path)
        if parsed.path=="/": self._send(HTML.replace("__TOKEN__",self.server.token).replace("__NONCE__",self.server.nonce).encode(),"text/html; charset=utf-8"); return
        if parsed.path in {"/icon.png","/favicon.ico"}: self._send(ICON_PNG,"image/png"); return
        if parsed.path=="/api/status":
            if not self._authorized(): self._json({"error":"Nicht autorisiert"},HTTPStatus.FORBIDDEN); return
            try: after=max(0,int(parse_qs(parsed.query).get("after",["0"])[0]))
            except ValueError: after=0
            self._json(self.server.controller.status(after)); return
        self._json({"error":"Nicht gefunden"},HTTPStatus.NOT_FOUND)
    def do_POST(self) -> None:
        if not self._authorized(): self._json({"error":"Aktion nicht autorisiert"},HTTPStatus.FORBIDDEN); return
        origin=self.headers.get("Origin"); expected=f"http://127.0.0.1:{self.server.server_port}"
        if origin and origin not in {expected,f"http://localhost:{self.server.server_port}"}: self._json({"error":"Ungültiger Ursprung"},HTTPStatus.FORBIDDEN); return
        try: length=int(self.headers.get("Content-Length","0"))
        except ValueError: length=MAX_REQUEST+1
        if not 0<=length<=MAX_REQUEST: self._json({"error":"Anfrage ist zu groß"},HTTPStatus.REQUEST_ENTITY_TOO_LARGE); return
        try:
            body=json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body,dict): raise ValueError
            result=self._route(urlparse(self.path).path,body); self._json({"ok":True,**result})
        except (json.JSONDecodeError,ValueError): self._json({"error":"Ungültige Anfrage"},HTTPStatus.BAD_REQUEST)
        except (ConfigError,TorError,RuntimeError) as exc: self._json({"error":str(exc)},HTTPStatus.BAD_REQUEST)
    def _route(self,path:str,body:dict)->dict[str,object]:
        c=self.server.controller
        if path=="/api/listen": c.start_listen(str(body.get("peer","default")),bool(body.get("temporary",False)))
        elif path=="/api/call": c.start_call(str(body.get("address","")),str(body.get("peer","default")))
        elif path=="/api/disconnect": c.disconnect()
        elif path=="/api/message": c.send_text(str(body.get("text","")))
        elif path=="/api/audio": c.send_audio(int(body.get("seconds",5)))
        elif path=="/api/audio/test": c.test_audio()
        elif path=="/api/secret/show": return {"secret":c.show_secret(str(body.get("peer","default")))}
        elif path=="/api/secret/import": c.set_secret(str(body.get("peer","default")),str(body.get("secret","")))
        elif path=="/api/shutdown": c.shutdown(); threading.Thread(target=self.server.shutdown,daemon=True).start()
        else: raise ValueError("Unbekannte Aktion")
        return {}


def create_server(port: int = 0, controller: GuiController | None = None) -> OnionHTTPServer:
    if not 0 <= port <= 65535: raise ValueError("Ungültiger GUI-Port")
    return OnionHTTPServer(("127.0.0.1", port), controller or GuiController())


def run_gui(port: int = 0, *, open_browser: bool = True) -> int:
    server=create_server(port); url=f"http://127.0.0.1:{server.server_port}/"
    print(f"BRZ – OnionCall GUI: {url}")
    if open_browser: threading.Timer(0.35, lambda: webbrowser.open(url)).start()
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.controller.disconnect(); server.server_close()
    return 0
