from __future__ import annotations

import argparse
import getpass
import os
import platform
import shutil
import socket
import sys
from contextlib import suppress

def _configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


_configure_utf8_stdio()

from . import __version__
from .audio import AudioBackend, AudioError, is_termux, missing_audio_commands
from .client_auth import (
    generate_authorized_client,
    import_client_authorization,
    list_client_authorizations,
    list_server_authorizations,
    remove_client_authorization,
    revoke_server_authorization,
)
from .config import ConfigError, app_home, ensure_private_dir, generate_secret, load_config, save_config
from .crypto import AuthenticationError
from .identity import load_or_create_identity
from .listener import accept_authenticated
from .peers import (
    create_peer,
    import_peer_secret,
    list_peers,
    load_peer,
    peer_secret_token,
    pin_peer_fingerprint,
    set_peer_onion,
)
from .protocol import perform_client_handshake
from .session import InteractiveSession
from .terminal_style import BOLD, CYAN, DIM, MAGENTA, RED, WHITE, YELLOW, brand, paint, status
from .tor import TorError, TorProcess, loopback_connect, socks5_connect, validate_loopback_host, validate_onion
from .webgui import run_gui


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="onioncall", description="Sicheres Push-to-talk und Text über Tor")
    result.add_argument("--version", action="version", version=f"BRZ – OnionCall {__version__}")
    commands = result.add_subparsers(dest="command")
    commands.add_parser("menu", help="Terminal-Oberfläche öffnen")
    commands.add_parser("terminal", help="Terminal-Oberfläche öffnen")
    gui = commands.add_parser("gui", help="Lokale grafische Oberfläche öffnen")
    gui.add_argument("--port", type=int, default=0)
    gui.add_argument("--no-browser", action="store_true")
    init = commands.add_parser("init", help="Konfiguration, Identität und Standardschlüssel erzeugen")
    init.add_argument("--replace", action="store_true", help="Standardschlüssel ersetzen")
    show = commands.add_parser("show-secret", help="Schlüssel eines Kontaktprofils anzeigen")
    show.add_argument("--peer", default="default")
    show.add_argument("--confirm", action="store_true")
    set_secret = commands.add_parser("set-secret", help="Schlüssel eines Kontaktprofils importieren")
    set_secret.add_argument("--peer", default="default")
    peer_add = commands.add_parser("peer-add", help="Eigenes Schlüsselprofil für einen Kontakt erzeugen")
    peer_add.add_argument("name")
    peer_add.add_argument("--address")
    commands.add_parser("peer-list", help="Kontaktprofile auflisten")
    auth_create = commands.add_parser("tor-auth-create", help="Tor-v3-Client-Autorisierung für einen Client erzeugen")
    auth_create.add_argument("name")
    auth_create.add_argument("--replace", action="store_true")
    auth_import = commands.add_parser("tor-auth-import", help="Private Tor-v3-Client-Autorisierung importieren")
    auth_import.add_argument("address")
    auth_import.add_argument("--name", default="service")
    auth_revoke = commands.add_parser("tor-auth-revoke", help="Öffentliche Tor-Autorisierung widerrufen")
    auth_revoke.add_argument("name")
    auth_remove = commands.add_parser("tor-auth-remove-client", help="Private Tor-Autorisierung entfernen")
    auth_remove.add_argument("name")
    commands.add_parser("tor-auth-list", help="Tor-v3-Client-Autorisierungen auflisten")
    commands.add_parser("doctor", help="Installation und Sicherheitsstatus prüfen")
    listen = commands.add_parser("listen", help="Onion-Adresse starten und authentifizierte Verbindung annehmen")
    listen.add_argument("--peer", default="default")
    listen.add_argument("--temporary-onion", action="store_true")
    listen.add_argument("--tor-timeout", type=float, default=180.0)
    call = commands.add_parser("call", help="Eine Onion-Adresse über Tor anrufen")
    call.add_argument("address", nargs="?")
    call.add_argument("--peer", default="default")
    call.add_argument("--tor-timeout", type=float, default=180.0)
    call.add_argument("--existing-tor", action="store_true")
    direct_listen = commands.add_parser("direct-listen", help=argparse.SUPPRESS)
    direct_listen.add_argument("--host", default="127.0.0.1")
    direct_listen.add_argument("--port", type=int, default=17777)
    direct_listen.add_argument("--peer", default="default")
    direct_call = commands.add_parser("direct-call", help=argparse.SUPPRESS)
    direct_call.add_argument("host")
    direct_call.add_argument("port", type=int)
    direct_call.add_argument("--peer", default="default")
    return result


def _audio(config) -> AudioBackend:
    runtime = app_home() / "runtime"
    ensure_private_dir(runtime)
    return AudioBackend(runtime, config.max_audio_seconds)


def _ensure_initialized() -> None:
    home = app_home()
    ensure_private_dir(home)
    config = load_config(home)
    save_config(config, home)
    load_or_create_identity(home)
    try:
        load_peer("default", home)
    except ConfigError:
        generate_secret(home)


def _doctor() -> int:
    failures = 0
    print(f"Python: {platform.python_version()} ({sys.executable})")
    print(f"Plattform: {'Android/Termux' if is_termux() else platform.system()}")
    config = load_config()
    for command in (config.tor_binary, *missing_audio_commands()):
        found = shutil.which(command)
        print(f"{status(bool(found))} {command}: {paint(found or 'nicht gefunden', DIM, WHITE)}")
        if not found:
            failures += 1
    try:
        home = app_home()
        ensure_private_dir(home)
        ident = load_or_create_identity(home)
        print(f"{status(True)} Lokale Identität: {ident.fingerprint}")
        peers = list_peers(home)
        print(f"{status(bool(peers))} Kontaktprofile: {', '.join(peers) if peers else 'keine'}")
        if not peers:
            failures += 1
    except (ConfigError, OSError, RuntimeError) as exc:
        print(paint(f"[FEHLER] {exc}", BOLD, RED))
        failures += 1
    print(f"[INFO] Tor Client Authorization (Server): {len(list_server_authorizations())}")
    print(f"[INFO] Tor Client Authorization (Client): {len(list_client_authorizations())}")
    return 0 if failures == 0 else 1


def _pin_after_handshake(peer, channel) -> None:
    if channel.peer_fingerprint:
        pin_peer_fingerprint(peer, channel.peer_fingerprint)
        print(paint(f"Identität: {channel.peer_fingerprint}", DIM, WHITE))


def _listen(peer_name: str, *, temporary_onion: bool, timeout: float) -> int:
    config = load_config()
    peer = load_peer(peer_name)
    identity = load_or_create_identity()
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", config.listen_port))
    tor = TorProcess(config, service=True, temporary_service=temporary_onion or config.temporary_onion)
    try:
        address = tor.start(timeout)
        assert address is not None
        print(f"{paint('Deine Onion-Adresse:', BOLD, MAGENTA)} {paint(address, BOLD, CYAN)}")
        print(paint("Warte auf eine authentifizierte Verbindung …", BOLD, YELLOW), flush=True)
        channel = accept_authenticated(listener, peer.key, identity, peer.fingerprint)
        listener.close()
        _pin_after_handshake(peer, channel)
        InteractiveSession(channel, _audio(config)).run()
    finally:
        with suppress(OSError):
            listener.close()
        tor.stop()
    return 0


def _call(address: str, peer_name: str, timeout: float, *, existing_tor: bool = False) -> int:
    config = load_config()
    peer = load_peer(peer_name)
    identity = load_or_create_identity()
    address = validate_onion(address)
    config.last_address = address
    save_config(config)
    set_peer_onion(peer, address)
    tor = None if existing_tor else TorProcess(config, service=False)
    try:
        if tor is not None:
            tor.start(timeout)
        else:
            probe = loopback_connect("127.0.0.1", config.socks_port, timeout=2)
            probe.close()
        connection = socks5_connect(address, config.listen_port, config.socks_port)
        channel = perform_client_handshake(connection, peer.key, identity, peer.fingerprint)
        _pin_after_handshake(peer, channel)
        InteractiveSession(channel, _audio(config)).run()
    finally:
        if tor is not None:
            tor.stop()
    return 0


def _menu() -> int:
    _ensure_initialized()
    while True:
        print("\n" + paint("═" * 56, MAGENTA))
        print(" " * 14 + brand(__version__))
        print(paint("═" * 56, MAGENTA))
        print("1  Gespräch empfangen\n2  Person anrufen\n3  Kontaktprofile anzeigen\n4  Sicherheitsdiagnose\n0  Beenden")
        try:
            choice = input("Auswahl: ").strip()
        except EOFError:
            return 0
        if choice == "1":
            peer = input("Kontaktprofil [default]: ").strip() or "default"
            temporary = input("Temporäre Onion-Adresse? [j/N]: ").strip().lower() in {"j", "ja", "y", "yes"}
            _listen(peer, temporary_onion=temporary, timeout=180.0)
        elif choice == "2":
            peer_name = input("Kontaktprofil [default]: ").strip() or "default"
            peer = load_peer(peer_name)
            raw = input(f"Onion-Adresse [{peer.onion or ''}]: ").strip() or peer.onion or ""
            _call(raw, peer_name, 180.0)
        elif choice == "3":
            for name in list_peers():
                peer = load_peer(name)
                print(f"- {name}: {peer.fingerprint or 'noch nicht gepinnt'} {peer.onion or ''}")
        elif choice == "4":
            _doctor()
        elif choice == "0":
            return 0


def run_terminal() -> int:
    return _menu()


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command is None:
            return run_gui()
        if args.command == "gui":
            return run_gui(port=args.port, open_browser=not args.no_browser)
        if args.command in {"menu", "terminal"}:
            return _menu()
        if args.command == "init":
            home = app_home(); ensure_private_dir(home); save_config(load_config(home), home); load_or_create_identity(home)
            try:
                generate_secret(home, replace=args.replace)
            except ConfigError:
                if args.replace:
                    raise
            print(f"OnionCall wurde in {home} eingerichtet.")
            return 0
        if args.command == "show-secret":
            if not args.confirm:
                raise ConfigError("Die Anzeige legt den Schlüssel offen; erneut mit --confirm aufrufen")
            print(peer_secret_token(load_peer(args.peer))); return 0
        if args.command == "set-secret":
            token = getpass.getpass("Verbindungsschlüssel (Eingabe bleibt unsichtbar): ").strip()
            if not token: raise ConfigError("Verbindungsschlüssel darf nicht leer sein")
            import_peer_secret(args.peer, token); print("Verbindungsschlüssel sicher gespeichert."); return 0
        if args.command == "peer-add":
            address = validate_onion(args.address) if args.address else None
            peer = create_peer(args.name, onion=address)
            print(f"Kontakt {peer.name} erstellt.\nSchlüssel zur sicheren Weitergabe:\n{peer_secret_token(peer)}"); return 0
        if args.command == "peer-list":
            for name in list_peers():
                peer = load_peer(name); print(f"{name}\t{peer.fingerprint or '-'}\t{peer.onion or '-'}")
            return 0
        if args.command == "tor-auth-create":
            print(generate_authorized_client(args.name, replace=args.replace)); return 0
        if args.command == "tor-auth-import":
            token = getpass.getpass("Privater Tor-Authorization-Schlüssel: ").strip()
            if not token: raise ConfigError("Tor-Authorization-Schlüssel darf nicht leer sein")
            print(import_client_authorization(validate_onion(args.address), token, name=args.name)); return 0
        if args.command == "tor-auth-revoke":
            return 0 if revoke_server_authorization(args.name) else 1
        if args.command == "tor-auth-remove-client":
            return 0 if remove_client_authorization(args.name) else 1
        if args.command == "tor-auth-list":
            print("Server / erlaubte Clients: " + (", ".join(list_server_authorizations()) or "keine"))
            print("Client / private Service-Zugänge: " + (", ".join(list_client_authorizations()) or "keine")); return 0
        if args.command == "doctor": return _doctor()
        _ensure_initialized()
        if args.command == "listen": return _listen(args.peer, temporary_onion=args.temporary_onion, timeout=args.tor_timeout)
        if args.command == "call":
            peer = load_peer(args.peer); address = args.address or peer.onion or load_config().last_address
            if not address: raise ConfigError("Keine Onion-Adresse angegeben oder im Kontaktprofil gespeichert")
            return _call(address, args.peer, args.tor_timeout, existing_tor=args.existing_tor)
        if args.command == "direct-listen":
            host = validate_loopback_host(args.host); config = load_config(); peer = load_peer(args.peer); identity = load_or_create_identity()
            family = socket.AF_INET6 if ":" in host else socket.AF_INET
            listener = socket.socket(family, socket.SOCK_STREAM); listener.bind((host, args.port))
            try:
                channel = accept_authenticated(listener, peer.key, identity, peer.fingerprint); _pin_after_handshake(peer, channel); InteractiveSession(channel, _audio(config)).run()
            finally: listener.close()
            return 0
        if args.command == "direct-call":
            host = validate_loopback_host(args.host); config = load_config(); peer = load_peer(args.peer); identity = load_or_create_identity()
            connection = loopback_connect(host, args.port, timeout=20); connection.settimeout(None)
            channel = perform_client_handshake(connection, peer.key, identity, peer.fingerprint); _pin_after_handshake(peer, channel); InteractiveSession(channel, _audio(config)).run(); return 0
        return 2
    except KeyboardInterrupt:
        print(paint("\nAbgebrochen.", YELLOW, stream=sys.stderr), file=sys.stderr); return 130
    except (ConfigError, TorError, AuthenticationError, AudioError, OSError, RuntimeError) as exc:
        print(paint(f"Fehler: {exc}", BOLD, RED, stream=sys.stderr), file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
