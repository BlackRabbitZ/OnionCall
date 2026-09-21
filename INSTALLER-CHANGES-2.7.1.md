# Installer-Änderungen 2.7.1

Die OnionCall-Haupt-GUI wurde nicht verändert.

Unter Windows wird beim ersten Setup automatisch Tor bereitgestellt, falls kein vorhandenes `tor.exe` gefunden wird. Das Setup lädt das Tor Expert Bundle 15.0.23 ausschließlich vom offiziellen Tor-Project-Server und prüft SHA-256 `231dad6b9cb401a54c260db7046965ef04e4f72ff071b140d423fb5da281ab1e`.

Da vor diesem Schritt noch kein Tor vorhanden ist, ist genau dieser Bootstrap technisch eine direkte HTTPS-Verbindung. Danach werden fehlende Python-Pakete standardmäßig über den lokal gestarteten Tor-SOCKS-Proxy geladen. Es gibt keinen stillen Clearnet-Fallback.
