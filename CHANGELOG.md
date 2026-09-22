# Changelog

## 2.7.6
### Installer / Tor-Paketdownload (Hotfix)
- Windows: Browser-Installer richtet FFmpeg 9.0.2 Essentials automatisch projektlokal ein; SHA-256-verifiziert, standardmäßig über Tor.
- Privater Python-Paketdownload nutzt jetzt Tor's nativen lokalen `HTTPTunnelPort` statt eines zusätzlichen internen HTTP→SOCKS-Bridge-Prozesses.
- Temporäre Tor-Ports werden dynamisch gewählt; ein belegter fester Port kann die Installation nicht mehr blockieren.
- Der temporäre Tor-Prozess startet mit dem Tor-Binärverzeichnis als Arbeitsverzeichnis (wichtig für Windows-Bundles).
- Der Browser-Installer zeigt den echten Tor-Bootstrap-Fortschritt und wartet auf `Bootstrapped 100%`, bevor `pip` startet.
- Ein fehlgeschlagener privater Tor-Start wird einmal vollständig mit neuer DataDirectory/Ports wiederholt. Kein automatischer Clearnet-Fallback.
- Bei einem endgültigen Fehlschlag werden Bootstrap-Stand und letzte Tor-Meldungen im Installationsprotokoll ausgegeben.
- Der Windows-Killswitch-Status prüft jetzt, ob die Firewallregeln tatsächlich den `.venv`-Python dieses aktuellen Projektordners schützen; alte Regeln aus einem anderen entpackten Ordner werden nicht mehr fälschlich als aktiv angezeigt.

- Haupt-GUI-Layout auf den bisherigen 2.7.5-Stil zurückgeführt; Browser-Installer-Layout bleibt unverändert. Sicherheitsfixes und Statuslogik aus 2.7.6 bleiben aktiv. — Security Hotfix

Siehe `SECURITY-CHANGES-2.7.6.md`. Schwerpunkt: GUI-Regressionsfix, DoS-Härtung, Audio-Validierung, Windows-Audio, Dependency-/Update-Härtung, Schlüsselspeicher und Onion-v3-Validierung.

Zusätzlich wurde der lokale Browser-Installer wieder als Standard eingerichtet. `OnionCall-Setup.py` öffnet die Setup-Oberfläche im Browser; unter Windows startet `OnionCall-Setup.cmd` sie ohne sichtbares Konsolenfenster. Der Browser-Installer bindet nur an `127.0.0.1`, nutzt einen zufälligen API-Token, Same-Origin-Prüfung und eine nonce-basierte Content-Security-Policy. `OnionCall-Terminal-Setup.py` bleibt als separate CLI-Alternative erhalten.

## 2.7.5

Vorheriger Stand des Projekts.

### GUI-Logo
- Neues BRZ-OnionCall-App-Icon (Hase + Onion/Tor, Rot/Lila) in der Haupt-GUI oben links integriert.
- Dasselbe Asset wird als Favicon der Haupt-GUI verwendet.
- Browser-Installer-Layout und dessen eigenes Setup-Symbol bleiben unverändert.
