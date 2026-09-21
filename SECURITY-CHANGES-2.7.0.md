# Sicherheitsänderungen 2.7.0

Die sichtbare OnionCall-GUI wurde gegenüber 2.6.2 nicht verändert.

- Tor v3 Client Authorization (`.auth` / `.auth_private`).
- Linux-Killswitch auf Python-only angepasst.
- Windows-Killswitch für `.venv\Scripts\python.exe`.
- Setup erzeugt `.venv`, keine OnionCall-EXE-Launcher.
- Fehlende Python-Abhängigkeiten standardmäßig über temporären Tor-SOCKS.
- Clearnet nur mit `--allow-clearnet`.
- Privater Windows-Git-Updater über Tor ohne Fallback.

## Tor Client Authorization

Service: `py -m onioncall.cli tor-auth-create NAME`

Client: `py -m onioncall.cli tor-auth-import <ONION-ADRESSE> --name NAME` (Token wird verdeckt abgefragt)

Widerruf: `py -m onioncall.cli tor-auth-revoke NAME`

## Windows-Killswitch

`powershell -ExecutionPolicy Bypass -File scripts\onioncall-killswitch-windows.ps1 status`

## Linux-Killswitch

`scripts/onioncall-killswitch-linux.sh call <adresse.onion> --peer default`

`scripts/onioncall-killswitch-linux.sh listen --peer default`
