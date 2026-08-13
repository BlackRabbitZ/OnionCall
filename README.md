# OnionCall v2

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Plattformen](https://img.shields.io/badge/Plattformen-Linux%20%7C%20macOS%20%7C%20Termux-2ea44f)
![Lizenz](https://img.shields.io/badge/Lizenz-Apache--2.0-blue)
![Status](https://img.shields.io/badge/Status-Alpha-orange)

OnionCall ist eine eigenständige Push-to-talk- und Textanwendung für Tor-Onion-Services mit einem sicherheitsorientierten Protokoll.

> [!CAUTION]
> OnionCall wurde noch nicht unabhängig auditiert. Verwende diese Alpha-Version nicht als alleinige Schutzmaßnahme in einer Hochrisikosituation.

## Inhaltsverzeichnis

- [Überblick](#überblick)
- [Sicherheitsmerkmale](#sicherheitsmerkmale)
- [Installation](#installation)
  - [Voraussetzungen](#voraussetzungen)
  - [Systemprogramme nach Plattform](#systemprogramme-nach-plattform)
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
- [Einfacher Start über das Menü](#einfacher-start-über-das-menü)
- [Zwei Geräte Schritt für Schritt einrichten](#zwei-geräte-schritt-für-schritt-einrichten)
  - [Rollen und Adressen verstehen](#rollen-und-adressen-verstehen)
  - [Installation auf beiden Geräten prüfen](#schritt-1-installation-auf-beiden-geräten-prüfen)
  - [Gemeinsamen Schlüssel einrichten](#schritt-2-gemeinsamen-verbindungsschlüssel-einrichten)
  - [Empfänger starten](#schritt-3-empfänger-starten)
  - [Empfängeradresse übertragen](#schritt-4-empfängeradresse-übertragen)
  - [Verbindung aufbauen](#schritt-5-vom-anrufer-verbindung-aufbauen)
  - [Nachrichten und Sprache verwenden](#schritt-6-nachrichten-und-sprache-verwenden)
  - [Nächster Anruf und Rollenwechsel](#nächster-anruf-und-rollenwechsel)
- [Konfiguration und Dateien](#konfiguration-und-dateien)
- [Tests und Entwicklung](#tests-und-entwicklung)
- [Bekannte Grenzen](#bekannte-grenzen)
- [Projektstatus](#projektstatus)
- [Urheber und Lizenz](#urheber-und-lizenz)

## Überblick

### Unterstützte Systeme

- Linux, einschließlich Raspberry Pi
- macOS auf Intel und Apple Silicon
- Android innerhalb von Termux

### Funktionsweise

OnionCall überträgt aufgezeichnete Opus-Sprachnachrichten, keine kontinuierlichen Telefonanrufe. Beide Seiten benötigen dieselbe zufällige Gesprächs-ID beziehungsweise denselben Verbindungsschlüssel.

## Sicherheitsmerkmale

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

## Installation

### Voraussetzungen

Du musst zuerst zwei Dinge herunterladen beziehungsweise installieren:

1. Systemprogramme für Python, Git, Tor und Audio.
2. Dieses OnionCall-Repository mit Git oder als ZIP-Datei.

> [!IMPORTANT]
> **Tor muss installiert sein, bevor OnionCall benutzt wird.** OnionCall liefert Tor nicht mit. Bei `onioncall listen` und `onioncall call` startet OnionCall selbst einen getrennten Tor-Prozess; ein systemweiter Tor-Dienst muss dafür nicht manuell gestartet werden. Prüfe die Installation mit `onioncall doctor`: Bei `tor` muss `[OK]` stehen.

> [!IMPORTANT]
> `python -m pip install .` installiert das Projekt aus dem **aktuellen Ordner**. Der Punkt `.` bedeutet „dieser Ordner“. Wechsle deshalb zuerst mit `cd OnionCall` in das heruntergeladene Repository. Dort muss die Datei `pyproject.toml` liegen.

Kontrolle vor der Installation:

```bash
pwd
ls pyproject.toml
```

Eine vollständige Schritt-für-Schritt-Anleitung für Fedora, Debian/Ubuntu, Raspberry Pi OS, Arch Linux, macOS und Android/Termux steht in **[docs/INSTALLATION.md](docs/INSTALLATION.md)**. Sie enthält auch Aktualisierung, Deinstallation und Fehlerbehebung.

### Systemprogramme nach Plattform

Installiere zuerst die Systemprogramme für dein Betriebssystem. **Jeder der folgenden Befehle installiert auch Tor.**

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

Installiere **Termux und Termux:API aus derselben Quelle**, vorzugsweise über [F-Droid](https://f-droid.org/packages/com.termux/). Die veraltete Play-Store-Ausgabe von Termux wird nicht unterstützt. Öffne anschließend Termux und führe aus:

```bash
pkg update
pkg install git python python-cryptography tor opus-tools sox ffmpeg termux-api
```

Für Termux gilt anschließend der [eigene Installationsablauf](#onioncall-unter-android-und-termux-installieren), weil dort `cryptography` als Systempaket verwendet wird.

### OnionCall unter Linux und macOS installieren

Nach der Installation der passenden Systemprogramme führst du diese Befehle nacheinander aus:

```bash
# Repository herunterladen
cd ~
git clone https://github.com/BlackRabbitZ/OnionCall.git

# In den heruntergeladenen Projektordner wechseln
cd OnionCall

# Prüfen, ob dies wirklich der Projektordner ist
ls pyproject.toml

# Abgeschlossene Python-Umgebung erstellen und aktivieren
python3 -m venv .venv
source .venv/bin/activate

# OnionCall aus genau diesem Ordner installieren
python -m pip install --upgrade pip
python -m pip install .

# Einrichten und alle Abhängigkeiten prüfen
onioncall init
onioncall doctor
```

Wenn `git clone` meldet, dass der Ordner `OnionCall` bereits existiert, klone nicht erneut. Verwende `cd ~/OnionCall` und folge der [Anleitung zum Aktualisieren](docs/INSTALLATION.md#aktualisieren).

### OnionCall unter Android und Termux installieren

Nach der oben beschriebenen Installation der Termux-Pakete:

```bash
cd ~
git clone https://github.com/BlackRabbitZ/OnionCall.git
cd ~/OnionCall
ls pyproject.toml
python -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install .
onioncall init
onioncall doctor
```

### Nach dem nächsten Terminalstart

OnionCall muss nicht erneut installiert werden. Aktiviere nur wieder die vorhandene Umgebung:

```bash
cd ~/OnionCall
source .venv/bin/activate
onioncall doctor
```

### Wenn Tor fehlt

Wenn `doctor` bei `tor` `[FEHLT]` anzeigt, wurde Tor nicht installiert oder ist nicht über den Suchpfad erreichbar. Installiere das Paket `tor` mit dem oben gezeigten Befehl für dein System und führe `onioncall doctor` erneut aus. Die ausführliche [Installationsanleitung](docs/INSTALLATION.md) beschreibt zusätzlich ZIP-Download, Aktualisierung, Deinstallation und weitere Fehlerfälle.

## Einfacher Start über das Menü

Nach der einmaligen Installation genügt dieser eine Befehl:

```bash
onioncall
```

Ohne weiteren Unterbefehl öffnet OnionCall einen geführten Startbildschirm:

```text
1  Gespräch empfangen
2  Person anrufen
3  Verbindungsschlüssel einrichten
4  Installation prüfen
0  Beenden
```

Du wählst nur noch eine Zahl. Der Assistent erzeugt bei Bedarf die Grundkonfiguration, erklärt den nächsten Schritt und erkennt, wenn Schlüssel und Onion-Adresse verwechselt wurden.

Für die erste Verbindung:

1. Auf Gerät A `onioncall` starten, **3** und danach **1** wählen. Die angezeigte Schlüsselzeile sicher an Gerät B übertragen.
2. Auf Gerät B `onioncall` starten, **3** und danach **2** wählen. Den Schlüssel bei der unsichtbaren Abfrage einfügen und Enter drücken.
3. Auf Gerät A im Hauptmenü **1** wählen. Das Terminal geöffnet lassen und die angezeigte Empfängeradresse an Gerät B senden.
4. Auf Gerät B im Hauptmenü **2** wählen und die Empfängeradresse einmal einfügen.
5. Bei späteren Anrufen merkt sich OnionCall auf Gerät B die zuletzt verwendete Empfängeradresse. Drücke einfach Enter, um sie erneut zu verwenden.

> [!NOTE]
> Schlüssel und Empfängeradresse müssen aus Sicherheitsgründen beim ersten Mal bewusst zwischen den Geräten übertragen werden. OnionCall sucht keine Geräte automatisch im lokalen Netzwerk und lädt keine Kontakte auf einen zentralen Server.

Die direkten Befehle wie `onioncall listen` und `onioncall call …` bleiben für erfahrene Benutzer und Skripte verfügbar. Die folgende ausführliche Anleitung erklärt weiterhin jeden Einzelschritt.

## Zwei Geräte Schritt für Schritt einrichten

Für ein Gespräch brauchst du zwei Geräte mit installiertem OnionCall. Im folgenden Beispiel ist **Gerät A der Empfänger** und **Gerät B der Anrufer**.

### Rollen und Adressen verstehen

| Gerät | Rolle in diesem Beispiel | Befehl | Verwendete Onion-Adresse |
| --- | --- | --- | --- |
| Gerät A | Empfänger | `onioncall listen` | zeigt seine eigene Empfängeradresse an |
| Gerät B | Anrufer | `onioncall call ADRESSE.onion` | verwendet exakt die von Gerät A angezeigte Adresse |

> [!IMPORTANT]
> **Jedes Gerät besitzt eine eigene Onion-Adresse. Unterschiedliche Adressen sind normal und richtig.** Angerufen wird ausschließlich die Adresse, die aktuell beim Empfänger nach `onioncall listen` steht. Verwende niemals die eigene Adresse des Anrufers, eine Adresse eines anderen Geräts oder eine Adresse aus einer gelöschten beziehungsweise neu eingerichteten Installation.

Der Verbindungsschlüssel und die Onion-Adresse haben verschiedene Aufgaben:

- Der **Verbindungsschlüssel** muss auf beiden Geräten identisch sein und authentifiziert das Gespräch. Er ist geheim.
- Die **Onion-Adresse** bezeichnet nur das Gerät, das gerade mit `onioncall listen` empfängt. Die beiden Geräte müssen nicht dieselbe Onion-Adresse haben.

### Schritt 1: Installation auf beiden Geräten prüfen

Aktiviere auf **beiden Geräten** die virtuelle Umgebung. Bei einer ZIP-Installation kann der Ordner stattdessen `~/OnionCall-main` heißen.

```bash
cd ~/OnionCall
source .venv/bin/activate
onioncall doctor
```

Fahre erst fort, wenn `doctor` Tor, Audio, Datenverzeichnis und Verbindungsschlüssel mit `[OK]` meldet. Ein systemweiter Tor-Dienst muss nicht manuell gestartet werden; OnionCall startet seinen eigenen Tor-Prozess.

### Schritt 2: Gemeinsamen Verbindungsschlüssel einrichten

Beide Geräte müssen exakt denselben Verbindungsschlüssel verwenden. Übertrage ihn so:

#### 2.1 Schlüssel auf Gerät A anzeigen

Auf **Gerät A** einen Schlüssel erzeugen und anzeigen:

```bash
onioncall init
onioncall show-secret --confirm
```

Falls `onioncall init` meldet, dass `conversation.key` bereits existiert, ist schon ein Schlüssel eingerichtet. Das ist kein Defekt. Zeige ihn einfach mit `onioncall show-secret --confirm` an. Gib jeden Befehl einzeln ein; `~` ist kein Trennzeichen zwischen Befehlen.

Die Ausgabe ist eine einzelne lange Zeile, beispielsweise:

```text
onioncall:v2:HIER-STEHT-DER-LANGE-GEHEIME-SCHLUESSEL
```

Kopiere die Zeile:

- vollständig vom Anfang `onioncall:v2:` bis zum letzten Zeichen,
- ohne den Shell-Prompt wie `(.venv) [user@computer OnionCall]$`,
- ohne Anführungszeichen, Zeilenumbruch oder zusätzliche Leerzeichen,
- ohne andere Terminalausgaben davor oder dahinter.

Übermittle ausschließlich diese vollständige Zeichenfolge **über einen bereits sicheren, vertrauenswürdigen Kanal** an Gerät B.

#### 2.2 Schlüssel auf Gerät B importieren

Auf **Gerät B** den Schlüssel über die verdeckte Eingabe importieren:

```bash
onioncall set-secret --replace
```

Gib diesen Befehl **genau einmal** ein und drücke Enter. Wenn links im Prompt bereits `(.venv)` steht, ist die virtuelle Umgebung schon aktiv; `source .venv/bin/activate` muss dann nicht erneut ausgeführt werden.

So sieht der Ablauf im Terminal aus:

```text
(.venv) [user@computer OnionCall]$ onioncall set-secret --replace
Verbindungsschlüssel (Eingabe bleibt unsichtbar):
Verbindungsschlüssel sicher gespeichert.
```

Zwischen der zweiten und dritten Zeile fügst du den Schlüssel ein und drückst Enter. Der eingefügte Schlüssel wird nicht dargestellt.

OnionCall zeigt danach:

```text
Verbindungsschlüssel (Eingabe bleibt unsichtbar):
```

Füge jetzt die vollständige Zeile `onioncall:v2:…` ein und drücke **einmal Enter**. Beim Einfügen werden absichtlich weder Buchstaben noch Punkte oder Sternchen angezeigt. Das ist normal und schützt den Schlüssel vor Blicken auf den Bildschirm.

Bei erfolgreichem Import erscheint:

```text
Verbindungsschlüssel sicher gespeichert.
```

Falls stattdessen eine Fehlermeldung erscheint, führe den Import erneut aus und achte darauf, ausschließlich die vollständige Schlüsselzeile einzufügen.

> [!WARNING]
> Kopiere nicht den gesamten Ordner `~/.config/onioncall` zwischen den Geräten. Importiere nur die Zeichenfolge `onioncall:v2:…` mit der verdeckten Abfrage von `onioncall set-secret --replace`. Veröffentliche den Schlüssel nicht in Gruppen, Screenshots oder unverschlüsselter E-Mail. Wer ihn besitzt, kann sich als Gesprächspartner ausgeben.

Gib den Schlüssel nicht direkt hinter dem Befehl ein. Die aktuelle Version weist zusätzliche Argumente ab:

```bash
# Unsicher – nicht verwenden:
onioncall set-secret onioncall:v2:GEHEIMER-SCHLUESSEL --replace
```

Diese Schreibweise könnte den Schlüssel in der Shell-History und in Prozessinformationen hinterlassen. Verwende immer nur `onioncall set-secret --replace` und füge den Schlüssel anschließend in die unsichtbare Eingabe ein.

Wiederhole auch nicht versehentlich den Befehl in derselben Zeile:

```bash
# Falsch – der Befehl steht doppelt:
onioncall set-secret --replace onioncall set-secret --replace
```

Das führt zu `onioncall: error: unrecognized arguments: set-secret`. Drücke in diesem Fall nicht weiter, sondern gib in einer neuen Zeile nur einmal `onioncall set-secret --replace` ein.

#### 2.3 Import prüfen

Prüfe auf Gerät B, ob der Schlüssel vorhanden ist und sichere Dateirechte besitzt:

```bash
onioncall doctor
```

Die Zeile zum Verbindungsschlüssel muss `[OK]` anzeigen. `doctor` zeigt den geheimen Schlüssel selbst nicht an.

Für einen neuen Gesprächskreis erzeugst du mit `onioncall init --replace` bewusst einen neuen Schlüssel und importierst ihn anschließend auf allen beteiligten Geräten.

### Schritt 3: Empfänger starten

Auf **Gerät A**:

```bash
onioncall listen
```

OnionCall startet eine eigene Tor-Instanz. Warte, bis beispielsweise Folgendes erscheint:

```text
Deine Onion-Adresse: abcdef…xyz.onion
Warte auf eine eingehende Verbindung …
```

Lass dieses Terminal geöffnet. Wird `listen` beendet, ist der Empfänger nicht mehr erreichbar.

### Schritt 4: Empfängeradresse übertragen

Übermittle die vollständige, bei **Gerät A** angezeigte Adresse an Gerät B. Vergleiche sie vor dem Anruf Zeichen für Zeichen. Eine Onion-v3-Adresse besteht vor `.onion` aus 56 Zeichen.

> [!CAUTION]
> Die Adresse auf Gerät B kann anders aussehen. Das ist kein Fehler. Gerät B darf nicht seine eigene Adresse anrufen, sondern muss die gerade von Gerät A angezeigte Empfängeradresse verwenden.

### Schritt 5: Vom Anrufer Verbindung aufbauen

Während `onioncall listen` auf Gerät A weiterläuft, auf **Gerät B** ausführen:

```bash
onioncall call HIER-DIE-ADRESSE-VON-GERÄT-A.onion
```

Ersetze den gesamten Platzhalter durch die Adresse des Empfängers. Kein `https://`, keine Leerzeichen und keine zusätzlichen Zeichen anhängen.

Der Fehler `SOCKS-Code 4` bedeutet, dass Tor das Ziel nicht erreichen konnte. Prüfe dann zuerst:

1. Wurde wirklich die aktuell auf dem Empfänger angezeigte Adresse verwendet?
2. Läuft `onioncall listen` auf dem Empfänger noch?
3. Sind beide Geräte mit dem Internet verbunden und zeigt `onioncall doctor` Tor als `[OK]`?
4. Wurde möglicherweise die eigene Adresse des Anrufers oder eine Adresse aus einer früheren Installation verwendet?

Ein falscher Verbindungsschlüssel verursacht keinen SOCKS-Code 4. Er wird erst nach einer erfolgreichen Tor-Verbindung geprüft und führt dann zu einem Authentifizierungsfehler.

### Schritt 6: Nachrichten und Sprache verwenden

Nach erfolgreicher gegenseitiger Authentifizierung ist die Bedienung vereinfacht:

```text
Hallo                         Text direkt senden
a                             fünf Sekunden aufnehmen und senden
q                             Sitzung sicher beenden
```

Die bisherigen ausführlichen Befehle bleiben ebenfalls verfügbar:

```text
/text Hallo                 Text senden
/say 5                      fünf Sekunden aufnehmen und senden
/help                       Hilfe anzeigen
/quit                       Sitzung sicher beenden
```

### Nächster Anruf und Rollenwechsel

Eine Sitzung nimmt genau eine Verbindung an. Für ein weiteres Gespräch startet der Empfänger erneut `onioncall listen`. Die Adresse bleibt normalerweise gleich, solange dessen OnionCall-Datenverzeichnis nicht gelöscht oder ersetzt wird; maßgeblich ist trotzdem immer die aktuell angezeigte Adresse.

Die Rollen können wechseln: Soll Gerät B der Empfänger sein, startet Gerät B `onioncall listen` und Gerät A ruft anschließend genau die dabei auf Gerät B angezeigte Adresse an.

### Lokaler Funktionstest ohne Tor

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
  "last_address": null,
  "max_audio_seconds": 120,
  "socks_port": 19050,
  "tor_binary": "tor"
}
```

`last_address` speichert nur die zuletzt angerufene Onion-Adresse, damit sie im Menü nicht erneut eingefügt werden muss. Der Verbindungsschlüssel wird getrennt gespeichert. OnionCall lehnt einen Schlüssel ab, wenn dessen Dateirechte anderen lokalen Benutzern Zugriff geben. `onioncall doctor` kontrolliert Installation und Berechtigungen.

## Tests und Entwicklung

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

## Urheber und Lizenz

Copyright 2026 [BlackRabbitZ](https://github.com/BlackRabbitZ).

OnionCall steht unter der [Apache License 2.0](LICENSE). Wer das Projekt oder eine veränderte Fassung weitergibt, muss die Lizenz und die anwendbaren Urheber- und Quellenhinweise beibehalten, die Hinweise aus [NOTICE](NOTICE) mitliefern und veränderte Dateien deutlich als geändert kennzeichnen.
