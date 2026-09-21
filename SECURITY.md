# Sicherheitsmodell – OnionCall 2.6

## Ziele

OnionCall versucht, die öffentliche IP der Kommunikationspartner gegenüber der jeweils anderen Seite nicht offenzulegen und die transportierten Inhalte zusätzlich Ende-zu-Ende zu authentifizieren und zu verschlüsseln.

### Netzwerk-Invarianten

1. Der normale Outbound-Pfad verbindet nur zu `127.0.0.1:<Tor-SOCKS>`.
2. Onion-Ziele werden als SOCKS5-Domain an Tor übergeben; OnionCall führt dafür keine lokale DNS-Auflösung durch.
3. Listener binden ausschließlich an Loopback.
4. Der Diagnose-Direktmodus akzeptiert ausschließlich `127.0.0.1` und `::1`.
5. Der Caller startet keinen Hidden Service.
6. Der optionale Linux-Killswitch erzwingt für den OnionCall-Prozess `IPAddressDeny=any` + `IPAddressAllow=localhost`.

## Handshake v3

Jede Sitzung kombiniert:

- 256-Bit PSK pro Kontaktprofil,
- frisches X25519-Schlüsselpaar pro Verbindung,
- langfristige Ed25519-Installationsidentität,
- zufällige 256-Bit Nonces,
- HMAC-SHA-256 über das vollständige Transcript,
- Ed25519-Signaturen über das Transcript,
- HKDF-SHA-256,
- getrennte Richtungs-Schlüssel,
- ChaCha20-Poly1305 pro Frame,
- strikt monotone Sequenznummern.

Der Ed25519-Fingerprint wird nach einer erfolgreich PSK-authentifizierten ersten Verbindung gepinnt. Ändert er sich später, wird die Verbindung vor Sitzungsbeginn abgebrochen.

## DoS-Härtung

Ein eingehender TCP-Client verbraucht den Listener nicht mehr dauerhaft. Fehlgeschlagene Handshakes werden geschlossen und der Listener akzeptiert weiter. Eine kleine capped Verzögerung erschwert blindes Flooding. Das ist kein vollständiger DoS-Schutz gegen einen globalen oder sehr ressourcenstarken Angreifer.

## Audio

Empfangene Audiodaten werden vor dem Decoder auf Ogg/Opus-Merkmale und Größe geprüft. Die dekodierte WAV-Datei besitzt ein aus der maximalen Spieldauer abgeleitetes Größenlimit. Auf Linux wird `opusdec`, sofern `prlimit` vorhanden ist, mit RAM-, CPU- und File-Size-Limits gestartet.

## Lokale Web-GUI

- Bind: 127.0.0.1
- Host-Allowlist
- API-Token für GET-Status und POST-Aktionen
- Origin-Prüfung für POST
- CSP mit Nonce
- X-Frame-Options: DENY
- Referrer-Policy: no-referrer
- Permissions-Policy
- COOP/CORP/COEP
- Cache-Control: no-store
- Request-Größenlimit

## Supply Chain

Das lokale Setup lädt nicht stillschweigend Abhängigkeiten. `private-update.sh` verwendet `torsocks` und bricht ohne Tor ab. Tag-Releases sollen ausschließlich über den Release-Workflow entstehen; der Workflow erzeugt SHA-256-Dateien und GitHub Artifact Attestations.

## Nicht-Ziele / verbleibende Risiken

- Schutz gegen globale Timing-/Traffic-Korrelation ist nicht garantiert.
- Endpoint-Kompromittierung, Keylogger, Malware oder physischer Zugriff werden nicht gelöst.
- Metadaten wie Erreichbarkeitszeiten können trotz Onion Services Rückschlüsse ermöglichen.
- Externe Audio-Decoder bleiben eine zusätzliche Angriffsfläche.
- systemd-Killswitch ist Linux-spezifisch.

## Schwachstellen melden

Bitte sensible Sicherheitsprobleme nicht zuerst öffentlich mit Exploit-Details posten. Nutze nach Möglichkeit GitHubs private Security-Advisory-Funktion des Repositorys.

## OS-Killswitch und Tor Client Authorization (2.7.0)

- Linux: `scripts/onioncall-killswitch-linux.sh` startet Tor außerhalb der eingeschränkten systemd-Unit und OnionCall innerhalb einer Unit, die nur Loopback-Netzwerkzugriffe erlaubt.
- Windows: `scripts/onioncall-killswitch-windows.ps1` sperrt direkte ausgehende Verbindungen des projektspezifischen `.venv\Scripts\python.exe` und lässt Loopback für den lokalen Tor-SOCKS offen. Die Regel schützt den OnionCall-Python-Prozess; fremde, absichtlich gestartete Netzwerkprogramme unterliegen eigenen Firewallregeln.
- Tor v3 Client Authorization ist optional und wird zusätzlich zum OnionCall-PSK/Identity-Handshake ausgewertet. Server-Keys liegen unter `~/.config/onioncall/tor_auth/server`, Client-Keys unter `~/.config/onioncall/tor_auth/client`.
- Das Setup verwendet für fehlende Python-Pakete standardmäßig Tor und bricht ohne Tor ab. Direkter Download ist nur mit `--allow-clearnet` möglich.
