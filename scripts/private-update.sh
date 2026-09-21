#!/usr/bin/env bash
set -euo pipefail

# Aktualisiert ein vorhandenes Checkout ausschließlich über einen eigens gestarteten Tor-Client.
command -v torsocks >/dev/null || { echo "torsocks fehlt; kein unsicherer Fallback." >&2; exit 2; }
command -v git >/dev/null || { echo "git fehlt." >&2; exit 2; }
command -v tor >/dev/null || { echo "tor fehlt." >&2; exit 2; }

repo=$(git config --get remote.origin.url || true)
case "$repo" in
  https://github.com/BlackRabbitZ/OnionCall.git|git@github.com:BlackRabbitZ/OnionCall.git) ;;
  *) echo "Unerwartete Remote-URL: $repo" >&2; exit 4;;
esac

TMP=$(mktemp -d)
SOCKS_PORT=${ONIONCALL_UPDATE_SOCKS_PORT:-19051}
cleanup(){ [[ -n ${TOR_PID:-} ]] && kill "$TOR_PID" >/dev/null 2>&1 || true; rm -rf "$TMP"; }
trap cleanup EXIT INT TERM
mkdir -p "$TMP/data"; chmod 700 "$TMP" "$TMP/data"
cat > "$TMP/torrc" <<EOF
DataDirectory $TMP/data
SocksPort 127.0.0.1:$SOCKS_PORT
SafeSocks 1
TestSocks 1
SafeLogging 1
Log notice file $TMP/tor.log
EOF
chmod 600 "$TMP/torrc"
tor -f "$TMP/torrc" >/dev/null 2>&1 & TOR_PID=$!

python - "$SOCKS_PORT" <<'PY'
import socket, sys, time
port=int(sys.argv[1]); end=time.monotonic()+120
while time.monotonic()<end:
    try:
        with socket.create_connection(("127.0.0.1",port),timeout=.5):
            raise SystemExit(0)
    except OSError:
        time.sleep(.25)
raise SystemExit("Tor-SOCKS wurde nicht bereit")
PY

echo "[1/3] Fetch ausschließlich über temporären Tor-SOCKS $SOCKS_PORT …"
torsocks -a 127.0.0.1 -P "$SOCKS_PORT" git fetch --tags --prune origin

echo "[2/3] Fast-forward main …"
git checkout main
git merge --ff-only origin/main

echo "[3/3] Lokales Paket neu installieren (ohne Netz-Fallback) …"
PY="./.venv/bin/python"; [[ -x "$PY" ]] || PY=$(command -v python3)
"$PY" -m pip install --no-deps -e .

echo "Fertig. Release-Artefakte zusätzlich mit 'gh attestation verify' prüfen, wenn du aus Releases installierst."
