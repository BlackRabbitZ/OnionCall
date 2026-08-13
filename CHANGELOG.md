# Änderungsprotokoll

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert. Das Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/), die Versionierung an [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

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
