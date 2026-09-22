# BRZ – OnionCall 2.7.6

OnionCall ist ein experimentelles, lokales Kommunikationswerkzeug für **Text und Push-to-talk-Sprachnachrichten über Tor Onion Services**. Zusätzlich zum Tor-Transport nutzt OnionCall eine eigene Ende-zu-Ende-verschlüsselte Sitzung mit X25519, Ed25519, PSK-Authentifizierung, HKDF-SHA256 und ChaCha20-Poly1305.

> **Status: Alpha.** Dieses Projekt wurde nicht unabhängig sicherheitsgeprüft. Für Hochrisiko-Kommunikation nicht als alleinige Schutzmaßnahme einsetzen.

## Was 2.7.6 ändert

- Web-GUI-JavaScript-Regression behoben und Tests aktualisiert.
- Pre-Auth-Handshakes sind begrenzt parallelisiert; ein idle Client blockiert den Listener nicht mehr.
- Ogg/Opus wird vor dem nativen Decoder strukturell inklusive CRC geprüft.
- Windows nutzt FFmpeg/DirectShow und ffplay statt Linux-ALSA-Kommandos.
- Installer prüft exakte Dependency-Versionen; Runtime/Dev-Versionen sind gepinnt.
- Private Updates akzeptieren nur verifizierte Commits/Tags oder einen explizit gepinnten Commit-Hash.
- Onion-v3-Adressen werden inklusive Version und SHA3-Prüfsumme validiert.
- Direkter Diagnosemodus erlaubt exakt `127.0.0.1` und `::1`.
- OnionCall-App-Schlüssel werden unter Windows per benutzergebundenem DPAPI geschützt; POSIX-Dateirechte werden strikt geprüft.
- Importierte PSKs müssen vollständige `onioncall:v2:`-Tokens sein; offensichtlich schwache Muster werden abgelehnt.

Details: [`SECURITY-CHANGES-2.7.6.md`](SECURITY-CHANGES-2.7.6.md)

## Voraussetzungen

- Python 3.10+
- Tor
- Windows Audio: FFmpeg/ffplay werden vom Browser-Installer automatisch projektlokal eingerichtet
- Linux Audio: `arecord`, `aplay`, `opusenc`, `opusdec`
- macOS Audio: `rec`, `play`, `opusenc`, `opusdec`
- Termux: Termux:API, FFmpeg, opus-tools und SoX

Unter Windows kann das Mikrofon optional festgelegt werden:

```powershell
$env:ONIONCALL_AUDIO_DEVICE="Mikrofonname aus FFmpeg/DirectShow"
```

## Installation

### Windows

**Empfohlen: Browser-Installer ohne sichtbares Terminal**

Doppelklick auf:

```text
OnionCall-Setup.cmd
```

Alternativ aus PowerShell/CMD:

```powershell
py OnionCall-Setup.py
```

`OnionCall-Setup.py` öffnet automatisch die lokale Setup-Oberfläche im Browser. Der Installer lauscht ausschließlich auf `127.0.0.1`, schützt seine API mit einem zufälligen Setup-Token und führt die eigentliche Installationslogik im Hintergrund aus.

Unter Windows richtet der Installer zusätzlich **FFmpeg 9.0.2 Essentials** projektlokal unter `tools/ffmpeg/` ein. Die Download-Datei wird vor dem Entpacken gegen eine fest hinterlegte SHA-256-Prüfsumme geprüft. Standardmäßig erfolgt auch dieser Download über Tor; bei bewusst aktiviertem **Direkten Paketdownload** direkt per HTTPS. Eine globale PATH-Änderung ist nicht nötig.

Das klassische Terminal-Setup bleibt bewusst separat verfügbar:

```powershell
py OnionCall-Terminal-Setup.py
```

Nach der Einrichtung kannst du OnionCall direkt im Browser-Installer über **OnionCall starten** öffnen oder manuell starten:

```powershell
.\.venv\Scripts\python.exe Start-OnionCall.py
```

### Linux / macOS

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.lock
./.venv/bin/python -m pip install --no-deps -e .
./.venv/bin/python Start-OnionCall.py
```

## Terminal

```bash
python -m onioncall terminal
python -m onioncall doctor
python -m onioncall peer-add alice
python -m onioncall listen --peer alice
python -m onioncall call <adresse>.onion --peer alice
```

## Tor Client Authorization

```bash
python -m onioncall tor-auth-create laptop
python -m onioncall tor-auth-import <service>.onion --name server
python -m onioncall tor-auth-list
```

## Sicherheitsmodell

Der normale Verbindungsweg bindet die Anwendung ausschließlich an Loopback und übergibt `.onion`-Ziele als SOCKS5-Domain an Tor. OnionCall ergänzt Tor durch einen authentifizierten Handshake mit ephemerem X25519, Ed25519-Identität, einem pro Kontakt geteilten 256-Bit-Schlüssel und getrennten Sitzungsschlüsseln je Richtung. Nachrichtenframes sind per ChaCha20-Poly1305 authentifiziert und verwenden monotone Sequenznummern gegen Replay/Umordnung.

Siehe [`SECURITY.md`](SECURITY.md) für Grenzen und Threat Model.

## Tests

```bash
python -m unittest discover -s tests -v
python -m compileall -q onioncall scripts tests
```

## Private Updates

Linux/macOS:

```bash
scripts/private-update.sh
```

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\private-update-windows.ps1
```

Seit 2.7.6 wird ein Update vor dem Merge zusätzlich authentifiziert. Ohne lokal verifizierbare Commit-/Tag-Signatur oder einen vorher außerbandig geprüften `ONIONCALL_TRUSTED_COMMIT` wird abgebrochen.
