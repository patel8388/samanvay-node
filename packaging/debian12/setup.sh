#!/usr/bin/env bash
# Preparation only. The default preflight does not install or write runtime files.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WHEELHOUSE="$ROOT_DIR/packaging/debian12/wheelhouse"
VENV_DIR="${SAMANVAY_VENV:-$HOME/.local/share/samanvay-node/venv}"
MODE=preflight
usage() {
  echo "Usage: $0 [--preflight|--install] [--wheelhouse DIR] [--venv DIR]"
  echo "Default: read-only checks. Install: NEW user-local dependency venv, offline wheels only."
}
while (($#)); do
  case "$1" in
    --preflight) MODE=preflight; shift;;
    --install) MODE=install; shift;;
    --wheelhouse) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; WHEELHOUSE=$2; shift 2;;
    --venv) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; VENV_DIR=$2; shift 2;;
    -h|--help) usage; exit 0;;
    *) usage >&2; exit 2;;
  esac
done
# Prevent inherited pip settings or environment variables from enabling indexes,
# caches, remote find-links, requirements, targets, or version checks.
failures=0
note() { printf '%s\n' "$*"; }
fail() { printf 'FAIL: %s\n' "$*"; failures=$((failures + 1)); }
note "Preflight: preparation only; no service, public bind, download, or automatic start."
if [[ $EUID -eq 0 ]]; then fail "run as an ordinary user, not root"; fi
if [[ -r /proc/meminfo ]]; then
  mem_kb=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)
  (( mem_kb >= 700*1024 )) || fail "need at least 700 MiB total RAM"
  note "RAM: $((mem_kb/1024)) MiB total; this is not a measured memory-fit guarantee."
else fail "cannot check total RAM"; fi
cpus=$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 0)
(( cpus >= 1 )) || fail "need at least one online vCPU"
free_kb=$(df -Pk "$ROOT_DIR" | awk 'NR==2 {print $4}')
(( free_kb >= 1024*1024 )) || fail "need at least 1 GiB free on the project filesystem"
note "Project disk free: $((free_kb/1024)) MiB; keep space reserved for SQLite and OS."
python_bin=""
if [[ -n "${SAMANVAY_PYTHON:-}" ]]; then
  candidates=("$SAMANVAY_PYTHON")
else
  candidates=(python3.12 python3.13 python3.14 python3)
fi
for candidate in "${candidates[@]}"; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; raise SystemExit(not ((3,12) <= sys.version_info[:2] < (4,0)))' 2>/dev/null; then
      python_bin=$(command -v "$candidate")
      break
    fi
  fi
done
if [[ -z "$python_bin" ]]; then
  fail "Python 3.12+ is unavailable; Debian 12's default Python 3.11 is not supported. Supply an existing suitable interpreter; do not replace system Python or compile here."
else
  note "Python: $python_bin ($("$python_bin" --version 2>&1))"
  "$python_bin" -c 'import venv, ensurepip' 2>/dev/null || fail "interpreter needs venv and ensurepip support"
  "$python_bin" -m pip --version >/dev/null 2>&1 || fail "interpreter needs an existing pip for offline dependency preflight"
fi
[[ -d "$WHEELHOUSE" ]] || fail "offline wheelhouse absent: $WHEELHOUSE; provide compatible cryptography-50.0.2, cffi and pycparser wheels; no downloads or compilation attempted"
# Use a minimal inherited environment and isolated pip. /dev/null disables pip
# configuration explicitly; resolver checks ABI/platform tags and dependencies,
# including valid abi3 wheels, instead of guessing from cp312 filename patterns.
run_pip() {
  env -i HOME="$HOME" PATH="/usr/bin:/bin" PIP_CONFIG_FILE=/dev/null PYTHONDONTWRITEBYTECODE=1 \
    "$python_bin" -m pip --isolated --disable-pip-version-check --no-cache-dir "$@"
}
if (( failures == 0 )); then
  if ! run_pip install --dry-run --ignore-installed --no-index --only-binary=:all: \
      --find-links "$WHEELHOUSE" 'cryptography==50.0.2'; then
    fail "offline wheel resolution failed; provide wheels matching this interpreter, Linux/glibc and CPU architecture; do not compile"
  fi
fi
if (( failures )); then
  note "Preflight failed. No runtime changes made; resolve prerequisites first."
  exit 1
fi
if [[ "$MODE" == preflight ]]; then
  note "Preflight passed only. No files, packages, services, firewall, or SSH settings changed."
  exit 0
fi
[[ ! -e "$VENV_DIR" ]] || { echo "refusing to alter existing venv: $VENV_DIR" >&2; exit 1; }
mkdir -p "$(dirname "$VENV_DIR")"
"$python_bin" -m venv "$VENV_DIR"
# Never install/build the project: run the checked source tree with this venv.
python_bin="$VENV_DIR/bin/python"
if ! run_pip install --no-index --only-binary=:all: --find-links "$WHEELHOUSE" 'cryptography==50.0.2'; then
  echo "Dependency install failed; newly created venv remains for inspection. Nothing started." >&2
  exit 1
fi
"$python_bin" -c 'import cryptography; assert cryptography.__version__ == "50.0.2"'
note "Created dependency venv: $VENV_DIR. Project remains source-run; no service started."
