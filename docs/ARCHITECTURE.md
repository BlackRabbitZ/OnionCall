# Architektur

OnionCall besteht aus klar getrennten Bereichen:

| Modul | Aufgabe |
|---|---|
| `config.py` | private Konfiguration und 256-Bit-Verbindungsschlüssel |
| `tor.py` | lokale Tor-Instanz, Onion-v3-Service und SOCKS5-Verbindung |
| `crypto.py` | X25519-Handschlag, Transkriptbeweise und HKDF-Schlüsselableitung |
| `protocol.py` | begrenzte binäre Frames, ChaCha20-Poly1305 und Sequenzprüfung |
| `audio.py` | plattformspezifische Aufnahme, Opus-Kodierung und Wiedergabe |
| `session.py` | interaktive Befehle und sichere Terminalausgabe |
| `terminal_style.py` | TTY-sichere Farben, `NO_COLOR` und Darstellung der Marke BRZ – OnionCall |
| `gui_session.py` | threadsichere Brücke zwischen verschlüsseltem Kanal und GUI |
| `webgui.py` | ausschließlich lokale Browser-GUI, Status und Aktionen |
| `OnionCall-Setup.py` | eigenständige grafische Installation und Plattform-Starter |
| `OnionCall-Terminal-Setup.py` | eigenständige Installation ohne Browser oder lokalen HTTP-Server |

## Lokale grafische Oberfläche

Die GUI enthält keinen externen Webserver und lädt keine entfernten Skripte, Schriftarten oder Stylesheets. `webgui.py` bindet einen zufälligen freien Port ausschließlich an `127.0.0.1` und öffnet diese Adresse im Standardbrowser. Schreibende Aktionen benötigen ein zufälliges Sitzungstoken. Zusätzlich werden Host und Origin geprüft, Anfragen begrenzt und eine restriktive Content Security Policy gesetzt.

Browser und OnionCall-Prozess laufen auf demselben Gerät. Der lokale HTTP-Teil ersetzt nur die Darstellung; Text und Audio durchlaufen danach unverändert den authentifizierten OnionCall-Kanal und Tor. Beim Schließen des Prozesses verschwindet auch die Oberfläche.

Das Setup verwendet denselben lokalen Ansatz. Systempakete werden ausschließlich über den erkannten Paketmanager installiert. Ein Administratorpasswort wird nicht von OnionCall gelesen oder gespeichert; eine Freigabe erfolgt über `pkexec`, `sudo` oder den Mechanismus des Betriebssystems.

Die Terminal-Oberfläche ruft dieselben Konfigurations-, Tor-, Protokoll- und Audiofunktionen direkt auf. Sie benötigt weder den Browser noch `webgui.py`. Das Terminal-Setup führt alle Installationsschritte synchron aus und zeigt jeden ausgeführten Systembefehl sichtbar an.

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
