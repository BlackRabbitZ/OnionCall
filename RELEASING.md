# Veröffentlichung einer Version

1. Tests und Build ausführen:

   ```bash
   make check
   ```

2. Version in `pyproject.toml` und `onioncall/__init__.py` identisch aktualisieren.
3. `CHANGELOG.md` ergänzen und das Datum eintragen.
4. Commit erstellen und einen signierten Tag setzen:

   ```bash
   git tag -s v2.0.1 -m 'OnionCall v2.0.1'
   git push origin main --follow-tags
   ```

5. Der Release-Workflow prüft Tests und Versionsgleichheit, baut Wheel sowie Source Distribution und legt daraus einen GitHub Release an.
6. Prüfsummen des veröffentlichten Artefakts dokumentieren. Eine PyPI-Veröffentlichung sollte erst nach Namensreservierung, Trusted-Publishing-Konfiguration und unabhängiger Paketprüfung aktiviert werden.

Keine Version veröffentlichen, solange eine bekannte Schwachstelle mit hoher Auswirkung ungepatcht ist.
