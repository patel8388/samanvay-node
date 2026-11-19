# Debian 12 private-node preparation

**Nothing has been installed on the VPS.** No SSH access was supplied, and no VPS connection, firewall change, public endpoint or mainnet deployment was attempted. This directory is included with the full source archive; it is not a ready-to-boot server image or a self-contained Python runtime.

## First: the unresolved Python prerequisite

The project requires **Python 3.12+**. [Debian 12's official default Python package](https://packages.debian.org/bookworm/python3) depends on Python 3.11. The scripts deliberately reject that default rather than changing project requirements or replacing system Python.

An appropriate existing Python interpreter must provide `venv`, `ensurepip` and `pip`. Select a specific interpreter with `SAMANVAY_PYTHON=/absolute/path/to/python3.12` if needed. No interpreter is downloaded or compiled by this bundle. Obtaining one is a separate preparation decision, not something performed on the owner's 1-GB VPS here.

An approved **offline wheelhouse** must also be supplied. It must contain `cryptography==50.0.2` and all dependencies, including compatible `cffi` and `pycparser` wheels. Pip's offline binary-only resolver checks the actual interpreter ABI, CPU architecture and Linux/glibc compatibility; compatible `abi3` wheels are allowed. There are no bundled wheels, no package downloads and no cryptography/cffi source builds. Use only trusted, integrity-checked dependency artifacts; a version pin alone is not a supply-chain audit.

## Read-only preparation checks

From the extracted source root, as an ordinary non-root user:

```bash
sha256sum -c SHA256SUMS
packaging/debian12/setup.sh --preflight --wheelhouse /existing/offline-wheelhouse
```

Preflight checks at least **700 MiB total RAM**, one online vCPU and **1 GiB free on the project filesystem**. These are minimum guardrails, not proof of fitness on the specified 1-vCPU/1-GB-RAM/10-GB-SSD machine. It does not measure a sustained workload, available RAM under contention, or the separate home/venv filesystem. Leave room for the OS, SQLite/WAL overhead and temporary/log growth.

Missing prerequisites cause failure without creating a runtime. The resolver may use temporary files but disables package caches and all indexes. No persistent installation, service, SSH or network configuration is changed.

## Later, only if explicitly chosen

The following commands are supplied for a later owner-controlled setup; **they were not run on the VPS**:

```bash
packaging/debian12/setup.sh --install --wheelhouse /existing/offline-wheelhouse
./verify.sh
packaging/debian12/run-local.sh
```

`--install` creates a **new dependency virtual environment** at `~/.local/share/samanvay-node/venv`, refusing to modify an existing one. It installs dependencies from local wheels only, then runs the checked source tree without building a project wheel. A failed dependency installation can leave the new venv for inspection; nothing starts automatically. If the default system Python is 3.11, run the verification commands using the selected interpreter/venv instead, for example:

```bash
~/.local/share/samanvay-node/venv/bin/python -m unittest discover -s tests -v
(cd docs/reference && ~/.local/share/samanvay-node/venv/bin/python -m unittest discover -s . -p test_reference_rules.py -v)
```

The runner binds **127.0.0.1 only**, remains in the foreground, and stops with Ctrl+C. No mining or wallet generation starts automatically. `SAMANVAY_VENV` can select a different dependency venv; pass `--db /absolute/path/to/disposable.sqlite3` for a custom database. Never open a firewall port or bind to a public interface.

## Optional limits template, disabled

`samanvay-local@.service` is a **manual user-service template only**. It is neither installed nor enabled. It has `MemoryMax=384M`, `TasksMax=16`, `CPUQuota=50%` and `Restart=no`, and no boot target. Its source-path placeholder must match the eventual checked extraction directory before any separately authorized use. These controls are not active merely because the file exists, and cgroup enforcement on the target VPS is unverified.

The node's own storage/height ceilings remain in force. Its experimental bounded retarget still has an intentionally easy target ceiling and has not had independent review; history remains trivially rewriteable and supports only disposable, no-value experiments. Independent volunteer checks, sustained VPS resource measurements, consensus/security review and later explicit endpoint approval are still outstanding.
