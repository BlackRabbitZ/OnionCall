# Contributing

- Änderungen klein und nachvollziehbar halten.
- Für sicherheitsrelevante Netzwerkänderungen Tests ergänzen.
- Kein neuer direkter Outbound-Socket außerhalb der expliziten Loopback-Helfer.
- Keine lokalen DNS-Auflösungen für Onion-Adressen.
- `python -m unittest discover -s tests -v` und `ruff check .` vor Pull Requests ausführen.
