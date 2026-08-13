# Änderungsprotokoll

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert. Das Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/), die Versionierung an [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

### Geändert

- plattformneutrale README und vollständige Installationsanleitung für Fedora, Debian/Ubuntu, Raspberry Pi OS, Arch, macOS und Termux; Tor wird deutlich als Voraussetzung genannt
- README mit Inhaltsverzeichnis, klarer Abschnittshierarchie und plattformbezogenen Sprungmarken übersichtlicher gestaltet
- ausführliche Zwei-Geräte-Anleitung ergänzt: Rollen, Schlüsselaustausch, richtige Empfängeradresse, Rollenwechsel und Fehlerhilfe für SOCKS-Code 4
- Schlüsselübertragung präzisiert: vollständiger Kopierbereich, unsichtbare Eingabe, Erfolgskontrolle und Warnung vor unsicheren Kommandozeilenargumenten
- doppelten `set-secret`-Befehl und den Fehler `unrecognized arguments` dokumentiert; Schlüsselwerte als Kommandozeilenargument technisch deaktiviert
- geführten Startbildschirm für Empfangen, Anrufen, Schlüsseleinrichtung und Diagnose ergänzt; letzter Gesprächspartner wird lokal gemerkt
- Sitzungsbedienung vereinfacht: normaler Text sendet direkt, `a` nimmt fünf Sekunden Audio auf und `q` beendet
- Verwechslungen zwischen einer `.onion`-Adresse und einem `onioncall:v2:`-Schlüssel werden mit einer gezielten Erklärung abgewiesen
- Unterstützung für aktuelle `cryptography`-Pakete bis vor Version 51, insbesondere für Termux

### Sicherheit

- `onioncall set-secret` fragt den Verbindungsschlüssel ohne Argument verdeckt ab, damit er nicht in der Shell-History erscheint

### Geplant

- reale Integrationstests auf Linux, macOS und Android/Termux
- Fuzzing des Handshakes und Frame-Parsers
- unabhängige kryptografische Prüfung

## [2.0.0] – 2026-08-13

### Hinzugefügt

- eigenständiges OnionCall-v2-Protokoll
- kurzlebiger X25519-Schlüsselaustausch
- ChaCha20-Poly1305 für authentifizierte Verschlüsselung
- HMAC-SHA-256 zur gegenseitigen Handshake-Authentifizierung
- richtungsgetrennte Sitzungsschlüssel und strikte Sequenznummern
- begrenzte Text- und Opus-Audiopakete
- Tor-Onion-v3-Unterstützung mit eigenem Tor-Prozess
- plattformabhängige Audio-Unterstützung für Linux, macOS und Termux
- sichere Dateirechte, Onion-Validierung und Terminal-Escaping
- automatisierte Protokoll- und Sicherheitstests
