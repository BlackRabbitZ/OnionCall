# OnionCall installieren und starten

Diese Anleitung führt vollständig durch automatische oder manuelle Installation, Einrichtung, Start, Aktualisierung und Fehlerbehebung.

## Empfohlen: eine Datei und eine grafische Installation

### Vollständig im Terminal installieren

Wenn du keine Web-GUI möchtest, lade stattdessen `OnionCall-Terminal-Setup.py` herunter und starte:

```bash
python3 OnionCall-Terminal-Setup.py
```

Wähle **1**, um Systemprogramme, Tor, Audio-Werkzeuge, Repository und Python-Umgebung automatisch einzurichten. Nach **DONE** kann das Setup direkt `onioncall-terminal` öffnen. Installation, Status, Einrichtung, Anruf und Chat bleiben vollständig im Terminal; es wird kein lokaler Webserver gestartet.

Unter Android/Termux:

```bash
pkg install python
termux-setup-storage
python ~/storage/downloads/OnionCall-Terminal-Setup.py
```

### Mit lokaler Browser-GUI installieren

Lade `OnionCall-Setup.py` herunter und starte sie im Downloadordner:

```bash
python3 OnionCall-Setup.py
```

Die lokale Setup-Oberfläche öffnet sich im Browser. Klicke auf **Installation starten**. Das Setup erkennt die Plattform, installiert Tor und Audio-Werkzeuge, klont das Repository, erstellt eine virtuelle Umgebung, installiert OnionCall, prüft das Ergebnis und zeigt anschließend **DONE**. Mit **OnionCall öffnen** startest du danach die Anwendungs-GUI.

Nur Python 3.10 oder neuer muss bereits vorhanden sein, weil Python die Setup-Datei ausführt. Für Android/Termux sind außerdem die Apps Termux und Termux:API erforderlich:

```bash
pkg install python
termux-setup-storage
python ~/storage/downloads/OnionCall-Setup.py
```

Unter macOS wird Homebrew für Tor und Audio benötigt. Fehlt es, verweist das Setup auf die offizielle Homebrew-Seite, führt aber kein heruntergeladenes Administratorskript selbstständig aus.

Alle Oberflächen werden ausschließlich lokal auf `127.0.0.1` bereitgestellt. Es wird kein Webkonto angelegt und kein zentraler OnionCall-Server benutzt. Die folgenden Abschnitte dokumentieren zusätzlich die vollständige **manuelle Installation**; dabei müssen die Befehle nacheinander ausgeführt werden.

## Das Wichtigste vorab

OnionCall besteht aus zwei Teilen:

1. **Systemprogramme** für Python, Tor und Audio. Diese werden mit `dnf`, `apt`, `pacman`, Homebrew oder `pkg` installiert.
2. **Der OnionCall-Quellcode** aus diesem GitHub-Repository. Dieser muss heruntergeladen werden.

> [!IMPORTANT]
> **Tor ist eine zwingende Voraussetzung und muss vor OnionCall installiert werden.** OnionCall enthält Tor nicht. Beim Start eines Gesprächs startet OnionCall selbst einen getrennten Tor-Prozess, deshalb musst du den systemweiten Tor-Dienst nicht mit `systemctl` oder `brew services` starten. Nach der Einrichtung muss `onioncall doctor` für `tor` den Status `[OK]` melden.

Der Befehl

```bash
python -m pip install .
```

bedeutet: „Installiere das Python-Projekt aus dem **aktuellen Ordner**.“ Der Punkt `.` steht für den aktuellen Ordner. Der Befehl funktioniert deshalb nur im heruntergeladenen Verzeichnis `OnionCall`, in dem `pyproject.toml` liegt.

Vor der Installation immer prüfen:

```bash
pwd
ls pyproject.toml
```

Wenn `ls` meldet, dass `pyproject.toml` nicht existiert, bist du im falschen Ordner. Wechsle zuerst mit `cd` in `OnionCall`.

## Downloadmethode wählen

Verwende entweder Git oder eine ZIP-Datei. Git ist für spätere Aktualisierungen einfacher.

### Methode A: Mit Git herunterladen (empfohlen)

Nachdem `git` entsprechend dem Abschnitt für dein Betriebssystem installiert wurde:

```bash
cd ~
git clone https://github.com/BlackRabbitZ/OnionCall.git
cd OnionCall
ls pyproject.toml
```

Die Befehle bedeuten:

- `cd ~`: wechselt in dein persönliches Home-Verzeichnis.
- `git clone …`: lädt das gesamte Repository in den neuen Ordner `OnionCall`.
- `cd OnionCall`: wechselt in den heruntergeladenen Projektordner.
- `ls pyproject.toml`: kontrolliert, ob du im richtigen Ordner bist.

### Methode B: ZIP-Datei herunterladen

1. Öffne <https://github.com/BlackRabbitZ/OnionCall>.
2. Wähle **Code → Download ZIP**.
3. Entpacke `OnionCall-main.zip`.
4. Öffne ein Terminal und wechsle in den entpackten Ordner.

Unter Linux liegt die Datei normalerweise in `~/Downloads`:

```bash
cd ~/Downloads
unzip OnionCall-main.zip
cd OnionCall-main
ls pyproject.toml
```

Falls du stattdessen das Release-Archiv `OnionCall-v2.5.0.zip` verwendest:

```bash
cd ~/Downloads
unzip OnionCall-v2.5.0.zip
cd OnionCall
ls pyproject.toml
```

Dateiname oder Downloadordner können abweichen. Suche bei Bedarf so:

```bash
find ~ -maxdepth 5 -name pyproject.toml 2>/dev/null
```

Wechsle anschließend mit `cd PFAD` in den Ordner, der die gefundene `pyproject.toml` enthält.

## Fedora

### 1. Systemprogramme installieren

```bash
sudo dnf install git python3 python3-pip tor opus-tools alsa-utils unzip
```

Installiert werden:

- `git`: lädt und aktualisiert das Repository.
- `python3`: führt OnionCall aus.
- `python3-pip`: installiert das Python-Projekt und seine Python-Abhängigkeiten.
- `tor`: stellt Onion-Verbindungen und den persönlichen Onion-Service bereit.
- `opus-tools`: enthält `opusenc` und `opusdec` für Sprachkomprimierung.
- `alsa-utils`: enthält `arecord` und `aplay` für Mikrofon und Wiedergabe.
- `unzip`: wird nur benötigt, wenn du die ZIP-Methode verwendest.

### 2. Repository herunterladen

```bash
cd ~
git clone https://github.com/BlackRabbitZ/OnionCall.git
cd OnionCall
ls pyproject.toml
```

### 3. Virtuelle Python-Umgebung erstellen

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Die virtuelle Umgebung hält OnionCall und seine Python-Pakete vom restlichen System getrennt. Nach der Aktivierung beginnt die Eingabezeile normalerweise mit `(.venv)`.

### 4. OnionCall aus dem aktuellen Projektordner installieren

```bash
python -m pip install --upgrade pip
python -m pip install .
```

Der zweite Befehl muss weiterhin im Ordner `~/OnionCall` ausgeführt werden.

### 5. Einrichten und prüfen

```bash
onioncall --version
onioncall init
onioncall doctor
```

`init` legt Konfiguration und Verbindungsschlüssel unter `~/.config/onioncall` mit privaten Dateirechten an. `doctor` prüft Python, Tor, Audio-Werkzeuge, Datenverzeichnis und Schlüssel.

## Debian, Ubuntu und Raspberry Pi OS

### 1. Systemprogramme installieren

```bash
sudo apt update
sudo apt install git python3 python3-venv python3-pip tor opus-tools alsa-utils unzip
```

### 2. Repository herunterladen und öffnen

```bash
cd ~
git clone https://github.com/BlackRabbitZ/OnionCall.git
cd OnionCall
ls pyproject.toml
```

### 3. Installieren und prüfen

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
onioncall --version
onioncall init
onioncall doctor
```

## Arch Linux und darauf basierende Distributionen

### 1. Systemprogramme installieren

```bash
sudo pacman -Syu
sudo pacman -S --needed git python tor opus-tools alsa-utils unzip
```

### 2. Repository herunterladen, installieren und prüfen

```bash
cd ~
git clone https://github.com/BlackRabbitZ/OnionCall.git
cd OnionCall
ls pyproject.toml
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
onioncall init
onioncall doctor
```

## macOS

Benötigt wird [Homebrew](https://brew.sh/). Installiere Homebrew zuerst von dessen offizieller Website, falls `brew --version` nicht funktioniert.

### 1. Systemprogramme installieren

```bash
brew install git python tor opus-tools sox
```

`sox` stellt auf macOS die Befehle `rec` und `play` bereit.

### 2. Repository herunterladen, installieren und prüfen

```bash
cd ~
git clone https://github.com/BlackRabbitZ/OnionCall.git
cd OnionCall
ls pyproject.toml
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
onioncall init
onioncall doctor
```

Erlaube dem Terminal beim ersten Aufnahmeversuch den Mikrofonzugriff unter **Systemeinstellungen → Datenschutz & Sicherheit → Mikrofon**.

## Android mit Termux

Termux ist eine Linux-Umgebung innerhalb von Android. Installiere **Termux** und die separate App **Termux:API** aus derselben vertrauenswürdigen Quelle, vorzugsweise F-Droid. Erteile Termux:API in Android die Mikrofonberechtigung.

### 1. Termux-Pakete installieren

```bash
pkg update
pkg upgrade
pkg install git python python-cryptography tor opus-tools sox ffmpeg termux-api
```

`python-cryptography` wird über Termux installiert, damit die große Kryptografie-Bibliothek nicht auf dem Smartphone kompiliert werden muss.

### 2. Repository herunterladen

```bash
cd ~
git clone https://github.com/BlackRabbitZ/OnionCall.git
cd OnionCall
ls pyproject.toml
```

### 3. Virtuelle Umgebung mit Zugriff auf Termux-Systempakete erstellen

```bash
python -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install .
```

Verwende in Termux absichtlich `--system-site-packages`, damit OnionCall das zuvor installierte `python-cryptography` nutzen kann. Aktualisiere Termux' `pip` nicht manuell.

### 4. Einrichten und prüfen

```bash
onioncall init
onioncall doctor
```

Android kann lange laufende Prozesse im Hintergrund beenden. Deaktiviere bei Bedarf die Akkuoptimierung für Termux und Termux:API.

## Grafische Oberfläche starten

Nach der automatischen Installation verwendest du den angelegten Starter oder:

```bash
onioncall-gui
```

Alternativ öffnen `onioncall` und `onioncall gui` dieselbe lokale Oberfläche. Sie bietet Tor- und Audiostatus, Empfangen, Anrufen, Schlüsseleinrichtung, Textchat und zeitlich begrenzte Sprachnachrichten. Bei der ersten Einrichtung gehst du so vor:

1. Gerät A: **Schlüssel anzeigen**, Schlüsselzeile sicher an Gerät B senden.
2. Gerät B: **Schlüssel importieren**, vollständige Zeile einfügen und sicher speichern.
3. Gerät A: **Empfangen**, warten und dessen angezeigte Onion-Adresse weitergeben.
4. Gerät B: **Onion-Adresse anrufen**, genau diese Empfängeradresse einfügen.

OnionCall merkt sich die zuletzt angerufene Adresse. Eine `.onion`-Adresse wird als Schlüssel abgewiesen; eine mit `onioncall:v2:` beginnende Schlüsselzeile wird als Adresse abgewiesen.

Die einmalige bewusste Übertragung von Schlüssel und Empfängeradresse bleibt erforderlich. Dadurch braucht OnionCall weder automatische Erkennung im lokalen Netzwerk noch einen zentralen Kontaktserver.

Die vollständige nummerierte Terminal-Oberfläche bleibt mit `onioncall-terminal`, `onioncall terminal` oder `onioncall menu` verfügbar. Sie enthält zusätzlich Onion-Adresse, Audiotest und Einstellungen.

Die Terminal-Oberfläche zeigt **BRZ – OnionCall** und aktiviert Farben nur in einem interaktiven Terminal. Für monochrome Ausgabe oder Bildschirmleser kannst du sie abschalten:

```bash
NO_COLOR=1 onioncall-terminal
```

## Zwei Geräte Schritt für Schritt verbinden

Im folgenden Beispiel empfängt **Gerät A** den Anruf und **Gerät B** ruft an. Jedes Gerät besitzt eine eigene Onion-Adresse. Unterschiedliche Adressen sind normal. Der Anrufer verwendet immer exakt die Adresse, die der Empfänger bei `onioncall listen` anzeigt.

### 1. Installation auf beiden Geräten prüfen

Auf beiden Geräten:

```bash
cd ~/OnionCall
source .venv/bin/activate
onioncall doctor
```

Bei einer ZIP-Installation kann der Ordner `~/OnionCall-main` heißen. Fahre erst fort, wenn Tor und die übrigen Prüfungen `[OK]` melden.

### 2. Verbindungsschlüssel sicher austauschen

Beide Geräte müssen denselben zufälligen Verbindungsschlüssel besitzen.

#### 2.1 Auf Gerät A anzeigen

Auf Gerät A:

```bash
onioncall init
onioncall show-secret --confirm
```

Meldet `onioncall init`, dass `~/.config/onioncall/conversation.key` bereits existiert, ist auf diesem Gerät schon ein Schlüssel eingerichtet. Er wird absichtlich nicht überschrieben. Zeige den vorhandenen Schlüssel mit diesem einzelnen Befehl erneut an:

```bash
onioncall show-secret --confirm
```

Führe mehrere Befehle immer in getrennten Zeilen aus. Schreibe beispielsweise nicht `onioncall doctor~onioncall show-secret --confirm`: Die Shell behandelt `doctor~onioncall` dann als einen ungültigen Befehlsnamen. Das Zeichen `~` steht in Pfaden für dein Home-Verzeichnis, ist aber kein Trennzeichen zwischen Befehlen.

Die Ausgabe besteht aus einer langen Zeile, die mit `onioncall:v2:` beginnt. Kopiere sie vollständig vom Präfix bis zum letzten Zeichen. Kopiere weder den Shell-Prompt noch Anführungszeichen, Zeilenumbrüche, Leerzeichen oder andere Terminalausgaben mit.

Übermittle ausschließlich diese vollständige Zeichenfolge über einen bereits sicheren, vertrauenswürdigen Kanal an Gerät B. Keine Gruppen, öffentlichen Chats oder unverschlüsselte E-Mail verwenden.

#### 2.2 Auf Gerät B verdeckt importieren

Auf Gerät B:

```bash
onioncall set-secret --replace
```

Gib den Befehl genau einmal ein. Steht links im Prompt bereits `(.venv)`, ist die virtuelle Umgebung aktiv und muss nicht erneut aktiviert werden. Der vollständige Ablauf sieht so aus:

```text
(.venv) [user@computer OnionCall]$ onioncall set-secret --replace
Verbindungsschlüssel (Eingabe bleibt unsichtbar):
Verbindungsschlüssel sicher gespeichert.
```

Zwischen der zweiten und dritten Zeile wird der Schlüssel eingefügt und mit Enter bestätigt; er bleibt dabei vollständig unsichtbar.

OnionCall fragt jetzt verdeckt nach dem Schlüssel:

```text
Verbindungsschlüssel (Eingabe bleibt unsichtbar):
```

Füge die vollständige Zeile `onioncall:v2:…` ein und drücke einmal Enter. Beim Einfügen erscheinen absichtlich keine Zeichen, Punkte oder Sternchen. Bei Erfolg steht anschließend:

```text
Verbindungsschlüssel sicher gespeichert.
```

Gib den Schlüssel nicht direkt als Argument hinter `onioncall set-secret` ein. Dadurch könnte er in der Shell-History oder in Prozessinformationen sichtbar werden; die aktuelle Version weist zusätzliche Argumente deshalb ab. Verwende ausschließlich den Befehl `onioncall set-secret --replace` und danach die unsichtbare Eingabe.

Schreibe den Befehl nicht doppelt in dieselbe Zeile. Diese Eingabe ist falsch:

```bash
onioncall set-secret --replace onioncall set-secret --replace
```

Sie verursacht `onioncall: error: unrecognized arguments: set-secret`. Beginne dann eine neue Zeile und gib den Befehl genau einmal ein.

Prüfe den Import auf Gerät B:

```bash
onioncall doctor
```

Der Verbindungsschlüssel muss mit `[OK]` gemeldet werden. Sein geheimer Inhalt wird dabei nicht angezeigt.

Kopiere niemals den gesamten Ordner `~/.config/onioncall` auf das andere Gerät. Importiere nur die Zeichenfolge `onioncall:v2:…`. Der Schlüssel muss auf beiden Geräten gleich sein; ihre Onion-Adressen sollen dagegen voneinander verschieden sein.

### 3. Empfänger starten

Auf Gerät A:

```bash
onioncall listen
```

Warte, bis OnionCall eine Adresse mit 56 Zeichen vor `.onion` anzeigt. Lass diesen Prozess und das Terminal laufen. Die angezeigte Adresse ist die **Empfängeradresse für diesen Anruf**.

### 4. Empfängeradresse an den Anrufer senden

Übermittle die vollständige Adresse von Gerät A an Gerät B und vergleiche sie Zeichen für Zeichen. Verwende nicht die eigene Onion-Adresse von Gerät B, keine Adresse eines anderen Geräts und keine Adresse aus einer gelöschten oder neu eingerichteten Installation.

### 5. Vom Anrufer verbinden

Während Gerät A weiterhin wartet, auf Gerät B:

```bash
onioncall call HIER-DIE-ONION-ADRESSE.onion
```

Ersetze den vollständigen Platzhalter durch die Adresse, die gerade auf Gerät A steht. Unterschiedliche Onion-Adressen auf Gerät A und B sind normal und kein Fehler.

### 6. Gespräch verwenden

In der Sitzung reicht die vereinfachte Eingabe:

```text
Hallo           Text direkt senden
a               fünf Sekunden aufnehmen und senden
q               Sitzung beenden
```

Eingehende Nachrichten werden oberhalb der aktiven Zeile `Du >` eingefügt. Bereits getippter, noch nicht abgesendeter Text bleibt dabei vollständig erhalten. `[Du]` kennzeichnet eigene Nachrichten und `[Gegenstelle]` empfangene Nachrichten.

Alternativ funktionieren weiterhin die ausführlichen Befehle:

```text
/text Hallo     Text senden
/say 5          fünf Sekunden aufnehmen und senden
/help           Hilfe anzeigen
/quit           Sitzung beenden
```

Für ein weiteres Gespräch startet der Empfänger erneut `onioncall listen`. Beim Rollenwechsel startet das andere Gerät `listen`; angerufen wird dann dessen angezeigte Adresse.

## Nach einem Neustart erneut verwenden

Die Installation muss nicht wiederholt werden. Aktiviere nur die vorhandene virtuelle Umgebung:

```bash
cd ~/OnionCall
source .venv/bin/activate
onioncall doctor
```

Danach kannst du die GUI öffnen:

```bash
onioncall-gui
```

Für die automatische Installation ist keine Aktivierung im Projektordner nötig; verwende einfach den angelegten Anwendungsstarter oder `~/.local/bin/onioncall-gui`.

## Aktualisieren

Bei Installation mit Git:

```bash
cd ~/OnionCall
git pull --ff-only
source .venv/bin/activate
python -m pip install --upgrade .
onioncall doctor
```

Bei einer ZIP-Installation die neue ZIP-Datei herunterladen, in einen neuen Ordner entpacken, dort eine neue virtuelle Umgebung anlegen und erneut installieren.

## Deinstallieren

Innerhalb der aktivierten virtuellen Umgebung:

```bash
python -m pip uninstall onioncall
deactivate
```

Anschließend kannst du den Projektordner löschen. Persönliche Konfiguration und Schlüssel liegen separat unter `~/.config/onioncall`. Lösche dieses Verzeichnis nur, wenn du den Schlüssel und die Onion-Identität wirklich nicht mehr benötigst.

## Häufige Fehler

### `Directory '.' is not installable`

Ursache: Du befindest dich nicht im OnionCall-Projektordner.

```bash
find ~ -maxdepth 5 -name pyproject.toml 2>/dev/null
cd /PFAD/ZUM/GEFUNDENEN/OnionCall
ls pyproject.toml
python -m pip install .
```

### `git: command not found`

Installiere `git` mit dem Paketbefehl deiner Plattform oder nutze die ZIP-Methode.

### `onioncall: command not found`

Aktiviere die virtuelle Umgebung:

```bash
cd ~/OnionCall
source .venv/bin/activate
```

Prüfe danach:

```bash
python -m pip show onioncall
onioncall --version
```

### `No module named venv`

Auf Debian/Ubuntu fehlt `python3-venv`:

```bash
sudo apt install python3-venv
```

### `Schlüssel existiert bereits` oder `invalid choice: 'doctor~onioncall'`

Ein vorhandener Schlüssel wird aus Sicherheitsgründen nicht durch `onioncall init` überschrieben. Zeige ihn so an:

```bash
onioncall show-secret --confirm
```

Der Fehler `invalid choice: 'doctor~onioncall'` bedeutet, dass zwei Befehle versehentlich zusammengefügt wurden. Führe sie einzeln aus:

```bash
onioncall doctor
onioncall show-secret --confirm
```

Veröffentliche die angezeigte Zeichenfolge nicht. Nutze `onioncall init --replace` nur, wenn du bewusst einen neuen Gesprächsschlüssel erzeugen und den bisherigen ungültig machen möchtest.

### `unrecognized arguments: set-secret`

Ursache: `onioncall set-secret --replace` wurde zweimal in dieselbe Befehlszeile eingefügt, zum Beispiel:

```bash
# Falsch:
onioncall set-secret --replace onioncall set-secret --replace
```

Gib den Befehl in einer neuen Zeile genau einmal ein:

```bash
onioncall set-secret --replace
```

Füge erst bei der anschließenden unsichtbaren Abfrage ausschließlich die vollständige Schlüsselzeile `onioncall:v2:…` ein und drücke Enter. Wenn der Prompt schon mit `(.venv)` beginnt, ist die virtuelle Umgebung bereits aktiv.

### `doctor` meldet fehlende Programme

Installiere genau die als `[FEHLT]` angezeigten Befehle über den Paketmanager deiner Plattform. Prüfe Mikrofon und Wiedergabe unter Linux zusätzlich mit:

```bash
arecord -l
aplay -l
```

### Tor startet nicht

Die detaillierte Meldung steht in:

```bash
cat ~/.config/onioncall/tor/tor.log
```

Ab Version 2.4 zeigt OnionCall die relevanten Tor-Warnungen normalerweise bereits direkt in der Fehlermeldung. Meldet OnionCall, dass der SOCKS-Port `19050` belegt ist, läuft wahrscheinlich noch eine andere OnionCall-/Tor-Instanz. Beende diese Instanz oder ändere in der Terminal-Oberfläche unter **7 Einstellungen** den Tor-SOCKS-Port.

Teile Logs nur nach Prüfung; sie können Informationen über dein System oder deine Nutzung enthalten.

### `Tor konnte die Onion-Adresse nicht verbinden (SOCKS-Code 4)`

Tor konnte den angegebenen Onion-Service nicht erreichen. Kontrolliere in dieser Reihenfolge:

1. Auf dem Empfänger läuft `onioncall listen` weiterhin.
2. Der Anrufer verwendet exakt die Onion-Adresse, die der Empfänger gerade anzeigt.
3. Der Anrufer verwendet nicht seine eigene Adresse oder eine Adresse aus einer früheren Installation.
4. Beide Geräte haben Internetzugang und `onioncall doctor` meldet Tor als `[OK]`.

Jedes Gerät hat eine eigene Onion-Adresse; unterschiedliche Adressen sind richtig. Ein falscher Verbindungsschlüssel verursacht keinen SOCKS-Code 4, sondern erst nach dem Tor-Verbindungsaufbau einen Authentifizierungsfehler.

## Sicherheitsgrenze

OnionCall ist Alpha-Software und wurde nicht unabhängig auditiert. Nutze es nicht als alleinige Schutzmaßnahme in einer Hochrisikosituation. Das Sicherheitsmodell und seine Grenzen stehen in [SECURITY.md](../SECURITY.md).
