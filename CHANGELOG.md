# Änderungsprotokoll

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert. Das Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/), die Versionierung an [Semantic Versioning](https://semver.org/lang/de/).

## [2.3.0] – 2026-08-13

### Hinzugefügt

- vollständige nummerierte Terminal-Oberfläche mit kompaktem Status für Tor, Schlüssel, Audio und Onion-Adresse
- direkte Terminal-Auswahl für Empfangen, Anrufen, Onion-Adresse, Schlüsselverwaltung, Audiotest, Diagnose und Einstellungen
- eigenständige Datei `OnionCall-Terminal-Setup.py` für Installation und Aktualisierung vollständig ohne Web-GUI
- eigener Programmstarter `onioncall-terminal` sowie Terminal-Starter für Linux, macOS und optional Termux:Widget

### Geändert

- das bisherige einfache Terminalmenü wurde zu einer vollständigen alternativen Benutzeroberfläche erweitert
- `onioncall terminal` und `onioncall menu` öffnen dieselbe Terminal-Oberfläche

## [2.2.0] – 2026-08-13

### Hinzugefügt

- lokale grafische Oberfläche für Installation, Tor-Status, Empfangen, Anrufen, Schlüsselübertragung, Chat und Sprachnachrichten
- eigenständige Datei `OnionCall-Setup.py`, die das Repository lädt, Systempakete installiert, eine virtuelle Umgebung erstellt, OnionCall prüft und Plattform-Starter anlegt
- Desktop-Starter für Linux und macOS sowie optionaler Termux:Widget-Starter
- abgesicherter lokaler Webserver mit zufälligem Sitzungstoken, Origin-/Host-Prüfung, Größenlimits und restriktiver Content Security Policy

### Geändert

- `onioncall` ohne Unterbefehl öffnet die grafische Oberfläche; das bisherige Terminalmenü bleibt über `onioncall menu` verfügbar
- Tor-Start wartet nun zusätzlich auf 100 Prozent Bootstrap und einen erreichbaren lokalen SOCKS-Port; alte Bootstrap-Logs werden dabei nicht als aktueller Erfolg gewertet
- Chat-Sitzungen besitzen für GUI und Terminal getrennte, threadsichere Darstellungen

### Behoben

- mehrfaches Beenden einer bereits geschlossenen Terminaleingabe löst keine nachlaufende `prompt-toolkit`-Ausnahme mehr aus
- der Abbrechen-Knopf im Anrufdialog startet keinen Verbindungsversuch

## [2.1.0] – 2026-08-13

### Geändert

- plattformneutrale README und vollständige Installationsanleitung für Fedora, Debian/Ubuntu, Raspberry Pi OS, Arch, macOS und Termux; Tor wird deutlich als Voraussetzung genannt
- README mit Inhaltsverzeichnis, klarer Abschnittshierarchie und plattformbezogenen Sprungmarken übersichtlicher gestaltet
- ausführliche Zwei-Geräte-Anleitung ergänzt: Rollen, Schlüsselaustausch, richtige Empfängeradresse, Rollenwechsel und Fehlerhilfe für SOCKS-Code 4
- Schlüsselübertragung präzisiert: vollständiger Kopierbereich, unsichtbare Eingabe, Erfolgskontrolle und Warnung vor unsicheren Kommandozeilenargumenten
- doppelten `set-secret`-Befehl und den Fehler `unrecognized arguments` dokumentiert; Schlüsselwerte als Kommandozeilenargument technisch deaktiviert
- geführten Startbildschirm für Empfangen, Anrufen, Schlüsseleinrichtung und Diagnose ergänzt; letzter Gesprächspartner wird lokal gemerkt
- Sitzungsbedienung vereinfacht: normaler Text sendet direkt, `a` nimmt fünf Sekunden Audio auf und `q` beendet
- Verwechslungen zwischen einer `.onion`-Adresse und einem `onioncall:v2:`-Schlüssel werden mit einer gezielten Erklärung abgewiesen
- robuste Terminaleingabe mit `prompt-toolkit`: Eingehende Nachrichten erscheinen oberhalb des Prompts und bereits getippter Text bleibt erhalten
- Unterstützung für aktuelle `cryptography`-Pakete bis vor Version 51, insbesondere für Termux

### Sicherheit

- `onioncall set-secret` fragt den Verbindungsschlüssel ohne Argument verdeckt ab, damit er nicht in der Shell-History erscheint

### Behoben

- gleichzeitiges Empfangen und Tippen zerreißt nicht mehr die Chatzeile
- einheitliche Kennzeichnung durch `[Du]`, `[Gegenstelle]`, `[Du · Audio]` und `[Gegenstelle · Audio]`

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
