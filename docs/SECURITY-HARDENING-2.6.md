# Security Hardening 2.6 – Umsetzung der Review-Punkte

| Review-Punkt | Umsetzung |
|---|---|
| `direct-call` / `direct-listen` umgehen Tor | Beide Befehle akzeptieren ausschließlich literale Loopback-IP-Adressen. Externe IPs und Hostnamen werden abgelehnt. |
| Erster Client beendet Listener vor Authentifizierung | `accept_authenticated()` hält den Listener offen, verwirft fehlgeschlagene Handshakes und schließt erst nach erfolgreicher Authentifizierung. |
| Ein gemeinsamer PSK | `peer-add`, `peer-list`, `--peer`: getrennte 256-Bit-Schlüssel pro Kontakt. `default` bleibt als Migrationsprofil. |
| Keine stabile Identitätsbindung | Ed25519-Installationsidentität + signierter v3-Handshake + TOFU-Fingerprint-Pinning nach PSK-Authentifizierung. |
| Caller startet ebenfalls Onion Service | `TorProcess(service=False)` im Call-Pfad: nur SOCKS, keine `HiddenService*`-Direktiven. |
| Linkability durch persistente Onion-Adresse | Optional `listen --temporary-onion`; temporäres Hidden-Service-Verzeichnis wird nach der Sitzung gelöscht. |
| Installation/Update über Clearnet | Setup lädt standardmäßig nichts nach; `--tor` nutzt `torsocks`. `private-update.sh` hat keinen Clearnet-Fallback. |
| Nicht verifizierte Releases | Release-Workflow erzeugt SHA-256-Manifest und GitHub Artifact Attestations. Eigene signierte Git-Tags werden in `RELEASING.md` empfohlen. |
| Opus an externen Decoder | Ogg/Opus-Vorprüfung, Größen-/Dauerlimit, Linux-`prlimit` für RAM/CPU/File-Size, enger Timeout, minimierte Umgebung. |
| Keine OS-Killswitch-Garantie | `onioncall-killswitch-linux.sh` trennt Tor und App in systemd-Units; App erhält `IPAddressDeny=any` + `IPAddressAllow=localhost`. Kein Fallback, wenn Filter nicht unterstützt werden. |
| Browser-GUI | Status-API tokenpflichtig, Host-/Origin-Prüfung, CSP, COOP, CORP, COEP, Permissions-Policy, Frame-/Referrer-/Cache-Schutz. |

## Automatisierte Regressionstests

Die Tests prüfen unter anderem:

- externe Ziele im Direktmodus werden abgelehnt,
- Client-Torrc enthält keinen Hidden Service,
- Hidden-Service-Forwarding zeigt nur auf Loopback,
- ein fehlerhafter erster Client verbraucht den Listener nicht,
- falscher PSK wird abgelehnt,
- geänderter Ed25519-Fingerprint wird abgelehnt,
- per-peer Schlüssel sind unterschiedlich,
- Nicht-Opus-Daten erreichen den Decoder nicht,
- lokale Web-API verlangt Token und liefert Security Header,
- direkte `socket.create_connection`-Verwendung wird außerhalb des Tor-Netzwerkmoduls als Regression erkannt.
