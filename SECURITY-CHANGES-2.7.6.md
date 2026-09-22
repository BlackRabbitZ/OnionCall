# OnionCall 2.7.6 – Security Hotfix

Dieser Patch ist für den Stand **OnionCall 2.7.5 / `main` vom 22.09.2026** vorgesehen. Er behebt bzw. härtet die zwölf Punkte aus der Sicherheitsanalyse.

| # | Problem | Änderung in 2.7.6 |
|---:|---|---|
| 1 | Web-GUI-JavaScript durch unescaped Zeilenumbruch ungültig | String wieder syntaktisch gültig; Regressionstest ergänzt |
| 2 | `test_webgui.py` verwendet alte `GuiHttpServer`-API | Tests auf `create_server`/`OnionHTTPServer`, Tokenpflicht und aktuelle API umgestellt |
| 3 | Ein langsamer Pre-Auth-Client blockiert den Listener | Begrenzte parallele Pre-Auth-Worker, 5-s-Timeout, sofortiges Abweisen bei vollem Pre-Auth-Limit |
| 4 | Nativer Audio-Decoder erhält nur oberflächlich geprüfte Daten | Strikte Ogg-Seiten-/Paketvalidierung inklusive CRC, Sequenz, Stream-Serial, BOS/EOS, OpusHead/OpusTags und Limits vor dem Decoder |
| 5 | Windows fällt auf `arecord`/`aplay` zurück | Eigener Windows-Pfad über FFmpeg DirectShow und `ffplay`; Mikrofon kann mit `ONIONCALL_AUDIO_DEVICE` gesetzt werden |
| 6 | Installer prüft nur, ob Imports funktionieren | Installierte Distributionen werden gegen exakt erwartete Versionen geprüft |
| 7 | Runtime-Dependencies sind nicht deterministisch gepinnt | `cryptography==50.0.1`, `prompt-toolkit==3.0.53`, `wcwidth==0.8.4`; außerdem `setuptools==84.0.0`, `build==1.6.1`, `ruff==0.16.8`; Lock-Dateien ergänzt |
| 8 | Tor-Update authentifiziert nicht den Git-Inhalt | Vor Merge ist signierter Commit/Tag oder ein außerbandig gepinnter `ONIONCALL_TRUSTED_COMMIT` erforderlich |
| 9 | App-Private-Keys liegen auf Windows im Klartext | Windows-DPAPI für Conversation-Key, Kontakt-PSKs und Ed25519-Identity; POSIX-Dateirechte/Symlink-Prüfung verschärft |
| 10 | Onion-v3 nur per Regex geprüft | Base32, Versionsbyte und offizielle SHA3-Onion-Prüfsumme werden validiert |
| 11 | Direktmodus akzeptiert ganz `127.0.0.0/8` | Exakt `127.0.0.1` und `::1`, passend zur Dokumentation |
| 12 | Manuell konstruierte schwache PSKs möglich | Import akzeptiert nur vollständige OnionCall-Tokens und weist offensichtliche schwache/repetitive 32-Byte-Werte zurück |

## Bewusst verbleibende Grenzen

Einige Restgrenzen lassen sich nicht durch einen kleinen Patch vollständig „wegprogrammieren“:

- **Native Audio-Decoder:** Die strikte Containerprüfung reduziert die Angriffsfläche deutlich. Ein noch unbekannter Fehler im eigentlichen Opus-/FFmpeg-Decoder bleibt grundsätzlich möglich, solange kein vollwertiger OS-Sandbox-Prozess verwendet wird.
- **Schlüssel-at-rest auf POSIX / Tor Client Authorization:** Windows-App-Schlüssel werden mit DPAPI geschützt. Unter Linux/macOS schützt OnionCall weiterhin primär über `0600`; Tor-Client-Authorization-Dateien müssen im von Tor lesbaren Format vorliegen. Eine echte plattformübergreifende Verschlüsselung-at-rest braucht ein separates Unlock-/Keychain-Konzept.
- **PSK-Entropie:** OnionCall kann offensichtliche schwache oder manuell konstruierte Tokens abweisen, aber nicht beweisen, dass ein beliebiger äußerlich zufällig wirkender 32-Byte-Wert tatsächlich kryptografisch zufällig erzeugt wurde. Deshalb nur von OnionCall erzeugte Tokens verwenden.
- **Dependency-Artefakte:** Die Versionen sind exakt gepinnt. Ein vollständiger plattformübergreifender `--require-hashes`-Lock für sämtliche Wheel-Varianten ist in diesem Hotfix noch nicht enthalten.

## Anwendung

1. ZIP entpacken.
2. Terminal/PowerShell im entpackten Hotfix-Ordner öffnen.
3. Patcher mit deinem lokalen OnionCall-Repository als Argument starten:

```powershell
py apply_security_fixes.py "C:\Pfad\zu\OnionCall"
```

Linux/macOS:

```bash
python3 apply_security_fixes.py /pfad/zu/OnionCall
```

Der Patcher legt vor jeder Änderung eine Sicherung unter `.onioncall-security-backup-*` im Repository an. Danach führt er `compileall` und – wenn möglich – die Unit-Tests aus.

## Automatische FFmpeg-Bereitstellung

Unter Windows kann der Browser-Installer FFmpeg 9.0.2 Essentials automatisch unter `tools/ffmpeg/` bereitstellen. Der Download ist auf eine konkrete Paketversion und SHA-256-Prüfsumme gepinnt. ZIP-Pfade werden vor dem Entpacken auf Traversal und Symlinks geprüft. Standardmäßig wird der Download über einen temporären Tor-HTTP-Tunnel durchgeführt; nur bei ausdrücklich aktiviertem direkten Paketdownload wird HTTPS ohne Tor verwendet. FFmpeg bleibt ein separates Drittanbieterprogramm und ist nicht Bestandteil des OnionCall-Quellcodes.
