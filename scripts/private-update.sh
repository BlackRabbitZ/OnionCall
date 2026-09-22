#!/usr/bin/env bash
set -euo pipefail

# Aktualisiert ein vorhandenes Checkout ausschließlich über einen eigens gestarteten Tor-Client.
# Der neue Commit wird VOR dem Merge kryptografisch oder per explizit gepinntem Commit-Hash geprüft.

command -v torsocks >/dev/null || { echo "torsocks fehlt; kein unsicherer Fallback." >&2; exit 2; }
command -v git >/dev/null || { echo "git fehlt." >&2; exit 2; }
command -v tor >/dev/null || { echo "tor fehlt." >&2; exit 2; }

repo=$(git config --get remote.origin.url || true)
case "$repo" in
  https://github.com/BlackRabbitZ/OnionCall.git|git@github.com:BlackRabbitZ/OnionCall.git) ;;
  *) echo "Unerwartete Remote-URL: $repo" >&2; exit 4 ;;
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

echo "[1/4] Fetch ausschließlich über temporären Tor-SOCKS $SOCKS_PORT …"
torsocks -a 127.0.0.1 -P "$SOCKS_PORT" git fetch --tags --prune origin
TARGET=$(git rev-parse --verify 'origin/main^{commit}')
CURRENT=$(git rev-parse --verify 'main^{commit}')

if ! git merge-base --is-ancestor "$CURRENT" "$TARGET"; then
  echo "Update abgebrochen: origin/main ist kein Fast-Forward von lokalem main." >&2
  exit 5
fi

echo "[2/4] Ziel-Commit vor Installation verifizieren: $TARGET"
verified=0
if [[ -n ${ONIONCALL_TRUSTED_COMMIT:-} ]]; then
  PIN=$(printf '%s' "$ONIONCALL_TRUSTED_COMMIT" | tr '[:upper:]' '[:lower:]')
  ACTUAL=$(printf '%s' "$TARGET" | tr '[:upper:]' '[:lower:]')
  if [[ "$PIN" == "$ACTUAL" ]]; then
    verified=1
    echo "Commit stimmt mit ONIONCALL_TRUSTED_COMMIT überein."
  else
    echo "Update abgebrochen: gepinnter Commit $PIN stimmt nicht mit $ACTUAL überein." >&2
    exit 6
  fi
fi

if [[ $verified -eq 0 ]] && git verify-commit "$TARGET" >/dev/null 2>&1; then
  verified=1
  echo "Commit-Signatur wurde lokal erfolgreich verifiziert."
fi

if [[ $verified -eq 0 ]]; then
  while IFS= read -r tag; do
    [[ -z "$tag" ]] && continue
    if git verify-tag "$tag" >/dev/null 2>&1; then
      verified=1
      echo "Signierter Tag '$tag' wurde lokal erfolgreich verifiziert."
      break
    fi
  done < <(git tag --points-at "$TARGET")
fi

if [[ $verified -eq 0 ]]; then
  cat >&2 <<EOF
Update abgebrochen: Der Ziel-Commit ist lokal nicht vertrauenswürdig verifiziert.
Sicherer Fallback für einen einmalig extern geprüften Commit:
  ONIONCALL_TRUSTED_COMMIT=$TARGET scripts/private-update.sh
Besser: zukünftige Release-Tags/Commits mit einem lokal vertrauenswürdigen GPG-/SSH-Key signieren.
EOF
  exit 6
fi

echo "[3/4] Verifizierten Fast-Forward anwenden …"
git checkout main
git merge --ff-only "$TARGET"

echo "[4/4] Lokales Paket neu installieren (ohne Netz-Fallback) …"
PY="./.venv/bin/python"; [[ -x "$PY" ]] || PY=$(command -v python3)
"$PY" -m pip install --no-deps -e .

echo "Fertig. Es wurde ausschließlich der vorab verifizierte Commit installiert."
