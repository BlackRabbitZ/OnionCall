# Installer-Änderungen 2.7.3

## Problem

Einige aktuelle Windows-Python-/pip-Kombinationen brechen beim direkten `socks5h://`-Proxy mit `proxy_ssl_context`-TypeErrors im von pip gebündelten urllib3 ab.

## Lösung

Der Installer gibt pip keinen SOCKS-Proxy mehr direkt. Stattdessen startet er temporär einen nur an `127.0.0.1` gebundenen HTTP-CONNECT-Proxy. Dieser baut jede HTTPS-Zielverbindung über den lokalen Tor-SOCKS-Port auf.

- pip → `http://127.0.0.1:<zufälliger Port>`
- lokaler Bridge-Proxy → Tor SOCKS `127.0.0.1:19052`
- Tor → PyPI / files.pythonhosted.org

TLS wird nicht terminiert oder entschlüsselt; pip führt die TLS-Verbindung weiterhin selbst zum Zielserver. Domainnamen werden als SOCKS5-Domain an Tor übergeben und nicht lokal aufgelöst. Der Bridge-Proxy akzeptiert ausschließlich HTTP CONNECT auf Port 443.

Die OnionCall-Haupt-GUI wurde nicht verändert.
