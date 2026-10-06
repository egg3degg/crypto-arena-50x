#!/usr/bin/env bash
set -euo pipefail

cd /workspace

PORT="${WEB_PORT:-8088}"
TMUX_CONF="/exec-daemon/tmux.portal.conf"
SESSION="crypto_arena"
LOG="/tmp/crypto_arena.log"

if curl -sf "http://127.0.0.1:${PORT}/api/ping" >/dev/null 2>&1; then
  echo "CryptoArena dashboard already responding on port ${PORT}"
  exit 0
fi

if ! tmux -f "${TMUX_CONF}" has-session -t "${SESSION}" 2>/dev/null; then
  tmux -f "${TMUX_CONF}" new-session -d -s "${SESSION}" -c /workspace -- \
    "exec python3 run_tournament.py 2>&1 | tee ${LOG}"
fi

for _ in $(seq 1 90); do
  if curl -sf "http://127.0.0.1:${PORT}/api/ping" >/dev/null 2>&1; then
    echo "CryptoArena dashboard ready at http://127.0.0.1:${PORT}"
    exit 0
  fi
  sleep 2
done

echo "CryptoArena failed to become ready within 180s; see ${LOG}"
exit 1
