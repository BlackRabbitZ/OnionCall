# Releases

1. `python -m unittest discover -s tests -v`
2. `ruff check .`
3. Version in `pyproject.toml` und `onioncall/__init__.py` anpassen.
4. Commit und annotierten/signierten Git-Tag erzeugen, z. B. `git tag -s v2.6.0` wenn ein eigener GPG/SSH-Signing-Key vorhanden ist.
5. Tag pushen.

Der GitHub-Workflow baut Wheel + sdist, erzeugt SHA-256-Hashes und GitHub Artifact Attestations. Die Attestation kann mit GitHub CLI geprüft werden:

```bash
gh attestation verify <datei> --repo BlackRabbitZ/OnionCall
```

Private Signierschlüssel gehören niemals in dieses Repository oder in Release-ZIPs.
