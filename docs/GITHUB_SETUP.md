# Empfohlene GitHub-Einstellungen

Nach dem ersten Upload sind folgende Einstellungen sinnvoll:

## Allgemein

- Standard-Branch `main`
- Issues aktivieren
- Private Vulnerability Reporting unter **Settings → Security → Code security** aktivieren
- Secret Scanning und Push Protection aktivieren, soweit für das Repository verfügbar
- keine echten Verbindungsschlüssel als Actions-Secrets speichern

## Branch-Regeln für `main`

- Pull Request vor Merge verlangen
- mindestens eine Freigabe verlangen
- erfolgreiche Statusprüfung `Test / CI erfolgreich` verlangen
- veraltete Freigaben bei neuen Commits verwerfen
- direkte Force-Pushes und Löschen des Branches sperren

## Actions

- Workflow-Berechtigungen standardmäßig auf **Read repository contents** setzen
- Schreibberechtigungen nur gezielt erlauben; hier benötigt ausschließlich der Release-Workflow `contents: write`
- Actions nur von GitHub beziehungsweise verifizierten Herausgebern zulassen

## Erste Veröffentlichung

```bash
git init
git branch -M main
git add .
git commit -m "Release BRZ - OnionCall 2.4 with colored terminal"
git remote add origin https://github.com/BlackRabbitZ/OnionCall.git
git push -u origin main
```

Vor `git add .` immer `git status --short --ignored` prüfen. Insbesondere dürfen `conversation.key`, Tor-Verzeichnisse, Onion-Service-Schlüssel, Logs und lokale virtuelle Umgebungen nicht im Commit erscheinen.
