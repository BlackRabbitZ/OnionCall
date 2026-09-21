# Changelog

## 2.7.5 - 2026-09-21

- Statusfarben der bestehenden Haupt-GUI vereinheitlicht, ohne Layout oder Bedienelemente zu verändern.
- Rot: nicht gestartet, fehlt oder Fehler.
- Gelb: wartet, verbindet oder ist vorübergehend beschäftigt.
- Grün: aktiv, bereit oder verbunden.
- Insbesondere wird `Tor: aktiv` jetzt grün statt gelb dargestellt.

## 2.7.4 - 2026-09-21

- Windows-Installer-Ausgaben und Python-Unterprozesse werden deterministisch als UTF-8 behandelt.
- Behebt `UnicodeEncodeError: charmap codec can't encode character \u2192` auf Windows-/PowerShell-Systemen mit Legacy-Codepage.
- Setup-Backend verwendet in Statusausgaben zusätzlich ASCII `->` statt des Unicode-Pfeils.
- pip-, Init- und Starter-Unterprozesse erhalten `PYTHONIOENCODING=utf-8` und `PYTHONUTF8=1`.
- Haupt-GUI unverändert.

## 2.7.3 - 2026-09-21

- Windows-Installer: pip nutzt für private Downloads keinen direkten SOCKS-Proxy mehr.
- Neuer lokaler HTTP-CONNECT-zu-Tor-SOCKS-Bridge verhindert urllib3/pip-Kompatibilitätsfehler mit `proxy_ssl_context`.
- TLS bleibt Ende-zu-Ende zwischen pip und PyPI aktiv; Hostnamen werden weiterhin durch Tor aufgelöst.
- Haupt-GUI unverändert.

## 2.7.2 - 2026-09-21

- Windows-Installer: pip/Tor-Kompatibilitätsfehler `key_proxy_ssl_context` behoben.
- pip wird beim privaten Tor-Installationspfad über einen lokalen Kompatibilitäts-Starter ausgeführt; die TLS-Prüfung und SOCKS5h-Namensauflösung bleiben aktiv.
- Haupt-GUI unverändert.

## 2.7.1 - 2026-09-21

- Geführten lokalen Browser-Installer wiederhergestellt.
- Windows: fehlt Tor, lädt das Setup automatisch das offizielle Tor Expert Bundle 15.0.23 vom Tor Project.
- Tor-Bootstrap wird gegen die offizielle SHA-256-Prüfsumme geprüft.
- Nach dem Tor-Bootstrap werden fehlende Python-Abhängigkeiten standardmäßig über Tor installiert.
- Python-only Start bleibt erhalten; keine OnionCall-EXE-Launcher.
- OnionCall-Haupt-GUI (`onioncall/webgui.py`) unverändert.

## 2.7.0 - 2026-09-21

- Tor v3 Client Authorization ergänzt.
- Linux-Killswitch Python-only.
- Windows-Killswitch ergänzt.
- Private Installation/Updates über Tor erweitert.
- Sichtbare GUI unverändert gegenüber 2.6.2.

## 2.6.1

- Windows/Python-Setup vereinfacht: OnionCall erzeugt keine eigenen `.exe`-CLI-Launcher mehr.
- `[project.scripts]` entfernt; Start erfolgt direkt über `py Start-OnionCall.py` oder `python -m onioncall.cli`.
- Setup installiert ausschließlich fehlende Python-Abhängigkeiten und verwendet `--no-warn-script-location`, damit normale Python-Installationen nicht mit PATH-Warnungen verwirrt werden.
- `Start-OnionCall.py` und `Start-OnionCall-Terminal.py` hinzugefügt.
- Setup bootstrapt `pip` bei Bedarf über `ensurepip`.

## 2.6.0

### Security
- direct-call/direct-listen strikt auf Loopback begrenzt.
- Listener bleibt nach nicht authentifizierten Verbindungen aktiv.
- Per-peer PSKs und Kontaktprofile hinzugefügt.
- Ed25519-Installationsidentität und Fingerprint-Pinning hinzugefügt.
- Protokoll auf v3 angehoben; beide Seiten müssen 2.6 verwenden.
- Caller startet keinen eigenen Onion Service mehr.
- Optionale temporäre Onion-v3-Adresse pro Empfangssitzung.
- Audio-Format-, Größen-, Dauer- und Ressourcenlimits.
- GUI-Status-API tokenpflichtig; zusätzliche Security Header.
- Optionaler Linux/systemd OS-Killswitch.
- Tor-only Update-Skript ohne Clearnet-Fallback.
- CI + Release-Hashing + GitHub Artifact Attestations.
