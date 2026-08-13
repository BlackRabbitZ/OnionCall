# Zu OnionCall beitragen

Danke für dein Interesse. OnionCall verarbeitet sicherheitsrelevante Daten; kleine, nachvollziehbare Änderungen mit passenden Tests sind deshalb besser als große Sammel-Pull-Requests.

## Vor einer Änderung

- Sicherheitslücken nicht öffentlich melden. Folge [SECURITY.md](SECURITY.md).
- Öffne bei größeren Funktionen zunächst ein Feature-Issue.
- Änderungen am Protokoll benötigen eine Bedrohungsanalyse, Testvektoren und eine dokumentierte Migrationsstrategie.
- Füge keine optionalen Cipher-Suites oder unsicheren Kompatibilitätsmodi hinzu.

## Entwicklungsumgebung

Repository herunterladen und in den Projektordner wechseln:

```bash
cd ~
git clone https://github.com/BlackRabbitZ/OnionCall.git
cd OnionCall
ls pyproject.toml
```

Erst innerhalb dieses Ordners die Entwicklungsumgebung erstellen:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Die benötigten Systempakete für alle unterstützten Plattformen beschreibt [docs/INSTALLATION.md](docs/INSTALLATION.md).

Vor einem Pull Request müssen diese Befehle erfolgreich sein:

```bash
ruff check .
python -m compileall -q onioncall tests
python -m unittest discover -s tests -v
python -m build
```

Tests dürfen keine echte Onion-Adresse, keinen echten Verbindungsschlüssel und keine dauerhaften Dateien im Benutzerprofil erzeugen. Verwende `tempfile` oder setze `ONIONCALL_HOME` auf ein temporäres Verzeichnis.

## Pull Requests

- Beschreibe Zweck, Sicherheitsauswirkung und Testverfahren.
- Halte Änderungen plattformübergreifend oder dokumentiere eine bewusste Einschränkung.
- Aktualisiere README, SECURITY oder CHANGELOG, wenn sich Verhalten oder Sicherheitsmodell ändern.
- Verwende keine geheimen Daten in Logs, Screenshots, Commits oder Test-Fixtures.

Mit deinem Beitrag erklärst du dich damit einverstanden, ihn unter der Apache License 2.0 des Projekts zu veröffentlichen.
