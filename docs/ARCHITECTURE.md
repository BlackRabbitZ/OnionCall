# Architektur

OnionCall besteht aus fünf klar getrennten Bereichen:

| Modul | Aufgabe |
|---|---|
| `config.py` | private Konfiguration und 256-Bit-Verbindungsschlüssel |
| `tor.py` | lokale Tor-Instanz, Onion-v3-Service und SOCKS5-Verbindung |
| `crypto.py` | X25519-Handschlag, Transkriptbeweise und HKDF-Schlüsselableitung |
| `protocol.py` | begrenzte binäre Frames, ChaCha20-Poly1305 und Sequenzprüfung |
| `audio.py` | plattformspezifische Aufnahme, Opus-Kodierung und Wiedergabe |
| `session.py` | interaktive Befehle und sichere Terminalausgabe |

## Verbindungsaufbau

1. Beide Seiten besitzen denselben zufälligen 256-Bit-Verbindungsschlüssel.
2. Der Client erzeugt ein kurzlebiges X25519-Schlüsselpaar und sendet sein Hello.
3. Der Server antwortet mit eigenem Hello und einem HMAC über das vollständige Transkript.
4. Der Client prüft den Server und sendet seinen eigenen Transkriptbeweis.
5. Beide Seiten leiten aus X25519-Ergebnis, Verbindungsschlüssel und Transkript zwei unabhängige Sitzungsschlüssel ab.
6. Anschließend akzeptiert der Kanal ausschließlich authentifizierte Binärframes.

Die Architektur verwendet keine kryptografische Aushandlung. Algorithmus und Limits gehören zur Protokollversion; dadurch gibt es keinen Downgrade auf schwächere Verfahren.

## Datenfluss einer Sprachnachricht

```text
Mikrofon → PCM 16 kHz Mono → Opus → AEAD-Frame → Tor Onion Service
Tor Onion Service → AEAD-Prüfung → Opus → PCM → Lautsprecher
```

Temporäre Audioinhalte liegen nur in einem privaten Laufzeitverzeichnis. Die Dateien werden nach Kodierung beziehungsweise Wiedergabe entfernt. Auf Flash-Speichern garantiert einfaches Löschen keine physische Vernichtung; Geräteverschlüsselung bleibt notwendig.

## Grenzen der Parallelität

Eine OnionCall-Instanz akzeptiert aktuell genau eine Gegenstelle. Empfang und interaktive Eingabe laufen in getrennten Threads. Sendevorgänge sind durch ein Lock serialisiert, damit Sequenznummern und Nonces nicht doppelt verwendet werden.
