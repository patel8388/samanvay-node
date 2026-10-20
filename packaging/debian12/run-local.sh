#!/usr/bin/env bash
# Foreground, manual, loopback-only runner. Requires setup.sh --install first.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="${SAMANVAY_VENV:-$HOME/.local/share/samanvay-node/venv}"
DB="$ROOT_DIR/.local/debian12/node.sqlite3"
PORT=8765
while (($#)); do
  case "$1" in
    --db) DB=${2:?--db needs a path}; shift 2;;
    --port) PORT=${2:?--port needs a number}; shift 2;;
    -h|--help) echo "Usage: $0 [--db PATH] [--port PORT] (always binds 127.0.0.1)"; exit 0;;
    *) echo "Unknown option: $1" >&2; exit 2;;
  esac
done
[[ "$PORT" =~ ^[0-9]+$ && "$PORT" -ge 1 && "$PORT" -le 65535 ]] || { echo "invalid port" >&2; exit 2; }
[[ -x "$VENV_DIR/bin/python" ]] || { echo "missing $VENV_DIR/bin/python; run setup.sh --install first" >&2; exit 1; }
DB="$(realpath -m -- "$DB")"
mkdir -p "$(dirname "$DB")"
cd "$ROOT_DIR"
exec "$VENV_DIR/bin/python" -m samanvay --db "$DB" serve --host 127.0.0.1 --port "$PORT"
