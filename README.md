# BRZ – OnionCall 2.7.6

<p align="center">
  <img src="onioncall/assets/onioncall-icon.png" alt="BRZ – OnionCall" width="180">
</p>

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Plattformen](https://img.shields.io/badge/Plattformen-Windows%20%7C%20Linux%20%7C%20macOS%20%7C%20Termux-2ea44f)
![Lizenz](https://img.shields.io/badge/Lizenz-Apache--2.0-blue)
![Status](https://img.shields.io/badge/Status-Alpha-orange)
![Version](https://img.shields.io/badge/Version-2.7.6-8A2BE2)

BRZ – OnionCall ist eine eigenständige Push-to-talk- und Textanwendung für Tor-Onion-Services mit einem sicherheitsorientierten Protokoll.

Die 2.7.x-Reihe ergänzt den bisherigen OnionCall-Aufbau um zusätzliche Schutzschichten gegen direkte IP-Leaks, einen gehärteten Installer, optionale Tor-v3-Client-Autorisierung und Betriebssystem-Killswitches. Die bestehende OnionCall-Haupt-GUI bleibt dabei in ihrem bisherigen Layout erhalten.

> [!CAUTION]
> OnionCall wurde noch nicht unabhängig auditiert. Verwende diese Alpha-Version nicht als alleinige Schutzmaßnahme in einer Hochrisikosituation.

## Neu in 2.7.6

Version 2.7.6 erweitert den vorhandenen 2.7.x-Stand, ohne die bestehende Projektstruktur oder die Haupt-GUI neu aufzubauen:

- Web-GUI-JavaScript-Regression behoben und zugehörige Tests aktualisiert.
- Pre-Auth-Handshakes werden begrenzt parallel verarbeitet; ein hängender Client blockiert den Listener nicht mehr allein.
- Ogg/Opus-Audio wird vor dem nativen Decoder zusätzlich auf Containerstruktur und CRC geprüft.
- Windows verwendet für Audio FFmpeg/DirectShow und `ffplay` statt Linux-ALSA-Kommandos.
- Der Browser-Installer bleibt die Standardoberfläche und lauscht ausschließlich lokal auf `127.0.0.1`.
- Der Installer prüft installierte Python-Abhängigkeiten gegen die vorgesehenen Versionen; Runtime- und Dev-Abhängigkeiten sind gepinnt.
- Private Updates werden vor dem Merge zusätzlich authentifiziert.
- Onion-v3-Adressen werden inklusive Version und SHA3-Prüfsumme validiert.
- `direct-call` und `direct-listen` akzeptieren ausschließlich `127.0.0.1` beziehungsweise `::1`.
- OnionCall-App-Schlüssel werden unter Windows benutzergebunden mit DPAPI geschützt; auf POSIX-Systemen werden Dateirechte und Dateitypen strenger geprüft.
- Importierte PSKs müssen vollständige `onioncall:v2:`-Tokens sein; offensichtlich schwache Muster werden abgelehnt.
- Der Windows-Installer kann FFmpeg 9.0.2 Essentials projektlokal unter `tools/ffmpeg/` einrichten und die Download-Datei vor dem Entpacken per SHA-256 prüfen.
- Das neue OnionCall-Logo wird in der Haupt-GUI als Logo/Favicon verwendet; das bestätigte Browser-Installer-Layout bleibt unverändert.

Weitere technische Details stehen in [SECURITY-CHANGES-2.7.6.md](SECURITY-CHANGES-2.7.6.md) und [CHANGELOG.md](CHANGELOG.md).

## Inhaltsverzeichnis

- [Neu in 2.7.6](#neu-in-276)
- [Überblick](#überblick)
- [Sicherheitsmerkmale](#sicherheitsmerkmale)
- [Zusätzliche Sicherheits-Härtung ab 2.7](#zusätzliche-sicherheits-härtung-ab-27)
- [Installation](#installation)
  - [Welche Setup-Datei soll ich nehmen?](#welche-setup-datei-soll-ich-nehmen)
  - [Grafische Setup-Datei](#setup-datei-1-grafische-installation-empfohlen)
  - [Terminal-Setup-Datei](#setup-datei-2-installation-vollständig-im-terminal)
  - [Windows-Erstinstallation und Tor-Bootstrap](#windows-erstinstallation-und-tor-bootstrap)
  - [Was vorher installiert sein muss](#was-vorher-installiert-sein-muss)
  - [Was das Setup automatisch erledigt](#was-das-setup-automatisch-erledigt)
  - [Voraussetzungen](#voraussetzungen)
  - [Systemprogramme nach Plattform](#systemprogramme-nach-plattform)
    - [Windows](#windows)
    - [Fedora](#fedora)
    - [Debian und Ubuntu](#debian-und-ubuntu)
    - [Raspberry Pi OS](#raspberry-pi-os)
    - [Arch Linux](#arch-linux-und-darauf-basierende-distributionen)
    - [macOS](#macos)
    - [Android mit Termux](#android-mit-termux)
  - [Linux und macOS installieren](#onioncall-unter-linux-und-macos-installieren)
  - [Android und Termux installieren](#onioncall-unter-android-und-termux-installieren)
  - [Nach einem Terminalneustart](#nach-dem-nächsten-terminalstart)
  - [Hilfe bei fehlendem Tor](#wenn-tor-fehlt)
- [OnionCall mit der GUI benutzen](#onioncall-mit-der-gui-benutzen)
  - [Erster Start](#erster-start)
  - [Zwei Geräte ohne Terminalbefehle verbinden](#zwei-geräte-ohne-terminalbefehle-verbinden)
  - [Terminal-Oberfläche als Alternative](#terminal-oberfläche-als-alternative)
- [OnionCall vollständig im Terminal benutzen](#onioncall-vollständig-im-terminal-benutzen)
- [Zwei Geräte Schritt für Schritt einrichten](#zwei-geräte-schritt-für-schritt-einrichten)
  - [Rollen und Adressen verstehen](#rollen-und-adressen-verstehen)
  - [Installation auf beiden Geräten prüfen](#schritt-1-installation-auf-beiden-geräten-prüfen)
  - [Gemeinsamen Schlüssel einrichten](#schritt-2-gemeinsamen-verbindungsschlüssel-einrichten)
  - [Empfänger starten](#schritt-3-empfänger-starten)
  - [Empfängeradresse übertragen](#schritt-4-empfängeradresse-übertragen)
  - [Verbindung aufbauen](#schritt-5-vom-anrufer-verbindung-aufbauen)
  - [Nachrichten und Sprache verwenden](#schritt-6-nachrichten-und-sprache-verwenden)
  - [Nächster Anruf und Rollenwechsel](#nächster-anruf-und-rollenwechsel)
- [Kontaktprofile und getrennte Schlüssel](#kontaktprofile-und-getrennte-schlüssel)
- [Tor v3 Client Authorization](#tor-v3-client-authorization)
- [Temporäre Onion-Adresse](#temporäre-onion-adresse)
- [OS-Killswitch](#os-killswitch)
  - [Linux-Killswitch](#linux-killswitch)
  - [Windows-Killswitch](#windows-killswitch)
- [Private Installation und Updates über Tor](#private-installation-und-updates-über-tor)
- [Konfiguration und Dateien](#konfiguration-und-dateien)
- [Tests und Entwicklung](#tests-und-entwicklung)
- [Bekannte Grenzen](#bekannte-grenzen)
- [Projektstatus](#projektstatus)
- [Urheber und Lizenz](#urheber-und-lizenz)

## Überblick

### Unterstützte Systeme

- Windows 10/11
- Linux, einschließlich Raspberry Pi
- macOS auf Intel und Apple Silicon
- Android innerhalb von Termux

### Funktionsweise

OnionCall überträgt Text und aufgezeichnete Opus-Sprachnachrichten, keine kontinuierlichen Telefonanrufe. Beide Seiten benötigen einen passenden zufälligen Verbindungsschlüssel. Die grafische Oberfläche wird ausschließlich auf `127.0.0.1` bereitgestellt und im lokalen Browser geöffnet; sie ist kein öffentlicher Webdienst und überträgt keine Inhalte an einen zentralen Server.

Die Verbindung zur Gegenstelle läuft über einen Tor Onion Service. Für direkte Gespräche wird ein authentifizierter, verschlüsselter Anwendungskanal innerhalb der Tor-Verbindung aufgebaut.

## Sicherheitsmerkmale

Die bisherige Sicherheitsarchitektur bleibt erhalten:

- ChaCha20-Poly1305 statt ungeschützter CBC-/CTR-Verschlüsselung
- kurzlebiger X25519-Schlüsselaustausch pro Verbindung
- gegenseitige Authentifizierung des vollständigen Handshakes mit einem zufälligen 256-Bit-Schlüssel
- Ed25519-Identitäten und Fingerprint-Pinning
- neue unabhängige Schlüssel für jede Verbindung und Richtung
- HKDF-SHA256 für die Ableitung der Sitzungsschlüssel
- strikte Sequenznummern gegen Replay und Umordnung
- feste Limits für Text und Audio
- sichere Rechte für Schlüssel, Tor-Daten und temporäre Klartextdateien
- keine Geheimnisse in Kommandozeilenargumenten von OpenSSL
- vollständig validierte Onion-v3-Adressen und bereinigte Terminalausgabe
- keine Shell-Auswertung empfangener oder gespeicherter Werte
- schlanke Python-Abhängigkeiten: `cryptography` für das Protokoll und `prompt-toolkit` für die Terminaleingabe

Die genaue Konstruktion und ihre Grenzen beschreibt [SECURITY.md](SECURITY.md).

## Zusätzliche Sicherheits-Härtung ab 2.7

Version 2.7 ergänzt die vorhandenen Schutzmechanismen um zusätzliche Defense-in-Depth-Maßnahmen:

- `direct-call` und `direct-listen` sind auf `127.0.0.1` beziehungsweise `::1` beschränkt; externe Direktverbindungen werden abgelehnt.
- Ein fremder oder hängenbleibender erster Client beendet den Listener nicht mehr vor einer erfolgreichen Authentifizierung.
- Kontaktprofile können eigene PSKs verwenden, sodass nicht mehr zwingend ein einziger gemeinsamer Schlüssel für alle Kontakte verwendet werden muss.
- Ed25519-Identitäten und Fingerprint-Pinning erschweren unbemerkte Identitätswechsel.
- Der Anrufer verwendet einen Tor-Client-Modus und veröffentlicht nicht unnötig selbst einen Onion Service.
- Tor-v3-Client-Authorization kann zusätzlich zum OnionCall-Handshake aktiviert werden.
- Audioeingaben und Decoderaufrufe besitzen zusätzliche Größen-, Format-, Zeit- und Ressourcenlimits.
- Die lokale Web-GUI verwendet Host-/Origin-Prüfung, Sitzungstoken und zusätzliche Security Header.
- Linux und Windows besitzen optionale Betriebssystem-Killswitches gegen direkte Clearnet-Verbindungen des OnionCall-Prozesses.
- Private Update- und Installationspfade verwenden Tor ohne stillen Clearnet-Fallback, sobald Tor verfügbar ist.
- Seit 2.7.6 werden Pre-Auth-Handshakes begrenzt parallelisiert und Audio-Container vor dem Decoder strenger validiert.
- Seit 2.7.6 wird unter Windows der OnionCall-App-Schlüsselbestand benutzergebunden mit DPAPI geschützt, soweit er von OnionCall selbst gelesen wird.

Weitere technische Details stehen unter anderem in [SECURITY-CHANGES-2.7.6.md](SECURITY-CHANGES-2.7.6.md), [SECURITY.md](SECURITY.md) und [CHANGELOG.md](CHANGELOG.md).

## Installation

### Welche Setup-Datei soll ich nehmen?

Du brauchst für die automatische Installation nur **eine** der beiden Setup-Dateien. Beide richten dieselbe Anwendung ein. Der Unterschied ist ausschließlich die Bedienoberfläche:

| Datei | Installation | Anwendung danach | Geeignet für |
| --- | --- | --- | --- |
| [`OnionCall-Setup.py`](OnionCall-Setup.py) / `OnionCall-Setup.cmd` | lokale grafische Oberfläche im Browser | grafische OnionCall-Oberfläche | Windows, Desktop, Smartphone und möglichst wenig Terminaleingaben |
| [`OnionCall-Terminal-Setup.py`](OnionCall-Terminal-Setup.py) | farbiges Terminal-Setup | Terminal-Oberfläche | Systeme ohne geeigneten Browser, SSH und reine Terminal-Nutzung |

> [!IMPORTANT]
> Die beiden Setup-Varianten sind **Alternativen**. Du musst nicht beide ausführen. Python 3.10 oder neuer muss vorher vorhanden sein, weil Python die gewählte Setup-Datei startet.

### Setup-Datei 1: Grafische Installation (empfohlen)

Die Datei [`OnionCall-Setup.py`](OnionCall-Setup.py) startet einen ausschließlich lokal erreichbaren Installationsbildschirm im Browser. Die OnionCall-Haupt-GUI selbst wird dadurch nicht neu gestaltet.

#### Windows

Entpacke das vollständige Repository und starte am einfachsten per Doppelklick:

```text
OnionCall-Setup.cmd
```

Alternativ öffnest du PowerShell im Projektordner und startest:

```powershell
py OnionCall-Setup.py
```

Danach:

1. Im Browser erscheint **BRZ – OnionCall Setup**.
2. Klicke auf **Installation starten**.
3. Das Setup erstellt beziehungsweise prüft die lokale `.venv`.
4. Fehlt Tor unter Windows, wird das vorgesehene Tor Expert Bundle heruntergeladen und vor der Verwendung per SHA-256 geprüft.
5. Sobald Tor vollständig gebootstrapped ist, werden fehlende Python-Pakete standardmäßig über Tors lokalen HTTP-CONNECT-Tunnel geladen.
6. Fehlt FFmpeg, richtet der Installer unter Windows **FFmpeg 9.0.2 Essentials** projektlokal unter `tools/ffmpeg/` ein und prüft das Archiv vor dem Entpacken per SHA-256.
7. Das Setup initialisiert OnionCall und richtet – sofern möglich – den Windows-Killswitch ein.
8. Warte auf **100 % / DONE**.
9. Klicke auf **OnionCall starten** oder starte später manuell:

```powershell
.\.venv\Scripts\python.exe Start-OnionCall.py
```

Für die Terminal-Oberfläche:

```powershell
.\.venv\Scripts\python.exe Start-OnionCall-Terminal.py
```

Der Browser-Installer bindet ausschließlich an `127.0.0.1`. Seine lokalen API-Aufrufe benötigen zusätzlich einen zufälligen Setup-Token; schreibende Aufrufe werden außerdem per Origin-Prüfung geschützt.

Die Option **Direkten Paketdownload erlauben** ist bewusst optional. Standardmäßig lädt OnionCall fehlende Python-Pakete und FFmpeg über Tor. Wird die Option aktiviert, dürfen diese Downloads direkt per HTTPS erfolgen.

#### Linux, macOS und Android/Termux

```bash
python3 OnionCall-Setup.py
```

Unter Android/Termux kann der Pfad zum Beispiel so aussehen:

```bash
pkg install python
termux-setup-storage
python ~/storage/downloads/OnionCall-Setup.py
```

Der genaue Downloadpfad kann abweichen. Der Dateiname muss auf `.py` und nicht auf `.py.txt` enden.

### Setup-Datei 2: Installation vollständig im Terminal

Wenn du keine Browser-Oberfläche möchtest, starte [`OnionCall-Terminal-Setup.py`](OnionCall-Terminal-Setup.py):

```bash
python3 OnionCall-Terminal-Setup.py
```

Unter Windows:

```powershell
py OnionCall-Terminal-Setup.py
```

Die Terminal-Variante zeigt Installationsschritte, Diagnose und Fehler direkt im Terminal an. Die eigentliche OnionCall-Oberfläche kann danach weiterhin über die Python-Starter geöffnet werden.

### Windows-Erstinstallation und Tor-Bootstrap

Unter Windows kann eine Erstinstallation ein Bootstrap-Problem haben: Für private Downloads soll Tor benutzt werden, Tor ist auf einem frischen Rechner möglicherweise aber noch nicht vorhanden.

In diesem Fall lädt der Installer das vorgesehene Tor Expert Bundle zunächst direkt vom Tor Project. Dieser eine Bootstrap-Schritt kann nicht bereits durch Tor laufen. Das Archiv wird gegen die fest hinterlegte SHA-256-Prüfsumme geprüft. Danach startet OnionCall eine lokale Tor-Instanz.

Seit 2.7.6 wartet der Installer auf einen vollständigen **Bootstrapped 100%**-Status und prüft anschließend die lokalen Proxy-Ports. Für private Python-Paketdownloads verwendet er Tors nativen `HTTPTunnelPort`. Dadurch bleibt die TLS-Verbindung zwischen `pip` und dem Zielserver erhalten; OnionCall transportiert lediglich die verschlüsselten Bytes durch Tor.

Prinzip:

```text
pip / HTTPS-Download
        ↓
HTTP CONNECT auf 127.0.0.1
        ↓
Tor HTTPTunnelPort
        ↓
Tor-Netzwerk
        ↓
PyPI / Zielserver
```

Domainnamen werden über den Tor-Pfad weitergegeben und nicht absichtlich lokal für die Zielverbindung aufgelöst.

### Was vorher installiert sein muss

| Plattform | Vor dem Start der Setup-Datei |
| --- | --- |
| Windows | Python 3.10 oder neuer |
| Fedora, Debian, Ubuntu, Raspberry Pi OS, Arch | Python 3.10 oder neuer |
| macOS | Python 3.10 oder neuer; Homebrew wird für Tor und Audio empfohlen |
| Android/Termux | Termux, Termux:API und `pkg install python`; beide Apps aus derselben vertrauenswürdigen Quelle |

### Was das Setup automatisch erledigt

Das Setup:

- erkennt Windows, Linux, macOS oder Android/Termux,
- erstellt eine getrennte virtuelle Python-Umgebung `.venv`,
- sucht nach einer geeigneten Tor-Installation,
- kann unter Windows bei fehlendem Tor das verifizierte Tor Expert Bundle bootstrapen,
- wartet vor privaten Downloads auf einen wirklich betriebsbereiten Tor-Tunnel,
- lädt fehlende Python-Abhängigkeiten standardmäßig über Tor,
- prüft installierte Python-Paketversionen,
- richtet unter Windows bei Bedarf FFmpeg/ffplay projektlokal ein,
- initialisiert OnionCall und führt die Diagnose aus,
- bereitet Startskripte vor,
- richtet auf unterstützten Systemen zusätzliche Killswitch-Härtung ein,
- zeigt erst dann **DONE** an.

Passwörter werden nicht durch OnionCall abgefragt oder gespeichert. Notwendige Administratorfreigaben erfolgen über den Mechanismus des Betriebssystems.

### Voraussetzungen

Für die manuelle Installation brauchst du:

1. Python 3.10 oder neuer.
2. Tor sowie die Audio-Werkzeuge für dein Betriebssystem – oder unter Windows das geführte Setup, das Tor und FFmpeg projektlokal einrichten kann.
3. Dieses OnionCall-Repository als Git-Checkout oder ZIP-Datei.

> [!IMPORTANT]
> `python -m pip install .` installiert das Projekt aus dem **aktuellen Ordner**. Der Punkt `.` bedeutet „dieser Ordner“. Wechsle deshalb zuerst mit `cd OnionCall` in das heruntergeladene Repository. Dort muss die Datei `pyproject.toml` liegen.

### Systemprogramme nach Plattform

#### Windows

Für die normale 2.7.6-Erstinstallation reicht Python 3.10+ als externe Voraussetzung. Das grafische Setup kann Tor bei Bedarf bootstrapen und FFmpeg/ffplay projektlokal einrichten.

Start:

```powershell
py OnionCall-Setup.py
```

Optional kann ein bestimmtes DirectShow-Mikrofon vorgegeben werden:

```powershell
$env:ONIONCALL_AUDIO_DEVICE="Mikrofonname aus FFmpeg/DirectShow"
```

#### Fedora

```bash
sudo dnf install git python3 python3-pip tor opus-tools alsa-utils unzip
```

#### Debian und Ubuntu

```bash
sudo apt update
sudo apt install git python3 python3-venv python3-pip tor opus-tools alsa-utils unzip
```

#### Raspberry Pi OS

```bash
sudo apt update
sudo apt install git python3 python3-venv python3-pip tor opus-tools alsa-utils unzip
```

#### Arch Linux und darauf basierende Distributionen

```bash
sudo pacman -Syu
sudo pacman -S --needed git python tor opus-tools alsa-utils unzip
```

#### macOS

Installiere zuerst [Homebrew](https://brew.sh/), falls `brew` noch nicht vorhanden ist. Danach:

```bash
brew install git python tor opus-tools sox
```

#### Android mit Termux

Installiere **Termux und Termux:API aus derselben Quelle**, vorzugsweise über F-Droid. Die veraltete Play-Store-Ausgabe von Termux wird nicht unterstützt.

```bash
pkg update
pkg install git python python-cryptography tor opus-tools sox ffmpeg termux-api
```

### OnionCall unter Linux und macOS installieren

Manuell:

```bash
cd ~
git clone https://github.com/BlackRabbitZ/OnionCall.git
cd OnionCall
ls pyproject.toml
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
python -m onioncall.cli init
python -m onioncall.cli doctor
```

Alternativ verwendest du direkt das geführte Setup:

```bash
python3 OnionCall-Setup.py
```

### OnionCall unter Android und Termux installieren

```bash
cd ~
git clone https://github.com/BlackRabbitZ/OnionCall.git
cd ~/OnionCall
ls pyproject.toml
python -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install .
python -m onioncall.cli init
python -m onioncall.cli doctor
```

### Nach dem nächsten Terminalstart

OnionCall muss nicht erneut installiert werden.

Linux/macOS/Termux:

```bash
cd ~/OnionCall
source .venv/bin/activate
python -m onioncall.cli doctor
```

Windows:

```powershell
py Start-OnionCall.py
```

### Wenn Tor fehlt

Wenn `doctor` bei Tor `[FEHLT]` anzeigt:

- unter Windows zuerst `py OnionCall-Setup.py` ausführen; das Setup kann Tor automatisch bootstrapen,
- unter Linux/macOS/Termux Tor mit dem Paketmanager installieren,
- alternativ `ONIONCALL_TOR_BINARY` auf den vollständigen Pfad zur Tor-Binärdatei setzen.

## OnionCall mit der GUI benutzen

### Erster Start

Nach der automatischen Installation öffnest du OnionCall über **OnionCall starten** oder später direkt mit Python.

Windows:

```powershell
py Start-OnionCall.py
```

Linux/macOS/Termux:

```bash
python3 Start-OnionCall.py
```

Alternativ innerhalb der eingerichteten virtuellen Umgebung:

```bash
python -m onioncall.cli gui
```

Die Oberfläche zeigt den Status von Tor, Verbindungsschlüssel, Audio und Verbindung an. Tor wird beim Empfangen oder Anrufen automatisch als eigener Prozess gestartet und beim Beenden wieder gestoppt.

Die Statuspunkte verwenden die eindeutige Ampellogik: **Rot = nicht gestartet, fehlt oder Fehler; Gelb = wartet, verbindet oder ist vorübergehend beschäftigt; Grün = aktiv, bereit oder verbunden.** Ein aktiver Tor-Prozess wird deshalb grün angezeigt.

Das Haupt-GUI behält in 2.7.6 das bisherige 2.7.5-Layout. Das neue OnionCall-Logo ersetzt lediglich das alte Symbol oben links und wird zusätzlich als Favicon verwendet.

### Zwei Geräte ohne Terminalbefehle verbinden

1. Öffne OnionCall auf beiden Geräten.
2. Klicke auf **Gerät A** auf **Schlüssel anzeigen** und kopiere die vollständige Zeile `onioncall:v2:…` beziehungsweise den Schlüssel des ausgewählten Kontaktprofils.
3. Übertrage diesen geheimen Schlüssel über einen bereits sicheren Kanal an Gerät B. Klicke dort auf **Schlüssel importieren** und speichere ihn sicher.
4. Klicke auf Gerät A auf **Empfangen**. Warte, bis Tor aktiv ist und unter **Meine Onion-Adresse** eine Adresse erscheint.
5. Kopiere genau diese Empfängeradresse und sende sie an Gerät B. Unterschiedliche eigene Onion-Adressen auf beiden Geräten sind normal.
6. Klicke auf Gerät B auf **Onion-Adresse anrufen**, füge ausschließlich die von Gerät A angezeigte Adresse ein und wähle **Verbinden**.
7. Nach **Sichere Sitzung hergestellt** kannst du Text senden oder eine Sprachnachricht aufnehmen.
8. Mit **Verbindung beenden** werden Sitzung und die zugehörige Tor-Instanz beendet.

> [!CAUTION]
> Der Verbindungsschlüssel ist geheim; die Onion-Adresse ist die erreichbare Adresse des aktuellen Empfängers. Füge niemals eine `.onion`-Adresse in den Schlüsseldialog und niemals einen geheimen Verbindungsschlüssel in den Anrufdialog ein.

### Terminal-Oberfläche als Alternative

Windows:

```powershell
py Start-OnionCall-Terminal.py
```

Linux/macOS/Termux:

```bash
python3 Start-OnionCall-Terminal.py
```

Die direkten CLI-Befehle bleiben für erfahrene Benutzer und Skripte verfügbar:

```bash
python -m onioncall.cli --help
```

## OnionCall vollständig im Terminal benutzen

Die Terminal-Oberfläche bietet Empfangen, Anrufen, Onion-Adresse, Schlüsselverwaltung, Audiotest, Diagnose und Einstellungen als nummerierte Auswahl.

Innerhalb einer Sitzung:

```text
Hallo                         Text senden
a                             fünf Sekunden Audio aufnehmen und senden
q                             Sitzung beenden
/help                         alle Chatbefehle anzeigen
```

Die Terminal-Ausgabe verwendet automatisch Farben. Bei Umleitung in Dateien oder CI-Ausgaben werden keine Farbcodes benötigt. Farben lassen sich mit `NO_COLOR=1` deaktivieren.

## Zwei Geräte Schritt für Schritt einrichten

Für ein Gespräch brauchst du zwei Geräte mit installiertem OnionCall. Im folgenden Beispiel ist **Gerät A der Empfänger** und **Gerät B der Anrufer**.

### Rollen und Adressen verstehen

| Gerät | Rolle in diesem Beispiel | Aktion | Verwendete Onion-Adresse |
| --- | --- | --- | --- |
| Gerät A | Empfänger | `listen` | zeigt seine eigene Empfängeradresse an |
| Gerät B | Anrufer | `call ADRESSE.onion` | verwendet exakt die von Gerät A angezeigte Adresse |

> [!IMPORTANT]
> **Jedes Gerät besitzt eine eigene Onion-Adresse. Unterschiedliche Adressen sind normal und richtig.** Angerufen wird ausschließlich die Adresse, die aktuell beim Empfänger angezeigt wird.

Der Verbindungsschlüssel und die Onion-Adresse haben verschiedene Aufgaben:

- Der **Verbindungsschlüssel** authentifiziert das Gespräch und ist geheim.
- Die **Onion-Adresse** bezeichnet das Gerät, das gerade empfängt.

### Schritt 1: Installation auf beiden Geräten prüfen

Windows:

```powershell
.venv\Scripts\python.exe -m onioncall.cli doctor
```

Linux/macOS/Termux:

```bash
.venv/bin/python -m onioncall.cli doctor
```

Fahre erst fort, wenn Tor, Datenverzeichnis und Verbindungsschlüssel korrekt erkannt werden.

### Schritt 2: Gemeinsamen Verbindungsschlüssel einrichten

#### 2.1 Schlüssel auf Gerät A anzeigen

Windows:

```powershell
.venv\Scripts\python.exe -m onioncall.cli init
.venv\Scripts\python.exe -m onioncall.cli show-secret --confirm
```

Linux/macOS/Termux:

```bash
.venv/bin/python -m onioncall.cli init
.venv/bin/python -m onioncall.cli show-secret --confirm
```

Die Ausgabe enthält eine einzelne lange Schlüsselzeile. Übermittle ausschließlich diese vollständige Zeichenfolge über einen bereits sicheren, vertrauenswürdigen Kanal an Gerät B.

#### 2.2 Schlüssel auf Gerät B importieren

Windows:

```powershell
.venv\Scripts\python.exe -m onioncall.cli set-secret
```

Linux/macOS/Termux:

```bash
.venv/bin/python -m onioncall.cli set-secret
```

Die Eingabe bleibt absichtlich unsichtbar. Gib den geheimen Schlüssel nicht als zusätzliches Kommandozeilenargument ein, damit er nicht in Shell-History oder Prozessinformationen landet.

#### 2.3 Import prüfen

```bash
python -m onioncall.cli doctor
```

`doctor` zeigt den geheimen Schlüssel selbst nicht an.

### Schritt 3: Empfänger starten

```bash
python -m onioncall.cli listen
```

OnionCall startet eine eigene Tor-Instanz und zeigt die Onion-Adresse des Empfängers an.

### Schritt 4: Empfängeradresse übertragen

Übermittle die vollständige, beim Empfänger angezeigte Adresse an Gerät B. Eine Onion-v3-Adresse besteht vor `.onion` aus 56 Zeichen.

### Schritt 5: Vom Anrufer Verbindung aufbauen

```bash
python -m onioncall.cli call HIER-DIE-ADRESSE-VON-GERÄT-A.onion
```

Kein `https://`, keine Leerzeichen und keine zusätzlichen Zeichen anhängen.

Ein SOCKS-Fehler bedeutet, dass Tor das Ziel nicht erreichen konnte. Prüfe dann zuerst:

1. Wurde wirklich die aktuell angezeigte Empfängeradresse verwendet?
2. Läuft der Empfänger noch?
3. Sind beide Geräte mit dem Internet verbunden und erkennt `doctor` Tor?
4. Wurde versehentlich die eigene Onion-Adresse oder eine veraltete Adresse verwendet?

Ein falscher Verbindungsschlüssel wird erst nach einer erfolgreichen Tor-Verbindung beim OnionCall-Handshake erkannt.

### Schritt 6: Nachrichten und Sprache verwenden

Nach erfolgreicher gegenseitiger Authentifizierung:

```text
Hallo                         Text direkt senden
a                             fünf Sekunden aufnehmen und senden
q                             Sitzung sicher beenden
```

Ausführliche Befehle:

```text
/text Hallo                   Text senden
/say 5                        fünf Sekunden aufnehmen und senden
/help                         Hilfe anzeigen
/quit                         Sitzung sicher beenden
```

### Nächster Anruf und Rollenwechsel

Eine Sitzung nimmt eine Verbindung an. Für ein weiteres Gespräch startet der Empfänger erneut `listen`. Die Rollen können jederzeit wechseln.

### Lokaler Funktionstest ohne Tor

Für lokale Entwicklung existieren die Diagnosebefehle:

```bash
python -m onioncall.cli direct-listen --port 17777
python -m onioncall.cli direct-call 127.0.0.1 17777
```

Ab 2.7 sind diese Befehle strikt auf Loopback beschränkt. Seit 2.7.6 werden ausschließlich `127.0.0.1` und `::1` akzeptiert. Externe IP-Adressen oder `0.0.0.0` werden abgelehnt.

## Kontaktprofile und getrennte Schlüssel

Statt eines einzigen gemeinsamen PSK können unterschiedliche Kontakte getrennte Profile erhalten.

```bash
python -m onioncall.cli peer-add alice
python -m onioncall.cli show-secret --peer alice --confirm
```

Auf der Gegenseite:

```bash
python -m onioncall.cli set-secret --peer alice
```

Verbindung:

```bash
python -m onioncall.cli listen --peer alice
python -m onioncall.cli call ADRESSE.onion --peer alice
```

Profile anzeigen:

```bash
python -m onioncall.cli peer-list
```

Das reduziert die Auswirkungen eines kompromittierten einzelnen Kontaktschlüssels.

## Tor v3 Client Authorization

Tor-v3-Client-Authorization ist eine zusätzliche optionale Schutzschicht vor dem OnionCall-Handshake. Ein Client ohne passenden Tor-Autorisierungsschlüssel erreicht den Onion Service dann gar nicht erst.

Auf dem Empfänger für einen Kontakt erzeugen:

```bash
python -m onioncall.cli tor-auth-create alice
```

Auf dem Client importieren:

```bash
python -m onioncall.cli tor-auth-import EMPFAENGERADRESSE.onion --name alice
```

Autorisierungen anzeigen:

```bash
python -m onioncall.cli tor-auth-list
```

Öffentliche Autorisierung eines Clients widerrufen:

```bash
python -m onioncall.cli tor-auth-revoke alice
```

Private Client-Autorisierung entfernen:

```bash
python -m onioncall.cli tor-auth-remove-client EMPFAENGERADRESSE.onion
```

> [!IMPORTANT]
> Tor Client Authorization ersetzt nicht den OnionCall-PSK oder die Ende-zu-Ende-Verschlüsselung. Sie ist eine zusätzliche Tor-Schicht davor.

## Temporäre Onion-Adresse

Für Sitzungen, in denen keine dauerhafte Onion-Adresse benötigt wird:

```bash
python -m onioncall.cli listen --peer alice --temporary-onion
```

Der zugehörige Onion-Service-Schlüssel wird für diese Laufzeit erzeugt und nicht als dauerhafte Identität weiterverwendet.

## OS-Killswitch

Der Killswitch ist eine zusätzliche Betriebssystem-Schutzschicht. Selbst wenn ein zukünftiger Programmierfehler versehentlich eine direkte Netzwerkverbindung erzeugt, soll der OnionCall-Prozess nicht am lokalen Tor vorbeikommunizieren können.

### Linux-Killswitch

```bash
scripts/onioncall-killswitch-linux.sh listen --peer alice
```

oder:

```bash
scripts/onioncall-killswitch-linux.sh call ADRESSE.onion --peer alice
```

Der OnionCall-Prozess darf im gehärteten Modus nur Loopback erreichen. Tor läuft separat und darf ins Internet. Kann die notwendige Isolation nicht aufgebaut werden, soll das Skript ohne unsicheren Fallback abbrechen.

### Windows-Killswitch

Windows verwendet dafür Windows Defender Firewall-Regeln für die projektspezifische virtuelle Python-Umgebung:

```text
OnionCall\.venv\Scripts\python.exe
```

Dadurch wird nicht die globale Python-Installation des Benutzers gesperrt.

Prinzip:

```text
OnionCall-Python → 127.0.0.1 / ::1     erlaubt
OnionCall-Python → lokaler Tor-Proxy    erlaubt
OnionCall-Python → direktes Internet    blockiert
Tor              → Internet             erlaubt
```

Das Setup kann dafür eine Administratorfreigabe benötigen. Seit 2.7.6 prüft der Installer zusätzlich, ob vorhandene OnionCall-Firewallregeln tatsächlich auf die Python-Executable des aktuellen Projektordners zeigen.

## Private Installation und Updates über Tor

Nach vorhandenem Tor sollen Paket- und Updatezugriffe nicht still auf Clearnet zurückfallen.

Linux/macOS:

```bash
scripts/private-update.sh
```

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\private-update-windows.ps1
```

Seit 2.7.6 wird ein Update vor dem Merge zusätzlich authentifiziert. Ohne lokal verifizierbare Commit-/Tag-Signatur oder einen vorher außerbandig geprüften `ONIONCALL_TRUSTED_COMMIT` wird abgebrochen.

## Konfiguration und Dateien

Standardpfad ist `~/.config/onioncall`. Für Tests kann `ONIONCALL_HOME` auf ein anderes Verzeichnis zeigen.

Beispiel:

```json
{
  "listen_port": 17777,
  "last_address": null,
  "max_audio_seconds": 120,
  "socks_port": 19050,
  "tor_binary": "tor"
}
```

`last_address` speichert nur die zuletzt angerufene Onion-Adresse. Verbindungsschlüssel, Identitäten, Kontaktprofile und Tor-Autorisierungen werden getrennt gespeichert. OnionCall prüft sensible Dateien auf sichere Rechte, soweit das Betriebssystem dies unterstützt. Unter Windows schützt 2.7.6 die von OnionCall verwalteten App-Schlüssel zusätzlich benutzergebunden über DPAPI.

## Tests und Entwicklung

Sicherheitstests:

```bash
python -m unittest discover -s tests -v
```

Die Tests prüfen unter anderem:

- erfolgreichen und abgewiesenen Handshake,
- falsche Schlüssel,
- AEAD-Manipulation und Replay,
- Größenlimits,
- Onion-v3-Validierung inklusive Prüfsumme,
- exakte Loopback-Beschränkung des Direktmodus,
- Listener-Verhalten bei fehlgeschlagener oder hängender Authentifizierung,
- Tor-Konfiguration,
- Tor-v3-Client-Authorization,
- lokale Web-GUI-Sicherheitsprüfungen,
- Browser-Installer-Token/Origin-Schutz,
- Ogg/Opus-Struktur- und CRC-Prüfung,
- den privaten Tor-Installationspfad.

Für die vollständigen Entwicklungsprüfungen:

```bash
python -m pip install -e '.[dev]'
ruff check .
python -m compileall -q onioncall scripts tests
python -m unittest discover -s tests -v
python -m build
```

Beiträge sind willkommen. Lies vorher [CONTRIBUTING.md](CONTRIBUTING.md) und melde Sicherheitsprobleme entsprechend [SECURITY.md](SECURITY.md), nicht als öffentliches Issue.

## Bekannte Grenzen

- Noch kein unabhängiges Sicherheitsaudit; daher keine Garantie für Hochrisikoeinsätze.
- Tor schützt nicht vor globaler zeitlicher Verkehrskorrelation.
- Ein kompromittiertes Gerät kann Inhalte und Schlüssel vor beziehungsweise nach der Verschlüsselung auslesen.
- Audio wird weiterhin über externe beziehungsweise native Audio-/Codec-Werkzeuge verarbeitet; zusätzliche Limits und Containerprüfungen reduzieren die Angriffsfläche, ersetzen aber keinen vollständigen Decoder-Sandbox-Audit.
- macOS und Termux besitzen derzeit keinen gleichwertigen OS-Netzwerk-Killswitch wie die Linux-/Windows-Härtung.
- Tor-v3-Client-Authorization erhöht die Zugangssicherheit, macht Schlüsselverteilung aber komplexer und ist deshalb optional.
- Die grafische Oberfläche läuft im lokalen Standardbrowser. Sie ist keine signierte native App und muss zusammen mit dem lokalen OnionCall-Prozess geöffnet bleiben.

## Projektstatus

Version 2.7.6 baut auf dem bestehenden OnionCall-MVP und der 2.7.5-Oberfläche auf. Sie ergänzt insbesondere die bereits vorhandene IP-Leak-Resistenz, Loopback-Diagnosepfade, Kontaktprofile, Identitäts-Pinning, Tor-v3-Client-Authorization und Killswitches um zusätzliche Listener-/Audio-Härtung, strengere Onion-v3-Prüfung, Dependency-/Update-Härtung, Windows-DPAPI, einen gehärteten Browser-Installer sowie Windows-Audio über FFmpeg/DirectShow.

Die sichtbare OnionCall-Haupt-GUI wurde für diese Sicherheitsarbeiten nicht neu gestaltet; lediglich das gewünschte OnionCall-Logo ersetzt das frühere Symbol. Der Browser-Installer behält sein bestätigtes dunkles Kartenlayout mit Rot-/Lila-Akzenten und Grün/Gelb/Rot-Statuspunkten.

Vor einer sicherheitskritischen Veröffentlichung sind weiterhin mindestens eine unabhängige Kryptografieprüfung, Fuzzing des Frame-Parsers und reale Integrationstests auf Windows, Linux, macOS und Android/Termux sinnvoll.

## Urheber und Lizenz

Copyright 2026 [BlackRabbitZ](https://github.com/BlackRabbitZ).

OnionCall steht unter der [Apache License 2.0](LICENSE). Wer das Projekt oder eine veränderte Fassung weitergibt, muss die Lizenz und die anwendbaren Urheber- und Quellenhinweise beibehalten, die Hinweise aus [NOTICE](NOTICE) mitliefern und veränderte Dateien deutlich als geändert kennzeichnen.
