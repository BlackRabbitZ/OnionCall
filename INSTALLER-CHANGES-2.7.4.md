# Installer-Änderungen 2.7.4

Diese Version behebt Windows-Encodingfehler bei Installationsausgaben.

- `UnicodeEncodeError: charmap codec can't encode character \u2192` behoben.
- Installer und Backend erzwingen UTF-8 für stdout/stderr.
- Das grafische Setup liest das Backend explizit als UTF-8.
- Python-Unterprozesse erhalten `PYTHONIOENCODING=utf-8` und `PYTHONUTF8=1`.
- Der sichtbare Unicode-Pfeil in der Proxy-Statuszeile wurde durch `->` ersetzt.
- Keine Änderungen an `onioncall/webgui.py`.
