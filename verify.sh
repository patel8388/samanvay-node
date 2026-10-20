#!/usr/bin/env bash
# Run from this source tree. No installs, downloads, public services or paid calls.
set -euo pipefail
cd "$(dirname "$0")"
python3 - <<'PY'
import sys
import cryptography
print('Python:', sys.version.split()[0])
print('cryptography:', cryptography.__version__)
PY
python3 -m compileall -q samanvay tests
python3 -m unittest discover -s tests -v
(cd docs/reference && python3 -m unittest discover -s . -p test_reference_rules.py -v)
