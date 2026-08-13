#!/usr/bin/env python3
"""Eigenständige Terminal-Installation für OnionCall.

Benötigt Python 3.10 oder neuer. Das Skript installiert Systemprogramme,
lädt OnionCall und startet danach die vollständige Terminal-Oberfläche.
"""

from __future__ import annotations

import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

REPOSITORY = "https://github.com/BlackRabbitZ/OnionCall.git"
MIN_PYTHON = (3, 10)
MIN_REPOSITORY_VERSION = (2, 3, 0)


class InstallerError(RuntimeError):
    pass


def is_termux() -> bool:
    return "com.termux" in os.environ.get("PREFIX", "") or "TERMUX_VERSION" in os.environ


def install_root() -> Path:
    override = os.environ.get("ONIONCALL_INSTALL_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "OnionCall"
    return Path.home() / ".local" / "share" / "onioncall"


def package_manager() -> str | None:
    if is_termux():
        return "pkg"
    if platform.system() == "Darwin":
        return "brew" if shutil.which("brew") else None
    for manager in ("dnf", "apt-get", "pacman"):
        if shutil.which(manager):
            return manager
    return None


def platform_label() -> str:
    if is_termux():
        return "Android / Termux"
    if platform.system() == "Darwin":
        return "macOS"
    names = {
        "dnf": "Fedora",
        "apt-get": "Debian / Ubuntu / Raspberry Pi OS",
        "pacman": "Arch Linux",
    }
    return names.get(package_manager(), platform.system())


def required_commands() -> list[str]:
    if is_termux():
        return ["git", "tor", "opusenc", "opusdec", "ffmpeg", "termux-microphone-record", "play"]
    if platform.system() == "Darwin":
        return ["git", "tor", "opusenc", "opusdec", "rec", "play"]
    return ["git", "tor", "opusenc", "opusdec", "arecord", "aplay"]


def package_commands(manager: str) -> list[list[str]]:
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
    if shutil.which("sudo"):
        return ["sudo", *command]
    if shutil.which("pkexec"):
        return ["pkexec", *command]
    raise InstallerError("Administratorfreigabe benötigt, aber weder sudo noch pkexec wurde gefunden")


def run(command: list[str], *, cwd: Path | None = None, administrator: bool = False) -> None:
    actual = elevated(command) if administrator else command
    print("\n$ " + shlex.join(command), flush=True)
    process = subprocess.Popen(actual, cwd=cwd)
    if process.wait() != 0:
        raise InstallerError(f"Befehl fehlgeschlagen: {shlex.join(command)}")


def step(number: int, total: int, message: str) -> None:
    print(f"\n[{number}/{total}] {message}")
    print("-" * 60)


def install_system_packages() -> None:
    missing = [command for command in required_commands() if shutil.which(command) is None]
    if not missing:
        print("[OK] Tor, Git und Audio-Werkzeuge sind bereits installiert.")
        return
    manager = package_manager()
    if manager is None and platform.system() == "Darwin":
        raise InstallerError(
            "Homebrew fehlt. Installiere Homebrew ausschließlich von https://brew.sh und starte danach erneut."
        )
    if manager is None:
        raise InstallerError("Kein unterstützter Paketmanager gefunden")
    print("Fehlende Programme: " + ", ".join(missing))
    for command in package_commands(manager):
        run(command, administrator=manager in {"dnf", "apt-get", "pacman"})
    remaining = [command for command in required_commands() if shutil.which(command) is None]
    if remaining:
        raise InstallerError("Nach der Installation fehlen weiterhin: " + ", ".join(remaining))


def repository_version(source: Path) -> tuple[int, int, int]:
    text = (source / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"(\d+)\.(\d+)\.(\d+)"', text, re.MULTILINE)
    return tuple(int(part) for part in match.groups()) if match else (0, 0, 0)


def clone_or_update(root: Path) -> Path:
    source = root / "source"
    root.mkdir(parents=True, exist_ok=True)
    if (source / ".git").is_dir():
        origin = subprocess.run(
            ["git", "-C", str(source), "remote", "get-url", "origin"],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout.strip()
        if origin.rstrip("/") != REPOSITORY.rstrip("/"):
            raise InstallerError(f"Unerwartete Repository-Quelle: {origin}")
        run(["git", "-C", str(source), "pull", "--ff-only"])
    elif source.exists() and any(source.iterdir()):
        raise InstallerError(f"Installationsordner ist nicht leer und kein Git-Repository: {source}")
    else:
        run(["git", "clone", "--depth", "1", REPOSITORY, str(source)])
    if not (source / "pyproject.toml").is_file() or not (source / "onioncall" / "cli.py").is_file():
        raise InstallerError("Das geladene Repository ist kein vollständiges OnionCall-Projekt")
    if repository_version(source) < MIN_REPOSITORY_VERSION:
        raise InstallerError("Das GitHub-Repository ist älter als OnionCall 2.3.0 und muss aktualisiert werden")
    return source


def venv_executable(venv: Path, name: str) -> Path:
    return venv / "bin" / name


def create_venv(root: Path, source: Path) -> Path:
    venv = root / "venv"
    if not venv_executable(venv, "python").exists():
        command = [sys.executable, "-m", "venv"]
        if is_termux():
            command.append("--system-site-packages")
        command.append(str(venv))
        run(command, cwd=source)
    return venv


def install_onioncall(source: Path, venv: Path) -> None:
    python = venv_executable(venv, "python")
    if not is_termux():
        run([str(python), "-m", "pip", "install", "--upgrade", "pip"], cwd=source)
    run([str(python), "-m", "pip", "install", "--upgrade", "."], cwd=source)


def private_write(path: Path, text: str, *, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o700 if executable else 0o600)


def create_launchers(source: Path, venv: Path) -> None:
    executable = venv_executable(venv, "onioncall")
    shell_text = f'#!/bin/sh\ncd {shlex.quote(str(source))}\nexec {shlex.quote(str(executable))} terminal "$@"\n'
    launcher = Path.home() / ".local" / "bin" / "onioncall-terminal"
    private_write(launcher, shell_text, executable=True)
    print(f"[OK] Terminal-Starter: {launcher}")
    if is_termux():
        shortcut_dir = Path.home() / ".shortcuts"
        if shortcut_dir.exists():
            private_write(shortcut_dir / "OnionCall-Terminal", shell_text, executable=True)
    elif platform.system() == "Darwin":
        command = Path.home() / "Applications" / "OnionCall-Terminal.command"
        private_write(command, shell_text, executable=True)
        print(f"[OK] macOS-Starter: {command}")
    else:
        desktop = Path.home() / ".local" / "share" / "applications" / "onioncall-terminal.desktop"
        private_write(
            desktop,
            "[Desktop Entry]\nType=Application\nName=OnionCall Terminal\n"
            "Comment=Sicherer Text und Sprache über Tor\n"
            f"Exec={launcher}\nTerminal=true\nCategories=Network;Chat;Security;\n",
        )
        desktop.chmod(0o644)
        print(f"[OK] Anwendungsstarter: {desktop}")


def verify(venv: Path) -> None:
    executable = venv_executable(venv, "onioncall")
    run([str(executable), "--version"])
    result = subprocess.run([str(executable), "doctor"], check=False)
    if result.returncode not in {0, 1}:
        raise InstallerError("OnionCall-Diagnose konnte nicht ausgeführt werden")


def install() -> None:
    if sys.version_info < MIN_PYTHON:
        raise InstallerError("Python 3.10 oder neuer wird benötigt")
    root = install_root()
    print(f"System: {platform_label()}")
    print(f"Installationsziel: {root}")
    step(1, 6, "Systemprogramme prüfen und installieren")
    install_system_packages()
    step(2, 6, "OnionCall-Repository laden oder aktualisieren")
    source = clone_or_update(root)
    step(3, 6, "Getrennte Python-Umgebung erstellen")
    venv = create_venv(root, source)
    step(4, 6, "OnionCall installieren")
    install_onioncall(source, venv)
    step(5, 6, "Terminal-Starter erstellen")
    create_launchers(source, venv)
    step(6, 6, "Installation prüfen")
    verify(venv)
    print("\n============================================================")
    print("DONE – OnionCall Terminal wurde vollständig installiert")
    print("============================================================")


def launch() -> None:
    executable = venv_executable(install_root() / "venv", "onioncall")
    if not executable.exists():
        raise InstallerError("OnionCall ist noch nicht installiert. Wähle zuerst 1.")
    os.execv(executable, [str(executable), "terminal"])


def menu() -> int:
    while True:
        print("\n============================================================")
        print("                  OnionCall Terminal Setup")
        print("============================================================")
        print(f"System: {platform_label()}")
        print("1  OnionCall vollständig installieren oder aktualisieren")
        print("2  Installiertes OnionCall Terminal starten")
        print("3  Installationspfad anzeigen")
        print("0  Beenden")
        try:
            choice = input("Auswahl: ").strip()
        except EOFError:
            return 0
        try:
            if choice == "1":
                install()
                if input("\nOnionCall jetzt starten? [J/n]: ").strip().lower() not in {"n", "nein"}:
                    launch()
            elif choice == "2":
                launch()
            elif choice == "3":
                print(f"Quellcode: {install_root() / 'source'}")
                print(f"Python-Umgebung: {install_root() / 'venv'}")
            elif choice == "0":
                print("Setup beendet.")
                return 0
            else:
                print("Bitte 0, 1, 2 oder 3 wählen.")
        except (InstallerError, OSError, subprocess.SubprocessError) as exc:
            print(f"\nFEHLER: {exc}", file=sys.stderr)
        if choice != "0":
            try:
                input("\nEnter drücken, um zum Setup-Menü zurückzukehren …")
            except EOFError:
                return 0


if __name__ == "__main__":
    raise SystemExit(menu())
