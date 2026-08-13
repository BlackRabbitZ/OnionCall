# OnionCall v2

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Plattformen](https://img.shields.io/badge/Plattformen-Linux%20%7C%20macOS%20%7C%20Termux-2ea44f)
![Lizenz](https://img.shields.io/badge/Lizenz-Apache--2.0-blue)
![Status](https://img.shields.io/badge/Status-Alpha-orange)

OnionCall ist eine neu entwickelte Push-to-talk- und Textanwendung für Tor-Onion-Services. Sie ist **nicht** protokollkompatibel mit TerminalPhone 1.x. Diese Trennung ist beabsichtigt: Unsichere Altlasten werden nicht übernommen.

> [!CAUTION]
> OnionCall wurde noch nicht unabhängig auditiert. Verwende diese Alpha-Version nicht als alleinige Schutzmaßnahme in einer Hochrisikosituation.

Unterstützte Systeme:

- Linux, einschließlich Raspberry Pi
- macOS auf Intel und Apple Silicon
- Android innerhalb von Termux

OnionCall überträgt aufgezeichnete Opus-Sprachnachrichten, keine kontinuierlichen Telefonanrufe. Beide Seiten benötigen dieselbe zufällige Gesprächs-ID beziehungsweise denselben Verbindungsschlüssel.

## Wichtige Sicherheitsverbesserungen

- ChaCha20-Poly1305 statt ungeschützter CBC-/CTR-Verschlüsselung
- kurzlebiger X25519-Schlüsselaustausch pro Verbindung
- gegenseitige Authentifizierung des vollständigen Handshakes mit einem zufälligen 256-Bit-Schlüssel
- neue unabhängige Schlüssel für jede Verbindung und Richtung
- strikte Sequenznummern gegen Replay und Umordnung
- feste Limits: 8 KiB Text und 8 MiB Audio
- sichere Rechte für Schlüssel, Tor-Daten und temporäre Klartextdateien
- keine Geheimnisse in Kommandozeilenargumenten von OpenSSL
- validierte Onion-v3-Adressen und bereinigte Terminalausgabe
- keine Shell-Auswertung empfangener oder gespeicherter Werte
- ausschließlich Python-Standardbibliothek plus das etablierte Paket `cryptography`

Die genaue Konstruktion und ihre Grenzen beschreibt [SECURITY.md](SECURITY.md).

## Vor der Installation

Du musst zuerst zwei Dinge herunterladen beziehungsweise installieren:

1. Systemprogramme für Python, Git, Tor und Audio.
2. Dieses OnionCall-Repository mit Git oder als ZIP-Datei.

> [!IMPORTANT]
> `python -m pip install .` installiert das Projekt aus dem **aktuellen Ordner**. Der Punkt `.` bedeutet „dieser Ordner“. Wechsle deshalb zuerst mit `cd OnionCall` in das heruntergeladene Repository. Dort muss die Datei `pyproject.toml` liegen.

Kontrolle vor der Installation:

```bash
pwd
ls pyproject.toml
```

Eine vollständige Schritt-für-Schritt-Anleitung für Fedora, Debian/Ubuntu, Arch Linux, macOS und Android/Termux steht in **[docs/INSTALLATION.md](docs/INSTALLATION.md)**. Sie enthält auch Aktualisierung, Deinstallation und Fehlerbehebung.

## Schnellstart unter Fedora

Die folgenden Befehle nacheinander ausführen:

```bash
# 1. Benötigte Systemprogramme installieren
sudo dnf install git python3 python3-pip tor opus-tools alsa-utils

# 2. Repository in das Home-Verzeichnis herunterladen
cd ~
git clone https://github.com/BlackRabbitZ/OnionCall.git

# 3. In den heruntergeladenen Projektordner wechseln
cd OnionCall

# 4. Prüfen, ob dies wirklich der Projektordner ist
ls pyproject.toml

# 5. Abgeschlossene Python-Umgebung erstellen und aktivieren
python3 -m venv .venv
source .venv/bin/activate

# 6. OnionCall aus genau diesem Ordner installieren
python -m pip install --upgrade pip
python -m pip install .

# 7. Einrichten und alle Abhängigkeiten prüfen
onioncall init
onioncall doctor
```

Wenn das Terminal später neu geöffnet wird, muss OnionCall nicht erneut installiert werden. Aktiviere nur wieder die Umgebung:

```bash
cd ~/OnionCall
source .venv/bin/activate
onioncall doctor
```

## Andere Plattformen – benötigte Downloads

| Plattform | Vorher installieren |
| --- | --- |
| Fedora | `git python3 python3-pip tor opus-tools alsa-utils` |
| Debian/Ubuntu/Raspberry Pi OS | `git python3 python3-venv python3-pip tor opus-tools alsa-utils` |
| Arch Linux | `git python tor opus-tools alsa-utils` |
| macOS | Homebrew, danach `git python tor opus-tools sox` |
| Android/Termux | Termux und Termux:API aus derselben Quelle; danach `git python python-cryptography tor opus-tools sox ffmpeg termux-api` |

Die passenden Paketmanager-Befehle und sämtliche folgenden Schritte stehen in der [Installationsanleitung](docs/INSTALLATION.md).

## Erster sicherer Schlüsselaustausch

Person A richtet OnionCall ein:

```bash
onioncall init
onioncall show-secret --confirm
```

Die Ausgabe beginnt mit `onioncall:v2:`. Person A übermittelt sie **über einen bereits sicheren Kanal** an Person B. Person B importiert sie über eine verdeckte Eingabe:

```bash
onioncall init
onioncall set-secret --replace
```

OnionCall fragt nach dem Schlüssel. Beim Einfügen werden absichtlich keine Zeichen angezeigt; danach Enter drücken. So erscheint der Schlüssel nicht in der Shell-History. Den Schlüssel nicht in Gruppen, Screenshots oder unverschlüsselter E-Mail weitergeben. Wer ihn besitzt, kann sich als Gesprächspartner ausgeben. Für einen neuen Gesprächskreis einen neuen Schlüssel mit `onioncall init --replace` erzeugen.

## Verwendung

Der Empfänger startet zuerst:

```bash
onioncall listen
```

OnionCall startet eine eigene Tor-Instanz und zeigt die persönliche Onion-Adresse. Der Anrufer verwendet:

```bash
onioncall call abcdef…xyz.onion
```

Nach erfolgreicher gegenseitiger Authentifizierung stehen folgende Befehle zur Verfügung:

```text
/text Hallo                 Text senden
/say 5                      fünf Sekunden aufnehmen und senden
/help                       Hilfe anzeigen
/quit                       Sitzung sicher beenden
```

Für einen lokalen Funktionstest ohne Tor gibt es die absichtlich nicht beworbenen Diagnosebefehle:

```bash
onioncall direct-listen --port 17777
onioncall direct-call 127.0.0.1 17777
```

Diese direkte Verbindung schützt den Inhalt kryptografisch, verbirgt aber **keine IP-Adresse** und ist nur zum Testen gedacht.

## Konfiguration und Dateien

Standardpfad ist `~/.config/onioncall`. Für Tests kann `ONIONCALL_HOME` auf ein anderes Verzeichnis zeigen.

```json
{
  "listen_port": 17777,
  "max_audio_seconds": 120,
  "socks_port": 19050,
  "tor_binary": "tor"
}
```

OnionCall lehnt einen Schlüssel ab, wenn dessen Dateirechte anderen lokalen Benutzern Zugriff geben. `onioncall doctor` kontrolliert Installation und Berechtigungen.

## Tests

```bash
python -m unittest discover -s tests -v
```

Die Tests prüfen unter anderem erfolgreichen und abgewiesenen Handshake, falsche Schlüssel, AEAD-Manipulation, Replay, Größenlimits, private Dateirechte, Onion-Validierung und Terminal-Steuerzeichen.

Für die vollständigen Entwicklungsprüfungen:

```bash
python -m pip install -e '.[dev]'
ruff check .
python -m compileall -q onioncall tests
python -m unittest discover -s tests -v
python -m build
```

Beiträge sind willkommen. Lies vorher [CONTRIBUTING.md](CONTRIBUTING.md) und melde Sicherheitsprobleme entsprechend [SECURITY.md](SECURITY.md), nicht als öffentliches Issue.

## Bekannte Grenzen

- Noch kein unabhängiges Sicherheitsaudit; daher keine Garantie für Hochrisikoeinsätze.
- Kein Gruppenrelay, kein Voice Changer und keine Cipher-Auswahl. Weniger Optionen reduzieren Angriffsfläche und Fehlkonfigurationen.
- Eine Sitzung nimmt genau eine eingehende Verbindung an. Danach kann `listen` erneut gestartet werden.
- Tor schützt nicht vor globaler zeitlicher Verkehrskorrelation.
- Ein kompromittiertes Gerät kann Sprache und Schlüssel vor beziehungsweise nach der Verschlüsselung auslesen.
- Die aktuelle Bedienung nutzt zeitlich begrenzte Aufnahmen (`/say 5`) statt einer globalen PTT-Taste. Das funktioniert konsistent auf allen drei Plattformen und vermeidet globale Tastatur-Hooks.

## Projektstatus

Version 2.0.0 ist ein gehärtetes, getestetes MVP. Vor einer sicherheitskritischen Veröffentlichung sind mindestens eine unabhängige Kryptografieprüfung, Fuzzing des Frame-Parsers und reale Integrationstests auf Linux, macOS und mehreren Android-Versionen notwendig.

## Danksagung

Die Grundidee wurde durch [TerminalPhone](https://gitlab.com/here_forawhile/terminalphone) angeregt. OnionCall ist eine eigenständige Neuimplementierung mit einem neuen Protokoll und ohne Kompatibilität zu TerminalPhone 1.x.

## Urheber und Lizenz

Copyright 2026 [BlackRabbitZ](https://github.com/BlackRabbitZ).

OnionCall steht unter der [Apache License 2.0](LICENSE). Wer das Projekt oder eine veränderte Fassung weitergibt, muss die Lizenz und die anwendbaren Urheber- und Quellenhinweise beibehalten, die Hinweise aus [NOTICE](NOTICE) mitliefern und veränderte Dateien deutlich als geändert kennzeichnen.
