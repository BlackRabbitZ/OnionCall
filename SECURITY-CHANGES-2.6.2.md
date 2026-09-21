# OnionCall 2.6.2 – Security-only Test Build

Diese Testversion behält die bekannte OnionCall-Oberfläche bei und ändert nur sicherheitsrelevante Backend-/Installationslogik.

## Enthaltene Härtungen

- `direct-call` und `direct-listen` akzeptieren nur Loopback-Ziele.
- Ein nicht authentifizierter erster Client beendet den Listener nicht mehr.
- Der anrufende Client startet keinen unnötigen Onion-Service.
- Tor-Client- und Onion-Service-Modus sind getrennt; Forwarding bleibt auf Loopback.
- Per-Peer-Schlüssel und Ed25519-Identität/Fingerprint-Pinning sind im Backend enthalten.
- Audioeingaben werden vor dem Decoder geprüft und begrenzt.
- Lokale Web-GUI bleibt auf Loopback und nutzt Token-, Origin-/Host-Prüfungen sowie zusätzliche Security-Header.
- Status-API benötigt ebenfalls das lokale Sitzungstoken.
- Das Python-Setup erzeugt keine OnionCall-`.exe`-Launcher.
- Start erfolgt mit `py Start-OnionCall.py` bzw. `python3 Start-OnionCall.py`.

## GUI

Die sichtbare GUI wurde auf das Layout des aktuellen GitHub-Projekts zurückgesetzt. Die einzige unsichtbare JavaScript-Anpassung ist das Mitsenden des lokalen Sitzungstokens beim Statusabruf, weil die Status-API nun geschützt ist.
