# Sicherheitsmodell – OnionCall 2.7.6

## Ziele

OnionCall versucht, die öffentliche IP der Kommunikationspartner gegenüber der jeweils anderen Seite nicht offenzulegen und transportierte Inhalte zusätzlich Ende-zu-Ende zu authentifizieren und zu verschlüsseln.

### Netzwerk-Invarianten

1. Der normale Outbound-Pfad verbindet nur zu `127.0.0.1:<Tor-SOCKS>`.
2. Onion-Ziele werden als SOCKS5-Domain an Tor übergeben; OnionCall führt dafür keine lokale DNS-Auflösung durch.
3. Listener binden ausschließlich an Loopback.
4. Der Diagnose-Direktmodus akzeptiert exakt `127.0.0.1` und `::1`.
5. Onion-v3-Adressen werden nicht nur syntaktisch, sondern auch anhand Version und SHA3-Prüfsumme validiert.
6. Der Caller startet keinen Hidden Service.
7. Optionale OS-Killswitches begrenzen direkte Netzwerkzugriffe des OnionCall-Prozesses.

## Handshake v3

Jede Sitzung kombiniert einen zufälligen 256-Bit-PSK pro Kontaktprofil, ein frisches X25519-Schlüsselpaar, eine langfristige Ed25519-Installationsidentität, zufällige Nonces, HMAC-SHA-256 und Ed25519-Signaturen über das Transcript, HKDF-SHA-256 sowie ChaCha20-Poly1305 mit getrennten Richtungs-Schlüsseln und monotonen Sequenznummern.

Der Ed25519-Fingerprint wird nach einer erfolgreich PSK-authentifizierten ersten Verbindung gepinnt. Ändert er sich später, wird die Verbindung vor Sitzungsbeginn abgebrochen.

## DoS-Härtung

Pre-Auth-Verbindungen werden in einem kleinen, begrenzten Worker-Pool verarbeitet. Ein einzelner Client, der den Handshake offen hält, blockiert deshalb nicht mehr den gesamten Listener. Der Standard-Handshake-Timeout beträgt fünf Sekunden; überzählige unauthentifizierte Sockets werden sofort geschlossen. Das begrenzt Ressourcenverbrauch, ist aber kein vollständiger Schutz gegen einen globalen oder sehr ressourcenstarken DoS-Angreifer.

## Audio

Eingehende Audiodaten werden vor einem nativen Decoder strikt als einzelner Ogg/Opus-Stream geprüft: Capture Pattern, Ogg-Version, Stream-Serial, Seitensequenz, Continuation/BOS/EOS, Seitengrößen, Ogg-CRC, `OpusHead`, `OpusTags`, Packet-Limits und Gesamtgröße. Dekodierte PCM-Daten haben feste Kanal-/Samplerate-/Größen-/Dauerlimits. Linux nutzt zusätzlich `prlimit`, sofern vorhanden.

Windows verwendet einen eigenen FFmpeg/DirectShow-Pfad (`ffmpeg`/`ffplay`) statt Linux-ALSA-Programme. `ONIONCALL_AUDIO_DEVICE` kann einen Mikrofon-Gerätenamen explizit festlegen.

Ein externer nativer Decoder bleibt trotz dieser Härtung eine zusätzliche Angriffsfläche. Die Prüfung reduziert unnötige Parser-Eingaben, ersetzt aber keine vollständige OS-Sandbox eines fehlerhaften Decoders.

## Private Schlüssel

- OnionCall-App-Schlüssel werden atomar geschrieben und auf POSIX nur mit privaten Dateirechten akzeptiert.
- Unter Windows werden `conversation.key`, Kontakt-PSKs und `identity.key` mit der benutzergebundenen Windows-DPAPI verschlüsselt. Bestehende Klartextdateien werden beim ersten erfolgreichen Laden migriert.
- Tor-Client-Authorization-Dateien bleiben im von Tor benötigten Klartextformat. OnionCall prüft sie auf sichere Dateirechte und verweigert Symlinks; eine DPAPI-Verschlüsselung wäre hier ohne separaten Entschlüsselungs-/Staging-Schritt nicht mit Tor kompatibel.
- Importierte PSKs müssen als vollständiges `onioncall:v2:`-Token vorliegen. Offensichtlich konstruierte/repetitive Schlüssel werden abgewiesen. Ein beliebiger 32-Byte-Wert kann jedoch nicht zuverlässig auf echte Entropie geprüft werden; nur von OnionCall erzeugte Schlüssel verwenden.

## Lokale Web-GUI

Die GUI bindet an `127.0.0.1`, verwendet Host-Allowlist, zufälliges API-Token, Origin-Prüfung für POST, CSP-Nonce, Frame-/Referrer-/Permissions-/COOP-/CORP-/COEP-Header, `Cache-Control: no-store` und Request-Größenlimits. Status-API und mutierende Aktionen benötigen das Sitzungstoken.

## Supply Chain und Updates

Runtime-Abhängigkeiten sind für 2.7.6 auf konkrete Versionen gepinnt und zusätzlich in `requirements.lock` dokumentiert. Das Setup prüft installierte Distributionen anhand ihrer tatsächlichen Paketversionen statt nur auf erfolgreiche Imports.

Private Update-Skripte fetchen weiterhin ausschließlich über Tor, installieren einen neuen Commit aber erst, wenn mindestens eine Vertrauensbedingung erfüllt ist: lokal verifizierbare Commit-Signatur, lokal verifizierbarer signierter Tag oder ein explizit außerbandig geprüfter `ONIONCALL_TRUSTED_COMMIT`. Ein bloßer HTTPS-/Tor-Transport wird nicht mehr als Herkunftsprüfung behandelt.

## Nicht-Ziele / verbleibende Risiken

- Schutz gegen globale Timing-/Traffic-Korrelation ist nicht garantiert.
- Endpoint-Kompromittierung, Keylogger, Malware oder physischer Zugriff werden nicht gelöst.
- Metadaten wie Erreichbarkeitszeiten können trotz Onion Services Rückschlüsse ermöglichen.
- Externe Audio-Decoder bleiben trotz Container-/Ressourcenprüfung eine zusätzliche Angriffsfläche.
- Tor-Client-Authorization-Private-Keys müssen für Tor in dessen erwartetem Dateiformat vorliegen.
- Unter POSIX schützt OnionCall App-Schlüssel primär durch restriktive Dateirechte; echte Verschlüsselung-at-rest erfordert ein separates Unlock-/Keychain-Modell.

## Schwachstellen melden

Sensible Sicherheitsprobleme bitte nicht zuerst öffentlich mit Exploit-Details posten. Nach Möglichkeit GitHubs private Security-Advisory-Funktion des Repositorys verwenden.
