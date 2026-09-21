#!/usr/bin/env bash
set -euo pipefail
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PY="$ROOT/.venv/bin/python"; [[ -x "$PY" ]] || PY=$(command -v python3 || true)
usage(){ cat <<'HELP'
OnionCall Linux OS-Killswitch (Python-only)
  scripts/onioncall-killswitch-linux.sh call <onion-adresse> [--peer NAME]
  scripts/onioncall-killswitch-linux.sh listen [--peer NAME]
HELP
}
[[ ${1:-} != --help && ${1:-} != -h ]] || { usage; exit 0; }
[[ $(uname -s) == Linux ]] || { echo "Nur Linux wird unterstützt." >&2; exit 2; }
command -v systemd-run >/dev/null || { echo "systemd-run fehlt." >&2; exit 2; }
command -v systemctl >/dev/null || { echo "systemctl fehlt." >&2; exit 2; }
command -v tor >/dev/null || { echo "tor fehlt." >&2; exit 2; }
[[ -n "$PY" && -x "$PY" ]] || { echo "python3 bzw. .venv/bin/python fehlt." >&2; exit 2; }
mode=${1:-}; [[ $mode == call || $mode == listen ]] || { usage; exit 2; }; shift
if ! systemd-run --user --wait --quiet --collect -p IPAddressDeny=any -p IPAddressAllow=localhost /usr/bin/true >/dev/null 2>&1; then
  echo "systemd/kernel unterstützt den IPAddress-Killswitch nicht zuverlässig. Abbruch." >&2; exit 3
fi
read -r SOCKS_PORT LISTEN_PORT HOME_DIR < <("$PY" - <<'READCFG'
from onioncall.config import app_home, load_config
c=load_config(); print(c.socks_port, c.listen_port, app_home())
READCFG
)
KS_DIR="$HOME_DIR/killswitch"; mkdir -p "$KS_DIR/data"; chmod 700 "$KS_DIR" "$KS_DIR/data"
TORRC="$KS_DIR/torrc"; LOG="$KS_DIR/tor.log"; TOR_UNIT="onioncall-tor-${UID}-$$"; APP_UNIT="onioncall-app-${UID}-$$"
cleanup(){ systemctl --user stop "$TOR_UNIT.service" >/dev/null 2>&1 || true; }; trap cleanup EXIT INT TERM
cat > "$TORRC" <<EOF
DataDirectory $KS_DIR/data
SocksPort 127.0.0.1:$SOCKS_PORT
SafeSocks 1
TestSocks 1
SafeLogging 1
Log notice file $LOG
EOF
CLIENT_AUTH="$HOME_DIR/tor_auth/client"
if compgen -G "$CLIENT_AUTH/*.auth_private" >/dev/null 2>&1; then echo "ClientOnionAuthDir $CLIENT_AUTH" >> "$TORRC"; fi
if [[ $mode == listen ]]; then
  HS_DIR="$KS_DIR/onion_service"; AUTH_DIR="$HS_DIR/authorized_clients"; mkdir -p "$HS_DIR"; chmod 700 "$HS_DIR"; rm -rf "$AUTH_DIR"
  SERVER_AUTH="$HOME_DIR/tor_auth/server"
  if compgen -G "$SERVER_AUTH/*.auth" >/dev/null 2>&1; then mkdir -p "$AUTH_DIR"; chmod 700 "$AUTH_DIR"; cp "$SERVER_AUTH"/*.auth "$AUTH_DIR"/; chmod 600 "$AUTH_DIR"/*.auth; fi
  cat >> "$TORRC" <<EOF
HiddenServiceDir $HS_DIR
HiddenServiceVersion 3
HiddenServicePort $LISTEN_PORT 127.0.0.1:$LISTEN_PORT
EOF
fi
chmod 600 "$TORRC"; systemd-run --user --quiet --collect --unit="$TOR_UNIT" tor -f "$TORRC"
"$PY" - "$SOCKS_PORT" <<'WAITPY'
import socket,sys,time
p=int(sys.argv[1]); end=time.monotonic()+120
while time.monotonic()<end:
    try:
        with socket.create_connection(('127.0.0.1',p),timeout=.5): raise SystemExit(0)
    except OSError: time.sleep(.25)
raise SystemExit('Tor-SOCKS wurde nicht bereit')
WAITPY
COMMON=(--user --wait --pty --collect --unit="$APP_UNIT" -p IPAddressDeny=any -p IPAddressAllow=localhost -p RestrictAddressFamilies="AF_UNIX AF_INET AF_INET6" -p NoNewPrivileges=yes -p PrivateTmp=yes)
if [[ $mode == call ]]; then
  [[ $# -ge 1 ]] || { usage; exit 2; }; systemd-run "${COMMON[@]}" "$PY" -m onioncall.cli call --existing-tor "$@"
else
  for _ in $(seq 1 480); do [[ -s "$KS_DIR/onion_service/hostname" ]] && break; sleep .25; done
  [[ -s "$KS_DIR/onion_service/hostname" ]] || { echo "Onion-Adresse wurde nicht erzeugt." >&2; exit 4; }
  echo "Onion-Adresse: $(cat "$KS_DIR/onion_service/hostname")"
  systemd-run "${COMMON[@]}" "$PY" -m onioncall.cli direct-listen --host 127.0.0.1 --port "$LISTEN_PORT" "$@"
fi
