from __future__ import annotations

import argparse
import getpass
import os
import platform
import shutil
import socket
import sys
from contextlib import suppress

from . import __version__
from .audio import AudioBackend, AudioError, is_termux, missing_audio_commands
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
from .terminal_style import BOLD, CYAN, DIM, GREEN, MAGENTA, RED, WHITE, YELLOW, brand, paint, status
from .tor import TorError, TorProcess, socks5_connect, validate_onion
from .webgui import run_gui


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="onioncall", description="Sicheres Push-to-talk und Text über Tor")
    result.add_argument("--version", action="version", version=f"BRZ – OnionCall {__version__}")
    commands = result.add_subparsers(dest="command")

    commands.add_parser("menu", help="Vollständige Terminal-Oberfläche öffnen")
    commands.add_parser("terminal", help="Vollständige Terminal-Oberfläche öffnen")

    gui = commands.add_parser("gui", help="Lokale grafische Oberfläche öffnen")
    gui.add_argument("--port", type=int, default=0, help="Lokaler HTTP-Port (Standard: automatisch)")
    gui.add_argument("--no-browser", action="store_true", help="Browser nicht automatisch öffnen")

    init = commands.add_parser("init", help="Konfiguration und zufälligen Verbindungsschlüssel erzeugen")
    init.add_argument("--replace", action="store_true", help="Vorhandenen Schlüssel ersetzen")

    show = commands.add_parser("show-secret", help="Verbindungsschlüssel zur sicheren Weitergabe anzeigen")
    show.add_argument("--confirm", action="store_true", help="Bestätigt die bewusste Anzeige")

    set_secret = commands.add_parser("set-secret", help="Verbindungsschlüssel der Gegenstelle importieren")
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
    print(paint("Warte auf eine eingehende Verbindung …", BOLD, YELLOW), flush=True)
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
            print(f"{status(True)} {command}: {paint(found, DIM, WHITE)}")
        else:
            print(f"{status(False)} {command}")
            failures += 1
    home = app_home()
    try:
        ensure_private_dir(home)
        mode = os.stat(home).st_mode & 0o777
        print(f"{status(True)} Datenverzeichnis: {paint(str(home), DIM, WHITE)} ({mode:o})")
        load_secret()
        print(f"{status(True)} Verbindungsschlüssel vorhanden und Rechte sicher")
    except ConfigError as exc:
        print(paint(f"[FEHLER] {exc}", BOLD, RED))
        failures += 1
    return 0 if failures == 0 else 1


def _pause() -> None:
    with suppress(EOFError):
        input("\nEnter drücken, um zum Menü zurückzukehren …")


def _ensure_initialized() -> None:
    home = app_home()
    ensure_private_dir(home)
    config = load_config(home)
    save_config(config, home)
    try:
        load_secret(home)
    except ConfigError:
        generate_secret(home)
        print(paint("Ein neuer Verbindungsschlüssel wurde sicher erzeugt.", GREEN))


def _share_secret_guided() -> None:
    _ensure_initialized()
    print("\n" + paint("GEHEIMER VERBINDUNGSSCHLÜSSEL", BOLD, YELLOW))
    print("Nur über einen bereits sicheren Kanal an die gewünschte Person senden.")
    print("Nicht veröffentlichen und nicht mit einer `.onion`-Adresse verwechseln.\n")
    print(paint(secret_token(load_secret()), BOLD, CYAN))


def _import_secret_guided() -> None:
    _ensure_initialized()
    print("\nFüge jetzt die vollständige Zeile ein, die mit `onioncall:v2:` beginnt.")
    print("Eine Adresse mit `.onion` gehört hier nicht hinein.")
    token = getpass.getpass("Verbindungsschlüssel (Eingabe bleibt unsichtbar): ").strip()
    if not token:
        raise ConfigError("Verbindungsschlüssel darf nicht leer sein")
    import_secret(token, replace=True)
    print(paint("Verbindungsschlüssel sicher gespeichert.", GREEN))


def _key_menu() -> None:
    while True:
        print("\n" + paint("── Verbindungsschlüssel ──", BOLD, MAGENTA))
        _menu_item("1", "Meinen Schlüssel zum Teilen anzeigen")
        _menu_item("2", "Erhaltenen Schlüssel einfügen")
        _menu_item("0", "Zurück", dim=True)
        try:
            choice = input("Auswahl: ").strip()
        except EOFError:
            return
        if choice == "1":
            _share_secret_guided()
            _pause()
        elif choice == "2":
            try:
                _import_secret_guided()
            except ConfigError as exc:
                print(f"Fehler: {exc}", file=sys.stderr)
            _pause()
        elif choice == "0":
            return
        else:
            print("Bitte 1, 2 oder 0 wählen.")


def _stored_onion_address() -> str | None:
    hostname = app_home() / "tor" / "onion_service" / "hostname"
    try:
        return validate_onion(hostname.read_text(encoding="ascii").strip())
    except (OSError, TorError):
        return None


def _terminal_status() -> None:
    config = load_config()
    tor_ok = shutil.which(config.tor_binary) is not None
    audio_missing = missing_audio_commands()
    try:
        load_secret()
        key_ok = True
    except ConfigError:
        key_ok = False
    address = _stored_onion_address()
    print(f"{paint('Tor:', DIM, WHITE)} {status(tor_ok)}", end="  ")
    print(f"{paint('Schlüssel:', DIM, WHITE)} {status(key_ok)}", end="  ")
    print(f"{paint('Audio:', DIM, WHITE)} {status(not audio_missing)}")
    shown_address = paint(address, CYAN) if address else paint("wird beim ersten Empfangen erstellt", DIM, WHITE)
    print(f"{paint('Onion-Adresse:', DIM, WHITE)} {shown_address}")


def _show_address() -> None:
    address = _stored_onion_address()
    if address:
        print("\n" + paint("Deine gespeicherte Onion-Adresse:", BOLD, MAGENTA))
        print(paint(address, BOLD, CYAN))
        print("Maßgeblich ist immer die Adresse, die beim Empfangen angezeigt wird.")
    else:
        print("\n" + paint("Noch keine Onion-Adresse vorhanden. Wähle zuerst ‚Gespräch empfangen‘.", YELLOW))


def _audio_test() -> None:
    config = load_config()
    print("\n" + paint("Audiotest: drei Sekunden aufnehmen …", YELLOW))
    payload = _audio(config).record_opus(3)
    print("Aufnahme wird wiedergegeben …")
    _audio(config).play_opus(payload)
    print(paint("Audiotest erfolgreich.", BOLD, GREEN))


def _number_setting(label: str, current: int, minimum: int, maximum: int) -> int:
    entered = input(f"{label} [{current}]: ").strip()
    if not entered:
        return current
    if not entered.isdigit() or not minimum <= int(entered) <= maximum:
        raise ConfigError(f"{label} muss zwischen {minimum} und {maximum} liegen")
    return int(entered)


def _settings_menu() -> None:
    config = load_config()
    print("\n" + paint("── Einstellungen ──", BOLD, MAGENTA))
    print("Enter übernimmt jeweils den bisherigen Wert.")
    try:
        config.listen_port = _number_setting("Gesprächsport", config.listen_port, 1024, 65535)
        config.socks_port = _number_setting("Tor-SOCKS-Port", config.socks_port, 1024, 65535)
        config.max_audio_seconds = _number_setting("Maximale Audiosekunden", config.max_audio_seconds, 1, 300)
        save_config(config)
        print(paint("Einstellungen sicher gespeichert.", GREEN))
    except (EOFError, ConfigError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)


def _address_for_menu() -> str:
    config = load_config()
    if config.last_address:
        prompt = f"Empfängeradresse einfügen (Enter = zuletzt verwendete {config.last_address}): "
    else:
        prompt = "Die beim Empfänger angezeigte `.onion`-Adresse einfügen: "
    try:
        entered = input(prompt).strip()
    except EOFError as exc:
        raise ConfigError("Keine Empfängeradresse eingegeben") from exc
    address = entered or config.last_address
    if not address:
        raise ConfigError("Keine Empfängeradresse eingegeben")
    address = validate_onion(address)
    config.last_address = address
    save_config(config)
    return address


def _menu_item(number: str, label: str, *, dim: bool = False) -> None:
    number_text = paint(number.rjust(2), BOLD, MAGENTA)
    label_text = paint(label, DIM, WHITE) if dim else paint(label, WHITE)
    print(f"{number_text}  {label_text}")


def _menu() -> int:
    while True:
        print("\n" + paint("═" * 60, MAGENTA))
        print(" " * 17 + brand(__version__))
        print(" " * 12 + paint("Sicherer Text und Sprache über Tor", DIM, WHITE))
        print(paint("═" * 60, MAGENTA))
        _terminal_status()
        print(paint("─" * 60, DIM, WHITE))
        _menu_item("1", "Gespräch empfangen")
        _menu_item("2", "Person anrufen")
        _menu_item("3", "Meine Onion-Adresse anzeigen")
        _menu_item("4", "Verbindungsschlüssel verwalten")
        _menu_item("5", "Audio testen (3 Sekunden)")
        _menu_item("6", "Installation ausführlich prüfen")
        _menu_item("7", "Einstellungen")
        _menu_item("0", "Beenden", dim=True)
        try:
            choice = input("Auswahl: ").strip()
        except EOFError:
            return 0

        if choice == "1":
            _ensure_initialized()
            print("\nEmpfänger wird gestartet. Dieses Terminal geöffnet lassen.")
            main(["listen"])
            _pause()
        elif choice == "2":
            _ensure_initialized()
            try:
                address = _address_for_menu()
            except (ConfigError, TorError) as exc:
                print(f"Fehler: {exc}", file=sys.stderr)
                _pause()
                continue
            main(["call", address])
            _pause()
        elif choice == "3":
            _show_address()
            _pause()
        elif choice == "4":
            _key_menu()
        elif choice == "5":
            try:
                _audio_test()
            except (AudioError, ConfigError, OSError) as exc:
                print(f"Fehler: {exc}", file=sys.stderr)
            _pause()
        elif choice == "6":
            _doctor()
            _pause()
        elif choice == "7":
            _settings_menu()
            _pause()
        elif choice == "0":
            print(paint("BRZ – OnionCall beendet.", DIM, WHITE))
            return 0
        else:
            print("Bitte eine Zahl von 0 bis 7 wählen.")


def run_terminal() -> int:
    """Entry point for the complete terminal interface."""
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
            token = getpass.getpass("Verbindungsschlüssel (Eingabe bleibt unsichtbar): ").strip()
            if not token:
                raise ConfigError("Verbindungsschlüssel darf nicht leer sein")
            import_secret(token, replace=args.replace)
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
                print(f"{paint('Deine Onion-Adresse:', BOLD, MAGENTA)} {paint(address, BOLD, CYAN)}")
                _run_listen(listener, psk, config)
            finally:
                tor.stop()
            return 0

        if args.command == "call":
            address = validate_onion(args.address)
            config.last_address = address
            save_config(config)
            tor = TorProcess(config)
            try:
                tor.start(args.tor_timeout)
                connection = socks5_connect(address, config.listen_port, config.socks_port)
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
        print(paint("\nAbgebrochen.", YELLOW, stream=sys.stderr), file=sys.stderr)
        return 130
    except (ConfigError, TorError, AuthenticationError, OSError) as exc:
        print(paint(f"Fehler: {exc}", BOLD, RED, stream=sys.stderr), file=sys.stderr)
        return 1
