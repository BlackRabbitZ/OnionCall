# Sicherheitsmodell von OnionCall v2

## Unterstützte Versionen

| Version | Sicherheitsupdates |
|---|---|
| 2.2.x | Ja |
| 2.0.x–2.1.x | Nur kritische Fehler; Aktualisierung empfohlen |
| älter als 2.0 | Nein; anderes und inkompatibles Protokoll |

## Schutzziele

- Inhalt und Nachrichtentypen werden mit ChaCha20-Poly1305 verschlüsselt und authentifiziert.
- Ein zufälliger 256-Bit-Verbindungsschlüssel authentifiziert beide Endpunkte.
- Für jede Verbindung werden neue kurzlebige X25519-Schlüssel erzeugt.
- Sitzungskeys werden mit HKDF-SHA-256 aus X25519-Ergebnis, Verbindungsschlüssel und vollständigem Handshake-Transkript abgeleitet.
- Streng ansteigende 64-Bit-Sequenznummern erkennen Wiederholung und Umordnung.
- Header, Typ, Sequenznummer und Länge sind Associated Data der AEAD-Verschlüsselung.
- Text und Audio haben feste Größenlimits, bevor Daten vollständig eingelesen werden.
- Schlüssel, Tor-Daten und temporäre Audioinhalte erhalten Rechte 0600 beziehungsweise 0700.
- Setup- und Anwendungs-GUI binden ausschließlich an Loopback und schützen schreibende Aktionen mit einem zufälligen Sitzungstoken sowie Host-/Origin-Prüfungen.

## Nicht abgedeckt

- Ein kompromittiertes Endgerät kann Mikrofon, Klartext und Schlüssel auslesen.
- Tor verhindert keine globale zeitliche Verkehrskorrelation.
- Der Verbindungsschlüssel muss über einen bereits sicheren Kanal ausgetauscht werden.
- Metadaten wie Zeitpunkt, Dauer und ungefähre Größe einer Übertragung können beobachtbar sein.
- Die Implementierung wurde noch nicht unabhängig auditiert.
- Ein kompromittierter Browser, eine schädliche Browser-Erweiterung oder ein anderer Prozess desselben lokalen Benutzerkontos liegt außerhalb des Schutzmodells.

## Protokollübersicht

Der Client sendet Protokollkennung, Version, Rolle, 32 Zufallsbytes und seinen kurzlebigen X25519-Schlüssel. Der Server antwortet analog und hängt einen HMAC-SHA-256-Beweis über das gesamte Transkript an. Nach dessen Prüfung sendet der Client seinen eigenen Transkriptbeweis.

Anschließend werden ausschließlich binäre AEAD-Frames übertragen. Der Nonce besteht aus vier Nullbytes und der 64-Bit-Sequenznummer; beide Richtungen besitzen getrennte zufällige Schlüssel. Ein Nonce wird dadurch unter demselben Schlüssel nie wiederverwendet.

## Schwachstellen melden

Bitte keine realen Geheimnisse oder Onion-Adressen in einen öffentlichen Fehlerbericht schreiben. Verwende nach dem Hochladen die Funktion **Security → Report a vulnerability** des GitHub-Repositories. Falls Private Vulnerability Reporting noch nicht aktiviert ist, veröffentliche keine technischen Details; kontaktiere die Repository-Verantwortlichen zunächst über einen privaten Kanal.

Eine gute Meldung enthält betroffene Version, Plattform, reproduzierbare Schritte mit ausschließlich künstlichen Testdaten, erwartete Auswirkung und – sofern vorhanden – einen minimalen Patch. Der Eingang sollte innerhalb von sieben Tagen bestätigt werden. Eine Veröffentlichung erfolgt koordiniert nach Bereitstellung eines Fixes.

Bis zu einem unabhängigen Audit sollte OnionCall nicht als alleinige Schutzmaßnahme in einer Hochrisikosituation eingesetzt werden.
