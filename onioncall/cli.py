from __future__ import annotations

import argparse
import os
import platform
import shutil
import socket
import sys

from . import __version__
from .audio import AudioBackend, is_termux, missing_audio_commands
from .config import (
    ConfigError,
    app_home,
    ensure_private_dir,
    generate_secret,
    import_secret,
    load_config,
    load_secret,
    save_config,
    secret_token,
)
from .crypto import AuthenticationError
from .protocol import perform_client_handshake, perform_server_handshake
from .session import InteractiveSession
from .tor import TorError, TorProcess, socks5_connect


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="onioncall", description="Sicheres Push-to-talk und Text über Tor")
    result.add_argument("--version", action="version", version=f"OnionCall {__version__}")
    commands = result.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="Konfiguration und zufälligen Verbindungsschlüssel erzeugen")
    init.add_argument("--replace", action="store_true", help="Vorhandenen Schlüssel ersetzen")

    show = commands.add_parser("show-secret", help="Verbindungsschlüssel zur sicheren Weitergabe anzeigen")
    show.add_argument("--confirm", action="store_true", help="Bestätigt die bewusste Anzeige")

    set_secret = commands.add_parser("set-secret", help="Verbindungsschlüssel der Gegenstelle importieren")
    set_secret.add_argument("token", help="onioncall:v2:…")
    set_secret.add_argument("--replace", action="store_true")

    commands.add_parser("doctor", help="Installation und Dateirechte prüfen")

    listen = commands.add_parser("listen", help="Onion-Adresse starten und einen Anruf annehmen")
    listen.add_argument("--tor-timeout", type=float, default=180.0)

    call = commands.add_parser("call", help="Eine Onion-Adresse anrufen")
    call.add_argument("address")
    call.add_argument("--tor-timeout", type=float, default=180.0)

    direct_listen = commands.add_parser("direct-listen", help=argparse.SUPPRESS)
    direct_listen.add_argument("--host", default="127.0.0.1")
    direct_listen.add_argument("--port", type=int, default=17777)
    direct_call = commands.add_parser("direct-call", help=argparse.SUPPRESS)
    direct_call.add_argument("host")
    direct_call.add_argument("port", type=int)
    return result


def _audio(config) -> AudioBackend:
    home = app_home()
    runtime = home / "runtime"
    ensure_private_dir(runtime)
    return AudioBackend(runtime, config.max_audio_seconds)


def _run_listen(sock: socket.socket, psk: bytes, config) -> None:
    sock.listen(1)
    print("Warte auf eine eingehende Verbindung …", flush=True)
    connection, _ = sock.accept()
    sock.close()
    channel = perform_server_handshake(connection, psk)
    InteractiveSession(channel, _audio(config)).run()


def _doctor() -> int:
    failures = 0
    print(f"Python: {platform.python_version()} ({sys.executable})")
    print(f"Plattform: {'Android/Termux' if is_termux() else platform.system()}")
    for command in ("tor", *missing_audio_commands()):
        found = shutil.which(command)
        if found:
            print(f"[OK] {command}: {found}")
        else:
            print(f"[FEHLT] {command}")
            failures += 1
    home = app_home()
    try:
        ensure_private_dir(home)
        mode = os.stat(home).st_mode & 0o777
        print(f"[OK] Datenverzeichnis: {home} ({mode:o})")
        load_secret()
        print("[OK] Verbindungsschlüssel vorhanden und Rechte sicher")
    except ConfigError as exc:
        print(f"[FEHLER] {exc}")
        failures += 1
    return 0 if failures == 0 else 1


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            home = app_home()
            ensure_private_dir(home)
            config = load_config(home)
            save_config(config, home)
            generate_secret(home, replace=args.replace)
            print(f"OnionCall wurde in {home} eingerichtet.")
            print("Gib den Schlüssel nur über einen bereits sicheren Kanal weiter: onioncall show-secret --confirm")
            return 0
        if args.command == "show-secret":
            if not args.confirm:
                raise ConfigError("Die Anzeige legt den Schlüssel offen; erneut mit --confirm aufrufen")
            print(secret_token(load_secret()))
            return 0
        if args.command == "set-secret":
            import_secret(args.token, replace=args.replace)
            print("Verbindungsschlüssel sicher gespeichert.")
            return 0
        if args.command == "doctor":
            return _doctor()

        config = load_config()
        psk = load_secret()

        if args.command == "listen":
            tor = TorProcess(config)
            try:
                address = tor.start(args.tor_timeout)
                listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind(("127.0.0.1", config.listen_port))
                print(f"Deine Onion-Adresse: {address}")
                _run_listen(listener, psk, config)
            finally:
                tor.stop()
            return 0

        if args.command == "call":
            tor = TorProcess(config)
            try:
                tor.start(args.tor_timeout)
                connection = socks5_connect(args.address, config.listen_port, config.socks_port)
                channel = perform_client_handshake(connection, psk)
                InteractiveSession(channel, _audio(config)).run()
            finally:
                tor.stop()
            return 0

        if args.command == "direct-listen":
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((args.host, args.port))
            _run_listen(listener, psk, config)
            return 0

        if args.command == "direct-call":
            connection = socket.create_connection((args.host, args.port), timeout=20)
            connection.settimeout(None)
            channel = perform_client_handshake(connection, psk)
            InteractiveSession(channel, _audio(config)).run()
            return 0
        return 2
    except KeyboardInterrupt:
        print("\nAbgebrochen.", file=sys.stderr)
        return 130
    except (ConfigError, TorError, AuthenticationError, OSError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
