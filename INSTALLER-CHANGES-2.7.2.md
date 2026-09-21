# Installer-Änderungen 2.7.2

Der Windows-Setup-Pfad über Tor konnte mit bestimmten von pip gebündelten urllib3-Versionen mit
`PoolKey.__new__() got an unexpected keyword argument 'key_proxy_ssl_context'` abbrechen.

2.7.2 startet den Netzwerk-Pip-Lauf über `scripts/pip_tor_runner.py`. Der Starter entfernt nur den
inkompatiblen `proxy_ssl_context`-Eintrag aus dem internen urllib3-Pool-Cache-Schlüssel, wenn die
verwendete `PoolKey`-Version dieses Feld nicht unterstützt. TLS-Zertifikatsprüfung, SOCKS5h und
Tor bleiben unverändert aktiv.

Die OnionCall-Haupt-GUI wurde nicht verändert.
